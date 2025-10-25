#!/usr/bin/env python3
"""
P5-P95パーセンタイル範囲を可視化するスクリプト
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import matplotlib.font_manager as fm
import seaborn as sns

sns.set_style("whitegrid")

plt.rcParams['font.family'] = 'sans-serif'
available_fonts = [f.name for f in fm.fontManager.ttflist]
japanese_fonts = ['Hiragino Sans', 'Hiragino Kaku Gothic Pro', 'Yu Gothic', 'Meiryo', 'MS Gothic', 'AppleGothic']
selected_font = None
for font in japanese_fonts:
    if font in available_fonts:
        selected_font = font
        break

if selected_font:
    plt.rcParams['font.sans-serif'] = [selected_font, 'DejaVu Sans']
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.figsize'] = (20, 6)
plt.rcParams['font.size'] = 10

def visualize_percentile_range(csv_file, output_dir):
    """P5-P95パーセンタイル範囲を可視化"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # 遅延条件のリスト
    latencies = ['2ms', '50ms', '100ms', '150ms']
    
    # プロトコル別の色設定（response_time_comparisonと同じ色）
    colors = {'HTTP/2': '#2E86AB', 'HTTP/3': '#A23B72'}
    
    # データを準備
    protocols = ['HTTP/2', 'HTTP/3']
    
    # P5-P95範囲を計算
    percentile_data = {}
    for protocol in protocols:
        percentile_data[protocol] = []
        for lat in latencies:
            data = df[(df['protocol'] == protocol) & (df['latency'] == lat)]['time_total']
            if not data.empty and len(data) > 1:
                p5 = data.quantile(0.05)
                p95 = data.quantile(0.95)
                percentile_range = p95 - p5
                percentile_data[protocol].append(percentile_range)
            else:
                percentile_data[protocol].append(0)
    
    # グラフを作成
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # プロトコル別にプロット
    for i, protocol in enumerate(['HTTP/2', 'HTTP/3']):
        ax.plot(latencies, percentile_data[protocol], 
                 marker='o', linewidth=3.5, markersize=12,
                 label=protocol, color=colors[protocol], zorder=3)

    # Y軸の範囲を動的に調整
    all_percentiles = []
    for protocol in ['HTTP/2', 'HTTP/3']:
        if protocol in percentile_data:
            all_percentiles.extend(percentile_data[protocol])

    if all_percentiles:
        min_val = min(all_percentiles)
        max_val = max(all_percentiles)
        margin = (max_val - min_val) * 0.1
        ax.set_ylim(max(0, min_val - margin), max_val + margin)
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=16, fontweight='bold')
    ax.set_ylabel('P5-P95パーセンタイル範囲 (秒)', fontsize=16, fontweight='bold')
    ax.set_title('P5-P95パーセンタイル範囲の比較', fontsize=18, fontweight='bold', pad=20)
    ax.legend(fontsize=14, loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1)
    # X軸ラベルを間引いて表示（10ms刻みで表示）
    step = 10  # 10ms刻みで表示
    tick_positions = []
    tick_labels = []
    for i in range(0, len(latencies), step):
        tick_positions.append(latencies[i])
        tick_labels.append(latencies[i])
    
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=10)
    ax.tick_params(axis='y', labelsize=12)
    
    # レイアウトを調整
    plt.tight_layout()
    
    # ファイルを保存
    output_file = os.path.join(output_dir, 'stability_percentile_range.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"P5-P95パーセンタイル範囲グラフを保存しました: {output_file}")
    plt.close()
    
    # 統計サマリーを表示
    print("\n=== P5-P95パーセンタイル範囲統計サマリー ===")
    for i, lat in enumerate(latencies):
        h2_range = percentile_data['HTTP/2'][i]
        h3_range = percentile_data['HTTP/3'][i]
        if h2_range > 0 and h3_range > 0:
            ratio = h2_range / h3_range
            winner = "HTTP/2" if h2_range < h3_range else "HTTP/3" if h3_range < h2_range else "同等"
            print(f"{lat}: HTTP/2={h2_range:.3f}s, HTTP/3={h3_range:.3f}s, 比={ratio:.2f}倍, 勝者: {winner}")
        else:
            print(f"{lat}: データ不足")

if __name__ == "__main__":
    csv_file_path = os.environ.get('BENCHMARK_CSV')
    output_directory = os.environ.get('BENCHMARK_OUTPUT_DIR')
    
    if not csv_file_path or not output_directory:
        print("エラー: BENCHMARK_CSV と BENCHMARK_OUTPUT_DIR 環境変数を設定してください")
        print("例: BENCHMARK_CSV='logs/latest/benchmark_results.csv' BENCHMARK_OUTPUT_DIR='logs/latest' python3 scripts/visualize_percentile_range.py")
        exit(1)

    if not os.path.exists(csv_file_path):
        print(f"エラー: CSVファイルが見つかりません: {csv_file_path}")
        exit(1)
    
    visualize_percentile_range(csv_file_path, output_directory)
