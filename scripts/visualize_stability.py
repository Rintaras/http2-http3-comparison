#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import matplotlib.font_manager as fm

sns.set_style("whitegrid")

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
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

import os

csv_file = os.environ.get('BENCHMARK_CSV', 'benchmark_results_20251001_171222.csv')
output_dir = os.environ.get('BENCHMARK_OUTPUT_DIR', '.')

df = pd.read_csv(csv_file)

df = df[df['success'] == 1].copy()
df['latency_ms'] = df['latency'].str.replace('ms', '').astype(int)

latencies = sorted(df['latency_ms'].unique())
colors = {'HTTP/2': '#2E86AB', 'HTTP/3': '#A23B72'}

# 3つのサブプロットを作成
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 7))

# 左側: 標準偏差（従来）
for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    stds = [data[data['latency_ms'] == lat]['time_total'].std() for lat in latencies]
    ax1.plot(latencies, stds, marker='o', linewidth=3, markersize=10,
            label=protocol, color=color)

ax1.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
ax1.set_ylabel('標準偏差 (秒)', fontsize=14, fontweight='bold')
ax1.set_title('標準偏差の比較（従来指標）\n低い値ほど安定', fontsize=16, fontweight='bold', pad=20)
ax1.legend(fontsize=13, loc='best')
ax1.grid(True, alpha=0.3)

for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    stds = [data[data['latency_ms'] == lat]['time_total'].std() for lat in latencies]
    for i, (lat, std) in enumerate(zip(latencies, stds)):
        ax1.annotate(f'{std:.3f}', 
                   xy=(lat, std), 
                   xytext=(5, 5), 
                   textcoords='offset points',
                   fontsize=10,
                   color=color,
                   fontweight='bold')

ax1.set_xticks(latencies)
ax1.set_xticklabels([f'{lat}ms' for lat in latencies])

# 右側: パーセンタイル範囲（P5-P95）
for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    p5_values = [data[data['latency_ms'] == lat]['time_total'].quantile(0.05) for lat in latencies]
    p95_values = [data[data['latency_ms'] == lat]['time_total'].quantile(0.95) for lat in latencies]
    p50_values = [data[data['latency_ms'] == lat]['time_total'].quantile(0.50) for lat in latencies]
    
    # 中央値
    ax2.plot(latencies, p50_values, marker='o', linewidth=3, markersize=10,
            label=f'{protocol} (中央値)', color=color)
    
    # 95%信頼区間（P5-P95）
    ranges = [p95 - p5 for p5, p95 in zip(p5_values, p95_values)]
    ax2.plot(latencies, ranges, marker='s', linewidth=2, markersize=8,
            label=f'{protocol} (P5-P95範囲)', color=color, linestyle='--', alpha=0.7)

ax2.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
ax2.set_ylabel('時間 (秒)', fontsize=14, fontweight='bold')
ax2.set_title('パーセンタイル分析（改善指標）\n95%信頼区間の範囲', fontsize=16, fontweight='bold', pad=20)
ax2.legend(fontsize=11, loc='best')
ax2.grid(True, alpha=0.3)

ax2.set_xticks(latencies)
ax2.set_xticklabels([f'{lat}ms' for lat in latencies])

# 右側: 変動係数（CV）
for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    cvs = []
    for lat in latencies:
        lat_data = data[data['latency_ms'] == lat]['time_total']
        mean_val = lat_data.mean()
        std_val = lat_data.std()
        cv = (std_val / mean_val) * 100  # パーセント表示
        cvs.append(cv)
    
    ax3.plot(latencies, cvs, marker='o', linewidth=3, markersize=10,
            label=protocol, color=color)

ax3.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
ax3.set_ylabel('変動係数 (%)', fontsize=14, fontweight='bold')
ax3.set_title('変動係数の比較（相対安定性）\n低い値ほど安定', fontsize=16, fontweight='bold', pad=20)
ax3.legend(fontsize=13, loc='best')
ax3.grid(True, alpha=0.3)

for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    cvs = []
    for lat in latencies:
        lat_data = data[data['latency_ms'] == lat]['time_total']
        mean_val = lat_data.mean()
        std_val = lat_data.std()
        cv = (std_val / mean_val) * 100
        cvs.append(cv)
    
    for i, (lat, cv) in enumerate(zip(latencies, cvs)):
        ax3.annotate(f'{cv:.1f}%', 
                   xy=(lat, cv), 
                   xytext=(5, 5), 
                   textcoords='offset points',
                   fontsize=10,
                   color=color,
                   fontweight='bold')

ax3.set_xticks(latencies)
ax3.set_xticklabels([f'{lat}ms' for lat in latencies])

plt.tight_layout()
output_file = os.path.join(output_dir, 'stability_comparison_comprehensive.png')
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"包括的な安定性グラフを保存しました: {output_file}")
plt.close()

print("\n=== 標準偏差サマリー（従来指標） ===")
for lat in latencies:
    http2_std = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == lat)]['time_total'].std()
    http3_std = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == lat)]['time_total'].std()
    ratio = http3_std / http2_std
    winner = "HTTP/2" if http2_std < http3_std else "HTTP/3"
    print(f"{lat}ms: HTTP/2={http2_std:.4f}s, HTTP/3={http3_std:.4f}s, 比={ratio:.2f}倍, 安定性: {winner}")

