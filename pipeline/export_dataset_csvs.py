"""Zenodo v0.1 package build: export the four public tables to flat CSVs.

Distinct from export_site_data.py (which nests sources/claims per incident
into JSON for the Astro site and deliberately narrows to availability_status
='available' sources and hides internal fields for a good browsing UX). A
research dataset release has a different transparency obligation: a source
later marked 'removed' or a claim marked 'contradicted' is itself part of
the record, not noise to hide, so this export keeps every public-schema row
for every non-test incident -- nothing is filtered out except the columns
data_dictionary.csv itself marks internal-only, and the Zhengzhou pipeline
test fixture (is_test_case=1, "不计入公开数据集" per its own seed note).

This does not publish anything -- it writes CSVs to release/ahid-cn-dataset-v0.1/
data/ for the package to be assembled and reviewed locally. Actual release
(Zenodo DOI, public GitHub tag) is gated on HRL-005 (license), HRL-008
(privacy QA signoff), HRL-009 (Zenodo/ORCID account) -- see human_review_log.md.

Run: python3 pipeline/export_dataset_csvs.py [--db pipeline/ahid_pilot.sqlite3]
     [--out-dir release/ahid-cn-dataset-v0.1/data]
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

INCIDENT_FIELDS = [
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

SOURCE_FIELDS = [
    "source_id", "incident_id", "source_type", "source_tier", "platform",
    "source_name", "original_url", "archived_url", "publication_date",
    "first_collected_at", "language", "primary_source_status",
    "independence_status", "independent_cluster_id", "cites_source_id",
    "availability_status",
]

CLAIM_FIELDS = [
    "claim_id", "incident_id", "claim_type", "claim_value", "support_status",
    "supporting_source_count", "independent_supporting_count",
    "contradicting_source_count", "confidence_category",
]

RESPONSE_FIELDS = [
    "response_id", "incident_id", "responder_type", "responder_name_public",
    "response_type", "response_date", "source_id", "summary_zh", "summary_en",
]

TABLES = [
    ("incidents_public", INCIDENT_FIELDS, "incidents_public.csv"),
    ("sources_public", SOURCE_FIELDS, "sources_public.csv"),
    ("claims_public", CLAIM_FIELDS, "claims_public.csv"),
    ("responses_public", RESPONSE_FIELDS, "responses_public.csv"),
]

NON_TEST_INCIDENT_IDS = (
    "SELECT incident_id FROM incidents_public WHERE is_test_case = 0"
)


def export(db_path: Path, out_dir: Path) -> None:
    conn = sqlite3.connect(db_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = {}
    for table, fields, filename in TABLES:
        if table == "incidents_public":
            where = "WHERE is_test_case = 0"
        else:
            where = f"WHERE incident_id IN ({NON_TEST_INCIDENT_IDS})"

        rows = conn.execute(
            f"SELECT {', '.join(fields)} FROM {table} {where} ORDER BY {fields[0]}"
        ).fetchall()

        out_path = out_dir / filename
        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            writer.writerows(rows)
        counts[filename] = len(rows)

    conn.close()
    for filename, n in counts.items():
        print(f"{filename}: {n} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    parser.add_argument("--out-dir", type=Path,
                         default=Path(__file__).parent.parent / "release" / "ahid-cn-dataset-v0.1" / "data")
    args = parser.parse_args()
    export(args.db, args.out_dir)
