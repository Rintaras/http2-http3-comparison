#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

# 日本語フォント設定
plt.rcParams['font.family'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
plt.rcParams['axes.unicode_minus'] = False

def compare_percentile_ranges(csv_file1, csv_file2, output_dir):
    """2つのデータセットのP5-P95パーセンタイル範囲を比較"""
    
    # CSVファイルを読み込み
    df1 = pd.read_csv(csv_file1)
    df2 = pd.read_csv(csv_file2)
    
    # 遅延条件のリスト（文字列形式）
    latencies = ['0ms', '50ms', '100ms', '150ms']
    lat_values = [0, 50, 100, 150]  # 数値での位置計算用
    
    # プロトコル別の色設定
    colors = {'HTTP/2': '#1f77b4', 'HTTP/3': '#9467bd'}
    
    # データセット別の色設定
    dataset_colors = {'20251016_150731': '#2E8B57', '20251001_211526': '#FF6347'}  # 緑とオレンジ
    
    # グラフ作成
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 各データセットとプロトコルでP5-P95範囲を計算
    datasets = [
        (df1, '20251016_150731', 'Dataset 1 (2025/10/16)'),
        (df2, '20251001_211526', 'Dataset 2 (2025/10/01)')
    ]
    
    for df, dataset_name, dataset_label in datasets:
        for protocol in ['HTTP/2', 'HTTP/3']:
            p5_values = []
            p95_values = []
            ranges = []
            
            for lat in latencies:
                data = df[df['protocol'] == protocol]
                lat_data = data[data['latency'] == lat]['time_total'].values
                if len(lat_data) > 0:
                    p5 = np.percentile(lat_data, 5)
                    p95 = np.percentile(lat_data, 95)
                    range_val = p95 - p5
                    p5_values.append(p5)
                    p95_values.append(p95)
                    ranges.append(range_val)
                else:
                    p5_values.append(0)
                    p95_values.append(0)
                    ranges.append(0)
            
            # プロット（プロトコルとデータセットを組み合わせたラベル）
            label = f'{protocol} - {dataset_label}'
            line_style = '-' if dataset_name == '20251016_150731' else '--'
            marker_style = 'o' if dataset_name == '20251016_150731' else 's'
            
            ax.plot(lat_values, ranges, 
                   marker=marker_style, linewidth=3, markersize=8,
                   label=label, color=colors[protocol], 
                   linestyle=line_style, alpha=0.8)
            
            # 各点に数値を表示
            for i, (lat, range_val) in enumerate(zip(lat_values, ranges)):
                if range_val > 0:  # データがある場合のみ表示
                    ax.annotate(f'{range_val:.3f}',
                               xy=(lat, range_val),
                               xytext=(5, 5),
                               textcoords='offset points',
                               fontsize=9,
                               color=colors[protocol],
                               fontweight='bold')
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
    ax.set_ylabel('P5-P95範囲 (秒)', fontsize=14, fontweight='bold')
    ax.set_title('P5-P95パーセンタイル範囲の比較\n2つのデータセット間での安定性比較', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='best', ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(lat_values)
    ax.set_xticklabels(latencies)
    
    # Y軸の範囲を調整（0から開始）
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'percentile_range_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"P5-P95パーセンタイル範囲比較グラフを保存しました: {output_file}")
    plt.close()
    
    # 統計サマリー
    print("\n=== P5-P95パーセンタイル範囲統計サマリー ===")
    for df, dataset_name, dataset_label in datasets:
        print(f"\n{dataset_label}:")
        for protocol in ['HTTP/2', 'HTTP/3']:
            print(f"  {protocol}:")
            for lat in latencies:
                data = df[df['protocol'] == protocol]
                lat_data = data[data['latency'] == lat]['time_total'].values
                if len(lat_data) > 0:
                    p5 = np.percentile(lat_data, 5)
                    p95 = np.percentile(lat_data, 95)
                    range_val = p95 - p5
                    print(f"    {lat}: P5={p5:.4f}s, P95={p95:.4f}s, 範囲={range_val:.4f}s")

if __name__ == "__main__":
    # 指定されたCSVファイル
    csv_file1 = 'logs/20251016_150731/benchmark_results.csv'
    csv_file2 = 'logs/20251001_211526/benchmark_results.csv'
    output_dir = 'logs'
    
    if not os.path.exists(csv_file1):
        print(f"CSVファイルが見つかりません: {csv_file1}")
        exit(1)
    
    if not os.path.exists(csv_file2):
        print(f"CSVファイルが見つかりません: {csv_file2}")
        exit(1)
    
    compare_percentile_ranges(csv_file1, csv_file2, output_dir)
