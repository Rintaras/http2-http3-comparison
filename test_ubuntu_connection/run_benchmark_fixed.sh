#!/bin/bash

set -uo pipefail

# Client-side benchmark driving the Ubuntu server via tc API
# Saves results under project logs/<timestamp>/ and triggers visualization

SERVER_BASE="https://192.168.1.100:8443"
IFACE="eth0"
RATE="5mbit"
ITERATIONS="${ITERATIONS:-25}"
SLEEP_BETWEEN_SEC="${SLEEP_BETWEEN_SEC:-0.1}"
# 0ms から 150ms まで 1ms 刻みで全遅延条件を測定（実測的なベンチマーク）
DELAYS=($(seq 0 1 150))

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

echo "timestamp,protocol,latency,iteration,time_total,speed_kbps,success,http_version" > "$OUTPUT_CSV"

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
  local proto="$1"
  local latency_lbl="$2"
  local i="$3"
  local warmup="${4:-false}"

  local url="$SERVER_BASE/1mb"
  local out
  if [ "$proto" = "H2" ]; then
    out=$($CURL -sk --http2 "$url" -o /dev/null -w "%{time_total} %{speed_download} %{http_version}" 2>/dev/null || true)
  else
    out=$($CURL -sk --http3 "$url" -o /dev/null -w "%{time_total} %{speed_download} %{http_version}" 2>/dev/null || true)
  fi

  local ts
  ts=$(date +%s)

  if [ -n "$out" ]; then
    local t s http_ver
    read -r t s http_ver <<<"$out"
    if [ -n "$t" ]; then
      local kb
      if [ -n "$s" ] && [ "$s" != "0" ]; then
        kb=$(awk -v v="$s" 'BEGIN{printf "%.2f", v/1024}')
      else
        kb=$(awk -v tt="$t" 'BEGIN{ if (tt>0) printf "%.2f", 1024/tt; else print "0.00" }')
      fi

      if [ "$warmup" != "true" ]; then
        local proto_name
        proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
        echo "$ts,$proto_name,$latency_lbl,$i,$t,$kb,1,$http_ver" >> "$OUTPUT_CSV"
      fi
      return 0
    fi
  fi

  if [ "$warmup" != "true" ]; then
    local proto_name
    proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
    echo "$ts,$proto_name,$latency_lbl,$i,,,0,unknown" >> "$OUTPUT_CSV"
  fi
  return 1
}

function warm_up() {
  local url="$SERVER_BASE/1mb"
  $CURL -sk --http3 "$url" -o /dev/null -m 15 || true
  $CURL -sk --http2 "$url" -o /dev/null -m 15 || true
  sleep 0.5
}

function initial_stabilization() {
  local url="$SERVER_BASE/1mb"
  echo "=== 初期安定化処理 (接続状態を安定化) ==="

  for i in {1..3}; do
    echo "  安定化接続 $i/3..."
    $CURL -sk --http3 "$url" -o /dev/null -m 15 || true
    $CURL -sk --http2 "$url" -o /dev/null -m 15 || true
    sleep 1.0
  done

  echo "  安定化完了"
  sleep 2.0
}

echo "結果保存先: $LOG_DIR"
echo ""
echo "========================================="
echo "実機ベンチマーク設定"
echo "========================================="
echo "遅延条件: ${#DELAYS[@]}個 (0-150ms全範囲, 1ms刻み)"
echo "反復回数: $ITERATIONS回"
echo "サーバー: $SERVER_BASE"
echo "帯域制限: $RATE"
echo "プロトコル: HTTP/2 vs HTTP/3 (実測的ベンチマーク)"
echo ""

initial_stabilization

for d in "${DELAYS[@]}"; do
  echo "========================================="
  echo "遅延 ${d}ms"
  echo "========================================="

  if [ "$d" -eq 0 ]; then
    echo "ベースライン測定（遅延なし）"
  else
    tc_setup "$d"
    sleep 0.7
  fi

  echo "=== HTTP/3 (${ITERATIONS}回) ==="
  if (( ITERATIONS > 5 )); then
    echo "  初回5回は除外されます"
    for i in $(seq 1 "$ITERATIONS"); do
      if (( i <= 5 )); then
        bench_once H3 "${d}ms" "$i" "true" >/dev/null 2>&1 || true
        echo "  ウォームアップ $i/5..."
      else
        bench_once H3 "${d}ms" "$i" "false" >/dev/null || true
        if (( (i-5) % 10 == 0 )); then echo "  進捗: $((i-5))/$((ITERATIONS-5))"; fi
      fi
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

  sleep 0.7

  echo "=== HTTP/2 (${ITERATIONS}回) ==="
  if (( ITERATIONS > 5 )); then
    echo "  初回5回は除外されます"
    for i in $(seq 1 "$ITERATIONS"); do
      if (( i <= 5 )); then
        bench_once H2 "${d}ms" "$i" "true" >/dev/null 2>&1 || true
        echo "  ウォームアップ $i/5..."
      else
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
echo ""

if [ -f "$PROJECT_ROOT/scripts/validate_benchmark_data.py" ]; then
  echo "========================================="
  echo "ベンチマークデータ検証"
  echo "========================================="
  python3 "$PROJECT_ROOT/scripts/validate_benchmark_data.py" "$OUTPUT_CSV" || true
  echo ""
fi

if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
  source "$PROJECT_ROOT/venv/bin/activate"
  export BENCHMARK_CSV="$OUTPUT_CSV"
  export BENCHMARK_OUTPUT_DIR="$LOG_DIR"
  python3 "$PROJECT_ROOT/scripts/visualize_response_time.py" 2>/dev/null || true
  python3 "$PROJECT_ROOT/scripts/visualize_standard_deviation.py" 2>/dev/null || true
  python3 "$PROJECT_ROOT/scripts/visualize_percentile_range.py" 2>/dev/null || true
  python3 "$PROJECT_ROOT/scripts/visualize_boxplot.py" 2>/dev/null || true
  python3 "$PROJECT_ROOT/scripts/generate_analysis_report.py" 2>/dev/null || true
fi

echo "完了: $LOG_DIR"
