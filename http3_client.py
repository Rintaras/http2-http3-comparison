#!/usr/bin/env python3
"""
HTTP/3専用クライアント
aioquicライブラリを使用してHTTP/3リクエストを実行
"""

import asyncio
import time
import sys
import argparse
from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3_ALPN
import ssl
import logging

# ログレベルを設定
logging.basicConfig(level=logging.WARNING)

class HTTP3Client:
    def __init__(self, host, port, path="/"):
        self.host = host
        self.port = port
        self.path = path
        self.configuration = QuicConfiguration(
            alpn_protocols=H3_ALPN,
            is_client=True,
        )
        
        # SSL設定
        self.configuration.verify_mode = ssl.CERT_NONE  # 証明書検証を無効化
        
    async def request(self):
        """HTTP/3リクエストを実行"""
        start_time = time.time()
        
        try:
            async with connect(
                self.host,
                self.port,
                configuration=self.configuration,
            ) as protocol:
                # HTTP/3リクエストを送信
                stream_id = protocol.get_next_available_stream_id()
                protocol._quic.send_stream_data(
                    stream_id,
                    f"GET {self.path} HTTP/3\r\nHost: {self.host}:{self.port}\r\n\r\n".encode(),
                    end_stream=True
                )
                
                # レスポンスを待機
                await protocol.wait_closed()
                
                end_time = time.time()
                return end_time - start_time
                
        except Exception as e:
            print(f"HTTP/3 request failed: {e}", file=sys.stderr)
            return None

async def main():
    parser = argparse.ArgumentParser(description='HTTP/3 Client')
    parser.add_argument('--host', default='localhost', help='Target host')
    parser.add_argument('--port', type=int, default=8444, help='Target port')
    parser.add_argument('--path', default='/', help='Request path')
    parser.add_argument('--output', choices=['time', 'json'], default='time', help='Output format')
    
    args = parser.parse_args()
    
    client = HTTP3Client(args.host, args.port, args.path)
    response_time = await client.request()
    
    if response_time is not None:
        if args.output == 'time':
            print(f"{response_time:.6f}")
        else:
            print(f'{{"time_total": {response_time:.6f}, "success": true}}')
    else:
        if args.output == 'time':
            print("0.000000")
        else:
            print('{"time_total": 0.000000, "success": false}')

if __name__ == "__main__":
    asyncio.run(main())

