// Vercel serverless function: receive a submission from /submit/ and create a
// labeled GitHub issue. This is the entire "backend" -- GitHub Issues is the
// submission store (PRD: docs/prd/submission_ui_prd_draft.md §2), so there is
// deliberately no database write here and nothing this function does can touch
// published data. Worst case of abuse is noisy issues, which get deleted.
//
// Env vars (set in the Vercel project, never committed):
//   GITHUB_TOKEN          fine-grained PAT, issues:write on the one repo only
//   GITHUB_REPO           e.g. "nanyi-deng/animal-harm-incident-database"
//   TURNSTILE_SECRET_KEY  optional; when absent, Turnstile check is skipped
//                         (honeypot + rate limit still apply) so the endpoint
//                         works before Cloudflare setup is done.

const MAX_URLS = 10;
const RATE_LIMIT_PER_HOUR = 5;

// In-memory, per-instance. Serverless instances are ephemeral, so this resets
// on cold start and isn't shared across instances -- a soft brake against
// casual flooding, not a guarantee. Turnstile is the real gate; documented in
// the PRD rather than pretended to be stronger than it is.
const recentByIp = new Map();

function rateLimited(ip) {
  const now = Date.now();
  const cutoff = now - 60 * 60 * 1000;
  const times = (recentByIp.get(ip) || []).filter((t) => t > cutoff);
  if (times.length >= RATE_LIMIT_PER_HOUR) return true;
  times.push(now);
  recentByIp.set(ip, times);
  return false;
}

function parseUrls(raw) {
  if (!raw) return [];
  return raw
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function isHttpUrl(s) {
  try {
    const u = new URL(s);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

async function verifyTurnstile(token, ip) {
  const secret = process.env.TURNSTILE_SECRET_KEY;
  if (!secret) return true; // not configured yet -- degrade, don't break
  if (!token) return false;
  const resp = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ secret, response: token, remoteip: ip || '' }),
  });
  const data = await resp.json().catch(() => ({}));
  return data.success === true;
}

// Body format must match FIELD_HEADERS in pipeline/screen_submissions.py --
// the pre-screen script parses issues from the GitHub template and from here
// with the same regex, so the two intake channels stay interchangeable.
function buildIssueBody(fields) {
  const sections = [
    ['事件公开报道链接（必填）', fields.source_url],
    ['其他相关链接（可选）', fields.additional_urls.join(', ') || '_No response_'],
    ['事件简述（必填）', fields.summary],
    ['动物类型', fields.animal_category || '_No response_'],
  ];
  // The channel note is its own "### " section (not a bare footer) so the
  // pre-screen parser's lookahead stops the previous field's capture at it --
  // a bare footer got glued onto the last field's value in testing.
  return (
    sections.map(([h, v]) => `### ${h}\n\n${v}`).join('\n\n') +
    '\n\n### 提交渠道\n\n网站表单（/submit/）'
  );
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const ip =
    (req.headers['x-forwarded-for'] || '').split(',')[0].trim() ||
    req.socket?.remoteAddress ||
    'unknown';

  const body = req.body || {};

  // Honeypot: humans never see this field; any value means a bot filled it.
  // Return success so the bot doesn't learn it was detected.
  if (body.website) {
    return res.status(200).json({ ok: true });
  }

  if (rateLimited(ip)) {
    return res.status(429).json({ error: '提交过于频繁，请一小时后再试' });
  }

  const sourceUrl = (body.source_url || '').trim();
  const summary = (body.summary || '').trim();
  const additionalUrls = parseUrls(body.additional_urls).slice(0, MAX_URLS);

  if (!isHttpUrl(sourceUrl)) {
    return res.status(400).json({ error: '来源链接缺失或格式不正确' });
  }
  if (summary.length < 10 || summary.length > 2000) {
    return res.status(400).json({ error: '事件简述需在 10–2000 字之间' });
  }
  if (additionalUrls.some((u) => !isHttpUrl(u))) {
    return res.status(400).json({ error: '其他链接中存在格式不正确的 URL' });
  }
  if (!body.minor_confirm) {
    return res.status(400).json({ error: '请先确认未包含未成年人身份信息' });
  }

  const turnstileOk = await verifyTurnstile(body['cf-turnstile-response'], ip);
  if (!turnstileOk) {
    return res.status(400).json({ error: '人机验证未通过，请刷新页面重试' });
  }

  const repo = process.env.GITHUB_REPO;
  const token = process.env.GITHUB_TOKEN;
  if (!repo || !token) {
    return res.status(500).json({ error: '服务端未配置，请通过 GitHub issue 渠道提交' });
  }

  const title = `[线索] ${summary.slice(0, 40)}${summary.length > 40 ? '…' : ''}`;
  const ghResp = await fetch(`https://api.github.com/repos/${repo}/issues`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title,
      body: buildIssueBody({
        source_url: sourceUrl,
        additional_urls: additionalUrls,
        summary,
        animal_category: (body.animal_category || '').trim(),
      }),
      labels: ['incident-submission'],
    }),
  });

  if (!ghResp.ok) {
    const detail = await ghResp.text().catch(() => '');
    console.error('GitHub issue creation failed:', ghResp.status, detail.slice(0, 500));
    return res.status(502).json({ error: '暂时无法记录提交，请稍后重试或通过 GitHub issue 渠道提交' });
  }

  return res.status(200).json({ ok: true });
}
