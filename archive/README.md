# archive/ — 定时任务提示词归档

OpenClaw cron 任务 "TrendRadar H5(GitHubPages)" 各版本 job message 的存档。

| 文件 | 版本 | 使用时间段 | 说明 |
|---|---|---|---|
| job_message_v3.txt | v3 | 2026-08-10 ~ 08-12 上午；08-12 下午起重新启用（当前） | 加入 RSS 源（每源≥1条）、选择性中英双语、分类配额（科技40/财经20/国际20/国内10/体育10）。仅同日时间窗去重，无跨期去重 → 出现跨天重复推送（如英伟达5000亿新闻重复出现在 8.11/8.12 早报） |
| job_message_v5.txt | v5 | 2026-08-12 中午短暂启用后回退 | 在 v3 基础上增加跨期去重：已推送台账 `.oc_pushed_items.json`（URL/标题精确去重由内置 Python 脚本完成，模型仅做近48h语义去重）；推送成功后追加台账并保留7天。v4（LLM 直接读台账逐条比对）因引发模型推理失控导致任务失败，未归档 |

配套状态文件（不在本仓库，位于服务器）：
- `/opt/TrendRadar/output/.oc_last_push` — 上次推送时间标记
- `/opt/TrendRadar/output/.oc_pushed_items.json` — 已推送条目台账（7天窗口）
