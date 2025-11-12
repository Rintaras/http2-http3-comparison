#!/bin/bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "このスクリプトは root 権限 (sudo) で実行してください" >&2
  exit 1
fi

detect_interface() {
  local preferred=("en7" "en9")
  local active_ifaces=()

  while IFS= read -r iface; do
    [[ -z "$iface" ]] && continue
    if [[ "$iface" == en* ]]; then
      if ifconfig "$iface" 2>/dev/null | grep -q "status: active"; then
        active_ifaces+=("$iface")
      fi
    fi
  done < <(ifconfig -lu | tr ' ' '\n')

  for target in "${preferred[@]}"; do
    for iface in "${active_ifaces[@]}"; do
      if [[ "$iface" == "$target" ]]; then
        echo "$iface"
        return 0
      fi
    done
  done

  if [[ "${#active_ifaces[@]}" -gt 0 ]]; then
    echo "${active_ifaces[0]}"
    return 0
  fi

  return 1
}

REQUESTED_INTERFACE=${1:-}
LOCAL_IP=${2:-192.168.1.101}
NETMASK=${3:-255.255.255.0}
NETWORK=${4:-192.168.1.0/24}
SERVER_IP=${5:-192.168.1.100}

if [[ -n "$REQUESTED_INTERFACE" ]]; then
  INTERFACE="$REQUESTED_INTERFACE"
else
  if ! INTERFACE=$(detect_interface); then
    echo "有効なネットワークインターフェースを自動検出できませんでした。" >&2
    echo "引数でインターフェース名を指定してください: sudo $0 <interface> [local_ip] [netmask] [network/prefix] [server_ip]" >&2
    exit 1
  fi
fi

find_http3_capable_curl() {
  local candidates=(
    "/opt/homebrew/opt/curl/bin/curl"
    "/usr/local/opt/curl/bin/curl"
    "$(command -v curl 2>/dev/null || true)"
  )

  for bin in "${candidates[@]}"; do
    if [[ -x "$bin" ]] && "$bin" --version 2>/dev/null | grep -q "HTTP3"; then
      echo "$bin"
      return 0
    fi
  done

  return 1
}

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

SERVER_BASE="https://${SERVER_IP}:8443"
HTTP3_CURL=$(find_http3_capable_curl || true)
DEFAULT_CURL="$(command -v curl 2>/dev/null || true)"

echo
echo "7) HTTP通信確認"
if [[ -n "$DEFAULT_CURL" ]]; then
  set +e
  HTTP2_RAW_OUTPUT=$("$DEFAULT_CURL" -sk --http2 "$SERVER_BASE/1mb" -o /tmp/http2_1mb.bin -w "%{http_code} %{time_total} %{http_version}" 2>/dev/null)
  HTTP2_STATUS=$?
  set -e
  if [[ $HTTP2_STATUS -eq 0 ]]; then
    read -r HTTP2_CODE HTTP2_TIME HTTP2_VER <<<"$HTTP2_RAW_OUTPUT"
    echo "  HTTP/2 通信: OK (code=${HTTP2_CODE}, time=${HTTP2_TIME}s, version=${HTTP2_VER})"
  else
    echo "⚠️ HTTP/2 通信確認に失敗しました (${DEFAULT_CURL})" >&2
  fi
else
  echo "⚠️ curl コマンドが見つかりませんでした。HTTP/2 通信確認をスキップします" >&2
fi

if [[ -n "$HTTP3_CURL" ]]; then
  set +e
  HTTP3_RAW_OUTPUT=$("$HTTP3_CURL" -sk --http3 "$SERVER_BASE/1mb" -o /tmp/http3_1mb.bin -w "%{http_code} %{time_total} %{http_version}" 2>/dev/null)
  HTTP3_STATUS=$?
  set -e
  if [[ $HTTP3_STATUS -eq 0 ]]; then
    read -r HTTP3_CODE HTTP3_TIME HTTP3_VER <<<"$HTTP3_RAW_OUTPUT"
    echo "  HTTP/3 通信: OK (code=${HTTP3_CODE}, time=${HTTP3_TIME}s, version=${HTTP3_VER}, curl=${HTTP3_CURL})"
  else
    echo "⚠️ HTTP/3 通信確認に失敗しました ($HTTP3_CURL)" >&2
  fi
else
  echo "⚠️ HTTP/3 をサポートする curl が見つかりませんでした。Homebrew 版 curl のインストールを検討してください" >&2
fi

echo "=== 完了しました ==="
