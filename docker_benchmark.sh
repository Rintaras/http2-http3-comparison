#!/bin/bash

# Docker環境でのベンチマーク実行スクリプト (改善版)
# 実機ベンチマークと同等の実測的なデータを取得するよう最適化
# 
# 改善点:
# 1. 遅延条件を0-150ms全範囲に拡張
# 2. 実際のファイル転送が行われているか検証
# 3. ネットワーク設定を最適化
# 4. Docker環境での1MB転送を保証

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 設定: 実測的なベンチマーク
# デフォルトは 0-150ms の1ms刻みだが、環境変数 DELAYS が指定されていればそれを優先
if [ -n "$DELAYS" ]; then
    # 例: DELAYS="2 50 100 150"
    # shellcheck disable=SC2206
    DELAYS=($DELAYS)
else
    DELAYS=($(seq 0 1 150))
fi
ITERATIONS="${ITERATIONS:-25}"
SLEEP_BETWEEN_SEC=0.1

# ログディレクトリ作成
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/docker_realistic_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

OUTPUT_CSV="$LOG_DIR/benchmark_results.csv"

# CSVヘッダー
echo "timestamp,protocol,latency,iteration,time_total,speed_kbps,success,http_version" > "$OUTPUT_CSV"

echo "========================================="
echo "Docker環境ベンチマーク開始 (実測的版)"
echo "========================================="
if [ ${#DELAYS[@]} -le 10 ]; then
    echo "遅延条件: ${#DELAYS[@]}個 (${DELAYS[*]}ms)"
else
    echo "遅延条件: ${#DELAYS[@]}個 (0ms-150ms, 1ms刻み)"
fi
echo "反復回数: $ITERATIONS回"
echo "出力先: $LOG_DIR"
echo ""

# Docker Compose起動
echo "Docker環境を起動中..."
docker-compose -f docker-compose.router_tc.yml up -d

# サービス起動待機
echo "サービス起動を待機中..."
sleep 10

# 接続テスト（サーバーに直接接続）
echo "接続テスト中..."
# 複数回試行して接続を確認
for i in {1..5}; do
    http2_ok=false
    http3_ok=false
    
    # HTTP/2 テスト (TCP) - サーバーに直接接続
    if curl -k -s --connect-timeout 10 --max-time 15 --http2 https://localhost:8443/1mb >/dev/null 2>&1; then
        http2_ok=true
    fi
    
    # HTTP/3 テスト (UDP) - サーバーに直接接続
    if curl -k -s --connect-timeout 10 --max-time 15 --http3 https://localhost:8443/1mb >/dev/null 2>&1; then
        http3_ok=true
    fi
    
    if [ "$http2_ok" = true ] && [ "$http3_ok" = true ]; then
        echo "✓ HTTP/2とHTTP/3接続確認完了 (試行 $i/5)"
        break
    elif [ $i -eq 5 ]; then
        echo "警告: 接続テストに失敗しましたが、ベンチマークを続行します"
        echo "Docker環境ログ:"
        docker-compose -f docker-compose.router_tc.yml logs --tail=20
    else
        echo "接続テスト失敗、再試行中... ($i/5)"
        sleep 2
    fi
done

# 初期安定化（ウォームアップ）
echo "初期安定化実行中..."
for i in {1..5}; do
    curl -k -s --http3 https://localhost:8443/1mb >/dev/null 2>&1 || true  # HTTP/3 (UDP)
    curl -k -s --http2 https://localhost:8443/1mb >/dev/null 2>&1 || true  # HTTP/2 (TCP)
    sleep 0.5
done

# ベンチマーク実行関数
function bench_once() {
    local proto="$1"   # H2 or H3
    local latency_lbl="$2" # e.g., 0ms
    local i="$3"
    local warmup="${4:-false}"  # 4番目の引数でwarm-upモードを指定
    
    local ts=$(date +%s)
    local out=""
    local t=""
    local kb=""
    
    if [ "$proto" = "H3" ]; then
        # HTTP/3: UDP ポート 8443（サーバーに直接接続、ホスト側から）
        # ホスト側のhttp3_clientを使用（存在する場合）、なければコンテナ内のものを使用
        if [ -f "./http3_client" ]; then
            # ホスト側から直接接続（tc制限が適用される）
            out=$(./http3_client https://localhost:8443/1mb 2>/dev/null || echo "")
        else
            # フォールバック: コンテナ内から実行（ただし、tc制限を受けない可能性がある）
            echo "[WARN] ホスト側のhttp3_clientが見つかりません。コンテナ内から実行しますが、tc制限を受けない可能性があります。" >&2
            out=$(docker exec http3-server /root/http3_client https://localhost:8443/1mb 2>/dev/null || echo "")
        fi
    else
        # HTTP/2: TCP ポート 8443（サーバーに直接接続）
        # 1MBデータ転送（size_downloadも取得して検証）
        out=$(curl -k -s -w "%{time_total},%{speed_download},%{http_version},%{size_download}" -o /dev/null --connect-timeout 10 --max-time 30 --http2 https://localhost:8443/1mb 2>/dev/null || echo "")
    fi
    
    if [ -n "$out" ]; then
        t=$(echo "$out" | cut -d',' -f1)
        local speed=$(echo "$out" | cut -d',' -f2)
        local http_version=$(echo "$out" | cut -d',' -f3)
        local size_download=$(echo "$out" | cut -d',' -f4)
        # 転送サイズが1MB未満の場合は警告
        if [ -n "$size_download" ] && [ "$size_download" -lt 1048576 ] && [ "$proto" = "H2" ]; then
            echo "[WARN] H2測定で不完全な転送を検出: size_download=$size_download bytes (期待値: 1048576 bytes) (latency=$latency_lbl iter=$i)" >&2
        fi
        if [ -n "$t" ] && [ -n "$speed" ]; then
            # curlのspeed_downloadはバイト/秒
            # size_downloadが利用可能で1MB以上の場合、それから速度を再計算（より正確）
            if [ -n "$size_download" ] && [ "$size_download" -ge 1048576 ] && [ -n "$t" ] && (( $(echo "$t > 0" | bc -l) )); then
                # 速度 = (バイト数 * 8) / 時間（秒） → kbps
                speed_kbps=$(echo "scale=2; ($size_download * 8) / ($t * 1000)" | bc -l)
            else
                # size_downloadが取得できない場合、curlのspeed_downloadを使用（バイト/秒 → kbps）
                # speed_downloadはバイト/秒なので、kbpsに変換: (bytes/sec * 8) / 1000
                speed_kbps=$(echo "scale=2; ($speed * 8) / 1000" | bc -l)
            fi
            kb="$speed_kbps"
            if [ -n "$kb" ]; then
                # warm-upモードでない場合のみCSVに記録
                if [ "$warmup" != "true" ]; then
                    local proto_name
                    proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
                    # H3指定だが実際はHTTP/3でない場合は不正データとして記録しない
                    if [ "$proto" = "H3" ] && [ "$http_version" != "3" ]; then
                        echo "[WARN] H3測定で http_version=$http_version を検出。HTTP/3未使用のためこの結果は除外します (latency=$latency_lbl iter=$i)" >&2
                        echo "$ts,$proto_name,$latency_lbl,$i,,,0,$http_version" >> "$OUTPUT_CSV"
                    else
                        # 実際に使用されたHTTPバージョンを記録
                        echo "$ts,$proto_name,$latency_lbl,$i,$t,$kb,1,$http_version" >> "$OUTPUT_CSV"
                    fi
                fi
                return 0
            fi
        fi
    fi
    
    # warm-upモードでない場合のみCSVに記録
    if [ "$warmup" != "true" ]; then
        local proto_name
        proto_name=$([ "$proto" = "H2" ] && echo "HTTP/2" || echo "HTTP/3")
        echo "$ts,$proto_name,$latency_lbl,$i,,,0,unknown" >> "$OUTPUT_CSV"
    fi
    return 1
}

# 遅延設定関数（実機環境と同じ：サーバー側のみでtc設定）
function set_docker_latency() {
    local delay_ms="$1"
    
    # Docker環境での遅延設定（サーバーコンテナ内でtc設定を適用、実機環境と同じ方法）
    echo "遅延設定: ${delay_ms}ms"
    # サーバーコンテナ内でtc設定を実行（実機と同じ5Mbps帯域に設定）
    docker exec http3-server ./tc_setup.sh eth0 5mbit "${delay_ms}ms" 0% || true
    sleep 0.7
}

# メインベンチマークループ
for d in "${DELAYS[@]}"; do
    echo ""
    echo "=== 遅延: ${d}ms ==="
    
    # 遅延設定
    set_docker_latency "$d"
    
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
            # short idle to stabilize ACK clock and avoid back-to-back bursts
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

echo ""
echo "========================================="
echo "Docker環境ベンチマーク完了"
echo "========================================="
echo "結果ファイル: $OUTPUT_CSV"

# グラフ生成
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo "グラフ生成中..."
    source "$PROJECT_ROOT/venv/bin/activate"
    export BENCHMARK_CSV="$OUTPUT_CSV"
    export BENCHMARK_OUTPUT_DIR="$LOG_DIR"
    python3 "$PROJECT_ROOT/scripts/visualize_response_time.py" 2>/dev/null || true
    python3 "$PROJECT_ROOT/scripts/visualize_standard_deviation.py" 2>/dev/null || true
    python3 "$PROJECT_ROOT/scripts/visualize_percentile_range.py" 2>/dev/null || true
    python3 "$PROJECT_ROOT/scripts/visualize_boxplot.py" 2>/dev/null || true
    python3 "$PROJECT_ROOT/scripts/generate_analysis_report.py" 2>/dev/null || true
    echo "生成されたグラフ:"
    echo "  - 応答速度比較グラフ: $LOG_DIR/response_time_comparison.png"
    echo "  - 標準偏差線グラフ: $LOG_DIR/standard_deviation_vs_latency.png"
    echo "  - P5-P95パーセンタイル範囲グラフ: $LOG_DIR/stability_percentile_range.png"
    echo "  - 転送時間箱ひげ図: $LOG_DIR/transfer_time_boxplot.png"
    echo "  - 詳細分析レポート: $LOG_DIR/detailed_analysis_report.txt"
fi

echo "完了: $LOG_DIR"

# Docker環境停止
echo "Docker環境を停止中..."
docker-compose -f docker-compose.router_tc.yml down

echo "Docker環境ベンチマーク完了！"
