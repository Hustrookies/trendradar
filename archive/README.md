# archive/ — 定时任务提示词归档

OpenClaw cron 任务 "TrendRadar H5(GitHubPages)" 各版本 job message 的存档。

| 文件 | 版本 | 使用时间段 | 说明 |
|---|---|---|---|
| job_message_v3.txt | v3 | 2026-08-10 ~ 08-12 上午；08-12 下午 ~ 08-17 下午 | 加入 RSS 源（每源≥1条）、选择性中英双语、分类配额（科技40/财经20/国际20/国内10/体育10）。仅同日时间窗去重，无跨期去重 → 出现跨天重复推送（如英伟达5000亿新闻重复出现在 8.11/8.12 早报）。单次运行约 350K token |
| job_message_v5.txt | v5 | 2026-08-12 中午短暂启用后回退 | 在 v3 基础上增加跨期去重：已推送台账 `.oc_pushed_items.json`（URL/标题精确去重由内置 Python 脚本完成，模型仅做近48h语义去重）；推送成功后追加台账并保留7天。v4（LLM 直接读台账逐条比对）因引发模型推理失控导致任务失败，未归档 |
| job_message_v6.txt | v6 | 2026-08-17 晚起（当前，午/晚间档 12:00/22:00） | 选题标准与 v3 相同，但为降 token 开销（目标 ~100K/次）把流程机械化：模型只做 2 次 exec 调用——`fetch_candidates.py --mode main` 取候选（自动读标记/限量输出）→ 输出选题 JSON 给 `render_issue.py`（套模板/写 index/清理旧刊/git 提交推送/轮询发布/写回标记全部由脚本完成，yieldMs=120000 一次同步跑完）。去重仍仅同日时间窗 |
| job_message_v6_morning.txt | v6 早间档 | 2026-08-18 早起（当前，06:00 RSS-only） | v6 的早间档变体：`fetch_candidates.py --mode rss --rss-limit 60`，只从 RSS 选题，配额 科技40/财经25/国际25 |

配套脚本（位于本仓库根目录）：
- `fetch_candidates.py` — v6 取候选脚本（读 `.oc_last_push` 标记 + 只读查询当天 news/rss 库，限量输出）
- `render_issue.py` — v6 渲染脚本（选题 JSON → HTML/index.html → 清理旧刊 → git commit+push（被拒自动 rebase 重推）→ 轮询发布 → 写回标记）

配套状态文件（不在本仓库，位于服务器）：
- `/opt/TrendRadar/output/.oc_last_push` — 上次推送时间标记
- `/opt/TrendRadar/output/.oc_pushed_items.json` — 已推送条目台账（7天窗口；v5 遗留，v3/v6 均不读写）
