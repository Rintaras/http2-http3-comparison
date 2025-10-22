#!/bin/bash

set -uo pipefail

# Client-side benchmark driving the Ubuntu server via tc API
# Saves results under project logs/<timestamp>/ and triggers visualization

SERVER_BASE="https://192.168.1.100:8443"
IFACE="eth0"
RATE="5mbit"
ITERATIONS="${ITERATIONS:-100}"    # override with env if needed
SLEEP_BETWEEN_SEC="${SLEEP_BETWEEN_SEC:-0.1}"  # per-iteration pause
DELAYS=(2 50 100 150)               # milliseconds (2ms base to stabilize TCP)

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
OUTPUT_CSV="$LOG_DIR/benchmark_results.csv"

# Prefer Homebrew curl with HTTP/3 support if available
if [ -x "/opt/homebrew/opt/curl/bin/curl" ]; then
  CURL="/opt/homebrew/opt/curl/bin/curl"
elif [ -x "/usr/local/opt/curl/bin/curl" ]; then
  CURL="/usr/local/opt/curl/bin/curl"
else
  CURL="curl"
fi

echo "timestamp,protocol,latency,iteration,time_total,speed_kbps,success" > "$OUTPUT_CSV"

function tc_setup() {
  local delay_ms="$1"
  # Allow non-zero exit (server may temporarily reject); continue benchmark
  $CURL -sk -X POST "$SERVER_BASE/tc/setup" \
    -H 'Content-Type: application/json' \
    -d "{\"if\":\"$IFACE\",\"rate\":\"$RATE\",\"delay_ms\":$delay_ms,\"loss_pct\":0}" \
    || true
}

function tc_reset() {
  $CURL -sk -X POST "$SERVER_BASE/tc/reset" \
    -H 'Content-Type: application/json' \
    -d "{\"if\":\"$IFACE\"}" >/dev/null || true
}

function bench_once() {
  local proto="$1"   # H2 or H3
  local latency_lbl="$2" # e.g., 0ms
  local i="$3"

  local url="$SERVER_BASE/1mb"
  local out
  if [ "$proto" = "H2" ]; then
    out=$($CURL -sk --http2 "$url" -o /dev/null -w "%{time_total} %{speed_download}" 2>/dev/null || true)
  else
    out=$($CURL -sk --http3 "$url" -o /dev/null -w "%{time_total} %{speed_download}" 2>/dev/null || true)
  fi

  local ts
  ts=$(date +%s)

  if [ -n "$out" ]; then
    local t s
    read -r t s <<<"$out"
    if [ -n "$t" ]; then
      # speed_download が空または0の場合は 1MB/秒から計算（1MB=1048576 bytes → 1024KB）
      local kb
      if [ -n "$s" ] && [ "$s" != "0" ]; then
        kb=$(awk -v v="$s" 'BEGIN{printf "%.2f", v/1024}')
      else
        kb=$(awk -v tt="$t" 'BEGIN{ if (tt>0) printf "%.2f", 1024/tt; else print "0.00" }')
      fi
      local proto_name
      proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
      echo "$ts,$proto_name,$latency_lbl,$i,$t,$kb,1" >> "$OUTPUT_CSV"
      return 0
    fi
  fi
  local proto_name
  proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
  echo "$ts,$proto_name,$latency_lbl,$i,,,0" >> "$OUTPUT_CSV"
  return 1
}

# Warm-up to stabilize TCP/TLS/QUIC state and avoid first-connection variance
function warm_up() {
  local url="$SERVER_BASE/1mb"
  # One request per protocol, errors ignored; small wait to let cwnd/conn settle
  $CURL -sk --http3 "$url" -o /dev/null -m 15 || true
  $CURL -sk --http2 "$url" -o /dev/null -m 15 || true
  sleep 0.5
}

# (removed batch mode; per-iteration to keep request model identical across protocols)

echo "結果保存先: $LOG_DIR"

for d in "${DELAYS[@]}"; do
  echo "========================================="
  echo "遅延 ${d}ms"
  echo "========================================="

  tc_setup "$d"
  # Allow netem/htb settings to fully apply before measurement
  sleep 0.7

  # Connection/TLS warm-up to reduce variance (first-request cost)
  warm_up

  # HTTP/3
  echo "=== HTTP/3 (${ITERATIONS}回) ==="
  for i in $(seq 1 "$ITERATIONS"); do
    bench_once H3 "${d}ms" "$i" >/dev/null || true
    # short idle to stabilize ACK clock and avoid back-to-back bursts
    sleep "$SLEEP_BETWEEN_SEC"
    if (( i % 10 == 0 )); then echo "  進捗: $i/$ITERATIONS"; fi
  done

  # brief pause between protocol switches to avoid transient effects
  sleep 0.7

  # HTTP/2
  echo "=== HTTP/2 (${ITERATIONS}回) ==="
  for i in $(seq 1 "$ITERATIONS"); do
    bench_once H2 "${d}ms" "$i" >/dev/null || true
    sleep "$SLEEP_BETWEEN_SEC"
    if (( i % 10 == 0 )); then echo "  進捗: $i/$ITERATIONS"; fi
  done

  # Trim first 5 measurements to remove initial connection variance for 2ms delay
  if [ "$d" = "2" ]; then
    echo "=== 初期ばらつき除去 (最初5件を除外) ==="
    # Count total lines in CSV
    total_lines=$(wc -l < "$OUTPUT_CSV")
    if [ "$total_lines" -gt 5 ]; then
      # Keep header + remove first 5 data lines
      head -1 "$OUTPUT_CSV" > "$OUTPUT_CSV.tmp"
      tail -n +7 "$OUTPUT_CSV" >> "$OUTPUT_CSV.tmp"
      mv "$OUTPUT_CSV.tmp" "$OUTPUT_CSV"
    fi
  fi
done

tc_reset

echo "結果ファイル: $OUTPUT_CSV"

# Optional: visualize if venv exists
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
  source "$PROJECT_ROOT/venv/bin/activate"
  export BENCHMARK_CSV="$OUTPUT_CSV"
  export BENCHMARK_OUTPUT_DIR="$LOG_DIR"
  python3 "$PROJECT_ROOT/scripts/visualize_response_time.py" 2>/dev/null || true
  python3 "$PROJECT_ROOT/scripts/visualize_standard_deviation.py" 2>/dev/null || true
  python3 "$PROJECT_ROOT/scripts/visualize_percentile_range.py" 2>/dev/null || true
  python3 "$PROJECT_ROOT/scripts/visualize_boxplot.py" 2>/dev/null || true
fi

echo "完了: $LOG_DIR"


