# リーベイツ還元率ナビ

楽天リーベイツ全ストアの還元率を毎日自動取得し、ランキング・還元率アップ情報・ストア別の推移ページを持つ静的サイトを生成します。サイト内に自分の **お友達紹介リンク** を掲載し、新規登録者からの紹介特典（1人あたり500ポイント前後）を狙う構成です。

## 仕組み

```
GitHub Actions（毎日 6:00 JST）
  └ scripts/fetch.py  … rebates.jp/stores を1回だけ取得 → data/stores.json, data/history.json に追記
  └ scripts/build.py  … site/ に HTML を生成（トップ、ストア別約1,000ページ、sitemap.xml）
  └ GitHub Pages に公開
```

外部ライブラリ不要（Python 3 標準ライブラリのみ）。

## 設定（config.json）

| 項目 | 内容 |
|---|---|
| `referral_url` | 楽天リーベイツの友達紹介リンク（https://www.rebates.jp/member/invite で取得）。空ならCTAは非表示 |
| `operator_name` | 運営者情報ページに出す名前（ニックネーム可） |
| `site_name` / `site_description` | サイト名・説明 |
| `base_url` | 独自ドメインを使う場合のみ。GitHub Pages では自動で上書きされる |

## ローカルで動かす

```bash
python3 scripts/fetch.py && python3 scripts/build.py && open site/index.html
```

## 公開手順（初回のみ）

1. GitHub で公開リポジトリ `rebates-navi` を作成し、このフォルダを push
2. リポジトリの Settings → Pages → Source を **GitHub Actions** に
3. Actions タブ → 「毎日の還元率更新」→ Run workflow
4. 公開URLを Google Search Console に登録し、`sitemap.xml` を送信

## 注意

- 紹介特典の条件や金額は楽天リーベイツ側で変わります。`referral_bonus_text` を随時合わせてください。
- 「PR」表記（ステマ規制対応）と非公式サイトである旨はテンプレートに入っています。消さないでください。
- 紹介プログラムの禁止事項（2026-10 時点）：紹介リンクURLの改変、紹介リンクを含むサイトへ誘導するための検索エンジン広告（リスティング）、企業SNSへの掲載、スパム。個人のブログ・SNSへの掲載は可。
- 取得数が200件未満になったら fetch.py は失敗して既存データを守ります。Actions の失敗通知が来たらページ構造の変更を疑ってください。
