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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
REQUEST_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 20

TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


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
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
            body = _decompress(raw, resp.headers.get("Content-Encoding", ""))
            return resp.status, body, None
    except urllib.error.HTTPError as e:
        return e.code, None, str(e)
    except Exception as e:  # noqa: BLE001 -- network fetch, want to log and move on
        return None, None, str(e)


def archive(db_path: Path, archive_dir: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(open(Path(__file__).parent / "schema.sql", encoding="utf-8").read())
    archive_dir.mkdir(parents=True, exist_ok=True)

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
            availability = "available" if status and status < 400 else "unavailable"
            conn.execute(
                "UPDATE sources_public SET first_collected_at = ?, availability_status = ? "
                "WHERE source_id = ?",
                (now, availability, source_id),
            )
            conn.execute(
                "INSERT INTO archive_log (source_id, fetched_at, http_status, sha256_hex, "
                "content_length, page_title, local_snapshot_path, error_message) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (source_id, now_ts, status, sha256_hex, len(raw), title, str(snapshot_path), error),
            )
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
    args = parser.parse_args()
    archive(args.db, args.archive_dir)
