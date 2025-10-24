#!/bin/bash

set -uo pipefail

# Client-side benchmark driving the Ubuntu server via tc API
# Saves results under project logs/<timestamp>/ and triggers visualization

SERVER_BASE="https://192.168.1.100:8443"
IFACE="eth0"
RATE="5mbit"
ITERATIONS="${ITERATIONS:-25}"    # override with env if needed
SLEEP_BETWEEN_SEC="${SLEEP_BETWEEN_SEC:-0.1}"  # per-iteration pause
DELAYS=(0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150)  # 0ms to 150ms in 1ms steps

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
  local warmup="${4:-false}"  # 4番目の引数でwarm-upモードを指定

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
      
      # warm-upモードでない場合のみCSVに記録
      if [ "$warmup" != "true" ]; then
        local proto_name
        proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
        echo "$ts,$proto_name,$latency_lbl,$i,$t,$kb,1" >> "$OUTPUT_CSV"
      fi
      return 0
    fi
  fi
  
  # warm-upモードでない場合のみCSVに記録
  if [ "$warmup" != "true" ]; then
    local proto_name
    proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
    echo "$ts,$proto_name,$latency_lbl,$i,,,0" >> "$OUTPUT_CSV"
  fi
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

# Initial stabilization with multiple connections
function initial_stabilization() {
  local url="$SERVER_BASE/1mb"
  echo "=== 初期安定化処理 (接続状態を安定化) ==="
  
  # Perform multiple warm-up connections for each protocol
  for i in {1..3}; do
    echo "  安定化接続 $i/3..."
    $CURL -sk --http3 "$url" -o /dev/null -m 15 || true
    $CURL -sk --http2 "$url" -o /dev/null -m 15 || true
    sleep 1.0  # Longer wait between stabilization connections
  done
  
  echo "  安定化完了"
  sleep 2.0  # Final wait to ensure all connections are settled
}

# (removed batch mode; per-iteration to keep request model identical across protocols)

echo "結果保存先: $LOG_DIR"

# Perform initial stabilization before starting measurements
initial_stabilization

for d in "${DELAYS[@]}"; do
  echo "========================================="
  echo "遅延 ${d}ms"
  echo "========================================="

  if [ "$d" -eq 0 ]; then
    # 0msの場合は遅延設定をスキップ（ベースライン測定）
    echo "ベースライン測定（遅延なし）"
  else
    tc_setup "$d"
    # Allow netem/htb settings to fully apply before measurement
    sleep 0.7
  fi

  # HTTP/3
  echo "=== HTTP/3 (${ITERATIONS}回) ==="
  if (( ITERATIONS > 5 )); then
    echo "  初回5回は除外されます"
    for i in $(seq 1 "$ITERATIONS"); do
      if (( i <= 5 )); then
        # 初回5回は実行するが、CSVには記録しない（warm-up用）
        bench_once H3 "${d}ms" "$i" "true" >/dev/null 2>&1 || true
        echo "  ウォームアップ $i/5..."
      else
        # 6回目以降は通常のベンチマークとして実行
        bench_once H3 "${d}ms" "$i" "false" >/dev/null || true
        if (( (i-5) % 10 == 0 )); then echo "  進捗: $((i-5))/$((ITERATIONS-5))"; fi
      fi
      # short idle to stabilize ACK clock and avoid back-to-back bursts
      sleep "$SLEEP_BETWEEN_SEC"
    done
  else
    echo "  全回数を記録します（5回以下のため除外なし）"
    for i in $(seq 1 "$ITERATIONS"); do
      bench_once H3 "${d}ms" "$i" "false" >/dev/null || true
      if (( i % 5 == 0 )); then echo "  進捗: $i/$ITERATIONS"; fi
      sleep "$SLEEP_BETWEEN_SEC"
    done
  fi

  # brief pause between protocol switches to avoid transient effects
  sleep 0.7

  # HTTP/2
  echo "=== HTTP/2 (${ITERATIONS}回) ==="
  if (( ITERATIONS > 5 )); then
    echo "  初回5回は除外されます"
    for i in $(seq 1 "$ITERATIONS"); do
      if (( i <= 5 )); then
        # 初回5回は実行するが、CSVには記録しない（warm-up用）
        bench_once H2 "${d}ms" "$i" "true" >/dev/null 2>&1 || true
        echo "  ウォームアップ $i/5..."
      else
        # 6回目以降は通常のベンチマークとして実行
        bench_once H2 "${d}ms" "$i" "false" >/dev/null || true
        if (( (i-5) % 10 == 0 )); then echo "  進捗: $((i-5))/$((ITERATIONS-5))"; fi
      fi
      sleep "$SLEEP_BETWEEN_SEC"
    done
  else
    echo "  全回数を記録します（5回以下のため除外なし）"
    for i in $(seq 1 "$ITERATIONS"); do
      bench_once H2 "${d}ms" "$i" "false" >/dev/null || true
      if (( i % 5 == 0 )); then echo "  進捗: $i/$ITERATIONS"; fi
      sleep "$SLEEP_BETWEEN_SEC"
    done
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


