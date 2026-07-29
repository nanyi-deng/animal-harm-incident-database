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

# --- 第三轮：HRL-026 定向重扫（2026-07-22）---
# 回溯审计（/data-pipeline-prd）发现假阳性(fp)排除路径从未被系统核验：329条fp仅
# 20条经93条QC样本抽查，其中6条(30%)被救回为真实案件。据此对剩余309条fp中命中
# B层强搭配词（偷狗/毒狗/毒镖等，命中即代表原文含这些词、却仍被AI判fp）的77条
# 做定向全量人工重读，非抽样。逐条判断结果：62条确认为真实偷狗案（嫌疑/未遂/
# 既遂/持有作案工具/以此为敲诈借口等情形，按"偷狗情节即计入"政策归poaching）、
# 1条为报复诬告者案（被诬陷偷狗后行凶报复，归retaliation）、14条核实后确认原
# fp判断正确（如"毒狗"武器用于伤人非偷狗、"偷狗"为诬陷/巧合背景提及等，均非
# 真实动物伤害情节）。14条真fp的具体理由见 docs/pipeline/census_privacy_qa.md
# 姊妹文档 docs/pipeline/judgment_census_protocol.md §10 记录，此处不重复。
RESCAN_FP_TO_POACHING_IDS = {
    'CAIL-cail_exercise_contest_test-00000-of-00001.parquet-006794',
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-008248',
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-029565',
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-047457',
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-085837',
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-094245',
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-004649',
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-021509',
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-032397',
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-091524',
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-163942',
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-166366',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-003938',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-004551',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-066368',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-097063',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-156066',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-191678',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-211254',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-245794',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-296744',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-305323',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-314125',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-367595',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-386949',
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-427315',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-047189',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-101292',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-142925',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-172646',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-176231',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-176704',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-187711',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-188694',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-225973',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-247775',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-264041',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-296011',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-296492',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-317435',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-320845',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-346695',
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-419552',
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-067602',
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-119788',
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-150406',
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-151223',
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-178128',
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-307950',
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-343413',
    'CAIL-cail_first_stage_train-00002-of-00004.parquet-403378',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-033431',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-057602',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-159306',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-195657',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-294387',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-303787',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-340605',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-361360',
    'CAIL-cail_valid.parquet-000740',
    'CAIL-cail_valid.parquet-001070',
    'CAIL-cail_valid.parquet-004852',
}
RESCAN_FP_TO_RETALIATION_IDS = {
    'CAIL-cail_first_stage_train-00000-of-00004.parquet-079930',  # 洪某某被诬陷偷狗后持刀报复诬告者，核心是报复诬告非动物受害
}

# --- 第四轮：HRL-026 A 层假阳性重扫（2026-07-22）---
# B 层（84条，含强搭配词）100%核查完后，对 A 层（248条，不含强搭配词）236条未审核
# fp 做同样的全量人工重读方法学，但先用动物词局部上下文窗口（±35字）做初筛而非
# 逐条通读全文（A 层每条平均含 3+ 起独立犯罪事实，通读成本远高于 B 层单一案情的
# 判决），236 条中筛出 17 条候选做深度全文核实。结果：5 条确认为真实动物伤害，
# 12 条经全文核实后确认原判 fp 无误。真实缺陷率 5/17≈29%（远低于 B 层的 82%，
# 印证了"A层不含强关键词故偏差机制大概率不适用"的推测）。
A_RESCAN_TO_CRUELTY_IDS = {
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-267243',  # 狗对其吠叫，捡石块扔向小狗（未遂，狗是否受伤未证实）
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-401724',  # 小狗踩到被告人，被告人打了小狗
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-299429',  # 怀疑同厂职工将自家狗毒死，怀疑未经判决认定
}
A_RESCAN_TO_POACHING_IDS = {
    'CAIL-cail_first_stage_train-00001-of-00004.parquet-315202',  # 指控邻居偷宰其狗，指控未经判决认定（双方各执一词）
}
# 宠物医疗事故致死：新的证据类型，不完全匹配现有 outcome_documented/
# claim_verified/animal_directly_harmed 任一标记——狗死亡是双方无争议的既定
# 背景事实（案件本身即因此引发），但医疗过失是否成立未经司法认定，判决审理的
# 是后续的故意毁坏财物行为。不强套现有标记，仅在 correction_note 如实说明。
A_RESCAN_TO_OTHER_TRUE_IDS = {
    'CAIL-cail_first_stage_test-00000-of-00001.parquet-190840',  # 宠物狗在店内治疗后死亡，双方发生医疗纠纷，被告人报复性砸坏店内医疗设备
}

