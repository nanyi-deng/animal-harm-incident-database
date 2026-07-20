"""Gold-standard audit data export (methodology.md §8).

Unlike export_site_data.py (public-facing, only 'available' sources, only
public fields), this export is for the PI's own internal audit use: it
includes every source regardless of availability_status (so the auditor can
also judge whether Stage 1/2's availability and independence calls were
themselves correct), the actual extracted body text per archived source (so
the auditor has the original text to check claims against, not just AHID's
summary of it), and internal fields like inclusion_note and seed_candidate_no
for full traceability back to the review history in candidate_incidents_seed.md.

This file is NOT meant for the public site and should stay out of anything
that gets deployed -- it's audit tooling input, gitignored alongside the
database and archive snapshots it draws from.

Run: python3 pipeline/export_audit_data.py [--db pipeline/ahid_pilot.sqlite3]
     [--archive-dir pipeline/archive] [--out pipeline/audit_data.json]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dependency_analysis import extract_body_text  # noqa: E402


def export(db_path: Path, archive_dir: Path, out_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    incidents = conn.execute("SELECT * FROM incidents_public ORDER BY incident_id").fetchall()

    out = []
    for row in incidents:
        incident = dict(row)
        incident_id = incident["incident_id"]

        sources = conn.execute(
            "SELECT * FROM sources_public WHERE incident_id = ? ORDER BY source_id",
            (incident_id,),
        ).fetchall()
        source_list = []
        for s in sources:
            s = dict(s)
            snapshot = archive_dir / f"{s['source_id']}.html"
            if s["availability_status"] == "available" and snapshot.exists():
                s["extracted_text"] = extract_body_text(snapshot.read_bytes())[:4000]
            else:
                s["extracted_text"] = None
            source_list.append(s)
        incident["sources"] = source_list

        claims = conn.execute(
            "SELECT * FROM claims_public WHERE incident_id = ? ORDER BY claim_id",
            (incident_id,),
        ).fetchall()
        incident["claims"] = [dict(c) for c in claims]

        dep_log = conn.execute(
            "SELECT * FROM dependency_log WHERE incident_id = ?", (incident_id,)
        ).fetchall()
        incident["dependency_log"] = [dict(d) for d in dep_log]

        out.append(incident)

    conn.close()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(out)} incidents (full audit detail, all sources regardless of "
          f"availability, extracted text included) to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    parser.add_argument("--archive-dir", type=Path, default=Path(__file__).parent / "archive")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "audit_data.json")
    args = parser.parse_args()
    export(args.db, args.archive_dir, args.out)
