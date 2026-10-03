"""data/ の還元率データから静的サイトを site/ に生成する。"""
import html
import json
import os
import re
import shutil
from pathlib import Path

from fetch import reward_value

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "site"

cfg = json.loads((ROOT / "config.json").read_text("utf-8"))
# GitHub Actions では Pages の実URLを環境変数で渡す
BASE = (os.environ.get("SITE_BASE_URL") or cfg["base_url"]).rstrip("/")
REF = cfg.get("referral_url", "").strip()
SITE = cfg["site_name"]

e = html.escape


def safe_slug(slug):
    return re.sub(r"[^A-Za-z0-9._-]", "_", slug)


def store_href(slug, prefix=""):
    return f"{prefix}stores/{safe_slug(slug)}/"


def rebates_url(slug):
    return f"https://www.rebates.jp/{slug}"


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--text:#1d1d1f;--sub:#6b6b70;--line:#e4e4e0;--accent:#d9480f;--accent-bg:#fff4ec;--up:#c92a2a;--down:#1971c2;--btn:#d9480f;--btn-text:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1e1e21;--text:#ececef;--sub:#a0a0a8;--line:#333338;--accent:#ff8a4c;--accent-bg:#2a1d15;--up:#ff6b6b;--down:#74c0fc;--btn:#e8590c;--btn-text:#fff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.7;font-size:15px}
a{color:var(--accent)}
.wrap{max-width:880px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--line);background:var(--card)}
header .wrap{display:flex;align-items:center;justify-content:space-between;height:56px}
header a.logo{font-weight:700;color:var(--text);text-decoration:none;font-size:17px}
.pr{font-size:12px;color:var(--sub);padding:6px 0}
h1{font-size:24px;line-height:1.4;margin:24px 0 8px}
h2{font-size:19px;margin:36px 0 12px;padding-left:10px;border-left:4px solid var(--accent)}
.lead{color:var(--sub);margin:0 0 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}
.cta{background:var(--accent-bg);border-color:transparent}
.cta strong{display:block;font-size:16px;margin-bottom:4px}
.btn{display:inline-block;background:var(--btn);color:var(--btn-text);text-decoration:none;font-weight:700;padding:12px 20px;border-radius:999px;margin-top:10px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;font-size:14px}
th{font-size:12px;color:var(--sub);font-weight:600}
td.num,th.num{text-align:right;white-space:nowrap}
tr:last-child td{border-bottom:none}
td a{color:var(--text);text-decoration:none}
td a:hover{color:var(--accent)}
.rank{color:var(--sub);width:2.5em}
.up{color:var(--up);font-weight:700}
.down{color:var(--down)}
.rate-big{font-size:40px;font-weight:800;color:var(--accent);line-height:1.2}
.meta{color:var(--sub);font-size:13px}
input[type=search]{width:100%;padding:12px 14px;font-size:16px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text)}
#results{margin-top:8px}
footer{margin:48px 0 0;padding:24px 0;border-top:1px solid var(--line);font-size:12px;color:var(--sub)}
footer a{color:var(--sub)}
svg.spark{width:100%;height:120px;display:block}
.tbl-scroll{overflow-x:auto}
"""


def page(title, body, desc, path, prefix=""):
    full_title = f"{title}｜{SITE}" if title != SITE else SITE
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}/{path}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<style>{CSS}</style>
</head><body>
<header><div class="wrap"><a class="logo" href="{prefix or './'}">{e(SITE)}</a></div></header>
<div class="wrap">
<div class="pr">※本サイトはプロモーション（紹介リンク）を含みます。楽天グループ公式サイトではありません。</div>
{body}
<footer>
<p>{e(SITE)}は楽天リーベイツの公開情報を毎日自動で集計している個人運営の非公式サイトです。還元率は取得時点のもので、最新の条件・対象外商品は必ず楽天リーベイツ公式ページでご確認ください。</p>
<p><a href="{prefix}about/">運営者情報・免責事項</a></p>
</footer>
</div></body></html>"""


def referral_box():
    if not REF:
        return ""
    return f"""<div class="card cta"><strong>楽天リーベイツをまだ使っていない方へ</strong>
<span>{e(cfg["referral_bonus_text"])}がもらえます。登録は楽天会員IDでかんたん。</span><br>
<a class="btn" href="{e(REF)}" rel="sponsored noopener" target="_blank">紹介リンクから無料登録する</a></div>"""


def sparkline(points):
    """points: [(date, value)]"""
    vals = [v for _, v in points if v is not None]
    if len(vals) < 2:
        return ""
    w, h, pad = 600, 120, 10
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    n = len(points)
    coords = []
    for i, (_, v) in enumerate(points):
        if v is None:
            continue
        x = pad + (w - 2 * pad) * i / (n - 1)
        y = h - pad - (h - 2 * pad) * (v - lo) / span
        coords.append(f"{x:.1f},{y:.1f}")
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" aria-label="還元率の推移">'
            f'<polyline fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" '
            f'vector-effect="non-scaling-stroke" points="{" ".join(coords)}"/></svg>')


