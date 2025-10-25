#!/usr/bin/env python3
"""
転送時間と遅延で箱ひげ図を可視化するスクリプト
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
plt.rcParams['figure.figsize'] = (30, 6)
plt.rcParams['font.size'] = 8

def visualize_boxplot(csv_file, output_dir):
    """転送時間と遅延で箱ひげ図を可視化"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # 遅延条件を動的に取得（数値でソート）
    latencies_str = df['latency'].unique()
    lat_values = [int(lat.replace('ms', '')) for lat in latencies_str]
    
    # 数値でソートしてインデックスを取得
    sorted_indices = sorted(range(len(lat_values)), key=lambda i: lat_values[i])
    latencies = [latencies_str[i] for i in sorted_indices]
    
    # プロトコル別の色設定（response_time_comparisonと同じ色）
    colors = {'HTTP/2': '#2E86AB', 'HTTP/3': '#A23B72'}
    
    # データを準備
    box_plot_data = []
    box_plot_labels = []
    box_plot_colors = []
    
    for protocol in ['HTTP/2', 'HTTP/3']:
        data = df[df['protocol'] == protocol]
        for lat in latencies:
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                box_plot_data.append(lat_data)
                box_plot_labels.append(f'{protocol}\n{lat}')
                box_plot_colors.append(colors[protocol])
    
    # グラフを作成
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 箱ひげ図を描画
    bp = ax.boxplot(box_plot_data, patch_artist=True, showfliers=False, widths=0.6)

    # Y軸の範囲を動的に調整
    all_values = []
    for data in box_plot_data:
        all_values.extend(data)

    if all_values:
        min_val = min(all_values)
        max_val = max(all_values)
        margin = (max_val - min_val) * 0.1
        ax.set_ylim(max(0, min_val - margin), max_val + margin)
    
    # 箱の色を設定
    for patch, color in zip(bp['boxes'], box_plot_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # 中央値の線を太くする
    for median in bp['medians']:
        median.set(color='black', linewidth=2)
    
    # 平均値の点を追加
    for i, data in enumerate(box_plot_data):
        mean_val = np.mean(data)
        ax.plot(i + 1, mean_val, 'D', color='red', markersize=8, markeredgecolor='white', markeredgewidth=1)
    
    # グラフの設定
    ax.set_xlabel('プロトコル・遅延条件', fontsize=16, fontweight='bold')
    ax.set_ylabel('転送時間 (秒)', fontsize=16, fontweight='bold')
    ax.set_title('転送時間の分布（箱ひげ図）', fontsize=18, fontweight='bold', pad=20)
    # X軸ラベルを間引いて表示（10ms刻みで表示）
    step = 10  # 10ms刻みで表示
    tick_positions = []
    tick_labels = []
    for i in range(0, len(box_plot_labels), step):
        tick_positions.append(i + 1)
        tick_labels.append(box_plot_labels[i])
    
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=8, rotation=90)
    ax.grid(True, alpha=0.3, axis='y', linewidth=1)
    ax.tick_params(axis='y', labelsize=12)
    
    # 凡例を手動で作成
    legend_patches = [
        plt.Line2D([0], [0], marker='s', color='w', label='HTTP/2',
                   markerfacecolor=colors['HTTP/2'], markersize=12, alpha=0.7),
        plt.Line2D([0], [0], marker='s', color='w', label='HTTP/3',
                   markerfacecolor=colors['HTTP/3'], markersize=12, alpha=0.7),
        plt.Line2D([0], [0], marker='D', color='red', label='平均値',
                   markersize=8, markeredgecolor='white', markeredgewidth=1)
    ]
    ax.legend(handles=legend_patches, fontsize=14, loc='upper right', framealpha=0.9)
    
    # レイアウトを調整
    plt.tight_layout()
    
    # ファイルを保存
    output_file = os.path.join(output_dir, 'transfer_time_boxplot.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"転送時間箱ひげ図を保存しました: {output_file}")
    plt.close()
    
    # 統計サマリーを表示
    print("\n=== 転送時間箱ひげ図統計サマリー ===")
    for i, (label, data) in enumerate(zip(box_plot_labels, box_plot_data)):
        if len(data) > 0:
            q1 = np.percentile(data, 25)
            median = np.percentile(data, 50)
            q3 = np.percentile(data, 75)
            mean_val = np.mean(data)
            std_val = np.std(data)
            print(f"{label}: 平均={mean_val:.3f}s, 中央値={median:.3f}s, Q1={q1:.3f}s, Q3={q3:.3f}s, 標準偏差={std_val:.3f}s")

if __name__ == "__main__":
    csv_file_path = os.environ.get('BENCHMARK_CSV')
    output_directory = os.environ.get('BENCHMARK_OUTPUT_DIR')
    
    if not csv_file_path or not output_directory:
        print("エラー: BENCHMARK_CSV と BENCHMARK_OUTPUT_DIR 環境変数を設定してください")
        print("例: BENCHMARK_CSV='logs/latest/benchmark_results.csv' BENCHMARK_OUTPUT_DIR='logs/latest' python3 scripts/visualize_boxplot.py")
        exit(1)

    if not os.path.exists(csv_file_path):
        print(f"エラー: CSVファイルが見つかりません: {csv_file_path}")
        exit(1)
    
    visualize_boxplot(csv_file_path, output_directory)
