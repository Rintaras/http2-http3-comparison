#!/bin/bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "このスクリプトは root 権限 (sudo) で実行してください" >&2
  exit 1
fi

INTERFACE=${1:-en9}
LOCAL_IP=${2:-192.168.1.101}
NETMASK=${3:-255.255.255.0}
NETWORK=${4:-192.168.1.0/24}
SERVER_IP=${5:-192.168.1.100}

echo "=== 実機ネットワーク設定を適用します ==="
echo "インターフェース : $INTERFACE"
echo "ローカルIP       : $LOCAL_IP / $NETMASK"
echo "ネットワーク     : $NETWORK"
echo "サーバーIP       : $SERVER_IP"
echo

echo "1) IPアドレスを設定中..."
ifconfig "$INTERFACE" inet "$LOCAL_IP" netmask "$NETMASK" up

echo "2) 既存ルートを削除..."
route -n delete -net "$NETWORK" >/dev/null 2>&1 || true

echo "3) ルートを追加..."
route -n add -net "$NETWORK" -interface "$INTERFACE"

echo "4) ARPエントリをリフレッシュ..."
arp -d "$SERVER_IP" >/dev/null 2>&1 || true

echo "5) 設定結果の確認"
ifconfig "$INTERFACE" | head -n 5
echo "---"
netstat -nr | grep "$INTERFACE" | grep "${NETWORK%%/*}" || true
echo "---"
arp -a | grep "$SERVER_IP" || echo "ARPエントリは未作成です (ping送信で登録されます)"

echo "6) 接続確認 (ping)"
if ping -c 2 -n "$SERVER_IP" >/dev/null 2>&1; then
  echo "接続確認: OK"
else
  echo "⚠️ ${SERVER_IP} へのpingに失敗しました。ケーブル接続やIP設定を確認してください" >&2
fi

echo "=== 完了しました ==="
