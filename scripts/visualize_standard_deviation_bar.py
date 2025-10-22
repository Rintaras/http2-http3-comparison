#!/usr/bin/env python3
"""
標準偏差を縦列（棒グラフ）で可視化するスクリプト
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

def visualize_standard_deviation_bar(csv_file, output_dir):
    """標準偏差を縦列（棒グラフ）で可視化"""
    
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
    x_pos = np.arange(len(latencies))
    width = 0.35  # 棒の幅
    
    # 標準偏差を計算
    std_data = {}
    for protocol in protocols:
        std_data[protocol] = []
        for lat in latencies:
            data = df[(df['protocol'] == protocol) & (df['latency'] == lat)]['time_total']
            if not data.empty:
                std_val = data.std()
                std_data[protocol].append(std_val)
            else:
                std_data[protocol].append(0)
    
    # グラフを作成
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 棒グラフを描画
    bars1 = ax.bar(x_pos - width/2, std_data['HTTP/2'], width, 
                   label='HTTP/2', color=colors['HTTP/2'], alpha=0.8)
    bars2 = ax.bar(x_pos + width/2, std_data['HTTP/3'], width, 
                   label='HTTP/3', color=colors['HTTP/3'], alpha=0.8)
    
    # 各棒の上に値を表示
    for i, (lat, h2_std, h3_std) in enumerate(zip(latencies, std_data['HTTP/2'], std_data['HTTP/3'])):
        # HTTP/2の値
        if h2_std > 0:
            ax.text(i - width/2, h2_std + 0.0001, f'{h2_std:.4f}', 
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # HTTP/3の値
        if h3_std > 0:
            ax.text(i + width/2, h3_std + 0.0001, f'{h3_std:.4f}', 
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # グラフの設定
    ax.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
    ax.set_ylabel('標準偏差 (秒)', fontsize=14, fontweight='bold')
    ax.set_title('標準偏差の比較（縦列表示）\n低い値ほど安定', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(latencies)
    ax.legend(fontsize=13, loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Y軸の範囲を調整（最大値の1.2倍）
    max_std = max(max(std_data['HTTP/2']), max(std_data['HTTP/3']))
    ax.set_ylim(0, max_std * 1.2)
    
    # レイアウトを調整
    plt.tight_layout()
    
    # ファイルを保存
    output_file = os.path.join(output_dir, 'stability_standard_deviation_bar.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"標準偏差縦列グラフを保存しました: {output_file}")
    plt.close()
    
    # 統計サマリーを表示
    print("\n=== 標準偏差統計サマリー（縦列表示用） ===")
    for i, lat in enumerate(latencies):
        h2_std = std_data['HTTP/2'][i]
        h3_std = std_data['HTTP/3'][i]
        ratio = h2_std / h3_std if h3_std > 0 else float('inf')
        winner = "HTTP/2" if h2_std < h3_std else "HTTP/3" if h3_std < h2_std else "同等"
        print(f"{lat}: HTTP/2={h2_std:.4f}s, HTTP/3={h3_std:.4f}s, 比={ratio:.2f}倍, 勝者: {winner}")

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
    
    visualize_standard_deviation_bar(csv_file_path, output_directory)
