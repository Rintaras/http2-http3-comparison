#!/bin/bash

# 2025年11月1日に自動プッシュするためのcrontab設定スクリプト

echo "crontab設定スクリプト"
echo "===================="
echo ""

PROJECT_DIR="/Users/root1/Documents/Research/gRPC_over_HTTP3/protocol_comparison"
SCRIPT_PATH="$PROJECT_DIR/schedule_push.sh"

echo "プロジェクトディレクトリ: $PROJECT_DIR"
echo "スクリプトパス: $SCRIPT_PATH"
echo ""

# 2025年11月1日の午前9時に実行するcrontabエントリを作成
CRON_ENTRY="0 9 1 11 * $SCRIPT_PATH"

echo "以下のcrontabエントリを追加します:"
echo "$CRON_ENTRY"
echo ""

# 現在のcrontabをバックアップ
echo "現在のcrontabをバックアップ中..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "既存のcrontabはありません"

# 新しいcrontabエントリを追加
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ crontabにエントリを追加しました"
    echo ""
    echo "設定内容:"
    crontab -l | grep schedule_push
    echo ""
    echo "2025年11月1日 午前9:00に自動実行されます"
    echo ""
    echo "手動でテストする場合:"
    echo "  $SCRIPT_PATH"
    echo ""
    echo "crontabを確認する場合:"
    echo "  crontab -l"
    echo ""
    echo "crontabを削除する場合:"
    echo "  crontab -r"
else
    echo "❌ crontabの設定に失敗しました"
    exit 1
fi
