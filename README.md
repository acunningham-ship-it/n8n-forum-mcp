# n8n Forum MCP

An [MCP](https://modelcontextprotocol.io) server that searches the [n8n community forum](https://community.n8n.io) so AI agents (Claude, etc.) can use it as a knowledge source — pairs nicely with the official [n8n Docs MCP](https://docs.n8n.io/~gitbook/mcp).

Solved threads on the forum (those with an accepted answer) are effectively vetted community documentation: real problems with confirmed fixes. This server makes them searchable and readable from your agent.

Read-only and anonymous — it only hits the public Discourse search/topic endpoints. No login, no credentials.

## Tools

- **`search_forum(query, solved_only=False, max_results=8)`** — search the forum. Set `solved_only=True` to return only threads with an accepted answer (vetted solutions). Returns each thread's solved-status, title, category, link, and excerpt — **plus, for solved threads, a snippet of the accepted answer inline** so the vetted fix shows up in the search itself.
- **`get_thread(topic_id)`** — read a thread by id (from `search_forum`). Surfaces the accepted answer first, then the posts.

### Adaptive recall

Discourse search ANDs every term, so pasting a whole error message or a full sentence (`"OpenAI node messages must be a non-empty array got null despite having inputs"`) tends to match **nothing** — while the same intent as a few key terms (`"messages non-empty array"`) finds the solved threads. `search_forum` handles this for you: it runs the exact query first (precision), then progressively broadens to the most distinctive 4 → 3 → 2 terms **only if results are thin** (recall), merging solved threads to the top. So you can hand it a raw error string and still get hits.

## Install

```bash
git clone https://github.com/acunningham-ship-it/n8n-forum-mcp
cd n8n-forum-mcp
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Use with Claude Code

```bash
claude mcp add n8n-forum -- /absolute/path/to/n8n-forum-mcp/.venv/bin/python /absolute/path/to/n8n-forum-mcp/forum_mcp.py
```

For Claude Desktop / other clients, add an equivalent stdio server entry pointing at `.venv/bin/python forum_mcp.py`.

## CLI (no MCP client needed)

`forumsearch.py` works standalone for quick lookups:

```bash
python3 forumsearch.py search "airtable rate limit"   # all results
python3 forumsearch.py solved "azure openai api version"  # accepted-answer threads only
python3 forumsearch.py thread 300911                  # read a thread + its accepted answer
```

## Who builds this

n8n-forum-mcp is built and maintained by **[HamTek](https://hamtek.dev)**.

We built it because the forum's own search ANDs every term, so a full-sentence question
matched almost nothing. This broadens the query when results are thin and returns the
accepted answer inline.

More of what we do at [hamtek.dev](https://hamtek.dev).

## License

MIT
