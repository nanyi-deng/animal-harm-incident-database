# ahid-cn-dataset-v0.1 (staging build, not yet released)

This directory is a **local staging build** of the first versioned AHID-CN
dataset package. It is assembled here for review and is **not** the
Zenodo release — no DOI has been minted, and the data has not been made
public. Publication is gated on three open items tracked in
`docs/human_review_log.md`: HRL-005 (license terms not yet finalized),
HRL-008 (a privacy QA signoff has not yet been run against this specific
snapshot), and HRL-009 (no Zenodo/ORCID account exists yet to publish
under). `LICENSE_DATA.txt` in this package is a placeholder for that
reason — do not treat it as binding.

## What's in this snapshot

30 incidents (Chinese-language public sources, Tier D URL-driven backfill —
see `documentation/inclusion_exclusion_criteria.md`), 53 sources, 151 claims,
34 structured institutional-response records. A 31st incident processed by
the pipeline (the Zhengzhou false-report case) is excluded from this package
by design — it is an internal test fixture used to validate the pipeline's
handling of contradicted claims, not a real incident record.

```
data/
  incidents_public.csv    30 rows — one per incident
  sources_public.csv      53 rows — every archived source, all availability
                           statuses included (not just currently-reachable ones)
  claims_public.csv       151 rows — every extracted claim, all support
                           statuses included (contradicted and claimed_only
                           claims are not filtered out; that they exist and
                           how they were resolved is part of the record)
  responses_public.csv    34 rows — institutional responses decomposed from
                           claims_public (see documentation/known_limitations.md
                           for how this decomposition was done and its limits)
documentation/
  data_dictionary.csv               field-by-field schema, types, enums
  methodology.md                    full methods documentation
  inclusion_exclusion_criteria.md   what qualifies an incident for inclusion
  evidence_scoring_method.md        the evidence sufficiency score and
                                     automation-status rules, in isolation
                                     from the rest of methodology.md
  known_limitations.md              honest accounting of what this dataset
                                     is not yet — pilot scale, single-rater
                                     audit, keyword-based response extraction
  changelog.md                      what changed since there was no prior version
LICENSE_DATA.txt          placeholder pending HRL-005
CITATION.cff              placeholder pending HRL-011 (author name/ORCID)
checksums.sha256          sha256 of every file in data/, for integrity
                           verification after this package is copied/moved
```

## Why sources/claims aren't pre-filtered here

`site/src/data/incidents.json` (the Astro site's data feed) hides sources
that are no longer reachable and reorders claims by support status, because
a website visitor clicking a dead link is a bad experience. A dataset
released for research use has the opposite obligation: a source going dark
after archiving, or a claim that turned out contradicted, is evidence the
pipeline is supposed to preserve, not smooth over. `availability_status` and
`support_status` are included as columns precisely so downstream analysis
can decide how to treat each row, rather than the export deciding for it.

## Regenerating this package

```
python3 pipeline/export_dataset_csvs.py
sha256sum release/ahid-cn-dataset-v0.1/data/*.csv > release/ahid-cn-dataset-v0.1/checksums.sha256
```

`documentation/data_dictionary.csv` and `documentation/methodology.md` are
verbatim copies of `docs/data_dictionary.csv` and `docs/methodology.md` in
the main repository — re-copy them if those change. The other four files
under `documentation/` are specific to this package and maintained here.
