"""Stage 2: source-dependency analysis.

Implements PRD v1.2 C4's conservative three-valued rule using only two
signals that can be asserted with confidence from the archived snapshots:

  1. citation-chain phrases ("据...报道", "转自", "来源：", etc.) that name
     another archived source's outlet for the same incident
  2. near-duplicate body text between two sources on the same incident

Either signal firing marks the pair `dependent` and merges them into one
cluster. Everything else is left `unknown` -- this script never assigns
`independent`. Per PRD v1.2 C4, that label is reserved for confirmed
human review (methodology.md §8 gold-standard audit), not something a
heuristic should assert on its own. A single-source incident is the only
case where a cluster count of 1 falls out trivially -- there's nothing to
compare it against, so it isn't "confirmed independent," it's just alone.

Only stdlib is used (html.parser + difflib) -- deliberate, given the
pilot's scale (19 incidents, mostly 1-2 sources each); see the Stage 2
plan discussed with the PI before this was built.

Run: python3 pipeline/dependency_analysis.py [--db pipeline/ahid_pilot.sqlite3]
"""

from __future__ import annotations

import argparse
import difflib
import re
import sqlite3
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

METHOD_VERSION = "stage2-stdlib-v0.1"

SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript"}

# Each pattern's group(1) is the cited entity's name -- e.g. "据@华中农业大学官方微博消息"
# extracts "@华中农业大学官方微博". This matters because two sources both citing the
# SAME external origin (a university's own Weibo notice, a wire service neither of
# them IS) is real dependency evidence even when neither source's name literally
# appears in the other's text -- catching that requires comparing what each side
# cites, not just cross-checking against the fixed list of already-archived names.
CITATION_PATTERNS = [
    re.compile(r"据([^，。,\s]{1,16}?)(?:报道|消息|通报)"),
    re.compile(r"转自([^，。,\s]{1,20})"),
    re.compile(r"来源[:：]\s*([^\s，。,]{1,20})"),
    re.compile(r"综合([^，。,\s]{1,16}?)(?:报道|消息)"),
    re.compile(r"本文转载自([^，。,\s]{1,20})"),
]

# Near-duplicate threshold: deliberately high. Two independently-written
# articles about the same official notice will share a fair amount of
# quoted text; only near-identical bodies should count as "dependent".
NEAR_DUP_RATIO_THRESHOLD = 0.85


class _TextExtractor(HTMLParser):
    """Collects all visible text (minus script/style/nav/header/footer/aside),
    AND separately collects only text inside <p> tags. Most news CMSs wrap
    article paragraphs in <p> while site chrome (breadcrumbs, share widgets,
    "back to homepage", copyright footers) usually isn't -- so <p>-only text
    is a much better proxy for "the actual article" than everything-minus-chrome.
    """

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._p_depth = 0
        self.all_chunks = []
        self.p_chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        if tag == "p":
            self._p_depth += 1

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "p" and self._p_depth > 0:
            self._p_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.all_chunks.append(stripped)
                if self._p_depth > 0:
                    self.p_chunks.append(stripped)


# Below this many characters, treat extracted text as unusable rather than
# comparing it -- either the page is JS-rendered (client fills content after
# load, e.g. some cctv.com templates show a literal "正在加载" placeholder in
# the static HTML) or something else went wrong. A near-zero similarity ratio
# from empty text looks exactly like confident evidence of independence, which
# it is not -- it's an extraction failure and must not be read as a signal.
MIN_USABLE_TEXT_CHARS = 60
LOADING_PLACEHOLDER_MARKERS = ("正在加载",)


def extract_body_text(raw_html: bytes) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(raw_html.decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001 -- malformed HTML shouldn't crash the pipeline
        return ""
    p_text = re.sub(r"\s+", " ", " ".join(parser.p_chunks)).strip()
    if len(p_text) >= MIN_USABLE_TEXT_CHARS:
        return p_text
    all_text = re.sub(r"\s+", " ", " ".join(parser.all_chunks)).strip()
    return all_text


def text_is_usable(text: str) -> bool:
    if len(text) < MIN_USABLE_TEXT_CHARS:
        return False
    return not any(marker in text for marker in LOADING_PLACEHOLDER_MARKERS)


# Generic words that a citation regex can capture as if they were a named
# outlet/entity but aren't specific enough to prove two sources share an
# origin -- "据媒体报道" (according to media reports) matches as many
# unrelated articles as "the news says so" does in English. Without this
# filter, two sources that both use vague generic attribution would look
# like they cite "the same" source when they don't share anything.
GENERIC_CITATION_STOPWORDS = {"媒体", "网友", "网络", "记者", "有关部门", "相关部门", "官方", "报道", "网传", "新闻"}


def extract_cited_names(text: str) -> list[str]:
    """Every SPECIFIC entity a source's text credits as its origin, e.g.
    'zhihu -> @华中农业大学官方微博'. Generic non-entity words are dropped --
    see GENERIC_CITATION_STOPWORDS.
    """
    names = []
    for pattern in CITATION_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1).strip("@ 　")
            if name and name not in GENERIC_CITATION_STOPWORDS:
                names.append(name)
    return names


