#!/usr/bin/env python3
"""Generate docs.json for the Chinese documentation site."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_JSON = ROOT / "docs.json"
BASE_CONFIG = ROOT / "i18n" / "docs-base.json"
NAV_FILE = ROOT / "i18n" / "upstream-navigation.json"
SITE_ZH = ROOT / "i18n" / "site-zh.json"
LOCK_FILE = ROOT / ".translation-lock.json"

BASE_KEYS = (
    "$schema",
    "theme",
    "colors",
    "favicon",
    "logo",
    "appearance",
    "background",
    "footer",
    "redirects",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_nav_path(slug: str, lock: dict) -> str:
    source_key = f"{slug}.mdx"
    entry = lock.get(source_key, {})
    status = entry.get("status", "missing")
    zh_path = ROOT / "zh" / f"{slug}.mdx"

    if status == "synced" and zh_path.exists():
        return f"zh/{slug}"
    return slug


def translate_label(label: str, mapping: dict[str, str]) -> str:
    return mapping.get(label, label)


def transform_pages(pages: list, lock: dict, group_map: dict[str, str]) -> list:
    result = []
    for item in pages:
        if isinstance(item, str):
            result.append(resolve_nav_path(item, lock))
        elif isinstance(item, dict) and "group" in item:
            nested = deepcopy(item)
            nested["group"] = translate_label(nested["group"], group_map)
            nested["pages"] = transform_pages(nested["pages"], lock, group_map)
            result.append(nested)
        else:
            result.append(item)
    return result


def transform_navigation(nav: dict, lock: dict, site_zh: dict) -> dict:
    tab_map = site_zh.get("tabs", {})
    group_map = site_zh.get("groups", {})
    result = deepcopy(nav)

    if "tabs" in result:
        new_tabs = []
        for tab in result["tabs"]:
            new_tab = deepcopy(tab)
            new_tab["tab"] = translate_label(new_tab.get("tab", ""), tab_map)
            if "groups" in new_tab:
                new_groups = []
                for group in new_tab["groups"]:
                    new_group = deepcopy(group)
                    new_group["group"] = translate_label(new_group.get("group", ""), group_map)
                    new_group["pages"] = transform_pages(new_group.get("pages", []), lock, group_map)
                    new_groups.append(new_group)
                new_tab["groups"] = new_groups
            new_tabs.append(new_tab)
        result["tabs"] = new_tabs

    if "global" in site_zh:
        result["global"] = deepcopy(site_zh["global"])

    return result


def build_navbar(base_docs: dict, site_zh: dict) -> dict:
    navbar = deepcopy(base_docs.get("navbar", {}))
    overlay = site_zh.get("navbar", {})
    if "primary" in overlay and "primary" in navbar:
        navbar["primary"] = {**navbar["primary"], **overlay["primary"]}
    return navbar


def build_docs(base_docs: dict, nav: dict, lock: dict, site_zh: dict) -> dict:
    output: dict = {}
    for key in BASE_KEYS:
        if key in base_docs:
            output[key] = deepcopy(base_docs[key])

    output["name"] = site_zh.get("name", base_docs.get("name", "Chainlit"))
    output["navigation"] = transform_navigation(nav, lock, site_zh)
    output["navbar"] = build_navbar(base_docs, site_zh)

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        type=Path,
        default=BASE_CONFIG,
        help="Base config for theme/colors/logo (default: i18n/docs-base.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DOCS_JSON,
        help="Output docs.json path",
    )
    args = parser.parse_args()

    if not NAV_FILE.exists():
        raise SystemExit(
            f"Missing {NAV_FILE}. Run: python scripts/copy_upstream_nav.py"
        )

    base_docs = load_json(args.base)
    nav = load_json(NAV_FILE)
    site_zh = load_json(SITE_ZH)
    lock = load_json(LOCK_FILE) if LOCK_FILE.exists() else {}

    docs = build_docs(base_docs, nav, lock, site_zh)
    args.output.write_text(
        json.dumps(docs, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
