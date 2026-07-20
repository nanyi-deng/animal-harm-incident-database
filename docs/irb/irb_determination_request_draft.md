# Fordham IRB — Determination Request Draft (AHID / AHID-CN)

**状态：** Draft for PI review — 未提交
**用途：** 在 Fordham Mentor IRB 系统中创建新提交（New Study）时可直接复制粘贴的叙述文本；实际点击提交须本人（HRL-004）
**重要声明：** 本文档由 AI 助手基于 Fordham IRB 公开指引页面（Guidelines and Procedures、FAQ、Exempt and Expedited Research）与通用 Common Rule（45 CFR 46）豁免范畴起草，**不构成法律或伦理意见**。最终判定权在 Fordham IRB（irb@fordham.edu）；提交前建议与 dissertation advisor 过一遍，因其与 dissertation 方法论（公开数据的二次研究使用）有直接可比性。

Fordham 官方立场（2026-07-27 查证）：即使研究者自认为符合豁免条件，仍必须正式提交 Mentor IRB 系统申请一次 determination，不能自行认定为"不需要 IRB"。

---

## 1. 建议申请路径

按优先顺序申请以下两种 determination 之一（Mentor IRB 表单通常会先问"是否构成 human subjects research"，回答后系统据此路由）：

**首选：Not Human Subjects Research（不构成人体研究）。**
论证核心：本项目不满足 45 CFR 46.102(e) 对 "human subject" 的定义——既不通过干预/互动从在世个人获取数据（无问卷、无访谈、无联系涉事者），采集的信息也不构成"私密信息"（仅限公开可访问、无需登录、无需绕过任何访问限制的网页与账号主页；PRD §11.3 明确禁止绕过验证码、登录墙或获取私聊/私密群组内容）。

**备选（若 IRB 认定仍构成 human subjects research）：Exempt — Category 4（对已存在数据的二次使用）。**
论证核心：数据在研究开始前已经公开存在；且本项目的核心设计原则（去身份化，PRD §6.4）确保记录以事件为分析单位、系统性剥离可识别个人信息，普通个人不会以可识别方式出现在公开数据集或论文中。

## 2. 项目描述（可直接用于 Mentor IRB "Project Description" 字段）

**中文：**

本项目（AHID / AHID-CN，Animal Harm Incident Database — Chinese-language Incident Corpus）是一个开源、多语言的事件数据库，系统性收集、归档、去重并交叉核验与中国大陆动物伤害相关的公开互联网信息（政府通报、新闻报道、公开社交媒体帖子等）。项目仅处理研究开始前已经公开存在的信息，不采集任何私密、需登录或需绕过访问限制获得的内容。分析单位是"事件"（event），不是个人：系统的核心设计原则明确排除普通个人身份信息的记录与公开发布，未成年人身份信息（姓名、面部、学校、住址）在任何情况下均自动屏蔽，不进入公开数据集。研究者与在世个人之间不发生任何直接互动或干预。数据用途为构建可供新闻、政策研究与学术研究使用的结构化公开事件档案，并将产出方法论文，评估自动化事件归并、来源核验与证据充分度评分方法的表现。

**English:**

This project (AHID / AHID-CN, Animal Harm Incident Database — Chinese-language Incident Corpus) is an open-source, multilingual incident database that systematically discovers, archives, deduplicates, and cross-verifies publicly available internet information related to animal harm incidents associated with mainland China (government notices, news reports, public social media posts). The project processes only information that was already publicly available before the research began, and does not collect any private, login-gated, or access-restriction-circumvented content. The unit of analysis is the event, not the individual: a core design principle excludes the recording or public disclosure of ordinary individuals' identifying information, and identifying information about minors (name, face, school, address) is automatically suppressed in all cases and never enters the public dataset. The researcher has no direct interaction or intervention with any living individual. The data support a structured, public incident archive usable by journalists, policy researchers, and academics, and will inform a methods paper evaluating automated event clustering, source verification, and evidence-sufficiency scoring.

## 3. 预期会被问到的字段（提前准备好答案）

| Mentor IRB 常见字段 | 建议回答要点 |
|---|---|
| Subject population | 无人类受试者被招募或互动；数据主体是公开发布内容的账号/机构，非研究参与者 |
| Recruitment | 不适用（无招募） |
| Consent | 不适用（无直接互动；公开发布内容豁免知情同意，属二手数据二次分析常规做法） |
| Data collection method | 公开网页/API 抓取与人工 URL 回填（Tier D，本轮不做需登录或需绕过限制的采集） |
| Identifiability | 公开数据集不含普通个人可识别信息；未成年人身份信息自动屏蔽，不进入任何公开产出 |
| Data storage/security | 原始媒体与内部字段存于访问受限存储；公开数据集单独打包，见 data_dictionary.csv |
| Risks to subjects | 极小风险（minimal risk）：不接触受试者、不改变其处境；主要风险为误归属/误识别，已有 PRD 层面的纠错与申诉机制（AF 状态、申诉 SLA） |
| International data | 数据来源为中国大陆公开平台，存储与处理位于研究者所在司法辖区 |
| PI/researcher | Nanyi Deng, PhD Candidate, [Fordham 院系待填], 指导教师：[待填] |

## 4. 提交前检查清单

- [ ] 与 dissertation advisor 讨论一次（可比先例：CPS policy RAG 项目同样处理已公开的政策文本）
- [ ] 登录 Mentor IRB，确认当前是否需要先完成 CITI 培训（多数机构要求）
- [ ] 将上方"项目描述"粘入系统对应字段，按系统实际字段结构调整措辞
- [ ] 附上本仓库 README 与 PRD v1.2 补丁链接作为补充材料（若系统支持附件/链接）
- [ ] 提交后记录 submission ID 与预计审核周期，回填 `docs/human_review_log.md` HRL-004