def find_citation_signal(text_a: str, cited_by_a: list[str], other_source_names: list[str],
                          cited_by_b: list[str]) -> str | None:
    # Case 1: A's text names one of the OTHER already-archived sources directly.
    for name in other_source_names:
        if name and any(name in cited for cited in cited_by_a):
            return f"cites archived source {name!r} directly"
    # Case 2: A and B both credit the same external origin neither of them is
    # (e.g. both are secondary write-ups of the same official Weibo notice).
    # Substring match in either direction since outlets abbreviate variably
    # ("华中农业大学官方微博" vs. "华中农业大学").
    for name_a in cited_by_a:
        for name_b in cited_by_b:
            if name_a and name_b and (name_a in name_b or name_b in name_a):
                return f"both cite the same external origin ({name_a!r} / {name_b!r})"
    return None


def text_similarity(text_a: str, text_b: str) -> float:
    if not text_a or not text_b:
        return 0.0
    # Cap comparison length for speed; near-dup detection doesn't need full articles.
    a, b = text_a[:5000], text_b[:5000]
    return difflib.SequenceMatcher(None, a, b).ratio()


class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def analyze(db_path: Path, archive_dir: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(open(Path(__file__).parent / "schema.sql", encoding="utf-8").read())

    incidents = conn.execute("SELECT incident_id FROM incidents_public").fetchall()
    now_ts = datetime.now(timezone.utc).isoformat()
    total_pairs, total_dependent = 0, 0

    for (incident_id,) in incidents:
        sources = conn.execute(
            "SELECT source_id, source_name, original_url FROM sources_public "
            "WHERE incident_id = ? AND first_collected_at IS NOT NULL",
            (incident_id,),
        ).fetchall()

        if not sources:
            continue  # nothing archived yet for this incident; Stage 1's job, not ours

        source_ids = [s[0] for s in sources]
        uf = UnionFind(source_ids)

        texts = {}
        cited_names = {}
        for source_id, _, _ in sources:
            snapshot = archive_dir / f"{source_id}.html"
            text = extract_body_text(snapshot.read_bytes()) if snapshot.exists() else ""
            texts[source_id] = text
            cited_names[source_id] = extract_cited_names(text)

        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                sid_a, name_a, _ = sources[i]
                sid_b, name_b, _ = sources[j]
                total_pairs += 1

                other_names_for_a = [n for sid, n, _ in sources if sid != sid_a]
                other_names_for_b = [n for sid, n, _ in sources if sid != sid_b]
                citation = (
                    find_citation_signal(texts[sid_a], cited_names[sid_a], other_names_for_a, cited_names[sid_b])
                    or find_citation_signal(texts[sid_b], cited_names[sid_b], other_names_for_b, cited_names[sid_a])
                )

                usable = text_is_usable(texts[sid_a]) and text_is_usable(texts[sid_b])
                if not usable:
                    ratio = None
                    citation = citation or "insufficient extracted text on one or both sides " \
                                            "(possibly JS-rendered) -- similarity not computed"
                    decision = "unknown"
                else:
                    ratio = text_similarity(texts[sid_a], texts[sid_b])
                    if citation or ratio >= NEAR_DUP_RATIO_THRESHOLD:
                        decision = "dependent"
                    else:
                        decision = "unknown"

                if decision == "dependent":
                    uf.union(sid_a, sid_b)
                    total_dependent += 1

                conn.execute(
                    "INSERT INTO dependency_log (incident_id, source_id_a, source_id_b, "
                    "text_similarity_ratio, citation_signal, decision, method_version, analyzed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (incident_id, sid_a, sid_b, ratio, citation, decision, METHOD_VERSION, now_ts),
                )

        # Assign cluster ids from the union-find groups, and independence_status:
        # a source is 'dependent' if it got merged with anything, else 'unknown'
        # (never 'independent' -- see module docstring).
        roots = {sid: uf.find(sid) for sid in source_ids}
        cluster_ids = {}
        for idx, root in enumerate(sorted(set(roots.values())), start=1):
            cluster_ids[root] = f"CLU-{incident_id}-{idx:02d}"

        cluster_members = {}
        for sid, root in roots.items():
            cluster_members.setdefault(root, []).append(sid)

        for sid, root in roots.items():
            status = "dependent" if len(cluster_members[root]) > 1 else "unknown"
            conn.execute(
                "UPDATE sources_public SET independence_status = ?, independent_cluster_id = ? "
                "WHERE source_id = ?",
                (status, cluster_ids[root], sid),
            )

        cluster_count = len(cluster_ids)
        conn.execute(
            "UPDATE incidents_public SET independent_source_cluster_count = ? WHERE incident_id = ?",
            (cluster_count, incident_id),
        )

    conn.commit()

    summary = conn.execute(
        "SELECT independent_source_cluster_count, COUNT(*) FROM incidents_public "
        "WHERE independent_source_cluster_count IS NOT NULL GROUP BY independent_source_cluster_count"
    ).fetchall()
    conn.close()

    print(f"Analyzed {total_pairs} source pairs across incidents with archived sources; "
          f"{total_dependent} pairs marked dependent.")
    print("Incidents by independent_source_cluster_count:", dict(summary))
    print("Note: independence_status is either 'dependent' or 'unknown' -- this script "
          "never assigns 'independent'; that label is reserved for the human gold-standard "
          "audit (methodology.md §8).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    parser.add_argument("--archive-dir", type=Path, default=Path(__file__).parent / "archive")
    args = parser.parse_args()
    analyze(args.db, args.archive_dir)
