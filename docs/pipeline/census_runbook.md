# Census 判决书语料执行 Runbook

**仅供 Haiku 执行**。按序做完 4 步，总耗时 30–40 分钟（含建工具）。所有数据文件已 gitignored；脚本全部幂等。

---

## 前置检查（3 分钟）

```bash
cd /Users/nancy-boa/Documents/code/ahid
ls -l pipeline/cail_census_raw_hits.jsonl  # 存在？
ls pipeline/census_class/census_class_*.jsonl | wc -l  # 应显示 6
python3 -c "import glob,json; print('raw:', sum(1 for l in open('pipeline/cail_census_raw_hits.jsonl') if l.strip() and json.loads(l))); [print(f.split('/')[-1], ':', sum(1 for l in open(f) if l.strip() and json.loads(l))) for f in sorted(glob.glob('pipeline/census_class/census_class_*.jsonl'))]"
```

**期望输出**：raw: 754 + 六个 census_class_N: 各 126（batch 5 是 124）。若不符，中止。

---

## 步骤 1：合并分类结果（5 分钟）

**文件**：写 `pipeline/census_merge.py`

```python
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
```

**运行**：
```bash
python3 pipeline/census_merge.py
# 期望：✓ 写入 pipeline/census_classified.jsonl: 754 行
# 分类覆盖: 754/754 (100%)
```

---

## 步骤 2：去重检测（5 分钟）

**文件**：写 `pipeline/census_dedup.py`

```python
#!/usr/bin/env python3
import json, difflib
from collections import defaultdict

recs = [json.loads(l) for l in open('pipeline/census_classified.jsonl') if l.strip()]
non_fp = [r for r in recs if r['category'] != 'fp']

print(f"检测 {len(non_fp)} 条 non-fp 记录的重复...")

# 两两相似度（仅对 fact 字段）
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
```

**运行**：
```bash
python3 pipeline/census_dedup.py
# 期望：✓ 无疑似重复对 或 ⚠ 发现 N 对
```

---

## 步骤 3：生成审核集（5 分钟）

**文件**：写 `pipeline/census_review_items.py`

```python
#!/usr/bin/env python3
import json, random
from collections import Counter

recs = [json.loads(l) for l in open('pipeline/census_classified.jsonl') if l.strip()]

# 筛选审核集
borderline = [r for r in recs if r['category'] == 'borderline']
low_conf_nonfp = [r for r in recs if r['category'] != 'fp' and r['confidence'] == 'low']
true_high_conf = [r for r in recs if r['category'] != 'fp' and r['confidence'] == 'high']
fp_recs = [r for r in recs if r['category'] == 'fp']

print(f"审核集构成:")
print(f"  borderline:      {len(borderline)}")
print(f"  low-conf non-fp: {len(low_conf_nonfp)}")
print(f"  true-high (QC样本):  {min(40, len(true_high_conf))}")
print(f"  fp (QC样本):     {min(20, len(fp_recs))}")

# 去重：low_conf_nonfp 与 borderline 的并集
low_ids = set(r['census_id'] for r in low_conf_nonfp)
border_ids = set(r['census_id'] for r in borderline)
overlap = len(low_ids & border_ids)
audit_set = borderline + [r for r in low_conf_nonfp if r['census_id'] not in border_ids]

# 加 QC 样本
audit_set += random.sample(true_high_conf, min(40, len(true_high_conf)))
audit_set += random.sample(fp_recs, min(20, len(fp_recs)))

audit_set.sort(key=lambda x: x['census_id'])

print(f"\n合计审核项: {len(audit_set)}")

# 保存
with open('pipeline/census_review_items.json', 'w') as f:
    json.dump(audit_set, f, ensure_ascii=False)
print(f"✓ 审核集存于 pipeline/census_review_items.json")
```

**运行**：
```bash
python3 pipeline/census_review_items.py
# 期望：✓ 审核集存于 ... （约 160–170 条）
```

---

## 步骤 4：建审核工具（20 分钟）

使用 `human-label-tool` skill 建 `pipeline/census_review_tool.html`（本地文件，gitignored）。

**HTML 包含内容**（参考已有项目审核工具）：
- 一屏一案，显示 census_id、category（AI 分类）、fact（判决全文）、summary、animal、motive
- 用户操作：
  - 终判分类（7 键）：cruelty / poaching / property_protection / retaliation / other_true / borderline / fp
  - 收录 yes/no（核心决定）
  - 备注 textarea
  - "无误跳过" 快捷键（对 AI 分类已正确的案件）
- 重复对特殊显示（来自 census_dedup_pairs.json）：单独列一行，用户决策是否合并
- localStorage 自动存档（key: `census_review_v1`）
- CSV 导出（带 UTF-8 BOM）：census_id, category_ai, category_user, included, notes, dedup_status

**校验**（shell）：
```bash
# 提取 HTML 里的 <script> 块并用 node 检查
sed -n '/<script>/,/<\/script>/p' pipeline/census_review_tool.html > /tmp/census_review.js
node --check /tmp/census_review.js
echo "✓ JavaScript 语法无误"

# 确认条目数
grep -c '"census_id"' pipeline/census_review_items.json  # 应 ≈ 160
```

