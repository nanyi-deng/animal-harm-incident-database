import { defineConfig } from 'astro/config';

// Static output only -- no server, no adapter. Consistent with PRD v1.2 C3's
// MVP downgrade (GitHub Actions + SQLite + static Astro instead of
// Prefect/OpenSearch/Next.js). Deployed on Cloudflare Pages (PRD C14,
// 2026-07-21) -- the submit form's backend lives in functions/api/submit.js
// as a Cloudflare Pages Function, not a Vercel serverless function.
export default defineConfig({
  output: 'static',
  site: 'https://example.invalid', // placeholder until a real domain is decided (HRL-006)
});
