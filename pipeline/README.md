# AHID Pilot Pipeline

Research-MVP pipeline (PRD v1.2 C11): Tier D, URL-driven, no automated discovery. Stages are built and run independently — each stage only fills in the fields it's actually responsible for, and leaves everything else `NULL` rather than guessing ahead.

## Stages

| Stage | Script | Status | What it fills in |
|---|---|---|---|
| 0. Seed | `seed_incidents.py` | **done** | Incident/source facts already established by PI review (HRL-007): dates, location, animal/harm category, involvement flags, known URLs |
| 1. Archive | `archive_sources.py` | **done** | Fetches each source URL, saves a snapshot + SHA-256 to `archive/` (gitignored), sets `sources_public.first_collected_at` and `availability_status` |
| 2. Dedup / source-dependency | *(not yet built)* | pending — needs a design decision, see below | URL canonicalization, text/media hashing, `independence_status` (three-valued, PRD v1.2 C4), `independent_cluster_id` |
| 3. Claim extraction | *(not yet built)* | pending | Populates `claims_public`; sets `official_response_found` and siblings on `incidents_public` from what sources actually document |
| 4. Scoring | *(not yet built)* | pending | `evidence_sufficiency_score`, `automation_status`, `score_version` |

Run stages 0 and 1:

```
python3 pipeline/seed_incidents.py
python3 pipeline/archive_sources.py
```

Produces `pipeline/ahid_pilot.sqlite3` and `pipeline/archive/*.html` (both gitignored — regenerate from the scripts, never commit; the archive holds full copies of third-party news content, which PRD v1.2 C2 says never leaves the internal layer). Schema: `schema.sql`, mirrors `docs/data_dictionary.csv` plus one internal-only table (`archive_log`).

## Status after Stage 1 (2026-07-27)

19/19 incidents have at least one archived source; 29/30 source URLs archived successfully. One failure: candidate #20's secondary Dutenews link returned HTTP 405 (left as a documented gap — #20 already has its primary The Paper source archived, so this doesn't block anything). Two Zhihu links (candidates #4, #6) returned HTTP 403 on the first run and were each an incident's *only* source; a follow-up search found and swapped in primary/near-primary replacements for both (see `docs/pipeline/candidate_incidents_seed.md` and the Stage 1 commit for what changed and why, including a year correction on #4 and a name-anonymization call on #6).

Candidate #20's original `inclusion_note` set a hard constraint — no primary source found means `automation_status` cannot exceed `A1` and it never enters the public export. That constraint is now satisfied (one Tier-2 source archived) rather than removed by fiat.

## Stage 2 design note (why it isn't auto-built yet)

PRD v1.2 C4 deliberately made source independence a conservative three-valued judgment (`independent` / `dependent` / `unknown`), not something to eyeball. Doing it properly means extracting each snapshot's actual body text (the current archiver only grabs `<title>`) and comparing across sources per-incident using the citation/hash/text-overlap signals in PRD §16 — a real design choice about thresholds and what counts as "clearly the same underlying source," not a mechanical follow-on from Stages 0–1. Worth a decision on approach before it gets built, rather than improvising a heuristic silently.
