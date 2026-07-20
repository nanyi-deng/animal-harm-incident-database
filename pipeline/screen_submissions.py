"""Pre-screen publicly submitted incident leads (GitHub Issues) for human review.

This is the "agent" half of the submission-intake design discussed with the
PI: the public can propose incidents via a GitHub issue form
(.github/ISSUE_TEMPLATE/incident_submission.yml), and this script does the
mechanical checking a human reviewer would otherwise have to do by hand for
every submission -- is the URL actually reachable, does it look like a real
article rather than a dead/blocked page, is it a duplicate of something
already in the seed list. What it deliberately does NOT do is decide
inclusion. That stays human-only, same as every other incident in this
dataset (HRL-007/016/017) and consistent with PRD's "a rule engine, not a
language model, decides what gets published" principle (methodology.md
S11) -- this script only prepares candidates for the existing manual
review workflow, appending to a staging file, never to seed_incidents.py
or the database directly.

Reuses archive_sources.py's fetch()/extract_title()/soft-404 heuristics
rather than reimplementing URL-liveness checking a second time.

Requires network access to the GitHub REST API (public read, no auth
token needed to list issues) and to each submitted URL, plus stdlib only.

Run: python3 pipeline/screen_submissions.py
     [--repo nanyi-deng/animal-harm-incident-database]
     [--out docs/pipeline/submitted_candidates_pending_review.md]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from archive_sources import (
    NO_TITLE_SUSPECT_MAX_BYTES,
    SOFT_404_TITLE_MARKERS,
    extract_title,
    fetch,
)
from seed_incidents import SOURCES

GITHUB_API = "https://api.github.com"
SUBMISSION_LABEL = "incident-submission"

# GitHub issue-form bodies render as "### <field label>\n\n<value>\n\n" blocks
# in submission order -- these must match the issue template's field labels
# exactly (.github/ISSUE_TEMPLATE/incident_submission.yml) or parsing silently
# returns nothing for that field.
FIELD_HEADERS = {
    "source_url": "事件公开报道链接（必填）",
    "additional_urls": "其他相关链接（可选）",
    "summary": "事件简述（必填）",
    "animal_category": "动物类型",
}


def _existing_urls() -> set:
    urls = set()
    for source_list in SOURCES.values():
        for url, *_ in source_list:
            urls.add(url.strip())
    return urls


def _parse_issue_form_body(body: str) -> dict:
    fields = {}
    for key, header in FIELD_HEADERS.items():
        m = re.search(
            rf"### {re.escape(header)}\s*\n+(.*?)(?=\n### |\Z)", body, re.DOTALL
        )
        if m:
            value = m.group(1).strip()
            if value and value != "_No response_":
                fields[key] = value
    return fields


def _github_headers() -> dict:
    # GH_TOKEN is optional locally; in the Actions workflow it's the built-in
    # token, which avoids the harsh unauthenticated rate limit on the shared
    # runner IPs (60 req/hr/IP would break the moment two issues arrive).
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_open_submissions(repo: str) -> list:
    url = f"{GITHUB_API}/repos/{repo}/issues?labels={SUBMISSION_LABEL}&state=open&per_page=100"
    req = urllib.request.Request(url, headers=_github_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        issues = json.loads(resp.read())
    # Issues API also returns PRs with issue-shaped payloads; exclude those.
    return [i for i in issues if "pull_request" not in i]


def _fetch_single_issue(repo: str, number: int) -> dict:
    url = f"{GITHUB_API}/repos/{repo}/issues/{number}"
    req = urllib.request.Request(url, headers=_github_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _check_url(url: str, existing: set) -> str:
    if url in existing:
        return "疑似重复：与已收录来源 URL 完全一致"
    status, raw, error = fetch(url)
    if not raw:
        return f"无法访问：HTTP {status}，{error}"
    title = extract_title(raw)
    if title and any(marker in title for marker in SOFT_404_TITLE_MARKERS):
        return f"疑似失效页面（标题：{title!r}）"
    if not title and len(raw) < NO_TITLE_SUSPECT_MAX_BYTES:
        return f"疑似反爬/挑战页（无标题，仅 {len(raw)} 字节）"
    return f"可访问（HTTP {status}，标题：{title!r}）"


def _screen_issue(issue: dict, existing: set) -> dict:
    fields = _parse_issue_form_body(issue.get("body") or "")
    urls = []
    if fields.get("source_url"):
        urls.append(fields["source_url"].strip())
    if fields.get("additional_urls"):
        urls.extend(u.strip() for u in fields["additional_urls"].split(",") if u.strip())

    checks = [(u, _check_url(u, existing)) for u in urls]

    return {
        "issue_number": issue["number"],
        "issue_url": issue["html_url"],
        "submitted_by": issue["user"]["login"],
        "title": issue["title"],
        "summary": fields.get("summary", "（未填写）"),
        "animal_category": fields.get("animal_category", "（未填写）"),
        "url_checks": checks,
    }


def format_comment(entry: dict) -> str:
    """Markdown comment posted back onto the issue by the Actions workflow."""
    lines = [
        "**自动预筛结果**（机械性检查，不构成收录判断——是否收录由人工按公开标准审核）",
        "",
    ]
    if entry["url_checks"]:
        for u, result in entry["url_checks"]:
            lines.append(f"- `{u}` — {result}")
    else:
        lines.append("- ⚠️ 未能从提交内容中解析出任何链接——请检查提交格式，或以评论补充来源 URL")
    lines += [
        "",
        "感谢提交。线索已进入人工审核队列，审核结论会回复在本 issue 下。",
    ]
    return "\n".join(lines)


def screen_single(repo: str, issue_number: int) -> None:
    """Screen one issue and print the result comment to stdout (Actions mode)."""
    existing = _existing_urls()
    issue = _fetch_single_issue(repo, issue_number)
    labels = {l["name"] for l in issue.get("labels", [])}
    if SUBMISSION_LABEL not in labels:
        print(f"Issue #{issue_number} lacks the {SUBMISSION_LABEL} label; nothing to do.",
              file=sys.stderr)
        return
    entry = _screen_issue(issue, existing)
    print(format_comment(entry))


def screen(repo: str, out_path: Path) -> None:
    existing = _existing_urls()
    issues = _fetch_open_submissions(repo)

    if not issues:
        print("No open incident-submission issues found.")
        return

    entries = [_screen_issue(issue, existing) for issue in issues]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(f"\n## 预筛批次 {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n")
        f.write(
            "以下候选来自公开提交（GitHub Issues），已经过自动预筛（链接可访问性、"
            "是否与已收录来源重复），**尚未经过人工审核，不构成收录决定**。"
            "审核后请手动移入 `candidate_incidents_seed.md` 并标注收录结果，"
            "同时在对应 GitHub issue 下回复审核结论、关闭 issue。\n\n"
        )
        for e in entries:
            f.write(f"### Issue #{e['issue_number']}：{e['title']}\n\n")
            f.write(f"- 提交者：@{e['submitted_by']}（{e['issue_url']}）\n")
            f.write(f"- 简述：{e['summary']}\n")
            f.write(f"- 动物类型：{e['animal_category']}\n")
            f.write("- 链接预筛结果：\n")
            for u, result in e["url_checks"]:
                f.write(f"  - `{u}` — {result}\n")
            f.write("- 人工审核结果：__（待填写：收录 / 不收录 / 需要更多信息）__\n\n")

    print(f"Screened {len(entries)} open submission(s), appended to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="nanyi-deng/animal-harm-incident-database")
    parser.add_argument(
        "--out", type=Path,
        default=Path(__file__).parent.parent / "docs" / "pipeline" / "submitted_candidates_pending_review.md",
    )
    parser.add_argument(
        "--issue", type=int, default=None,
        help="Screen a single issue and print the result comment to stdout "
             "(used by the prescreen GitHub Actions workflow) instead of "
             "appending all open submissions to the staging file",
    )
    args = parser.parse_args()
    if args.issue is not None:
        screen_single(args.repo, args.issue)
    else:
        screen(args.repo, args.out)
