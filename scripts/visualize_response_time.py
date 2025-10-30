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
plt.rcParams['figure.figsize'] = (20, 6)
plt.rcParams['font.size'] = 10

import os

csv_file = os.environ.get('BENCHMARK_CSV')
output_dir = os.environ.get('BENCHMARK_OUTPUT_DIR')

if not csv_file or not output_dir:
    print("エラー: BENCHMARK_CSV と BENCHMARK_OUTPUT_DIR 環境変数を設定してください")
    print("例: BENCHMARK_CSV='logs/latest/benchmark_results.csv' BENCHMARK_OUTPUT_DIR='logs/latest' python3 scripts/visualize_response_time.py")
    exit(1)

df = pd.read_csv(csv_file)

df = df[df['success'] == 1].copy()
df['latency_ms'] = df['latency'].str.replace('ms', '').astype(int)

latencies = sorted(df['latency_ms'].unique())
colors = {'HTTP/2': '#2E86AB', 'HTTP/3': '#A23B72'}

fig, ax = plt.subplots(figsize=(12, 8))

for protocol, color in colors.items():
    data = df[df['protocol'] == protocol]
    means = [data[data['latency_ms'] == lat]['time_total'].mean() for lat in latencies]
    stds = [data[data['latency_ms'] == lat]['time_total'].std() for lat in latencies]
    
    ax.plot(latencies, means, marker='o', linewidth=3.5, markersize=12,
            label=protocol, color=color, zorder=3)
    
    ax.fill_between(latencies, 
                      np.array(means) - np.array(stds), 
                      np.array(means) + np.array(stds), 
                      alpha=0.2, color=color, zorder=1)

    # 主要な遅延ポイントに値を注記（0/2/50/100/150ms が存在する場合のみ）
    target_ms = {0, 2, 50, 100, 150}
    for lat, mean in zip(latencies, means):
        if lat in target_ms and not np.isnan(mean):
            ax.annotate(f"{mean:.3f}秒",
                        xy=(lat, mean),
                        xytext=(6, -10),
                        textcoords='offset points',
                        fontsize=9,
                        color=color,
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=color, alpha=0.7))

# Y軸の範囲を動的に調整
all_means = []
for protocol in colors.keys():
    data = df[df['protocol'] == protocol]
    means = [data[data['latency_ms'] == lat]['time_total'].mean() for lat in latencies]
    all_means.extend(means)

if all_means:
    min_val = min(all_means)
    max_val = max(all_means)
    margin = (max_val - min_val) * 0.1
    ax.set_ylim(max(0, min_val - margin), max_val + margin)

ax.set_xlabel('遅延 (ms)', fontsize=16, fontweight='bold')
ax.set_ylabel('平均応答時間 (秒)', fontsize=16, fontweight='bold')
ax.set_title('HTTP/2 vs HTTP/3 応答速度の比較', fontsize=18, fontweight='bold', pad=20)
ax.legend(fontsize=14, loc='upper left', framealpha=0.9)
ax.grid(True, alpha=0.3, linewidth=1)

# X軸ラベルを間引いて表示（10ms刻みで表示）
step = 10  # 10ms刻みで表示
tick_positions = []
tick_labels = []
for i in range(0, len(latencies), step):
    tick_positions.append(latencies[i])
    tick_labels.append(f'{latencies[i]}ms')

ax.set_xticks(tick_positions)
ax.set_xticklabels(tick_labels, fontsize=10)
ax.tick_params(axis='y', labelsize=12)

textstr = '※ 塗りつぶし部分は標準偏差の範囲を示す'
ax.text(0.02, 0.75, textstr, transform=ax.transAxes,
        fontsize=10, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
output_file = os.path.join(output_dir, 'response_time_comparison.png')
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"グラフを保存しました: {output_file}")
plt.close()

print("\n=== 平均応答時間サマリー ===")
for lat in latencies:
    http2_mean = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == lat)]['time_total'].mean()
    http3_mean = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == lat)]['time_total'].mean()
    diff = http3_mean - http2_mean
    diff_pct = (diff / http2_mean) * 100
    winner = "HTTP/2" if http2_mean < http3_mean else "HTTP/3"
    print(f"{lat}ms: HTTP/2={http2_mean:.3f}秒, HTTP/3={http3_mean:.3f}秒, 差={diff*1000:.1f}ms ({diff_pct:+.1f}%), 勝者: {winner}")

print("\n=== 速度改善率（0msを基準） ===")
http2_baseline = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == 0)]['time_total'].mean()
http3_baseline = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == 0)]['time_total'].mean()

for lat in latencies:
    if lat == 0:
        continue
    http2_mean = df[(df['protocol'] == 'HTTP/2') & (df['latency_ms'] == lat)]['time_total'].mean()
    http3_mean = df[(df['protocol'] == 'HTTP/3') & (df['latency_ms'] == lat)]['time_total'].mean()
    
    http2_slowdown = ((http2_mean - http2_baseline) / http2_baseline) * 100
    http3_slowdown = ((http3_mean - http3_baseline) / http3_baseline) * 100
    
    print(f"{lat}ms: HTTP/2 {http2_slowdown:+.1f}%遅延, HTTP/3 {http3_slowdown:+.1f}%遅延")

