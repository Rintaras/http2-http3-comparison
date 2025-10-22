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

def visualize_raw_data(csv_file, output_dir):
    """生のデータ分布を可視化"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # 遅延条件のリスト（文字列形式）
    latencies = ['0ms', '50ms', '100ms', '150ms']
    lat_values = [0, 50, 100, 150]  # 数値での位置計算用
    
    # プロトコル別の色設定
    colors = {'HTTP/2': '#1f77b4', 'HTTP/3': '#9467bd'}
    
    # 1. 箱ひげ図での分布比較
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    # 左側: 箱ひげ図
    for i, protocol in enumerate(['HTTP/2', 'HTTP/3']):
        data = df[df['protocol'] == protocol]
        protocol_data = []
        labels = []
        
        for lat in latencies:
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                protocol_data.append(lat_data)
                labels.append(f'{lat}ms')
        
        if protocol_data:
            bp = ax1.boxplot(protocol_data, positions=[j + i*0.4 for j in range(len(protocol_data))], 
                           widths=0.35, patch_artist=True, 
                           boxprops=dict(facecolor=colors[protocol], alpha=0.7),
                           medianprops=dict(color='red', linewidth=2))
    
    ax1.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('応答時間 (秒)', fontsize=14, fontweight='bold')
    ax1.set_title('生データ分布比較（箱ひげ図）\n全データポイントの分布', fontsize=16, fontweight='bold', pad=20)
    ax1.set_xticks([i + 0.2 for i in range(len(latencies))])
    ax1.set_xticklabels([f'{lat}ms' for lat in latencies])
    ax1.grid(True, alpha=0.3)
    ax1.legend(['HTTP/2', 'HTTP/3'], fontsize=12)
    
    # 右側: 散布図
    for protocol in ['HTTP/2', 'HTTP/3']:
        data = df[df['protocol'] == protocol]
        for i, lat in enumerate(latencies):
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                x_pos = lat_values[i] + (0.1 if protocol == 'HTTP/2' else -0.1)
                ax2.scatter([x_pos] * len(lat_data), lat_data, 
                           c=colors[protocol], alpha=0.6, s=30, label=protocol if lat == latencies[0] else "")
    
    ax2.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
    ax2.set_ylabel('応答時間 (秒)', fontsize=14, fontweight='bold')
    ax2.set_title('生データ分布比較（散布図）\n全データポイントの位置', fontsize=16, fontweight='bold', pad=20)
    ax2.set_xticks(lat_values)
    ax2.set_xticklabels(latencies)
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=12)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'raw_data_distribution.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"生データ分布グラフを保存しました: {output_file}")
    plt.close()
    
    # 2. ヒストグラムでの分布比較
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    axes = axes.flatten()
    
    for i, lat in enumerate(latencies):
        ax = axes[i]
        
        for protocol in ['HTTP/2', 'HTTP/3']:
            data = df[df['protocol'] == protocol]
            lat_data = data[data['latency'] == lat]['time_total'].values
            
            if len(lat_data) > 0:
                ax.hist(lat_data, bins=20, alpha=0.7, color=colors[protocol], 
                       label=f'{protocol} (n={len(lat_data)})', density=True)
        
        ax.set_xlabel('応答時間 (秒)', fontsize=12, fontweight='bold')
        ax.set_ylabel('密度', fontsize=12, fontweight='bold')
        ax.set_title(f'遅延 {lat}ms での分布', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'raw_data_histograms.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"生データヒストグラムを保存しました: {output_file}")
    plt.close()
    
    # 3. 統計サマリー
    print("\n=== 生データ統計サマリー ===")
    for protocol in ['HTTP/2', 'HTTP/3']:
        print(f"\n{protocol}:")
        data = df[df['protocol'] == protocol]
        for lat in latencies:
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                print(f"  {lat}: 平均={lat_data.mean():.3f}s, 最小={lat_data.min():.3f}s, 最大={lat_data.max():.3f}s, 標準偏差={lat_data.std():.3f}s")

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
    visualize_raw_data(csv_file, output_dir)
