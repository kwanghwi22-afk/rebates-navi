"""楽天リーベイツのストア一覧ページから全ストアの還元率を取得し、履歴に追記する。

1日1回、公開ページ（robots.txt で許可されている /stores）を1リクエストだけ取得する。
"""
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STORES_URL = "https://www.rebates.jp/stores"
UA = "Mozilla/5.0 (compatible; rebates-navi/1.0; daily rate check)"
HISTORY_DAYS = 120

JST = datetime.timezone(datetime.timedelta(hours=9))


def fetch_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read().decode("utf-8")


def with_unit(text):
    """'250' や '最大1,000' のような単位なしの固定ポイントに「pt」を付ける"""
    text = (text or "").strip()
    if text and re.search(r"\d$", text):
        return text + "pt"
    return text


def parse_stores(html):
    stores = {}
    for m in re.finditer(r'\{"shoppingUrl":[^{}]*\}', html):
        try:
            o = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if o.get("status") != "active" or not o.get("link"):
            continue
        stores[o["link"]] = {
            "slug": o["link"],
            "name": o.get("name", "").strip(),
            "kana": o.get("nameKatakana", ""),
            "name_en": o.get("nameEn", ""),
            "reward": with_unit(o.get("rewardText", "")),
            "reward_was": with_unit(o.get("rewardTextWas", "")),
        }
    return stores


def reward_value(text):
    """'最大14.0%' -> (14.0, '%'), '250ポイント' -> (250, 'pt')"""
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(%|ポイント|pt)?", text or "")
    if not m:
        return None, None
    v = float(m.group(1).replace(",", ""))
    return v, ("%" if m.group(2) == "%" else "pt")


def main():
    html = fetch_html(STORES_URL)
    stores = parse_stores(html)
    if len(stores) < 200:
        # ページ構造が変わった可能性。古いデータを壊さないよう失敗させる
        sys.exit(f"取得ストア数が少なすぎます({len(stores)}件)。ページ構造の変更を確認してください。")

    today = datetime.datetime.now(JST).date().isoformat()
    hist_path = DATA / "history.json"
    history = json.loads(hist_path.read_text("utf-8")) if hist_path.exists() else {}

    for slug, s in stores.items():
        h = history.setdefault(slug, {})
        h[today] = s["reward"]
    # 古い履歴を削除
    cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=HISTORY_DAYS)).isoformat()
    for slug in list(history):
        history[slug] = {d: r for d, r in history[slug].items() if d >= cutoff}
        if not history[slug]:
            del history[slug]

    DATA.mkdir(exist_ok=True)
    (DATA / "stores.json").write_text(
        json.dumps({"updated": today, "stores": list(stores.values())}, ensure_ascii=False, indent=1), "utf-8"
    )
    hist_path.write_text(json.dumps(history, ensure_ascii=False, sort_keys=True), "utf-8")
    print(f"{today}: {len(stores)} stores")


if __name__ == "__main__":
    main()
