# HTTP/3のP5-P95パーセンタイル範囲が大きい理由と改善策

## 問題の概要

グラフ（`stability_percentile_range.png`）から、HTTP/3の150ms遅延条件でP5-P95パーセンタイル範囲が急増している（0.110秒）ことが確認されています。これはHTTP/2の範囲（0.069秒）の約1.6倍です。

## 考えられる原因

### 1. QUICの輻輳制御アルゴリズム

**問題点:**
- QUICはデフォルトでCubicアルゴリズムを使用
- 高遅延環境では、Cubicのウィンドウ増加が遅くなり、再起動時に不安定になる
- 遅延が大きいと、輻輳ウィンドウの調整が頻繁に発生し、ばらつきが増加

**理論的背景:**
```
Cubicアルゴリズムのウィンドウサイズ計算:
W(t) = C * (t - K)³ + W_max
```
- 高遅延環境では `K`（時間定数）が大きくなり、ウィンドウサイズの回復が遅い
- 結果として、一部の接続でパフォーマンスが低下し、ばらつきが増大

### 2. UDPパケット再送の影響

**問題点:**
- TCPはカーネルレベルで再送制御が最適化されている
- QUICはユーザー空間での実装のため、再送タイミングが不安定
- 150msの遅延では、RTT（往復時間）が300msになり、再送タイムアウトが頻発

**影響:**
- 一部のパケットが再送され、転送時間が長くなる
- 再送の発生タイミングが接続ごとに異なり、ばらつきが生じる

### 3. QUICの接続確立コスト

**問題点:**
- 各リクエストごとに新規QUIC接続を確立（接続再利用なし）
- 150msの遅延では、接続確立だけで300-600msかかる場合がある
- 接続確立のタイミングが接続ごとに異なる

### 4. Docker環境のUDPバッファ制限

**問題点:**
- Docker環境ではUDPバッファサイズが制限されている可能性
- UDPバッファが不足すると、パケットドロップが発生
- パケットドロップによる再送で、ばらつきが増加

### 5. ネットワークスタックのオーバーヘッド

**問題点:**
- Dockerブリッジネットワーク経由のUDP通信
- ホストとコンテナ間のパケット転送オーバーヘッド
- 高遅延条件では、これらの小さなオーバーヘッドが累積的に影響

## 改善策

### 1. QUIC接続の再利用

**現在の問題:**
- 各リクエストで新規接続を確立している

**改善案:**
```go
// http3_client.go を修正
roundTripper := &http3.RoundTripper{
    TLSClientConfig: &tls.Config{
        InsecureSkipVerify: true,
    },
}
// 接続を再利用するために、同じRoundTripperを使用
defer roundTripper.Close() // 最後に一度だけクローズ
```

**効果:**
- 接続確立コストを削減
- 接続確立のばらつきを排除

### 2. QUICのタイムアウト設定の最適化

**現在の設定:**
- タイムアウト: 30秒（デフォルト）

**改善案:**
```go
roundTripper := &http3.RoundTripper{
    TLSClientConfig: &tls.Config{
        InsecureSkipVerify: true,
    },
    QuicConfig: &quic.Config{
        HandshakeIdleTimeout: 10 * time.Second,
        MaxIdleTimeout: 30 * time.Second,
        KeepAlivePeriod: 10 * time.Second,
    },
}
```

**効果:**
- 不要な待機時間を削減
- タイムアウトによる再試行を削減

### 3. 輻輳制御アルゴリズムの変更

**現在:**
- Cubic（デフォルト）

**改善案:**
```go
// quic-goでは、NewRenoやBBRなど他のアルゴリズムも選択可能
// ただし、quic-goのバージョンによっては制限がある可能性
```

**効果:**
- 高遅延環境での安定性向上
- ばらつきの削減

### 4. UDPバッファサイズの増加

