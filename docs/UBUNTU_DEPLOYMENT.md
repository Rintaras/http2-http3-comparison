## Ubuntu 実機デプロイ手順（Docker非依存版）

このドキュメントは、Raspberry Pi 上で Docker を用いて動かしていた HTTP/2/HTTP/3 サーバー・ベンチマーク環境を、実機の Ubuntu 上でネイティブに再現するための手順をまとめたものです。

### 1. 前提条件

- Ubuntu 22.04 LTS 以上（Kernel 5.15+ 推奨）
- 権限: `sudo`、`CAP_NET_ADMIN`（`tc` 利用のため）
- 時刻同期: `chrony` を有効化（測定安定性向上）
- 開発ツール: Go 1.22+、Python 3.10+（`venv` 利用）

```bash
sudo apt update
sudo apt install -y build-essential iproute2 curl chrony python3-venv
```

### 2. リポジトリ配置とディレクトリ

リポジトリを任意のパスに配置。以下のディレクトリを使用します。

- `server/` Go サーバー実装（HTTP/1.1/2/3）
- `scripts/` ベンチ・可視化・`tc` スクリプト
- `certs/` テスト用証明書（`localhost+2.pem`, `localhost+2-key.pem`）
- `logs/` 実行結果（CSV/PNG）

### 3. 証明書

ベンチ用にテスト証明書を使用します（検証をスキップ）。本番では正規証明書と検証を必須化してください。

```bash
# 例: mkcert を利用（任意）
# mkcert -install
# mkcert localhost 127.0.0.1 ::1

cp certs/localhost+2.pem /path/to/server/
cp certs/localhost+2-key.pem /path/to/server/
chmod 600 /path/to/server/localhost+2-key.pem
```

### 4. サーバーのビルドと起動（ネイティブ）

```bash
cd server
go build -o main .

# 単体起動（8443 で HTTP/1.1/2/3）
GOMAXPROCS=1 ./main

# systemd ユニット（任意）
# /etc/systemd/system/http3-server.service
# [Unit]
# Description=HTTP/1.1/2/3 Server
# After=network.target
#
# [Service]
# WorkingDirectory=/path/to/repo/server
# ExecStart=/path/to/repo/server/main
# Restart=always
# AmbientCapabilities=CAP_NET_BIND_SERVICE
#
# [Install]
# WantedBy=multi-user.target
```

起動確認:

```bash
ss -lntup | grep 8443
```

### 5. ルータ/ネットワークエミュレーション（`tc`）

Docker の router コンテナの代替として、実機 NIC に `htb`/`netem` を直接設定します。

1) NIC 名を把握（例: `ens160`, `enp3s0` など）

```bash
ip -br link
```

2) 帯域・遅延を設定（例: 5Mbps, 50ms, 損失0%）

```bash
IF=ens160
sudo tc qdisc del dev $IF root 2>/dev/null || true
sudo tc qdisc add dev $IF root handle 1: htb default 10
sudo tc class add dev $IF parent 1: classid 1:10 htb rate 5mbit
sudo tc qdisc add dev $IF parent 1:10 handle 10: netem delay 50ms loss 0%

# 確認
tc qdisc show dev $IF
```

3) リセット

```bash
IF=ens160
sudo tc qdisc del dev $IF root || true
```

プロジェクトの `scripts/tc_setup.sh` / `scripts/tc_reset.sh` を流用する場合は、IF 名だけ Ubuntu 実機のものに書き換えて使ってください。

### 6. クライアント疎通（HTTP/2/HTTP/3）

```bash
# HTTP/2 経路（curl 7.58+ で対応）
curl -sk --http2 https://<server-ip>:8443/1mb -o /dev/null -w 'H2 %{time_total}s\n'

# HTTP/3 経路（nghttp3 対応の新しめの curl が必要）
curl -sk --http3 https://<server-ip>:8443/1mb -o /dev/null -w 'H3 %{time_total}s\n'
```

ベンチ時はクライアント/サーバー双方で `InsecureSkipVerify` 有効（テスト証明書のため）。本番では無効化し、正規 CA で検証してください。

### 7. ベンチマーク実行（実機版）

