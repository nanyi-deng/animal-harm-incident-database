"""Stage 0: load the 19 PI-approved pilot candidates into the AHID database.

Source of truth for what gets seeded: docs/pipeline/candidate_incidents_seed.md,
reviewed row by row by the PI on 2026-07-27 (see docs/human_review_log.md HRL-007).

This script only registers incident- and source-level facts that were already
established by that human review (dates, location, animal/harm category,
involvement flags, and the URLs found during search). It deliberately leaves
NULL everything that later pipeline stages are responsible for computing:
independence_status, automation_status, evidence_sufficiency_score, and all
official/police/school/ngo/rescue/legal/policy response flags. Those require
archiving the pages (Stage 1), source-dependency analysis (Stage 2), and claim
extraction (Stage 3) -- none of which have run yet. Populating them here would
mean fabricating pipeline output instead of recording pipeline input.

Excluded from this seed: candidate #12 (Guangxi zoo flood) -- PI ruled it out
of scope (disaster/management failure, not deliberate harm) and it gets no
incident_id at all.

Run: python3 pipeline/seed_incidents.py [--db pipeline/ahid_pilot.sqlite3]
"""

import argparse
import sqlite3
from pathlib import Path

INCIDENTS = [
    # seed_no, province, city, location_precision, date_start, date_precision,
    # date_status, animal_category, estimated_animal_count, juvenile_animal,
    # mortality_status, harm_categories, minor_involvement,
    # institutional_involvement, commercial_involvement, group_involvement,
    # content_creation_involvement, is_test_case, inclusion_note
    dict(seed_no=1, province="广东省", city="揭阳市", location_precision="district",
         date_start="2026-06-28", date_precision="day", date_status="officially_reported",
         animal_category="dog", estimated_animal_count="4", juvenile_animal="yes",
         mortality_status="dead", harm_categories="beating|burning|suffocation",
         minor_involvement="yes", institutional_involvement="no",
         commercial_involvement="no", group_involvement="yes",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="项目起源个案（\"旺旺事件\"）；用户 2026-07-27 确认收录"),
    dict(seed_no=2, province=None, city=None, location_precision="unknown",
         date_start="2026-05", date_precision="month", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="content_motivated_abuse",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；校名待归档阶段二次核实"),
    dict(seed_no=3, province="湖北省", city="武汉市", location_precision="city",
         date_start="2024-07", date_precision="month", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="other_harm",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="unknown", is_test_case=0, inclusion_note="收录"),
    dict(seed_no=4, province="广东省", city="湛江市", location_precision="city",
         date_start=None, date_precision="unknown", date_status="claimed_only",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="other_harm",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="no", group_involvement="unknown",
         content_creation_involvement="unknown", is_test_case=0,
         inclusion_note="收录；日期待归档阶段二次核实"),
    dict(seed_no=5, province="湖北省", city="武汉市", location_precision="city",
         date_start="2024-10", date_precision="month", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="dead", harm_categories="poisoning",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；一手来源已补齐（2026-07-27 二次搜索：央视网+腾讯新闻）"),
    dict(seed_no=6, province="山东省", city="淄博市", location_precision="city",
         date_start="2020", date_precision="year", date_status="officially_reported",
         animal_category="cat", estimated_animal_count="80", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="beating|content_motivated_abuse",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="yes", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；历史性案例，推动过反虐待动物立法讨论"),
    dict(seed_no=7, province="河南省", city="南阳市", location_precision="city",
         date_start="2023-08-27", date_precision="day", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="content_motivated_abuse",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；一手来源已补齐（2026-07-27 二次搜索：澎湃新闻+腾讯新闻）；开除决定于 2023-09-02，另有警方行拘 7 日"),
    dict(seed_no=8, province="江苏省", city="南京市", location_precision="city",
         date_start="2024-04", date_precision="month", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="other_harm",
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；一手来源已补齐（2026-07-27 二次搜索：央视网+光明网）；施虐发生于东南大学宿舍，"
                         "机构后续（拒录）发生于南京大学，归档时两校均需体现；日期为拒录报道时间，非施虐时间（待核实）"),
    dict(seed_no=9, province=None, city=None, location_precision="unknown",
         date_start="2023", date_precision="year", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="content_motivated_abuse",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0, inclusion_note="收录"),
    dict(seed_no=10, province="江苏省", city="宿迁市", location_precision="district",
         date_start="2024-11-04", date_precision="day", date_status="officially_reported",
         animal_category="multiple", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="medical_neglect|other_harm",
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="yes", group_involvement="unknown",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；一手来源与日期已补齐（2026-07-27 二次搜索：澎湃新闻）；地点为沭阳县南湖公园动物园"),
    dict(seed_no=11, province="广西壮族自治区", city=None, location_precision="province",
         date_start=None, date_precision="unknown", date_status="claimed_only",
         animal_category="captive_wildlife", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="beating",
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="yes", group_involvement="unknown",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；日期待归档阶段二次核实"),
    # seed #12 (Guangxi zoo flood) intentionally omitted -- excluded from scope
    dict(seed_no=13, province=None, city=None, location_precision="unknown",
         date_start="2026-04", date_precision="month", date_status="claimed_only",
         animal_category="dog", estimated_animal_count="1", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="medical_neglect",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="yes", group_involvement="no",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；用户 2026-07-27 定性为繁育端忽视/虐待（breeder neglect），非单纯消费维权"),
    dict(seed_no=14, province="福建省", city="晋江市", location_precision="city",
         date_start="2015", date_precision="year", date_status="claimed_only",
         animal_category="dog", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="forced_fighting",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="yes", group_involvement="yes",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；对应执法记录待归档阶段二次核实"),
    dict(seed_no=15, province="河南省", city="郑州市", location_precision="city",
         date_start=None, date_precision="unknown", date_status="contradicted",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories=None,
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="no", is_test_case=1,
         inclusion_note="测试用例：举报本身被校方认定为虚假声称，非真实虐猫事件；用于测试 Claim 层 "
                         "support_status=contradicted 与 AF 状态的区分；不计入公开数据集 v0.1"),
    dict(seed_no=16, province="湖南省", city="永州市", location_precision="district",
         date_start="2026-05-28", date_precision="day", date_status="officially_reported",
         animal_category="dog", estimated_animal_count="1", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="inhumane_killing|inhumane_capture",
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；施害方为城管执法人员，官方已致歉并停职"),
    dict(seed_no=17, province="江苏省", city="连云港市", location_precision="city",
         date_start="2026-06-13", date_precision="day", date_status="metadata_supported",
         animal_category="multiple", estimated_animal_count="23", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="inhumane_transport",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="yes", group_involvement="no",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；托运公司层层转包，是否有正式监管通报待归档阶段核实"),
    dict(seed_no=18, province="江苏省", city="苏州市", location_precision="city",
         date_start="2026-02-25", date_precision="day", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="content_motivated_abuse|scalding",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；警方立案记录待归档阶段核实；有英语（Vice）国际报道，适合作多语言来源测试案例"),
    dict(seed_no=19, province="江苏省", city="昆山市", location_precision="city",
         date_start=None, date_precision="unknown", date_status="claimed_only",
         animal_category="multiple", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="medical_neglect",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="yes", group_involvement="unknown",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；央视报道具体年份待归档阶段核实"),
    dict(seed_no=20, province="广东省", city="深圳市", location_precision="district",
         date_start="2019-04-07", date_precision="day", date_status="officially_reported",
         animal_category="other", estimated_animal_count="9", juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="forced_fighting",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="yes", group_involvement="yes",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；原弱来源约束已解除（2026-07-27 二次搜索找到两条独立一手报道：澎湃新闻+都市时报，"
                         "含具体日期/地点/涉案人数/处理结果，来源等级升级为 Tier 2）"),
    # --- Round 2 expansion (2026-07-27, HRL-016), toward the 30-50 v0.1 target ---
    dict(seed_no=21, province="重庆市", city="重庆市", location_precision="district",
         date_start="2026-03", date_precision="month", date_status="officially_reported",
         animal_category="multiple", estimated_animal_count="3+", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="beating|dismemberment|other_harm",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="no", group_involvement="yes",
         content_creation_involvement="unknown", is_test_case=0,
         inclusion_note="收录；\"山姆打包哥\"虐畜风波，重庆首例真正走到立案调查+行拘的候选，"
                         "有独立维基百科条目及线下抗议角度"),
    dict(seed_no=22, province="江苏省", city="徐州市", location_precision="city",
         date_start="2026-07-13", date_precision="day", date_status="officially_reported",
         animal_category="cat", estimated_animal_count="1", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="beating",
         minor_involvement="yes", institutional_involvement="no",
         commercial_involvement="no", group_involvement="yes",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；未成年人案例，警方仅批评教育，未送专门学校——与旺旺案对比处理力度"),
    dict(seed_no=23, province="江苏省", city="连云港市", location_precision="district",
         date_start="2026-02-01", date_precision="day", date_status="officially_reported",
         animal_category="dog", estimated_animal_count="1", juvenile_animal="no",
         mortality_status="dead", harm_categories="burning",
         minor_involvement="yes", institutional_involvement="no",
         commercial_involvement="no", group_involvement="yes",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；未成年人案例，警方调解各赔3000元了事——与旺旺案对比处理力度"),
    dict(seed_no=24, province="四川省", city="成都市", location_precision="district",
         date_start="2024-12-07", date_precision="day", date_status="officially_reported",
         animal_category="cat", estimated_animal_count="1", juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="burning|beating",
         minor_involvement="yes", institutional_involvement="unknown",
         commercial_involvement="no", group_involvement="yes",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；未成年人案例，教育局通报停课反省+心理辅导——与旺旺案对比处理力度；"
                         "动物是否死亡未见明确报道，mortality_status 保守标 unknown"),
    dict(seed_no=25, province="河南省", city="郑州市", location_precision="city",
         date_start="2025-05-21", date_precision="day", date_status="officially_reported",
         animal_category="captive_wildlife", estimated_animal_count="1", juvenile_animal="unknown",
         mortality_status="alive", harm_categories="beating",
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="yes", group_involvement="no",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；郑州锦艺城海洋馆海狮被踢事件，园方开除员工+停业整顿+对海狮做心理安抚"),
    dict(seed_no=26, province="云南省", city="西双版纳傣族自治州", location_precision="city",
         date_start="2026-01-23", date_precision="day", date_status="officially_reported",
         animal_category="captive_wildlife", estimated_animal_count="1", juvenile_animal="yes",
         mortality_status="alive", harm_categories="beating",
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="yes", group_involvement="no",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；西双版纳野生动物园饲养员殴打小象，此前已有多起长期虐待疑似投诉"),
    dict(seed_no=27, province="四川省", city="都江堰市", location_precision="city",
         date_start="2023-03", date_precision="month", date_status="contradicted",
         animal_category="wildlife", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="alive", harm_categories=None,
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="yes", group_involvement="yes",
         content_creation_involvement="yes", is_test_case=0, misattribution_flag=1,
         inclusion_note="收录为 AF 类型测试候选（首个）；核心事实是\"网络谣言被法院判决证实为虚假\"，"
                         "不是一次真实的动物伤害——harm_categories 故意留空，不为凑字段编造伤害方式；"
                         "PRD 原 AF 定义偏向旧视频/异地视频误传，本案是完全捏造的谣言，性质相近但不完全"
                         "等同，methodology.md 需备注这一定义边界"),
    dict(seed_no=28, province="四川省", city=None, location_precision="province",
         date_start="2026-02-25", date_precision="day", date_status="metadata_supported",
         animal_category="multiple", estimated_animal_count="62", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="abandonment",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="unknown", group_involvement="unknown",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；乐山-重庆高速沿线62具宠物尸体，记者实地发现，无法归因到单一施害人，"
                         "跨川渝两地故 city 留空、location_precision 标 province；是否适配 Incident "
                         "单一事件模型存疑，与 HRL-014 性质相同"),
    # --- Round 3 expansion (2026-07-27, HRL-017), clearing the 30-incident floor ---
    dict(seed_no=31, province="北京市", city="北京市", location_precision="district",
         date_start="2022-09-14", date_precision="day", date_status="officially_reported",
         animal_category="multiple", estimated_animal_count="11", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="poisoning",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；\"9·14\"北京宠物中毒案，张某华，目前池中法律后果最重的候选"
                         "（投放危险物质罪，一审4年，二审维持）"),
    dict(seed_no=32, province="山西省", city="晋中市", location_precision="city",
         date_start="2024-05-20", date_precision="day", date_status="officially_reported",
         animal_category="cat", estimated_animal_count="1", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="beating|suffocation",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；晋中学院校猫\"刘海\"事件，校方回应从批评教育升级为报警立案，"
                         "与重庆案类似的回应升级模式"),
    dict(seed_no=33, province="广西壮族自治区", city="南宁市", location_precision="city",
         date_start="2023-08-28", date_precision="day", date_status="officially_reported",
         animal_category="cat", estimated_animal_count="16", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="beating|dismemberment|content_motivated_abuse",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="yes", group_involvement="yes",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；南宁工行\"猫瘾治疗师\"王某某案，银行作为雇主的机构回应"),
    dict(seed_no=34, province="浙江省", city="杭州市", location_precision="city",
         date_start="2020", date_precision="year", date_status="officially_reported",
         animal_category="multiple", estimated_animal_count="约300", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="beating|dismemberment|content_motivated_abuse",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="unknown", group_involvement="unknown",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；浙江警察学院教师王照蔚案，教职工作案类型（此前仅有学生/雇员案例）；"
                         "官方通报本身用实名\"王照蔚\"，按 HRL-015 沿用实名"),
]

# One or more (original_url, source_name, source_type, source_tier, publication_date)
# tuples per seed_no, taken directly from candidate_incidents_seed.md.
SOURCES = {
    1: [
        ("https://zh.wikipedia.org/wiki/%E6%8F%AD%E9%99%BD%E6%8F%AD%E6%9D%B1%E6%9C%AA%E6%88%90%E5%B9%B4%E4%BA%BA%E8%99%90%E7%8B%97%E6%A1%88",
         "维基百科", "other", "2", None),
        ("https://news.sina.com.cn/s/2026-06-30/doc-inifesxs1524289.shtml",
         "新浪新闻", "news", "2", "2026-06-30"),
    ],
    2: [
        ("https://m.gmw.cn/2026-05/15/content_1304457296.htm", "光明网", "news", "2", "2026-05-15"),
        ("https://www.163.com/dy/article/KSU40KLG0550LJ66.html", "网易", "news", "3", None),
    ],
    3: [("https://m.mp.oeeee.com/a/BAAFRD000020240719976606.html", "南方都市报", "news", "2", "2024-07-19")],
    4: [
        ("https://news.cctv.com/2025/06/22/ARTI3mFywdSCwZEoWipFdWqd250622.shtml", "央视网", "news", "1", "2025-06-22"),
        ("https://finance.sina.com.cn/roll/2025-06-25/doc-infcfxpq8273201.shtml", "新浪财经", "news", "2", "2025-06-25"),
    ],
    5: [
        ("https://news.cctv.com/2024/12/07/ARTITlG6kaHFh2VV0jQaUJPa241207.shtml", "央视网", "news", "1", "2024-12-07"),
        ("https://news.qq.com/rain/a/20241207A04CVI00", "腾讯新闻", "news", "2", "2024-12-07"),
    ],
    6: [
        ("https://h5.cqliving.com/info/detail/2456129.html?cid=2456129&cqxhlwdc=3f", "华龙网", "news", "2", "2020-04"),
        ("https://news.qingdaonews.com/wap/2020-04/10/content_21555517.htm", "青岛新闻网", "news", "2", "2020-04-10"),
    ],
    7: [
        ("https://m.thepaper.cn/newsDetail_forward_24488202", "澎湃新闻", "news", "2", "2023-09-02"),
        ("https://news.qq.com/rain/a/20230902A054B200", "腾讯新闻", "news", "2", "2023-09-02"),
    ],
    8: [
        ("https://news.cctv.com/2024/04/07/ARTIZp6CvXMIn8meOOA75WdM240407.shtml", "央视网", "news", "1", "2024-04-07"),
        ("https://m.gmw.cn/2024-04/04/content_1303704302.htm", "光明网", "news", "2", "2024-04-04"),
    ],
    9: [
        ("https://www.chinanews.com.cn/gsztc/2023/05-09/10004022.shtml", "中新网", "news", "2", "2023-05-09"),
        ("https://news.bjd.com.cn/2023/05/13/10429508.shtml", "北京日报", "news", "2", "2023-05-13"),
    ],
    10: [("https://www.thepaper.cn/newsDetail_forward_4862028", "澎湃新闻", "news", "2", "2024-11-04")],
    11: [("https://m.thepaper.cn/newsDetail_forward_1686617", "澎湃新闻（马上评）", "news", "2", None)],
    13: [("https://news.qq.com/rain/a/20260430A04O7D00", "腾讯新闻", "news", "2", "2026-04-30")],
    14: [("https://www.chinanews.com.cn/m/sh/2015/05-04/7250467.shtml", "中新网", "news", "2", "2015-05-04")],
    15: [("https://www.163.com/dy/article/KT0H7ME30550LJ66.html", "网易", "news", "3", None)],
    16: [
        ("https://www.chinanews.com.cn/sh/2026/05-28/10630456.shtml", "中新网", "news", "2", "2026-05-28"),
        ("https://news.cctv.com/2026/05/28/ARTIKTR2iVTX3Hn7Di2WsoLH260528.shtml", "央视网", "news", "1", "2026-05-28"),
    ],
    17: [
        ("https://news.china.com/socialgd/10000169/20260621/49560206.html", "中华网", "news", "2", "2026-06-21"),
        ("https://www.163.com/dy/article/KVUSUM0O05568W0A.html", "网易", "news", "3", None),
    ],
    18: [("https://www.vice.com/en/article/animal-abuse-china-cat-abuse-suzhou/", "Vice", "news", "2", None)],
    19: [("https://m.thepaper.cn/newsDetail_forward_4036022", "澎湃新闻（转央视）", "news", "2", None)],
    20: [
        ("https://m.thepaper.cn/newsDetail_forward_3278123", "澎湃新闻", "news", "2", "2019-04-07"),
        ("https://www.dutenews.com/n/article/181543", "都市时报", "news", "2", None),
    ],
    21: [
        ("https://zh.wikipedia.org/wiki/%E9%87%8D%E6%85%B6%E3%80%8C%E5%B1%B1%E5%A7%86%E6%89%93%E5%8C%85%E5%93%A5%E3%80%8D%E8%99%90%E7%95%9C%E4%BA%8B%E4%BB%B6%E5%8F%8A%E7%A4%BA%E5%A8%81",
         "维基百科", "other", "2", None),
        ("https://m.gmw.cn/2026-06/10/content_1304490199.htm", "光明网", "news", "2", "2026-06-10"),
        ("https://finance.sina.com.cn/wm/2026-06-10/doc-iniawicy6101485.shtml", "新浪财经", "news", "2", "2026-06-10"),
    ],
    22: [
        ("https://i.ifeng.com/c/8ukv2BygIRU", "凤凰网", "news", "2", None),
        ("https://m.sohu.com/a/1050278916_120094090", "搜狐", "news", "3", None),
    ],
    23: [
        ("https://m.163.com/dy/article/KKRV6PS40550B6IS.html", "网易", "news", "3", "2026-02-03"),
        ("https://m.thepaper.cn/newsDetail_forward_32522926", "澎湃新闻", "news", "2", None),
    ],
    24: [
        ("https://news.qq.com/rain/a/20241211A06O1500", "腾讯新闻", "news", "2", "2024-12-11"),
        ("https://m.thepaper.cn/newsDetail_forward_29615413", "澎湃新闻", "news", "2", None),
    ],
    25: [
        ("https://m.gmw.cn/2025-05/22/content_1304042318.htm", "光明网", "news", "2", "2025-05-22"),
        ("https://www.sohu.com/a/897772608_162758", "搜狐", "news", "3", None),
    ],
    26: [
        ("https://finance.sina.com.cn/wm/2026-01-24/doc-inhikrie2742845.shtml", "新浪财经", "news", "2", "2026-01-24"),
        ("https://view.inews.qq.com/a/20260123A0854A00", "腾讯新闻", "news", "2", "2026-01-23"),
    ],
    27: [
        ("https://www.scfzbs.com/tt/202602/83207478.html", "四川法治报", "news", "1", None),
        ("https://finance.sina.com.cn/tech/digi/2026-07-01/doc-iniffyth6379540.shtml", "新浪科技", "news", "2", "2026-07-01"),
    ],
    28: [
        ("https://news.ycwb.com/ikimvkitil/content_53982739.htm", "羊城晚报", "news", "2", None),
        ("https://m.163.com/dy/article/KMRRK76E05149PH8.html", "网易", "news", "3", None),
    ],
    31: [
        ("https://www.sohu.com/a/1010613071_161795", "搜狐", "news", "3", "2025-12-11"),
        ("https://www.jiemian.com/article/13748540.html", "界面新闻", "news", "2", "2025-12-11"),
        ("https://baike.baidu.com/item/9%C2%B714%E5%8C%97%E4%BA%AC%E5%AE%A0%E7%89%A9%E4%B8%AD%E6%AF%92%E6%A1%88/65242193",
         "百度百科", "other", "2", None),
    ],
    32: [("https://news.qq.com/rain/a/20240522A07W5Q00", "腾讯新闻", "news", "2", "2024-05-22")],
    33: [("https://news.qq.com/rain/a/20230903A06QJN00", "腾讯新闻", "news", "2", "2023-09-03")],
    34: [
        ("https://www.thepaper.cn/newsDetail_forward_10709036", "澎湃新闻", "news", "2", "2021-01-08"),
        ("https://www.163.com/news/article/FVRKUM020001899O.html", "网易", "news", "3", None),
    ],
}


def build_incident_id(seq: int) -> str:
    return f"AHID-CN-2026-{seq:04d}"


def seed(db_path: Path) -> None:
    schema_sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_sql)

    seq = 0
    source_seq = 0
    # 2026-07-27 follow-up search resolved 5, 7, 8, 10, 20 (primary sources found);
    # these six remain unresolved.
    needs_verification_seeds = {2, 4, 11, 14, 18, 19}

    for row in INCIDENTS:
        seq += 1
        incident_id = build_incident_id(seq)
        conn.execute(
            """
            INSERT OR REPLACE INTO incidents_public (
                incident_id, seed_candidate_no, province, city, location_precision,
                event_date_start, date_precision, date_status, animal_category,
                estimated_animal_count, juvenile_animal, mortality_status,
                harm_categories, minor_involvement, institutional_involvement,
                commercial_involvement, group_involvement, content_creation_involvement,
                is_test_case, inclusion_note, misattribution_flag
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id, row["seed_no"], row["province"], row["city"], row["location_precision"],
                row["date_start"], row["date_precision"], row["date_status"], row["animal_category"],
                row["estimated_animal_count"], row["juvenile_animal"], row["mortality_status"],
                row["harm_categories"], row["minor_involvement"], row["institutional_involvement"],
                row["commercial_involvement"], row["group_involvement"], row["content_creation_involvement"],
                row["is_test_case"], row["inclusion_note"], row.get("misattribution_flag", 0),
            ),
        )

        needs_verify = 1 if row["seed_no"] in needs_verification_seeds else 0
        for original_url, source_name, source_type, source_tier, publication_date in SOURCES.get(row["seed_no"], []):
            source_seq += 1
            source_id = f"SRC-{source_seq:05d}"
            conn.execute(
                """
                INSERT OR REPLACE INTO sources_public (
                    source_id, incident_id, source_type, source_tier, platform,
                    source_name, original_url, publication_date, language,
                    primary_source_status, independence_status, availability_status,
                    needs_primary_source_verification
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id, incident_id, source_type, source_tier, source_name,
                    source_name, original_url, publication_date, "zh-Hans" if source_name != "Vice" else "en",
                    "unknown", "unknown", "unknown", needs_verify,
                ),
            )

    conn.commit()
    n_incidents = conn.execute("SELECT COUNT(*) FROM incidents_public").fetchone()[0]
    n_sources = conn.execute("SELECT COUNT(*) FROM sources_public").fetchone()[0]
    n_no_source = conn.execute(
        "SELECT COUNT(*) FROM incidents_public i WHERE NOT EXISTS "
        "(SELECT 1 FROM sources_public s WHERE s.incident_id = i.incident_id)"
    ).fetchone()[0]
    conn.close()

    print(f"Seeded {n_incidents} incidents, {n_sources} sources into {db_path}")
    if n_no_source:
        print(f"WARNING: {n_no_source} incident(s) have zero sources logged yet "
              f"(seed_no 5, 7, 8, 10, 20 -- flagged needs_primary_source_verification "
              f"upstream, or in 20's case, still missing entirely). Archive stage "
              f"cannot run on these until at least one URL is found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "ahid_pilot.sqlite3")
    args = parser.parse_args()
    seed(args.db)
