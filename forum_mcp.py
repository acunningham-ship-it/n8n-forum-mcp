#!/usr/bin/env python3
"""MCP server for community.n8n.io forum search.

Exposes the n8n community forum as MCP tools so it can be used as a
verification source alongside the n8n Docs MCP — solved threads (accepted
answers) are vetted community documentation. Read-only, anonymous.

Run via the dedicated venv: ~/n8n_forum_bot/mcpvenv/bin/python forum_mcp.py
Registered in Claude Code as the `n8n-forum` MCP server (stdio).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp.server.fastmcp import FastMCP  # noqa: E402
import forumsearch as fs  # noqa: E402

mcp = FastMCP("n8n-forum")


@mcp.tool()
def search_forum(query: str, solved_only: bool = False,
                 max_results: int = 8) -> str:
    """Search the community.n8n.io (n8n) forum for threads matching a query.

    Use this to find how others diagnosed/solved an n8n problem, error,
    node behavior, or feature question — the community forum often has the
    answer when the docs don't. Set solved_only=True to return ONLY threads
    with an accepted answer (vetted solutions = best for verifying a fix).

    You can pass a full error string or a whole sentence — search adaptively
    broadens to the most distinctive terms when an exact query is too narrow
    (Discourse ANDs every word, so long queries otherwise match nothing), and
    sorts solved threads first. For each solved hit it also returns a snippet
    of the ACCEPTED ANSWER inline, so the vetted fix shows up in the result
    itself. Returns solved-status, title, category, link, excerpt, and (for
    solved threads) the accepted-answer snippet.
    """
    return fs._fmt_search(fs.search(query, solved_only=solved_only,
                                    max_results=max_results))


@mcp.tool()
def get_thread(topic_id: int) -> str:
    """Read a specific n8n forum thread by topic id (from search_forum).

    Returns the accepted answer (if the thread is solved) surfaced first,
    then the posts in order. Use after search_forum to read the full vetted
    solution / the back-and-forth on a relevant thread.
    """
    return fs._fmt_thread(fs.thread(topic_id))


if __name__ == "__main__":
    mcp.run()