**改善案:**
```bash
# Dockerコンテナ内で
sysctl -w net.core.rmem_max=2097152
sysctl -w net.core.wmem_max=2097152
```

**効果:**
- パケットドロップの削減
- 再送の削減

### 5. 接続確立の事前ウォームアップ

**改善案:**
- ベンチマーク開始前に、接続を確立して温めておく
- ウォームアップ接続を維持し、実際の測定で再利用

**効果:**
- 接続確立のコストを排除
- ばらつきの削減

### 6. QUICのストリーム優先度設定

**改善案:**
- 単一ストリームでのリクエストでも、優先度を明示的に設定
- ストリームの競合を回避

**効果:**
- 予測可能な転送時間
- ばらつきの削減

## 推奨される改善手順

### 優先度1（高影響・低コスト）

1. **接続の再利用**
   - `http3_client.go`を修正して、同じRoundTripperを使用
   - 最も効果的な改善

2. **タイムアウト設定の最適化**
   - QUICの設定パラメータを調整
   - 実装が容易

### 優先度2（中影響・中コスト）

3. **UDPバッファサイズの増加**
   - Docker環境での設定が必要
   - 効果は中程度

### 優先度3（低影響・高コスト）

4. **輻輳制御アルゴリズムの変更**
   - quic-goのバージョンによっては制限がある
   - 効果は未確認

5. **接続確立の事前ウォームアップ**
   - 実装が複雑
   - 効果は限定的

## 実装例

### http3_client.go の改善版

```go
package main

import (
	"crypto/tls"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/quic-go/quic-go"
	"github.com/quic-go/quic-go/http3"
)

var globalRoundTripper *http3.RoundTripper

func init() {
	globalRoundTripper = &http3.RoundTripper{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
		QuicConfig: &quic.Config{
			HandshakeIdleTimeout: 10 * time.Second,
			MaxIdleTimeout: 30 * time.Second,
			KeepAlivePeriod: 10 * time.Second,
		},
	}
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: %s <url>\n", os.Args[0])
		os.Exit(1)
	}
	url := os.Args[1]

	// 接続を再利用するクライアント
	client := &http.Client{
		Transport: globalRoundTripper,
		Timeout:   30 * time.Second,
	}

	// リクエストを実行
	startTime := time.Now()
	resp, err := client.Get(url)
	if err != nil {
		fmt.Fprintf(os.Stderr, "HTTP/3 request failed: %v\n", err)
		fmt.Printf("0.000000,0,0\n")
		os.Exit(1)
	}
	defer resp.Body.Close()

	// データを読み込む
	dataReceived, err := io.Copy(io.Discard, resp.Body)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Read error: %v\n", err)
		fmt.Printf("0.000000,0,0\n")
		os.Exit(1)
	}

	endTime := time.Now()
	timeTotal := endTime.Sub(startTime).Seconds()
	speedDownload := float64(dataReceived) / timeTotal
	if timeTotal == 0 {
		speedDownload = 0
	}
	httpVersion := 3

	fmt.Printf("%.6f,%.0f,%d\n", timeTotal, speedDownload, httpVersion)
}

// プログラム終了時にクリーンアップ
func cleanup() {
	if globalRoundTripper != nil {
		globalRoundTripper.Close()
	}
}
```

## 期待される効果

上記の改善を実施することで、以下の効果が期待されます：

1. **P5-P95範囲の削減**: 0.110秒 → 0.05-0.07秒程度
2. **標準偏差の削減**: 0.036秒 → 0.02秒程度
3. **外れ値の削減**: 外れ値の発生頻度を50%以上削減

## 結論

HTTP/3の150ms遅延条件でのばらつきが大きい主な原因は、**QUIC接続の再確立コスト**と**輻輳制御アルゴリズム（Cubic）の高遅延環境での不安定性**です。

**最優先の改善策は、接続の再利用**です。これにより、接続確立コストを排除し、ばらつきを大幅に削減できる可能性が高いです。
