#!/usr/bin/env python3
import json, random
from collections import Counter

# 固定随机种子：审核集抽样必须可复现，否则"我们审了一个随机样本"这句话在论文里
# 不可核查（重跑得到不同样本）。注意：本项目实际发布的 v0.2 审核集是在加此种子
# 之前抽取的，其确切构成以 census_audit_set_ids.txt 冻结记录为准（见 protocol §10）。
random.seed(20260721)

recs = [json.loads(l) for l in open('pipeline/census_classified.jsonl') if l.strip()]

# 筛选审核集
borderline = [r for r in recs if r['category'] == 'borderline']
low_conf_nonfp = [r for r in recs if r['category'] != 'fp' and r['confidence'] == 'low']
true_high_conf = [r for r in recs if r['category'] != 'fp' and r['confidence'] == 'high']
fp_recs = [r for r in recs if r['category'] == 'fp']

print(f"审核集构成:")
print(f"  borderline:          {len(borderline)}")
print(f"  low-conf non-fp:     {len(low_conf_nonfp)}")
print(f"  true-high (QC样本):  {min(40, len(true_high_conf))}")
print(f"  fp (QC样本):         {min(20, len(fp_recs))}")

# 去重：low_conf_nonfp 与 borderline 的并集
low_ids = set(r['census_id'] for r in low_conf_nonfp)
border_ids = set(r['census_id'] for r in borderline)
overlap = len(low_ids & border_ids)
print(f"  (borderline vs low-conf 重叠: {overlap})")

audit_set = borderline + [r for r in low_conf_nonfp if r['census_id'] not in border_ids]

# 加 QC 样本
audit_set += random.sample(true_high_conf, min(40, len(true_high_conf)))
audit_set += random.sample(fp_recs, min(20, len(fp_recs)))

audit_set.sort(key=lambda x: x['census_id'])

print(f"\n合计审核项: {len(audit_set)}")
print(f"  其中 fp: {sum(1 for r in audit_set if r['category'] == 'fp')}")

# 保存
with open('pipeline/census_review_items.json', 'w') as f:
    json.dump(audit_set, f, ensure_ascii=False)
print(f"✓ 审核集存于 pipeline/census_review_items.json")
