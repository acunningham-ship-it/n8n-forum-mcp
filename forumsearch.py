#!/usr/bin/env python3
"""community.n8n.io forum search — core logic + CLI.

Searches the n8n community forum (Discourse). Solved threads (accepted
answers) are vetted documentation, so this is a first-class verification
source alongside the n8n Docs MCP. Read-only, anonymous (public search).

Shared by forum_mcp.py (the MCP server). CLI usage:
  python3 forumsearch.py search "airtable rate limit"          # all results
  python3 forumsearch.py solved "airtable rate limit"          # solved only
  python3 forumsearch.py thread 300911                         # read a thread
"""
import sys
import re
import requests

F = "https://community.n8n.io"
UA = {'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                     'Chrome/131.0.0.0 Safari/537.36')}


def _clean(html):
    return re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', html or '')).strip()


def search(query, solved_only=False, max_results=8):
    """Search the forum. Returns a list of dicts (topic_id, title, url,
    solved, category, blurb)."""
    q = query + (' status:solved' if solved_only else '')
    try:
        r = requests.get(f"{F}/search.json", params={'q': q},
                         headers=UA, timeout=25).json()
    except Exception as e:
        return [{'error': str(e)}]
    topics = {t['id']: t for t in r.get('topics', [])}
    cats = {c['id']: c.get('name', '') for c in r.get('categories', [])}
    # map topic -> first matching post blurb
    blurbs = {}
    for p in r.get('posts', []):
        blurbs.setdefault(p.get('topic_id'), _clean(p.get('blurb', '')))
    out = []
    for tid, t in topics.items():
        out.append({
            'topic_id': tid,
            'title': t.get('title', ''),
            'url': f"{F}/t/{t.get('slug', '')}/{tid}",
            'solved': bool(t.get('has_accepted_answer')),
            'category': cats.get(t.get('category_id'), ''),
            'blurb': blurbs.get(tid, ''),
        })
        if len(out) >= max_results:
            break
    return out


def thread(topic_id, max_posts=20):
    """Read a thread. Surfaces the accepted answer + the posts."""
    try:
        d = requests.get(f"{F}/t/{topic_id}.json", headers=UA,
                         timeout=25).json()
    except Exception as e:
        return {'error': str(e)}
    posts = d.get('post_stream', {}).get('posts', [])
    accepted_pns = {a.get('post_number')
                    for a in (d.get('accepted_answers') or [])}
    accepted = None
    out_posts = []
    for p in posts[:max_posts]:
        pn = p.get('post_number')
        txt = _clean(p.get('cooked', ''))
        entry = {'post_number': pn, 'username': p.get('username', ''),
                 'accepted': pn in accepted_pns, 'text': txt}
        out_posts.append(entry)
        if pn in accepted_pns:
            accepted = entry
    return {
        'topic_id': topic_id,
        'title': d.get('title', ''),
        'url': f"{F}/t/{d.get('slug', '')}/{topic_id}",
        'solved': bool(d.get('accepted_answers')),
        'accepted_answer': accepted,
        'posts': out_posts,
    }


def _fmt_search(rows):
    lines = []
    for r in rows:
        if 'error' in r:
            return "ERROR: " + r['error']
        mark = 'SOLVED' if r['solved'] else '      '
        lines.append(f"[{mark}] {r['topic_id']} | {r['title']} "
                     f"({r['category']})\n   {r['url']}\n   {r['blurb'][:200]}")
    return '\n'.join(lines) if lines else "no results"


def _fmt_thread(t):
    if 'error' in t:
        return "ERROR: " + t['error']
    s = [f"{t['title']} {'[SOLVED]' if t['solved'] else ''}\n{t['url']}"]
    if t['accepted_answer']:
        a = t['accepted_answer']
        s.append(f"\n=== ACCEPTED ANSWER (pn{a['post_number']} "
                 f"@{a['username']}) ===\n{a['text'][:1200]}")
    s.append("\n=== POSTS ===")
    for p in t['posts']:
        tag = ' *ACCEPTED*' if p['accepted'] else ''
        s.append(f"pn{p['post_number']} @{p['username']}{tag}: "
                 f"{p['text'][:400]}")
    return '\n'.join(s)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, arg = sys.argv[1], ' '.join(sys.argv[2:])
    if cmd == 'search':
        print(_fmt_search(search(arg)))
    elif cmd == 'solved':
        print(_fmt_search(search(arg, solved_only=True)))
    elif cmd == 'thread':
        print(_fmt_thread(thread(int(arg))))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
