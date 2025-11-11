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
from pathlib import Path
from itertools import cycle
import seaborn as sns

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

def create_combined_visualization(dataset_infos, output_dir, y_min=None, y_max=None, exclude_range=None):
    """複数のベンチマーク結果を統合したグラフを作成"""
    print("Creating combined graph...")
    for csv_file, label in dataset_infos:
        print(f"  - {label}: {csv_file}")
    
    # データ読み込み
    frames = []
    for csv_file, label in dataset_infos:
        frames.append(load_and_prepare_data(csv_file, label))
    
    # 統合
    df = pd.concat(frames, ignore_index=True)
    
    # 成功したデータのみ使用
    df = df[df['success'] == 1]
    
    # 指定された時間範囲を除外
    if exclude_range is not None:
        ex_min, ex_max = exclude_range
        if ex_min >= ex_max:
            raise ValueError("除外範囲の最小値は最大値より小さく設定してください")
        df = df[(df['time_total'] <= ex_min) | (df['time_total'] >= ex_max)]
    
    # プロトコルごとの遅延条件別平均を計算
    protocols = ['HTTP/2', 'HTTP/3']
    fig, ax = plt.subplots(figsize=(12, 8))
    
    sources = list(df['source'].unique())
    base_palette = sns.color_palette("husl", len(sources))
    linestyle_cycle = cycle(['-', '--', '-.', ':'])
    marker_cycle = cycle(['o', 's', '^', 'D', 'P', 'X', 'v', '*'])

    def lighten_color(color, amount=0.5):
        r, g, b = color
        return tuple(1 - (1 - channel) * amount for channel in (r, g, b))

    colors = {}
    linestyles = {}
    markers = {}

    for source, base_color in zip(sources, base_palette):
        linestyles[source] = next(linestyle_cycle)
        markers[source] = next(marker_cycle)
        colors[('HTTP/2', source)] = base_color
        colors[('HTTP/3', source)] = lighten_color(base_color, 0.65)
    
    # 各プロトコル×ソースの組み合わせでプロット
    for protocol in protocols:
        for source in sources:
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
        if y_min is None or y_max is None:
            margin = (max_val - min_val) * 0.15
            default_min = max(0, min_val - margin)
            default_max = max_val + margin
        else:
            default_min = y_min
            default_max = y_max
        lower = y_min if y_min is not None else default_min
        upper = y_max if y_max is not None else default_max
        if lower >= upper:
            raise ValueError("y_min は y_max より小さく設定してください")
        ax.set_ylim(lower, upper)
    
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

def infer_label_from_path(path_str):
    path = Path(path_str)
    parent_name = path.parent.name or "データセット"
    return parent_name


if __name__ == "__main__":
    import sys
    
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 visualize_comparison_combined.py [--output <dir>] <csv[:label]> <csv[:label]> [<csv[:label]> ...]")
        sys.exit(1)
    
    output_dir = None
    y_min = None
    y_max = None
    exclude_range = None
    dataset_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-o", "--output"):
            if i + 1 >= len(args):
                raise ValueError("--output オプションにはディレクトリを指定してください")
            output_dir = args[i + 1]
            i += 2
        elif arg == "--ymin":
            if i + 1 >= len(args):
                raise ValueError("--ymin には値を指定してください")
            y_min = float(args[i + 1])
            i += 2
        elif arg == "--ymax":
            if i + 1 >= len(args):
                raise ValueError("--ymax には値を指定してください")
            y_max = float(args[i + 1])
            i += 2
        elif arg == "--exclude-range":
            if i + 2 >= len(args):
                raise ValueError("--exclude-range には2つの数値を指定してください")
            ex_min = float(args[i + 1])
            ex_max = float(args[i + 2])
            exclude_range = (ex_min, ex_max)
            i += 3
        else:
            dataset_args.append(arg)
            i += 1
    
    if len(dataset_args) < 2:
        raise ValueError("比較するCSVは2つ以上指定してください")
    
    dataset_infos = []
    for item in dataset_args:
        if ':' in item:
            csv_path, label = item.split(':', 1)
        else:
            csv_path = item
            label = infer_label_from_path(csv_path)
        dataset_infos.append((csv_path, label))
    
    if output_dir is None:
        output_dir = str(Path(dataset_infos[0][0]).parent / "comparison_combined")
    os.makedirs(output_dir, exist_ok=True)
    
    create_combined_visualization(dataset_infos, output_dir, y_min, y_max, exclude_range)
