# DM相場

デュエル・マスターズの販売・買取相場検索サイト（遊々亭データ）。

- **Scraper:** Python (`fetch_yuyutei.py`)
- **Frontend:** Astro + Tailwind
- **Hosting:** Cloudflare Pages（静的）
- **更新:** GitHub Actions（1日2回）

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

## Cloudflare Pages 接続

1. [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → **Create** → **Pages** → Connect to Git
2. リポジトリを選択
3. ビルド設定:
   - **Framework preset:** Astro
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
   - **Node version:** `22`（環境変数 `NODE_VERSION=22` でも可）
4. Save and Deploy

以降、`main` への push（価格更新 Actions 含む）で自動デプロイされます。

## GitHub Actions

| Workflow | 内容 |
|----------|------|
| `update-prices.yml` | 毎日 09:00 / 21:00 JST に全弾取得 → `cards.json` を commit |
| `ci.yml` | push / PR で JSON 検証 + `npm run build` |

手動実行: Actions タブ → **Update prices** → **Run workflow**

初回はリポジトリ設定で Actions の write 権限が必要な場合があります（Settings → Actions → General → Workflow permissions → Read and write）。

## 検証

```powershell
python scripts/validate_cards.py
npm run build
```
