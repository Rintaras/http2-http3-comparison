#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
import matplotlib.font_manager as fm
import os

sns.set_style("whitegrid")

plt.rcParams['font.family'] = 'sans-serif'
if os.environ.get('FAST_PLOT') == '1':
    plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'DejaVu Sans']
else:
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

def visualize_standard_deviation(csv_file, output_dir):
    """標準偏差と遅延の関係を可視化"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # 遅延条件を動的に取得（数値でソート）
    latencies_str = df['latency'].unique()
    lat_values = [int(lat.replace('ms', '')) for lat in latencies_str]
    
    # 数値でソートしてインデックスを取得
    sorted_indices = sorted(range(len(lat_values)), key=lambda i: lat_values[i])
    latencies = [latencies_str[i] for i in sorted_indices]
    lat_values = [lat_values[i] for i in sorted_indices]
    
    # プロトコル別の色設定（response_time_comparisonと同じ色）
    colors = {'HTTP/2': '#2E86AB', 'HTTP/3': '#A23B72'}
    
    # 各遅延条件での標準偏差を計算
    std_data = []
    
    for protocol in ['HTTP/2', 'HTTP/3']:
        protocol_std = []
        for lat in latencies:
            data = df[df['protocol'] == protocol]
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                std_value = lat_data.std()
                protocol_std.append(std_value)
            else:
                protocol_std.append(0)
        std_data.append(protocol_std)
    
    # グラフ作成
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # プロトコル別にプロット
    for i, protocol in enumerate(['HTTP/2', 'HTTP/3']):
        ax.plot(lat_values, std_data[i], 
                marker='o', linewidth=3.5, markersize=12,
                label=protocol, color=colors[protocol], zorder=3)

        # 主要な遅延ポイントに値を注記（0/2/50/100/150ms が存在する場合のみ）
        target_ms = {0, 2, 50, 100, 150}
        lat_to_std = {lv: sv for lv, sv in zip(lat_values, std_data[i])}
        protocol_name = ['HTTP/2', 'HTTP/3'][i]
        for t in sorted(target_ms):
            if t in lat_to_std and lat_to_std[t] is not None:
                val = float(lat_to_std[t])
                # 数値をより見やすく表示（プロトコルごとに垂直・水平方向にずらして重なりを防ぐ）
                if protocol_name == 'HTTP/2':
                    offset_x = -8  # 左にずらす
                    offset_y = 20  # 上に配置
                else:  # HTTP/3
                    offset_x = 8   # 右にずらす
                    offset_y = 30  # より上に配置
                ax.annotate(f"{val:.3f}s",
                            xy=(t, val),
                            xytext=(offset_x, offset_y),
                            textcoords='offset points',
                            fontsize=11,
                            fontweight='bold',
                            color=colors[protocol],
                            ha='center',
                            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor=colors[protocol], linewidth=1.5, alpha=0.9))

    # Y軸の範囲を動的に調整
    all_stds = []
    for data in std_data:
        all_stds.extend(data)

    if all_stds:
        min_val = min(all_stds)
        max_val = max(all_stds)
        margin = (max_val - min_val) * 0.1
        ax.set_ylim(max(0, min_val - margin), max_val + margin)
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=16, fontweight='bold')
    ax.set_ylabel('標準偏差 (秒)', fontsize=16, fontweight='bold')
    ax.set_title('標準偏差と遅延の比較', fontsize=18, fontweight='bold', pad=20)
    ax.legend(fontsize=14, loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1)
    # X軸に実施したベンチマーク（0/2/50/100/150ms）を明示的に表示
    benchmark_ms = {0, 2, 50, 100, 150}
    tick_positions = []
    tick_labels = []
    
    # 実施したベンチマークの遅延値を優先的に表示
    for lat_val, lat_str in zip(lat_values, latencies):
        if lat_val in benchmark_ms:
            tick_positions.append(lat_val)
            tick_labels.append(f'{lat_val}ms')
        elif len(tick_positions) == 0 or lat_val - tick_positions[-1] >= 10:
            # ベンチマーク以外は10ms刻みで間引く
            tick_positions.append(lat_val)
            tick_labels.append(lat_str)
    
    ax.set_xticks(tick_positions)
    # X軸ラベルを回転させて重なりを防ぐ
    ax.set_xticklabels(tick_labels, fontsize=11, fontweight='bold', rotation=45, ha='right')
    ax.tick_params(axis='y', labelsize=12)
    
    # Y軸の範囲を調整（0から開始）
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'standard_deviation_vs_latency.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"標準偏差と遅延のグラフを保存しました: {output_file}")
    plt.close()
    
    # 統計サマリー
    print("\n=== 標準偏差統計サマリー ===")
    for i, protocol in enumerate(['HTTP/2', 'HTTP/3']):
        print(f"\n{protocol}:")
        for j, lat in enumerate(latencies):
            std_val = std_data[i][j]
            print(f"  {lat}: 標準偏差={std_val:.4f}秒")

if __name__ == "__main__":
    # 最新のログディレクトリを取得
    log_dirs = [d for d in os.listdir('logs') if os.path.isdir(os.path.join('logs', d)) and d.startswith('2025')]
    if not log_dirs:
        print("ログディレクトリが見つかりません")
        exit(1)
    
    csv_file = os.environ.get('BENCHMARK_CSV')
    output_dir = os.environ.get('BENCHMARK_OUTPUT_DIR')
    
    if not csv_file or not output_dir:
        print("エラー: BENCHMARK_CSV と BENCHMARK_OUTPUT_DIR 環境変数を設定してください")
        print("例: BENCHMARK_CSV='logs/latest/benchmark_results.csv' BENCHMARK_OUTPUT_DIR='logs/latest' python3 scripts/visualize_standard_deviation.py")
        exit(1)
    
    if not os.path.exists(csv_file):
        print(f"CSVファイルが見つかりません: {csv_file}")
        exit(1)
    
    visualize_standard_deviation(csv_file, output_dir)