`scripts/benchmark_latency.sh` は Docker Compose を前提とした実装です。実機では以下方針に変更してください。

- `docker-compose` 呼び出しを削除し、`tc_setup/reset` を直接呼ぶ
- `ITERATIONS=100`、遅延条件 `[0, 50, 100, 150]ms` を維持
- 結果は `logs/<timestamp>/benchmark_results.csv` に保存

擬似コード（編集イメージ）:

```bash
# 例: 実機向け run_benchmark 実装断片
IF=ens160
for LAT in 0ms 50ms 100ms 150ms; do
  sudo bash scripts/tc_reset.sh $IF
  sudo bash scripts/tc_setup.sh $IF 5mbit $LAT 0%
  # HTTP/3 側: Go クライアント or curl --http3
  # HTTP/2 側: curl --http2
  # CSV に追記
done
```

### 8. 可視化とレポート

Python 仮想環境を使用します。

```bash
python3 -m venv venv
source venv/bin/activate
pip install -U pandas matplotlib seaborn

export BENCHMARK_CSV=logs/<ts>/benchmark_results.csv
export BENCHMARK_OUTPUT_DIR=logs/<ts>
python3 scripts/visualize_response_time.py
python3 scripts/visualize_stability.py
python3 scripts/visualize_results.py
```

出力物:

- `benchmark_visualization.png`（6面比較）
- `stability_comparison_comprehensive.png`（標準偏差/パーセンタイル/CV）
- `stability_percentile_range.png`（P5–P95 のみ）
- `benchmark_analysis.png`（詳細グラフ）

### 9. 測定安定化のための推奨設定

- CPU ピニング: `taskset -c 0 ./main`（クライアントも同様）
- Go スレッド数: `GOMAXPROCS=1`（一貫性重視）
- Go GC 停止（ベンチのみ）: `debug.SetGCPercent(-1)`
- 優先度: `sudo chrt -f 10 <pid>` or `nice -n -10`（必要に応じて）
- CPU 周波数固定: `sudo apt install cpufrequtils && sudo cpufreq-set -g performance`
- IPv6 無効化（任意）: `sysctl` で `net.ipv6.conf.all.disable_ipv6=1`
- ファイアウォール: `ufw allow 8443/tcp` `ufw allow 8443/udp`

### 10. セキュリティ注意

- ベンチでは `InsecureSkipVerify: true` を使用していますが、本番では**必ず無効化**し、正規証明書と検証を行ってください。
- 秘密鍵は 600、所有者限定で管理。バックアップポリシーを定義。

### 11. トラブルシューティング

- `curl --http3` が失敗: curl のバージョンと nghttp3/openssl3 の対応を確認
- `tc` が効かない: NIC 名が誤っていないか、root 権限で実行しているか確認
- 速度が期待より低い: CPU 周波数スケーリング、電源設定、IRQ バランスを見直し
- グラフが文字化け: `visualize_*.py` は日本語フォント自動検出に対応済み（DejaVu Sans フォールバック）

### 12. 最小動作確認コマンド（抜粋）

```bash
# サーバー起動
cd server && GOMAXPROCS=1 ./main

# ルータ設定（5Mbps, 50ms）
IF=ens160; sudo tc qdisc del dev $IF root 2>/dev/null || true
sudo tc qdisc add dev $IF root handle 1: htb default 10
sudo tc class add dev $IF parent 1: classid 1:10 htb rate 5mbit
sudo tc qdisc add dev $IF parent 1:10 handle 10: netem delay 50ms loss 0%

# 疎通
curl -sk --http2 https://<server-ip>:8443/1mb -o /dev/null -w '%{time_total}\n'
curl -sk --http3 https://<server-ip>:8443/1mb -o /dev/null -w '%{time_total}\n'

# 可視化（最新ログ）
source venv/bin/activate
TS=$(ls -t logs | head -1)
BENCHMARK_CSV=logs/$TS/benchmark_results.csv BENCHMARK_OUTPUT_DIR=logs/$TS \
python3 scripts/visualize_results.py
```

---

運用/自動化をご希望の場合は、`systemd` 化・NIC 固定・`tc` ラッパースクリプトの Ubuntu 向けテンプレートを追加します。必要であればお知らせください。


