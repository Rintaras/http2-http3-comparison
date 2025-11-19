#!/bin/bash
set -euo pipefail

# 実機ベンチマークを複数の帯域 (Mbps) で連続実行するヘルパースクリプト
# 既存の run_benchmark.sh を呼び出し、帯域を切り替えながら順番に実行します。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

DEFAULT_RATES=("2mbit" "4mbit" "6mbit" "7mbit" "8mbit" "9mbit")

if [ "$#" -gt 0 ]; then
  # 引数で帯域一覧が指定された場合
  RATES=("$@")
elif [ -n "${RATES:-}" ]; then
  # 環境変数 RATES が指定されている場合（例: RATES="2mbit 5mbit"）
  read -r -a RATES <<<"${RATES}"
else
  RATES=("${DEFAULT_RATES[@]}")
fi

if [ "${#RATES[@]}" -eq 0 ]; then
  echo "帯域が指定されていません。引数または RATES 環境変数で指定してください。" >&2
  exit 1
fi

echo "=========================================="
echo "実機ベンチマーク連続実行スクリプト"
echo "=========================================="
echo "ベンチマーク対象帯域: ${RATES[*]}"
echo "PROJECT_ROOT: ${PROJECT_ROOT}"
echo "スクリプト: ${SCRIPT_DIR}/run_benchmark.sh"
echo

SUMMARY_FILE="${PROJECT_ROOT}/logs/benchmark_series_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$SUMMARY_FILE")"
touch "$SUMMARY_FILE"

run_count=1
for rate in "${RATES[@]}"; do
  if [[ "$rate" =~ ^[0-9]+$ ]]; then
    rate="${rate}mbit"
  fi
  echo "------------------------------------------"
  echo "[$run_count/${#RATES[@]}] 帯域: ${rate}"
  echo "------------------------------------------"

  tmp_log=$(mktemp)
  trap 'rm -f "$tmp_log"' RETURN

  if RATE="$rate" ./run_benchmark.sh | tee "$tmp_log"; then
    completed_path=$(grep -E 'Complete:' "$tmp_log" | tail -n 1 | awk '{print $2}')
    if [ -n "$completed_path" ]; then
      echo "✅ 帯域 ${rate} のベンチマーク完了: ${completed_path}"
      echo "$(date +%F_%T) ${rate} -> ${completed_path}" >>"$SUMMARY_FILE"
    else
      echo "⚠️ 帯域 ${rate} のログパスを取得できませんでした (run_benchmark.sh の出力形式を確認してください)" >&2
      echo "$(date +%F_%T) ${rate} -> (パス取得失敗)" >>"$SUMMARY_FILE"
    fi
  else
    echo "❌ 帯域 ${rate} でベンチマークが失敗しました" >&2
    echo "$(date +%F_%T) ${rate} -> 失敗" >>"$SUMMARY_FILE"
    exit 1
  fi
  run_count=$((run_count + 1))
  trap - RETURN
  rm -f "$tmp_log"
done

echo
echo "=========================================="
echo "全ての帯域でのベンチマークが完了しました"
echo "サマリー: ${SUMMARY_FILE}"
cat "$SUMMARY_FILE"
echo "=========================================="


