#!/usr/bin/env python3
"""
Export latitude and longitude from the Niche reviews SQLite database 
into data/national_university_data.json, matching rows by school name.

Usage (from project root):
    python scripts/export_location_from_niche.py --dry-run
    python scripts/export_location_from_niche.py
    python scripts/export_location_from_niche.py --db NicheReviewScraper/niche_reviews.sqlite
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    root = _project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=root / "NicheReviewScraper" / "niche_reviews.sqlite",
        help="Niche reviews SQLite file",
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
    args = parser.parse_args()

    db_path = args.db
    json_path = args.json

    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1
    
    if not json_path.is_file():
        print(f"JSON not found: {json_path}", file=sys.stderr)
        return 1

    # Query the Niche database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT school_name, latitude, longitude
        FROM schools
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """
    )
    
    by_name: dict[str, dict] = {}
    for row in cur:
        name = row["school_name"]
        if not name:
            continue
        by_name[name] = {
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
        }
    conn.close()

    print(f"Found {len(by_name)} schools with location data from {db_path.name}")

    # Load and update the JSON file
    with open(json_path, "r", encoding="utf-8") as f:
        schools = json.load(f)

    if not isinstance(schools, list):
        print("JSON root must be an array of school objects.", file=sys.stderr)
        return 1

    matched = 0
    updated = 0
    
    for obj in schools:
        if not isinstance(obj, dict):
            continue
        name = obj.get("school_name")
        if name not in by_name:
            continue
        
        matched += 1
        location = by_name[name]
        
        # Update latitude if not present or different
        if obj.get("latitude") != location["latitude"]:
            obj["latitude"] = location["latitude"]
            updated += 1
        
        # Update longitude if not present or different
        if obj.get("longitude") != location["longitude"]:
            obj["longitude"] = location["longitude"]
            updated += 1

    print(f"Matched {matched} school(s) in JSON; {updated} location field(s) updated/added.")

    if args.dry_run:
        print("(Dry-run mode: no changes written)")
        return 0

    # Write the updated JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(schools, f, indent=2, ensure_ascii=False)
    
    print(f"Updated {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
