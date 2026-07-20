"""HRL-008 privacy QA support: flag candidate personal-name tokens in the
free-text fields (claims_public.claim_value, responses_public.summary_zh)
for human review before a real data release.

This is NOT a certified PII detector -- there is no real Chinese NER
library available in this environment, so this uses a blunt heuristic
(common surname character + 1-2 following Han characters) that will
over-flag institution names, place names, and other non-person tokens.
That is intentional: the cost of a human spending a few extra seconds
dismissing "张家口" as not a person is much lower than the cost of a real
name slipping through an automated filter that claimed high precision it
didn't have. The output is a candidate list for a human to read, not a
pass/fail verdict -- HRL-015's actual identity policy still requires
human judgment about whether a name matches an official source's own
disclosure level.

Cross-references findings against the three names HRL-015 already
approved for real-name use (the primary/official source itself named
them): 范源庆 (#6), 徐志辉 (#9), 王照蔚 (#34). Anything else that looks
like a name is flagged as needing a check against HRL-015's default rule
(follow the identification level the source itself used; don't dig
deeper to identify someone the source anonymized).

Run: python3 pipeline/privacy_scan.py [--db pipeline/ahid_pilot.sqlite3]
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

# Top ~150 common Chinese surnames (single-char) plus a handful of common
# two-char (compound) surnames. Covers the large majority of real names;
# missing a rare surname just means under-flagging that specific case,
# which is why this tool is explicitly a candidate list, not a guarantee.
COMMON_SURNAMES = set(
    "王李张刘陈杨黄赵周吴徐孙朱马胡郭林何高梁郑罗宋谢唐韩曹许邓萧冯曾程蔡彭潘袁于董余"
    "苏叶吕魏蒋田杜丁沈姜范江傅钟卢汪戴崔任陆廖姚方金邱夏谭韦贾邹石熊孟秦阎薛侯雷白龙"
    "段郝孔邵史毛常万顾赖武康贺严尹钱施牛洪龚"
)
COMMON_COMPOUND_SURNAMES = {"欧阳", "司马", "上官", "诸葛", "东方", "皇甫", "尉迟", "公孙"}

APPROVED_REAL_NAMES = {
    "范源庆": "校方声明本身用实名，见 HRL-015",
    "徐志辉": "官方通稿本身用实名，见 HRL-015",
    "王照蔚": "校方通报本身用实名，见 HRL-015",
}

# Common words that happen to start with a surname character but are not
# personal names -- filtered out to keep the candidate list usable rather
# than dominated by obvious noise. Not exhaustive by design.
STOPWORD_PREFIXES = {
    "王照蔚", "范源庆", "徐志辉",  # already-approved names, reported separately
    "何时", "何况", "常见", "常委", "史料",
}

NAME_CANDIDATE_RE = re.compile(
    r"[{surnames}][一-鿿]{{1,2}}".format(surnames=COMMON_SURNAMES)
)
MASKED_MARKER_RE = re.compile(r"[一-鿿]某[一-鿿]?")


def find_candidates(text: str) -> set:
    if not text:
        return set()
    candidates = set()
    for compound in COMMON_COMPOUND_SURNAMES:
        for m in re.finditer(re.escape(compound) + r"[一-鿿]{1,2}", text):
            candidates.add(m.group())
    for m in NAME_CANDIDATE_RE.finditer(text):
        token = m.group()
        if token in STOPWORD_PREFIXES:
            continue
        candidates.add(token)
    return candidates


def scan(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)

    rows = conn.execute(
        "SELECT c.incident_id, 'claim' AS field, c.claim_value AS text "
        "FROM claims_public c JOIN incidents_public i ON c.incident_id = i.incident_id "
        "WHERE i.is_test_case = 0 "
        "UNION ALL "
        "SELECT r.incident_id, 'response' AS field, r.summary_zh AS text "
        "FROM responses_public r JOIN incidents_public i ON r.incident_id = i.incident_id "
        "WHERE i.is_test_case = 0"
    ).fetchall()
    conn.close()

    masked_incidents = set()
    approved_hits = defaultdict(set)
    other_candidates = defaultdict(set)  # token -> set of incident_ids

    for incident_id, field, text in rows:
        if not text:
            continue
        if MASKED_MARKER_RE.search(text):
            masked_incidents.add(incident_id)
        for name, _ in APPROVED_REAL_NAMES.items():
            if name in text:
                approved_hits[name].add(incident_id)
        for token in find_candidates(text):
            other_candidates[token].add(incident_id)

    print(f"Scanned {len(rows)} free-text fields across claims_public + responses_public.\n")

    print("== 已批准实名（HRL-015）在文本中出现的情况 ==")
    for name, note in APPROVED_REAL_NAMES.items():
        hits = approved_hits.get(name, set())
        status = "found in " + ", ".join(sorted(hits)) if hits else "NOT FOUND in current text"
        print(f"  {name}: {status} -- expected: {note}")
    print()

    print(f"== 使用「某」字匿名化标记的事件数：{len(masked_incidents)} ==")
    print("  " + ", ".join(sorted(masked_incidents)) if masked_incidents else "  (none)")
    print()

    flagged = {tok: ids for tok, ids in other_candidates.items() if tok not in APPROVED_REAL_NAMES}
    print(f"== 待人工核对的候选人名 token（{len(flagged)} 个，按出现频率排序） ==")
    print("  (启发式规则：常见姓氏+1-2个汉字；会大量误报机构名/地名，"
          "只是缩小人工核对范围，不是自动判定结果)")
    for tok, ids in sorted(flagged.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tok}  ({len(ids)} incident): {', '.join(sorted(ids))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    args = parser.parse_args()
    scan(args.db)
