#!/usr/bin/env python3
"""
产业链推定标准（用户决定 2026-07-21，v2 修订）：
borderline + 非明确死亡(death != True) 案例，作案工具/动机模式与已确认 poaching
案例相同（夹狗钳/铁丝圈套/毒镖等捕狗手段），一律归入 poaching——盗窃本身
（脱离主人占有、被陌生人捕捉/搬运/囚禁）即构成动物受害，不要求死亡结局，
也不因为后来被追回就不算数（追回只说明案件侦破，不代表被偷期间没有经历
强行捕捉/关押/运输——类比人被绑架后获救仍是绑架受害者）。

每条升级记录都打上 outcome_documented=false（若无死亡实据）或
recovered_after_theft=true（若判决记载了追回），如实区分证据类型，
供方法论透明披露：论文里能清楚说明"多少条有直接死亡证据、多少条是
盗窃既遂后追回、多少条是纯粹的作案模式推定"。
"""
import json

RECOVERED_KEYWORDS = ['追回', '发还']

# 敲诈借口案：动物"受害"只是敲诈者单方声称，判决未认定为事实
EXTORTION_PRETEXT_IDS = {
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-084547',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-156001',
}
# 意外死亡案：无人为恶意，判决关注的是后续纠纷不是动物伤害本身
ACCIDENTAL_DEATH_IDS = {
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-162232',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-166263',
}
# 加害人未定罪的真实死亡案：狗确实被毒死(death=True 有实据)，但下毒者身份未坐实，
# 判决实际审理的是错误怀疑引发的非法拘禁罪——动物伤害真实发生，归 other_true
UNCONFIRMED_PERP_IDS = {
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-174589',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-052287',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-302930',
    'CAIL-cail_valid.parquet-007320',
}

# cruelty vs other_true 边界修正（用户例：踢飞路人牵的小狗案）：
# 区分标准 = 动物是不是暴力的直接目标/诱因（狗叫/狗咬→针对狗施暴=cruelty），
# 还是死亡只是打砸财物/入室行窃时的附带后果（暴力真正指向财物或人=other_true）
CRUELTY_RECLASSIFY_IDS = {
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-130853',  # 与 013297 为同案(相似度0.986)，一致性修正
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-002017',  # 狗叫→木棍打死，与已有cruelty案194672同构
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-282830',  # 被狗咬→报复打死2条狗，直接针对动物的暴力
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-269073',  # 用户指出：醉酒踢飞路人牵的小狗
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-380166',  # 269073 同案重复记录
    # 用户人工审核第二轮：原 AI 误标 poaching，实为直接针对狗施暴（被关键词"狗/毒/打"误触发）
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-099031',   # 狗吠→扔石块打狗
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-157540',   # 狗惊吓→铁锹追打
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-159975',  # 酒后持砖砸拴着的狗
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-350062',  # 嫌狗吼叫去打狗
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-036056',  # 嫌狗吠叫持石头击打
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-270139',  # 原 retaliation：敌敌畏毒死邻居6条狗，手段/规模够重升级 cruelty
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-252194',  # 向行驶三轮车下扔活狗做碰瓷道具，直接置狗于危险
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-198234',   # 斗狗厂看斗狗引发纠纷——组织斗狗本身即systemic cruelty
}

# 下毒指控类：判决未认定"动物确实被下毒"为事实（单方声称/怀疑），但用户决定
# 采信声称本身计入 cruelty（与"产业链推定"同一逻辑延伸：不苛求判决直接实锤）。
# 标 claim_verified=False 如实区分"判决认定的事实" vs "案件当事人的声称"。
CRUELTY_UNVERIFIED_CLAIM_IDS = {
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-114557',   # 疑似投毒鸡肝毒狗，怀疑人被殴打（投毒未被判决认定）
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-193059',   # 以"药狗"为由敲诈
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-084547',  # 以"毒死其细狗"为由敲诈（原已标fp，改标cruelty）
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-156001',  # 084547 同案重复记录
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-277414',  # 疑似投毒，围殴致死疑凶（狗本身结局未描述）
}

