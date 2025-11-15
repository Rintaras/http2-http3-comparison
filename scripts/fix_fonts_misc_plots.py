#!/usr/bin/env python3
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager as fm
from matplotlib.font_manager import FontProperties

# Detect a Japanese-capable font available on this macOS system.
def pick_japanese_font() -> str:
    candidates = [
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Hiragino Maru Gothic ProN",
        "Yu Gothic",
        "Meiryo",
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "IPAexGothic",
        "TakaoGothic",
        "MS Gothic",
        "DejaVu Sans",
    ]
    available = {os.path.basename(p).split(".")[0]: p for p in fm.findSystemFonts(fontpaths=None, fontext="ttf")}
    for name in candidates:
        try:
            # findfont returns a path if it resolves
            path = fm.findfont(name, fallback_to_default=False)
            if os.path.exists(path):
                return name
        except Exception:
            continue
        # fallback: some systems register family slightly different from filename
        if name in available:
            return name
    # As a last resort, let matplotlib choose default sans but it may miss glyphs
    return "DejaVu Sans"

def apply_font():
    jp_font = pick_japanese_font()
    # Apply across all families to avoid fallback to Arial on macOS
    common = [jp_font, "Noto Sans CJK JP", "Yu Gothic", "Meiryo", "DejaVu Sans"]
    plt.rcParams["font.family"] = common
    plt.rcParams["font.sans-serif"] = common
    plt.rcParams["font.serif"] = common
    plt.rcParams["font.cursive"] = common
    plt.rcParams["font.fantasy"] = common
    plt.rcParams["font.monospace"] = common
    plt.rcParams["text.usetex"] = False
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["axes.unicode_minus"] = False
    sns.set_style("whitegrid")
    plt.rcParams["figure.figsize"] = (12, 8)
    plt.rcParams["font.size"] = 16
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.labelweight"] = "bold"
    return jp_font, FontProperties(family=jp_font)

def style_plot(ax, title_text: str, label_text: str, fp: FontProperties):
    line_color = "#2E86AB"
    ax.fill_between([], [], color=line_color, alpha=0.15, zorder=1)  # keep style consistent (no-op placeholder)
    ax.set_title(title_text, fontsize=22, fontweight="bold", pad=20, fontproperties=fp)
    ax.set_xlabel("x", fontsize=18, fontweight="bold", fontproperties=fp)
    ax.set_ylabel("y", fontsize=18, fontweight="bold", fontproperties=fp)
    ax.grid(True, linewidth=1, alpha=0.3)
    bold_fp = FontProperties(family=fp.get_family(), weight="bold")
    ax.legend([label_text], fontsize=15, loc="upper right", framealpha=0.9, prop=bold_fp)
    ax.set_xlim(0, 10)
    ax.tick_params(axis="both", labelsize=14)
    # Make tick labels bold explicitly
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(bold_fp)

def annotate_integers(ax, func):
    line_color = "#2E86AB"
    for t in range(0, 11):
        y_val = float(func(t))
        ax.scatter([t], [y_val], color=line_color, s=70, zorder=5)
        ax.annotate(
            f"{y_val:.2f}",
            xy=(t, y_val),
            xytext=(0, 12),
            textcoords="offset points",
            ha="center",
            fontsize=13,
            fontweight="bold",
            color=line_color,
            bbox=dict(
                boxstyle="round,pad=0.35",
                facecolor="white",
                edgecolor=line_color,
                linewidth=1.2,
                alpha=0.9,
            ),
        )

def draw_and_save(func, label, title, out_path, fp: FontProperties):
    x = np.linspace(0, 10, 800)
    y = func(x)
    fig, ax = plt.subplots(figsize=(12, 8))
    line_color = "#2E86AB"
    ax.plot(x, y, color=line_color, linewidth=3.5, label=label)
    ax.fill_between(x, y, color=line_color, alpha=0.15, zorder=1)
    annotate_integers(ax, func)
    style_plot(ax, title, label, fp)
    plt.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out_path}")

def main():
    jp_font, fp = apply_font()
    print(f"Using font: {jp_font}")
    out_dir = "logs/misc_plots"
    # Original
    func1 = lambda x: 211.61 * np.exp(-0.5511 * x) + 16.04
    draw_and_save(
        func1,
        r"$y = 211.61 e^{-0.5511x} + 16.04$",
        "y = 211.61 e^{-0.5511x} + 16.04 のグラフ",
        os.path.join(out_dir, "exp_decay_function_original.png"),
        fp,
    )
    # Updated single-exponential
    func2 = lambda x: 236.4 * np.exp(-0.6839 * x) + 18.51
    draw_and_save(
        func2,
        r"$y = 236.4 e^{-0.6839x} + 18.51$",
        "y = 236.4 e^{-0.6839x} + 18.51 のグラフ",
        os.path.join(out_dir, "exp_decay_function.png"),
        fp,
    )
    # Third single-exponential
    func3 = lambda x: 233.8 * np.exp(-0.642 * x) + 16.9
    draw_and_save(
        func3,
        r"$y = 233.8 e^{-0.642x} + 16.9$",
        "y = 233.8 e^{-0.642x} + 16.9 のグラフ",
        os.path.join(out_dir, "exp_decay_function_v3.png"),
        fp,
    )
    # Double-exponential
    func4 = lambda x: 258.17 * np.exp(-0.976 * x) + 44.92 * np.exp(-0.0978 * x)
    draw_and_save(
        func4,
        r"$y = 258.17 e^{-0.976x} + 44.92 e^{-0.0978x}$",
        "y = 258.17 e^{-0.976x} + 44.92 e^{-0.0978x} のグラフ",
        os.path.join(out_dir, "exp_decay_function_v4.png"),
        fp,
    )

if __name__ == "__main__":
    main()


