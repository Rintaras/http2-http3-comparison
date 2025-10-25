# Docker環境でのHTTP/3実装設計

## 1. 概要

Docker環境でのHTTP/2 vs HTTP/3ベンチマークを、実機環境と同様に実現するための実装設計。

## 2. ネットワーク構成

### 2.1 Docker環境のアーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│              ホスト（macOS）                         │
│  ┌─────────────────────────────────────────────┐   │
│  │  ベンチマーク実行スクリプト (docker_benchmark.sh)│   │
│  └─────────────────────────────────────────────┘   │
│           ↓                          ↓             │
│   HTTP/2 (TCP:8444)         HTTP/3 (UDP:8443)     │
│           ↓                          ↓             │
└───────────┼──────────────────────────┼─────────────┘
            │                          │
            ↓                          ↓
    ┌───────────────────────────────────────┐
    │        Docker Bridge Network          │
    │      (protocol_net)                   │
    └───────────────────────────────────────┘
            ↑ TCP:8444                ↑ UDP:8443
            │                         │
    ┌───────┴─────────────────────────┴──────┐
    │    Network Router Container             │
    │    (Dockerfile.router_tc)               │
    │                                         │
    │  • TCP Proxy: 8444 → server:8443       │
    │  • UDP Proxy: 8443 → server:8443       │
    │  • Traffic Control (tc): 遅延・帯域制御 │
    └─────────────────────────────────────────┘
            ↓ TCP                 ↓ UDP
    ┌─────────────────────────────────────┐
    │   HTTP/3 Server Container           │
    │   (server/Dockerfile)               │
    │                                     │
    │  • HTTP/1.1 + HTTP/2 (TCP:8443)    │
    │  • HTTP/3 (QUIC/UDP:8443)          │
    │  • TLS: localhost+2証明書           │
    └─────────────────────────────────────┘
```

### 2.2 ポートマッピング

| プロトコル | ホスト | ルーター | サーバー | 用途 |
|-----------|--------|---------|---------|------|
| HTTP/2 | 8444/tcp | 8444/tcp | 8443/tcp | クライアント → ルーター（tcフィルタリング） → サーバー |
| HTTP/3 | 8443/udp | 8443/udp | 8443/udp | クライアント → ルーター（tcフィルタリング） → サーバー |

## 3. 実装パターン

### 3.1 パターンA: ホスト側直接接続（ホストにHTTP/3対応curl必須）

```bash
# HTTP/2
curl -k --http2 https://localhost:8444/1mb

# HTTP/3 
curl -k --http3 https://localhost:8443/1mb  # curl --http3サポート必須
```

**利点**: シンプル、オーバーヘッド小
**欠点**: ホスト側がHTTP/3対応curlを必須

### 3.2 パターンB: Docker コンテナ経由（推奨）

```bash
# HTTP/2（ホスト側）
curl -k --http2 https://localhost:8444/1mb

# HTTP/3（Docker ルーター経由）
docker exec network-router curl -k https://http3-server:8443/1mb
```

**利点**: 
- ホスト側にHTTP/3対応curl不要
- Docker内部ネットワークを活用
- 一貫した測定環境

**欠点**: 
- Docker exec オーバーヘッド
- コンテナ内でのURL（内部DNS: http3-server）使用

### 3.3 パターンC: ハイブリッド（現在の実装）

```bash
# HTTP/2（ホスト側 → ルーター → サーバー）
ホスト: curl -k --http2 https://localhost:8444/1mb

# HTTP/3（ホスト側 or Docker経由）
# ホスト側HTTP/3対応なし → Docker経由自動フォールバック
docker exec network-router curl -k https://http3-server:8443/1mb
```

## 4. 現在の実装（docker_benchmark.sh）

### 4.1 接続テスト

```bash
# HTTP/2テスト（ホスト側）
curl -k --http2 https://localhost:8444/ >/dev/null 2>&1

# HTTP/3テスト（Docker経由）
docker exec network-router curl -k https://http3-server:8443/ >/dev/null 2>&1
```

### 4.2 ベンチマーク実行

```bash
# HTTP/2（ホスト側）
curl -k --http2 https://localhost:8444/1mb \
  -w "%{time_total},%{speed_download},%{http_version}"

# HTTP/3（Docker経由）
docker exec network-router curl -k https://http3-server:8443/1mb \
  -w "%{time_total},%{speed_download},%{http_version}"
```

### 4.3 データ記録

```csv
timestamp,protocol,latency,iteration,time_total,speed_kbps,success,http_version
1761316186,HTTP/3,2ms,6,0.000384,0,1,0  # HTTP/3のデータ
1761316188,HTTP/2,2ms,6,0.029488,.98,1,2  # HTTP/2のデータ
```

## 5. メリットと課題

### 5.1 メリット

✅ **実機と同等の比較**
- 同一サーバー実装
- 同一ネットワーク制御（tc）
- 独立した測定フレームワーク

✅ **多環境サポート**
- ホスト側がHTTP/3対応curl不要
- Docker環境で自動的にサポート
- 柔軟な実装選択肢

### 5.2 課題と対策

| 課題 | 原因 | 対策 |
|------|------|------|
| ホスト側HTTP/3対応curl不要 | 標準curlが未対応 | Docker経由での実装 |
| Docker exec オーバーヘッド | コンテナ間通信 | プール接続・複数接続の再利用 |
| ホスト側通信フロー異なる | HTTP/2はルーター経由、HTTP/3はDocker経由 | ウォームアップ・安定化フェーズで対応 |

## 6. 測定精度の考慮

### 6.1 タイムスタンプ

```bash
# ホスト側（HTTP/2）
local ts=$(date +%s)  # ホスト時刻

# Docker経由（HTTP/3）
docker exec network-router curl ...  # Docker内部での実行
# 注: ホスト側でタイムスタンプを記録（一貫性のため）
```

### 6.2 通信フロー

**HTTP/2:**
```
ホスト → localhost:8444/tcp → ルーター:8444 → tc制御 → サーバー:8443/tcp
```

**HTTP/3:**
```
ホスト（docker exec） → ルーター → tc制御 → サーバー:8443/udp
```

### 6.3 比較の妥当性

- ✅ 同一ネットワークリソース（tc）で制御
- ✅ 同一サーバー実装
- ✅ 同一1MBペイロード
- ⚠️ クライアント実装が異なる（curl vs docker exec）
  - 対応: ウォームアップで両方を安定化

## 7. 推奨される改善

### 7.1 短期的

1. **Docker内部curl統一**
   - ルーター・サーバーコンテナ両方でcurl --http3対応版を使用
   - ホスト側のHTTP/2測定も docker exec経由で統一

2. **タイムスタンプ精密化**
   - curl の `-w "%{time_starttransfer}"` など細分化

### 7.2 長期的

1. **Go カスタムクライアント**
   - HTTP/2・HTTP/3ネイティブ実装
   - プール接続・再利用
   - 精密なタイミング測定

2. **専用ベンチマークツール**
   - wrk、wrk2、h2load 等の活用
   - スクリプト化・自動化

## 8. まとめ

Docker環境でのHTTP/3実装は、以下の特性を持つ：

✅ **実現可能性**
- ホスト側HTTP/3対応curl不要
- Docker経由での実装で対応可能
- 実機環境と同等の測定フレームワーク

✅ **柔軟性**
- 複数実装パターン対応
- 段階的改善が容易

⚠️ **測定精度**
- HTTP/2とHTTP/3でクライアント実装が異なる点に留意
- ウォームアップ・安定化フェーズで対応
- 結果解釈時にこの点を考慮

