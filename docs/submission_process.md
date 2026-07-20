# 公开提交事件线索的处理流程

对应 `human_review_log.md` HRL-021。这份文档说明"任何人都能提交线索，但没有任何一条线索能自动进入数据库"这个原则在具体机制上是怎么落地的。

## 为什么不做"agent 自动核实通过就发布"

最初讨论过让 agent 判断"证据是否充分"然后自动过审，明确决定不这么做，理由记录在 HRL-021：

- PRD 的既有原则——"发布决策由规则引擎而非语言模型执行"（`methodology.md` §11）——针对的正是这种情况：一个基于文本判断"是否可信"的系统，本质上是语言模型式的判断，不是规则引擎。
- 公开提交入口一旦自动过审，任何人都可以用来构陷一个具体的人或机构，而 AF（错误归属/谣言）状态的存在本身就说明这类假指控在这个领域是真实发生过的问题（见 #26 大熊猫谣言案）。
- 现有 31 条收录事件没有一条是自动收录的，全部经过人工判断（HRL-007/016/017）。公开提交的线索没有理由被给予更低的审核门槛。

## 实际流程

1. **提交**（两个渠道，进入同一条流水线）：
   - **网站表单（主入口，面向普通用户）**：`/submit/` 页面（`site/src/pages/submit.astro`），零注册、零 GitHub 知识要求。提交经 Vercel serverless 函数（`site/api/submit.js`）校验（必填字段、URL 格式、蜜罐、频率限制、Cloudflare Turnstile 人机验证）后，自动创建带 `incident-submission` 标签的 GitHub issue——正文格式与 GitHub 模板渠道完全一致（已用测试验证两渠道解析结果逐字段相同）。部署步骤见 `site/DEPLOY.md`（需用户账号操作）。架构决策与成本核算见 `docs/prd/submission_ui_prd_draft.md`（HRL-022）。
   - **GitHub Issue 表单（备用，面向懂技术的协作者）**：`.github/ISSUE_TEMPLATE/incident_submission.yml`，字段相同。

   两个渠道都有"确认未写出未成年人身份信息"的强制确认项；网页渠道并明确提示提交内容将公开、请勿留个人联系方式。
2. **agent 预筛**（`pipeline/screen_submissions.py`）：拉取所有带 `incident-submission` 标签的开放 issue，对每条提交做**纯机械性检查**——链接是否可以打开、页面是否疑似失效/反爬拦截页、URL 是否与已收录来源完全重复。**不判断内容是否属实、是否达到收录标准**——这两件事都是人来做的。结果追加写入 `docs/pipeline/submitted_candidates_pending_review.md`，格式跟现有 `candidate_incidents_seed.md` 一致，方便直接比对审核。
3. **人工审核**：PI（或未来的项目协作者，视分工另行确定）按 `release/ahid-cn-dataset-v0.1/documentation/inclusion_exclusion_criteria.md` 的标准逐条判断，结论写回 `submitted_candidates_pending_review.md`，通过的移入 `candidate_incidents_seed.md` 并进入正常的 Stage 0-5 流水线；不通过的在 GitHub issue 下回复理由并关闭。
4. **提交者不会自动收到"已收录"通知**——现阶段没有自动回复机制（没有配置 GitHub token），审核结论目前需要人工回到 issue 下评论。这个手动步骤未来可以脚本化，但现在没做，避免为了自动化而自动化。

## 关于协作者

如果之后有多人参与审核（不只是 PI 一个人），这个流程本身不需要改——第 3 步"谁来审"是分工问题，不影响"agent 只预筛、人来判断"这条边界。具体由谁审、怎么分工，待你确定后另行记录。

## 运行方式

```
python3 pipeline/screen_submissions.py
```

需要能访问 GitHub API 和被提交的各个 URL；不需要 GitHub token（读取公开 issue 不需要认证）。