# --- 第五轮：HRL-025 同案重复标签统一 + 野生动物边界案排除（2026-07-23，用户决定）---
# 92 对近重复里有 3 对终判标签不一致（同一案件因分片不同被处理两次得出不同结论），
# 用户逐对裁定统一到哪个标签。以下两条不涉及人工审核集覆盖冲突（这两条 census_id
# 均未出现在 census_review_result.csv 里），故直接在此层修正即可生效；另外两条
# （119321、380166）因用户浏览器审核时已对其中一份副本给出过 category_user，
# 会被 census_apply_review.py 的人工审核层覆盖，故那两条的统一改在
# census_apply_review.py 里做"终局裁定"层，不在此处，且不改写用户原始审核记录。
DUP_LABEL_UNIFY_TO_CRUELTY_IDS = {
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-041314',  # 狗叫持石头砸狗引发放火砍人，与036056同案，统一为cruelty
}
DUP_LABEL_UNIFY_TO_RETALIATION_IDS = {
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-124396',  # 林地纠纷打死狗/母猪/鸡，与292444同案，统一为retaliation
}
# 野生动物边界案：余某私设电网猎捕野生动物电死麂子+野猪，罪名"以危险方法危害
# 公共安全"而非"非法狩猎"，技术上未违反 HRL-023"野生动物盗猎/狩猎暂不纳入"的
# 检索排除规则字面（走的是公共安全关键词路径非狩猎罪路径），但用户确认这本质
# 就是一起野生动物盗猎案，按 HRL-023 精神排除出 census——不是假阳性（案件真实
# 发生），是范围排除（scope exclusion），故不改 category，只标记排除原因，
# 由 census_apply_review.py 读取此标记强制 included=False。
WILDLIFE_OUT_OF_SCOPE_IDS = {
    'CAIL-cail_exercise_contest_train-00000-of-00001.parquet-132978',
    'CAIL-cail_first_stage_train-00003-of-00004.parquet-338743',
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

# --- 第三轮：HRL-026 定向重扫修正（B层命中却被判fp的77条全量重读结果）---
round3 = []
for r in recs:
    cid = r['census_id']

    if cid in RESCAN_FP_TO_POACHING_IDS and r['category'] == 'fp':
        r['category'] = 'poaching'
        r['animal_directly_harmed'] = False
        r['correction_note'] = 'HRL-026定向重扫：原判fp有误，判决记载真实偷狗情节(既遂/未遂/嫌疑/持有作案工具/敲诈借口)，按"偷狗情节即计入"政策归poaching；动物本身受伤情况未证实故animal_directly_harmed=False'
        round3.append((cid, 'poaching'))

    elif cid in RESCAN_FP_TO_RETALIATION_IDS and r['category'] == 'fp':
        r['category'] = 'retaliation'
        r['correction_note'] = 'HRL-026定向重扫：原判fp有误，本记录核心是行为人因被诬陷偷狗而报复诬告者，归retaliation'
        round3.append((cid, 'retaliation'))

# --- 第四轮：HRL-026 A 层假阳性重扫修正（236条局部上下文初筛出17条候选的全文核实结果）---
round4 = []
for r in recs:
    cid = r['census_id']

    if cid in A_RESCAN_TO_CRUELTY_IDS and r['category'] == 'fp':
        r['category'] = 'cruelty'
        r['animal_directly_harmed'] = False
        r['correction_note'] = 'HRL-026 A层定向重扫：原判fp有误，动物是暴力直接目标或蓄意伤害指控的对象，归cruelty；受伤情况未证实故animal_directly_harmed=False'
        round4.append((cid, 'cruelty'))

    elif cid in A_RESCAN_TO_POACHING_IDS and r['category'] == 'fp':
        r['category'] = 'poaching'
        r['animal_directly_harmed'] = False
        r['correction_note'] = 'HRL-026 A层定向重扫：原判fp有误，判决记载偷狗指控（未经判决认定为事实，双方各执一词），按既定政策纳入poaching'
        round4.append((cid, 'poaching'))

    elif cid in A_RESCAN_TO_OTHER_TRUE_IDS and r['category'] == 'fp':
        r['category'] = 'other_true'
        r['correction_note'] = 'HRL-026 A层定向重扫：原判fp有误，宠物在医疗纠纷中死亡（双方无争议的既定背景事实，案件本身即由此引发），但医疗过失是否成立未经司法认定，判决审理的是后续故意毁坏财物行为——新的证据类型，不完全匹配现有透明标记'
        round4.append((cid, 'other_true'))

# --- 第五轮：HRL-025 同案标签统一（不涉及审核集覆盖的两条）+ 野生动物范围排除标记 ---
round5 = []
for r in recs:
    cid = r['census_id']

    if cid in DUP_LABEL_UNIFY_TO_CRUELTY_IDS and r['category'] != 'cruelty':
        r['category'] = 'cruelty'
        r['correction_note'] = 'HRL-025：与另一近重复副本终判标签不一致，用户裁定统一为cruelty'
        round5.append((cid, 'cruelty'))

    elif cid in DUP_LABEL_UNIFY_TO_RETALIATION_IDS and r['category'] != 'retaliation':
        r['category'] = 'retaliation'
        r['correction_note'] = 'HRL-025：与另一近重复副本终判标签不一致，用户裁定统一为retaliation'
        round5.append((cid, 'retaliation'))

    if cid in WILDLIFE_OUT_OF_SCOPE_IDS:
        r['out_of_scope'] = True
        r['correction_note'] = 'HRL-025：真实野生动物盗猎案（私设电网猎捕，罪名"以危险方法危害公共安全"非"非法狩猎"），技术上未违反HRL-023检索排除规则字面但本质是野生动物盗猎，用户确认按HRL-023精神排除出census——非假阳性，是范围排除'
        round5.append((cid, 'out_of_scope'))

with open('pipeline/census_classified.jsonl', 'w') as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f"✓ 产业链推定升级为 poaching: {len(presumed)} 条")
print(f"✓ 标记建议排除（追回未受伤，明确证据）: {len(marked_excluded)} 条 — {marked_excluded}")
print(f"✓ 特殊性质重分类: {len(reclassified)} 条 — {reclassified}")
print(f"✓ 第二轮人工审核修正: {len(round2)} 条 — {round2}")
print(f"✓ 第三轮HRL-026定向重扫修正(B层): {len(round3)} 条（62 poaching + 1 retaliation，14条核实后确认原fp正确未改）")
print(f"✓ 第四轮HRL-026定向重扫修正(A层): {len(round4)} 条（{sum(1 for _,c in round4 if c=='cruelty')} cruelty + {sum(1 for _,c in round4 if c=='poaching')} poaching + {sum(1 for _,c in round4 if c=='other_true')} other_true，17条候选中12条核实后确认原fp正确未改）")
print(f"✓ 第五轮HRL-025标签统一+范围排除: {len(round5)} 条 — {round5}")

from collections import Counter
cat_cnt = Counter(r['category'] for r in recs)
print("\n更新后分类分布:")
for cat, cnt in cat_cnt.most_common():
    print(f"  {cat:22s} {cnt:3d}")
