#!/usr/bin/env python3
import json, difflib

recs = [json.loads(l) for l in open('pipeline/census_classified.jsonl') if l.strip()]
non_fp = [r for r in recs if r['category'] != 'fp']

print(f"检测 {len(non_fp)} 条 non-fp 记录的重复...")

# 两两相似度（仅对 fact 字段前 500 字）
dups = []
for i, r1 in enumerate(non_fp):
    for r2 in non_fp[i+1:]:
        sim = difflib.SequenceMatcher(None, r1['fact'][:500], r2['fact'][:500]).ratio()
        if sim > 0.75:
            dups.append({
                'r1_id': r1['census_id'],
                'r2_id': r2['census_id'],
                'similarity': round(sim, 3),
                'r1_cat': r1['category'],
                'r2_cat': r2['category']
            })

if dups:
    print(f"⚠ 发现 {len(dups)} 对疑似重复（相似度>0.75）:")
    for d in dups[:10]:  # 仅打前 10 对
        print(f"  {d['r1_id']} ↔ {d['r2_id']} (sim={d['similarity']}, {d['r1_cat']}/{d['r2_cat']})")
    if len(dups) > 10:
        print(f"  ... 及其他 {len(dups)-10} 对")
else:
    print("✓ 无疑似重复对")

# 保存给后续人工审核
with open('pipeline/census_dedup_pairs.json', 'w') as f:
    json.dump(dups, f, ensure_ascii=False, indent=2)
print(f"✓ 重复对清单存于 pipeline/census_dedup_pairs.json")