# 加害人未定罪但动物死亡有实据的案例：与上面"未认定"不同——狗确实吃毒饵死了(死亡实据充分)，
# 只是下毒者身份未坐实。用户决定这类归 cruelty（非 other_true）：伤害本身是真实的。
CONFIRMED_HARM_UNKNOWN_PERP_TO_CRUELTY = UNCONFIRMED_PERP_IDS  # 见下方定义后引用

# 偷狗现象即计入（用户决定 2026-07-21 通用原则）：只要案情涉及"偷狗"情节
# （既遂/未遂/嫌疑/持有作案工具/以此为敲诈借口），不论动物本身是否受伤——
# 哪怕受伤的是嫌疑人或围殴者——一律归入 poaching，因为判决书语料本就是在
# 记录"偷狗现象"整体的社会代价，不只是"确认无误的动物身体伤害"。
# animal_directly_harmed=False 标注这类记录里动物本身未被证实受伤，供论文
# 拆分"偷狗现象总规模" vs "动物真实受伤的子集"。
THEFT_PHENOMENON_NO_ANIMAL_HARM_IDS = {
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-214682',  # 发现偷狗贼将其砍伤（伤的是贼，狗无恙）
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-204549',  # 村民围殴疑似偷狗者致其死亡（狗无恙,人死亡）
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-322535',  # 车内查获偷狗工具,逃检袭警（无完整作案描述）
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-333252',  # 拿"偷狗"当敲诈借口毁人财物（无真实动物出现）
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-119321',  # 争夺疑似丢失的狗引发打人（狗未受伤）
}

# 原始 AI 分类的确认性修正（读原文核实,不是判断分歧）
FP_TO_POACHING_CONFIRMED_THEFT = {
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-085350',  # 从养狗场真实偷出多条狗,原判fp是错的
}
POACHING_TO_FP_NO_ANIMAL = {
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-285052',  # 纯人身纠纷(赔偿协商争执殴打),此条无动物受害描述
}

recs = [json.loads(l) for l in open('pipeline/census_classified.jsonl') if l.strip()]

presumed, marked_excluded, reclassified = [], [], []

for r in recs:
    if r['category'] == 'other_true' and r['census_id'] in CRUELTY_RECLASSIFY_IDS:
        r['category'] = 'cruelty'
        r['correction_note'] = 'cruelty/other_true 边界修正：动物是暴力直接目标/诱因（非打砸财物的附带后果），归入 cruelty'
        reclassified.append((r['census_id'], 'cruelty'))

for r in recs:
    if r['category'] != 'borderline':
        continue
    cid = r['census_id']

    if cid in EXTORTION_PRETEXT_IDS:
        r['category'] = 'fp'
        r['correction_note'] = '敲诈借口：动物受害仅为敲诈者单方声称，判决未认定为事实，不计入真实动物伤害'
        reclassified.append((cid, 'fp'))
        continue
    if cid in ACCIDENTAL_DEATH_IDS:
        r['category'] = 'fp'
        r['correction_note'] = '意外死亡：无人为恶意（车祸/医疗事故），非虐待/伤害行为，判决关注后续纠纷非动物伤害本身'
        reclassified.append((cid, 'fp'))
        continue
    if cid in UNCONFIRMED_PERP_IDS:
        r['category'] = 'other_true'
        r['correction_note'] = '动物死亡真实发生(有实据)，但下毒者身份未坐实/未定罪，判决实际审理的是由此引发的非法拘禁罪；如实标注加害人未确认'
        r['perpetrator_confirmed'] = False
        reclassified.append((cid, 'other_true'))
        continue

    # 剩余：偷狗产业链模式,不论 death 字段是 False 还是"不详"字符串,一律归 poaching
    # （盗窃既遂本身即构成受害，追回与否不改变这一点）
    if r['death'] is not True:
        text = (r.get('motive', '') or '') + (r.get('summary', '') or '')
        has_recovered = any(k in text for k in RECOVERED_KEYWORDS)

        r['category'] = 'poaching'
        r.pop('suggested_included', None)  # 清除上一版遗留的排除建议
        if has_recovered:
            r['recovered_after_theft'] = True
            r['correction_note'] = '盗窃既遂后被追回：狗曾脱离主人占有、经历强行捕捉/搬运，追回不改变已发生的受害事实；归入 poaching'
        else:
            r['outcome_documented'] = False
            r['correction_note'] = '产业链推定：判决书未明写动物最终结局，但盗窃手段/动机与已确认 poaching 案例一致，按用户政策纳入 poaching（非判决原文直接证据）'
        presumed.append(cid)

