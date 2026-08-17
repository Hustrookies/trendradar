#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_issue.py — TrendRadar H5 渲染器（v6 流程核心脚本）

从 stdin 读取选题 JSON，一次完成：
  套模板生成 <YYYY-MM-DD-HHMM>.html + index.html → 清理 7 天前旧刊 →
  git commit + push（被拒自动 pull --rebase 重推一次）→ 轮询发布状态 →
  写回 /opt/TrendRadar/output/.oc_last_push 标记。

输入 JSON 格式：
{
  "title": "热点精选 08-17 晚间档",
  "desc":  "一句话本期概述",
  "items": [
    {"cat":"科技","badge":"知乎 · 第1名","url":"https://...","main":"中文标题"},
    {"cat":"财经","badge":"CNBC 国际(财经) · RSS","url":"https://...",
     "main":"中文翻译标题","sub":"英文原标题"}
  ]
}

输出（stdout 每行一个键值）：
  SLUG=<YYYY-MM-DD-HHMM>
  URL=<发布地址>
  CARDS=<条数> REMOVED=<清理旧刊数>
  PUSH=ok|failed
  FINAL=<http状态码>（仅 PUSH=ok 时）
  MARKER=written（仅 PUSH=ok 时）

退出码：0=成功；1=输入错误；2=推送失败。

测试用环境变量：
  RD_REPO      覆盖仓库目录（默认 /opt/trend-digest/repo）
  RD_MARKER    覆盖标记文件路径
  RD_SKIP_PUSH=1  只渲染+清理，不做 git/轮询/写标记
"""
import sys, os, json, html, re, subprocess, time, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(os.environ.get('RD_REPO', '/opt/trend-digest/repo'))
MARKER = Path(os.environ.get('RD_MARKER', '/opt/TrendRadar/output/.oc_last_push'))
SKIP_PUSH = os.environ.get('RD_SKIP_PUSH') == '1'
BASE = 'https://hustrookies.github.io/trendradar'
CATS = ['科技', '财经', '国际局势', '国内要点', '体育']
TZ = ZoneInfo('Asia/Shanghai')


def die(msg, code=1):
    print(f'ERROR: {msg}')
    sys.exit(code)


def esc(s):
    return html.escape(str(s), quote=True)


def main():
    raw = sys.stdin.read()
    if len(raw) > 200_000:
        die('input too large')
    try:
        data = json.loads(raw)
    except Exception as e:
        die(f'invalid JSON: {e}')

    title = str(data.get('title', '')).strip()
    desc = str(data.get('desc', '')).strip()
    items = data.get('items')
    if not title or not desc:
        die('missing title/desc')
    if not isinstance(items, list) or not (1 <= len(items) <= 25):
        die('items must be a list of 1-25 entries')

    for i, it in enumerate(items):
        if not isinstance(it, dict):
            die(f'item {i} is not an object')
        if it.get('cat') not in CATS:
            die(f"item {i} bad cat: {it.get('cat')!r} (allowed: {'/'.join(CATS)})")
        for k in ('badge', 'url', 'main'):
            if not str(it.get(k, '')).strip():
                die(f'item {i} missing {k}')
        if not str(it['url']).startswith(('http://', 'https://')):
            die(f'item {i} bad url')

    # ---- 生成 CONTENT（类别固定顺序，空类别跳过）----
    parts = []
    for cat in CATS:
        its = [it for it in items if it['cat'] == cat]
        if not its:
            continue
        parts.append(f'<div class="group">{cat} · {len(its)}条</div>')
        for it in its:
            inner = esc(it['main'])
            if str(it.get('sub', '')).strip():
                inner = (f'<span class="t-main">{esc(it["main"])}</span>'
                         f'<span class="t-sub">{esc(it["sub"])}</span>')
            parts.append(
                f'<div class="card"><span class="badge">{esc(it["badge"])}</span>'
                f'<a href="{esc(it["url"])}" target="_blank" rel="noopener">{inner}</a></div>')
    content = '\n'.join(parts)

    tmpl = (REPO / 'template.html').read_text(encoding='utf-8')
    page = (tmpl.replace('{{TITLE}}', esc(title))
                .replace('{{DESC}}', esc(desc))
                .replace('{{CONTENT}}', content))

    now = datetime.datetime.now(TZ)
    slug = now.strftime('%Y-%m-%d-%H%M')
    out = REPO / f'{slug}.html'
    out.write_text(page, encoding='utf-8')
    (REPO / 'index.html').write_text(page, encoding='utf-8')
    print(f'SLUG={slug}')
    print(f'URL={BASE}/{slug}.html')

    # ---- 清理 7 天前的旧期刊（按文件名日期；保留 index/cover/template 等）----
    cutoff = now.date() - datetime.timedelta(days=7)
    removed = 0
    for f in REPO.glob('*.html'):
        m = re.fullmatch(r'(\d{4}-\d{2}-\d{2})-\d{4}', f.stem)
        if m:
            try:
                if datetime.date.fromisoformat(m.group(1)) < cutoff:
                    f.unlink()
                    removed += 1
            except ValueError:
                pass
    print(f'CARDS={len(items)} REMOVED={removed}')

    if SKIP_PUSH:
        print('PUSH=skipped (RD_SKIP_PUSH)')
        return

    # ---- git commit + push（被拒自动 rebase 重推一次）----
    env = dict(os.environ, GIT_ASKPASS='/root/.gh-askpass.sh')

    def run(*a):
        return subprocess.run(list(a), cwd=REPO, env=env,
                              capture_output=True, text=True, timeout=120)

    run('git', 'add', '-A')
    run('git', 'commit', '-m', f'digest {slug}')
    push = run('git', 'push', 'origin', 'main')
    if push.returncode != 0 and ('rejected' in push.stderr or 'fetch first' in push.stderr.lower()):
        pull = run('git', 'pull', '--rebase', 'origin', 'main')
        if pull.returncode == 0:
            push = run('git', 'push', 'origin', 'main')
    if push.returncode != 0:
        print('PUSH=failed')
        print((push.stderr or push.stdout or '').strip()[-400:])
        sys.exit(2)
    print('PUSH=ok')

    # ---- 轮询发布状态（最多 ~90s，保证整体 <120s 可同步返回），然后无条件写回标记 ----
    url = f'{BASE}/{slug}.html'
    code = '000'
    for _ in range(6):
        try:
            c = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                 '-m', '8', '--retry', '1', url],
                capture_output=True, text=True, timeout=20)
            code = c.stdout.strip()
        except Exception:
            code = '000'
        if code == '200':
            break
        time.sleep(8)
    print(f'FINAL={code}')

    MARKER.write_text(datetime.datetime.now(TZ).strftime('%Y-%m-%d %H:%M') + '\n')
    print('MARKER=written')


if __name__ == '__main__':
    main()
