#!/usr/bin/env python3
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import os

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Noto Sans CJK JP', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

# Updated function: y = 236.4 e^{-0.6839 x} + 18.51
func = lambda x: 236.4 * np.exp(-0.6839 * x) + 18.51
x = np.linspace(0, 10, 400)
y = func(x)

fig, ax = plt.subplots(figsize=(12, 8))
line_color = '#2E86AB'
ax.plot(x, y, color=line_color, linewidth=3.5, label=r"$y = 236.4 e^{-0.6839x} + 18.51$")
ax.fill_between(x, y, color=line_color, alpha=0.15, zorder=1)

# Annotate integer points 0..10 (including odd numbers)
for t in range(0, 11):
    y_val = func(t)
    ax.scatter([t], [y_val], color=line_color, s=70, zorder=5)
    ax.annotate(f"{y_val:.2f}",
                xy=(t, y_val),
                xytext=(0, 12),
                textcoords='offset points',
                ha='center',
                fontsize=11,
                fontweight='bold',
                color=line_color,
                bbox=dict(boxstyle='round,pad=0.35', facecolor='white', edgecolor=line_color, linewidth=1.2, alpha=0.9))

ax.set_title('y = 236.4 e^{-0.6839x} + 18.51 のグラフ', fontsize=18, fontweight='bold', pad=20)
ax.set_xlabel('x', fontsize=16, fontweight='bold')
ax.set_ylabel('y', fontsize=16, fontweight='bold')
ax.grid(True, linewidth=1, alpha=0.3)
ax.legend(fontsize=13, loc='upper right', framealpha=0.9)
ax.set_xlim(0, 10)
ax.tick_params(axis='both', labelsize=12)

plt.tight_layout()
output_dir = 'logs/misc_plots'
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, 'exp_decay_function.png')
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print('グラフを保存しました:', output_path)
