import { defineConfig } from 'astro/config';

// Static output only -- no server, no adapter. Consistent with PRD v1.2 C3's
// MVP downgrade (GitHub Actions + SQLite + static Astro instead of
// Prefect/OpenSearch/Next.js). Not deployed anywhere yet -- see HRL-002.
export default defineConfig({
  output: 'static',
  site: 'https://example.invalid', // placeholder until a real domain is decided (HRL-006)
});
