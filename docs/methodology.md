# AHID Methodology（骨架 — v0.1 目标：2026-08 成稿）

> 本文档是公开方法说明与未来方法论文（working paper）的共同底稿。每节标注状态：`stub` / `draft` / `final`。

## 1. Overview and Positionality — `stub`

项目定位（incident database，非定罪平台）；与 AI Incident Database 方法论谱系的关系；**positionality 声明**：项目起源于旺旺个案倡议，此起源对收录优先级的潜在影响及缓解措施（PRD v1.2 C8）。

## 2. Scope and Inclusion Criteria — `stub`

地理与事件范围（PRD §7）；默认不收录清单；AHID-CN 语料定义。

## 3. Data Model — `draft`

六对象模型（Incident / Source / Media Asset / Claim / Evidence Relation / Response，PRD §8）；公开数据集四表结构见 `data_dictionary.csv`（权威版本）。

## 4. Source Tiers and Independence — `stub`

来源四级体系（PRD §11.1）；来源依赖图；**独立性三值保守判定规则**（PRD v1.2 C4）——方法论文的核心贡献之一。

## 5. Pipeline — `stub`

研究版 MVP 采集方式：Tier D URL 驱动回填（无自动发现）；归档、去重（URL/文本/图片/视频 Hash）、事件归并、Claim 提取、反证检索各环节；每个机器提取字段携带 value / confidence / evidence_span / source_id / model_version。

## 6. Evidence Sufficiency Scoring — `stub`

评分结构与权重（PRD §20，v0 未校准）；扣分规则与下限；分数与状态（A0–A4/AX/AF）的判定关系（PRD v1.2 C4）；score_version 版本管理。

## 7. Privacy, Minors, and Identity Protection — `stub`

去身份化原则；未成年人字段联动规则（minor_involvement=yes → 全库无身份字段）；face detection（允许，仅遮挡）与 face recognition（禁止）的区分；公开层不再分发第三方媒体原则（PRD v1.2 C2）。

## 8. Human Audit and Gold-Standard Set — `stub`

季度抽样审计设计（≥30 事件）；标注维度（聚类/去重/字段/独立性）；precision 报告；gold set 的三重用途（权重校准、论文评估、回归测试）；标注工具（human-label-tool）。**方法论文的评估章。**

## 9. Multilingual Generation — `stub`

模板本地化架构（PRD v1.2 C10）：模板一次性定稿、槽位程序化填充、OpenCC 简繁转换、残余文本 Cloud Translation + glossary + 脚本化 QA、失败回退。

## 10. Known Biases and Limitations — `stub`

报道/地区/平台/语言/内容/删除/模型七类偏差（PRD §33）；"数据库不代表真实发生率"的解释边界。

## 11. Ethics and Governance — `stub`

IRB determination（结果待补，见 human_review_log HRL-004）；申诉与更正机制及 SLA；存续与落日条款；规则引擎（非 LLM）作为发布决策者。

## 12. Versioning and Citation — `stub`

数据集季度 snapshot 与 Zenodo DOI；score_version / ruleset_version / model_version 三版本体系；引用规范。
