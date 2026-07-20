# 部署提交 UI（Vercel）——用户操作指南

代码已全部就绪（`src/pages/submit.astro` 表单页 + `api/submit.js` serverless 函数）。
以下步骤需要你本人的账号在浏览器里操作，AI 无法代劳，总计约 20-30 分钟。
参考了 dissertation 项目 `api/DEPLOY.md` 的同款流程，你已经走过一遍类似的。

## 1. GitHub：创建 fine-grained PAT（约 5 分钟）

1. GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token。
2. Repository access 选 **Only select repositories** → 只勾 `animal-harm-incident-database`。
3. Permissions → Repository permissions → **Issues: Read and write**。其他一律不给。
4. 有效期建议选 1 年（到期 GitHub 会发邮件提醒续期）。
5. 生成后**立刻复制**token（只显示一次），下一步要用。

这个 token 泄漏的最坏后果是"有人能在这一个仓库开 issue"——爆炸半径刻意控制到这么小。

## 2. Vercel：导入项目（约 5-10 分钟）

1. vercel.com → Add New → Project → 选 `nanyi-deng/animal-harm-incident-database` 仓库。
2. **Root Directory 设为 `site`**（关键一步，别漏）。Framework 会自动识别为 Astro。
3. 部署前先到 Environment Variables 加两条：
   - `GITHUB_REPO` = `nanyi-deng/animal-harm-incident-database`
   - `GITHUB_TOKEN` = 第 1 步的 PAT
4. Deploy。完成后记下分配的 URL（形如 `https://xxx.vercel.app`）。

此时表单已经可用（蜜罐 + 频率限制生效，人机验证暂缺，见第 3 步）。

## 3. Cloudflare Turnstile：人机验证（约 10 分钟，建议做但可稍后补）

1. dash.cloudflare.com 注册/登录（免费）→ 左侧 Turnstile → Add widget。
2. Widget 名随意；Domains 填你的 Vercel 域名（以及未来的自有域名）；Mode 选 **Managed**。
3. 拿到 **Site Key** 和 **Secret Key**，回到 Vercel 项目 → Settings → Environment Variables 加两条：
   - `PUBLIC_TURNSTILE_SITE_KEY` = Site Key
   - `TURNSTILE_SECRET_KEY` = Secret Key
4. Redeploy（Vercel 项目页 → Deployments → 最新一条 → Redeploy），让新环境变量生效。

没配这一步时表单照常工作，只是防机器人能力弱一档——代码里是优雅降级，不会报错。

## 4. 线上冒烟测试（部署完成后，5 分钟）

- [ ] 打开 `https://你的域名/submit/`，表单正常渲染、暗色模式正常
- [ ] 提交一条测试线索（链接用任意真实新闻 URL，简述注明"测试"）→ 页面显示成功
- [ ] 到 GitHub 仓库 Issues 确认出现一条带 `incident-submission` 标签的新 issue，正文格式含"### 事件公开报道链接（必填）"等小节
- [ ] 跑 `python3 pipeline/screen_submissions.py`，确认这条测试提交被正常解析预筛
- [ ] 删除测试 issue
- [ ] 不填必填项提交一次 → 确认被前端拦截；简述少于 10 字 → 确认后端返回错误

## 5. 已知事项

- **大陆可达性**：`*.vercel.app` 在大陆经常不可达（PRD §3 已如实记录）。绑自有域名（HRL-006）可显著改善；若实测不行，备选方案是平移 Cloudflare Pages，代码基本不用改。
- **网站整体仍是 noindex**：部署 ≠ 公开推广。取消 noindex、正式对外是另一个决定，部署完提交 UI 不会自动改变网站的公开状态。
- 频率限制是 serverless 实例内存级的（冷启动即重置），软刹车而非硬保证——真正的防线是 Turnstile，这是第 3 步值得做的原因。
