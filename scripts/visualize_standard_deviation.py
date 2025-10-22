#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
import matplotlib.font_manager as fm

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
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

def visualize_standard_deviation(csv_file, output_dir):
    """標準偏差と遅延の関係を可視化"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # 遅延条件のリスト（文字列形式）
    latencies = ['0ms', '50ms', '100ms', '150ms']
    lat_values = [0, 50, 100, 150]  # 数値での位置計算用
    
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
        
        # 各点に数値を表示
        for j, (lat, std_val) in enumerate(zip(lat_values, std_data[i])):
            ax.annotate(f'{std_val:.4f}秒',
                       xy=(lat, std_val),
                       xytext=(8, -15),
                       textcoords='offset points',
                       fontsize=11,
                       color=colors[protocol],
                       fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=colors[protocol], alpha=0.8))
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=16, fontweight='bold')
    ax.set_ylabel('標準偏差 (秒)', fontsize=16, fontweight='bold')
    ax.set_title('標準偏差と遅延の比較', fontsize=18, fontweight='bold', pad=20)
    ax.legend(fontsize=14, loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1)
    ax.set_xticks(lat_values)
    ax.set_xticklabels(latencies, fontsize=13)
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
    
    latest_dir = sorted(log_dirs)[-1]
    csv_file = os.path.join('logs', latest_dir, 'benchmark_results.csv')
    
    if not os.path.exists(csv_file):
        print(f"CSVファイルが見つかりません: {csv_file}")
        exit(1)
    
    output_dir = os.path.join('logs', latest_dir)
    visualize_standard_deviation(csv_file, output_dir)