print("\n=== パーセンタイル分析サマリー（改善指標） ===")
for lat in latencies:
    http2_data = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == lat)]['time_total']
    http3_data = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == lat)]['time_total']
    
    http2_p5 = http2_data.quantile(0.05)
    http2_p95 = http2_data.quantile(0.95)
    http2_range = http2_p95 - http2_p5
    
    http3_p5 = http3_data.quantile(0.05)
    http3_p95 = http3_data.quantile(0.95)
    http3_range = http3_p95 - http3_p5
    
    ratio = http3_range / http2_range
    winner = "HTTP/2" if http2_range < http3_range else "HTTP/3"
    print(f"{lat}ms: HTTP/2範囲={http2_range:.4f}s, HTTP/3範囲={http3_range:.4f}s, 比={ratio:.2f}倍, 安定性: {winner}")

print("\n=== 変動係数サマリー（相対安定性指標） ===")
for lat in latencies:
    http2_data = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == lat)]['time_total']
    http3_data = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == lat)]['time_total']
    
    http2_cv = (http2_data.std() / http2_data.mean()) * 100
    http3_cv = (http3_data.std() / http3_data.mean()) * 100
    
    ratio = http3_cv / http2_cv
    winner = "HTTP/2" if http2_cv < http3_cv else "HTTP/3"
    print(f"{lat}ms: HTTP/2 CV={http2_cv:.1f}%, HTTP/3 CV={http3_cv:.1f}%, 比={ratio:.2f}倍, 安定性: {winner}")

print("\n=== 総合安定性評価 ===")
print("各指標での勝敗を集計:")
for lat in latencies:
    # 標準偏差
    http2_std = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == lat)]['time_total'].std()
    http3_std = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == lat)]['time_total'].std()
    std_winner = "HTTP/2" if http2_std < http3_std else "HTTP/3"
    
    # パーセンタイル範囲
    http2_data = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == lat)]['time_total']
    http3_data = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == lat)]['time_total']
    http2_range = http2_data.quantile(0.95) - http2_data.quantile(0.05)
    http3_range = http3_data.quantile(0.95) - http3_data.quantile(0.05)
    range_winner = "HTTP/2" if http2_range < http3_range else "HTTP/3"
    
    # 変動係数
    http2_cv = (http2_data.std() / http2_data.mean()) * 100
    http3_cv = (http3_data.std() / http3_data.mean()) * 100
    cv_winner = "HTTP/2" if http2_cv < http3_cv else "HTTP/3"
    
    # 集計
    http2_wins = sum([std_winner == "HTTP/2", range_winner == "HTTP/2", cv_winner == "HTTP/2"])
    http3_wins = sum([std_winner == "HTTP/3", range_winner == "HTTP/3", cv_winner == "HTTP/3"])
    
    overall_winner = "HTTP/2" if http2_wins > http3_wins else "HTTP/3" if http3_wins > http2_wins else "引き分け"
    print(f"{lat}ms: 標準偏差={std_winner}, パーセンタイル={range_winner}, 変動係数={cv_winner} → 総合: {overall_winner}")

"""
ここから下は、ユーザー要望に基づき「P5-P95範囲のみ」を可視化するスタンドアロンのグラフを生成する。
上の包括グラフとは独立したファイルとして出力する。
"""

# パーセンタイル範囲（P5-P95）のみを可視化
fig, ax = plt.subplots(figsize=(10, 7))

for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    p5_values = [data[data['latency_ms'] == lat]['time_total'].quantile(0.05) for lat in latencies]
    p95_values = [data[data['latency_ms'] == lat]['time_total'].quantile(0.95) for lat in latencies]
    ranges = [p95 - p5 for p5, p95 in zip(p5_values, p95_values)]
    ax.plot(latencies, ranges, marker='o', linewidth=3, markersize=10,
            label=protocol, color=color)
    for lat, r in zip(latencies, ranges):
        ax.annotate(f"{r:.3f}", xy=(lat, r), xytext=(5, 5), textcoords='offset points',
                    fontsize=10, color=color, fontweight='bold')

ax.set_xlabel('遅延 (ms)', fontsize=14, fontweight='bold')
ax.set_ylabel('P5–P95 範囲 (秒)', fontsize=14, fontweight='bold')
ax.set_title('パーセンタイル範囲のみの比較（P5–P95）\n低いほど安定', fontsize=16, fontweight='bold', pad=20)
ax.legend(fontsize=13, loc='best')
ax.grid(True, alpha=0.3)
ax.set_xticks(latencies)
ax.set_xticklabels([f'{lat}ms' for lat in latencies])

plt.tight_layout()
only_range_file = os.path.join(output_dir, 'stability_percentile_range.png')
plt.savefig(only_range_file, dpi=300, bbox_inches='tight')
print(f"P5–P95範囲のみのグラフを保存しました: {only_range_file}")
plt.close()
