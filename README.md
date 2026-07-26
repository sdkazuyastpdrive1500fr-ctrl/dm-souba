# DM相場

デュエル・マスターズの販売・買取相場検索サイト（遊々亭データ）。

- **Scraper:** Python (`fetch_yuyutei.py`)
- **Frontend:** Astro + Tailwind
- **Hosting:** Cloudflare Workers（静的）
- **公開URL:** `https://dm-souba.dm-info.workers.dev/`（ Domains で workers.dev を有効化したとき）
- **更新:** ローカルの `update_prices.bat`（タスクスケジューラ 毎日 16:00）

## ローカル開発

```powershell
# 依存関係
pip install -r requirements.txt
npm install

# データ取得（例: 1弾だけ）
python fetch_yuyutei.py --set dm01

# 全弾（時間がかかります）
python fetch_yuyutei.py --all

# サイト起動
npm run dev
```

http://127.0.0.1:4321/

## データ形式 (`public/cards.json`)

| フィールド | 説明 |
|-----------|------|
| `buy_price` / `sell_price` | 買取 / 販売価格 |
| `spread` | 販売 − 買取（片方欠ける場合は null） |
| `buy_url` / `sell_url` | 遊々亭の詳細ページ |

`public/meta.json` に最終取得日時・件数・レアリティ/弾一覧があります。

## GitHub への公開

```powershell
cd C:\Users\sdkaz\Desktop\DM-SITE
git init
git add .
git commit -m "Initial commit: DM相場 MVP"
gh repo create dm-souba --public --source=. --remote=origin --push
```

（`gh` 未ログインの場合は先に `gh auth login`）

## Cloudflare 接続

Worker 名: `dm-souba` / アカウント側サブドメイン: `dm-info`  
→ URL: `https://dm-souba.dm-info.workers.dev/`

`main` への push で自動デプロイされます。workers.dev を無効にしている間は外部から 404 になります。

## GitHub Actions

| Workflow | 内容 |
|----------|------|
| `update-prices.yml` | **スケジュール停止中**（手動 Run workflow のみ可）。通常の価格更新は `update_prices.bat` |
| `ci.yml` | push / PR で JSON 検証 + `npm run build` |

価格更新（推奨）: プロジェクト直下の `update_prices.bat` をダブルクリック

手動実行（任意）: Actions タブ → **Update prices** → **Run workflow**

初回はリポジトリ設定で Actions の write 権限が必要な場合があります（Settings → Actions → General → Workflow permissions → Read and write）。

## 検証

```powershell
python scripts/validate_cards.py
npm run build
```
