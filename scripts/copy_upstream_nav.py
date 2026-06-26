#!/usr/bin/env python3
"""Extract navigation from docs.json into i18n/upstream-navigation.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCS = ROOT / "docs.json"
DEFAULT_OUT = ROOT / "i18n" / "upstream-navigation.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--docs",
        type=Path,
        default=DEFAULT_DOCS,
        help="Path to docs.json (default: repo root docs.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Output path for upstream navigation snapshot",
    )
    args = parser.parse_args()

    docs = json.loads(args.docs.read_text(encoding="utf-8"))
    navigation = docs.get("navigation")
    if not navigation:
        raise SystemExit(f"No navigation key found in {args.docs}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(navigation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote navigation snapshot to {args.output}")


if __name__ == "__main__":
    main()
