AHID-CN is the first-release language corpus of the Animal Harm Incident Database (AHID), an open-source project that discovers, archives, deduplicates, and cross-checks publicly available information about animal harm events. This dataset covers 30 incidents reported in Chinese-language public sources, collected via manual URL-driven backfill (not automated platform scraping) and processed through a rule-based pipeline: archiving, source-dependency analysis, claim extraction, and evidence-sufficiency scoring. A rule engine, not a language model, decides what gets published.

The project's methodological lineage follows the AI Incident Database (AIID): both address the same underlying problem — public information that is scattered, prone to deletion, easily misattributed, and costly to get wrong — with a reproducible, source-traceable, uncertainty-disclosing structure.

**What's included**

Four tables, distributed as CSV files with a shared incident_id key:

- incidents_public.csv (30 rows) — one row per incident, including date/location precision, animal category, harm type, an automated evidentiary status (A1-A4/AX/AF), and a 0-100 evidence sufficiency score
- sources_public.csv (53 rows) — every archived source, including ones later found unavailable; source tier, independence status, and archival status are retained rather than filtered out
- claims_public.csv (151 rows) — every extracted, individually checkable factual claim, including claims marked contradicted or claimed-only
- responses_public.csv (34 rows) — institutional responses (police, courts, schools, agencies) decomposed from claims_public

Source independence is modeled explicitly and conservatively: the pipeline only ever marks two sources "dependent" (proven via citation chain or near-duplicate text) or "unknown" — it never automatically asserts "independent," which is reserved for confirmed human review. Automated status (A1-A4/AX/AF) and the evidence score are determined independently and do not derive from each other.

**Known limitations (full detail in documentation/known_limitations.md)**

This is a 30-incident pilot release, not a stable-rate corpus: it reflects what was collected via manually-sourced URLs, not automated discovery, and should not be used to infer relative incidence rates across regions or groups. Evidence-scoring weights are an uncalibrated v0. A single-rater gold-standard audit (2026-07-27, full documentation in the repository) found zero content errors across all 30 incidents but has not yet produced a publishable inter-rater reliability statistic. Minors involved in any incident are never identified, with no exceptions; adults are identified only to the extent the original primary source itself already did.

**License**

The four CSV tables are licensed CC BY-SA 4.0, matching the AI Incident Database's licensing of its core structured collections. Third-party source article text and media referenced by this dataset are not redistributed and remain with their original rights holders — sources_public.csv contains only metadata about where each source can be found.

**Links**

Source code and full documentation: https://github.com/nanyi-deng/animal-harm-incident-database
