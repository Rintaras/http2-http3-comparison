# Git リポジトリ管理

## リポジトリ情報

- **リポジトリ名**: protocol_comparison
- **GitHub URL**: https://github.com/root1/protocol_comparison
- **プッシュ予定日**: 2025年11月1日

## 自動プッシュ設定

### 1. スケジュールスクリプト

```bash
./schedule_push.sh
```

このスクリプトは2025年11月1日に自動的にGitHubにプッシュします。

### 2. crontab設定（推奨）

```bash
./crontab_setup.sh
```

2025年11月1日 午前9:00に自動実行されるようにcrontabを設定します。

### 3. 手動プッシュ

```bash
git push -u origin main
```

いつでも手動でプッシュできます。

## プロジェクト構成

```
protocol_comparison/
├── .git/                    # Gitリポジトリ
├── .gitignore              # Git除外設定
├── README.md               # プロジェクト説明
├── README_GIT.md           # Git管理説明（このファイル）
├── schedule_push.sh        # 自動プッシュスクリプト
├── crontab_setup.sh        # crontab設定スクリプト
├── server/                 # HTTP/2/3サーバー
├── router/                 # 帯域制限ルーター
├── client/                 # ベンチマーククライアント
├── scripts/                # 分析・可視化スクリプト
├── docs/                   # ドキュメント
└── logs/                   # ベンチマーク結果（.gitignore対象）
```

## コミット履歴

1. **Initial commit** - プロジェクト初期化
2. **Add: 自動プッシュスケジュール機能** - スケジュール機能追加

## 技術スタック

- **Go 1.21** - メイン言語
- **quic-go** - HTTP/3実装
- **golang.org/x/net/http2** - HTTP/2実装
- **Docker** - コンテナ化
- **Python** - 分析・可視化
- **Git** - バージョン管理

## 注意事項

- ログファイル（`logs/`）は`.gitignore`で除外されています
- 証明書ファイル（`*.pem`）はセキュリティのため除外されています
- バイナリファイルは自動的に除外されています

## トラブルシューティング

### プッシュが失敗する場合

1. GitHub認証を確認
2. リモートリポジトリの存在を確認
3. ネットワーク接続を確認

### crontabが動作しない場合

1. crontabの設定を確認: `crontab -l`
2. スクリプトの実行権限を確認: `ls -la schedule_push.sh`
3. ログを確認: `/var/log/cron` または `journalctl`

## 今後の予定

- 2025年11月1日: 自動プッシュ実行
- 継続的な実験結果の蓄積
- ドキュメントの更新
