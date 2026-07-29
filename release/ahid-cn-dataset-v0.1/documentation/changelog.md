# Changelog

Follows the spirit of [Keep a Changelog](https://keepachangelog.com/). Since v0.1
is the first release, its entry records what the version contains and the notable
build decisions, rather than differences from a predecessor. Later versions add
entries describing incidents added/removed, pipeline fixes, and any scoring-weight
changes relative to the previous version. English first; 中文版见下半部分。

## [v0.2] — Unreleased (draft) — adds the judgment census sub-corpus

> Draft entry. The data is built and finalized; the release date and whether v0.2
> also bundles other additions are not yet decided. Do not treat this as a
> published record until it carries a DOI and date.

### What v0.2 adds

A new flat table, `judgments_census.csv` — 490 criminal-judgment cases involving
animal harm, drawn from CAIL2018 (the "Law Research Cup" corpus of 2.68 million
pre-2019 single-defendant Chinese criminal judgments, released by a body the
Supreme People's Court's information center took part in). This is the project's
first sub-corpus with an explicit sampling frame: anyone who downloads the same
dataset and runs the same search reproduces the same candidate set, so the census
carries a denominator the 30-incident curated collection cannot.

The census stays a **separate flat table by design** — it does not join the
six-table `incidents_public` schema, run the scoring engine, or generate claims
(census_runbook.md; PRD C14 does not cover it). The public CSV **includes the full
judgment fact text**, because these are official government documents (not
copyright-bearing third-party media), CAIL2018 released them openly, and the
corpus already carries "张某某"-style name masking consistent with the project's
identity policy.

### How the 490 were selected (PRISMA flow, four review rounds)

Full-corpus search returned 754 raw candidates (layer A: four charge types ×
animal terms × harm terms = 368; layer B: strong collocations like 偷狗/毒狗/毒镖
regardless of charge = 386). All 754 were AI-classified; a difflib pass flagged 92
near-duplicate pairs (retained, not merged, so the same real case can appear as
both "confirmed theft with injury" and "alleged-theft investigation" with metadata
distinguishing them).

Round one: a 93-item audit set (borderline + low-confidence non-false-positive +
QC samples) went through the project lead's browser review tool — 78 included, 15
excluded, ~98% agreement with the AI's high-confidence labels. This round included
only 20 of the AI's 332 false-positive calls; 6 of those 20 (30%) turned out to be
real cases, which raised the question of how many more were sitting unreviewed in
the remaining false-positive pool. Round-one public table: 424.

Round two (2026-07-22): a backward audit against the `/data-pipeline-prd`
verification skill split the 332 AI-called false positives by which search layer
had matched them. The 84 that matched layer B — meaning the judgment text
literally contains 偷狗/毒狗/毒镖-class vocabulary, yet the AI still called the case
not-real — carry the highest risk of the exact bias round one had already caught
(the model applying a stricter "was the animal itself harmed" test than the
project's "theft context counts" policy). All 84 have now been read by hand (7
already covered in round one, 77 read fresh this round): 62 reclassified to
poaching, 1 to retaliation, 14 confirmed as genuinely not real cases. Layer-B
false-positive review coverage is 100%.

Round three, same day: the remaining 248 layer-A false positives (no strong
theft/poisoning vocabulary present) were reviewed too, rather than left as an
open question. Since every layer-A record already contains an animal word and a
harm word somewhere in what is often a multi-count indictment — reading all 236
unreviewed ones cover to cover would have been the same cost as round two for a
population expected to have a much lower hit rate — a local-context pass pulled
the ±35-character window around each animal-word mention instead of the
document's opening, which let 17 genuine candidates surface for full-text
reading without requiring a full read of all 236. Result: 3 reclassified to
cruelty, 1 to poaching, 1 to other_true (a pattern layer B never produced: a pet
died in a dispute with a pet hospital — an undisputed fact both sides agree on,
though whether it was actual medical negligence was never adjudicated), and 12
confirmed as genuinely not real cases. The true miss rate here was 5/17 ≈ 29%,
far below layer B's 82% — consistent with the hypothesis that layer B's specific
bias mechanism doesn't transfer to layer A, but not zero, and three of the five
recovered cases are patterns layer B's rescan never surfaced.

**All 332 of the AI's original false-positive calls have now been read by a
person — none of this dataset's false-positive exclusions rest on sampling
extrapolation.**

A fourth pass (2026-07-23) resolved three small remaining inconsistencies rather
than leaving them open: one row whose final label was "borderline" (undecided) —
odd for a published dataset — was resolved to `poaching`, matching a near-duplicate
copy of the same case; three same-case near-duplicate pairs whose two copies had
been given *different* final labels were unified to one label each; and one
case — an illegal electric net that killed a muntjac and a wild boar, charged as
"endangering public safety" rather than under a hunting statute — was confirmed as
a genuine wildlife-poaching case and removed from the census under the project's
existing scope decision that wildlife poaching is a different, larger corpus this
project doesn't cover. That removal is a **scope exclusion, not a false-positive
call** — the case is real, just outside what this table is meant to hold — so it's
tracked with a distinct `out_of_scope` marker rather than being relabeled `fp`.

Final public table: **490** (424 from round one + 63 from round two + 5 from
round three − 2 removed as out of scope in round four).

### Near-duplicate composition (effective N)

CAIL2018 distributes the same judgment across its competition splits (train /
test / valid), so the 490 rows are not 490 distinct cases. A difflib pass over
`fact[:500]` flags 92 near-duplicate pairs (75 of them ≥0.95 similarity); with the
wildlife-exclusion pair removed, 91 remain comparable, collapsing into 73
same-case clusters covering 154 rows. **Effective unique-case count is ~409, not
490** — 81 rows are split-duplication. The design keeps both members rather than
merging (retain-with-metadata: the same real case can carry `recovered_after_theft`
vs `animal_directly_harmed` distinctions across its copies), but anyone computing
counts must dedupe first. Run `pipeline/census_validate.py` for the current
numbers.

### Evidence-transparency flags

The CSV carries per-row flags so the methodology can report evidence strength
honestly rather than presenting all 490 as court-proven harm: `outcome_documented`
= false on 61 industry-pattern presumption cases (the judgment did not state the
animal's fate but the method/motive matched confirmed cases — this is almost
entirely the round-two recovery, since a documented theft context with an
undocumented animal outcome was exactly what round one's stricter AI pass had
missed), `claim_verified` = false on 5 unverified poisoning allegations,
`animal_directly_harmed` = false on 66 dog-theft cases where the animal itself was
not shown to be harmed, `recovered_after_theft` and `perpetrator_confirmed` on 4
each. One row — the round-three pet-hospital death — doesn't fit any existing flag
cleanly and is documented in its own free-text `correction_note` instead of being
forced into one. Most of the 490 are court-documented harm; the flags mark the
minority that entered by presumption or unverified claim.

### Notable finding

The dog-theft-and-poisoning industry chain — the single largest category — is
prosecuted entirely as property crime (theft, robbery, food-safety offenses),
never as cruelty. In the absence of an anti-cruelty statute, intentional harm to
animals enters the criminal record only when it collides with some other offense.
The census is, in effect, an empirical portrait of the legislative gap.

### CAIL2018 limitations (recorded honestly)

No case number, court, or date (competition-corpus anonymization); coverage ends
at 2018; single-defendant cases only (a CAIL2018 construction filter). Provenance
is by dataset + record index rather than a court-website link; individual cases can
be re-anchored to the original judgment via a distinctive fact-text string when
needed. One methodological upside: CAIL2018 was frozen before the 2021 mass
takedown of the judgment website, so it retains some judgments later removed.

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

## [v0.2] — 未发布（草稿）— 新增判决书 census 子语料

> 草稿条目。数据已构建并定稿；发布日期、以及 v0.2 是否同时打包其他新增内容尚未决定。在带上 DOI 与日期之前，不应视为已发布记录。

### v0.2 新增内容

新增扁平表 `judgments_census.csv`——490 条涉动物伤害的刑事判决案件，取自 CAIL2018（"法研杯"语料，268 万份 2018 年前单被告人中国刑事判决，由最高人民法院信息中心参与的机构发布）。这是本项目**首个有明确抽样框的子语料**：任何人下载同一数据集、跑同一检索式，都能复现同一候选集——它有 30 条便利样本所不具备的分母。

census **有意保持为独立扁平表**——不并入 `incidents_public` 六表体系、不跑评分引擎、不生成 claim（见 census_runbook.md；PRD C14 未涉及）。公开 CSV **包含判决书事实认定全文**，因为这些是官方公文（不受版权保护的第三方媒体内容之外）、CAIL2018 已公开发布，且语料自带"张某某"式姓名遮蔽，与项目身份政策天然一致。

### 490 条如何筛选（PRISMA 流水，四轮审核）

全量检索得 754 条原始候选（A 层：4 案由×动物词×伤害词=368；B 层：偷狗/毒狗/毒镖等强搭配词、不限案由=386）。754 条全部经 AI 分类；difflib 比对标出 92 对近重复（保留、未合并，故同一真实案件可同时呈现为"确认盗窃致伤"与"疑似偷狗调查"两个侧面，以元数据区分）。

第一轮：93 条审核集（borderline + 低置信非假阳性 + QC 抽样）经项目负责人的浏览器审核工具终判——78 纳入、15 排除，与 AI 高置信标注约 98% 一致。这一轮只覆盖了 AI 的 332 条假阳性判定中的 20 条，其中 6 条（30%）其实是真实案件，这提出了一个问题：剩下没审核的假阳性里还有多少没被发现。第一轮公开表：424 条。

第二轮（2026-07-22）：按 `/data-pipeline-prd` 验证方法论做回溯审计，把 332 条 AI 判假阳性按命中的检索层拆开看。其中 84 条命中 B 层——即判决原文里明确出现"偷狗/毒狗/毒镖"这类词汇，AI 却仍判定不是真实案件——这批风险最集中，因为它正好对应第一轮已经抓到过的偏差（模型用比项目"偷狗情节即计入"政策更严的标准去判断动物是否受害）。这 84 条现已全部人工读过（第一轮已覆盖 7 条，本轮新读 77 条）：62 条改判 poaching、1 条改判 retaliation、14 条确认原判无误。B 层假阳性审核覆盖率 100%。

第三轮（同日）：剩下 248 条 A 层假阳性（不含强偷狗/毒狗词汇）也审核完了，没有留作悬而未决的问题。由于 A 层每条记录本来就同时含动物词与伤害词（否则不会进候选池），且往往是长达数百字、含 3 起以上独立犯罪事实的起诉书——逐条通读全部 236 条的成本跟第二轮相当，但预期命中率会低得多——改用抓取动物词前后 ±35 字的局部上下文窗口代替读全文开头，从 236 条里筛出 17 条值得深读的候选，再对这 17 条做全文核实。结果：3 条改判 cruelty、1 条改判 poaching、1 条改判 other_true（一种 B 层从未出现过的新模式：一只宠物在与宠物医院的纠纷中死亡——死亡本身双方无争议，但是否构成医疗过失从未经司法认定），12 条确认原判无误。这一轮的真实缺陷率是 5/17≈29%，远低于 B 层的 82%——印证了"B 层那个具体偏差机制在 A 层大概率不适用"的推测，但不是零，找回的 5 条里有 3 条是 B 层重扫完全没出现过的新模式。

**AI 最初判定的 332 条假阳性，现已全部经人工读过——本数据集的假阳性排除，没有一条建立在抽样外推之上。**

第四轮（2026-07-23）：处理了三处剩余的小不一致，没有留作未决问题。一条终判标签是"borderline"（未决）的记录——公开数据集里出现"未决"分类偏怪——被归到 `poaching`，与同案的另一份副本一致；三对因分片不同被独立处理、终判标签却不一样的同案近重复对，逐对统一成一个标签；一起私设电网猎捕野生动物、电死一只麂子和一只野猪、罪名是"以危险方法危害公共安全"而非狩猎类罪名的案件，确认属于真实的野生动物盗猎案，按项目既有的范围决定（野生动物盗猎是另一个更大、性质不同的语料，不在本项目覆盖范围）从 census 中移除。这次移除是**范围排除，不是假阳性判定**——案件本身是真实的，只是不在这张表要覆盖的范围内——所以用独立的 `out_of_scope` 标记区分，不与 `fp` 混为一谈。

最终公开表：**490 条**（第一轮 424 条 + 第二轮找回 63 条 + 第三轮找回 5 条 − 第四轮范围排除 2 条）。

### 近重复构成（有效 N）

CAIL2018 把同一份判决分散在竞赛的 train/test/valid 各分片，所以 490 行并非 490 个不同案件。对 `fact[:500]` 做 difflib 比对标出 92 对近重复（其中 75 对相似度 ≥0.95）；剔除野生动物范围排除那一对后还有 91 对可比较，折叠成 73 个同案簇、覆盖 154 行。**有效唯一案件数约 409，而非 490**——81 行是分片重复。设计上保留双方而非合并（附元数据区分：同一真实案件的不同副本可分别带 `recovered_after_theft` / `animal_directly_harmed` 等区分），但任何做计数的人必须先去重。当前数字见 `pipeline/census_validate.py`。

### 证据类型透明标记

CSV 逐行携带标记，让方法论文能如实报告证据强度，而非把 490 条全部呈现为判决实锤的伤害：`outcome_documented`=false 见于 61 条产业链推定案（判决未明写动物结局，但作案手段/动机与已确认案例一致——这批几乎全部来自第二轮找回，因为"偷狗语境记录在案、动物结局未写"正是第一轮较严标准漏掉的类型），`claim_verified`=false 见于 5 条未经认定的下毒指控，`animal_directly_harmed`=false 见于 66 条偷狗案（动物本身未被证实受伤），`recovered_after_theft` 与 `perpetrator_confirmed` 各 4 条。第三轮找回的宠物医院死亡那条不完全匹配以上任何一个标记，改在 `correction_note` 自由文本里如实说明其证据性质。490 条中绝大多数是判决实证的伤害；这些标记标出以推定或未证实声称纳入的少数。

### 关键发现

偷狗毒狗产业链——最大的单一类别——完全以财产犯罪起诉（盗窃、抢劫、食品安全类罪名），从不以虐待罪起诉。在没有反虐待动物法的情况下，对动物的蓄意伤害只有在恰好触犯别的罪名时才会进入刑事记录。这份 census 实际上就是立法空白的实证画像。

### CAIL2018 局限（如实记录）

无案号、法院、日期（竞赛语料匿名化）；覆盖止于 2018 年；仅单被告人案件（CAIL2018 构建时的过滤）。溯源方式为数据集+记录索引而非文书网链接；需要时可用判决事实中的独特字串把个案回锚到原判决。一处方法学优点：CAIL2018 冻结于 2021 年文书网大规模下架之前，反而保留了部分后来被下架的判决。

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
