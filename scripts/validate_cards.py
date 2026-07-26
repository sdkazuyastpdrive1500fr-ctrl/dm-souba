#!/usr/bin/env python3
"""cards.json のスキーマと件数を簡易検証する。

前回 commit 済みのデータより件数が 20% 以上減っている場合はエラーにする
(取得途中でブロックされた不完全データの commit を防ぐ)。
環境変数 ALLOW_COUNT_DROP=1 で件数チェックを無効化できる。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_PATH = ROOT / "public" / "cards.json"
META_PATH = ROOT / "public" / "meta.json"

REQUIRED = {"id", "name", "sub_info", "shop", "updated_at"}
MIN_COUNT_RATIO = 0.8


def previous_count() -> int | None:
    """直前の commit に入っている meta.json の件数を返す。取れなければ None。"""
    try:
        raw = subprocess.run(
            ["git", "show", "HEAD:public/meta.json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=ROOT,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if raw.returncode != 0:
        return None
    try:
        return int(json.loads(raw.stdout).get("count"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def main() -> int:
    if not CARDS_PATH.exists():
        print(f"ERROR: {CARDS_PATH} not found", file=sys.stderr)
        return 1

    cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    if not isinstance(cards, list) or not cards:
        print("ERROR: cards.json must be a non-empty array", file=sys.stderr)
        return 1

    for i, card in enumerate(cards[:50]):
        missing = REQUIRED - set(card)
        if missing:
            print(f"ERROR: card[{i}] missing {missing}", file=sys.stderr)
            return 1
        if card.get("buy_price") is None and card.get("sell_price") is None:
            print(f"ERROR: card[{i}] has neither buy_price nor sell_price", file=sys.stderr)
            return 1

    print(f"OK: {len(cards)} cards")

    if os.environ.get("ALLOW_COUNT_DROP") != "1":
        prev = previous_count()
        if prev and len(cards) < prev * MIN_COUNT_RATIO:
            print(
                f"ERROR: card count dropped {prev} -> {len(cards)} "
                f"(less than {int(MIN_COUNT_RATIO * 100)}% of previous). "
                "Incomplete scrape? Set ALLOW_COUNT_DROP=1 to override.",
                file=sys.stderr,
            )
            return 1
        if prev:
            print(f"OK: count vs previous commit {prev} -> {len(cards)}")

    if META_PATH.exists():
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        print(f"OK: meta updated_at={meta.get('updated_at')} count={meta.get('count')}")
    else:
        print("WARN: public/meta.json not found (optional for older data)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
