# CLAUDE.md

**Read [`AGENTS.md`](AGENTS.md) in full before doing anything** — it is the playbook
for operating this project (setup, connecting accounts, posting, extending, and how to
guide the user). This file just restates the essentials.

This repo lets you post to the user's social accounts (YouTube, Instagram, VK, Dzen, …)
via a self-hosted Nango + a thin MCP server. Users are non-technical and Russian-speaking
— reply in Russian, in plain words, and shield them from every avoidable difficulty.

First run: `./setup.sh` (boots Nango, installs the MCP server, runs tests). Then follow
AGENTS.md §2–§5.

Non-negotiable rules (full list in AGENTS.md §7):
- Never register an OAuth app for the user — guide them; that step needs their account.
- Never run a write action (post/delete/unfollow) without `confirm=true` **and** an explicit user "yes".
- Never auto-activate self-generated tools — they stay in `sandbox/` until the user approves the diff.
- Never commit or print secrets (`nango/.env`, `mcp-server/.env` are gitignored).
- Don't change `NANGO_ENCRYPTION_KEY` once set.

Verify live sources for changing values (provider slugs, scopes) — don't trust memory (AGENTS.md §9).
