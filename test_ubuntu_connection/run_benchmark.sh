#!/bin/bash
set -uo pipefail
SERVER_BASE="https://192.168.1.100:8443"
IFACE="eth0"
RATE="${RATE:-5mbit}"
ITERATIONS="${ITERATIONS:-25}"
SLEEP_BETWEEN_SEC="${SLEEP_BETWEEN_SEC:-0.1}"
DELAYS=($(seq 0 1 150))
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
OUTPUT_CSV="$LOG_DIR/benchmark_results.csv"
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
  local ts=$(date +%s)
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
        local proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
        echo "$ts,$proto_name,$latency_lbl,$i,$t,$kb,1,$http_ver" >> "$OUTPUT_CSV"
      fi
      return 0
    fi
  fi
  if [ "$warmup" != "true" ]; then
    local proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
    echo "$ts,$proto_name,$latency_lbl,$i,,,0,unknown" >> "$OUTPUT_CSV"
  fi
  return 1
}
function initial_stabilization() {
  local url="$SERVER_BASE/1mb"
  echo "=== Initial stabilization ==="
  for i in {1..3}; do
    echo "  Connection $i/3..."
    $CURL -sk --http3 "$url" -o /dev/null -m 15 || true
    $CURL -sk --http2 "$url" -o /dev/null -m 15 || true
    sleep 1.0
  done
  echo "  Stabilization complete"
  sleep 2.0
}
echo "Log directory: $LOG_DIR"
echo ""
echo "=========================================="
echo "Real Measurement Benchmark"
echo "=========================================="
echo "Delay conditions: ${#DELAYS[@]} (0-150ms, 1ms steps)"
echo "Iterations: $ITERATIONS per condition"
echo "Server: $SERVER_BASE"
echo "Bandwidth: $RATE"
echo "Protocol: HTTP/2 vs HTTP/3"
echo ""
initial_stabilization
for d in "${DELAYS[@]}"; do
  echo "=========================================="
  echo "Delay: ${d}ms"
  echo "=========================================="
  if [ "$d" -eq 0 ]; then
    echo "Baseline measurement (delay=0ms)"
  fi
  tc_setup "$d"
  sleep 0.7
  echo "HTTP/3 ($ITERATIONS iterations)"
  if (( ITERATIONS > 5 )); then
    echo "  First 5 excluded from results"
    for i in $(seq 1 "$ITERATIONS"); do
      if (( i <= 5 )); then
        bench_once H3 "${d}ms" "$i" "true" >/dev/null 2>&1 || true
        echo "  Warmup $i/5..."
      else
        bench_once H3 "${d}ms" "$i" "false" >/dev/null || true
        if (( (i-5) % 10 == 0 )); then echo "  Progress: $((i-5))/$((ITERATIONS-5))"; fi
      fi
      sleep "$SLEEP_BETWEEN_SEC"
    done
  else
    echo "  All iterations recorded (5 or fewer)"
    for i in $(seq 1 "$ITERATIONS"); do
      bench_once H3 "${d}ms" "$i" "false" >/dev/null || true
      if (( i % 5 == 0 )); then echo "  Progress: $i/$ITERATIONS"; fi
      sleep "$SLEEP_BETWEEN_SEC"
    done
  fi
  sleep 0.7
  echo "HTTP/2 ($ITERATIONS iterations)"
  if (( ITERATIONS > 5 )); then
    echo "  First 5 excluded from results"
    for i in $(seq 1 "$ITERATIONS"); do
      if (( i <= 5 )); then
        bench_once H2 "${d}ms" "$i" "true" >/dev/null 2>&1 || true
        echo "  Warmup $i/5..."
      else
        bench_once H2 "${d}ms" "$i" "false" >/dev/null || true
        if (( (i-5) % 10 == 0 )); then echo "  Progress: $((i-5))/$((ITERATIONS-5))"; fi
      fi
      sleep "$SLEEP_BETWEEN_SEC"
    done
  else
    echo "  All iterations recorded (5 or fewer)"
    for i in $(seq 1 "$ITERATIONS"); do
      bench_once H2 "${d}ms" "$i" "false" >/dev/null || true
      if (( i % 5 == 0 )); then echo "  Progress: $i/$ITERATIONS"; fi
      sleep "$SLEEP_BETWEEN_SEC"
    done
  fi
done
tc_reset
echo "Results: $OUTPUT_CSV"
echo ""
if [ -f "$PROJECT_ROOT/scripts/validate_benchmark_data.py" ]; then
  echo "=========================================="
  echo "Validating benchmark data"
  echo "=========================================="
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
echo "Complete: $LOG_DIR"
