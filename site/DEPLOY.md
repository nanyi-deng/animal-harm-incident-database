# 部署提交 UI（Cloudflare Pages）——用户操作指南

代码已全部就绪（`src/pages/submit.astro` 表单页 + `functions/api/submit.js` Cloudflare Pages Function）。
以下步骤需要你本人的账号在浏览器里操作，AI 无法代劳，总计约 20-30 分钟。

**为什么是 Cloudflare Pages 不是 Vercel**：PRD C14（2026-07-21）——`*.vercel.app` 在中国大陆经常不可达
（实测延迟增加 3-8 倍、连接常超时）；Cloudflare Pages 的可达性也不保证（GFW 对 Cloudflare 按 IP/SNI
选择性封锁），但优于 Vercel 且免费。这不是完美方案，只是本阶段成本最低的合理选择——网站首要受众
是本轮求职季的国际学术评审人，大陆可达性是加分项不是硬指标；Zenodo 数据集是不依赖网站的备用获取渠道。

## 1. GitHub：创建 fine-grained PAT（约 5 分钟）

1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token。
2. Repository access 选 **Only select repositories** → 只勾 `animal-harm-incident-database`。
3. Permissions → Repository permissions → **Issues: Read and write**。其他一律不给。
4. 有效期建议选 1 年（到期 GitHub 会发邮件提醒续期）。
5. 生成后**立刻复制**token（只显示一次），下一步要用。

这个 token 泄漏的最坏后果是"有人能在这一个仓库开 issue"——爆炸半径刻意控制到这么小。

## 2. Cloudflare Pages：导入项目（约 5-10 分钟）

1. dash.cloudflare.com 注册/登录（免费）→ Workers & Pages → Create → Pages → Connect to Git。
2. 选 `nanyi-deng/animal-harm-incident-database` 仓库并授权。
3. Build 设置：
   - **Root directory**：`site`（关键一步，别漏——仓库根目录不是 Astro 项目根）
   - **Build command**：`npm run build`
   - **Build output directory**：`dist`
   - Framework preset 可选 Astro（若列表里有）
4. 部署前先到 Settings → Environment variables 加两条（Production 和 Preview 都要加，或至少 Production）：
   - `GITHUB_REPO` = `nanyi-deng/animal-harm-incident-database`
   - `GITHUB_TOKEN` = 第 1 步的 PAT
5. Save and Deploy。完成后记下分配的 URL（形如 `https://xxx.pages.dev`）。

此时表单已经可用（蜜罐 + 频率限制生效，人机验证暂缺，见第 3 步）。`functions/api/submit.js` 会被
Cloudflare 自动识别为 Pages Function，映射到 `/api/submit`，无需额外配置。

## 3. Cloudflare Turnstile：人机验证（约 10 分钟，建议做但可稍后补）

1. dash.cloudflare.com → 左侧 Turnstile → Add widget。
2. Widget 名随意；Domains 填你的 `*.pages.dev` 域名（以及未来的自有域名）；Mode 选 **Managed**。
3. 拿到 **Site Key** 和 **Secret Key**，回到 Pages 项目 → Settings → Environment variables 加两条：
   - `PUBLIC_TURNSTILE_SITE_KEY` = Site Key（注意：这个要在**构建时**注入，Astro 用 `import.meta.env` 读取，
     需要在 Cloudflare Pages 的 Build 环境变量里设置，不是 Runtime 变量）
   - `TURNSTILE_SECRET_KEY` = Secret Key（Function 运行时读取，设为 Runtime 环境变量即可）
4. Retry deployment（Pages 项目页 → Deployments → 最新一条 → Retry deployment），让新环境变量生效。

没配这一步时表单照常工作，只是防机器人能力弱一档——代码里是优雅降级，不会报错。

## 4. 线上冒烟测试（部署完成后，5 分钟）

- [ ] 打开 `https://你的域名/submit/`，表单正常渲染、暗色模式正常
- [ ] 提交一条测试线索（链接用任意真实新闻 URL，简述注明"测试"）→ 页面显示成功
- [ ] 到 GitHub 仓库 Issues 确认出现一条带 `incident-submission` 标签的新 issue，正文格式含"### 事件公开报道链接（必填）"等小节
- [ ] 跑 `python3 pipeline/screen_submissions.py`，确认这条测试提交被正常解析预筛
- [ ] 删除测试 issue
- [ ] 不填必填项提交一次 → 确认被前端拦截；简述少于 10 字 → 确认后端返回错误

## 5. 已知事项

- **大陆可达性**：Cloudflare Pages 的可达性不是保证（PRD C14 已如实记录，见 astro.config.mjs 注释）。
  页脚已加提示语，引导访问不通的用户改用 Zenodo 数据集。绑自有域名（HRL-006）不会解决这个问题——
  瓶颈在 Cloudflare 的 IP/SNI 被 GFW 选择性封锁，不在域名本身。
- **网站整体仍是 noindex**：部署 ≠ 公开推广。取消 noindex、正式对外是另一个决定，部署完提交 UI 不会自动改变网站的公开状态。
- 频率限制是 Worker isolate 内存级的，软刹车而非硬保证——真正的防线是 Turnstile，这是第 3 步值得做的原因。
- 若之后要重新评估更强的大陆访问方案（香港 CDN 加速 / ICP 备案），走 PRD C14 的重新评估触发条件，
  不要作为单纯的部署技术问题处理——ICP 备案牵涉真实身份关联，与 §41.2 家属风险评估同一决策层级。
