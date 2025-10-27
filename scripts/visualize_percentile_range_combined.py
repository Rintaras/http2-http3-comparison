#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2つのベンチマーク結果のP5-P95パーセンタイル範囲を統合したグラフを作成
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

def calculate_percentile_range(df):
    """P5-P95パーセンタイル範囲を計算"""
    percentile_data = {}
    for protocol in df['protocol'].unique():
        for latency_ms in df['latency_ms'].unique():
            data = df[(df['protocol'] == protocol) & (df['latency_ms'] == latency_ms) & (df['success'] == 1)]['time_total']
            if len(data) > 0:
                p5 = np.percentile(data, 5)
                p95 = np.percentile(data, 95)
                percentile_range = p95 - p5
                key = (protocol, latency_ms)
                percentile_data[key] = percentile_range
    return percentile_data

def create_combined_percentile_visualization(csv_file1, csv_file2, output_dir):
    """2つのベンチマーク結果のP5-P95パーセンタイル範囲を統合したグラフを作成"""
    print(f"Creating combined percentile range graph...")
    print(f"File 1: {csv_file1}")
    print(f"File 2: {csv_file2}")
    
    # データ読み込み
    df1 = load_and_prepare_data(csv_file1, '実機環境 (10/1)')
    df2 = load_and_prepare_data(csv_file2, '仮想環境 (10/19)')
    
    # 統合
    df = pd.concat([df1, df2], ignore_index=True)
    
    # プロトコルとソースの組み合わせ
    protocols = ['HTTP/2', 'HTTP/3']
    sources = ['実機環境 (10/1)', '仮想環境 (10/19)']
    
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
        for source in sources:
            data = df[(df['protocol'] == protocol) & (df['source'] == source) & (df['success'] == 1)]
            
            if not data.empty:
                # 各遅延条件でP5-P95範囲を計算
                latencies = sorted(data['latency_ms'].unique())
                percentile_ranges = []
                
                for latency_ms in latencies:
                    lat_data = data[data['latency_ms'] == latency_ms]['time_total'].values
                    if len(lat_data) > 0:
                        p5 = np.percentile(lat_data, 5)
                        p95 = np.percentile(lat_data, 95)
                        percentile_range = p95 - p5
                        percentile_ranges.append(percentile_range)
                    else:
                        percentile_ranges.append(0)
                
                label = f"{protocol} - {source}"
                color = colors.get((protocol, source), '#95a5a6')
                
                ax.plot(latencies, percentile_ranges,
                       color=color,
                       linestyle=linestyles[source],
                       marker=markers[source],
                       linewidth=3.5,
                       markersize=12,
                       label=label,
                       zorder=3)
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=16, fontweight='bold')
    ax.set_ylabel('P5-P95パーセンタイル範囲 (秒)', fontsize=16, fontweight='bold')
    ax.set_title('P5-P95パーセンタイル範囲の比較 (実機環境 vs 仮想環境)', fontsize=18, fontweight='bold', pad=20)
    ax.legend(fontsize=12, loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1)
    
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
    
    ax.tick_params(axis='y', labelsize=12)
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'stability_percentile_range_combined.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Graph saved: {output_file}")
    
    plt.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 visualize_percentile_range_combined.py <csv1> <csv2> [output_dir]")
        sys.exit(1)
    
    csv_file1 = sys.argv[1]
    csv_file2 = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.dirname(csv_file1)
    
    create_combined_percentile_visualization(csv_file1, csv_file2, output_dir)
