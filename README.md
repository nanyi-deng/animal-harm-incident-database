# AHID — Animal Harm Incident Database

**动物伤害事件数据库** · First corpus: **AHID-CN** (Chinese-language Incident Corpus)

> 让被删除、被误传、被分散和被遗忘的信息，变成可持续查询、核验和研究的公共记录。
> Turning deleted, misattributed, scattered, and forgotten public information into a durable, queryable, and verifiable public record.

## What this is

AHID is a multilingual, open-source **incident database** that discovers, archives, deduplicates, clusters, and cross-checks publicly available information about animal harm events. The first corpus (AHID-CN) covers Chinese-language public sources. The system records events and institutional responses — it is **not** a blacklist, a conviction platform, or a graphic-content aggregator, and it never publishes the identities of minors or private individuals.

AHID 是一个多语言、开源的**事件数据库**：持续发现、保存、去重、归并并交叉核验公开互联网上与动物伤害有关的信息，透明展示来源、证据充分度、冲突与机构回应。首期语料（AHID-CN）覆盖中文公开来源。本项目记录事件与制度回应，**不是**涉事人员名单、民间定罪平台或血腥内容聚合站，并且原则上不公开未成年人及普通个人的身份信息。

## Status

**Pre-release (v0.0.x-dev).** PRD v1.2 adopted 2026-07-20. Research MVP:

- [x] Pilot pipeline (seed → archive → dependency analysis → claim extraction → scoring), Tier D URL-driven backfill — done 2026-07-27, ahead of the original Sept target
- [x] 31 incidents processed end to end (30 public + 1 internal test fixture), clearing the 30-incident floor toward the `ahid-cn-dataset-v0.1` target — 2026-07-27
- [x] Site scaffold built and populated with real pilot data (Astro, static) — 2026-07-27, **not deployed publicly** (gated on HRL-002)
- [ ] Gold-standard human audit sample (methodology.md §8) — pending
- [ ] `ahid-cn-dataset-v0.1` + Zenodo DOI — Oct 2026 target
- [ ] Methods white paper (SocArXiv) — Nov–Dec 2026 target
- [ ] Six-locale site content (currently zh-Hans only; gated on HRL-010) and public deployment (gated on HRL-002) — after interview season

## Repository structure

```
docs/
  prd/PRD_v1.2_patch.md         # Adopted revision patch on top of PRD v1.0 + v1.1
  data_dictionary.csv            # Public dataset schema
  methodology.md                 # Methods documentation
  human_review_log.md            # Every item requiring human decision/verification
  irb/, pipeline/                # IRB materials; candidate seed lists and review notes
pipeline/
  schema.sql, seed_incidents.py, archive_sources.py,
  dependency_analysis.py, claims_extraction.py, scoring.py,
  export_site_data.py            # Stages 0-5; database and archived snapshots are gitignored
site/
  src/data/incidents.json        # Generated public export (see site/README.md); site itself unpublished
```

The canonical PRD v1.0 + v1.1 text is maintained by the founder and should be added under `docs/prd/` (see HRL-012).

## Governance in one paragraph

Every published claim traces to a source. Source dependency is modeled explicitly (ten reposts of one Weibo post are one independent cluster, not ten). Evidence sufficiency is scored by versioned, uncalibrated-then-calibrated rules — never presented as "probability of truth" or a judicial finding. Misattributed content (old/relocated videos) is not deleted but converted into correction records. A rule engine — not a language model — decides what gets published.

## Citation

Dataset citation will be available with `ahid-cn-dataset-v0.1` (Zenodo DOI, expected Oct 2026). Until then, please cite this repository (see `CITATION.cff`).

## License

To be finalized before first public release (planned: CC BY 4.0 for original structured data, MIT for code; third-party source content remains with its rights holders). See `docs/human_review_log.md` HRL-005.
