#!/bin/bash

LATEST_DIR="logs/$(ls -t logs/ 2>/dev/null | grep -E '^[0-9]{8}_[0-9]{6}$' | head -1)"

if [ -z "$(ls -t logs/ 2>/dev/null | grep -E '^[0-9]{8}_[0-9]{6}$' | head -1)" ]; then
    echo "エラー: ベンチマーク結果が見つかりません"
    echo "まず ./benchmark_latency.sh を実行してください"
    exit 1
fi

echo "========================================="
echo "最新のベンチマーク結果"
echo "========================================="
echo ""
echo "保存場所: $LATEST_DIR"
echo ""

if [ -d "$LATEST_DIR" ]; then
    echo "=== ファイル一覧 ==="
    ls -lh "$LATEST_DIR" | tail -n +2 | awk '{print $9 "\t" $5}'
    
    echo ""
    echo "=== 生成されたグラフ ==="
    
    if [ -f "$LATEST_DIR/response_time_comparison.png" ]; then
        echo "✓ 応答速度比較グラフ: $LATEST_DIR/response_time_comparison.png"
    fi
    
    if [ -f "$LATEST_DIR/standard_deviation_vs_latency.png" ]; then
        echo "✓ 標準偏差線グラフ: $LATEST_DIR/standard_deviation_vs_latency.png"
    fi
    
    if [ -f "$LATEST_DIR/stability_percentile_range.png" ]; then
        echo "✓ P5-P95パーセンタイル範囲グラフ: $LATEST_DIR/stability_percentile_range.png"
    fi
    
    if [ -f "$LATEST_DIR/transfer_time_boxplot.png" ]; then
        echo "✓ 転送時間箱ひげ図: $LATEST_DIR/transfer_time_boxplot.png"
    fi
    
    if [ -f "$LATEST_DIR/detailed_analysis_report.txt" ]; then
        echo "✓ 詳細分析レポート: $LATEST_DIR/detailed_analysis_report.txt"
    fi
    
    echo ""
    echo "=== CSV確認 ==="
    if [ -f "$LATEST_DIR/benchmark_results.csv" ]; then
        echo "データ数: $(wc -l < "$LATEST_DIR/benchmark_results.csv") 行"
        echo ""
        echo "先頭5行:"
        head -6 "$LATEST_DIR/benchmark_results.csv"
    fi
else
    echo "エラー: ディレクトリが見つかりません"
fi

