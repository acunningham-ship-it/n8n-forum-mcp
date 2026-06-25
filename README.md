# n8n Forum MCP

An [MCP](https://modelcontextprotocol.io) server that searches the [n8n community forum](https://community.n8n.io) so AI agents (Claude, etc.) can use it as a knowledge source — pairs nicely with the official [n8n Docs MCP](https://docs.n8n.io/~gitbook/mcp).

Solved threads on the forum (those with an accepted answer) are effectively vetted community documentation: real problems with confirmed fixes. This server makes them searchable and readable from your agent.

Read-only and anonymous — it only hits the public Discourse search/topic endpoints. No login, no credentials.

## Tools

- **`search_forum(query, solved_only=False, max_results=8)`** — search the forum. Set `solved_only=True` to return only threads with an accepted answer (vetted solutions). Returns each thread's solved-status, title, category, link, and excerpt.
- **`get_thread(topic_id)`** — read a thread by id (from `search_forum`). Surfaces the accepted answer first, then the posts.

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

## License

MIT
