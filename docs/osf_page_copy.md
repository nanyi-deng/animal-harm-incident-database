# OSF Project Page — Copy Draft

**状态：** Draft for PI review，未发布
**用途：** 创建 OSF 项目页时可直接复制粘贴；OSF 账号注册与发布本身须本人（参照 HRL-009 同类操作性事项，若需单独追踪请在 human_review_log 新增一行）
**建议可见性**：先设为 Private，待 HRL-002 的家属风险评估与最终署名方式确认后再切换 Public——这不阻塞现在起草文案，只阻塞点击 "Make Public"

---

## Title

**AHID: Animal Harm Incident Database — Project Registration and Methods Home**
中文：动物伤害事件数据库（AHID）— 项目注册与方法论主页

## Description（OSF 摘要字段）

**English:**

AHID is an open-source, multilingual incident database that discovers, archives, deduplicates, clusters, and cross-verifies publicly available information about animal harm incidents. Its first corpus, AHID-CN, covers Chinese-language public sources. The project records events and institutional responses — not individual identities — and is designed around source-dependency modeling, evidence-sufficiency scoring, and transparent disclosure of uncertainty and contradiction. This OSF page hosts the project's research registration materials, methodology documentation, and analysis plan; code lives on GitHub, and versioned public datasets will be archived on Zenodo with DOIs.

**中文：**

AHID 是一个开源、多语言的事件数据库，持续发现、保存、去重、归并并交叉核验与动物伤害相关的公开互联网信息。首期语料 AHID-CN 覆盖中文公开来源。项目记录的是事件与机构回应，而非个人身份，围绕来源依赖建模、证据充分度评分与不确定性/冲突的透明展示设计。本 OSF 页面承载项目的研究注册材料、方法论文档与分析计划；代码托管于 GitHub，带版本号与 DOI 的公开数据集将发布于 Zenodo。

## Category

Project（非 Preregistration——数据集/方法尚在迭代，不适合预注册的锁定语义；待方法固定后可考虑单独提交 Registration）

## Wiki 首页建议结构

1. **Overview** — 复用上方 Description
2. **Links** — GitHub: https://github.com/nanyi-deng/animal-harm-incident-database；Zenodo dataset（待 v0.1 发布后补充）
3. **Current status** — 复用 README.md 的 Status 清单（pilot/v0.1/白皮书三个里程碑及日期）
4. **Methodology** — 链接或嵌入 `docs/methodology.md` 全文
5. **Governance and ethics** — 简述去身份化原则、IRB determination 状态（待补）、申诉机制
6. **How to cite** — 待 v0.1 DOI 发布后补充；此前引用本仓库

## Components（OSF 子项目，建议后续按需建立，非本轮必需）

- Data（关联 Zenodo，v0.1 发布后）
- Materials（六语术语表、模板文案定稿版）
- Analysis（gold-standard 审计设计与结果，§8）

## Tags

animal welfare; open-source intelligence; incident database; computational social science; multilingual NLP; evidence provenance; public interest technology; China; social work
