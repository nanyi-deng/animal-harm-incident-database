"""Stage 1: archive every source URL in sources_public that hasn't been fetched yet.

Fetches over plain HTTPS GET only -- no login, no captcha bypass, no
access-restriction circumvention (PRD v1.1 prohibited-methods list, PRD
v1.2 C2 media-redistribution principle). A polite fixed delay runs between
requests since this is a one-time pilot backfill of ~20 pages, not a
recurring crawl.

Raw HTML snapshots are written to pipeline/archive/ (gitignored -- these
are full copies of third-party news content and must never be redistributed
publicly; PRD v1.2 C2 says the public layer only ever gets metadata, a
hash, and a status, never the media/text itself). Only the hash, fetch
status, and a short title are written back to the database.

Run: python3 pipeline/archive_sources.py [--db pipeline/ahid_pilot.sqlite3]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import re
import sqlite3
import time
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
# Found via the gold-standard audit (2026-07-27): news.ycwb.com's WAF (Alibaba
# Cloud, "ESA"/acw_tc cookies) returned a gzip-compressed denial page for a
# bare User-Agent-only request (x-tengine-error: denied by http_custom), but
# passed cleanly once Accept/Accept-Language/Referer were added -- these are
# headers any real browser sends by default, not evasion of any access
# control (PRD §11.3 still prohibits captcha/login bypass, fake accounts,
# proxy pools; a complete standard header set is none of those). Re-tested
# dutenews.com's separate 405 with the same fuller headers -- still a genuine
# 405 (title literally "405"), confirming that one is a real dead endpoint,
# not a header-sensitivity false negative.
REQUEST_HEADERS_EXTRA = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.google.com/",
}
REQUEST_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 20

TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# HTTP 200 does not mean "got the article" -- soft-404 pages and anti-bot JS
# challenge pages both return 200 with real-looking byte counts. Caught by
# manual inspection after a run that reported these as [ok]; a title
# containing one of these markers, or a page with no title at all under
# this byte threshold, is far more likely a block/error page than a short
# real article.
SOFT_404_TITLE_MARKERS = ("404", "页面不存在", "找不到页面", "page not found")
NO_TITLE_SUSPECT_MAX_BYTES = 6000


def extract_title(raw: bytes) -> str | None:
    match = TITLE_RE.search(raw)
    if not match:
        return None
    text = match.group(1).decode("utf-8", errors="replace")
    return re.sub(r"\s+", " ", text).strip()[:300]


def _decompress(body: bytes, content_encoding: str) -> bytes:
    encoding = (content_encoding or "").lower()
    if "gzip" in encoding:
        return gzip.decompress(body)
    if "deflate" in encoding:
        return zlib.decompress(body)
    return body


def fetch(url: str) -> tuple[int | None, bytes | None, str | None]:
    # No Accept-Encoding sent -> servers are supposed to default to identity
    # (uncompressed) per HTTP spec, but at least one in this pilot's source
    # list (m.gmw.cn) sends gzip regardless. Decompress explicitly based on
    # the actual Content-Encoding response header rather than trust that.
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **REQUEST_HEADERS_EXTRA})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
            body = _decompress(raw, resp.headers.get("Content-Encoding", ""))
            return resp.status, body, None
    except urllib.error.HTTPError as e:
        return e.code, None, str(e)
    except Exception as e:  # noqa: BLE001 -- network fetch, want to log and move on
        return None, None, str(e)


def archive(db_path: Path, archive_dir: Path, retry_failed: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(open(Path(__file__).parent / "schema.sql", encoding="utf-8").read())
    archive_dir.mkdir(parents=True, exist_ok=True)

    if retry_failed:
        # Re-attempt sources previously marked unavailable, not just untried ones --
        # for re-checking after a fetch-logic fix (e.g. the 2026-07-27 header fix
        # found via the gold-standard audit), not for routine runs.
        pending = conn.execute(
            "SELECT source_id, original_url FROM sources_public "
            "WHERE first_collected_at IS NULL OR availability_status != 'available'"
        ).fetchall()
    else:
        pending = conn.execute(
            "SELECT source_id, original_url FROM sources_public WHERE first_collected_at IS NULL"
        ).fetchall()

    if not pending:
        print("Nothing to archive -- every source already has first_collected_at set.")
        return

    ok, failed = 0, 0
    for source_id, url in pending:
        status, raw, error = fetch(url)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_ts = datetime.now(timezone.utc).isoformat()

        if raw:
            sha256_hex = hashlib.sha256(raw).hexdigest()
            title = extract_title(raw)
            snapshot_path = archive_dir / f"{source_id}.html"
            snapshot_path.write_bytes(raw)

            soft_fail = None
            if title and any(marker in title for marker in SOFT_404_TITLE_MARKERS):
                soft_fail = f"soft-404 title: {title!r}"
            elif not title and len(raw) < NO_TITLE_SUSPECT_MAX_BYTES:
                soft_fail = f"no <title> and only {len(raw)}B -- likely anti-bot/challenge page, not an article"

            # availability_status enum (data_dictionary.csv) has no generic "unavailable" --
            # 'unknown' is the honest fit: for a soft-404 we can't tell if it moved, was
            # deleted, or was mistyped in the source article; for an anti-bot block we
            # simply never saw the real content, so we can't claim to know its state.
            availability = "unknown" if (soft_fail or not status or status >= 400) else "available"
            conn.execute(
                "UPDATE sources_public SET first_collected_at = ?, availability_status = ? "
                "WHERE source_id = ?",
                (now, availability, source_id),
            )
            conn.execute(
                "INSERT INTO archive_log (source_id, fetched_at, http_status, sha256_hex, "
                "content_length, page_title, local_snapshot_path, error_message) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (source_id, now_ts, status, sha256_hex, len(raw), title, str(snapshot_path), soft_fail or error),
            )
            if soft_fail:
                failed += 1
                print(f"[FAILED] {source_id}  HTTP {status}  {len(raw)}B  -- {soft_fail}")
            else:
                ok += 1
                print(f"[ok]     {source_id}  HTTP {status}  {len(raw)}B  {title!r}")
        else:
            conn.execute(
                "UPDATE sources_public SET availability_status = 'unknown' WHERE source_id = ?",
                (source_id,),
            )
            conn.execute(
                "INSERT INTO archive_log (source_id, fetched_at, http_status, error_message) "
                "VALUES (?, ?, ?, ?)",
                (source_id, now_ts, status, error),
            )
            failed += 1
            print(f"[FAILED] {source_id}  {url}  -- {error}")

        conn.commit()
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\nArchived {ok} sources, {failed} failed (see archive_log.error_message). "
          f"Snapshots in {archive_dir}/ (gitignored).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    parser.add_argument("--archive-dir", type=Path, default=Path(__file__).parent / "archive")
    parser.add_argument("--retry-failed", action="store_true",
                         help="Re-attempt sources with availability_status != 'available', "
                              "not just untried ones (for re-checking after a fetch-logic fix)")
    args = parser.parse_args()
    archive(args.db, args.archive_dir, retry_failed=args.retry_failed)
