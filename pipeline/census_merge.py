#!/usr/bin/env python3
import json, glob, sys
from pathlib import Path

# 加载 raw_hits（索引by (file,idx)）
raw_hits = {}
for line in open('pipeline/cail_census_raw_hits.jsonl'):
    if not line.strip(): continue
    rec = json.loads(line)
    raw_hits[(rec['file'], rec['idx'])] = rec

# 加载 6 个分类批次
classifications = {}
for fpath in sorted(glob.glob('pipeline/census_class/census_class_*.jsonl')):
    for line in open(fpath):
        if not line.strip(): continue
        rec = json.loads(line)
        classifications[(rec['file'], rec['idx'])] = rec

# 合并
merged = []
missing = 0
for key in raw_hits:
    if key not in classifications:
        print(f"WARNING: {key} 无分类结果", file=sys.stderr)
        missing += 1
    raw_rec = raw_hits[key]
    class_rec = classifications.get(key, {})
    merged_rec = {
        'census_id': f"CAIL-{key[0]}-{key[1]:06d}",
        'cail_file': key[0],
        'cail_idx': key[1],
        'category': class_rec.get('cat', 'unknown'),
        'animal': class_rec.get('animal', ''),
        'death': class_rec.get('death', None),
        'n_animals': class_rec.get('n_animals', ''),
        'motive': class_rec.get('motive', ''),
        'summary': class_rec.get('summary', ''),
        'confidence': class_rec.get('conf', 'low'),
        'charges': raw_rec.get('accusation', []),
        'fact': raw_rec.get('fact', '')
    }
    merged.append(merged_rec)

merged.sort(key=lambda x: (x['cail_file'], x['cail_idx']))

# 输出
out_path = 'pipeline/census_classified.jsonl'
with open(out_path, 'w') as f:
    for rec in merged:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

print(f"✓ 写入 {out_path}: {len(merged)} 行")
print(f"  分类覆盖: {len(merged) - missing}/754 ({100*(len(merged)-missing)//754}%)")
if missing > 0:
    print(f"  ⚠ 缺失分类: {missing}")
    sys.exit(1)

# 分类计数
from collections import Counter
cat_cnt = Counter(r['category'] for r in merged)
print("  分类分布:")
for cat, cnt in cat_cnt.most_common():
    print(f"    {cat:22s} {cnt:3d}")

sys.exit(0)
