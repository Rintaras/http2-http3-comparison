#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
import matplotlib.font_manager as fm

def get_japanese_font_family():
    # macOS
    if os.uname().sysname == "Darwin":
        if os.path.exists("/System/Library/Fonts/Hiragino Sans GB.ttc"):
            return "Hiragino Sans GB"
        elif os.path.exists("/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"):
            return "Hiragino Sans"
        elif os.path.exists("/Library/Fonts/ヒラギノ角ゴシック W4.ttc"):
            return "Hiragino Sans"
    # Linux (Ubuntu/Debian)
    elif os.path.exists("/usr/share/fonts/opentype/ipafont-gothic/ipaexg.ttf"):
        return "IPAexGothic"
    elif os.path.exists("/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf"):
        return "TakaoPGothic"
    # Windows
    elif os.name == 'nt':
        if os.path.exists("C:/Windows/Fonts/meiryo.ttc"):
            return "Meiryo"
        elif os.path.exists("C:/Windows/Fonts/YuGothM.ttc"):
            return "Yu Gothic"
    return "sans-serif" # Fallback

def visualize_raw_data(csv_file, output_dir):
    """生のデータ分布を可視化（P5-P95分析なし）"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # 遅延条件のリスト（文字列形式）
    latencies = ['0ms', '50ms', '100ms', '150ms']
    lat_values = [0, 50, 100, 150]  # 数値での位置計算用
    
    # プロトコル別の色設定
    colors = {'HTTP/2': '#1f77b4', 'HTTP/3': '#9467bd'}
    
    # 日本語フォント設定
    plt.rcParams['font.family'] = get_japanese_font_family()
    plt.rcParams['axes.unicode_minus'] = False # マイナス記号の文字化けを防ぐ

    # 1. 箱ひげ図での分布比較
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    # 左側: 箱ひげ図
    box_plot_data = []
    box_plot_labels = []
    box_plot_colors = []

    for i, protocol in enumerate(['HTTP/2', 'HTTP/3']):
        data = df[df['protocol'] == protocol]
        for lat in latencies:
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                box_plot_data.append(lat_data)
                box_plot_labels.append(f'{protocol} {lat}')
                box_plot_colors.append(colors[protocol])

    # 箱ひげ図の描画
    bp = ax1.boxplot(box_plot_data, patch_artist=True, showfliers=False, widths=0.6) # 外れ値は表示しない
    for patch, color in zip(bp['boxes'], box_plot_colors):
        patch.set_facecolor(color)
    for median in bp['medians']:
        median.set(color='black', linewidth=2)
    
    ax1.set_xlabel('条件', fontsize=14, fontweight='bold')
    ax1.set_ylabel('応答時間 (秒)', fontsize=14, fontweight='bold')
    ax1.set_title('生データ分布比較（箱ひげ図）\n中央値と四分位範囲', fontsize=16, fontweight='bold', pad=20)
    ax1.set_xticks(range(1, len(box_plot_labels) + 1))
    ax1.set_xticklabels(box_plot_labels, rotation=45, ha='right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 凡例を手動で作成
    legend_patches = [plt.Line2D([0], [0], marker='o', color='w', label='HTTP/2',
                                 markerfacecolor=colors['HTTP/2'], markersize=10),
                      plt.Line2D([0], [0], marker='o', color='w', label='HTTP/3',
                                 markerfacecolor=colors['HTTP/3'], markersize=10)]
    ax1.legend(handles=legend_patches, fontsize=12)

    # 右側: 散布図
    for protocol in ['HTTP/2', 'HTTP/3']:
        data = df[df['protocol'] == protocol]
        for i, lat in enumerate(latencies):
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                # プロトコルごとにX軸をわずかにずらす
                x_offset = -0.15 if protocol == 'HTTP/2' else 0.15
                x_positions = np.array([lat_values[i]] * len(lat_data)) + x_offset
                ax2.scatter(x_positions, lat_data, 
                           c=colors[protocol], alpha=0.6, s=30, 
                           label=protocol if lat == latencies[0] else "") # 凡例は一度だけ表示

    ax2.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
    ax2.set_ylabel('応答時間 (秒)', fontsize=14, fontweight='bold')
    ax2.set_title('生データ分布比較（散布図）\n全データポイントの位置', fontsize=16, fontweight='bold', pad=20)
    ax2.set_xticks(lat_values)
    ax2.set_xticklabels([f'{lat}ms' for lat in latencies])
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=12)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'raw_data_distribution_20251016_153121.png')
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
        
        ax.set_title(f'遅延 {lat}ms での応答時間分布', fontsize=14, fontweight='bold')
        ax.set_xlabel('応答時間 (秒)', fontsize=12)
        ax.set_ylabel('密度', fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'raw_data_histograms_20251016_153121.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"生データヒストグラムを保存しました: {output_file}")
    plt.close()
    
    # 3. 統計サマリー
    print("\n=== 生データ統計サマリー（20251016_153121データ） ===")
    for protocol in ['HTTP/2', 'HTTP/3']:
        print(f"\n{protocol}:")
        data = df[df['protocol'] == protocol]
        for lat in latencies:
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                print(f"  {lat}: 平均={lat_data.mean():.3f}s, 最小={lat_data.min():.3f}s, 最大={lat_data.max():.3f}s, 標準偏差={lat_data.std():.3f}s")

if __name__ == "__main__":
    # 指定されたCSVファイル
    csv_file = 'logs/20251016_153121/benchmark_results.csv'
    output_dir = 'logs/20251016_153121'
    
    if not os.path.exists(csv_file):
        print(f"CSVファイルが見つかりません: {csv_file}")
        exit(1)
    
    visualize_raw_data(csv_file, output_dir)