# --- 第二轮：用户人工审核（93条QC样本）反馈的修正，按 ID 直接定位，不再依赖当前 category ---
round2 = []
for r in recs:
    cid = r['census_id']

    if cid in CRUELTY_RECLASSIFY_IDS and r['category'] != 'cruelty':
        r['category'] = 'cruelty'
        r['correction_note'] = '人工审核修正：直接针对动物施暴或手段/规模够重，原AI分类有误（多为被"狗/毒/打"关键词误触发标成poaching）'
        round2.append((cid, 'cruelty'))

    elif cid in CRUELTY_UNVERIFIED_CLAIM_IDS and r['category'] != 'cruelty':
        r['category'] = 'cruelty'
        r['claim_verified'] = False
        r['correction_note'] = '下毒指控未经判决认定为事实（单方声称/怀疑），用户决定采信声称本身计入cruelty，标注claim_verified=False'
        round2.append((cid, 'cruelty'))

    elif cid in CONFIRMED_HARM_UNKNOWN_PERP_TO_CRUELTY and r['category'] != 'cruelty':
        r['category'] = 'cruelty'
        r['perpetrator_confirmed'] = False
        r['correction_note'] = '动物死亡有实据(确实吃毒饵身亡)，加害人身份未坐实但伤害本身真实，归cruelty而非other_true'
        round2.append((cid, 'cruelty'))

    elif cid in THEFT_PHENOMENON_NO_ANIMAL_HARM_IDS:
        r['category'] = 'poaching'
        r['animal_directly_harmed'] = False
        r['correction_note'] = '偷狗情节即计入(用户通用原则)：案情涉及偷狗，但本记录中动物本身未被证实受伤(受伤/死亡的是嫌疑人或围殴者)；归poaching并标注animal_directly_harmed=False'
        round2.append((cid, 'poaching'))

    elif cid in FP_TO_POACHING_CONFIRMED_THEFT:
        r['category'] = 'poaching'
        r['correction_note'] = '原AI分类核实有误：判决记载狗确实被盗走(非仅嫌疑)，是真实盗窃既遂案例'
        round2.append((cid, 'poaching'))

    elif cid in POACHING_TO_FP_NO_ANIMAL:
        r['category'] = 'fp'
        r['correction_note'] = '原AI分类核实有误：本记录事实为纯人身纠纷(赔偿协商引发殴打)，无任何动物受害描述'
        round2.append((cid, 'fp'))

with open('pipeline/census_classified.jsonl', 'w') as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f"✓ 产业链推定升级为 poaching: {len(presumed)} 条")
print(f"✓ 标记建议排除（追回未受伤，明确证据）: {len(marked_excluded)} 条 — {marked_excluded}")
print(f"✓ 特殊性质重分类: {len(reclassified)} 条 — {reclassified}")
print(f"✓ 第二轮人工审核修正: {len(round2)} 条 — {round2}")

from collections import Counter
cat_cnt = Counter(r['category'] for r in recs)
print("\n更新后分类分布:")
for cat, cnt in cat_cnt.most_common():
    print(f"  {cat:22s} {cnt:3d}")
