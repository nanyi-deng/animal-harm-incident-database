"""Site build input (census sub-corpus): export judgments_census.csv to JSON
for the Astro website's /census/ page.

Mirrors export_site_data.py's role for incidents_public, but for the judgment
census -- a genuinely different shape (flat table, no claims/sources/scoring,
per protocol PRD C14 and methodology.md §13). This script does not try to
force the census into the incident export's field set; it exports the
census's own fields as-is.

Run: python3 pipeline/export_census_site_data.py
     [--csv release/v0.2/judgments_census.csv]
     [--out site/src/data/census.json]
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDS = [
    "census_id", "category", "animal", "death", "n_animals", "motive",
    "summary", "charges", "fact", "confidence", "review_status",
    "animal_directly_harmed", "outcome_documented", "recovered_after_theft",
    "claim_verified", "perpetrator_confirmed", "correction_note",
]


def export(csv_path: Path, out_path: Path) -> None:
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    out = [{k: r.get(k, "") for k in FIELDS} for r in rows]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Exported {len(out)} judgment records to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path,
                         default=Path(__file__).parent.parent / "release" / "v0.2" / "judgments_census.csv")
    parser.add_argument("--out", type=Path,
                         default=Path(__file__).parent.parent / "site" / "src" / "data" / "census.json")
    args = parser.parse_args()
    export(args.csv, args.out)
