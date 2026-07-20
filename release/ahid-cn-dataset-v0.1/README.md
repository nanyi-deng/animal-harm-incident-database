# AHID-CN Dataset v0.1

First versioned release of the AHID-CN corpus — 30 animal harm incidents
from Chinese-language public sources, processed through the Animal Harm
Incident Database (AHID) pipeline: archiving, source-dependency analysis,
claim extraction, and evidence-sufficiency scoring. See
`methodology.md` in this package for full methods, and
`known_limitations.md` for what this pilot-scale release is and is not.

Source code, issue tracker, and living documentation:
https://github.com/nanyi-deng/animal-harm-incident-database

## Files

Data (four tables, shared `incident_id` key; UTF-8 with BOM, Excel-safe):

| File | Rows | One row per |
|---|---|---|
| `incidents_public.csv` | 30 | incident |
| `sources_public.csv` | 53 | archived source — all availability statuses included, not just currently-reachable ones |
| `claims_public.csv` | 151 | extracted checkable claim — contradicted and claimed-only claims included, not filtered out |
| `responses_public.csv` | 34 | institutional response (police, court, school, agency) |

Documentation:

- `data_dictionary.csv` — field-by-field schema, types, enums (authoritative)
- `methodology.md` — full methods documentation
- `inclusion_exclusion_criteria.md` — what qualifies an incident for inclusion
- `evidence_scoring_method.md` — the 0–100 evidence score and A1–A4/AX/AF status rules
- `known_limitations.md` — honest accounting of limits: pilot scale, discovery bias, single-rater audit, keyword-based response extraction, correction boundaries of published versions
- `changelog.md` — what this first version contains and notable build decisions

Integrity: `checksums.sha256` holds SHA-256 hashes of the four data CSVs.
License: `LICENSE_DATA.txt` (CC BY-SA 4.0 for the structured data; third-party
source content is not redistributed and remains with its rights holders).

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

See `CITATION.cff`. DOI for this version: `10.5281/zenodo.21462312`.
Cite the specific version (v0.1) and check the Zenodo record for any later
corrected versions before use — published versions are immutable;
corrections appear as new versions with changelog notes.
