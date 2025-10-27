# 実機環境におけるHTTP/3クライアント設計の分析

## 1. 概要

実機環境（macOS + 有線LAN接続）でHTTP/2 vs HTTP/3の真の比較を実現するため、複数のHTTP/3クライアント実装が並行して用意されている。

## 2. クライアント実装の構成

### 2.1 ネイティブ実装の全体図

```
┌─────────────────────────────────────────────────┐
│  HTTP/2 vs HTTP/3 ベンチマーククライアント      │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  ベンチマーク実行層（Bash/Shell）        │  │
│  │  test_ubuntu_connection/run_benchmark.sh │  │
│  └──────────────────────────────────────────┘  │
│                    ↓ ↓                          │
│    ┌──────────────┐  ┌──────────────┐         │
│    │  HTTP/2      │  │  HTTP/3      │         │
│    │  クライアント │  │  クライアント │         │
│    └──────────────┘  └──────────────┘         │
│         ↓                  ↓                    │
│    curl --http2         curl --http3           │
│    (libcurl標準)        (カスタムビルド)       │
│                                                │
└─────────────────────────────────────────────────┘
```

### 2.2 実装パターン

#### パターンA: curl（標準/カスタム）
- **HTTP/2**: `curl --http2`（標準curllib対応）
- **HTTP/3**: `curl --http3`（カスタムビルド版必須）

#### パターンB: Go専用クライアント
- **実装**: `client/http3_client.go`, `client/quick_test.go`
- **ライブラリ**: `github.com/quic-go/quic-go/http3`
- **特性**: 
  - ネイティブGo実装
  - HTTP/2: `golang.org/x/net/http2`
  - HTTP/3: `quic-go` ライブラリ

#### パターンC: Python実装
- **実装**: `http3_client.py`（提案段階）
- **ライブラリ**: `aioquic`
- **状態**: Docker環境想定の試験実装

## 3. 実機でのクライアント設計（現状）

### 3.1 選択されたアプローチ

**実機環境では、cURL を用いた実装が採用されています。**

```bash
# HTTP/2
curl -sk --http2 https://192.168.1.100:8443/1mb \
  -o /dev/null \
  -w "%{time_total} %{speed_download} %{http_version}"

# HTTP/3
curl -sk --http3 https://192.168.1.100:8443/1mb \
  -o /dev/null \
  -w "%{time_total} %{speed_download} %{http_version}"
```

### 3.2 理由と実装上の考慮

| 項目 | HTTP/2 | HTTP/3 |
|------|--------|--------|
| 実装方式 | curl 標準 | curl カスタム OR Go |
| クライアント可用性 | ✓ 標準提供 | ✗ ビルド必要 |
| パフォーマンス | 優秀 | 優秀 |
| 管理容易性 | 単純 | 複雑 |

### 3.3 実装結果

**ベンチマーク結果に基づく確認:**

```csv
protocol,http_version
HTTP/3,3  ✓ HTTP/3を使用
HTTP/2,2  ✓ HTTP/2を使用
```

実機環境でHTTP/3が正常に動作していることが確認されました。

## 4. サーバーの対応

### 4.1 Go実装による統合サーバー

**`server/main.go` の設計:**

```go
// HTTP/1.1 + HTTP/2 (TLS)
httpServer := &http.Server{
    Addr: ":8443",
    TLSConfig: &tls.Config{
        Certificates: []tls.Certificate{cert},
        NextProtos:   []string{"h2", "http/1.1"},
    },
    Handler: handler,
}

// HTTP/3 (QUIC/UDP)
http3Server := &http3.Server{
    Addr: ":8443",
    TLSConfig: &tls.Config{
        Certificates: []tls.Certificate{cert},
        NextProtos:   []string{"h3", "h3-29", "h3-28", "h3-27"},
    },
    Handler: handler,
}
```

**特性:**
- 同一ポート8443で複数プロトコル対応
- TCP: HTTP/1.1, HTTP/2
- UDP: HTTP/3 (QUIC)
- Alt-Svc ヘッダーでHTTP/3広告

### 4.2 プロトコル検出メカニズム

#### ALPN (Application Layer Protocol Negotiation)

```
TLSハンドシェイク時にプロトコルをネゴシエーション

クライアント: "h2" or "h3"をサーバーに提示
    ↓
サーバー: 対応するプロトコルを選択
    ↓
確認: %{http_version} で取得
```

#### Alt-Svc (Alternative Services)

```
HTTP/2レスポンス ヘッダー:
  Alt-Svc: h3=":8443"; ma=86400

→ HTTP/3へのアップグレードを示唆
```

## 5. パフォーマンス検証結果

### 5.1 実機ベンチマーク（2/50/100/150ms遅延）

| 遅延 | HTTP/2 | HTTP/3 | 勝者 | 改善 |
|-----|--------|--------|------|------|
| 2ms | 1.778s | 1.823s | H/2 | +2.5% |
| 50ms | 1.959s | 1.918s | H/3 | -2.1% |
| 100ms | 2.216s | 2.053s | H/3 | -7.4% |
| 150ms | 2.515s | 2.209s | H/3 | -12.2% |

**結論:**
- **低遅延（<27ms）**: HTTP/2優位
- **高遅延（>27ms）**: HTTP/3優位（最大12.2%改善）
- **安定性**: HTTP/3の方が高遅延環境で安定

### 5.2 プロトコルバージョン検出の精度

```
HTTP/3指定 → http_version=3  ✓ 正確
HTTP/2指定 → http_version=2  ✓ 正確
```

完全に機能しており、複数の独立した測定から検証可能。

## 6. 実装推奨事項

### 6.1 本番環境への展開

| レイヤー | 推奨実装 | 理由 |
|----------|---------|------|
| クライアント | curl --http3 | シンプル・標準化 |
| 代替案 | Go quic-go | パフォーマンス要件時 |
| サーバー | Go + quic-go | 複数プロトコル同時対応 |

### 6.2 ビルド・デプロイ

**HTTP/3対応curl構築:**

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential git libssl-dev \
    libnghttp3-dev libngtcp2-dev

WORKDIR /tmp
RUN git clone https://github.com/curl/curl.git
WORKDIR /tmp/curl

RUN autoreconf -fi && \
    ./configure \
      --with-nghttp3 \
      --with-ngtcp2 \
      --prefix=/usr/local && \
    make -j$(nproc) install
```

### 6.3 運用上の考慮事項

1. **証明書**: 自己署名証明書は検証をスキップ（`-k`/`--insecure`）
2. **タイムアウト**: UDP（HTTP/3）は再送が必要な場合あり → `--max-time` 設定
3. **接続の再利用**: 同一接続での複数リクエストは経済的 → プール実装推奨
4. **ローカルテスト**: IPv6 (`::1`) でのリッスン検証 (`[::1]:8443`)

## 7. まとめ

実機環境でのHTTP/3クライアント設計は、以下の特性を持つ：

✅ **達成されたもの**
- HTTP/3対応クライアント（curl/Go）の並行実装
- プロトコルバージョン検出（%{http_version}）
- 複数プロトコルの同一測定フレームワーク

✅ **メリット**
- 公正な比較（同一条件・同一サーバー）
- 実際のプロトコルバージョン確認
- 高遅延環境でのHTTP/3の優位性実証

⚠️ **課題と解決策**
- curl標準がHTTP/3未対応 → カスタムビルド版・Goクライアント
- ビルド複雑性 → Docker化・事前ビルド提供
- 依存性管理 → コンテナ・venv 利用

