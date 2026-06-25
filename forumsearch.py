#!/usr/bin/env python3
"""community.n8n.io forum search — core logic + CLI.

Searches the n8n community forum (Discourse). Solved threads (accepted
answers) are vetted documentation, so this is a first-class verification
source alongside the n8n Docs MCP. Read-only, anonymous (public search).

Two things make Discourse search actually useful as an agent verifier:
  1. Adaptive recall. Discourse ANDs every term, so a full-sentence query
     ("OpenAI node messages must be a non-empty array got null despite ...")
     matches almost nothing (1 result), while the same intent as a few key
     terms ("messages non-empty array") finds the solved threads. search()
     runs the exact query first for precision, then progressively broadens to
     the most distinctive 4 -> 3 -> 2 terms ONLY if results are thin, merging
     solved threads to the top.
  2. Answers, not questions. A solved thread's value is its accepted answer,
     not the asker's question. search(..., with_answers=True) attaches a
     snippet of the accepted answer to each solved hit, so the vetted fix
     shows up in the search itself (no second round-trip).

Shared by forum_mcp.py (the MCP server). CLI usage:
  python3 forumsearch.py search "messages non-empty array"     # all results
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

# Words too common to discriminate on the n8n forum — dropped when distilling a
# long query down to its distinctive terms for the recall-broadening passes.
_STOP = set((
    "a an the is are was were be been being am to of in on at for with and or "
    "but not no my your you i it its this that these those as by from up down "
    "about into over after before when what how why where which who whom whose "
    "can cant could would should do does did doesnt dont didnt im ive id got "
    "getting get still even very really just only also any some please trying "
    "need want using use despite having has have had may might must will shall "
    "them they then than there here out off via per if so we our us me he she "
    "while been being able way around again new like able").split())
_GENERIC = set((
    "n8n node nodes error errors issue issues problem problems question questions "
    "workflow workflows help fails failing failed work working broken").split())


def _clean(html):
    return re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', html or '')).strip()


def _terms(query):
    """Distinctive terms from a query, order-preserved, deduped."""
    out, seen = [], set()
    for t in re.findall(r"[a-z0-9_.+-]+", query.lower()):
        if len(t) > 2 and t not in _STOP and t not in _GENERIC and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _raw(query, solved_only):
    q = query + (' status:solved' if solved_only else '')
    try:
        r = requests.get(f"{F}/search.json", params={'q': q},
                         headers=UA, timeout=25).json()
    except Exception as e:
        return None, {'error': str(e)}
    cats = {c['id']: c.get('name', '') for c in r.get('categories', [])}
    blurbs = {}
    for p in r.get('posts', []):
        blurbs.setdefault(p.get('topic_id'), _clean(p.get('blurb', '')))
    rows = []
    for t in r.get('topics', []):
        tid = t['id']
        rows.append({
            'topic_id': tid,
            'title': t.get('title', ''),
            'url': f"{F}/t/{t.get('slug', '')}/{tid}",
            'solved': bool(t.get('has_accepted_answer')),
            'category': cats.get(t.get('category_id'), ''),
            'blurb': blurbs.get(tid, ''),
        })
    return rows, None


def _accepted_answer(topic_id, chars=320):
    """First accepted-answer snippet for a solved thread, or ''."""
    try:
        d = requests.get(f"{F}/t/{topic_id}.json", headers=UA, timeout=20).json()
    except Exception:
        return ''
    pns = {a.get('post_number') for a in (d.get('accepted_answers') or [])}
    for p in d.get('post_stream', {}).get('posts', []):
        if p.get('post_number') in pns:
            return _clean(p.get('cooked', ''))[:chars]
    return ''


def search(query, solved_only=False, max_results=8, with_answers=True):
    """Search the forum with adaptive recall broadening.

    Runs the exact query first, then broadens to the most distinctive 4/3/2
    terms only while results stay thin, merging (dedup by topic_id, solved
    threads first). When with_answers, attaches the accepted-answer snippet to
    each solved hit. Returns a list of dicts (topic_id, title, url, solved,
    category, blurb, [answer]) or a single {'error': ...}."""
    rows, err = _raw(query, solved_only)
    if err:
        return [err]
    by_id = {r['topic_id']: r for r in rows}
    terms = _terms(query)
    # broaden only if the precise query came back thin
    if len(by_id) < max_results and len(terms) > 2:
        for k in (4, 3, 2):
            if len(terms) <= k:
                continue
            more, e2 = _raw(' '.join(terms[:k]), solved_only)
            for r in (more or []):
                by_id.setdefault(r['topic_id'], r)
            if len(by_id) >= max_results:
                break
    # solved first, otherwise preserve discovery order
    ordered = sorted(by_id.values(), key=lambda r: (not r['solved'],))
    out = ordered[:max_results]
    if with_answers:
        n = 0
        for r in out:
            if r['solved'] and n < 4:
                r['answer'] = _accepted_answer(r['topic_id'])
                n += 1
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
        block = (f"[{mark}] {r['topic_id']} | {r['title']} "
                 f"({r['category']})\n   {r['url']}\n   {r['blurb'][:200]}")
        if r.get('answer'):
            block += f"\n   ANSWER: {r['answer']}"
        lines.append(block)
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
