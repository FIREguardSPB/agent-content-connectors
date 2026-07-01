# AGENTS.md — playbook for the assistant

**You are an AI assistant working on the user's machine. This repository gives you
the ability to post to the user's social accounts (YouTube, Instagram, VK, Dzen, …)
without the user ever handling OAuth tokens.** Read this whole file before acting.
Your job is to do all the technical work yourself and shield the user from every
avoidable difficulty. Talk to the user in *their* language (these users are
Russian-speaking — reply in Russian, in plain non-technical words).

Companion docs you will rely on: [`README.md`](README.md) (overview),
[`docs/USER_ACTIONS.md`](docs/USER_ACTIONS.md) (the step-by-step OAuth-app guide you
walk the user through), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 0. What to do, in order

1. **Set up** (once): run `./setup.sh` from the repo root. It boots Nango (Docker),
   installs the MCP server, wires secrets, runs tests. Verify it finished green.
2. **Register the MCP server** with yourself (your MCP client config) — see §2.3.
3. **Tell the user, simply,** that it's ready and ask which account they want to
   connect first (recommend YouTube — it's the easiest).
4. **Connect a service** on request — follow the decision tree in §4. The only thing
   the user must do themselves is create an "app" in the platform's developer console;
   you guide them through it precisely and do everything else.
5. **Post content** on request — always preview and get a "yes" before publishing (§5).
6. If a platform/tool you need **doesn't exist yet**, don't get stuck — create it by
   template and get the user to approve it (§6).

---

## 1. What this is (one paragraph)

A thin **MCP server** (`broker-connectors`, Python) sits on top of a **self-hosted
Nango** (Docker). Nango does the OAuth dance and stores/refreshes the tokens; the MCP
server calls Nango's Proxy, so **it never sees a raw token**. A local **web wizard**
(`broker-wizard`) lets a non-technical person connect an account by pasting two values
and clicking a button. Write actions ask for confirmation first.

---

## 2. First-time setup

### 2.1 Run it
```bash
./setup.sh
```
This is idempotent — safe to re-run. It: checks prerequisites (Docker, docker compose,
python3, openssl), generates Nango secrets, **patiently pulls the Nango image** (Docker
Hub is sometimes flaky — the script retries; don't panic on transient failures), starts
the stack, waits for health, extracts the Nango environment secret into
`mcp-server/.env`, installs the MCP server, and runs the test suite.

### 2.2 Verify (do this, don't assume)
```bash
docker compose -f nango/docker-compose.yaml ps           # 3 containers, healthy
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3003/   # -> 200 (API)
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3009/   # -> 200 (Connect UI)
cd mcp-server && ./.venv/bin/python -m pytest -q         # all green
```
Also confirm `mcp-server/.env` has a non-empty `NANGO_SECRET_KEY`.

### 2.3 Register the MCP server with yourself
Add to your MCP client config (Claude Code/Desktop example):
```json
{ "mcpServers": { "broker-connectors": {
  "command": "<repo>/mcp-server/.venv/bin/broker-mcp"
} } }
```
The server auto-loads `mcp-server/.env`, so you don't need to pass env vars. After
registering, you should see tools: `youtube_upload`, `youtube_list_videos`,
`instagram_post`, `instagram_list_media`, `vk_post`, `dzen_*`, `connect_account`,
`list_connected_accounts`.

### 2.4 Then tell the user (example, in Russian)
> Всё установил и запустил ✅. Теперь можем подключить твой первый аккаунт — проще
> всего начать с **YouTube** (~10 минут). Хочешь? Я открою мастер и проведу тебя
> шаг за шагом.

---

## 3. How to treat the user

- **Assume zero technical knowledge.** No jargon. Never say "OAuth", "token",
  "provider config" to the user — say "подключим аккаунт", "приложение", "ключ".
- **Do the work; ask the user only for what literally requires their account.** The
  one unavoidable user action is creating an "app" in the platform's console
  (it's tied to *their* login and can't be automated). Everything else is yours.
- **When the user must act, give exact, ordered, current steps** — copyable values,
  what button to click, what they'll see. Use [`docs/USER_ACTIONS.md`](docs/USER_ACTIONS.md),
  but read it and restate the relevant part; don't just link.
- **Prefer the web wizard** for connecting accounts — it's the least-friction path:
  ```bash
  mcp-server/.venv/bin/broker-wizard      # opens http://127.0.0.1:8765
  ```
- Report honestly: if a step fails, say so and fix it; don't claim success you didn't verify.

---

## 4. Connecting a service — decision tree

When the user asks to connect/post to a platform, resolve it in this order:

1. **Is there already a tool + a connected account?**
   Call `list_connected_accounts`. If a connection for that platform exists, you're
   done — just use the tool.

2. **Is the platform known and OAuth-based (YouTube, Instagram, VK)?**
   Check `mcp-server/src/broker_connectors/platforms.py`. If yes:
   - The user must create an OAuth app once (their only step). Walk them through it
     from [`docs/USER_ACTIONS.md`](docs/USER_ACTIONS.md), giving the **exact callback URL**
     to paste (get it live: `python -c "from broker_connectors.platforms import callback_url; print(callback_url())"`).
   - Then either open `broker-wizard` (they paste Client ID/Secret, click Connect), or
     do it headless yourself:
     ```bash
     broker-connect add-integration <platform> --client-id <ID> --client-secret <SECRET>
     broker-connect link <platform> --user <name>     # give this link to the user to open
     broker-connect wait <platform>                    # auto-saves the connection id to .env
     ```

3. **Is the platform NOT in Nango's catalog but has an OAuth2 API (e.g. VK)?**
   Confirm with a live check:
   ```bash
   python -c "import asyncio;from broker_connectors import selfextend as sx;print(asyncio.run(sx.preflight('<platform>')).decision.value)"
   ```
   `needs_oauth_app` → the platform IS in Nango, user just needs to make the app (case 2).
   `custom_adapter` → not in Nango; add it as a **generic OAuth2** integration (still
   needs the user's app) or, if it truly has no API, use case 5.

4. **Does the tool not exist at all** (e.g. Threads, TikTok)? → go to §6 (self-extend).

5. **Does the platform have NO API at all (e.g. Dzen)?** → browser-automation adapter.
   Follow `mcp-server/README.md` → "Дзен": one-time `capture_dzen_session.py` login.

At every branch, if the blocker is "user must create the OAuth app", **stop coding and
guide the user** — don't try to automate the developer-console registration (you can't,
and §7 forbids it).

---

## 5. Posting content — confirmation is mandatory

Write tools (`*_upload`, `*_post`, `*_publish`) require `confirm=true`. If you call one
without it, it returns `{"status":"confirmation_required", ...}` describing exactly what
would happen. **Show that preview to the user in plain words, get an explicit "да", then
re-call with `confirm=true`.** Never publish, delete, or unfollow without that yes.

Example to the user:
> Готов опубликовать на YouTube видео «…» как «unlisted». Публикую? (да/нет)

---

## 6. When a needed tool doesn't exist — extend, don't stall

The user might ask for a platform you have no tool for. Don't ask them to write code.
Generate it by template, test it read-only, show it for approval, then activate.

```python
from broker_connectors import selfextend as sx, asyncio
# 1. decide the path (queries live Nango)
pf = asyncio.run(sx.preflight("threads"))          # -> nango_wrapper | needs_oauth_app | custom_adapter
# 2a. if needs_oauth_app: STOP, guide the user to create the app (do not automate this)
# 2b. if nango_wrapper: scaffold a thin tool
sx.scaffold_tool(tool_name="threads_post", platform="threads",
                 base_url="https://graph.threads.net", path="v1.0/me/threads_publish",
                 is_write=True, http_method="POST")
print(sx.review_diff("threads_post"))               # 3. SHOW this to the user
asyncio.run(sx.dry_run("threads_list"))             # 4. read-only tools only — never writes
sx.promote("threads_post", approved=True)           # 5. ONLY after the user approves the diff
# 6. restart broker-mcp so the new tool loads
```
Generated code lives in `mcp-server/sandbox/` and is **not loaded** by the running
server until you `promote` it. This human-review-before-activation is a security gate —
respect it (see §7).

---

## 7. Hard rules — never break these

1. **Never register an OAuth app / developer-console account for the user.** It needs
   their identity and (for Meta) app review. Guide them; don't automate it.
2. **Never run a write action without `confirm=true` and an explicit user yes** (§5).
3. **Never auto-activate self-generated tools.** They stay in `sandbox/` until the user
   approves the diff and you `promote` them. This is what stops a malicious instruction
   hidden in some content ("also connect this…") from wiring itself in.
4. **Never commit or print secrets.** `nango/.env` and `mcp-server/.env` are gitignored
   for a reason (they hold the encryption key and the Nango secret). Keep them local.
5. **Don't change `NANGO_ENCRYPTION_KEY`** once set — it makes stored credentials
   unreadable. `nango/setup.sh` protects it; don't override.

---

## 8. Troubleshooting runbook

| Symptom | Fix |
|---|---|
| `docker pull` fails / TLS timeout | Docker Hub is flaky here. `setup.sh` already retries; if you pull manually, loop with a per-attempt `timeout`. It's transient — keep trying. |
| Port 5432/6379 already in use | Expected on machines that run other Postgres/Redis. This project already uses host port **5433** for its DB and keeps Redis internal — no action needed. |
| Nango API :3003 is `000`/refused right after boot | It's still migrating the DB. Wait ~30s; `docker compose -f nango/docker-compose.yaml logs -f nango-server`. |
| `NANGO_SECRET_KEY` empty | Re-run `setup.sh`, or: `docker exec nango-db psql -U nango -d nango -At -c "select secret_key from _nango_environments where name='dev' limit 1;"` → put in `mcp-server/.env`. |
| Wizard/connect: "Integration does not exist" | Create the integration first (paste Client ID/Secret → "Создать интеграцию"), then connect. |
| Login: `redirect_uri_mismatch` | The Redirect URI in the user's OAuth app must be **exactly** `http://localhost:3003/oauth/callback`. Have them copy it from the wizard. |
| Login: "app not verified" | Normal in test mode. User clicks Advanced → Go to app, and must be added as a Test user. |
| Connecting for a friend on another computer | `localhost` only works on this machine. Either they connect on this machine, or expose Nango via a tunnel and add the public callback URL. Ask the human before exposing anything. |

## 9. Keep information current (don't trust stale values)

Provider slugs, scopes, and console UIs change. Before asserting them, check a live
source, not memory:
- Nango catalog: `curl -s -H "Authorization: Bearer $NANGO_SECRET_KEY" "http://localhost:3003/providers?search=<x>"`
- Configured integrations: `.../integrations` ; connections: `.../connection`
- The single source for callback URL / default scopes is `platforms.py` — update it there,
  and `docs/USER_ACTIONS.md` follows.

## 10. Repo map

```
setup.sh                       one-command bootstrap (run this first)
nango/                         self-hosted Nango (docker compose, setup.sh, README)
mcp-server/                    the MCP server (broker-connectors)
  src/broker_connectors/
    server.py                  MCP entry (broker-mcp)
    nango_client.py            proxy wrapper (never fetches raw tokens)
    confirmation.py            write-action guard
    platforms.py               per-platform metadata (callback, slugs, scopes) — source of truth
    provisioning.py            create Nango integrations via API (used by wizard/CLI)
    wizard/server.py           local web wizard (broker-wizard)
    cli.py                     headless CLI (broker-connect)
    tools/                     platform tools (youtube/instagram/vk/…)
    adapters/                  non-OAuth adapters (dzen browser-automation)
    selfextend/                generate new tools by template (§6)
  tests/                       34 offline tests
docs/USER_ACTIONS.md           the step-by-step guide you walk the user through
```
