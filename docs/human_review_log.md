# Human Review Log — AHID

凡需要人工核实、决策或批准的事项一律记录于此表，不允许只存在于对话中。状态：`PENDING` / `DECIDED` / `DEFERRED` / `DROPPED`。

| ID | 提出日期 | 事项 | 需要的决策/核实 | 状态 | 决定 | 决定日期 |
|---|---|---|---|---|---|---|
| HRL-001 | 2026-07-20 | 项目定名 | 选定项目名与数据集命名体系 | DECIDED | AHID（Animal Harm Incident Database / 动物伤害事件数据库）；首期语料 AHID-CN；数据包 `ahid-cn-dataset-vX.Y` | 2026-07-20 |
| HRL-002 | 2026-07-20 | 署名与运营方式 | 实名运营 vs 机构挂靠 vs 团队名义；数据托管司法辖区；家属风险评估 | PARTIALLY DECIDED | 代码/文档层：实名，托管于个人 GitHub 账号 nanyi-deng（隐含决定，2026-07-27 提供仓库 URL 时确认）。**仍开放**：家属风险评估尚未走过一遍；数据集/网站层的署名方式（是否与代码层一致）待 10 月发布前最终确认 | 2026-07-27（部分） |
| HRL-003 | 2026-07-20 | GitHub 可见性 | 是否建 GitHub 远程仓库、公开时点 | DECIDED | 仓库已建：https://github.com/nanyi-deng/animal-harm-incident-database（用户提供，2026-07-27）。首次 push 时仓库内容为 PRD/schema/方法论骨架，不含任何已采集事件数据 | 2026-07-27 |
| HRL-004 | 2026-07-20 | IRB determination | 提交哪所机构、何时提交（8 月材料由 AI 起草，提交须本人） | PENDING | 机构已定：Fordham（`docs/irb/irb_determination_request_draft.md` 已起草，2026-07-27）。**待办**：填入院系/指导教师姓名，确认是否需先完成 CITI 培训，登录 Mentor IRB 提交，回填 submission ID 与预计周期 | |
| HRL-005 | 2026-07-20 | License | 建议：结构化数据 CC BY 4.0；代码 MIT；第三方内容权利保留声明。需确认 | PENDING | | |
| HRL-006 | 2026-07-20 | 域名 | animalharmdatabase.org 与 ahid-cn.org 均可注册（2026-07-20 查证）；ahid.org 已被占用。是否购买、买哪个 | PENDING | | |
| HRL-007 | 2026-07-20 | 事件种子清单 | 9 月 pilot 需要 20 个已知事件的线索清单（含旺旺事件）；收录判断须本人 | DECIDED | 全部 20 条候选审核完成：`docs/pipeline/candidate_incidents_seed.md`。19 条收录、1 条不收录（#12）、1 条特殊测试用例（#15，另计）。#20（斗鸡赌博案）用户接受弱来源，但设约束：pipeline 归档阶段找不到一手来源则 `automation_status` 上限为 A1，不进入公开数据集。另有 11 条标记"归档阶段需二次核实一手来源/日期/校名"——不阻塞 pipeline 启动，转为归档脚本任务 | 2026-07-27 |
| HRL-008 | 2026-07-20 | 隐私 QA 签核 | 每次数据发布前的隐私检查清单（未成年人/身份/地址/敏感媒体）须本人签核；签核模板待建 | PENDING | | |
| HRL-009 | 2026-07-20 | Zenodo/ORCID | Zenodo 账号注册、ORCID 关联、点击发布均须本人（10 月前完成） | PENDING | | |
| HRL-010 | 2026-07-20 | 六语模板人工核对 | §22.3 摘要模板每语一次性翻译定稿后，须母语者或本人核对一遍（每语仅一次） | PENDING | 术语表种子已建：`docs/i18n/glossary.csv`（14 条核心术语，六语）。**注意**：这版是 AI 手动初译，不是走 Cloud Translation + glossary 生产管线（PRD v1.2 C10 的管线用于自由文本，不适用于这批一次性定稿术语）；标记 `machine_draft`，发布前仍需你或母语者逐条核对，尤其西/日/韩三语 | |
| HRL-013 | 2026-07-27 | OSF 项目页 | 文案已起草（`docs/osf_page_copy.md`）；账号注册、页面创建与可见性切换须本人；建议先设 Private，待 HRL-002 家属风险评估完成后再切 Public | PENDING | | |
| HRL-011 | 2026-07-20 | 学术署名 | 确认引用用名（Deng, Nanyi vs Deng, Nancy）与 ORCID iD，写入 CITATION.cff | PENDING | | |
| HRL-012 | 2026-07-20 | PRD 正本入库 | 将 PRD v1.0 + v1.1 正本文件放入 `docs/prd/`（v1.2 补丁已在库） | PENDING | | |
