"""Internal-consistency validation for the published judgment census CSV.

Pure verification: every check either passes or names a specific offending row.
Run after census_apply_review.py regenerates the CSV; exits non-zero on any
hard failure so it can gate a release. Locks the invariants that a real bug
already violated once (transparency flags drifting onto the wrong category
after human review overrode the automated classification).

Run: python3 pipeline/census_validate.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

CSV = Path(__file__).parent.parent / "release/v0.2/judgments_census.csv"

VALID_CATEGORIES = {
    "poaching", "property_protection", "other_true", "cruelty",
    "retaliation", "borderline",  # 'fp' must never appear (excluded on export)
}
VALID_CONFIDENCE = {"high", "med", "low"}
VALID_REVIEW_STATUS = {"reviewed", "auto"}

# Each flag's only non-blank value, and the single category it may appear on.
POACHING_FLAGS = {
    "outcome_documented": "false",
    "recovered_after_theft": "true",
    "animal_directly_harmed": "false",
}
CRUELTY_FLAGS = {
    "claim_verified": "false",
    "perpetrator_confirmed": "false",
}


def main() -> None:
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    errors: list[str] = []

    def err(msg: str) -> None:
        errors.append(msg)

    # 1. row count + unique id
    ids = [r["census_id"] for r in rows]
    if len(ids) != len(set(ids)):
        dupes = {i for i in ids if ids.count(i) > 1}
        err(f"census_id 重复: {sorted(dupes)}")

    for r in rows:
        cid = r["census_id"]

        # 2. census_id 与 cail_file/cail_idx 一致
        expected = f"CAIL-{r['cail_file']}-{int(r['cail_idx']):06d}"
        if cid != expected:
            err(f"{cid}: census_id 与 file/idx 不符（期望 {expected}）")

        # 3. 枚举合法性
        if r["category"] not in VALID_CATEGORIES:
            err(f"{cid}: 非法 category={r['category']!r}（fp 不应出现在公开表）")
        if r["confidence"] not in VALID_CONFIDENCE:
            err(f"{cid}: 非法 confidence={r['confidence']!r}")
        if r["review_status"] not in VALID_REVIEW_STATUS:
            err(f"{cid}: 非法 review_status={r['review_status']!r}")

        # 4. fact 非空
        if not (r.get("fact") or "").strip():
            err(f"{cid}: fact 为空")

        # 5. 证据标记：值合法 + 只出现在对应 category
        for flag, only_val in POACHING_FLAGS.items():
            v = r[flag].strip()
            if v and v != only_val:
                err(f"{cid}: {flag}={v!r} 非法（只应为空或 {only_val}）")
            if v and r["category"] != "poaching":
                err(f"{cid}: {flag} 出现在非 poaching 行（category={r['category']}）")
        for flag, only_val in CRUELTY_FLAGS.items():
            v = r[flag].strip()
            if v and v != only_val:
                err(f"{cid}: {flag}={v!r} 非法（只应为空或 {only_val}）")
            if v and r["category"] != "cruelty":
                err(f"{cid}: {flag} 出现在非 cruelty 行（category={r['category']}）")

    # ---- report ----
    print(f"校验 {CSV.relative_to(CSV.parent.parent.parent)} — {len(rows)} 行\n")
    checks = [
        ("行数 = 424", len(rows) == 424),
        ("census_id 唯一", len(ids) == len(set(ids))),
        ("无 fp 泄漏进公开表", all(r["category"] != "fp" for r in rows)),
        ("fact 100% 非空", all((r.get("fact") or "").strip() for r in rows)),
        ("证据标记全部与 category 对齐", not any(
            e for e in errors if "出现在非" in e)),
    ]
    for label, ok in checks:
        print(f"  [{'✓' if ok else '✗'}] {label}")

    # 软提示（非错误）：borderline 意为"未决"，出现在公开研究数据集里语义上偏怪，
    # 值得人工确认是否要归入某个确定类别。用户在审核中显式选了 borderline，故不当错误。
    borderline = [r["census_id"] for r in rows if r["category"] == "borderline"]
    if borderline:
        print(f"  [!] 软提示：{len(borderline)} 条终判为 borderline（未决）——"
              f"用户审核时的选择，建议确认是否要落到确定类别：{borderline}")
        print()

    # 近重复对最终数据的影响（信息性，非阻塞）：CAIL2018 test/train 分片间同案重复，
    # 设计上保留双方不合并（附元数据区分），但有效唯一案件数因此 < 名义行数——论文须如实报告。
    pairs_path = Path(__file__).parent / "census_dedup_pairs.json"
    if pairs_path.exists():
        import json
        from collections import Counter, defaultdict
        pairs = json.load(open(pairs_path))
        final_set = set(ids)
        cat_of = {r["census_id"]: r["category"] for r in rows}
        adj: dict = defaultdict(set)
        nodes: set = set()
        cross = []  # 同案不同终判
        for p in pairs:
            a, b = p["r1_id"], p["r2_id"]
            if a in final_set and b in final_set:
                adj[a].add(b); adj[b].add(a); nodes |= {a, b}
                if cat_of[a] != cat_of[b]:
                    cross.append((p["similarity"], cat_of[a], cat_of[b], a, b))
        seen: set = set(); clusters = 0; clustered = 0
        for nd in nodes:
            if nd in seen:
                continue
            clusters += 1; stack = [nd]
            while stack:
                x = stack.pop()
                if x in seen:
                    continue
                seen.add(x); clustered += 1; stack.extend(adj[x] - seen)
        redundant = clustered - clusters
        print(f"  [i] 近重复影响：{len(rows)} 名义行 → 有效唯一案件约 "
              f"{len(rows) - redundant} 条（{clustered} 行属 {clusters} 个同案簇，"
              f"冗余 {redundant} 行为 CAIL 分片间重复，设计上保留不合并）")
        if cross:
            print(f"  [!] {len(cross)} 对同案近重复的终判分类不一致（同一案件两个标签，"
                  f"建议确认是否需要统一）：")
            for sim, ca, cb, a, b in cross:
                print(f"        sim={sim}  {ca} vs {cb}  ({a[-16:]} / {b[-16:]})")
        print()

    if errors:
        print(f"✗ 校验失败：{len(errors)} 处问题")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)
    print("✓ 全部校验通过（含上述软提示，软提示不阻塞）。")


if __name__ == "__main__":
    main()
