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

def visualize_stability_percentile(csv_file, output_dir):
    """P5-P95パーセンタイル範囲の安定性を可視化"""
    
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

    # P5-P95範囲を計算
    percentile_ranges = []
    
    for protocol in ['HTTP/2', 'HTTP/3']:
        protocol_ranges = []
        for lat in latencies:
            data = df[df['protocol'] == protocol]
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                p5 = np.percentile(lat_data, 5)
                p95 = np.percentile(lat_data, 95)
                range_val = p95 - p5
                protocol_ranges.append(range_val)
            else:
                protocol_ranges.append(0)
        percentile_ranges.append(protocol_ranges)
    
    # グラフ作成
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # プロトコル別にプロット
    for i, protocol in enumerate(['HTTP/2', 'HTTP/3']):
        ax.plot(lat_values, percentile_ranges[i], 
                marker='o', linewidth=3, markersize=10,
                label=f'{protocol} (P5-P95範囲)', color=colors[protocol])
        
        # 各点に数値を表示
        for j, (lat, range_val) in enumerate(zip(lat_values, percentile_ranges[i])):
            ax.annotate(f'{range_val:.4f}',
                       xy=(lat, range_val),
                       xytext=(5, 5),
                       textcoords='offset points',
                       fontsize=10,
                       color=colors[protocol],
                       fontweight='bold')
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
    ax.set_ylabel('P5-P95範囲 (秒)', fontsize=14, fontweight='bold')
    ax.set_title('パーセンタイル範囲のみの比較（P5-P95）\n低い値ほど安定', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=13, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(lat_values)
    ax.set_xticklabels(latencies)
    
    # Y軸の範囲を調整（0から開始）
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'stability_percentile_range_20251016_153121.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"P5-P95パーセンタイル範囲グラフを保存しました: {output_file}")
    plt.close()
    
    # 統計サマリー
    print("\n=== P5-P95パーセンタイル範囲統計サマリー（20251016_153121データ） ===")
    for i, protocol in enumerate(['HTTP/2', 'HTTP/3']):
        print(f"\n{protocol}:")
        for j, lat in enumerate(latencies):
            range_val = percentile_ranges[i][j]
            print(f"  {lat}: P5-P95範囲={range_val:.4f}秒")

if __name__ == "__main__":
    # 指定されたCSVファイル
    csv_file = 'logs/20251016_153121/benchmark_results.csv'
    output_dir = 'logs/20251016_153121'
    
    if not os.path.exists(csv_file):
        print(f"CSVファイルが見つかりません: {csv_file}")
        exit(1)
    
    visualize_stability_percentile(csv_file, output_dir)
