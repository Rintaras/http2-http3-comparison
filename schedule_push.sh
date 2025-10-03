#!/bin/bash

# 2025年11月1日にプッシュするためのスケジュールスクリプト

echo "HTTP/2 vs HTTP/3 プロトコル比較プロジェクト"
echo "============================================="
echo ""
echo "このスクリプトは2025年11月1日にGitHubにプッシュします"
echo ""

# 現在の日付を確認
current_date=$(date +%Y-%m-%d)
target_date="2025-11-01"

echo "現在の日付: $current_date"
echo "プッシュ予定日: $target_date"
echo ""

if [ "$current_date" = "$target_date" ]; then
    echo "✅ 今日はプッシュ日です！"
    echo ""
    echo "GitHubにプッシュを実行します..."
    
    # 最新の変更をコミット
    git add .
    git commit -m "Update: プロジェクト最終版

- ベンチマーク結果の追加
- 分析スクリプトの改善
- ドキュメントの更新
- 実験条件の詳細化

プッシュ日: $(date +%Y-%m-%d)"

    # GitHubにプッシュ
    echo "GitHubにプッシュ中..."
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 プッシュが完了しました！"
        echo "リポジトリURL: https://github.com/root1/protocol_comparison"
        echo ""
        echo "プロジェクトの特徴:"
        echo "- HTTP/2 vs HTTP/3 パフォーマンス比較"
        echo "- 帯域制限機能付きルーター"
        echo "- Docker環境での再現可能な実験"
        echo "- 詳細な統計分析・可視化"
        echo "- スケジューラー解析機能"
    else
        echo "❌ プッシュに失敗しました"
        exit 1
    fi
else
    echo "⏰ まだプッシュ日ではありません"
    echo "プッシュ予定日まで待機中..."
    echo ""
    echo "手動でプッシュする場合は以下を実行:"
    echo "  git push -u origin main"
    echo ""
    echo "このスクリプトを毎日実行してプッシュ日を確認できます"
fi
