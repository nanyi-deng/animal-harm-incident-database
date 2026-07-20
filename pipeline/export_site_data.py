"""Stage 5 (site build input): export the public-facing dataset to JSON for Astro.

Deliberately excludes internal-only columns that exist in incidents_public/
sources_public but aren't part of the public data_dictionary.csv schema:
seed_candidate_no, inclusion_note (PI review rationale -- not for public
consumption), needs_primary_source_verification. Also excludes is_test_case=1
rows entirely (the Zhengzhou false-report pipeline test fixture, per its own
seed note: "不计入公开数据集"). This mirrors the same public/internal
boundary the data dictionary and PRD v1.2 C2 already draw -- the site must
not accidentally surface something the schema itself marks internal.

Run: python3 pipeline/export_site_data.py [--db pipeline/ahid_pilot.sqlite3]
     [--out site/src/data/incidents.json]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

INCIDENT_PUBLIC_FIELDS = [
    "incident_id", "first_detected_at", "last_updated_at",
    "event_date_start", "event_date_end", "date_precision", "date_status",
    "province", "city", "location_precision", "location_status",
    "animal_category", "species", "estimated_animal_count",
    "juvenile_animal", "injury_status", "mortality_status", "rescue_status",
    "harm_categories", "minor_involvement", "institutional_involvement",
    "commercial_involvement", "group_involvement", "content_creation_involvement",
    "official_response_found", "police_response_found", "school_response_found",
    "ngo_response_found", "rescue_response_found", "legal_outcome_found",
    "policy_response_found", "automation_status", "evidence_sufficiency_score",
    "score_version", "ruleset_version", "model_version",
    "independent_source_cluster_count", "official_source_count",
    "contradiction_count", "disputed_flag", "misattribution_flag",
]

SOURCE_PUBLIC_FIELDS = [
    "source_id", "source_type", "source_tier", "platform", "source_name",
    "original_url", "archived_url", "publication_date", "first_collected_at",
    "language", "primary_source_status", "independence_status",
    "independent_cluster_id", "availability_status",
]

CLAIM_PUBLIC_FIELDS = [
    "claim_id", "claim_type", "claim_value", "support_status",
    "supporting_source_count", "independent_supporting_count",
    "contradicting_source_count", "confidence_category",
]


def export(db_path: Path, out_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    incidents = conn.execute(
        f"SELECT {', '.join(INCIDENT_PUBLIC_FIELDS)} FROM incidents_public "
        f"WHERE is_test_case = 0 ORDER BY incident_id"
    ).fetchall()

    out = []
    for row in incidents:
        incident = dict(row)
        incident_id = incident["incident_id"]

        sources = conn.execute(
            f"SELECT {', '.join(SOURCE_PUBLIC_FIELDS)} FROM sources_public "
            f"WHERE incident_id = ? AND availability_status = 'available' "
            f"ORDER BY source_id",
            (incident_id,),
        ).fetchall()
        # Only 'available' sources are exposed -- a source flagged unknown/removed
        # (dead links, anti-bot blocks) isn't something a site visitor can verify
        # by clicking through, so listing it as if it were a normal citation would
        # be misleading. It still exists in the pipeline DB for internal audit.
        incident["sources"] = [dict(s) for s in sources]

        claims = conn.execute(
            f"SELECT {', '.join(CLAIM_PUBLIC_FIELDS)} FROM claims_public "
            f"WHERE incident_id = ? ORDER BY claim_id",
            (incident_id,),
        ).fetchall()
        incident["claims"] = [dict(c) for c in claims]

        out.append(incident)

    conn.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    n_publishable = sum(
        1 for i in out
        if i["automation_status"] not in ("AX", "AF")
        and i["evidence_sufficiency_score"] is not None
        and i["evidence_sufficiency_score"] >= {"A1": 40, "A2": 55, "A3": 70, "A4": 85}.get(i["automation_status"], 999)
    )
    print(f"Exported {len(out)} public incidents to {out_path} "
          f"({n_publishable} meet their PRD §22.1 publication threshold; "
          f"all {len(out)} are included in the JSON regardless -- the site's "
          f"own display logic decides what to show per status, not this export)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    parser.add_argument("--out", type=Path,
                         default=Path(__file__).parent.parent / "site" / "src" / "data" / "incidents.json")
    args = parser.parse_args()
    export(args.db, args.out)
