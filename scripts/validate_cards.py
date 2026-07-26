#!/usr/bin/env python3
"""cards.json のスキーマを簡易検証する。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_PATH = ROOT / "public" / "cards.json"
META_PATH = ROOT / "public" / "meta.json"

REQUIRED = {"id", "name", "sub_info", "shop", "updated_at"}


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

    if META_PATH.exists():
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        print(f"OK: meta updated_at={meta.get('updated_at')} count={meta.get('count')}")
    else:
        print("WARN: public/meta.json not found (optional for older data)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
