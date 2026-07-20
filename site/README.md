# AHID site (Astro, static)

Public-facing incident browser. Static output (PRD v1.2 C3's MVP downgrade — no server, no adapter), plus exactly one serverless function: `api/submit.js`, the submission-intake endpoint behind `/submit/` (HRL-022). The function only creates labeled GitHub issues — it writes to no database and cannot touch published data. Deployment steps for it are in `DEPLOY.md` (Vercel, root directory = `site`).

## Status: built, not published

`astro.config.mjs` ships `noindex, nofollow` and a placeholder `site:` URL on purpose. The family-risk assessment (HRL-002) was signed off 2026-07-27, so the governance blocker is resolved — but actually deploying publicly (and removing noindex) remains a separate, explicit decision this repo doesn't make unilaterally. Deploying the submission UI per `DEPLOY.md` does not by itself publish the site.

## Data flow

`src/data/incidents.json` is generated from the pipeline SQLite database, not hand-edited:

```
python3 ../pipeline/export_site_data.py
```

It's committed to git (unlike the pipeline's own `.sqlite3` file and archived HTML snapshots, which are gitignored). That's a deliberate difference, not an inconsistency: the JSON only contains fields `docs/data_dictionary.csv` already marks public, only cites sources with `availability_status='available'` (dead links and anti-bot-blocked pages are silently dropped from the export, not just hidden in the UI), and excludes the `is_test_case=1` fixture entirely. It contains no raw third-party article text — only structured claims and metadata already written by the pipeline. Committing it means the site is buildable from a fresh clone without re-running the full pipeline (which needs live network access and produces non-reproducible timestamps), and it gives the public dataset a diffable version history in git, consistent with PRD §26.3's snapshot/versioning philosophy.

Re-run the export (and rebuild) any time the pipeline database changes.

## Commands

```
npm install
npm run dev       # local preview at localhost:4321
npm run build     # -> dist/, gitignored
```

## What's deliberately not done yet

- **Six-language support**: architected for (PRD v1.2 C10's template-based localization), but `src/lib/labels.js` is zh-Hans only. Gated on HRL-010 (native-speaker review of `docs/i18n/glossary.csv`, currently `machine_draft`).
- **Media display**: no images or video anywhere — this pilot only archived HTML text, not media assets, so PRD §14's sensitivity-tier display rules (C0–C3) aren't yet exercised. Will matter once media archiving is built.
- **Search beyond client-side filters**: the incident list page filters by province/animal-type/status/minor-involvement with a small inline script, no build step, no external service. Fine at 30 incidents; won't scale indefinitely.
