#!/usr/bin/env python3
"""
HTTP/3専用クライアント（curl互換出力形式）
aioquicライブラリを使用してHTTP/3リクエストを実行
curl形式: time_total,speed_download,http_version
"""

import asyncio
import time
import sys
import argparse
from aioquic.asyncio.client import connect
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import HeadersReceived, DataReceived
from aioquic.quic.configuration import QuicConfiguration
import ssl
import logging
from urllib.parse import urlparse

# ログレベルを設定
logging.basicConfig(level=logging.WARNING)

class HTTP3Client:
    def __init__(self, url):
        parsed = urlparse(url)
        self.host = parsed.hostname or 'localhost'
        self.port = parsed.port or 8443
        self.path = parsed.path or '/'
        self.configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,
            is_client=True,
        )
        
        # SSL設定
        self.configuration.verify_mode = ssl.CERT_NONE  # 証明書検証を無効化
        
    async def request(self):
        """HTTP/3リクエストを実行してcurl形式で結果を返す"""
        start_time = time.time()
        data_received = 0
        
        try:
            async with connect(
                self.host,
                self.port,
                configuration=self.configuration,
            ) as protocol:
                # H3Connectionを作成
                h3 = H3Connection(protocol._quic)
                
                # HTTP/3リクエストを送信
                stream_id = h3.get_next_available_stream_id()
                h3.send_headers(
                    stream_id=stream_id,
                    headers=[
                        (b':method', b'GET'),
                        (b':path', self.path.encode()),
                        (b':scheme', b'https'),
                        (b':authority', f'{self.host}:{self.port}'.encode()),
                    ],
                )
                h3.end_stream(stream_id)
                
                # レスポンスを待機
                response_received = False
                while True:
                    # イベント処理
                    for event in h3.handle_events():
                        if isinstance(event, HeadersReceived):
                            # ヘッダー受信
                            response_received = True
                        elif isinstance(event, DataReceived):
                            # データ受信
                            data_received += len(event.data)
                            if event.stream_ended:
                                break
                    
                    # タイムアウトチェック
                    if time.time() - start_time > 30:
                        break
                    
                    # データ受信完了
                    if response_received and data_received > 0:
                        # 少し待って追加データを確認
                        await asyncio.sleep(0.1)
                        break
                    
                    await asyncio.sleep(0.01)
                
                end_time = time.time()
                time_total = end_time - start_time
                speed_download = (data_received * 8) / time_total if time_total > 0 else 0
                http_version = 3  # HTTP/3を使用
                
                # curl形式: time_total,speed_download,http_version
                return f"{time_total:.6f},{speed_download:.0f},{http_version}"
                
        except Exception as e:
            print(f"HTTP/3 request failed: {e}", file=sys.stderr)
            return None

async def main():
    parser = argparse.ArgumentParser(description='HTTP/3 Client (curl compatible)')
    parser.add_argument('url', help='Target URL (e.g., https://http3-server:8443/)')
    
    args = parser.parse_args()
    
    client = HTTP3Client(args.url)
    result = await client.request()
    
    if result is not None:
        print(result)
        sys.exit(0)
    else:
        print("0.000000,0,0")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
