# 実測的ベンチマーク実行計画

## 概要

実機環境での0-150ms全遅延条件ベンチマークを実施するための実行計画書です。

---

## 実行設定

| 項目 | 値 |
|------|-----|
| **遅延条件** | 0-150ms (151条件) |
| **反復回数** | 25回/条件 |
| **プロトコル** | HTTP/2, HTTP/3 |
| **総リクエスト数** | 7,550個 |
| **推定実行時間** | **4.5時間** |
| **総データポイント** | 7,550+ |

---

## 実行時間の内訳

```
初期化・ウォームアップ:           10分
遅延条件処理 (151条件):         4時間 18分
  - TC設定:                   ~106分
  - HTTP/3測定 (25回×151):    ~1h18m
  - HTTP/2測定 (25回×151):    ~1h18m
  - 切り替え・待機:            ~36分

データ検証・グラフ生成:           10分
─────────────────────────────────────
**合計:                        約4.5時間**
```

---

## ステップバイステップの実行ガイド

### ステップ 1: 前準備 (実行前)

```bash
# プロジェクトディレクトリに移動
cd /Users/root1/Documents/Research/gRPC_over_HTTP3/protocol_comparison

# スクリプトが最新であることを確認
grep "DELAYS=" test_ubuntu_connection/run_benchmark.sh
# 出力: DELAYS=($(seq 0 1 150))  ✅ 

# 依存関係の確認
python3 -c "import pandas, matplotlib, seaborn; print('✅ Dependencies OK')"
```

### ステップ 2: ベンチマーク実行

```bash
# 方法A: 標準実行 (推奨)
./bench.sh -n 25 -p 0.1

# または方法B: 直接実行
ITERATIONS=25 SLEEP_BETWEEN_SEC=0.1 test_ubuntu_connection/run_benchmark.sh
```

**実行中の表示**:
```
========================================
実機ベンチマーク設定
========================================
遅延条件: 151個 (0-150ms全範囲, 1ms刻み)
反復回数: 25回
サーバー: https://192.168.1.100:8443
帯域制限: 5mbit
プロトコル: HTTP/2 vs HTTP/3 (実測的ベンチマーク)

=== 初期安定化処理 ...
遅延 0ms
  ...
遅延 150ms
  ...

========================================
ベンチマークデータ検証
========================================
📊 ベンチマークデータの検証: logs/20251025_120000/benchmark_results.csv
...
```

### ステップ 3: 結果確認

実行完了後、以下が自動生成されます：

```
logs/20251025_120000/
├── benchmark_results.csv           (7550行 のベンチマークデータ)
├── response_time_comparison.png    (応答時間グラフ)
├── standard_deviation_vs_latency.png (標準偏差グラフ)
├── stability_percentile_range.png   (P5-P95パーセンタイル)
├── transfer_time_boxplot.png        (箱ひげ図)
├── analysis_report.txt              (詳細分析レポート)
└── validation_report.txt            (検証結果)  ← NEW!
```

### ステップ 4: データ検証

```bash
# 検証結果の確認
python3 scripts/validate_benchmark_data.py logs/latest/benchmark_results.csv

# 期待結果:
# ✅ 転送サイズが妥当（1024 KB 付近）
# ✅ 通信時間が妥当（0.5-5秒の範囲内）
# ✅ 転送速度が妥当（50-2000 kbps の範囲内）
# ✅ 包括的なテスト（100以上の遅延条件）
```

---

## リスク・対応策

### リスク1: 実行中の接続失敗

**症状**: 一部の遅延条件でカールが失敗
**対応策**: スクリプトは失敗を容認して続行（`|| true`）

```bash
# 失敗は許容値として記録される
# CSV: success=0 の行が増えるが、全体の統計には影響小
```

### リスク2: ネットワーク不安定

**症状**: 高遅延条件でタイムアウト
**対応策**: curlのタイムアウトは15秒設定（十分な余裕）

```bash
# 実際の転送時間: 1-3秒 
# タイムアウト:  15秒 ✅ 十分な余裕
```

