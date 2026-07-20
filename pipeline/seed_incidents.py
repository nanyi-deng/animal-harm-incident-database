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
         inclusion_note="收录；一手来源待归档阶段二次核实"),
    dict(seed_no=6, province="山东省", city="淄博市", location_precision="city",
         date_start="2020", date_precision="year", date_status="officially_reported",
         animal_category="cat", estimated_animal_count="80", juvenile_animal="unknown",
         mortality_status="dead", harm_categories="beating|content_motivated_abuse",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="yes", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；历史性案例，推动过反虐待动物立法讨论"),
    dict(seed_no=7, province="河南省", city="南阳市", location_precision="city",
         date_start="2023", date_precision="year", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="content_motivated_abuse",
         minor_involvement="no", institutional_involvement="unknown",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0,
         inclusion_note="收录；一手通报链接待归档阶段二次核实"),
    dict(seed_no=8, province="江苏省", city="南京市", location_precision="city",
         date_start=None, date_precision="unknown", date_status="claimed_only",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="other_harm",
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="unknown", is_test_case=0,
         inclusion_note="收录；事件核心是机构后续（拒录），非施虐行为本身；一手来源待核实"),
    dict(seed_no=9, province=None, city=None, location_precision="unknown",
         date_start="2023", date_precision="year", date_status="officially_reported",
         animal_category="cat", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="content_motivated_abuse",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="no", group_involvement="no",
         content_creation_involvement="yes", is_test_case=0, inclusion_note="收录"),
    dict(seed_no=10, province="江苏省", city="宿迁市", location_precision="city",
         date_start=None, date_precision="unknown", date_status="claimed_only",
         animal_category="multiple", estimated_animal_count=None, juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="medical_neglect|other_harm",
         minor_involvement="no", institutional_involvement="yes",
         commercial_involvement="yes", group_involvement="unknown",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录；一手报道链接与日期待归档阶段二次核实"),
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
         date_start="2019", date_precision="year", date_status="claimed_only",
         animal_category="other", estimated_animal_count="9", juvenile_animal="unknown",
         mortality_status="unknown", harm_categories="forced_fighting",
         minor_involvement="no", institutional_involvement="no",
         commercial_involvement="yes", group_involvement="yes",
         content_creation_involvement="no", is_test_case=0,
         inclusion_note="收录（用户接受弱来源）；约束：归档阶段找不到一手来源则 automation_status "
                         "上限为 A1，不进入公开数据集"),
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
    4: [("https://www.zhihu.com/question/1920061492117640254/answer/1920412957826851731",
         "知乎（引用海大通报）", "blog", "3", None)],
    5: [],  # no directly citable URL from this round's search; needs a follow-up search pass
    6: [("https://www.zhihu.com/question/386412537", "知乎讨论帖", "blog", "3", None)],
    7: [],  # needs a follow-up search pass for a primary link
    8: [],  # needs a follow-up search pass for a primary link
    9: [
        ("https://www.chinanews.com.cn/gsztc/2023/05-09/10004022.shtml", "中新网", "news", "2", "2023-05-09"),
        ("https://news.bjd.com.cn/2023/05/13/10429508.shtml", "北京日报", "news", "2", "2023-05-13"),
    ],
    10: [],  # needs a follow-up search pass for a primary link
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
    20: [],  # weakest-sourced candidate; no primary link located this round -- see inclusion_note
}


def build_incident_id(seq: int) -> str:
    return f"AHID-CN-2026-{seq:04d}"


def seed(db_path: Path) -> None:
    schema_sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_sql)

    seq = 0
    source_seq = 0
    needs_verification_seeds = {2, 4, 5, 7, 8, 10, 11, 14, 18, 19, 20}

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
                is_test_case, inclusion_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id, row["seed_no"], row["province"], row["city"], row["location_precision"],
                row["date_start"], row["date_precision"], row["date_status"], row["animal_category"],
                row["estimated_animal_count"], row["juvenile_animal"], row["mortality_status"],
                row["harm_categories"], row["minor_involvement"], row["institutional_involvement"],
                row["commercial_involvement"], row["group_involvement"], row["content_creation_involvement"],
                row["is_test_case"], row["inclusion_note"],
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
