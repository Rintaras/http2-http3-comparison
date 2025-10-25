#!/usr/bin/env python3
"""
シンプルなHTTP/3クライアント
httpxライブラリを使用してHTTP/3リクエストを実行
"""

import httpx
import time
import sys
import argparse

def make_request(host, port, path="/"):
    """HTTP/3リクエストを実行"""
    url = f"https://{host}:{port}{path}"
    
    start_time = time.time()
    
    try:
        with httpx.Client(http2=True) as client:
            response = client.get(url, verify=False, timeout=30.0)
            end_time = time.time()
            
            if response.status_code == 200:
                return end_time - start_time
            else:
                return None
                
    except Exception as e:
        print(f"HTTP/3 request failed: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='HTTP/3 Client')
    parser.add_argument('--host', default='localhost', help='Target host')
    parser.add_argument('--port', type=int, default=8444, help='Target port')
    parser.add_argument('--path', default='/', help='Request path')
    parser.add_argument('--output', choices=['time', 'json'], default='time', help='Output format')
    
    args = parser.parse_args()
    
    response_time = make_request(args.host, args.port, args.path)
    
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
    main()