### リスク3: 実行時間が長い

**症状**: 4.5時間は長すぎる
**代替案**: 遅延条件を削減
```bash
# 軽量版: 10ms刻み (16条件)
# DELAYS=($(seq 0 10 150))
# 推定時間: 18分
```

---

## 期待される結果

### 20251001との比較

| 指標 | 20251001 | 予想値 |
|------|---------|--------|
| 総データ数 | 400行 | 7,550行 |
| 遅延条件 | 151個 | 151個 ✅ |
| 平均転送 | 1024 KB | 1024 KB ✅ |
| HTTP/3改善 | 5.5% | 5-10% ✅ |

### グラフの改善

```
旧データ (20251001):
- 151個の遅延条件をカバー
- ポイント数: 400個

新データ (予定):
- 151個の遅延条件をカバー  
- ポイント数: 7,550個 ← 詳細な曲線が得られる！
- より正確なトレンド線
- より低いばらつき
```

---

## 実行後のアクション

### 1. グラフの確認

```bash
# 最新グラフを表示
open logs/latest/response_time_comparison.png
open logs/latest/stability_percentile_range.png
open logs/latest/standard_deviation_vs_latency.png
open logs/latest/transfer_time_boxplot.png
```

### 2. 分析レポートの確認

```bash
# 詳細分析レポート
cat logs/latest/analysis_report.txt

# 検証レポート
cat logs/latest/validation_report.txt  # NEW!
```

### 3. Docker環境との比較

```bash
# Docker版も実行（オプション）
./docker_benchmark.sh

# データを並べて比較
python3 << 'PYTHON'
import pandas as pd

real = pd.read_csv('logs/20251025_120000/benchmark_results.csv')
docker = pd.read_csv('logs/docker_realistic_20251025_120000/benchmark_results.csv')

print("実機 vs Docker比較:")
print(f"実機:   平均転送 {real['time_total'].mean():.4f}秒")
print(f"Docker: 平均転送 {docker['time_total'].mean():.4f}秒")
PYTHON
```

---

## トラブルシューティング

### Q: サーバーに接続できない
```bash
# 接続テスト
curl -sk https://192.168.1.100:8443/

# サーバー確認
ssh ubuntu@192.168.1.100 'systemctl status http3-server'
```

### Q: グラフが生成されない
```bash
# Python環境の確認
source venv/bin/activate
python3 -c "import matplotlib; print(matplotlib.__version__)"

# 手動でグラフ生成
BENCHMARK_CSV="logs/latest/benchmark_results.csv" \
BENCHMARK_OUTPUT_DIR="logs/latest" \
python3 scripts/visualize_response_time.py
```

### Q: 実行が途中で止まった
```bash
# 続きから再開 (まだ実装されていない - 全からやり直す必要)
./bench.sh -n 25 -p 0.1
```

---

## 推奨スケジュール

| 時刻 | 実行内容 | 所要時間 |
|------|---------|---------|
| 09:00 | 準備確認 | 10分 |
| 09:10 | **ベンチマーク開始** | **4時間30分** |
| 13:45 | **ベンチマーク終了** | - |
| 13:45 | 結果検証 | 15分 |
| 14:00 | 分析完了 | - |

---

## 次のステップ

✅ 実機: 0-150ms全遅延条件実行

🟡 Docker: 検証と改善 (オプション)
- [ ] Docker Compose設定の確認
- [ ] ルーター設定の検証
- [ ] 全遅延条件でのテスト
- [ ] 検証ツールで確認

🔵 最終比較 (オプション)
- [ ] 実機 vs Docker の詳細比較
- [ ] パフォーマンス差の分析
- [ ] 論文への掲載

---

## まとめ

✅ **実機での0-150ms全遅延条件ベンチマークは実現可能**
- 推定実行時間: 4.5時間
- 総データ数: 7,550+
- 信頼性: 高い

✅ **検証ツールも準備完了**
- 自動データ検証
- 異常値の検出
- 信頼性の確保

🚀 **すぐに実行可能です！**

