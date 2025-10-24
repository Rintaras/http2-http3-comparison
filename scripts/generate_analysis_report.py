#!/usr/bin/env python3
"""
ベンチマーク結果の詳細分析レポート生成スクリプト
各遅延条件でのHTTP/2とHTTP/3の性能比較、優位逆転地点の特定
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

def find_crossover_points(h2_means, h3_means, latencies):
    """HTTP/2とHTTP/3の優位逆転地点を特定"""
    crossovers = []
    
    for i in range(1, len(latencies)):
        # 前回の優位性を確認
        prev_h2_faster = h2_means[i-1] < h3_means[i-1]
        curr_h2_faster = h2_means[i] < h3_means[i]
        
        # 優位性が逆転した場合
        if prev_h2_faster != curr_h2_faster:
            # 線形補間で正確な逆転点を計算
            h2_diff = h2_means[i] - h2_means[i-1]
            h3_diff = h3_means[i] - h3_means[i-1]
            
            # 前回の差
            prev_diff = h2_means[i-1] - h3_means[i-1]
            
            if h2_diff != h3_diff:  # 傾きが異なる場合のみ
                # 線形補間で逆転点を計算
                ratio = prev_diff / (prev_diff - (h2_means[i] - h3_means[i]))
                crossover_latency = latencies[i-1] + ratio * (latencies[i] - latencies[i-1])
                
                crossovers.append({
                    'latency': crossover_latency,
                    'h2_time': h2_means[i-1] + ratio * (h2_means[i] - h2_means[i-1]),
                    'h3_time': h3_means[i-1] + ratio * (h3_means[i] - h3_means[i-1]),
                    'direction': 'H3→H2' if prev_h2_faster else 'H2→H3'
                })
    
    return crossovers

def generate_analysis_report(csv_file, output_dir):
    """詳細分析レポートを生成"""
    
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file)
    
    # 遅延条件を動的に取得（数値でソート）
    latencies_str = df['latency'].unique()
    lat_values = [int(lat.replace('ms', '')) for lat in latencies_str]
    
    # 数値でソートしてインデックスを取得
    sorted_indices = sorted(range(len(lat_values)), key=lambda i: lat_values[i])
    latencies = [latencies_str[i] for i in sorted_indices]
    lat_values = [lat_values[i] for i in sorted_indices]
    
    # プロトコル別データを準備
    h2_data = []
    h3_data = []
    
    for lat in latencies:
        h2_subset = df[(df['protocol'] == 'HTTP/2') & (df['latency'] == lat)]['time_total']
        h3_subset = df[(df['protocol'] == 'HTTP/3') & (df['latency'] == lat)]['time_total']
        
        h2_data.append({
            'latency': lat,
            'mean': h2_subset.mean(),
            'std': h2_subset.std(),
            'count': len(h2_subset)
        })
        
        h3_data.append({
            'latency': lat,
            'mean': h3_subset.mean(),
            'std': h3_subset.std(),
            'count': len(h3_subset)
        })
    
    # 優位逆転地点を特定
    h2_means = [d['mean'] for d in h2_data]
    h3_means = [d['mean'] for d in h3_data]
    crossovers = find_crossover_points(h2_means, h3_means, lat_values)
    
    # レポート生成
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("HTTP/2 vs HTTP/3 ベンチマーク詳細分析レポート")
    report_lines.append("=" * 80)
    report_lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"データファイル: {os.path.basename(csv_file)}")
    report_lines.append(f"総遅延条件数: {len(latencies)}")
    report_lines.append("")
    
    # サマリー統計
    report_lines.append("【サマリー統計】")
    report_lines.append("-" * 40)
    
    # 0msでの性能
    h2_0ms = h2_data[0]
    h3_0ms = h3_data[0]
    report_lines.append(f"0ms遅延時:")
    report_lines.append(f"  HTTP/2: 平均={h2_0ms['mean']:.3f}秒, 標準偏差={h2_0ms['std']:.4f}秒")
    report_lines.append(f"  HTTP/3: 平均={h3_0ms['mean']:.3f}秒, 標準偏差={h3_0ms['std']:.4f}秒")
    
    # 150msでの性能
    h2_150ms = h2_data[-1]
    h3_150ms = h3_data[-1]
    report_lines.append(f"150ms遅延時:")
    report_lines.append(f"  HTTP/2: 平均={h2_150ms['mean']:.3f}秒, 標準偏差={h2_150ms['std']:.4f}秒")
    report_lines.append(f"  HTTP/3: 平均={h3_150ms['mean']:.3f}秒, 標準偏差={h3_150ms['std']:.4f}秒")
    
    # 性能差の計算
    h2_improvement = ((h2_150ms['mean'] - h2_0ms['mean']) / h2_0ms['mean']) * 100
    h3_improvement = ((h3_150ms['mean'] - h3_0ms['mean']) / h3_0ms['mean']) * 100
    
    report_lines.append(f"遅延による性能劣化:")
    report_lines.append(f"  HTTP/2: {h2_improvement:.1f}%")
    report_lines.append(f"  HTTP/3: {h3_improvement:.1f}%")
    report_lines.append("")
    
    # 優位逆転地点
    if crossovers:
        report_lines.append("【優位逆転地点】")
        report_lines.append("-" * 40)
        for i, crossover in enumerate(crossovers, 1):
            report_lines.append(f"逆転地点 {i}: {crossover['latency']:.1f}ms")
            report_lines.append(f"  方向: {crossover['direction']}")
            report_lines.append(f"  HTTP/2: {crossover['h2_time']:.3f}秒")
            report_lines.append(f"  HTTP/3: {crossover['h3_time']:.3f}秒")
            report_lines.append("")
    else:
        report_lines.append("【優位逆転地点】")
        report_lines.append("-" * 40)
        report_lines.append("優位逆転は発生していません")
        report_lines.append("")
    
    # 詳細データテーブル
    report_lines.append("【詳細データテーブル】")
    report_lines.append("-" * 80)
    report_lines.append(f"{'遅延':<8} {'HTTP/2平均':<12} {'HTTP/2標準偏差':<15} {'HTTP/3平均':<12} {'HTTP/3標準偏差':<15} {'優位性':<8}")
    report_lines.append("-" * 80)
    
    for i, lat in enumerate(latencies):
        h2 = h2_data[i]
        h3 = h3_data[i]
        
        # 優位性の判定
        if h2['mean'] < h3['mean']:
            advantage = "HTTP/2"
        elif h3['mean'] < h2['mean']:
            advantage = "HTTP/3"
        else:
            advantage = "同等"
        
        report_lines.append(f"{lat:<8} {h2['mean']:<12.3f} {h2['std']:<15.4f} {h3['mean']:<12.3f} {h3['std']:<15.4f} {advantage:<8}")
    
    report_lines.append("")
    
    # 統計分析
    report_lines.append("【統計分析】")
    report_lines.append("-" * 40)
    
    # 各遅延での優位性カウント
    h2_wins = sum(1 for i in range(len(latencies)) if h2_data[i]['mean'] < h3_data[i]['mean'])
    h3_wins = sum(1 for i in range(len(latencies)) if h3_data[i]['mean'] < h2_data[i]['mean'])
    ties = len(latencies) - h2_wins - h3_wins
    
    report_lines.append(f"HTTP/2優位: {h2_wins}回 ({h2_wins/len(latencies)*100:.1f}%)")
    report_lines.append(f"HTTP/3優位: {h3_wins}回 ({h3_wins/len(latencies)*100:.1f}%)")
    report_lines.append(f"同等: {ties}回 ({ties/len(latencies)*100:.1f}%)")
    
    # 平均性能差
    avg_h2 = np.mean([d['mean'] for d in h2_data])
    avg_h3 = np.mean([d['mean'] for d in h3_data])
    avg_diff = ((avg_h2 - avg_h3) / avg_h3) * 100
    
    report_lines.append(f"平均性能差: {avg_diff:+.1f}% (HTTP/2基準)")
    
    # 標準偏差の比較
    avg_h2_std = np.mean([d['std'] for d in h2_data])
    avg_h3_std = np.mean([d['std'] for d in h3_data])
    
    report_lines.append(f"平均標準偏差:")
    report_lines.append(f"  HTTP/2: {avg_h2_std:.4f}秒")
    report_lines.append(f"  HTTP/3: {avg_h3_std:.4f}秒")
    
    # レポートをファイルに保存
    report_content = "\n".join(report_lines)
    report_file = os.path.join(output_dir, "detailed_analysis_report.txt")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"詳細分析レポートを保存しました: {report_file}")
    
    # コンソールにも表示
    print("\n" + "=" * 80)
    print("HTTP/2 vs HTTP/3 ベンチマーク詳細分析レポート")
    print("=" * 80)
    print(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"データファイル: {os.path.basename(csv_file)}")
    print(f"総遅延条件数: {len(latencies)}")
    print("")
    
    # サマリー統計
    print("【サマリー統計】")
    print("-" * 40)
    print(f"0ms遅延時:")
    print(f"  HTTP/2: 平均={h2_0ms['mean']:.3f}秒, 標準偏差={h2_0ms['std']:.4f}秒")
    print(f"  HTTP/3: 平均={h3_0ms['mean']:.3f}秒, 標準偏差={h3_0ms['std']:.4f}秒")
    print(f"150ms遅延時:")
    print(f"  HTTP/2: 平均={h2_150ms['mean']:.3f}秒, 標準偏差={h2_150ms['std']:.4f}秒")
    print(f"  HTTP/3: 平均={h3_150ms['mean']:.3f}秒, 標準偏差={h3_150ms['std']:.4f}秒")
    print(f"遅延による性能劣化:")
    print(f"  HTTP/2: {h2_improvement:.1f}%")
    print(f"  HTTP/3: {h3_improvement:.1f}%")
    print("")
    
    # 優位逆転地点
    if crossovers:
        print("【優位逆転地点】")
        print("-" * 40)
        for i, crossover in enumerate(crossovers, 1):
            print(f"逆転地点 {i}: {crossover['latency']:.1f}ms")
            print(f"  方向: {crossover['direction']}")
            print(f"  HTTP/2: {crossover['h2_time']:.3f}秒")
            print(f"  HTTP/3: {crossover['h3_time']:.3f}秒")
            print("")
    else:
        print("【優位逆転地点】")
        print("-" * 40)
        print("優位逆転は発生していません")
        print("")
    
    # 統計分析
    print("【統計分析】")
    print("-" * 40)
    print(f"HTTP/2優位: {h2_wins}回 ({h2_wins/len(latencies)*100:.1f}%)")
    print(f"HTTP/3優位: {h3_wins}回 ({h3_wins/len(latencies)*100:.1f}%)")
    print(f"同等: {ties}回 ({ties/len(latencies)*100:.1f}%)")
    print(f"平均性能差: {avg_diff:+.1f}% (HTTP/2基準)")
    print(f"平均標準偏差:")
    print(f"  HTTP/2: {avg_h2_std:.4f}秒")
    print(f"  HTTP/3: {avg_h3_std:.4f}秒")

if __name__ == "__main__":
    # 環境変数からファイルパスを取得
    csv_file = os.environ.get('BENCHMARK_CSV')
    output_dir = os.environ.get('BENCHMARK_OUTPUT_DIR')
    
    if not csv_file or not output_dir:
        print("エラー: BENCHMARK_CSV と BENCHMARK_OUTPUT_DIR 環境変数を設定してください")
        sys.exit(1)
    
    if not os.path.exists(csv_file):
        print(f"エラー: CSVファイルが見つかりません: {csv_file}")
        sys.exit(1)
    
    if not os.path.exists(output_dir):
        print(f"エラー: 出力ディレクトリが見つかりません: {output_dir}")
        sys.exit(1)
    
    generate_analysis_report(csv_file, output_dir)
