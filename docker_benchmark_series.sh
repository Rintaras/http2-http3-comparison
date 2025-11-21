#!/bin/bash
set -euo pipefail

# Docker環境でのベンチマークを複数の帯域 (Mbps) で連続実行するスクリプト
# 10,9,8,7,6,5,4,3,2,1Mbpsの順で実行します

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR" && pwd)"
cd "$PROJECT_ROOT"

# デフォルトの帯域リスト（10Mbpsから1Mbpsまで降順）
DEFAULT_RATES=("10mbit" "9mbit" "8mbit" "7mbit" "6mbit" "5mbit" "4mbit" "3mbit" "2mbit" "1mbit")

if [ "$#" -gt 0 ]; then
  # 引数で帯域一覧が指定された場合
  RATES=("$@")
elif [ -n "${RATES:-}" ]; then
  # 環境変数 RATES が指定されている場合（例: RATES="10mbit 5mbit 1mbit"）
  read -r -a RATES <<<"${RATES}"
else
  RATES=("${DEFAULT_RATES[@]}")
fi

if [ "${#RATES[@]}" -eq 0 ]; then
  echo "帯域が指定されていません。引数または RATES 環境変数で指定してください。" >&2
  exit 1
fi

echo "=========================================="
echo "Docker環境ベンチマーク連続実行スクリプト"
echo "=========================================="
echo "ベンチマーク対象帯域: ${RATES[*]}"
echo "PROJECT_ROOT: ${PROJECT_ROOT}"
echo "スクリプト: ${PROJECT_ROOT}/docker_benchmark.sh"
echo ""

# デフォルトの遅延範囲と反復回数（環境変数で上書き可能）
DELAYS="${DELAYS:-$(seq 0 1 150)}"
ITERATIONS="${ITERATIONS:-30}"
SLEEP_BETWEEN_SEC="${SLEEP_BETWEEN_SEC:-0.1}"

echo "設定:"
echo "  - 遅延範囲: ${DELAYS}"
echo "  - 各条件の反復回数: ${ITERATIONS}回"
echo "  - 反復間の待機時間: ${SLEEP_BETWEEN_SEC}秒"
echo ""

SUMMARY_FILE="${PROJECT_ROOT}/logs/docker_benchmark_series_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$SUMMARY_FILE")"
touch "$SUMMARY_FILE"

run_count=1
for rate in "${RATES[@]}"; do
  # 数値のみの場合は "mbit" を追加
  if [[ "$rate" =~ ^[0-9]+$ ]]; then
    rate="${rate}mbit"
  fi
  
  echo "------------------------------------------"
  echo "[$run_count/${#RATES[@]}] 帯域: ${rate}"
  echo "------------------------------------------"
  echo "開始時刻: $(date '+%Y-%m-%d %H:%M:%S')"
  
  tmp_log=$(mktemp)
  trap 'rm -f "$tmp_log"' RETURN
  
  # docker_benchmark.sh を実行（BANDWIDTH環境変数を渡す）
  if BANDWIDTH="$rate" DELAYS="$DELAYS" ITERATIONS="$ITERATIONS" SLEEP_BETWEEN_SEC="$SLEEP_BETWEEN_SEC" \
     bash "${PROJECT_ROOT}/docker_benchmark.sh" 2>&1 | tee "$tmp_log"; then
    
    # ログディレクトリのパスを取得（docker_benchmark.shの出力から）
    completed_path=$(grep -E '完了:|Complete:' "$tmp_log" | tail -n 1 | awk '{print $NF}' || echo "")
    if [ -z "$completed_path" ]; then
      # 別のパターンで検索（"結果ファイル:" や "出力先:" から）
      completed_path=$(grep -E '結果ファイル:|出力先:' "$tmp_log" | tail -n 1 | awk '{print $NF}' || echo "")
    fi
    
    if [ -n "$completed_path" ]; then
      echo "✅ 帯域 ${rate} のベンチマーク完了: ${completed_path}"
      echo "$(date '+%Y-%m-%d %H:%M:%S') ${rate} -> ${completed_path}" >>"$SUMMARY_FILE"
    else
      # ログディレクトリ名を推測（docker_benchmark.shの命名規則に基づく）
      bandwidth_suffix=$(echo "$rate" | sed 's/mbit//')
      latest_log=$(ls -td "${PROJECT_ROOT}/logs/docker_${bandwidth_suffix}mbit_"* 2>/dev/null | head -1 || echo "")
      if [ -n "$latest_log" ]; then
        echo "✅ 帯域 ${rate} のベンチマーク完了: ${latest_log}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') ${rate} -> ${latest_log}" >>"$SUMMARY_FILE"
      else
        echo "⚠️ 帯域 ${rate} のログパスを取得できませんでした" >&2
        echo "$(date '+%Y-%m-%d %H:%M:%S') ${rate} -> (パス取得失敗)" >>"$SUMMARY_FILE"
      fi
    fi
  else
    echo "❌ 帯域 ${rate} でベンチマークが失敗しました" >&2
    echo "$(date '+%Y-%m-%d %H:%M:%S') ${rate} -> 失敗" >>"$SUMMARY_FILE"
    # エラーが発生しても続行するか、ここで終了するかは要検討
    # とりあえず続行する設定にしておく（必要に応じて exit 1 に変更可能）
  fi
  
  echo "終了時刻: $(date '+%Y-%m-%d %H:%M:%S')"
  echo ""
  
  run_count=$((run_count + 1))
  trap - RETURN
  rm -f "$tmp_log"
done

echo "=========================================="
echo "全ての帯域でのベンチマークが完了しました"
echo "サマリー: ${SUMMARY_FILE}"
echo "=========================================="
cat "$SUMMARY_FILE"
echo "=========================================="

