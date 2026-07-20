"""Stage 4: evidence sufficiency scoring and automation_status.

Implements PRD §20 (scoring) and PRD v1.2 C4 (status determined by RULE
CONDITIONS, score only gates publication -- the two systems don't derive
each other). This is a deterministic rule/arithmetic engine, not a model
call, consistent with PRD §27.5 ("规则引擎而非LLM决定发布"). score_version
is stamped 'v0-pilot-uncalibrated' throughout -- PRD §20.2's point weights
are the initial, unvalidated PRD values; calibrating them against the
Stage-8 human gold-standard audit is future work, not something this pilot
can do with 19 incidents and zero audited labels yet.

Two fields this script backfills before scoring, because nothing upstream
had a reason to set them yet:
  - incidents_public.location_status: derived 1:1 from location_precision
    (district->district_supported, etc.) -- a deliberate simplification,
    not independent verification. Documented, not hidden.
  - incidents_public.official_source_count: COUNT of archived sources_public
    rows with source_tier='1' per incident.

The independent-sources scoring dimension (PRD §20.2, 0-20 points, the
single highest-weighted dimension) does NOT use Stage 2's raw
independent_source_cluster_count at face value. That count treats every
standalone 'unknown'-independence source as its own full cluster, which is
correct for *counting distinct information threads* but would overstate
confidence if fed directly into a score dimension that's explicitly about
"真正独立" (genuinely independent) sources -- Stage 2 deliberately never
confirms independence, only rules out dependence. So here, a cluster that
Stage 2 actually merged (proven dependent via citation/near-dup evidence)
counts as 1.0 confirmed unit; a standalone source Stage 2 could only mark
'unknown' counts as 0.5 (per the discount already proposed in
methodology.md §4). This means most of this pilot's 2-source incidents cap
out around 1.0 effective unit rather than 2 -- lower than raw cluster count
would suggest, and that's intentional: it reflects what Stage 2 actually
established, not what a naive count implies.

Run: python3 pipeline/scoring.py [--db pipeline/ahid_pilot.sqlite3]
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

SCORE_VERSION = "v0-pilot-uncalibrated"
RULESET_VERSION = "prd-v1.2-C4"

PUBLICATION_THRESHOLDS = {"A1": 40, "A2": 55, "A3": 70, "A4": 85}

LOCATION_PRECISION_TO_STATUS = {
    "district": "district_supported",
    "city": "city_supported",
    "province": "province_supported",
    "unknown": "unknown",
}

DATE_STATUS_POINTS = {  # of 15
    "officially_reported": 15, "metadata_supported": 13, "multiple_sources_supported": 13,
    "claimed_only": 6, "unknown": 2, "contradicted": 0,
}
LOCATION_STATUS_POINTS = {  # of 15
    "district_supported": 15, "city_supported": 11, "province_supported": 7,
    "claimed_only": 4, "unknown": 1, "contradicted": 0,
}
SOURCE_TIER_POINTS = {"1": 15, "2": 10, "3": 6, "4": 2}  # of 15, "原始来源" dimension


def backfill_missing_fields(conn: sqlite3.Connection) -> None:
    for precision, status in LOCATION_PRECISION_TO_STATUS.items():
        conn.execute(
            "UPDATE incidents_public SET location_status = ? "
            "WHERE location_precision = ? AND location_status IS NULL",
            (status, precision),
        )
    conn.execute("""
        UPDATE incidents_public SET official_source_count = (
            SELECT COUNT(*) FROM sources_public s
            WHERE s.incident_id = incidents_public.incident_id
              AND s.source_tier = '1' AND s.availability_status = 'available'
        )
        WHERE official_source_count IS NULL
    """)


def independent_source_dimension_points(conn: sqlite3.Connection, incident_id: str) -> tuple[float, float]:
    """Returns (points out of 20, effective_units) for the highest-weighted dimension.

    Filters to availability_status='available' -- a source Stage 1 flagged as a
    soft-404 or anti-bot block still gets a cluster_id from Stage 2 (that's a
    fair reflection of "we couldn't determine its relationship to anything"),
    but it must not earn scoring credit here as if it were a verified,
    content-bearing corroborating source. Caught on the first scoring run: two
    incidents (#22 Xuzhou, #28 highway abandonment) each had one blocked source
    still counting toward their independent-sources score, inflating both past
    what the actually-available evidence supports.
    """
    clusters = conn.execute(
        "SELECT independent_cluster_id, COUNT(*) FROM sources_public "
        "WHERE incident_id = ? AND independent_cluster_id IS NOT NULL "
        "AND availability_status = 'available' "
        "GROUP BY independent_cluster_id",
        (incident_id,),
    ).fetchall()
    effective_units = sum(1.0 if size > 1 else 0.5 for _, size in clusters)
    if effective_units >= 3:
        points = 20
    elif effective_units >= 2:
        points = 15
    elif effective_units >= 1:
        points = 9
    elif effective_units > 0:
        points = 4
    else:
        points = 0
    return points, effective_units


def score_incident(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    incident_id = row["incident_id"]

    # All three queries below filter to availability_status='available', not just
    # first_collected_at IS NOT NULL -- a soft-404 or anti-bot-blocked fetch still
    # sets first_collected_at (Stage 1 got *a* response), but it isn't real,
    # usable content and must not earn scoring credit. See the docstring on
    # independent_source_dimension_points for the bug this fixes.
    best_tier = conn.execute(
        "SELECT MIN(source_tier) FROM sources_public WHERE incident_id = ? AND availability_status = 'available'",
        (incident_id,),
    ).fetchone()[0]
    primary_source_pts = SOURCE_TIER_POINTS.get(best_tier, 0)

    n_archived = conn.execute(
        "SELECT COUNT(*) FROM sources_public WHERE incident_id = ? AND availability_status = 'available'",
        (incident_id,),
    ).fetchone()[0]
    media_preservation_pts = 8 if n_archived >= 1 else 0  # of 10 -- see module docstring

    date_pts = DATE_STATUS_POINTS.get(row["date_status"], 0)
    location_pts = LOCATION_STATUS_POINTS.get(row["location_status"], 0)
    independent_pts, effective_units = independent_source_dimension_points(conn, incident_id)
    authoritative_pts = 15 if row["official_response_found"] == 1 else 0  # of 15
    animal_outcome_pts = 5 if row["mortality_status"] not in (None, "unknown") or \
        row["rescue_status"] not in (None, "unknown") else 0  # of 5
    consistency_pts = 0 if row["disputed_flag"] == 1 else 5  # of 5

    total = (primary_source_pts + media_preservation_pts + date_pts + location_pts +
             independent_pts + authoritative_pts + animal_outcome_pts + consistency_pts)
    total = max(0, min(100, total))  # PRD §20.3: floor at 0; ceiling implicit at 100

    return dict(
        total=total, effective_units=effective_units,
        breakdown=dict(primary_source=primary_source_pts, media_preservation=media_preservation_pts,
                        date=date_pts, location=location_pts, independent_sources=independent_pts,
                        authoritative_record=authoritative_pts, animal_outcome=animal_outcome_pts,
                        consistency=consistency_pts),
    )


def determine_status(row: sqlite3.Row, effective_units: float, n_sources: int) -> str:
    # Order matters: AF > AX > A4 > A3 > A2 > A1. No incident in this pilot is AF
    # (misattributed) -- all 19 are Tier-D-verified real events, not viral-video
    # misattribution cases -- so that branch never fires here but is kept for
    # when Stage 0 seeds ever include an AF-flagged candidate.
    if row["misattribution_flag"] == 1:
        return "AF"
    if row["disputed_flag"] == 1:
        return "AX"
    if row["official_response_found"] == 1:
        return "A4"
    if effective_units >= 2.0:
        return "A3"
    if n_sources >= 2:
        return "A2"
    return "A1"


def run(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(open(Path(__file__).parent / "schema.sql", encoding="utf-8").read())

    backfill_missing_fields(conn)
    conn.commit()

    rows = conn.execute("SELECT * FROM incidents_public").fetchall()
    results = []
    for row in rows:
        incident_id = row["incident_id"]
        scoring = score_incident(conn, row)
        n_sources = conn.execute(
            "SELECT COUNT(*) FROM sources_public WHERE incident_id = ? AND availability_status = 'available'",
            (incident_id,),
        ).fetchone()[0]
        status = determine_status(row, scoring["effective_units"], n_sources)
        publishable = scoring["total"] >= PUBLICATION_THRESHOLDS[status] if status not in ("AX", "AF") else False
        # AX/AF pages publish under their own PRD-defined rules (dispute/correction
        # pages), not the A1-A4 score thresholds -- not modeled here, left False
        # rather than silently applying an A-tier threshold that doesn't apply.

        conn.execute(
            "UPDATE incidents_public SET evidence_sufficiency_score = ?, automation_status = ?, "
            "score_version = ?, ruleset_version = ? WHERE incident_id = ?",
            (scoring["total"], status, SCORE_VERSION, RULESET_VERSION, incident_id),
        )
        results.append((incident_id, row["seed_candidate_no"], status, scoring["total"],
                         publishable, scoring["breakdown"]))

    conn.commit()
    conn.close()

    print(f"{'incident':<22} {'seed#':>5} {'status':>6} {'score':>5} {'publishable':>11}  breakdown")
    for incident_id, seed_no, status, total, publishable, breakdown in sorted(results, key=lambda r: r[1]):
        b = breakdown
        b_str = f"src={b['primary_source']} media={b['media_preservation']} date={b['date']} " \
                f"loc={b['location']} indep={b['independent_sources']} auth={b['authoritative_record']} " \
                f"animal={b['animal_outcome']} consist={b['consistency']}"
        print(f"{incident_id:<22} {seed_no:>5} {status:>6} {total:>5} {str(publishable):>11}  {b_str}")

    status_counts = {}
    for r in results:
        status_counts[r[2]] = status_counts.get(r[2], 0) + 1
    n_publishable = sum(1 for r in results if r[4])
    print(f"\nStatus distribution: {status_counts}")
    print(f"Publishable under PRD §22.1 thresholds: {n_publishable}/{len(results)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    args = parser.parse_args()
    run(args.db)
