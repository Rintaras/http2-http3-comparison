# ベンチマーク実装戦略: 実測的データの取得

## 問題分析

### 現状の課題

1. **Docker環境での不完全な転送**
   - 転送データサイズ: 30バイト ❌
   - 期待値: 1MB (1024 KB) ✅
   - 原因候補: ルーター設定、プロキシ、バッファサイズ

2. **遅延条件の限定**
   - 実測対象: 2/50/100/150ms のみ
   - 期待値: 0-150ms の全範囲 (151条件)

3. **実機での成功例**
   - 20251001_211526: 1MB完全転送 ✅
   - 実装: 実機サーバーのtcコマンド直接制御

---

## 実測的ベンチマークの実装方針

### 1. 実機ベンチマーク (推奨 ★★★)

**戦略**: サーバー側でのtc制御を活用

```bash
# 実機スクリプト (run_benchmark.sh)
DELAYS=($(seq 0 1 150))  # 0-150ms全範囲

for d in "${DELAYS[@]}"; do
    # サーバー側のtcを設定
    curl -sk -X POST https://192.168.1.100:8443/tc/setup \
      -H 'Content-Type: application/json' \
      -d "{\"if\":\"eth0\",\"rate\":\"5mbit\",\"delay_ms\":$d,\"loss_pct\":0}"
    
    # 測定実行
    curl --http2/--http3 https://192.168.1.100:8443/1mb
done
```

**利点**:
- ✅ 実際の1MB転送 (確認済み)
- ✅ 0-150ms全範囲対応可能
- ✅ 現実的な性能差 (5.5%)

**実装状況**: ✅ 完了 (DELAYS配列を更新予定)

---

### 2. Docker環境の改善案

#### 問題点と対策

| 問題 | 原因候補 | 対策 |
|------|---------|------|
| 転送サイズ不足 | プロキシバッファサイズ | バッファを大きくする |
| 不完全な転送 | 遅延制御による切断 | tc設定を最適化 |
| 限定的な遅延 | スクリプト仕様 | DELAYS配列を全範囲に |

#### 改善実装

**A. Docker Composeの改善**
```yaml
# ulimits を増加
ulimits:
  nofile: 65536
  nproc: 65536

# MTU を適切に設定
driver_opts:
  com.docker.network.driver.mtu: 1500
```

**B. ルーター設定の最適化**
```go
// io.Copy で完全な転送を保証
io.Copy(lw, clientConn)

// バッファサイズを動的に調整
buf := make([]byte, 1<<20)  // 1MB単位
```

**C. tc設定の改善**
```bash
# 帯域制限と遅延の同時制御
tc qdisc add dev eth0 root handle 1: htb default 1
tc class add dev eth0 parent 1: classid 1:1 htb rate 100mbit
tc qdisc add dev eth0 parent 1:1 handle 10: netem delay ${LATENCY}ms
```

---

## 実装チェックリスト

### 実機側 (優先度: 🔴 高)

- [ ] `run_benchmark.sh` の DELAYS を全範囲に変更
  ```bash
  DELAYS=($(seq 0 1 150))
  ```
- [ ] 遅延条件数の表示を更新
  ```bash
  echo "遅延条件: ${#DELAYS[@]}個 (0-150ms全範囲)"
  ```
- [ ] 実行と結果検証
  ```bash
  ./bench.sh -n 25 -p 0.1
  python3 scripts/validate_benchmark_data.py logs/latest/benchmark_results.csv
  ```

### Docker側 (優先度: 🟡 中)

- [ ] Docker Compose の ulimits 設定を追加
- [ ] `docker_benchmark.sh` の DELAYS を全範囲に変更
- [ ] ルーター設定の最適化
- [ ] テスト実行と検証

### 検証ツール (優先度: 🟢 低)

- [x] `validate_benchmark_data.py` 作成完了
- [ ] 検証基準の確立
  - 転送サイズ: 900-1150 KB (±12%)
  - 通信時間: 0.5-5 秒
  - 転送速度: 50-2000 kbps
  - 遅延条件: 100以上

---

## 実行手順

### ステップ1: 実機ベンチマーク (全遅延条件版)

```bash
# スクリプト更新後
./bench.sh -n 25 -p 0.1

# 結果検証
python3 scripts/validate_benchmark_data.py logs/latest/benchmark_results.csv
```

**期待結果**:
- ✅ 転送サイズ: ~1024 KB
- ✅ 通信時間: ~2 秒
- ✅ 遅延条件: 151個 (0-150ms)

### ステップ2: Docker環境の修正 (オプション)

```bash
# Docker Compose の改善を適用
docker-compose -f docker-compose.router_tc.yml build --no-cache

# 全遅延条件でテスト
./docker_benchmark.sh

# 結果検証
python3 scripts/validate_benchmark_data.py logs/docker_realistic_latest/benchmark_results.csv
```

---

## パフォーマンス期待値

### 実機 (0-150ms全遅延)

| 指標 | 値 |
|------|-----|
| 総データポイント数 | 7500+ |
| 遅延条件数 | 151個 |
| 平均転送サイズ | 1024 KB |
| 平均通信時間 | 2.0秒 |
| HTTP/3改善率 | 5-10% |

### Docker (改善後、理想値)

| 指標 | 値 |
|------|-----|
| 総データポイント数 | 7500+ |
| 遅延条件数 | 151個 |
| 平均転送サイズ | 900-1150 KB |
| 平均通信時間 | 1.5-3.0秒 |
| HTTP/3改善率 | 5-15% |

---

## まとめ

**最優先**: 実機での0-150ms全遅延条件実行
- 既に成功例あり (20251001)
- スクリプト修正のみで実現可能
- 実測的で信頼性高い

**次点**: Docker環境の改善
- 複数の改善ポイント
- 検証ツール準備完了
- 段階的な実装推奨

