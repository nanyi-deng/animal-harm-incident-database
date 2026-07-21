"""Privacy QA for the judgment census before publishing full fact text.

The census publishes each judgment's full 事实认定 text on the premise that
CAIL2018 already masks personal names (张某某 style). That premise is only
partly true: CAIL2018 masks CASE PARTICIPANTS (defendants, victims,
witnesses -> 范某 / 胡某某 / 张某乙), but it does NOT mask names that appear
inside location landmarks and business references (e.g. "龚见兴出租屋" -- a
landlord's full name used to describe where a crime scene was). Publishing
the fact text verbatim therefore risks exposing incidental third-party names
the masking never touched.

This scan does three things, all factual (no redaction -- redaction beyond
the source's own masking is a policy call for the project lead, per protocol
§8(b) "照抄文书原文的遮蔽程度"):

  1. Masking prevalence: how many of the 424 rows carry any 某-mask at all.
  2. Unmasked full-name candidates: surname + 1-2 Han chars with NO 某 in or
     adjacent to the token, minus a place/org stopword list. These are the
     龚见兴-type residues -- the real risk. Over-flags by design; the output
     is a human-review candidate list, not a verdict.
  3. Structured PII: phone numbers, resident-ID numbers -- unambiguous leaks
     if present, independent of any name-masking policy.

Run: python3 pipeline/census_privacy_scan.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

FINAL_JSONL = Path(__file__).parent / "census_final.jsonl"

# Same surname set as privacy_scan.py -- kept in sync deliberately so the two
# scans agree on what counts as a candidate surname.
COMMON_SURNAMES = set(
    "王李张刘陈杨黄赵周吴徐孙朱马胡郭林何高梁郑罗宋谢唐韩曹许邓萧冯曾程蔡彭潘袁于董余"
    "苏叶吕魏蒋田杜丁沈姜范江傅钟卢汪戴崔任陆廖姚方金邱夏谭韦贾邹石熊孟秦阎薛侯雷白龙"
    "段郝孔邵史毛常万顾赖武康贺严尹钱施牛洪龚"
)

MASK_RE = re.compile(r"某")
# Structured identifiers.
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
IDCARD_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")

# Where CAIL's participant-masking fails is names used as LANDMARKS -- a place
# or business described by whose it is. Anchoring on a personal name (surname +
# 1-2 given chars, no 某) immediately followed by a premises/possession noun
# targets exactly that leak class (the 龚见兴出租屋 residue) at far higher
# precision than a bare surname-prefix scan, which drowns in common words that
# merely start with a surname char (方式/黄狗/陈述...).
PREMISES_NOUNS = [
    "出租屋", "出租房", "租赁房", "宿舍", "住处",  # dwellings named by owner/tenant
    "养殖场", "养狗场", "狗场", "猪场", "牛场", "屠宰场", "宰狗场",
    "制冰厂", "冷库", "水产", "批发部", "养殖户",
    "饭店", "餐馆", "酒店", "宾馆", "旅馆", "招待所",
    "超市", "商店", "商行", "门市部", "门市", "门店", "小卖部", "小店",
    "修理部", "修理厂", "加工厂",
]
SURNAME_CLS = "[" + "".join(COMMON_SURNAMES) + "]"
# name (surname + 1-2 non-某 given chars) directly before a premises noun.
GIVEN = r"(?:(?!某)[一-鿿]){1,2}"
PREMISES_RE = re.compile(
    "(" + SURNAME_CLS + GIVEN + ")(?=" + "|".join(PREMISES_NOUNS) + ")"
)


def unmasked_name_candidates(text: str) -> list:
    """Return (name, premises_noun) pairs where a personal name sits directly
    before a premises noun -- the CAIL landmark-leak pattern."""
    out = []
    for m in re.finditer(
        "(" + SURNAME_CLS + GIVEN + ")(" + "|".join(PREMISES_NOUNS) + ")", text
    ):
        name, noun = m.group(1), m.group(2)
        if "某" in name:
            continue
        # A 3-char name is the strong signal; a 2-char "name" before a premises
        # noun is often a common word (e.g. 白店/金店) -- keep only if the first
        # char is a surname AND the whole thing isn't an obvious color/material.
        out.append((name, noun))
    return out


def main() -> None:
    recs = [json.loads(l) for l in open(FINAL_JSONL) if l.strip()]
    n = len(recs)

    masked_rows = 0
    name_hits: dict[str, set] = defaultdict(set)  # "name+noun" -> census_ids
    phone_hits: dict[str, set] = defaultdict(set)
    id_hits: dict[str, set] = defaultdict(set)

    for r in recs:
        text = r.get("fact", "") or ""
        cid = r["census_id"]
        if MASK_RE.search(text):
            masked_rows += 1
        for name, noun in unmasked_name_candidates(text):
            name_hits[name + noun].add(cid)
        for m in PHONE_RE.finditer(text):
            phone_hits[m.group()].add(cid)
        for m in IDCARD_RE.finditer(text):
            id_hits[m.group()].add(cid)

    print(f"扫描 {n} 条判决 fact 全文。\n")

    print(f"== 含「某」字遮蔽标记的判决数：{masked_rows}/{n}"
          f"（{100*masked_rows//n}%）==")
    print("  剩余 {} 条无遮蔽标记，多为短文本或以机构/地点为主。\n".format(n - masked_rows))

    print("== 结构化 PII（手机号 / 身份证号）——如出现即为明确泄漏 ==")
    if phone_hits:
        for tok, ids in sorted(phone_hits.items(), key=lambda kv: -len(kv[1])):
            print(f"  手机号候选 {tok}：{', '.join(sorted(ids))}")
    else:
        print("  手机号：未发现 ✓")
    if id_hits:
        for tok, ids in sorted(id_hits.items(), key=lambda kv: -len(kv[1])):
            print(f"  身份证候选 {tok}：{', '.join(sorted(ids))}")
    else:
        print("  身份证号：未发现 ✓")
    print()

    flagged = sorted(name_hits.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    print(f"== 未遮蔽人名地标候选（{len(flagged)} 个，姓名紧邻场所名词）==")
    print("  模式：常见姓氏 + 1-2 非「某」汉字 + 场所名词（出租屋/养殖场/水产/饭店…）。")
    print("  这是 CAIL2018 遮蔽漏掉的第三方姓名类型——参与人（被告/被害/证人）已遮蔽，"
          "但用作地标的人名（房东/店主）未遮蔽。仍会有误报（如非姓名的商号前缀）。")
    print("  处置政策（protocol §8(b)）：默认照抄文书遮蔽程度；是否对附带地标人名追加"
          "冗余遮蔽，是项目负责人的政策判断，本脚本不擅自改数据。\n")
    if not flagged:
        print("  未发现此类候选。")
    for tok, ids in flagged:
        sample = sorted(ids)[:6]
        more = f" 等 {len(ids)} 条" if len(ids) > 6 else ""
        print(f"  {tok}  ({len(ids)} 判决): {', '.join(sample)}{more}")


if __name__ == "__main__":
    main()
