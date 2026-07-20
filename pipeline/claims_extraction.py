"""Stage 3: claim extraction (AI-assisted manual pass, not an automated model).

Per the Stage 3 design discussion with the PI (2026-07-27): claim extraction
is a reading-comprehension task PRD §27.5 assigns to a capable language
model, not something a regex/stdlib script can safely do the way Stage 2's
comparison problem allowed. No LLM API is wired into this repo yet, so this
pass was done by the AI assistant reading every archived snapshot directly
and encoding the results here -- claims_public.model_version is left NULL
for all rows this script writes; that field is reserved for a future
deployed-model run, and it would be dishonest to backfill a version string
for a manual/AI-assisted pass.

Identity policy applied throughout (HRL-015, decided 2026-07-27): minors are
always anonymized, no exceptions. For adults, AHID's own claim_value text
follows whatever identification level the primary/official source itself
already used -- it does not proactively cross-reference lower-tier sources
to fill in a name an official notice redacted. Concretely: incident #6 uses
the real name 范源庆 because Shandong University of Technology's own
official statement named him; incident #9 uses the real name 徐志辉 because
official newswire coverage (Xinhua-affiliated outlets) used it. Every other
incident in this file keeps the anonymized X某某 form its own official
source used.

This pass also corrects several factual errors caught only by reading full
archived text (not just search-result summaries) -- see the incident-by-
incident comments below and the Stage 3 commit message for the complete
list. Two genuine contradictions between sources are encoded as competing
claims with support_status='contradicted' rather than silently picking one
version (incident #4's harm-method narrative, incident #5's corpse-
placement suspicion that investigation actually cleared).

Run: python3 pipeline/claims_extraction.py [--db pipeline/ahid_pilot.sqlite3]
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


# --- Corrections to incidents_public, found only by reading full archived
# text (search-result summaries had gotten these wrong or under-specified).
INCIDENT_CORRECTIONS = {
    "AHID-CN-2026-0002": {  # seed #2, 邱某某
        # City name was "待核实" in the seed doc; archived text confirms it.
        "province": "江西省", "city": "赣州市", "location_precision": "city",
    },
    "AHID-CN-2026-0003": {  # seed #3, 付某某 (surname now known)
        "harm_categories": "beating|suffocation|other_harm",
    },
    "AHID-CN-2026-0004": {  # seed #4, 崔某某 -- contradicted harm method, see claims
        "harm_categories": "other_harm|scalding",
        "disputed_flag": 1,
    },
    "AHID-CN-2026-0005": {  # seed #5, 苏某某
        "estimated_animal_count": "10+",
    },
    "AHID-CN-2026-0006": {  # seed #6, 范源庆 -- real name per HRL-015
        "harm_categories": "beating|burning|scalding|dismemberment|content_motivated_abuse",
    },
    "AHID-CN-2026-0008": {  # seed #8, 徐某某 (abuse at Southeast Univ.)
        "harm_categories": "suffocation|other_harm",
    },
    "AHID-CN-2026-0009": {  # seed #9, 徐志辉 -- real name per HRL-015; location was unset
        "province": "安徽省", "city": "阜阳市", "location_precision": "district",
    },
    "AHID-CN-2026-0014": {  # seed #15, 郑州大学张某 -- false-report test case. This incident's
        # own core claim (event_occurred) is support_status='contradicted' -- the abuse never
        # happened, per the joint school/police investigation. disputed_flag must reflect that,
        # otherwise Stage 4 scoring has no signal to avoid classifying this as A4 "authoritatively
        # documented" just because a school disciplinary response exists (which it does, but for
        # the false report itself, not for animal cruelty). Caught by inspecting Stage 4's first
        # run: this incident scored A4 before this fix, which is exactly backwards for a case
        # whose entire point is that the accusation was false.
        "disputed_flag": 1,
    },
    "AHID-CN-2026-0010": {  # seed #10, 宿迁动物园
        "species": "梅花鹿、黑熊",
    },
    "AHID-CN-2026-0011": {  # seed #11 -- WRONG PROVINCE in original seed (said Guangxi)
        "province": "福建省", "city": "福州市", "location_precision": "city",
        "species": "熊",
    },
    "AHID-CN-2026-0018": {  # seed #19 -- WRONG CITY in original seed (said Kunshan;
        # archived CCTV Finance piece is actually about Rugao/Jining, no Kunshan mention)
        "province": "江苏省", "city": "如皋市", "location_precision": "district",
    },
    # --- Round 2 (2026-07-27) corrections, found reading the newly archived text ---
    "AHID-CN-2026-0020": {  # seed #21, Chongqing "Sam's Club bagging guy"
        "estimated_animal_count": "3+ survivors, multiple additional deaths/missing",
    },
    "AHID-CN-2026-0027": {  # seed #28, highway abandonment -- the source that actually stated
        # the specific date (羊城晚报) failed to archive (anti-bot block); the surviving 网易
        # source corroborates the event but doesn't restate the exact date in what was extracted.
        # Downgrading date_status accordingly rather than keeping unwarranted confidence.
        "date_status": "claimed_only",
    },
}

# --- Response flags on incidents_public, set only where the archived text
# actually documents that response (not inferred/assumed).
RESPONSE_FLAGS = {
    "AHID-CN-2026-0001": dict(official_response_found=1, police_response_found=1,
                               school_response_found=0, legal_outcome_found=0),
    "AHID-CN-2026-0002": dict(official_response_found=1, school_response_found=1),
    "AHID-CN-2026-0003": dict(official_response_found=1, school_response_found=1),
    "AHID-CN-2026-0004": dict(official_response_found=1, school_response_found=1),
    "AHID-CN-2026-0005": dict(official_response_found=1, school_response_found=1, police_response_found=1),
    "AHID-CN-2026-0006": dict(official_response_found=1, school_response_found=1),
    "AHID-CN-2026-0007": dict(official_response_found=1, school_response_found=1),
    "AHID-CN-2026-0008": dict(official_response_found=1, school_response_found=1, police_response_found=1),
    "AHID-CN-2026-0009": dict(official_response_found=1, police_response_found=1, policy_response_found=1),
    "AHID-CN-2026-0010": dict(official_response_found=0),  # staff acknowledgment only, not a formal response
    "AHID-CN-2026-0011": dict(official_response_found=1),
    "AHID-CN-2026-0012": dict(official_response_found=0, legal_outcome_found=1),  # court judgment exists for a
    # different customer at the same shop -- not a regulator response, and not yet resolved for THIS incident's
    # own buyer; see claims for the distinction.
    "AHID-CN-2026-0013": dict(official_response_found=0),  # investigative piece; no enforcement case exists
    "AHID-CN-2026-0014": dict(official_response_found=1, school_response_found=1, police_response_found=1),
    # ^ this is #15 in the seed doc, the false-report test case
    "AHID-CN-2026-0015": dict(official_response_found=1, police_response_found=1),
    "AHID-CN-2026-0016": dict(official_response_found=0, police_response_found=1),  # traffic police attended
    # the crash scene procedurally; no regulatory finding on the transport company documented yet
    "AHID-CN-2026-0017": dict(official_response_found=1, police_response_found=1),
    "AHID-CN-2026-0018": dict(official_response_found=0),  # investigative piece; no enforcement case exists
    "AHID-CN-2026-0019": dict(official_response_found=1, police_response_found=1, legal_outcome_found=1),
    # --- Round 2 (2026-07-27) ---
    "AHID-CN-2026-0020": dict(official_response_found=1, police_response_found=1, legal_outcome_found=0),
    # ^ Chongqing: case formally opened + administrative detention, but no court outcome yet
    "AHID-CN-2026-0021": dict(official_response_found=1, police_response_found=1, school_response_found=0),
    "AHID-CN-2026-0022": dict(official_response_found=1, police_response_found=1),
    "AHID-CN-2026-0023": dict(official_response_found=1, school_response_found=1, police_response_found=1),
    "AHID-CN-2026-0024": dict(official_response_found=1),  # 海洋馆自身机构回应，非政府监管部门
    "AHID-CN-2026-0025": dict(official_response_found=1),  # 动物园自身机构回应；另有更早的官方（林业和草原
    # 局）投诉答复，见 claims -- 但那是回应"长期虐待"的更早投诉，不是回应这次1月23日事件本身
    "AHID-CN-2026-0026": dict(official_response_found=1, legal_outcome_found=1, policy_response_found=1),
    # ^ 法院判决 + 涉事机构主动辟谣（policy_response 借用来记录"机构辟谣行动"，非严格意义的政策回应，
    # 但现有 enum 里没有更贴切的选项，claims 里会写清楚具体是什么）
    "AHID-CN-2026-0027": dict(official_response_found=0),  # 记者实地发现报道，未见对应监管部门回应
}

# --- Claims. Each tuple: (claim_type, claim_value, support_status,
# supporting_source_count, independent_supporting_count, contradicting_source_count,
# confidence_category). independent_supporting_count comes from Stage 2's
# independent_source_cluster_count for that incident, not re-derived here.
CLAIMS = {
    "AHID-CN-2026-0001": [  # Wangwang
        ("event_occurred", "四名未满14岁男童虐杀流浪母狗及其三只幼犬", "supported", 2, 2, 0, "high"),
        ("event_date", "2026-06-28", "supported", 2, 2, 0, "high"),
        ("event_location", "广东省揭阳市揭东区新亨镇坪埔村", "supported", 2, 2, 0, "high"),
        ("animal_count", "4（1只母犬+3只幼犬）", "supported", 2, 2, 0, "high"),
        ("harm_method", "铁丝勒颈拖行、木棍殴打、泼易燃液体纵火", "supported", 2, 2, 0, "high"),
        ("animal_death", "母犬及三只幼犬全部死亡", "supported", 2, 2, 0, "high"),
        ("minor_involvement", "4名涉案者均未满14周岁", "supported", 2, 2, 0, "high"),
        ("official_response", "揭阳市公安局揭东分局立案调查；新亨镇人民政府成立专项工作组，将4人送专门学校矫治教育", "supported", 2, 2, 0, "high"),
        ("policy_response", "事件引发关于制定全国性动物保护法的公众讨论，多名人大代表此前已连续提出相关建议", "partially_supported", 1, 1, 0, "medium"),
    ],
    "AHID-CN-2026-0002": [  # 邱某某
        ("event_occurred", "赣南师范大学科技学院学生邱某某发布虐猫影像，校方通报违法行为属实", "supported", 2, 2, 0, "high"),
        ("event_date", "2026-05-14（校方通报日期）", "supported", 2, 2, 0, "high"),
        ("animal_species", "猫", "supported", 2, 2, 0, "high"),
        ("official_response", "赣南师范大学科技学院给予开除学籍处分", "supported", 2, 2, 0, "high"),
        ("legal_outcome", "警方行政拘留10日", "claimed_only", 0, 0, 0, "low"),
        # ^ this appeared in earlier web-search summaries but is NOT present in either
        # archived source's text; flagged low-confidence/unverified rather than dropped
        # silently or upgraded to 'supported' on the strength of an unarchived claim.
    ],
    "AHID-CN-2026-0003": [  # 付某某, 武汉理工大学
        ("event_occurred", "武汉理工大学土木工程与建筑学院学生付某某多次伤害校内一只猫", "supported", 1, 1, 0, "high"),
        ("event_date", "2024-07-18（校方接到举报日期）", "supported", 1, 1, 0, "high"),
        ("harm_method", "多次殴打、装入盛水袋中封闭、喷花露水、双脚捆绑悬挂晾衣架", "supported", 1, 1, 0, "high"),
        ("official_response", "学院成立工作组调查，对该生严肃批评教育；截至报道时尚未公布最终处分结果", "partially_supported", 1, 1, 0, "medium"),
    ],
    "AHID-CN-2026-0004": [  # 崔某某, 广东海洋大学 -- CONTRADICTED
        ("event_occurred", "广东海洋大学食品科技学院学生崔某某将猫杀死", "supported", 2, 1, 0, "high"),
        ("event_date", "2025-06-20（据校方处分决定）", "supported", 2, 1, 0, "high"),
        ("harm_method", "官方处分决定称：崔某某在校外居住处照顾他人猫只期间被咬伤，遂将猫杀害",
         "partially_supported", 1, 1, 1, "medium"),
        ("harm_method", "更早的网友爆料称：崔某某偷走便利店老板的宠物猫，21日凌晨被抓获后承认虐杀并弃尸垃圾桶；"
                        "经查猫的前爪断裂、尾巴骨折、身上有明显烫伤痕迹",
         "contradicted", 1, 1, 1, "medium"),
        # ^ two claim rows on the same claim_type, each contradicting the other -- this
        # is deliberate (PRD's "反证不得隐藏" principle), not a data-entry duplicate.
        # The school's own formal disciplinary decision is the more authoritative
        # document, but it directly conflicts with the initial eyewitness/whistleblower
        # account in both cause (bitten-then-killed vs. theft-then-tortured) and severity
        # (no injury detail vs. broken limbs + burns). Neither is dismissed here.
        ("official_response", "广东海洋大学给予留校察看处分，暂停学业（2025-06-24决定）", "supported", 1, 1, 0, "high"),
    ],
    "AHID-CN-2026-0005": [  # 苏某某, 华中农业大学
        ("event_occurred", "华中农业大学学生苏某某将药物碾粉兑水投喂校内流浪猫", "supported", 2, 1, 0, "high"),
        ("event_date", "2024-10~11（投毒期间）", "supported", 2, 1, 0, "high"),
        ("harm_method", "5片人用药物碾成粉末分次兑水投喂流浪猫", "supported", 2, 1, 0, "high"),
        ("animal_death", "十余只校内流浪猫接连死亡", "supported", 2, 1, 0, "high"),
        ("animal_death", "另有一只黑猫尸体被发现，网传系人为蓄意放置；经辖区派出所现场勘察、调看监控及X光检查，"
                         "未发现人为放置或骨折证据", "contradicted", 2, 1, 0, "high"),
        # ^ this is the cleared suspicion -- the investigation actively refuted the
        # deliberate-placement claim; recorded because PRD requires contradictory
        # evidence to stay visible, not because it supports the incident.
        ("official_response", "学校联合属地派出所调查，给予苏某某严重警告处分", "supported", 2, 1, 0, "high"),
    ],
    "AHID-CN-2026-0006": [  # 范源庆, 山东理工大学 -- real name per HRL-015
        ("event_occurred", "山东理工大学数学与统计学院2016级学生范源庆虐待流浪猫并拍摄视频在网络贩卖",
         "supported", 2, 2, 0, "high"),
        ("event_date", "2020-02~04（虐待期间）/ 2020-04-09（学校官方声明日期）", "supported", 2, 2, 0, "high"),
        ("animal_count", "80余只", "supported", 2, 2, 0, "high"),
        ("harm_method", "剥皮、掏肠、挖眼、拔舌、开水烫身、火烧、电击等手段，过程拍摄成视频通过微博/QQ贩卖牟利",
         "supported", 2, 2, 0, "high"),
        ("official_response", "学校官方声明证实身份，给予严肃批评教育，责令向网友道歉；未见开除或退学处分",
         "supported", 2, 2, 0, "high"),
        ("legal_outcome", "律师接受采访时提出可能以非法经营罪等罪名追责的法律观点；未见实际立案或起诉记录",
         "claimed_only", 2, 2, 0, "low"),
    ],
    "AHID-CN-2026-0007": [  # 李某某, 南阳理工学院
        ("event_occurred", "南阳理工学院学生李某某虐猫并在网上发布视频及不当言论", "supported", 2, 2, 0, "high"),
        ("event_date", "2023-09-02（校方通报处理决定日期；视频最初曝光的具体日期未见于已归档来源，"
                       "此前搜索摘要提及的8月27日/28日无法在本轮归档正文中核实）", "partially_supported", 2, 2, 0, "medium"),
        ("official_response", "南阳理工学院给予开除学籍处分", "supported", 2, 2, 0, "high"),
        ("legal_outcome", "警方另处行政拘留7日", "claimed_only", 0, 0, 0, "low"),
        # ^ same treatment as #2's detention claim: seen in early search summaries,
        # not present in the two sources actually archived for this incident.
    ],
    "AHID-CN-2026-0008": [  # 徐某某, 施虐于东南大学, 后果发生于南京大学/兰州大学
        ("event_occurred", "徐某某本科就读东南大学期间在宿舍虐杀猫只并拍摄视频上传网络", "supported", 2, 1, 0, "high"),
        ("event_location", "施虐地点：东南大学（南京）；机构后续（考研拒录）：南京大学", "supported", 2, 1, 0, "high"),
        ("harm_method", "将猫放入水桶，用脚踩踏猫头", "supported", 2, 1, 0, "high"),
        ("official_response", "南京大学物理学院复试认定徐某某思想品德考核不合格，专业笔面第一但未予录取（2024-04）",
         "supported", 2, 1, 0, "high"),
        ("official_response", "调剂至兰州大学核科学与技术学院复试，最终未进入拟录取名单（2024-04-08）",
         "supported", 1, 1, 0, "high"),
        ("official_response", "南京市公安局对徐某某及家人进行约谈，徐某某写悔过书", "supported", 2, 1, 0, "high"),
    ],
    "AHID-CN-2026-0009": [  # 徐志辉, 网名"杰克辣条" -- real name per HRL-015
        ("event_occurred", "网络博主徐志辉（网名\"杰克辣条\"）拍摄\"处刑式虐猫\"短视频传播", "supported", 2, 2, 0, "high"),
        ("harm_method", "对猫实施虐待并拍摄成短视频在QQ群传播", "supported", 2, 2, 0, "high"),
        ("official_response", "安徽省阜南县公安局依据治安管理处罚法对徐志辉予以治安拘留", "supported", 2, 2, 0, "high"),
        ("policy_response", "阜南县文明办取消徐志辉此前获得的\"阜南好人\"荣誉称号（2026-05-05）", "supported", 1, 1, 0, "high"),
    ],
    "AHID-CN-2026-0010": [  # 宿迁动物园
        ("event_occurred", "沭阳县南湖公园动物园黑熊被铅条绑嘴、梅花鹿腿部溃烂生蛆，游客拍摄视频提供给媒体",
         "claimed_only", 1, 1, 0, "medium"),
        ("event_date", "2024-11-04", "supported", 1, 1, 0, "high"),
        ("official_response", "报道时动物园员工仅口头回应\"会去了解情况\"，未见正式官方调查或处理结果", "unknown", 1, 1, 0, "low"),
    ],
    "AHID-CN-2026-0011": [  # 福州动物园
        ("event_occurred", "福州动物园一只狗熊在表演中因连续失败遭驯兽师脚踹", "supported", 1, 1, 0, "high"),
        ("event_location", "福州动物园（福建省）——原线索误记为广西，2026-07-27归档正文核实后更正", "supported", 1, 1, 0, "high"),
        ("official_response", "动物园管理处回应称驯兽师情绪急躁，已将其停职", "supported", 1, 1, 0, "high"),
    ],
    "AHID-CN-2026-0012": [  # 边牧犬维权群（星期宠）
        ("event_occurred", "消费者在北京一家宠物店购买的边牧犬到家第2天生病，15天后抽搐死亡", "supported", 1, 1, 0, "high"),
        ("event_date", "2026-04-30（报道日期）", "supported", 1, 1, 0, "high"),
        ("harm_method", "涉事宠物店存在检疫证明存疑、隐瞒病情、拒绝担责等模式；同店另一消费者购买的柴犬经检测"
                        "确诊携带犬瘟热、细小病毒，四天后死亡", "supported", 1, 1, 0, "high"),
        ("legal_outcome", "同店柴犬买家已通过法院强制执行程序获约4000元赔偿，历时近两年；本文起始的边牧犬买家"
                          "本人是否已获赔偿或诉讼未见报道", "partially_supported", 1, 1, 0, "medium"),
    ],
    "AHID-CN-2026-0013": [  # 晋江斗狗 -- see HRL-014, phenomenon not single dated incident
        ("event_occurred", "记者调查报道称闽南（晋江等地）存在地下斗狗赌博活动，画面残忍血腥", "claimed_only", 1, 1, 0, "medium"),
        ("event_date", "2015-05-04（报道刊发日期；描述的斗狗活动本身无具体单一日期，见HRL-014）",
         "claimed_only", 1, 1, 0, "low"),
        ("official_response", "记者向工商部门了解到，我国法律法规对斗狗是否违法并未明确规定；泉州当地未处理过"
                              "非法开设斗狗场或斗狗赌博案件", "supported", 1, 1, 0, "high"),
        # ^ this claim_value documents the ABSENCE of an official response, which is
        # itself a documented fact worth recording, not an omission.
    ],
    "AHID-CN-2026-0014": [  # 郑州大学张某 -- false-report test case
        ("event_occurred", "经郑州大学土木工程学院联合公安部门调查，未发现学生张某有虐猫行为；张某因与网友"
                          "就养猫观点产生分歧，一时冲动谎称自己曾虐猫并发布不当言论及来源于网络的图片",
         "contradicted", 1, 1, 0, "high"),
        # ^ deliberately claim_type=event_occurred with support_status='contradicted':
        # the CLAIM that abuse occurred is what gets contradicted here, by the joint
        # police/school investigation -- this is the intended reading for this test case.
        ("event_date", "2026-04-29（网传发帖日期）/ 2026-05-15（校方通报日期）", "supported", 1, 1, 0, "high"),
        ("official_response", "郑州大学土木工程学院给予张某严重警告处分——处分依据是发布不实信息造成不良影响，"
                              "不是动物虐待行为本身", "supported", 1, 1, 0, "high"),
    ],
    "AHID-CN-2026-0015": [  # 湖南江永城管拖狗
        ("event_occurred", "湖南江永县城管执法人员在处置一只追人流浪犬时违规操作，将犬只系于车辆尾部拖行致死",
         "supported", 2, 2, 0, "high"),
        ("event_date", "2026-05-28上午8时许", "supported", 2, 2, 0, "high"),
        ("harm_method", "现场缺乏专业带离工具，工作人员擅自违规操作将犬只系于车尾缓慢带离，致其被拖行致死",
         "supported", 2, 2, 0, "high"),
        ("animal_death", "涉事犬只死亡", "supported", 2, 2, 0, "high"),
        ("official_response", "江永县城市管理和综合执法局发布通报公开致歉，涉事工作人员停职接受进一步调查处理",
         "supported", 2, 2, 0, "high"),
    ],
    "AHID-CN-2026-0016": [  # 连云港托运车起火
        ("event_occurred", "G15沈海高速连云港段托运车追尾起火，车载23只宠物猫狗全部死亡", "supported", 2, 2, 0, "high"),
        ("event_date", "2026-06-13 22:55", "supported", 2, 2, 0, "high"),
        ("animal_count", "约23只（猫、犬）", "supported", 2, 2, 0, "high"),
        ("harm_method", "托运公司宣传\"专车专运、一猫一座\"，实际使用密闭依维柯大车混装运输；涉事托运公司"
                        "\"易丰运宠\"系\"永鹏控股\"旗下分支业务", "supported", 2, 2, 0, "high"),
        ("official_response", "事故发生当晚交警到场处理；截至报道时未见交通或农业农村部门就托运资质/责任认定"
                              "发布正式调查结论", "partially_supported", 2, 2, 0, "medium"),
        ("legal_outcome", "受害宠物主人表示已准备向法院提起诉讼；未见法院受理或判决记录", "claimed_only", 2, 2, 0, "low"),
    ],
    "AHID-CN-2026-0017": [  # 苏州虐猫诱骗领养
        ("event_occurred", "苏州男子李某伪装领养意愿诱骗获取猫只，自述在QQ群直播中对多只猫施虐", "supported", 1, 1, 0, "high"),
        ("event_date", "2026-02-25（志愿者拦截当日）/ 2026-02-28（警方通报调查日期）", "partially_supported", 1, 1, 0, "medium"),
        ("harm_method", "本人承认虐待5只猫，含用开水浇烫；QQ群内其他成员另有强喂酸性物质、高空抛掷、活活烧死等"
                        "手段，但未明确归因于本人", "supported", 1, 1, 0, "high"),
        ("official_response", "苏州市吴中区警方发布官方通报，同时对李某（涉嫌虐杀领养猫只并传播视频）与介入"
                              "的志愿者（涉嫌拘禁殴打李某）两方展开调查", "supported", 1, 1, 0, "high"),
    ],
    "AHID-CN-2026-0018": [  # 如皋/济宁地下宠物繁殖场（原线索误记昆山）-- 见HRL-014
        ("event_occurred", "央视财经《经济半小时》调查报道江苏如皋、山东济宁等地存在无证地下宠物交易与繁殖场，"
                          "病猫病犬翻新转卖、繁殖场死亡率超五成", "supported", 1, 1, 0, "high"),
        ("event_location", "江苏省南通市如皋市（主要调查地点）；另涉及山东省济宁市——原线索误记\"昆山\"，"
                          "2026-07-27归档正文核实后更正，原文完全未提及昆山", "supported", 1, 1, 0, "high"),
        ("harm_method", "无证经营、不打疫苗、伪造检疫证明、交叉感染风险高、繁殖场死亡率超50%", "supported", 1, 1, 0, "high"),
        ("official_response", "市场监管、畜牧兽医站等多部门互相推诿，均表示不在自身监管范围；报道未见任何"
                              "实际处罚或取缔记录", "supported", 1, 1, 0, "high"),
    ],
    "AHID-CN-2026-0019": [  # 深圳龙岗斗鸡赌博
        ("event_occurred", "深圳市公安局龙岗分局破获以\"斗鸡\"形式进行的聚众赌博窝点", "supported", 1, 1, 0, "high"),
        ("event_date", "2019-04-07", "supported", 1, 1, 0, "high"),
        ("animal_count", "斗鸡9只被查获", "supported", 1, 1, 0, "high"),
        ("harm_method", "组织者建立斗鸡场地、制定规则，召集6名\"斗鸡\"爱好者自带斗鸡进行赌博，每盘赌注100-1200元",
         "supported", 1, 1, 0, "high"),
        ("official_response", "现场抓获涉赌人员21人；组织者杨某某、胡某某涉嫌开设赌场罪被刑事拘留，参赌者分别"
                              "处以治安拘留或行政处罚", "supported", 1, 1, 0, "high"),
        ("legal_outcome", "2名组织者被刑事拘留（开设赌场罪）", "supported", 1, 1, 0, "high"),
    ],
    # --- Round 2 (2026-07-27, HRL-016) ---
    "AHID-CN-2026-0020": [  # 重庆"山姆打包哥"李某（HRL-015：官方通报本身匿名为"李某"，
        # 维基百科条目用真名"李萌"，但官方信源是更权威的一手来源，AHID 记录跟随官方口径，不采用真名）
        ("event_occurred", "重庆两江新区男子李某长期以领养为名骗取猫狗，实施虐待并致多只动物死亡", "supported", 3, 3, 0, "high"),
        ("event_date", "2026-03（邻居首次报案）～2026-06-09（正式立案）", "supported", 3, 3, 0, "high"),
        ("harm_method", "锯平牙齿、剪断尾巴、折断骨骼；将已死亡动物从高层阳台抛下", "supported", 3, 3, 0, "high"),
        ("animal_death", "至少1只成年犬及多只动物死亡；3只幸存犬送医收容；另有多只动物下落不明", "supported", 3, 3, 0, "high"),
        ("official_response", "2026-03邻居首次报案时警方因证据不足未采取有效措施；2026-06-05报案时办案警员"
                              "表示\"打杀狗不犯法\"、将事件定性为民事纠纷，处理消极；经持续曝光及民众聚集后，"
                              "2026-06-09两江新区公安分局正式立案调查，06-10对李某处以行政拘留",
         "supported", 2, 2, 0, "high"),
        # ^ 故意在同一条 claim 里呈现官方回应从消极到积极的转变过程，不美化也不隐藏早期不作为
        ("policy_response", "事件引发数百市民及志愿者连续多日聚集抗议，要求订立专门反虐待动物法；"
                            "警方对集会现场进行清场并对网上流传的集会影像进行审查", "partially_supported", 1, 1, 0, "medium"),
    ],
    "AHID-CN-2026-0021": [  # 徐州3名男孩虐猫
        ("event_occurred", "徐州四季连城锦宸小区3名男孩持棍棒及锤子将一只白猫按压致死", "supported", 1, 1, 0, "high"),
        ("event_date", "2026-07-13晚", "supported", 1, 1, 0, "high"),
        ("harm_method", "棍棒及锤子按压击打", "supported", 1, 1, 0, "high"),
        ("minor_involvement", "3名涉事者均为未成年男孩", "supported", 1, 1, 0, "high"),
        ("official_response", "辖区九里派出所于当晚介入，对涉事男孩及家长进行批评教育；其中一名男孩家长自称"
                              "已对孩子进行教育与体罚；未见任何一方被送专门学校或其他更严厉处置",
         "supported", 1, 1, 0, "high"),
    ],
    "AHID-CN-2026-0022": [  # 连云港两男童烧死萨摩耶 -- CONTRADICTED（赔偿是否达成一致）
        ("event_occurred", "连云港东海县中央花园小区两名男童将点燃的烟花投入狗笼，烧死一只饲养7年的萨摩耶犬",
         "supported", 2, 2, 0, "high"),
        ("event_date", "2026-02-01中午12时34分许", "supported", 2, 2, 0, "high"),
        ("harm_method", "点燃烟花投入狗笼引发火灾", "supported", 2, 2, 0, "high"),
        ("animal_death", "萨摩耶犬被烧死", "supported", 2, 2, 0, "high"),
        ("official_response", "施害男孩家长一方陈述：警方已当面调解，两家各赔3000元共6000元并签订协议书，"
                              "双方达成一致", "partially_supported", 1, 1, 1, "medium"),
        ("official_response", "狗主人姜女士一方陈述：警方提出联合赔偿6000元或另赔一只狗的方案，但她和家人"
                              "并未接受，坚持要求男孩家属在业主群公开道歉", "contradicted", 1, 1, 1, "medium"),
        # ^ 两条互斥的 official_response claim：施害方与受害方对"是否已达成调解协议"陈述不一致，
        # 均予保留，不采信任何一方
    ],
    "AHID-CN-2026-0023": [  # 大邑4初中生虐猫
        ("event_occurred", "成都大邑县安仁镇学校八年级二班4名学生买猫后虐待并拍视频发布网络", "supported", 2, 2, 0, "high"),
        ("event_date", "2024-12-07晚（事件）/ 2024-12-11（教育局通报）", "supported", 2, 2, 0, "high"),
        ("harm_method", "用打火机烧猫脸部、用石头砸猫头部、用脚将猫踹飞", "supported", 2, 2, 0, "high"),
        ("minor_involvement", "4名涉事者均为在校初中生", "supported", 2, 2, 0, "high"),
        ("official_response", "大邑县教育局联合辖区派出所核查；对涉事学生批评教育，给予停课反省处理，安排"
                              "专业人员心理辅导及行为干预", "supported", 2, 2, 0, "high"),
    ],
    "AHID-CN-2026-0024": [  # 郑州锦艺城海洋馆海狮被踢
        ("event_occurred", "郑州锦艺城海洋馆驯养员在海狮表演结束后于后台脚踢海狮，游客拍摄曝光", "supported", 2, 2, 0, "high"),
        ("event_date", "2025-05-21（事件）/ 2025-05-22（园方通报）", "supported", 2, 2, 0, "high"),
        ("harm_method", "驯养师称因遭海狮攻击而脚踢海狮作为反应", "supported", 2, 2, 0, "high"),
        ("official_response", "园方与涉事驯养员解除劳动合同，暂停营业进行闭馆整顿", "supported", 2, 2, 0, "high"),
    ],
    "AHID-CN-2026-0025": [  # 西双版纳野生动物园小象被打 -- 含长期虐待指控与官方早前调查的矛盾
        ("event_occurred", "西双版纳野生动物园饲养员用金属锁多次砸向两只未成年亚洲象（\"念念\"5岁、\"乐宝\"近4岁）头部",
         "supported", 2, 2, 0, "high"),
        ("event_date", "2026-01-21（视频拍摄）/ 2026-01-23（视频网传及园方通报）", "supported", 2, 2, 0, "high"),
        ("harm_method", "手持金属锁多次砸向象头部，并高声呵斥", "supported", 2, 2, 0, "high"),
        ("official_response", "园方发布情况说明，承认饲养员\"操作不规范\"，对其严肃批评教育；兽医检查后称"
                              "小象身体状况良好", "supported", 2, 2, 0, "high"),
        ("official_response", "多名网友称该园小象长期被虐待、饲养环境差、屡遭殴打；但西双版纳州景洪市林业和"
                              "草原局在2025年4月对相关投诉的官方回复认定\"念念\"身体健康、生活环境达标（室内"
                              "86平方米、室外890平方米）", "contradicted", 1, 1, 1, "medium"),
        # ^ 游客长期虐待指控 vs 更早的官方调查结论相互矛盾，均予记录；注意后者回应的是更早的一般性投诉，
        # 不是专门针对本次1月23日这一具体事件的调查
    ],
    "AHID-CN-2026-0026": [  # 大熊猫网络谣言案 -- AF 类型；harm_categories 故意留空
        ("event_occurred", "网名\"大辽皇后\"的主播白某红与徐某于2023年3月至2024年5月在抖音、快手等平台散布"
                          "中国大熊猫保护研究中心及工作人员\"虐待大熊猫\"\"电击取精\"等虚假信息，并编造工作"
                          "人员因违规违纪被查处等不实内容，煽动网民投诉、举报、辱骂相关单位及个人",
         "contradicted", 2, 2, 0, "high"),
        # ^ 核心 claim 本身即被证伪：不存在真实的大熊猫虐待事件，这是本案与其余18条候选的本质区别
        ("event_date", "2023-03～2024-05（散布期间）", "supported", 2, 2, 0, "high"),
        ("official_response", "都江堰市人民法院一审公开审理，以寻衅滋事罪判处白某红有期徒刑1年6个月、徐某"
                              "有期徒刑1年2个月；（2025）川0181刑初69号，2025-06-26宣判，双方均未上诉、"
                              "检察机关未抗诉，判决已生效", "supported", 2, 2, 0, "high"),
        ("legal_outcome", "白某红、徐某均以寻衅滋事罪定罪量刑；该案入选四川法院年度优秀案例及全国法院案例库，"
                          "系全国首例涉大熊猫网络谣言、网络暴力刑事案件", "supported", 2, 2, 0, "high"),
        ("policy_response", "中国大熊猫保护研究中心等相关单位自谣言传播初期起，通过官方微博、微信公众号、"
                            "中央政法媒体及中国互联网联合辟谣平台等渠道发布辟谣信息", "supported", 1, 1, 0, "high"),
        ("rescue_outcome", "造谣行为导致大熊猫人工繁育国际科研合作项目一度停滞；未见大熊猫本身受到任何实际"
                           "伤害的记录", "supported", 2, 2, 0, "high"),
    ],
    "AHID-CN-2026-0027": [  # 乐山-重庆高速62具宠物尸体 -- 无单一施害人，HRL-014 性质
        ("event_occurred", "一男子驾车沿乐山至重庆约300公里高速路段，累计发现62具猫狗尸体，其中约七八只为犬，"
                          "其余多为猫；部分犬只穿着衣物、毛发整洁，推测系家养宠物", "supported", 1, 1, 0, "high"),
        ("event_location", "四川乐山至重庆高速沿线（跨川渝两地，无法归入单一省市）", "supported", 1, 1, 0, "high"),
        ("harm_method", "报道推测系春节返乡途中因运输防护不足导致宠物死亡或被沿途遗弃，非单一施害人的蓄意"
                        "行为；报道同时提及湖北嘉鱼至武汉高速段另有两只犬只因车窗未关跳车被撞死的类似个案",
         "claimed_only", 1, 1, 0, "medium"),
        ("official_response", "报道中未见交通或农业农村部门就本次乐山-重庆事件发布对应调查或处理通报",
         "unknown", 1, 1, 0, "low"),
    ],
}


def apply(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(open(Path(__file__).parent / "schema.sql", encoding="utf-8").read())

    for incident_id, fields in INCIDENT_CORRECTIONS.items():
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE incidents_public SET {set_clause} WHERE incident_id = ?",
            (*fields.values(), incident_id),
        )

    for incident_id, flags in RESPONSE_FLAGS.items():
        set_clause = ", ".join(f"{k} = ?" for k in flags)
        conn.execute(
            f"UPDATE incidents_public SET {set_clause} WHERE incident_id = ?",
            (*flags.values(), incident_id),
        )

    claim_seq = 0
    for incident_id, claims in CLAIMS.items():
        for claim_type, claim_value, support_status, supp_count, indep_count, contra_count, confidence in claims:
            claim_seq += 1
            claim_id = f"CLM-{claim_seq:05d}"
            # independent_supporting_count is NOT trusted from the hand-typed value above --
            # it's recomputed just below from Stage 2's actual independent_source_cluster_count,
            # capped by this claim's own supporting_source_count. Hand-typing this number across
            # 90 rows produced real inconsistencies (e.g. incident #8: both archived sources
            # support the same claims, but some rows were typed as independent_supporting_count=1
            # instead of 2) that a spot-check caught. min(supporting_count, incident_cluster_count)
            # can't overstate independence -- it's bounded by both how many sources back this
            # specific claim AND what Stage 2 actually found about their independence.
            conn.execute(
                "INSERT OR REPLACE INTO claims_public (claim_id, incident_id, claim_type, claim_value, "
                "support_status, supporting_source_count, independent_supporting_count, "
                "contradicting_source_count, confidence_category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (claim_id, incident_id, claim_type, claim_value, support_status,
                 supp_count, indep_count, contra_count, confidence),
            )

    conn.execute("""
        UPDATE claims_public
        SET independent_supporting_count = (
            SELECT MIN(claims_public.supporting_source_count, i.independent_source_cluster_count)
            FROM incidents_public i
            WHERE i.incident_id = claims_public.incident_id
        )
        WHERE supporting_source_count > 0
    """)

    conn.commit()

    n_claims = conn.execute("SELECT COUNT(*) FROM claims_public").fetchone()[0]
    n_contradicted = conn.execute(
        "SELECT COUNT(*) FROM claims_public WHERE support_status = 'contradicted'"
    ).fetchone()[0]
    incidents_with_claims = conn.execute(
        "SELECT COUNT(DISTINCT incident_id) FROM claims_public"
    ).fetchone()[0]
    n_total_incidents = conn.execute("SELECT COUNT(*) FROM incidents_public").fetchone()[0]
    conn.close()

    print(f"Wrote {n_claims} claims across {incidents_with_claims}/{n_total_incidents} incidents "
          f"({n_contradicted} marked contradicted). Applied {len(INCIDENT_CORRECTIONS)} "
          f"incident field corrections and {len(RESPONSE_FLAGS)} response-flag updates.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    args = parser.parse_args()
    apply(args.db)
