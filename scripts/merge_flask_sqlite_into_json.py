#!/usr/bin/env python3
"""
Copy location (and optional stats) from the Flask app SQLite DB into
data/national_university_data.json, matching rows by school name.

Use this when you edited schools directly in data.db and want the JSON
to become the canonical backup for teammates / reseeds.

Default DB path: <project-root>/data.db (same as sqlite:///data.db when
you run `python src/app.py` from the project root).

Usage (from project root):

    python scripts/merge_flask_sqlite_into_json.py --dry-run
    python scripts/merge_flask_sqlite_into_json.py
    python scripts/merge_flask_sqlite_into_json.py --coordinates-only
    python scripts/merge_flask_sqlite_into_json.py --db /path/to/data.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_db_path() -> Path:
    root = _project_root()
    for candidate in (root / "data.db", root / "instance" / "data.db"):
        if candidate.is_file():
            return candidate
    return root / "data.db"


def _row_to_updates(row: sqlite3.Row, *, coordinates_only: bool) -> dict:
    """Only include keys we want in JSON; skip NULL columns."""
    keys: tuple[str, ...]
    if coordinates_only:
        keys = ("latitude", "longitude")
    else:
        keys = (
            "city",
            "state",
            "latitude",
            "longitude",
            "acceptance_rate",
            "tuition",
            "enrollment",
        )
    out = {}
    for k in keys:
        v = row[k]
        if v is None:
            continue
        if k == "acceptance_rate":
            out["acceptance_rate"] = float(v)
        elif k in ("tuition", "enrollment"):
            out[k] = int(v)
        elif k in ("latitude", "longitude"):
            out[k] = float(v)
        else:
            out[k] = v
    return out


def main() -> int:
    root = _project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help=f"Flask SQLite file (default: first existing of data.db or instance/data.db under {root})",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=root / "data" / "national_university_data.json",
        help="Target JSON array file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print how many schools would change, do not write",
    )
    parser.add_argument(
        "--coordinates-only",
        action="store_true",
        help="Only write latitude and longitude (skip city, state, tuition, etc.)",
    )
    args = parser.parse_args()

    db_path = args.db or _default_db_path()
    json_path = args.json

    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        print("Run the Flask app once from the project root or pass --db explicitly.", file=sys.stderr)
        return 1
    if not json_path.is_file():
        print(f"JSON not found: {json_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT name, city, state, latitude, longitude, acceptance_rate, tuition, enrollment
        FROM schools
        """
    )
    by_name: dict[str, dict] = {}
    for row in cur:
        name = row["name"]
        if not name:
            continue
        updates = _row_to_updates(row, coordinates_only=args.coordinates_only)
        if updates:
            by_name[name] = updates
    conn.close()

    with open(json_path, "r", encoding="utf-8") as f:
        schools = json.load(f)

    if not isinstance(schools, list):
        print("JSON root must be an array of school objects.", file=sys.stderr)
        return 1

    changed = 0
    for obj in schools:
        if not isinstance(obj, dict):
            continue
        name = obj.get("school_name")
        if name not in by_name:
            continue
        patch = by_name[name]
        for k, v in patch.items():
            if obj.get(k) != v:
                obj[k] = v
                changed += 1

    school_count = sum(1 for obj in schools if isinstance(obj, dict) and obj.get("school_name") in by_name)
    print(f"Matched {school_count} school(s) in JSON; {changed} field value(s) written or updated.")

    if args.dry_run:
        print("Dry run: no file written.")
        return 0

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(schools, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
