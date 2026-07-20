# AHID Pilot Pipeline

Research-MVP pipeline (PRD v1.2 C11): Tier D, URL-driven, no automated discovery. Stages are built and run independently — each stage only fills in the fields it's actually responsible for, and leaves everything else `NULL` rather than guessing ahead.

## Stages

| Stage | Script | Status | What it fills in |
|---|---|---|---|
| 0. Seed | `seed_incidents.py` | **done** | Incident/source facts already established by PI review (HRL-007): dates, location, animal/harm category, involvement flags, known URLs |
| 1. Archive | *(not yet built)* | pending | Fetches each source URL, saves a snapshot + SHA-256, sets `sources_public.first_collected_at` and `availability_status` |
| 2. Dedup / source-dependency | *(not yet built)* | pending | URL canonicalization, text/media hashing, `independence_status` (three-valued, PRD v1.2 C4), `independent_cluster_id` |
| 3. Claim extraction | *(not yet built)* | pending | Populates `claims_public`; sets `official_response_found` and siblings on `incidents_public` from what sources actually document |
| 4. Scoring | *(not yet built)* | pending | `evidence_sufficiency_score`, `automation_status`, `score_version` |

Run stage 0:

```
python3 pipeline/seed_incidents.py
```

Produces `pipeline/ahid_pilot.sqlite3` (gitignored — regenerate from the script, don't commit the binary). Schema: `schema.sql`, mirrors `docs/data_dictionary.csv`.

## Known gaps after Stage 0

Five incidents have zero sources logged (seed candidates #5, #7, #8, #10, #20) — this round's search didn't turn up a directly citable primary link. Stage 1 (archiving) cannot run on these until at least one URL exists; see `docs/pipeline/candidate_incidents_seed.md` for what's missing on each.

Candidate #20's `inclusion_note` encodes a hard constraint from the PI's review: if Stage 1 still can't find a primary source, that incident's `automation_status` must not exceed `A1`, and it must not enter the public dataset export. This constraint lives in the seed data, not just in a doc, so a future scoring stage has no excuse to silently ignore it.
