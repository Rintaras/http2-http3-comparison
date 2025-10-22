#!/usr/bin/env python3
"""
転送時間と遅延で箱ひげ図を可視化するスクリプト
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

def visualize_boxplot(csv_file, output_dir):
    """転送時間と遅延で箱ひげ図を可視化"""
    
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
    box_plot_data = []
    box_plot_labels = []
    box_plot_colors = []
    
    for protocol in ['HTTP/2', 'HTTP/3']:
        data = df[df['protocol'] == protocol]
        for lat in latencies:
            lat_data = data[data['latency'] == lat]['time_total'].values
            if len(lat_data) > 0:
                box_plot_data.append(lat_data)
                box_plot_labels.append(f'{protocol}\n{lat}')
                box_plot_colors.append(colors[protocol])
    
    # グラフを作成
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 箱ひげ図を描画
    bp = ax.boxplot(box_plot_data, patch_artist=True, showfliers=False, widths=0.6)
    
    # 箱の色を設定
    for patch, color in zip(bp['boxes'], box_plot_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # 中央値の線を太くする
    for median in bp['medians']:
        median.set(color='black', linewidth=2)
    
    # 平均値の点を追加
    for i, data in enumerate(box_plot_data):
        mean_val = np.mean(data)
        ax.plot(i + 1, mean_val, 'D', color='red', markersize=8, markeredgecolor='white', markeredgewidth=1)
    
    # グラフの設定
    ax.set_xlabel('プロトコル・遅延条件', fontsize=14, fontweight='bold')
    ax.set_ylabel('転送時間 (秒)', fontsize=14, fontweight='bold')
    ax.set_title('転送時間の分布（箱ひげ図）\n各遅延条件でのプロトコル比較', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(range(1, len(box_plot_labels) + 1))
    ax.set_xticklabels(box_plot_labels, fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 凡例を手動で作成
    legend_patches = [
        plt.Line2D([0], [0], marker='s', color='w', label='HTTP/2',
                   markerfacecolor=colors['HTTP/2'], markersize=12, alpha=0.7),
        plt.Line2D([0], [0], marker='s', color='w', label='HTTP/3',
                   markerfacecolor=colors['HTTP/3'], markersize=12, alpha=0.7),
        plt.Line2D([0], [0], marker='D', color='red', label='平均値',
                   markersize=8, markeredgecolor='white', markeredgewidth=1)
    ]
    ax.legend(handles=legend_patches, fontsize=12, loc='upper right')
    
    # レイアウトを調整
    plt.tight_layout()
    
    # ファイルを保存
    output_file = os.path.join(output_dir, 'transfer_time_boxplot.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"転送時間箱ひげ図を保存しました: {output_file}")
    plt.close()
    
    # 統計サマリーを表示
    print("\n=== 転送時間箱ひげ図統計サマリー ===")
    for i, (label, data) in enumerate(zip(box_plot_labels, box_plot_data)):
        if len(data) > 0:
            q1 = np.percentile(data, 25)
            median = np.percentile(data, 50)
            q3 = np.percentile(data, 75)
            mean_val = np.mean(data)
            std_val = np.std(data)
            print(f"{label}: 平均={mean_val:.3f}s, 中央値={median:.3f}s, Q1={q1:.3f}s, Q3={q3:.3f}s, 標準偏差={std_val:.3f}s")

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
    
    visualize_boxplot(csv_file_path, output_directory)