def main():
    data = json.loads((DATA / "stores.json").read_text("utf-8"))
    history = json.loads((DATA / "history.json").read_text("utf-8"))
    updated = data["updated"]
    stores = data["stores"]
    all_dates = sorted({d for h in history.values() for d in h})
    prev_date = all_dates[-2] if len(all_dates) >= 2 else None

    for s in stores:
        s["value"], s["unit"] = reward_value(s["reward"])
        h = history.get(s["slug"], {})
        prev = h.get(prev_date) if prev_date else None
        if not prev and s.get("reward_was"):
            prev = s["reward_was"]
        s["prev"] = prev
        pv, pu = reward_value(prev) if prev else (None, None)
        s["delta"] = (s["value"] - pv) if (pv is not None and pu == s["unit"] and s["value"] is not None) else 0
        s["is_new"] = bool(prev_date) and s["slug"] not in {k for k, v in history.items() if prev_date in v}

    pct = sorted([s for s in stores if s["unit"] == "%"], key=lambda s: -s["value"])
    fixed = sorted([s for s in stores if s["unit"] == "pt"], key=lambda s: -s["value"])
    ups = sorted([s for s in stores if s["delta"] > 0], key=lambda s: -s["delta"])
    downs = [s for s in stores if s["delta"] < 0]
    news = [s for s in stores if s["is_new"]]

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    def rows(items, show_delta=False, limit=None):
        out = []
        for i, s in enumerate(items[:limit] if limit else items, 1):
            d = ""
            if show_delta:
                d = f'<td class="num meta">{e(s["prev"] or "")} →</td>'
            out.append(f'<tr><td class="rank">{i}</td><td><a href="{store_href(s["slug"])}">{e(s["name"])}</a></td>{d}'
                       f'<td class="num{" up" if s["delta"] > 0 else ""}">{e(s["reward"])}</td></tr>')
        return "\n".join(out)

    up_html = (f'<div class="tbl-scroll"><table><tr><th></th><th>ストア</th><th class="num">前回</th><th class="num">現在</th></tr>{rows(ups, True)}</table></div>'
               if ups else '<p class="meta">前回チェック時から還元率が上がったストアはありません。</p>')
    new_html = (f'<h2>新しく追加されたストア</h2><div class="tbl-scroll"><table>{rows(news)}</table></div>' if news else "")

    search_index = json.dumps([[s["name"], s["kana"], s["name_en"], s["reward"], safe_slug(s["slug"])] for s in stores],
                              ensure_ascii=False, separators=(",", ":"))

    top = pct[0] if pct else None
    index_body = f"""
<h1>楽天リーベイツ 還元率ランキング・アップ情報（{updated}更新）</h1>
<p class="lead">楽天リーベイツ掲載の全{len(stores)}ストアの還元率を毎日チェック。{f'本日の最高還元率は「{e(top["name"])}」の{e(top["reward"])}。' if top else ''}還元率アップ中のストアは{len(ups)}件です。</p>
{referral_box()}
<h2>ストアを検索</h2>
<input type="search" id="q" placeholder="ストア名で検索（例：ユニクロ、Apple、じゃらん）" autocomplete="off">
<div id="results"></div>
<h2>本日の還元率アップ（{len(ups)}件）</h2>
{up_html}
{new_html}
<h2>還元率ランキング TOP50（%還元）</h2>
<div class="tbl-scroll"><table>{rows(pct, limit=50)}</table></div>
<h2>ポイント固定還元 TOP20</h2>
<p class="meta">サービス申込などで決まったポイントがもらえるストアです。</p>
<div class="tbl-scroll"><table>{rows(fixed, limit=20)}</table></div>
<h2>楽天リーベイツの使い方</h2>
<div class="card">
<ol>
<li>楽天リーベイツに楽天会員IDでログイン（初めての方は無料登録）</li>
<li>使いたいストアを探して「ショップへ」から公式サイトに移動</li>
<li>いつも通りお買い物をすると、還元率に応じた楽天ポイントが後日もらえる</li>
</ol>
<p class="meta">ポイント付与はストアにより数か月かかることがあります。広告ブロッカーやCookie制限があると計測されない場合があります。</p>
</div>
{referral_box()}
<script>
const D={search_index};
const q=document.getElementById('q'),r=document.getElementById('results');
const norm=s=>s.toLowerCase().normalize('NFKC').replace(/[\\u3041-\\u3096]/g,c=>String.fromCharCode(c.charCodeAt(0)+0x60));
q.addEventListener('input',()=>{{const v=norm(q.value.trim());if(!v){{r.innerHTML='';return}}
const hit=D.filter(d=>norm(d[0]+' '+d[1]+' '+d[2]).includes(v)).slice(0,30);
r.innerHTML=hit.length?'<table>'+hit.map(d=>`<tr><td><a href="stores/${{d[4]}}/"></a></td><td class="num">${{d[3]}}</td></tr>`).join('')+'</table>':'<p class="meta">見つかりませんでした</p>';
r.querySelectorAll('a').forEach((a,i)=>a.textContent=hit[i][0]);}});
</script>
"""
    (OUT / "index.html").write_text(page(SITE, index_body, cfg["site_description"], ""), "utf-8")

    # ストア個別ページ
    rank_of = {s["slug"]: i for i, s in enumerate(pct, 1)}
    for s in stores:
        h = history.get(s["slug"], {})
        dates = sorted(h)
        pts = [(d, reward_value(h[d])[0]) for d in dates]
        vals = [v for _, v in pts if v is not None]
        hist_rows = "".join(f"<tr><td>{d}</td><td class='num'>{e(h[d])}</td></tr>" for d in reversed(dates[-14:]))
        stats = ""
        if len(vals) >= 2:
            stats = (f'<p class="meta">直近{len(dates)}日間の最高：{max(vals):g}{"%" if s["unit"] == "%" else "pt"}／'
                     f'最低：{min(vals):g}{"%" if s["unit"] == "%" else "pt"}</p>')
        similar = [x for x in pct if x["slug"] != s["slug"]]
        if s["unit"] == "%" and s["value"] is not None:
            similar.sort(key=lambda x: abs(x["value"] - s["value"]))
        similar = similar[:8]
        sim_rows = "".join(f'<tr><td><a href="../{safe_slug(x["slug"])}/">{e(x["name"])}</a></td><td class="num">{e(x["reward"])}</td></tr>' for x in similar)
        rank_txt = f'（全%還元ストア中 {rank_of[s["slug"]]}位）' if s["slug"] in rank_of else ""
        change = ""
        if s["delta"] > 0:
            change = f'<p class="up">前回の{e(s["prev"])}から還元率アップ中！</p>'
        elif s["delta"] < 0:
            change = f'<p class="down">前回の{e(s["prev"])}から下がっています。</p>'
        body = f"""
<h1>{e(s["name"])}の楽天リーベイツ還元率</h1>
<div class="card">
<div class="meta">{updated}時点の還元率{rank_txt}</div>
<div class="rate-big">{e(s["reward"])}</div>
{change}
<a class="btn" href="{e(rebates_url(s["slug"]))}" rel="noopener" target="_blank">楽天リーベイツで{e(s["name"])}を見る</a>
</div>
<h2>還元率の推移</h2>
{sparkline(pts) or '<p class="meta">データを蓄積中です。毎日更新されます。</p>'}
{stats}
<div class="tbl-scroll"><table><tr><th>日付</th><th class="num">還元率</th></tr>{hist_rows}</table></div>
{referral_box()}
<h2>還元率が近いストア</h2>
<div class="tbl-scroll"><table>{sim_rows}</table></div>
"""
        desc = f"{s['name']}を楽天リーベイツ経由で利用すると{s['reward']}のポイント還元。還元率の推移を毎日記録しています（{updated}更新）。"
        d = OUT / "stores" / safe_slug(s["slug"])
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            page(f"{s['name']}の楽天リーベイツ還元率は{s['reward']}", body, desc, f"stores/{safe_slug(s['slug'])}/", "../../"), "utf-8")

    about = f"""
<h1>運営者情報・免責事項</h1>
<div class="card">
<p>運営者：{e(cfg["operator_name"])}</p>
<p>当サイトは楽天リーベイツの公開ページから還元率を1日1回自動取得し、まとめて掲載している非公式サイトです。楽天グループ株式会社とは関係ありません。</p>
<p>当サイトには楽天リーベイツの友達紹介リンクが含まれており、リンク経由で登録・購入された場合、運営者に紹介特典が付与されることがあります。</p>
<p>掲載情報の正確性には努めていますが、還元率・条件は予告なく変更されます。ご利用の際は必ず公式ページで最新情報をご確認ください。当サイトの情報により生じた損害について責任を負いかねます。</p>
</div>"""
    (OUT / "about").mkdir()
    (OUT / "about" / "index.html").write_text(page("運営者情報・免責事項", about, "運営者情報と免責事項", "about/", "../"), "utf-8")

    urls = [f"{BASE}/", f"{BASE}/about/"] + [f"{BASE}/{store_href(s['slug'])}" for s in stores]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"<url><loc>{e(u)}</loc><lastmod>{updated}</lastmod></url>" for u in urls) + "\n</urlset>\n", "utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n", "utf-8")
    (OUT / ".nojekyll").write_text("", "utf-8")
    print(f"built {len(stores)} store pages, ups={len(ups)}, downs={len(downs)}, new={len(news)}")


if __name__ == "__main__":
    main()
