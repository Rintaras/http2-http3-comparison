#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2つのベンチマーク結果を統合して1つのグラフにプロットするスクリプト
実機環境 (20251001) vs 仮想環境 (20251019) の比較
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

# 日本語フォント設定
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

def load_and_prepare_data(csv_file, source_label):
    """CSVファイルを読み込んで遅延条件を数値に変換"""
    df = pd.read_csv(csv_file)
    
    # http_versionカラムがない場合の対応
    if 'http_version' not in df.columns:
        df['http_version'] = 'unknown'
    
    # latency列を数値に変換
    df['latency_ms'] = df['latency'].str.replace('ms', '').astype(int)
    
    # ソース情報を追加
    df['source'] = source_label
    
    return df

def create_combined_visualization(csv_file1, csv_file2, output_dir):
    """2つのベンチマーク結果を統合したグラフを作成"""
    print(f"Creating combined graph...")
    print(f"File 1: {csv_file1}")
    print(f"File 2: {csv_file2}")
    
    # データ読み込み
    df1 = load_and_prepare_data(csv_file1, '実機環境 (10/1)')
    df2 = load_and_prepare_data(csv_file2, '仮想環境 (10/19)')
    
    # 統合
    df = pd.concat([df1, df2], ignore_index=True)
    
    # 成功したデータのみ使用
    df = df[df['success'] == 1]
    
    # プロトコルごとの遅延条件別平均を計算
    protocols = ['HTTP/2', 'HTTP/3']
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors = {
        ('HTTP/2', '実機環境 (10/1)'): '#2E86AB',
        ('HTTP/3', '実機環境 (10/1)'): '#A23B72',
        ('HTTP/2', '仮想環境 (10/19)'): '#1f5f8b',
        ('HTTP/3', '仮想環境 (10/19)'): '#7a2a56'
    }
    
    linestyles = {
        '実機環境 (10/1)': '-',
        '仮想環境 (10/19)': '--'
    }
    
    markers = {
        '実機環境 (10/1)': 'o',
        '仮想環境 (10/19)': 's'
    }
    
    # 各プロトコル×ソースの組み合わせでプロット
    for protocol in protocols:
        for source in df['source'].unique():
            condition = (df['protocol'] == protocol) & (df['source'] == source)
            data = df[condition].groupby('latency_ms')['time_total'].agg(['mean', 'std']).reset_index()
            
            if not data.empty:
                label = f"{protocol} - {source}"
                color = colors.get((protocol, source), '#95a5a6')
                
                ax.plot(data['latency_ms'], data['mean'], 
                       color=color, 
                       linestyle=linestyles[source],
                       marker=markers[source],
                       linewidth=3.5, 
                       markersize=12,
                       label=label,
                       zorder=3)
                
                # 標準偏差の範囲を表示（薄い色）
                std_data = data['std'].fillna(0)
                ax.fill_between(data['latency_ms'], 
                               data['mean'] - std_data, 
                               data['mean'] + std_data, 
                               color=color, 
                               alpha=0.2,
                               zorder=1)
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=16, fontweight='bold')
    ax.set_ylabel('平均応答時間 (秒)', fontsize=16, fontweight='bold')
    ax.set_title('HTTP/2 vs HTTP/3 応答速度の比較 (実機環境 vs 仮想環境)', fontsize=18, fontweight='bold', pad=20)
    ax.legend(fontsize=12, loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1)
    
    # Y軸の範囲を調整
    all_means = []
    for protocol in protocols:
        for source in df['source'].unique():
            condition = (df['protocol'] == protocol) & (df['source'] == source)
            data = df[condition].groupby('latency_ms')['time_total'].mean()
            all_means.extend(data.values)
    
    if all_means:
        min_val = min(all_means)
        max_val = max(all_means)
        margin = (max_val - min_val) * 0.15
        ax.set_ylim(max(0, min_val - margin), max_val + margin)
    
    ax.tick_params(axis='y', labelsize=12)
    
    # X軸ラベルの調整
    all_latencies = sorted(df['latency_ms'].unique())
    if len(all_latencies) > 20:
        step = max(1, len(all_latencies) // 20)
        tick_positions = []
        tick_labels = []
        for i in range(0, len(all_latencies), step):
            tick_positions.append(all_latencies[i])
            tick_labels.append(f"{all_latencies[i]}ms")
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, fontsize=10)
    else:
        ax.set_xticks(all_latencies)
        ax.set_xticklabels([f"{lat}ms" for lat in all_latencies], fontsize=10)
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'response_time_comparison_combined.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Graph saved: {output_file}")
    
    plt.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 visualize_comparison_combined.py <csv1> <csv2> [output_dir]")
        sys.exit(1)
    
    csv_file1 = sys.argv[1]
    csv_file2 = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.dirname(csv_file1)
    
    create_combined_visualization(csv_file1, csv_file2, output_dir)
