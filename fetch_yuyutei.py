"""
遊々亭 デュエルマスターズの販売・買取ページからカード情報を取得し cards.json に出力する。

使い方:
  python fetch_yuyutei.py              # デフォルト: sale を取得
  python fetch_yuyutei.py --set dm01   # 指定弾のみ
  python fetch_yuyutei.py --all        # 全収録弾を巡回 (時間がかかります)
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://yuyu-tei.jp"
SET_URL = f"{BASE_URL}/{{mode}}/dm/s/{{set_code}}"
SHOP_NAME = "遊々亭"
ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT_DIR / "public" / "cards.json"
OUTPUT_PATH_ROOT = ROOT_DIR / "cards.json"
JST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": f"{BASE_URL}/",
}

PRICE_RE = re.compile(r"([\d,]+)\s*円")
SET_SKIP = {"search", "searchSP", "ultra", "special"}


class FetchError(RuntimeError):
    """取得に失敗したことを示す。原因を必ずメッセージに含める。"""


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        connect=3,
        read=3,
        backoff_factor=2.0,
        status_forcelist=(403, 408, 429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(HEADERS)
    return session


def fetch_html(session: requests.Session, url: str) -> str:
    try:
        response = session.get(url, timeout=30)
    except requests.RequestException as exc:
        raise FetchError(f"{url} への接続に失敗: {exc}") from exc

    if response.status_code != 200:
        snippet = " ".join(response.text[:300].split())
        raise FetchError(f"{url} が HTTP {response.status_code} を返しました: {snippet}")

    # Content-Type に charset があればそれを使う (apparent_encoding は大きいページで遅い)
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def parse_price(text: str) -> int | None:
    match = PRICE_RE.search(text.replace("\u00a0", " "))
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def load_known_set_codes() -> list[str]:
    """過去に取得した meta.json から収録弾一覧を読む (一覧ページ取得失敗時の保険)。"""
    for path in (OUTPUT_PATH.parent / "meta.json", OUTPUT_PATH_ROOT.parent / "meta.json"):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        codes = [str(c).strip().lower() for c in data.get("set_codes") or [] if str(c).strip()]
        if codes:
            print(f"[INFO] fallback set list from {path} ({len(codes)} sets)")
            return codes
    return []


def resolve_set_codes(session: requests.Session) -> list[str]:
    seed_url = SET_URL.format(mode="buy", set_code="sale")
    print(f"[GET] set list from {seed_url}")
    try:
        set_codes = extract_set_codes(fetch_html(session, seed_url))
    except FetchError as exc:
        print(f"[WARN] 収録弾一覧の取得に失敗: {exc}")
        set_codes = []

    if not set_codes:
        set_codes = load_known_set_codes()

    if not set_codes:
        raise FetchError(
            "収録弾一覧を取得できませんでした。"
            "遊々亭側でブロックされているか、サイト構造が変わった可能性があります。"
        )
    return set_codes


def extract_set_codes(html: str) -> list[str]:
    """収録弾チェックボックスから set code 一覧を取得する。"""
    soup = BeautifulSoup(html, "html.parser")
    codes: list[str] = []
    seen: set[str] = set()

    for checkbox in soup.select('input.versPhone[name="vers[]"], input.vers[name="vers[]"]'):
        value = (checkbox.get("value") or "").strip().lower()
        if not value or value in seen or value in SET_SKIP:
            continue
        seen.add(value)
        codes.append(value)

    return codes


def parse_cards_from_html(
    html: str,
    set_code: str,
    mode: str,
    updated_at: str,
) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards: list[dict] = []

    for section in soup.select("div.cards-list"):
        rarity_el = section.select_one("h3 span")
        section_rarity = rarity_el.get_text(strip=True) if rarity_el else ""

        for product in section.select("div.card-product"):
            card = parse_product(product, set_code, section_rarity, mode, updated_at)
            if card:
                cards.append(card)

    if not cards:
        for product in soup.select("div.card-product"):
            card = parse_product(product, set_code, "", mode, updated_at)
            if card:
                cards.append(card)

    return cards


def parse_product(
    product,
    set_code: str,
    section_rarity: str,
    mode: str,
    updated_at: str,
) -> dict | None:
    cid_el = product.select_one("input.cart_cid")
    ver_el = product.select_one("input.cart_ver")
    name_el = product.select_one("h4")
    price_el = product.select_one("strong")
    number_el = product.select_one("span.d-block.border")
    img_el = product.select_one("div.product-img img")

    card_id = (cid_el.get("value") if cid_el else "") or ""
    version = (ver_el.get("value") if ver_el else "") or set_code
    name = name_el.get_text(strip=True) if name_el else ""
    price = parse_price(price_el.get_text(" ", strip=True)) if price_el else None

    link_pattern = f'a[href*="/{mode}/dm/card/"]'
    link = product.select_one(link_pattern) or product.select_one('a[href*="/dm/card/"]')

    if not card_id or not name or price is None:
        if link and link.get("href"):
            parts = link["href"].rstrip("/").split("/")
            if len(parts) >= 2 and not card_id:
                card_id = parts[-1]
            if len(parts) >= 3 and not version:
                version = parts[-2]
        if not card_id or not name or price is None:
            return None

    number = number_el.get_text(strip=True) if number_el else ""
    rarity = section_rarity
    if not rarity and img_el and img_el.get("alt"):
        alt_parts = img_el["alt"].split()
        if len(alt_parts) >= 2:
            rarity = alt_parts[1]

    sub_parts = [p for p in (number, rarity, version.upper()) if p]
    sub_info = " / ".join(sub_parts)
    detail_url = urljoin(BASE_URL, f"/{mode}/dm/card/{version}/{card_id}")

    card: dict = {
        "id": f"{version}-{card_id}",
        "name": name,
        "sub_info": sub_info,
        "shop": SHOP_NAME,
        "updated_at": updated_at,
        "set_code": version,
        "card_id": card_id,
        "rarity": rarity,
        "number": number,
        "buy_price": None,
        "sell_price": None,
        "buy_url": None,
        "sell_url": None,
    }

    if mode == "buy":
        card["buy_price"] = price
        card["buy_url"] = detail_url
    else:
        card["sell_price"] = price
        card["sell_url"] = detail_url

    return card


def fetch_mode(
    session: requests.Session,
    set_code: str,
    mode: str,
    updated_at: str,
) -> list[dict]:
    url = SET_URL.format(mode=mode, set_code=set_code)
    print(f"[GET] {url}")
    html = fetch_html(session, url)
    cards = parse_cards_from_html(html, set_code, mode, updated_at)
    print(f"  -> {len(cards)} cards ({mode})")
    return cards


def fetch_set(session: requests.Session, set_code: str, updated_at: str, delay: float) -> list[dict]:
    buy_cards = fetch_mode(session, set_code, "buy", updated_at)
    if delay > 0:
        time.sleep(delay)
    sell_cards = fetch_mode(session, set_code, "sell", updated_at)
    return merge_cards(buy_cards + sell_cards)


def merge_cards(cards: Iterable[dict]) -> list[dict]:
    merged: dict[str, dict] = {}

    for card in cards:
        existing = merged.get(card["id"])
        if not existing:
            merged[card["id"]] = dict(card)
            continue

        for key in ("name", "sub_info", "shop", "updated_at", "set_code", "card_id", "rarity", "number"):
            if card.get(key):
                existing[key] = card[key]

        if card.get("buy_price") is not None:
            existing["buy_price"] = card["buy_price"]
            existing["buy_url"] = card.get("buy_url")
        if card.get("sell_price") is not None:
            existing["sell_price"] = card["sell_price"]
            existing["sell_url"] = card.get("sell_url")

    return list(merged.values())


def save_cards(cards: list[dict], path: Path = OUTPUT_PATH) -> None:
    output = []
    for card in cards:
        buy = card.get("buy_price")
        sell = card.get("sell_price")
        spread = None
        if buy is not None and sell is not None:
            spread = sell - buy

        output.append(
            {
                "id": card["id"],
                "name": card["name"],
                "sub_info": card["sub_info"],
                "buy_price": buy,
                "sell_price": sell,
                "spread": spread,
                "shop": card["shop"],
                "updated_at": card["updated_at"],
                "set_code": card.get("set_code"),
                "card_id": card.get("card_id"),
                "rarity": card.get("rarity"),
                "number": card.get("number"),
                "buy_url": card.get("buy_url"),
                "sell_url": card.get("sell_url"),
            }
        )

    # 見やすさのため販売価格降順 → 買取価格降順
    output.sort(
        key=lambda c: (
            c["sell_price"] is None,
            -(c["sell_price"] or 0),
            c["buy_price"] is None,
            -(c["buy_price"] or 0),
            c["name"],
        )
    )

    payload = json.dumps(output, ensure_ascii=False, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    print(f"[SAVE] {path} ({len(output)} cards)")

    if path.resolve() != OUTPUT_PATH_ROOT.resolve():
        OUTPUT_PATH_ROOT.write_text(payload, encoding="utf-8")
        print(f"[SAVE] {OUTPUT_PATH_ROOT} ({len(output)} cards)")

    save_meta(output, path.parent / "meta.json")


def save_meta(cards: list[dict], path: Path) -> None:
    updated_at = ""
    for card in cards:
        if card.get("updated_at"):
            updated_at = card["updated_at"]
            break

    rarities = sorted({c.get("rarity") for c in cards if c.get("rarity")})
    set_codes = sorted({c.get("set_code") for c in cards if c.get("set_code")})
    both = sum(1 for c in cards if c.get("buy_price") is not None and c.get("sell_price") is not None)

    meta = {
        "updated_at": updated_at,
        "count": len(cards),
        "both_price_count": both,
        "rarity_count": len(rarities),
        "set_count": len(set_codes),
        "rarities": rarities,
        "set_codes": set_codes,
        "source": "yuyutei",
        "shop": SHOP_NAME,
    }
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVE] {path}")
    root_meta = OUTPUT_PATH_ROOT.parent / "meta.json"
    if path.resolve() != root_meta.resolve():
        root_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVE] {root_meta}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="遊々亭デュエマ販売・買取データを取得して cards.json を生成")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--set",
        dest="set_code",
        default=None,
        help="取得する収録弾コード (例: dm01, dm26rp2, sale)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="全収録弾を巡回取得 (リクエスト間隔あり)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="リクエスト間隔秒 (デフォルト: 1.0)",
    )
    parser.add_argument(
        "--limit-sets",
        type=int,
        default=0,
        help="--all 時に先頭 N 弾だけ取得 (動作確認用, 0=制限なし)",
    )
    return parser.parse_args()


# 連続でこれだけ失敗したら IP ブロックとみなして中断する
MAX_CONSECUTIVE_FAILURES = 10


def main() -> None:
    args = parse_args()
    updated_at = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    all_cards: list[dict] = []

    failed_sets: list[str] = []
    consecutive_failures = 0

    with build_session() as session:
        if args.all:
            set_codes = resolve_set_codes(session)

            if args.limit_sets > 0:
                set_codes = set_codes[: args.limit_sets]

            print(f"[INFO] {len(set_codes)} sets to fetch (buy + sell)")
            for i, set_code in enumerate(set_codes, start=1):
                try:
                    all_cards.extend(fetch_set(session, set_code, updated_at, args.delay))
                    consecutive_failures = 0
                except FetchError as exc:
                    failed_sets.append(set_code)
                    consecutive_failures += 1
                    print(f"  !! skip {set_code}: {exc}")
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        raise FetchError(
                            f"{MAX_CONSECUTIVE_FAILURES} 弾連続で取得に失敗したため中断します。"
                            "アクセス元IPがブロックされている可能性が高いです。"
                            f" (成功: {i - len(failed_sets)} 弾 / 失敗: {len(failed_sets)} 弾)"
                        ) from exc
                if i < len(set_codes):
                    time.sleep(args.delay)
        else:
            set_code = args.set_code or "sale"
            all_cards = fetch_set(session, set_code, updated_at, args.delay)

    cards = merge_cards(all_cards)
    if not cards:
        raise FetchError(
            "カードを1件も取得できませんでした。"
            f" 失敗した弾: {len(failed_sets)} 件。遊々亭へのアクセスがブロックされている可能性があります。"
        )

    if failed_sets:
        print(f"[WARN] {len(failed_sets)} sets failed: {', '.join(failed_sets[:20])}")

    save_cards(cards)


if __name__ == "__main__":
    main()
