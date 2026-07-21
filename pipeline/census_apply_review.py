#!/usr/bin/env python3
import json, csv
from pathlib import Path
from collections import Counter

# 加载 AI 分类
classified = {r['census_id']: r for r in (json.loads(l) for l in open('pipeline/census_classified.jsonl') if l.strip())}

# 加载用户审核结果（CSV）
user_review = {}
# Try both locations: current dir and parent (repo root)
if Path('census_review_result.csv').exists():
    csv_input = 'census_review_result.csv'
else:
    csv_input = '../census_review_result.csv'
with open(csv_input, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        user_review[row['census_id']] = row

# 合并与筛选
final = []
for r in classified.values():
    if r['census_id'] in user_review:
        u = user_review[r['census_id']]
        # 用户标注的分类覆盖 AI 分类
        if u.get('category_user'):
            r['category_final'] = u['category_user']
        else:
            r['category_final'] = r['category']
        r['included'] = u.get('included', '').lower() == 'true'
        r['review_notes'] = u.get('notes', '')
    else:
        # 未审核项目（非审核集中的）自动纳入 AI 分类为 non-fp 的
        r['category_final'] = r['category'] if r['category'] != 'fp' else 'fp'
        r['included'] = r['category'] != 'fp'
        r['review_notes'] = '[auto-included]'

    # 仅保留 included=true 的
    if r['included']:
        final.append(r)

final.sort(key=lambda x: x['census_id'])

# 输出 JSONL（中间格式）
with open('pipeline/census_final.jsonl', 'w') as f:
    for r in final:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f"✓ 最终纳入 {len(final)}/754 条判决")

# 导出公开 CSV（带 UTF-8 BOM）
csv_path = 'release/v0.2/judgments_census.csv'
Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=[
        'census_id', 'cail_file', 'cail_idx', 'category', 'animal', 'death', 'n_animals',
        'motive', 'summary', 'charges', 'fact', 'confidence', 'review_status'
    ])
    w.writeheader()
    for r in final:
        w.writerow({
            'census_id': r['census_id'],
            'cail_file': r['cail_file'],
            'cail_idx': r['cail_idx'],
            'category': r.get('category_final', r['category']),
            'animal': r.get('animal', ''),
            'death': r.get('death', ''),
            'n_animals': r.get('n_animals', ''),
            'motive': r.get('motive', ''),
            'summary': r.get('summary', ''),
            'charges': '|'.join(r.get('charges', [])),
            'fact': r.get('fact', ''),
            'confidence': r.get('confidence', ''),
            'review_status': 'reviewed' if r['census_id'] in user_review else 'auto'
        })

print(f"✓ 导出公开 CSV: {csv_path}")

# 打印 PRISMA 流水
print("\n=== PRISMA 流水 ===")
print("检索命中        → 754")
print("去重查证对数    → " + str(len(json.load(open('pipeline/census_dedup_pairs.json')))) + " 对")
print("分类分布:")
for cat, cnt in Counter(r['category'] for r in classified.values()).most_common():
    print(f"  {cat:22s} {cnt:3d}")
print(f"人工审核纳入    → {len(final)}")
