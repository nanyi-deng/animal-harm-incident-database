# AHID Pilot Pipeline

Research-MVP pipeline (PRD v1.2 C11): Tier D, URL-driven, no automated discovery. Stages are built and run independently — each stage only fills in the fields it's actually responsible for, and leaves everything else `NULL` rather than guessing ahead.

## Stages

| Stage | Script | Status | What it fills in |
|---|---|---|---|
| 0. Seed | `seed_incidents.py` | **done** | Incident/source facts already established by PI review (HRL-007): dates, location, animal/harm category, involvement flags, known URLs |
| 1. Archive | `archive_sources.py` | **done** | Fetches each source URL, saves a snapshot + SHA-256 to `archive/` (gitignored), sets `sources_public.first_collected_at` and `availability_status` |
| 2. Dedup / source-dependency | `dependency_analysis.py` | **done** | `independence_status` (`dependent`/`unknown` only — see below), `independent_cluster_id`, `incidents_public.independent_source_cluster_count` |
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

## Stage 2 results and how they were validated (2026-07-27)

`dependency_analysis.py` never assigns `independent` — per PRD v1.2 C4 that label is reserved for the human gold-standard audit (methodology.md §8). It only ever asserts `dependent` (citation match or >0.85 near-duplicate body text) or leaves `unknown`. Final run: 10 comparable source pairs (incidents with 2+ archived sources), **1 marked dependent** (candidate #4 — two sources both explicitly cite 广东海洋大学官网 as their origin), the other 9 left `unknown`.

That 1-out-of-10 number is lower than a first pass suggested, and getting there took two real bug fixes worth recording rather than glossing over:

1. **First run: 0/10 dependent, but the 0 wasn't trustworthy.** Manual inspection of the highest-similarity pair (candidate #5, CCTV vs. a Tencent-hosted Jimu News piece, both quoting Huazhong Agricultural University's own Weibo notice almost verbatim) showed a *false negative* — the similarity ratio only reached 0.51 because both pages' extracted text was diluted with site-navigation and footer boilerplate that the simple script/style/nav/header/footer strip didn't catch. Separately, one CCTV-hosted page (candidate #16) turned out to render its article body client-side via JavaScript — the static HTML literally contains the placeholder text "正在加载" ("Loading...") where the article should be, so there was nothing to compare at all. Fix: extractor now prefers `<p>`-tag text specifically (site chrome is rarely wrapped in `<p>`), and any source with under 60 characters of extracted text (or a loading placeholder) is marked "insufficient extracted text" rather than silently compared as if empty text were meaningful evidence of independence.

2. **Second run: 2/10 dependent, but one was a false positive.** The improved citation-matching (which now also catches two sources citing the *same third-party origin*, not just citing each other) flagged candidate #7's pair as both citing '媒体' — which just means "media" in Chinese, not a named outlet. Fix: added a stopword list for generic non-entity terms (媒体/网友/网络/新闻/etc.) that a citation regex can grab but that don't actually prove two sources share an origin.

Candidate #5's pair is a good illustration of this approach's real ceiling: it's very likely genuinely dependent (both are secondary write-ups of the same official notice), but neither source names the *other*, and they credit different immediate origins (CCTV cites the university's Weibo directly; the Tencent-hosted piece credits Jimu News, which presumably got it from the same Weibo one hop further back). A stdlib text-similarity/citation heuristic can't safely resolve a two-hop citation chain like that without risking false positives elsewhere — it's correctly left `unknown`, which is exactly the case the human gold-standard audit (§8) exists to catch.
