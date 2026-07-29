AHID-CN is the Chinese-language corpus of the Animal Harm Incident Database (AHID), an open-source project that discovers, archives, deduplicates, and cross-checks publicly available information about animal harm events. This release holds two sub-corpora that answer different questions and are kept deliberately separate rather than merged into one table.

The first sub-corpus covers 30 incidents reported in Chinese-language public sources, collected via manual URL-driven backfill (not automated platform scraping) and processed through a rule-based pipeline: archiving, source-dependency analysis, claim extraction, and evidence-sufficiency scoring. A rule engine, not a language model, decides what gets published. It has broad coverage of whatever becomes publicly visible, but no denominator.

The second sub-corpus, added in this version, is a systematic census of 490 animal-harm criminal judgments drawn from CAIL2018 — a frozen, downloadable research corpus of 2.68 million Chinese criminal judgments. Because the search procedure and source corpus are both fixed and public, this sub-corpus has an explicit denominator: anyone can rerun the same search against the same data and get the same candidate set. It covers only what happened to result in a criminal prosecution, which the incident table does not guarantee, and its single largest finding is that in the absence of a dedicated anti-cruelty statute, intentional animal harm almost never enters the criminal record under its own name — it is prosecuted as theft, robbery, or a food-safety offense instead.

The project's methodological lineage follows the AI Incident Database (AIID): both address the same underlying problem — public information that is scattered, prone to deletion, easily misattributed, and costly to get wrong — with a reproducible, source-traceable, uncertainty-disclosing structure.

**What's included**

Five tables, distributed as CSV files:

- incidents_public.csv (30 rows) — one row per incident, including date/location precision, animal category, harm type, an automated evidentiary status (A1-A4/AX/AF), and a 0-100 evidence sufficiency score
- sources_public.csv (53 rows) — every archived source, including ones later found unavailable; source tier, independence status, and archival status are retained rather than filtered out
- claims_public.csv (151 rows) — every extracted, individually checkable factual claim, including claims marked contradicted or claimed-only
- responses_public.csv (34 rows) — institutional responses (police, courts, schools, agencies) decomposed from claims_public
- judgments_census.csv (490 rows) — one row per judgment, including the full court-established fact text, charge, and per-row evidence-transparency flags distinguishing court-documented harm from presumed or unverified cases

The first four tables share an incident_id key and belong to the reported-incident pipeline described above; judgments_census.csv is an independent flat table with its own census_id key and does not run the evidence-sufficiency scoring engine, because a single authoritative court judgment does not need the multi-source independence scoring built for socially-sourced claims.

Source independence in the incident pipeline is modeled explicitly and conservatively: it only ever marks two sources "dependent" (proven via citation chain or near-duplicate text) or "unknown" — never automatically "independent," which is reserved for confirmed human review. Automated status (A1-A4/AX/AF) and the evidence score are determined independently and do not derive from each other.

**Known limitations (full detail in documentation/known_limitations.md)**

The incident table is a 30-incident pilot release, not a stable-rate corpus: it reflects what was collected via manually-sourced URLs, not automated discovery, and should not be used to infer relative incidence rates across regions or groups. Evidence-scoring weights are an uncalibrated v0. A single-rater gold-standard audit found zero content errors across all 30 incidents but has not yet produced a publishable inter-rater reliability statistic. Minors involved in any incident are never identified, with no exceptions; adults are identified only to the extent the original primary source itself already did. The judgment census retains CAIL2018's own name-masking of case participants rather than adding further redaction, and it inherits CAIL2018's own limitations: no case number, court, or date; coverage ends at 2018; single-defendant cases only. Roughly 17% of its rows are the same underlying case appearing in more than one CAIL2018 competition split — kept deliberately unmerged rather than collapsed, so counts require deduplication first.

**License**

All five CSV tables are licensed CC BY-SA 4.0, matching the AI Incident Database's licensing of its core structured collections. Third-party source article text and media referenced by the incident tables are not redistributed and remain with their original rights holders — sources_public.csv contains only metadata about where each source can be found. The judgment census's full-text column is republished from CAIL2018's own public release of official court documents, which are not third-party media.

**Links**

Source code and full documentation: https://github.com/nanyi-deng/animal-harm-incident-database
