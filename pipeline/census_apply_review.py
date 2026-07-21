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

# 证据透明标记是分类语境相关的：偷狗/产业链语境 vs 蓄意虐待语境。
# apply_corrections 在它当时赋予的分类下打标记，但用户人工审核（或后续 round2
# 规则）可能把分类改到别处——那时旧标记就与终判分类矛盾，必须清除，否则会出现
# "retaliation 行带 animal_directly_harmed=false（偷狗语境标记）"这类自相矛盾的行。
POACHING_CONTEXT_FLAGS = ('outcome_documented', 'recovered_after_theft', 'animal_directly_harmed')
CRUELTY_CONTEXT_FLAGS = ('claim_verified', 'perpetrator_confirmed')


def normalize_metadata(rec):
    """把证据标记与 correction_note 对齐到终判分类 category_final。"""
    cat = rec['category_final']
    if cat != 'poaching':
        for f in POACHING_CONTEXT_FLAGS:
            rec.pop(f, None)
    if cat != 'cruelty':
        for f in CRUELTY_CONTEXT_FLAGS:
            rec.pop(f, None)
    # 若人工终判覆盖了 apply_corrections 赋予的分类(rec['category'])，那条自动生成
    # 的 correction_note 描述的是已被推翻的中间分类，与终判矛盾——替换为如实说明。
    if rec.get('correction_note') and cat != rec['category']:
        rec['correction_note'] = '人工审核终判：以人工分类为准，自动推定/修正分类已被覆盖'


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

    normalize_metadata(r)

    # 仅保留 included=true 的
    if r['included']:
        final.append(r)

final.sort(key=lambda x: x['census_id'])

# 输出 JSONL（中间格式）
with open('pipeline/census_final.jsonl', 'w') as f:
    for r in final:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f"✓ 最终纳入 {len(final)}/754 条判决")


# 证据类型透明标记（census_apply_corrections.py 生成）——只在非默认情形写入，
# 空值 = 标准情形/不适用。这些标记让方法论文能如实拆分"判决实证的伤害" vs
# "产业链推定" vs "未经判决认定的声称"，而不是把三类混为一谈。
def fmt_flag(r, key):
    v = r.get(key)
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    return ''


# 导出公开 CSV（带 UTF-8 BOM）
csv_path = 'release/v0.2/judgments_census.csv'
Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=[
        'census_id', 'cail_file', 'cail_idx', 'category', 'animal', 'death', 'n_animals',
        'motive', 'summary', 'charges', 'fact', 'confidence', 'review_status',
        'animal_directly_harmed', 'outcome_documented', 'recovered_after_theft',
        'claim_verified', 'perpetrator_confirmed', 'correction_note'
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
            'review_status': 'reviewed' if r['census_id'] in user_review else 'auto',
            'animal_directly_harmed': fmt_flag(r, 'animal_directly_harmed'),
            'outcome_documented': fmt_flag(r, 'outcome_documented'),
            'recovered_after_theft': fmt_flag(r, 'recovered_after_theft'),
            'claim_verified': fmt_flag(r, 'claim_verified'),
            'perpetrator_confirmed': fmt_flag(r, 'perpetrator_confirmed'),
            'correction_note': r.get('correction_note', ''),
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
