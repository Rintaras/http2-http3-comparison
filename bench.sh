#!/bin/bash

# 簡易ベンチマーク実行スクリプト
# 使い方:
#   ./bench.sh                # 既定 (ITERATIONS=50, SLEEP_BETWEEN_SEC=0.1)
#   ./bench.sh -n 100         # 回数を指定
#   ./bench.sh -p 0.2         # 1回ごとのスリープ秒数
#   ./bench.sh --server https://192.168.1.100:8443  # サーバーURLを上書き
#   ./bench.sh --iface eth0   # サーバー側IF名を上書き
#   ./bench.sh --rate 5mbit   # 帯域を上書き

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
cd "$PROJECT_ROOT"

# 既定値
ITERATIONS=25
SLEEP_BETWEEN_SEC=0.1
SERVER_BASE=""
IFACE=""
RATE=""

print_help() {
  cat <<USAGE
Usage: ./bench.sh [options]
  -n NUM              1条件あたりの試行回数 (default: 50)
  -p SECONDS          各試行間のスリープ秒 (default: 0.1)
  --server URL        サーバーURLを上書き (例: https://192.168.1.100:8443)
  --iface NAME        サーバー側IF名 (例: eth0)
  --rate RATE         帯域 (例: 5mbit)
  -h, --help          このヘルプを表示

例:
  ./bench.sh -n 100 -p 0.2 --server https://192.168.1.100:8443 --iface eth0 --rate 5mbit
USAGE
}

# 引数解析
while (( "$#" )); do
  case "$1" in
    -n)
      ITERATIONS="$2"; shift 2;;
    -p)
      SLEEP_BETWEEN_SEC="$2"; shift 2;;
    --server)
      SERVER_BASE="$2"; shift 2;;
    --iface)
      IFACE="$2"; shift 2;;
    --rate)
      RATE="$2"; shift 2;;
    -h|--help)
      print_help; exit 0;;
    *)
      echo "Unknown option: $1" >&2; print_help; exit 1;;
  esac
done

# venv があれば有効化（グラフ生成に必要な依存を使用）
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/venv/bin/activate"
fi

echo "=== 実行設定 ==="
echo "Iterations: ${ITERATIONS}"
echo "Sleep/sec:  ${SLEEP_BETWEEN_SEC}"
if [ -n "$SERVER_BASE" ]; then echo "Server:     ${SERVER_BASE}"; fi
if [ -n "$IFACE" ]; then echo "Iface:      ${IFACE}"; fi
if [ -n "$RATE" ]; then echo "Rate:       ${RATE}"; fi
echo

# 環境変数を組み立て
ENVLINE=(ITERATIONS="$ITERATIONS" SLEEP_BETWEEN_SEC="$SLEEP_BETWEEN_SEC")
if [ -n "$SERVER_BASE" ]; then ENVLINE+=(SERVER_BASE="$SERVER_BASE"); fi
if [ -n "$IFACE" ]; then ENVLINE+=(IFACE="$IFACE"); fi
if [ -n "$RATE" ]; then ENVLINE+=(RATE="$RATE"); fi

# 実行
echo "=== ベンチマーク開始 ==="
env "${ENVLINE[@]}" "$PROJECT_ROOT/test_ubuntu_connection/run_benchmark.sh"
EXIT_CODE=$?

echo
echo "=== 最新結果の概要 ==="
"$PROJECT_ROOT/scripts/view_latest_results.sh" || true

exit "$EXIT_CODE"


