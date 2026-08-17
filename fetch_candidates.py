#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_candidates.py — 一次性读取推送标记并输出选题候选（v6 流程）

用法：
  python3 fetch_candidates.py [--mode main|rss] [--hot-limit N] [--rss-limit N]

  --mode main  热榜 + RSS（午间/晚间档，默认）
  --mode rss   仅 RSS（早间档）
  --hot-limit  热榜候选条数上限（默认 60）
  --rss-limit  RSS 候选条数上限（默认 40）

行为：
  1. 读 /opt/TrendRadar/output/.oc_last_push（格式 YYYY-MM-DD HH:MM，Asia/Shanghai）。
     文件不存在或其中日期不是今天 → 上次时间视为今天 00:00。
  2. 热榜：只读当天 news 库，筛选 first_crawl_time >= 窗口起点 且
     (rank<=20 或 权威平台)，按 rank、时间排序，截取前 hot-limit 条。
     热榜库 first_crawl_time 为 HH-MM（连字符）。
  3. RSS：只读当天 rss 库，按时间倒序截取前 rss-limit 条；
     窗口内(first_crawl_time >= 窗口起点)的条目前面加 * 号。
     RSS 库 first_crawl_time 为 HH:MM（冒号）。
  4. 打印（供模型选题）：
     WINDOW=<HH:MM>  TODAY=<YYYY-MM-DD>  MODE=<mode>
     ===HOT===  （仅 main 模式）
     <rank>|<platform>|<title>|<url>
     ===RSS===
     <*?>|<source>|<time>|<title>|<url>

只读，不写任何文件。
"""
import sys, os, re, sqlite3, datetime, argparse
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Shanghai')
NEWS_DIR = '/opt/TrendRadar/output/news'
RSS_DIR = '/opt/TrendRadar/output/rss'
MARKER = '/opt/TrendRadar/output/.oc_last_push'
AUTH = ('thepaper', 'cls-hot', 'wallstreetcn-hot', 'ifeng')


def read_window(today):
    """返回上次推送时间的 datetime（Asia/Shanghai）；缺失/非今天则为今天 00:00。"""
    try:
        raw = open(MARKER).read().strip()
        dt = datetime.datetime.strptime(raw, '%Y-%m-%d %H:%M').replace(tzinfo=TZ)
        if dt.date() != today:
            raise ValueError('marker date is not today')
        return dt
    except Exception:
        return datetime.datetime.combine(today, datetime.time(0, 0), tzinfo=TZ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['main', 'rss'], default='main')
    ap.add_argument('--hot-limit', type=int, default=60)
    ap.add_argument('--rss-limit', type=int, default=40)
    args = ap.parse_args()

    now = datetime.datetime.now(TZ)
    today = now.date()
    win = read_window(today)
    today_s = today.isoformat()

    print(f'WINDOW={win.strftime("%H:%M")}  TODAY={today_s}  MODE={args.mode}')

    # ---- 热榜 ----
    if args.mode == 'main':
        print('===HOT===')
        win_hm = win.strftime('%H-%M')  # 连字符
        db = f'file:{NEWS_DIR}/{today_s}.db?mode=ro'
        try:
            con = sqlite3.connect(db, uri=True)
            ph = ','.join('?' * len(AUTH))
            q = (f"SELECT n.rank, p.name, n.title, n.url FROM news_items n "
                 f"JOIN platforms p ON n.platform_id=p.id "
                 f"WHERE n.first_crawl_time >= ? AND (n.rank <= 20 OR p.id IN ({ph})) "
                 f"ORDER BY n.rank ASC, n.first_crawl_time DESC LIMIT ?")
            for rank, pname, title, url in con.execute(q, (win_hm, *AUTH, args.hot_limit)):
                print(f'{rank}|{pname}|{title}|{url}')
            con.close()
        except Exception as e:
            print(f'HOT-ERROR: {e}')

    # ---- RSS ----
    print('===RSS===')
    win_colon = win.strftime('%H:%M')  # 冒号
    db = f'file:{RSS_DIR}/{today_s}.db?mode=ro'
    try:
        con = sqlite3.connect(db, uri=True)
        q = ("SELECT i.first_crawl_time, f.name, i.title, i.url FROM rss_items i "
             "JOIN rss_feeds f ON i.feed_id=f.id "
             "ORDER BY i.first_crawl_time DESC LIMIT ?")
        for t, fname, title, url in con.execute(q, (args.rss_limit,)):
            mark = '*' if t >= win_colon else ' '
            print(f'{mark}|{fname}|{t}|{title}|{url}')
        con.close()
    except Exception as e:
        print(f'RSS-ERROR: {e}')


if __name__ == '__main__':
    main()
