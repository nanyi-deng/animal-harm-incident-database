"""Reshape audit_data.json into the flat ITEMS list the audit tool template expects.

Scratch/intermediate step (per the human-label-tool build process) -- keeps
data assembly separate from and auditable independently of the HTML template.

Run: python3 pipeline/prepare_audit_tool_items.py
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "audit_data.json"
OUT = HERE / "audit_tool_items.json"

INCIDENT_DISPLAY_FIELDS = [
    "province", "city", "event_date_start", "date_precision", "date_status",
    "location_precision", "location_status", "animal_category", "species",
    "estimated_animal_count", "harm_categories", "minor_involvement",
    "institutional_involvement", "mortality_status",
    "automation_status", "evidence_sufficiency_score", "score_version",
    "independent_source_cluster_count", "official_source_count",
    "disputed_flag", "misattribution_flag", "is_test_case", "inclusion_note",
]


def main():
    incidents = json.loads(SRC.read_text(encoding="utf-8"))
    items = []
    for inc in incidents:
        item = {
            "id": inc["incident_id"],
            "incident": {k: inc.get(k) for k in INCIDENT_DISPLAY_FIELDS},
            "claims": [
                {
                    "claim_type": c["claim_type"],
                    "claim_value": c["claim_value"],
                    "support_status": c["support_status"],
                    "confidence_category": c["confidence_category"],
                }
                for c in inc.get("claims", [])
            ],
            "sources": [
                {
                    "source_id": s["source_id"],
                    "source_name": s["source_name"],
                    "original_url": s["original_url"],
                    "source_tier": s["source_tier"],
                    "independence_status": s["independence_status"],
                    "independent_cluster_id": s["independent_cluster_id"],
                    "availability_status": s["availability_status"],
                    "extracted_text": s.get("extracted_text"),
                }
                for s in inc.get("sources", [])
            ],
            "dependency_log": [
                {
                    "source_id_a": d["source_id_a"],
                    "source_id_b": d["source_id_b"],
                    "text_similarity_ratio": d["text_similarity_ratio"],
                    "citation_signal": d["citation_signal"],
                    "decision": d["decision"],
                }
                for d in inc.get("dependency_log", [])
            ],
        }
        items.append(item)

    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(items)} items -> {OUT}")


if __name__ == "__main__":
    main()
