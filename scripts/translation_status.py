#!/usr/bin/env python3
"""Track translation status and maintain .translation-lock.json.

Hash strategy: SHA256 of the full English MDX file bytes (including frontmatter).
Using the full file ensures title-only changes are also flagged for re-translation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK_FILE = ROOT / ".translation-lock.json"


def slug_to_source(slug: str) -> Path:
    return ROOT / f"{slug}.mdx"


def slug_to_zh(slug: str) -> Path:
    return ROOT / "zh" / f"{slug}.mdx"


def source_key(source_path: Path) -> str:
    return str(source_path.relative_to(ROOT)).replace("\\", "/")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_english_mdx() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.mdx"):
        rel = path.relative_to(ROOT)
        parts = rel.parts
        if parts[0] == "zh":
            continue
        files.append(path)
    return sorted(files)


def load_lock() -> dict:
    if not LOCK_FILE.exists():
        return {}
    return json.loads(LOCK_FILE.read_text(encoding="utf-8"))


def save_lock(lock: dict) -> None:
    LOCK_FILE.write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def compute_status(source_path: Path, lock_entry: dict | None) -> str:
    if not source_path.exists():
        return "missing_source"
    current_sha = file_sha256(source_path)
    zh_path = slug_to_zh(source_path.relative_to(ROOT).with_suffix("").as_posix())

    if not zh_path.exists():
        return "missing"

    if not lock_entry:
        return "outdated"

    if lock_entry.get("source_sha") != current_sha:
        return "outdated"

    return "synced"


def refresh_lock(lock: dict | None = None) -> dict:
    lock = {} if lock is None else dict(lock)
    for source_path in iter_english_mdx():
        key = source_key(source_path)
        slug = source_path.relative_to(ROOT).with_suffix("").as_posix()
        zh_path = slug_to_zh(slug)
        entry = lock.get(key, {})
        status = compute_status(source_path, entry if entry else None)

        if status == "missing_source":
            continue

        if status == "synced":
            lock[key] = {
                "zh_path": str(zh_path.relative_to(ROOT)).replace("\\", "/"),
                "source_sha": file_sha256(source_path),
                "translated_at": entry.get("translated_at", date.today().isoformat()),
                "status": "synced",
            }
        elif status == "outdated":
            lock[key] = {
                "zh_path": str(zh_path.relative_to(ROOT)).replace("\\", "/"),
                "source_sha": entry.get("source_sha", file_sha256(source_path)),
                "translated_at": entry.get("translated_at"),
                "status": "outdated",
            }
        else:
            lock[key] = {
                "zh_path": str(zh_path.relative_to(ROOT)).replace("\\", "/"),
                "source_sha": file_sha256(source_path),
                "translated_at": None,
                "status": "missing",
            }
    return lock


def changed_since_merge() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD^", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []

    if result.returncode != 0:
        return []

    changed: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip().replace("\\", "/")
        if not line.endswith(".mdx"):
            continue
        if line.startswith("zh/"):
            continue
        changed.append(line)
    return changed


def mark_translated(zh_path: Path) -> None:
    zh_path = zh_path if zh_path.is_absolute() else ROOT / zh_path
    if not zh_path.exists():
        raise SystemExit(f"Chinese file not found: {zh_path}")

    rel = zh_path.relative_to(ROOT)
    if rel.parts[0] != "zh":
        raise SystemExit(f"Expected path under zh/: {zh_path}")

    slug = Path(*rel.parts[1:]).with_suffix("").as_posix()
    source_path = slug_to_source(slug)
    if not source_path.exists():
        raise SystemExit(f"English source not found: {source_path}")

    lock = load_lock()
    key = source_key(source_path)
    lock[key] = {
        "zh_path": str(rel).replace("\\", "/"),
        "source_sha": file_sha256(source_path),
        "translated_at": date.today().isoformat(),
        "status": "synced",
    }
    save_lock(lock)
    print(f"Marked synced: {key} -> {rel.as_posix()}")


def build_report(lock: dict, focus_files: list[str] | None = None) -> str:
    lines = ["# Translation Status Report", ""]

    buckets: dict[str, list[str]] = {
        "synced": [],
        "missing": [],
        "outdated": [],
    }

    for source_path in iter_english_mdx():
        key = source_key(source_path)
        if focus_files is not None and key not in focus_files:
            continue
        entry = lock.get(key, {})
        status = compute_status(source_path, entry if entry else None)
        if status == "missing_source":
            continue
        buckets.setdefault(status, []).append(key)

    for status in ("missing", "outdated", "synced"):
        items = buckets.get(status, [])
        lines.append(f"## {status.title()} ({len(items)})")
        lines.append("")
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("_None_")
        lines.append("")

    needs_work = len(buckets.get("missing", [])) + len(buckets.get("outdated", []))
    lines.append(f"**Pages needing translation: {needs_work}**")
    return "\n".join(lines) + "\n"


def validate_lock(lock: dict) -> list[str]:
    errors: list[str] = []
    for key, entry in lock.items():
        source_path = ROOT / key
        if not source_path.exists():
            errors.append(f"Lock references missing source: {key}")
            continue
        zh_rel = entry.get("zh_path")
        if not zh_rel:
            errors.append(f"Lock entry missing zh_path: {key}")
            continue
        if entry.get("status") == "synced" and not (ROOT / zh_rel).exists():
            errors.append(f"Synced entry missing zh file: {zh_rel}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Refresh lock for all English MDX files")
    parser.add_argument("--since-merge", action="store_true", help="Report files changed in last merge")
    parser.add_argument("--report", action="store_true", help="Print translation report to stdout")
    parser.add_argument(
        "--mark-translated",
        metavar="ZH_PATH",
        help="Mark a zh/*.mdx file as synced with its English source",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate lock consistency (exit 1 on errors)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write report to file instead of stdout",
    )
    args = parser.parse_args()

    if args.mark_translated:
        mark_translated(Path(args.mark_translated))
        return

    lock = load_lock()

    if args.all or args.since_merge or args.report or args.validate:
        lock = refresh_lock(lock)
        save_lock(lock)

    focus: list[str] | None = None
    if args.since_merge:
        focus = changed_since_merge()
        if not focus:
            focus = None

    if args.validate:
        errors = validate_lock(lock)
        if errors:
            for err in errors:
                print(err, file=sys.stderr)
            raise SystemExit(1)
        print("Lock validation passed.")
        return

    if args.report or args.since_merge or args.all:
        report = build_report(lock, focus_files=focus)
        if args.output:
            args.output.write_text(report, encoding="utf-8")
            print(f"Wrote report to {args.output}")
        else:
            print(report, end="")
        return

    if args.all:
        print(f"Refreshed lock with {len(lock)} entries.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
