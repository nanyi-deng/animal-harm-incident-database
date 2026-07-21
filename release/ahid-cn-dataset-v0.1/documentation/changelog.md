# Changelog

Follows the spirit of [Keep a Changelog](https://keepachangelog.com/). Since v0.1
is the first release, its entry records what the version contains and the notable
build decisions, rather than differences from a predecessor. Later versions add
entries describing incidents added/removed, pipeline fixes, and any scoring-weight
changes relative to the previous version. English first; 中文版见下半部分。

## [v0.1.1] — 2026-07-20 — documentation correction, no data changes

- **Corrected this changelog**: the copy published with v0.1 had been drafted
  before publication and still described the package as an unpublished local
  staging build with Zenodo publication pending — factually wrong on a published
  record. It now reflects the published status.
- **Corrected internal dates**: several build-log entries were mistakenly dated
  2026-07-27; the work they describe took place on 2026-07-20 (the actual
  publication date, as the Zenodo record itself shows).
- **CITATION.cff updated**: now cites the concept DOI (10.5281/zenodo.21462311,
  always resolves to the latest version) and the actual release date.
- **Data files unchanged** — the four CSV tables are byte-identical to v0.1
  (`checksums.sha256` unchanged). This correction release exercises exactly the
  mechanism described in `known_limitations.md` §6: published versions are
  immutable, so corrections arrive as a new version with a changelog note.

## [v0.1] — 2026-07-20 — first release

DOI: 10.5281/zenodo.21462312

### Dataset composition

30 incidents (Chinese-language public sources), 53 sources, 151 claims, 34
structured institutional-response records. All incidents collected via Tier D
(URL-driven backfill, no automated platform discovery), each individually
approved by the project lead before ingestion (repository
`docs/human_review_log.md` HRL-007, HRL-016, HRL-017). A 31st
pipeline-processed incident (an internal test fixture for contradicted-claim
handling) is excluded from the public dataset by design.

### Pipeline build and notable fixes

- Stages 0–5 (seeding → archiving → dependency analysis → claim extraction →
  scoring → export) first ran end to end on 2026-07-20.
- Archiving fixes: gzip responses were not decompressed, breaking text
  extraction for some sources; overly minimal request headers triggered a CDN's
  anti-bot check, causing at least one actually-reachable source to be
  misclassified as unavailable (found by the human audit; see
  `known_limitations.md`).
- Dependency-analysis fixes: site navigation/footer boilerplate diluted
  text-similarity scores; one source rendered its body via JavaScript so only a
  loading placeholder was captured; generic phrases like "据媒体报道" ("media
  reported") were misread as shared-citation signals.
- Scoring fixes: contradiction findings did not propagate to the incident-level
  `disputed_flag`; four scoring queries counted sources by fetch-timestamp
  presence rather than actual availability, letting dead/blocked links inflate
  scores.
- Added the `responses_public` extraction stage (the table had never been
  populated); fixed a negation-blindness misclassification ("no filing was
  found" matching the "filing" keyword) via an upstream supported-claims-only
  filter; manually excluded one rumor-case claim whose content did not fit any
  response category (rationale in `known_limitations.md` §4).

### Human audit

Gold-standard audit round 1 (repository HRL-018): the project lead reviewed all
31 pipeline-processed incidents against archived source text. Zero content
errors; three minor issues, all source-availability notes rather than content
accuracy, one of which was a real fix (the anti-bot misclassification above).
Limitations of this single-rater round are documented in
`known_limitations.md` §3.

### Privacy QA and license

Heuristic name-scan of all 185 free-text claim/response fields found no
unapproved real names; the four minor-involvement incidents were additionally
read in full — zero identity leakage. One real fix: two incidents (both
involving minors) named a specific residential compound, precise enough to
plausibly identify the children within a small community; blurred to city/county
level, with all other location and institutional detail retained at full
precision. Data license: CC BY-SA 4.0 (deliberately matching the AI Incident
Database's licensing of its core collections); pipeline code: MIT.

---

# 更新日志（中文）

## [v0.1.1] — 2026-07-20 — 文档更正，数据无变化

- 更正本 changelog：随 v0.1 发布的版本系发布前起草，仍将数据包描述为"尚未正式发布的本地暂存构建"——在已发布记录上属于事实错误，现已改为反映发布状态。
- 更正内部日期：多处构建记录误写为 2026-07-27，实际工作与发布日期均为 2026-07-20（以 Zenodo 记录为准）。
- CITATION.cff 更新为 concept DOI（10.5281/zenodo.21462311，恒指向最新版本）与实际发布日期。
- **四张数据 CSV 逐字节不变**（`checksums.sha256` 未变）。本次修订正是 `known_limitations.md` 第六节所述更正机制的首次实际运转：已发布版本不可修改，更正以新版本+changelog 说明的形式出现。

## [v0.1] — 2026-07-20 — 首个正式发布版本

DOI: 10.5281/zenodo.21462312

### 数据集组成

30 条事件（中文公开来源），53 条来源，151 条 claim，34 条结构化机构回应记录。全部事件均通过 Tier D（URL 驱动回填）采集，逐条经项目负责人人工收录判断（主仓库 `docs/human_review_log.md` HRL-007、HRL-016、HRL-017）。流水线处理过的第 31 条事件（矛盾处理内部测试用例）按设计不进入公开数据集。

### 流水线构建与关键修复节点

- Stage 0–5（种子录入 → 归档 → 去重与依赖分析 → claim 抽取 → 评分 → 导出）于 2026-07-20 首次端到端跑通。
- 归档阶段修复：未处理 gzip 压缩响应导致部分来源正文抓取失败；请求头过于精简触发内容分发网络的反爬校验，导致至少 1 条实际可访问的来源被误判为不可用（由人工审计发现，详见 `known_limitations.md`）。
- 依赖分析阶段修复：页面导航/页脚等模板文字稀释了正文相似度计算；一处来源正文由 JavaScript 动态渲染、抓取到的是加载占位符；"据媒体报道"一类泛化措辞被误判为共同引用信号。
- 评分阶段修复：反证/矛盾标记未正确传导至事件级别的 `disputed_flag`；四处评分查询以"是否有抓取时间戳"而非"是否真正可访问"作为来源计入条件，导致死链/被拦截来源虚增评分。
- 新增 `responses_public` 抽取环节（此前该表从未被写入）；修复关键词匹配不理解否定语义导致的分类反转（上游过滤仅处理已证实 claim）；1 条谣言性质事件的 claim 因内容与任何回应类型不符被人工排除（理由见 `known_limitations.md` 第四节）。

### 人工审计

第一轮 gold-standard 人工审计（主仓库 HRL-018）：项目负责人对照归档原文核对全部 31 条流水线处理事件。0 条内容错误；3 条轻微问题均为来源可访问性备注而非内容准确性问题，其中 1 条为真实修复（即上述反爬误判）。单一审核者的局限如实记录于 `known_limitations.md` 第三节。

### 隐私 QA 与许可证

对全部 185 段 claim/response 自由文本做候选人名启发式扫描，未发现未经批准的真实姓名；4 条未成年人涉案事件另行逐条通读全文，零身份线索。1 处真实修复：两条未成年人涉案事件的正文精确到具体小区名，在小规模社区内有实质指认风险，已模糊到市/县级，其余事件的地点与机构细节保持原有精度。数据许可证 CC BY-SA 4.0（刻意与 AI Incident Database 核心数据集合一致）；流水线代码 MIT。
