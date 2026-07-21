// Dependency-free regression test for the submission Cloudflare Pages Function.
// Run: npm test  (from site/)  — or: node functions/api/submit.test.mjs
// Exits non-zero on any failure so it can gate a deploy.
//
// Covers the validation paths, the per-IP rate limit, and the structural
// contract the pre-screen parser depends on: the "### 提交渠道" footer must be
// its own section so it never glues onto the last field's value (a real bug
// that occurred once and must not regress -- see pipeline/screen_submissions.py
// FIELD_HEADERS and its lookahead regex).
import { onRequestPost, onRequestGet } from './submit.js';

let capturedBody = null;
globalThis.fetch = async (url, opts) => {
  if (String(url).includes('api.github.com')) {
    capturedBody = JSON.parse(opts.body);
    return { ok: true, json: async () => ({ number: 1 }) };
  }
  throw new Error('unexpected fetch: ' + url);
};

let ipCounter = 0;
function mkCtx(body, { env, ip } = {}) {
  const clientIp = ip || `198.51.100.${++ipCounter}`;
  return {
    request: {
      method: 'POST',
      headers: { get: (k) => (k === 'CF-Connecting-IP' ? clientIp : null) },
      json: async () => body,
    },
    env: env || { GITHUB_REPO: 'owner/repo', GITHUB_TOKEN: 'x' },
  };
}

const valid = {
  source_url: 'https://news.example.com/a',
  additional_urls: 'https://a.com/1, https://b.com/2',
  summary: '2024年某地某人毒死小区流浪狗数只，警方已介入调查。',
  animal_category: '犬',
  minor_confirm: 'on',
};

let pass = 0, fail = 0;
function check(label, ok) {
  console.log(`  [${ok ? '✓' : '✗'}] ${label}`);
  ok ? pass++ : fail++;
}

const cases = [
  ['正常提交 → 200', valid, 200],
  ['蜜罐命中 → 200（静默丢弃）', { ...valid, website: 'bot' }, 200],
  ['缺来源链接 → 400', { ...valid, source_url: '' }, 400],
  ['来源非 http → 400', { ...valid, source_url: 'ftp://x' }, 400],
  ['简述过短 → 400', { ...valid, summary: '太短' }, 400],
  ['其他链接含非法 URL → 400', { ...valid, additional_urls: 'notaurl' }, 400],
  ['未勾未成年人确认 → 400', { ...valid, minor_confirm: '' }, 400],
];
for (const [label, body, expect] of cases) {
  const res = await onRequestPost(mkCtx(body));
  check(`${label} (got ${res.status})`, res.status === expect);
}

// Rate limit: same IP, 5 allowed then blocked.
let allowed = 0, blocked = 0;
for (let i = 0; i < 7; i++) {
  const r = await onRequestPost(mkCtx(valid, { ip: '192.0.2.55' }));
  r.status === 429 ? blocked++ : allowed++;
}
check(`限频 5/小时（放行 ${allowed}, 拦截 ${blocked}）`, allowed === 5 && blocked === 2);

check('服务端未配置 env → 500', (await onRequestPost(mkCtx(valid, { env: {} }))).status === 500);
check('GET → 405', (await onRequestGet()).status === 405);

// Structural contract for the pre-screen parser: footer is its own section and
// never leaks into the last field's value.
capturedBody = null;
await onRequestPost(mkCtx(valid));
const body = capturedBody.body;
check('issue 正文含全部 4 个字段小节', [
  '### 事件公开报道链接（必填）',
  '### 其他相关链接（可选）',
  '### 事件简述（必填）',
  '### 动物类型',
].every((h) => body.includes(h)));
check('提交渠道为独立小节（防页脚粘连）', body.includes('\n\n### 提交渠道\n\n网站表单（/submit/）'));
// The animal value block must be exactly '犬' with the footer starting a new section.
check('动物类型值不含页脚文本', /### 动物类型\n\n犬\n\n### 提交渠道/.test(body));
check("labels 含 'incident-submission'", JSON.stringify(capturedBody.labels).includes('incident-submission'));

console.log(`\n${fail === 0 ? '✓' : '✗'} ${pass} 通过, ${fail} 失败`);
process.exit(fail > 0 ? 1 : 0);
