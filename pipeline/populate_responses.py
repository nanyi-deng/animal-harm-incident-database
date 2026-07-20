"""Stage 3.5: decompose official_response/legal_outcome/policy_response/rescue_outcome
claims into structured responses_public rows.

This fills a real gap: data_dictionary.csv defines responses_public as one of
the four public tables, but nothing upstream ever wrote to it -- the
underlying facts were captured as free text inside claims_public instead.
Found while assembling the v0.1 Zenodo package, not before.

Method is deliberately conservative and disclosed as such: one Response row
per matching claim (not a full re-parse into multiple responders per claim,
which several claims genuinely describe -- e.g. "警方立案...学校批评教育" in
one sentence). responder_type/response_type are inferred by keyword matching
on the claim text, in a fixed priority order; when a claim clearly names
multiple responder types, only the first match in that priority order is
recorded, and the full text is preserved in summary_zh regardless so nothing
is lost, just not fully structured. Documented as a known limitation in the
v0.1 package rather than presented as fully resolved structured data.

source_id: the incident's first 'available' source, since PRD requires every
Response to trace to a Source and claims_public doesn't itself record which
specific source each claim came from.

Run: python3 pipeline/populate_responses.py [--db pipeline/ahid_pilot.sqlite3]
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

# (keyword, responder_type) in priority order -- first match wins.
RESPONDER_KEYWORDS = [
    ("法院", "court"), ("判决", "court"), ("刑初", "court"),
    ("公安", "police"), ("警方", "police"), ("派出所", "police"),
    ("教育局", "school"), ("学校", "school"), ("学院", "school"), ("大学", "school"),
    ("动物园", "company"), ("海洋馆", "company"), ("银行", "company"), ("支行", "company"),
    ("宠物店", "company"), ("托运", "company"),
    ("街道办", "government"), ("镇政府", "government"), ("市场监管", "government"),
    ("农业农村", "government"), ("城管", "government"), ("林业和草原局", "government"),
    ("志愿者", "rescue_group"), ("收容所", "rescue_group"), ("动物救助", "rescue_group"),
    ("动物福利组织", "ngo"), ("Companion Animals Working Group", "ngo"),
]

RESPONSE_TYPE_KEYWORDS = [
    ("致歉", "statement"), ("道歉", "statement"), ("声明", "statement"),
    ("开除", "penalty"), ("处分", "penalty"), ("拘留", "penalty"), ("解除劳动合同", "penalty"),
    ("停业", "penalty"), ("停职", "penalty"), ("记大过", "penalty"), ("罚款", "penalty"),
    ("有期徒刑", "penalty"), ("行政处罚", "penalty"),
    ("立案", "investigation"), ("调查", "investigation"), ("核查", "investigation"),
    ("送往", "rescue"), ("救治", "rescue"), ("收容", "rescue"), ("寄养", "rescue"),
    ("辟谣", "denial"), ("否认", "denial"), ("未发现", "denial"),
]

CLAIM_TYPE_TO_RESPONSE_TYPE_DEFAULT = {
    "legal_outcome": "filing",
    "official_response": "statement",
    "policy_response": "policy",
    "rescue_outcome": "rescue",
}

# Manual exclusions -- claims that pass the support_status='supported' filter (the
# underlying fact really is confirmed) but whose content isn't an institutional
# response at all, so forcing them into a Response row via the claim_type default
# misrepresents them. Found by scanning the 36-row output for negation markers.
#
# CLM-00129 (AHID-CN-2026-0026, the AF panda-rumor case): claim_type='rescue_outcome'
# but the text says a research program was disrupted and *no* animal harm occurred --
# there was no rescue, nothing to rescue from. The incident's real institutional
# responses (court verdict CLM-00126, legal outcome CLM-00127, official debunking
# CLM-00128) are already captured as separate claims, so excluding this one loses no
# response data -- it just stops a "no harm found" fact from being mislabeled as a
# rescue action.
EXCLUDED_CLAIM_IDS = {
    "CLM-00129": "misattribution outcome claim, not an institutional response",
}


def infer(text: str, keywords: list, default: str) -> str:
    for kw, val in keywords:
        if kw in text:
            return val
    return default


def populate(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(open(Path(__file__).parent / "schema.sql", encoding="utf-8").read())
    conn.execute("DELETE FROM responses_public")

    # support_status='supported' only -- caught by manual spot-check, not anticipated up
    # front: naive keyword matching has no concept of negation, so a claim like "未见
    # 实际立案或起诉记录" ("no filing was found") matched the "立案" keyword and got
    # structured as if a filing/investigation had happened -- backwards. Rather than try
    # to patch keyword matching with negation detection, the cleaner fix is upstream:
    # claims that are only claimed_only/unknown/contradicted don't represent a CONFIRMED
    # institutional action in the first place, so they shouldn't become a confidently-
    # structured Response row regardless of what words appear in them. Verified this
    # filter catches every case found by manual review (see commit message) without
    # needing per-row hand correction.
    claims = conn.execute(
        "SELECT claim_id, incident_id, claim_type, claim_value FROM claims_public "
        "WHERE claim_type IN ('official_response','legal_outcome','policy_response','rescue_outcome') "
        "AND support_status = 'supported' "
        "ORDER BY claim_id"
    ).fetchall()

    seq = 0
    skipped_no_source = 0
    skipped_excluded = 0
    for claim_id, incident_id, claim_type, claim_value in claims:
        if claim_id in EXCLUDED_CLAIM_IDS:
            skipped_excluded += 1
            continue
        source_row = conn.execute(
            "SELECT source_id FROM sources_public WHERE incident_id = ? "
            "AND availability_status = 'available' ORDER BY source_id LIMIT 1",
            (incident_id,),
        ).fetchone()
        if not source_row:
            skipped_no_source += 1
            continue
        source_id = source_row[0]

        responder_type = infer(claim_value, RESPONDER_KEYWORDS, "other")
        response_type = infer(
            claim_value, RESPONSE_TYPE_KEYWORDS, CLAIM_TYPE_TO_RESPONSE_TYPE_DEFAULT[claim_type]
        )

        seq += 1
        response_id = f"RSP-{seq:05d}"
        conn.execute(
            "INSERT INTO responses_public (response_id, incident_id, responder_type, "
            "response_type, source_id, summary_zh) VALUES (?, ?, ?, ?, ?, ?)",
            (response_id, incident_id, responder_type, response_type, source_id, claim_value),
        )

    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM responses_public").fetchone()[0]
    conn.close()
    print(f"Populated {n} responses_public rows from {len(claims)} source claims "
          f"({skipped_no_source} skipped -- no available source to cite, "
          f"{skipped_excluded} skipped -- manually excluded, see EXCLUDED_CLAIM_IDS)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    args = parser.parse_args()
    populate(args.db)
