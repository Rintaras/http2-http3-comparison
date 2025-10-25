#!/usr/bin/env python3
"""
ベンチマークデータの検証スクリプト

実測的なデータが得られているか確認:
1. 転送サイズが約1MB（1024 KB）か
2. 転送時間が妥当か（1-3秒程度）
3. 転送速度が現実的か（300-800 kbps）
"""

import pandas as pd
import sys
import os
from pathlib import Path

def validate_benchmark_data(csv_file):
    """ベンチマークデータの妥当性を検証"""
    
    if not os.path.exists(csv_file):
        print(f"❌ エラー: CSVファイルが見つかりません: {csv_file}")
        return False
    
    print(f"📊 ベンチマークデータの検証: {csv_file}")
    print("=" * 60)
    
    df = pd.read_csv(csv_file)
    
    # 成功したレコードのみを対象
    df_success = df[df['success'] == 1]
    
    print(f"\n【データ統計】")
    print(f"総レコード数: {len(df)}")
    print(f"成功レコード: {len(df_success)}")
    print(f"失敗レコード: {len(df) - len(df_success)}")
    
    if len(df_success) == 0:
        print("❌ 成功したレコードがありません！")
        return False
    
    # 転送サイズの計算
    print(f"\n【転送サイズ検証】")
    df_success['transferred_kb'] = df_success['time_total'] * df_success['speed_kbps']
    
    avg_transferred = df_success['transferred_kb'].mean()
    min_transferred = df_success['transferred_kb'].min()
    max_transferred = df_success['transferred_kb'].max()
    std_transferred = df_success['transferred_kb'].std()
    
    print(f"平均転送量: {avg_transferred:.2f} KB")
    print(f"最小転送量: {min_transferred:.2f} KB")
    print(f"最大転送量: {max_transferred:.2f} KB")
    print(f"標準偏差:   {std_transferred:.2f} KB")
    
    # 1MB (1024 KB) 付近かチェック
    expected_kb = 1024
    tolerance = 100  # ±100 KBの許容範囲
    
    if abs(avg_transferred - expected_kb) < tolerance:
        print(f"✅ 転送サイズが妥当（1024 KB 付近）")
        size_ok = True
    else:
        print(f"❌ 転送サイズが異常（期待値: ~1024 KB, 実値: {avg_transferred:.2f} KB）")
        if avg_transferred < 50:
            print("   → ファイルサイズが非常に小さい（転送が正常に行われていない可能性）")
        size_ok = False
    
    # 通信時間の検証
    print(f"\n【通信時間検証】")
    avg_time = df_success['time_total'].mean()
    min_time = df_success['time_total'].min()
    max_time = df_success['time_total'].max()
    std_time = df_success['time_total'].std()
    
    print(f"平均通信時間: {avg_time:.4f}秒")
    print(f"最小通信時間: {min_time:.4f}秒")
    print(f"最大通信時間: {max_time:.4f}秒")
    print(f"標準偏差:     {std_time:.4f}秒")
    
    # 1MBなら1-3秒程度が妥当
    if 0.5 < avg_time < 5:
        print(f"✅ 通信時間が妥当（0.5-5秒の範囲内）")
        time_ok = True
    else:
        print(f"❌ 通信時間が異常")
        if avg_time < 0.1:
            print("   → 転送が異常に高速（実際のデータ転送ではない可能性）")
        time_ok = False
    
    # 転送速度の検証
    print(f"\n【転送速度検証】")
    avg_speed = df_success['speed_kbps'].mean()
    min_speed = df_success['speed_kbps'].min()
    max_speed = df_success['speed_kbps'].max()
    
    print(f"平均転送速度: {avg_speed:.2f} kbps")
    print(f"最小転送速度: {min_speed:.2f} kbps")
    print(f"最大転送速度: {max_speed:.2f} kbps")
    
    # 300-800 kbps 程度が妥当
    if 50 < avg_speed < 2000:
        print(f"✅ 転送速度が妥当（50-2000 kbps の範囲内）")
        speed_ok = True
    else:
        print(f"❌ 転送速度が異常")
        if avg_speed < 5:
            print("   → 転送速度が異常に遅い（通信が確立されていない可能性）")
        speed_ok = False
    
    # プロトコル確認
    print(f"\n【プロトコル検証】")
    protocols = df_success['protocol'].unique()
    print(f"検出されたプロトコル: {protocols}")
    
    for proto in protocols:
        proto_data = df_success[df_success['protocol'] == proto]
        if 'http_version' in proto_data.columns:
            versions = proto_data['http_version'].unique()
            print(f"  {proto}: {versions}")
    
    # 遅延条件の確認
    print(f"\n【遅延条件検証】")
    latencies = sorted([int(lat.replace('ms', '')) for lat in df_success['latency'].unique()])
    print(f"遅延条件数: {len(latencies)}")
    print(f"遅延範囲: {min(latencies)}ms - {max(latencies)}ms")
    if len(latencies) > 10:
        print(f"遅延条件: {latencies[:5]} ... {latencies[-5:]} (最初と最後の5条件を表示)")
    else:
        print(f"遅延条件: {latencies}")
    
    if len(latencies) >= 100:
        print(f"✅ 包括的なテスト（100以上の遅延条件）")
        latency_ok = True
    elif len(latencies) >= 30:
        print(f"⚠️  一定の包括性（30以上の遅延条件）")
        latency_ok = True
    else:
        print(f"❌ 限定的なテスト（30未満の遅延条件）")
        latency_ok = False
    
    # 総合判定
    print(f"\n【総合評価】")
    print("=" * 60)
    
    all_ok = size_ok and time_ok and speed_ok and latency_ok
    
    if all_ok:
        print("✅ 実測的で信頼できるベンチマークデータです")
        return True
    else:
        print("⚠️  データに問題がある可能性があります:")
        if not size_ok:
            print("   - 転送サイズが異常（1MB未満または非常に大きい）")
        if not time_ok:
            print("   - 通信時間が異常（0.1秒以下または5秒以上）")
        if not speed_ok:
            print("   - 転送速度が異常（50 kbps未満または2000 kbps以上）")
        if not latency_ok:
            print("   - 遅延条件が限定的（30未満）")
        print("\nDocker環境の設定を見直してください")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用法: python3 validate_benchmark_data.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    success = validate_benchmark_data(csv_file)
    sys.exit(0 if success else 1)
