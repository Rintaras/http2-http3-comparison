#!/usr/bin/env python3
"""
P5-P95パーセンタイル範囲を可視化するスクリプト
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import matplotlib.font_manager as fm

def get_japanese_font_family():
    """日本語フォントを自動検出"""
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

def visualize_percentile_range(csv_file, output_dir):
    """P5-P95パーセンタイル範囲を可視化"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # 遅延条件のリスト
    latencies = ['2ms', '50ms', '100ms', '150ms']
    
    # 日本語フォント設定
    plt.rcParams['font.family'] = get_japanese_font_family()
    plt.rcParams['axes.unicode_minus'] = False
    
    # プロトコル別の色設定
    colors = {'HTTP/2': '#1f77b4', 'HTTP/3': '#9467bd'}
    
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
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # 折れ線グラフを描画
    for protocol, color in colors.items():
        data = percentile_data[protocol]
        ax.plot(latencies, data, marker='o', linewidth=3, markersize=10,
                label=protocol, color=color)
        
        # 各点の上に値を表示
        for lat, value in zip(latencies, data):
            if value > 0:
                ax.annotate(f'{value:.3f}', xy=(lat, value), xytext=(5, 5),
                           textcoords='offset points', fontsize=10, color=color, fontweight='bold')
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
    ax.set_ylabel('P5-P95範囲 (秒)', fontsize=14, fontweight='bold')
    ax.set_title('P5-P95パーセンタイル範囲の比較', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=13, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(latencies)
    ax.set_xticklabels([f'{lat}' for lat in latencies])
    
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
    # 最新のログディレクトリを取得
    log_dirs = [d for d in os.listdir('logs') if os.path.isdir(os.path.join('logs', d)) and d.startswith('2025')]
    if not log_dirs:
        print("エラー: ログディレクトリが見つかりません。")
        exit(1)
    
    latest_log_dir = sorted(log_dirs, reverse=True)[0]
    csv_file_path = os.path.join('logs', latest_log_dir, 'benchmark_results.csv')
    output_directory = os.path.join('logs', latest_log_dir)

    if not os.path.exists(csv_file_path):
        print(f"エラー: CSVファイルが見つかりません: {csv_file_path}")
        exit(1)
    
    visualize_percentile_range(csv_file_path, output_directory)
