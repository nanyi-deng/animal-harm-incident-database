# AHID-CN Dataset v0.2

Adds a second, independently-sampled sub-corpus to the AHID-CN release: 490
animal-harm criminal judgments drawn from CAIL2018 (a frozen, 2.68-million-
judgment research corpus), alongside the original 30 incidents from
Chinese-language public sources. The two sub-corpora are deliberately kept
side by side, not merged into one table — see "Why two sub-corpora" below —
but this package always ships both together so anyone downloading "the
dataset" gets the complete picture, not just whichever table changed most
recently.

The 30-incident table was processed through the Animal Harm Incident
Database (AHID) pipeline: archiving, source-dependency analysis, claim
extraction, and evidence-sufficiency scoring. See `methodology.md` in this
package for full methods on both sub-corpora, and `known_limitations.md`
for what each is and is not.

Source code, issue tracker, and living documentation:
https://github.com/nanyi-deng/animal-harm-incident-database

## Files

Data (UTF-8 with BOM, Excel-safe):

| File | Rows | One row per |
|---|---|---|
| `incidents_public.csv` | 30 | incident (shared `incident_id` key with the three tables below) |
| `sources_public.csv` | 53 | archived source — all availability statuses included, not just currently-reachable ones |
| `claims_public.csv` | 151 | extracted checkable claim — contradicted and claimed-only claims included, not filtered out |
| `responses_public.csv` | 34 | institutional response (police, court, school, agency) |
| `judgments_census.csv` | 490 | criminal judgment (independent flat table, own `census_id` key — see "Why two sub-corpora") |

Documentation:

- `data_dictionary.csv` — field-by-field schema, types, enums, for all five tables (authoritative)
- `methodology.md` — full methods documentation, both sub-corpora
- `inclusion_exclusion_criteria.md` — what qualifies an incident for inclusion
- `evidence_scoring_method.md` — the 0–100 evidence score and A1–A4/AX/AF status rules (incidents_public only; the judgment census does not run this engine — see methodology.md §13)
- `known_limitations.md` — honest accounting of limits for both sub-corpora
- `changelog.md` — what each version added and notable build decisions

Integrity: `checksums.sha256` holds SHA-256 hashes of all five data CSVs.
License: `LICENSE_DATA.txt` (CC BY-SA 4.0 for the structured data; third-party
source content is not redistributed and remains with its rights holders).

## Why two sub-corpora, not one

`incidents_public` and `judgments_census` answer different questions and
can't honestly be forced into one table. The incident table draws on
whatever public reporting surfaces — no denominator, but broad coverage of
what becomes publicly visible. The judgment census draws on a fixed,
downloadable, frozen corpus with an explicit search procedure — a real
denominator, but narrowed to whatever happened to result in a criminal
prosecution. A single authoritative court judgment doesn't need the
multi-source independence scoring built for socially-sourced claims, which
is why the census skips `evidence_sufficiency_score` entirely rather than
forcing a score that wouldn't mean anything. Comparing what each corpus
does and doesn't capture — which cases enter public reporting versus which
enter the criminal record — is itself one of this project's research
questions, not a gap to paper over by merging the two.

## Why sources and claims aren't pre-filtered

A dataset released for research use has the opposite obligation of a
browsing website: a source that went dark after archiving, or a claim that
turned out contradicted, is evidence the pipeline is supposed to preserve,
not smooth over. `availability_status` and `support_status` are included as
columns precisely so downstream analysis can decide how to treat each row,
rather than the export deciding for it. (The project website filters for
readability; this package does not.)

## Do not use this dataset to rank regions or groups

The corpus reflects publicly observable information collected via
manually-sourced URLs (Tier D backfill), not automated discovery, and
carries the reporting, platform, and deletion biases documented in
`known_limitations.md`. It is a pilot-scale evidence base, not an
incidence-rate estimate.

## Citation

See `CITATION.cff`. DOI for this specific version: assigned at upload time
(see the Zenodo record). Cite the specific version (v0.2) and check the
Zenodo record for any later corrected versions before use — published
versions are immutable; corrections appear as new versions with changelog
notes.