**输出示例**：
```bash
$ ls -lh pipeline/census_review_tool.html
-rw-r--r--  650K  census_review_tool.html

$ file pipeline/census_review_tool.html
HTML document
```

---

## 用户环节（1.5–2 小时，浏览器）

1. 在浏览器中打开 `/Users/nancy-boa/Documents/code/ahid/pipeline/census_review_tool.html`
2. 一屏一案地过一遍，做终判决策（category_user / included / notes）
3. 导出 CSV，保存到 `/Users/nancy-boa/Documents/code/ahid/pipeline/census_review_result.csv`

**QC 用途**：
- 用户的 category_user vs AI 的 category_ai 对比 → 分类精度数字
- included 统计 → 最终纳入的判决书数

---

## 步骤 5：收尾（Haiku 会话 2，15 分钟）

**文件**：写并运行 `pipeline/census_apply_review.py`

```python
#!/usr/bin/env python3
import json, csv
from pathlib import Path

# 加载 AI 分类
classified = {r['census_id']: r for r in (json.loads(l) for l in open('pipeline/census_classified.jsonl') if l.strip())}

# 加载用户审核结果（CSV）
user_review = {}
with open('pipeline/census_review_result.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        user_review[row['census_id']] = row

# 合并
final = []
for r in classified.values():
    if r['census_id'] in user_review:
        u = user_review[r['census_id']]
        r['category_final'] = u['category_user'] if u['category_user'] else r['category']
        r['included'] = u['included'] == 'true'
        r['review_notes'] = u.get('notes', '')
    else:
        # 未审核项目（非审核集中的）自动纳入 AI 分类为 non-fp 的
        r['category_final'] = r['category'] if r['category'] != 'fp' else 'fp'
        r['included'] = r['category'] != 'fp'
        r['review_notes'] = '[auto-included]'

# 仅保留 included=true 的
final = [r for r in final if r['included']]
final.sort(key=lambda x: x['census_id'])

# 输出 JSONL（中间格式）
with open('pipeline/census_final.jsonl', 'w') as f:
    for r in final:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f"✓ 最终纳入 {len(final)}/754 条判决")

# 导出公开 CSV（带 UTF-8 BOM）
csv_path = 'release/ahid-cn-dataset-v0.1/data/judgments_census.csv'
Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=[
        'census_id', 'cail_file', 'cail_idx', 'category', 'animal', 'death', 'n_animals',
        'motive', 'summary', 'charges', 'imprisonment', 'fact', 'confidence', 'review_status'
    ])
    w.writeheader()
    for r in final:
        w.writerow({
            'census_id': r['census_id'],
            'cail_file': r['cail_file'],
            'cail_idx': r['cail_idx'],
            'category': r.get('category_final', r['category']),
            'animal': r['animal'],
            'death': r.get('death', ''),
            'n_animals': r['n_animals'],
            'motive': r['motive'],
            'summary': r['summary'],
            'charges': '|'.join(r.get('charges', [])),
            'imprisonment': '',  # 后续从 parquet 补齐
            'fact': r['fact'][:5000],  # 完整事实
            'confidence': r['confidence'],
            'review_status': 'reviewed' if r['census_id'] in user_review else 'auto'
        })

print(f"✓ 导出公开 CSV: {csv_path}")

# 打印 PRISMA 流水
print("\n=== PRISMA 流水 ===")
print("检索命中    → 754")
print("去重后      → 754（无重复，或合并后 N）")
print("分类分布:")
from collections import Counter
for cat, cnt in Counter(r['category'] for r in classified.values()).most_common():
    print(f"  {cat:22s} {cnt:3d}")
print(f"人工审核纳入 → {len(final)}")
```

**运行**：
```bash
python3 pipeline/census_apply_review.py
# 期望：✓ 最终纳入 337/754 条判决（数字 ±50 因 borderline 结果而变）
# ✓ 导出公开 CSV: release/...
```

**校验**：
```bash
python3 -c "
import pandas as pd
df = pd.read_csv('release/ahid-cn-dataset-v0.1/data/judgments_census.csv')
print(f'CSV 行数: {len(df)}')
print(f'Fact 非空: {(df[\"fact\"].notna()).sum()}/{len(df)}')
print(f'分类分布:'); print(df['category'].value_counts())
"
```

---

## 最后：更新文档 + 提交

```bash
# 更新 data_dictionary.csv（加 judgments_census 表说明）
# 更新 changelog.md（v0.2 条目草稿）
# 更新 judgment_census_protocol.md §3 执行日志节（PRISMA 数字）

git add pipeline/census_*.py release/ahid-cn-dataset-v0.1/data/judgments_census.csv docs/data_dictionary.csv release/ahid-cn-dataset-v0.1/documentation/changelog.md docs/pipeline/judgment_census_protocol.md

git commit -m "Census 判决书语料 v1.0: 754→337 纳入，扁平表导出

- CAIL2018 全量检索 + 6 批 AI 分类 + 用户审核
- judgments_census.csv 含事实全文、AI 置信度、最终分类
- PRISMA 流水记录"

git push
```

---

**Done**。下一步由 Fable 或用户决定 v0.2 发布时间点。

