"""Local, dependency-free web wizard (stdlib http.server).

    broker-wizard            # opens http://127.0.0.1:8765 in your browser

Flow for the user (per platform):
  1. Copy the callback URL shown -> paste into their OAuth app's Redirect URI.
  2. Paste Client ID + Client Secret -> "Создать интеграцию" (we call Nango's API).
  3. "Подключить аккаунт" -> log in in the popup -> we auto-detect the connection
     and write NANGO_CONN_<PLATFORM> to mcp-server/.env. Done.
No terminal, no dashboard, no editing files.
"""
from __future__ import annotations

import asyncio
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from ..config import settings
from ..envfile import set_var
from ..nango_client import NangoClient
from ..platforms import PLATFORMS, callback_url


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _platforms_payload() -> dict:
    return {
        "callback_url": callback_url(),
        "nango_host": settings.nango_host,
        "platforms": [
            {
                "key": p.key, "label": p.label, "kind": p.kind, "provider": p.provider,
                "scopes": p.scopes, "console_label": p.console_label, "console_url": p.console_url,
                "difficulty": p.difficulty, "needs_review": p.needs_review, "notes": p.notes,
            }
            for p in PLATFORMS.values()
        ],
    }


async def _mint_link(platform: str, user: str) -> dict:
    meta = PLATFORMS.get(platform)
    provider = meta.provider if meta else platform
    async with NangoClient() as c:
        sess = await c.create_connect_session(
            end_user_id=user or "master",
            display_name=user or "Master",
            allowed_integrations=[provider or platform],
        )
    return {"connect_link": sess.get("connect_link"), "expires_at": sess.get("expires_at")}


HTML = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Подключение аккаунтов</title>
<style>
:root{--bg:#0f1220;--card:#1a1f36;--ink:#eef1ff;--mut:#9aa4d6;--acc:#5b8cff;--ok:#3ecf8e;--warn:#ffb020}
*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
.wrap{max-width:760px;margin:0 auto;padding:28px 18px 80px}
h1{font-size:24px;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 22px}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.pf{background:var(--card);border:1px solid #2a3157;border-radius:14px;padding:16px;cursor:pointer;transition:.15s}
.pf:hover{border-color:var(--acc);transform:translateY(-1px)}.pf b{font-size:18px}.pf .d{color:var(--mut);font-size:13px;margin-top:4px}
.panel{background:var(--card);border:1px solid #2a3157;border-radius:16px;padding:22px;margin-top:18px;display:none}
.step{padding:14px 0;border-top:1px solid #2a3157}.step:first-child{border-top:0}
.step h3{margin:0 0 8px;font-size:16px}.step .n{display:inline-flex;width:24px;height:24px;border-radius:50%;background:var(--acc);color:#fff;align-items:center;justify-content:center;font-size:13px;margin-right:8px}
code,.copyrow input{font-family:ui-monospace,Menlo,Consolas,monospace}
.copyrow{display:flex;gap:8px;margin:8px 0}
.copyrow input{flex:1;background:#0c0f1d;border:1px solid #2a3157;color:var(--ink);border-radius:10px;padding:10px 12px}
button{background:var(--acc);color:#fff;border:0;border-radius:10px;padding:11px 16px;font-size:15px;cursor:pointer}
button.ghost{background:#232a4d}button:disabled{opacity:.5;cursor:default}
label{display:block;color:var(--mut);font-size:13px;margin:10px 0 4px}
input.f{width:100%;background:#0c0f1d;border:1px solid #2a3157;color:var(--ink);border-radius:10px;padding:11px 12px}
.msg{margin-top:12px;padding:10px 12px;border-radius:10px;font-size:14px;display:none}
.msg.ok{background:rgba(62,207,142,.12);border:1px solid var(--ok);color:var(--ok);display:block}
.msg.err{background:rgba(255,80,80,.12);border:1px solid #ff5050;color:#ff9a9a;display:block}
.msg.info{background:rgba(91,140,255,.12);border:1px solid var(--acc);color:#bcd0ff;display:block}
a{color:var(--acc)}.back{color:var(--mut);cursor:pointer;display:inline-block;margin-bottom:8px}
.hint{color:var(--mut);font-size:13px}.big{font-weight:600}
</style></head><body><div class="wrap">
<h1>Подключение аккаунтов</h1><p class="sub">Подключи соцсеть в пару шагов. Токены и пароли остаются на твоём компьютере.</p>
<div id="home"><div class="cards" id="cards"></div></div>
<div class="panel" id="panel"></div>
</div>
<script>
let CFG=null, PF=null;
const $=s=>document.querySelector(s);
async function boot(){CFG=await (await fetch('/api/platforms')).json();renderHome()}
function renderHome(){
  $('#panel').style.display='none';$('#home').style.display='block';
  $('#cards').innerHTML=CFG.platforms.map(p=>
    `<div class="pf" onclick="open_('${p.key}')"><b>${p.label}</b><div class="d">${p.difficulty||''}</div></div>`).join('');
}
function open_(key){PF=CFG.platforms.find(p=>p.key===key);$('#home').style.display='none';
  const el=$('#panel');el.style.display='block';el.innerHTML=PF.kind==='browser'?dzen():oauth();}
function esc(s){return (s||'').replace(/</g,'&lt;')}
function oauth(){const cb=CFG.callback_url;const scopes=(PF.scopes||[]).join(' ');
 return `<span class="back" onclick="renderHome()">← назад</span>
 <h2>${PF.label}</h2><p class="hint">${esc(PF.notes)}</p>
 <div class="step"><h3><span class="n">1</span>Открой консоль разработчика</h3>
   <p>Создай OAuth-приложение здесь: <a href="${PF.console_url}" target="_blank">${PF.console_label} →</a><br>
   <span class="hint">Подробная пошаговая инструкция — в файле <code>docs/USER_ACTIONS.md</code>.</span></p></div>
 <div class="step"><h3><span class="n">2</span>Вставь этот адрес в поле «Redirect URI»</h3>
   <p class="hint">Скопируй один-в-один — любая опечатка ломает вход (ошибка redirect_uri_mismatch).</p>
   <div class="copyrow"><input id="cb" readonly value="${cb}"><button class="ghost" onclick="cp('cb')">Копировать</button></div>
   ${scopes?`<label>Права (scopes) — уже подставлены, копировать при необходимости:</label>
   <div class="copyrow"><input id="sc" readonly value="${esc(scopes)}"><button class="ghost" onclick="cp('sc')">Копировать</button></div>`:''}</div>
 <div class="step"><h3><span class="n">3</span>Вставь Client ID и Client Secret из приложения</h3>
   <label>Client ID</label><input class="f" id="cid" placeholder="напр. 12345-abc.apps.googleusercontent.com">
   <label>Client Secret</label><input class="f" id="sec" type="password" placeholder="секрет приложения">
   <div style="margin-top:12px"><button onclick="mkInteg()">Создать интеграцию</button></div>
   <div class="msg" id="m3"></div></div>
 <div class="step" id="s4" style="opacity:.5;pointer-events:none"><h3><span class="n">4</span>Подключи аккаунт</h3>
   <p class="hint">Откроется окно входа. Войди и нажми «Разрешить». Мы сами всё сохраним.</p>
   <button onclick="connect()">Подключить аккаунт ${PF.label}</button>
   <div class="msg" id="m4"></div></div>`;}
function dzen(){return `<span class="back" onclick="renderHome()">← назад</span>
 <h2>${PF.label}</h2><p class="hint">${esc(PF.notes)}</p>
 <div class="step"><h3>Особый способ (без токенов)</h3>
 <p>У Дзена нет API. Один раз войди в браузере — сохранится сессия. В терминале:</p>
 <div class="copyrow"><input readonly value="python scripts/capture_dzen_session.py"><button class="ghost" onclick="this.previousElementSibling.select();document.execCommand('copy')">Копировать</button></div>
 <p class="hint">Подробности — в <code>mcp-server/README.md</code>, раздел «Дзен».</p></div>`;}
function cp(id){const e=document.getElementById(id);e.select();document.execCommand('copy');}
function show(id,cls,txt){const m=document.getElementById(id);m.className='msg '+cls;m.textContent=txt;}
async function mkInteg(){const cid=$('#cid').value.trim(),sec=$('#sec').value.trim();
 if(!cid||!sec){show('m3','err','Заполни оба поля.');return;}
 show('m3','info','Создаю интеграцию в Nango…');
 const r=await (await fetch('/api/integration',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({platform:PF.key,client_id:cid,client_secret:sec})})).json();
 if(r.ok){show('m3','ok','Готово — интеграция '+r.action+'. Переходи к шагу 4.');
   const s=$('#s4');s.style.opacity=1;s.style.pointerEvents='auto';}
 else{show('m3','err','Не вышло: '+JSON.stringify(r.error||r));}}
let poll=null;
async function connect(){show('m4','info','Открываю окно входа…');
 const r=await (await fetch('/api/connect-link',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({platform:PF.key})})).json();
 if(!r.connect_link){show('m4','err','Не удалось создать ссылку: '+JSON.stringify(r));return;}
 window.open(r.connect_link,'_blank');
 show('m4','info','Окно входа открыто. Войди и нажми «Разрешить» — жду подключения…');
 clearInterval(poll);poll=setInterval(checkStatus,3000);}
async function checkStatus(){const r=await (await fetch('/api/status?platform='+PF.key)).json();
 if(r.connected){clearInterval(poll);show('m4','ok','✅ Аккаунт подключён и сохранён (connection: '+r.connection_id+'). Всё готово!');}}
boot();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, HTML.encode(), "text/html; charset=utf-8")
        if u.path == "/api/platforms":
            return self._json(200, _platforms_payload())
        if u.path == "/api/status":
            platform = (parse_qs(u.query).get("platform") or [""])[0]
            from ..provisioning import find_connection

            meta = PLATFORMS.get(platform)
            key = meta.provider if meta else platform
            try:
                conn = _run(find_connection(key or platform))
            except Exception as e:
                return self._json(200, {"connected": False, "error": str(e)})
            if conn and conn.get("connection_id"):
                set_var(f"NANGO_CONN_{platform.upper()}", conn["connection_id"])
                return self._json(200, {"connected": True, "connection_id": conn["connection_id"]})
            return self._json(200, {"connected": False})
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        u = urlparse(self.path)
        try:
            data = self._body()
        except Exception:
            return self._json(400, {"ok": False, "error": "bad json"})
        if u.path == "/api/integration":
            from ..provisioning import upsert_integration

            try:
                res = _run(upsert_integration(
                    data["platform"], data["client_id"], data["client_secret"],
                    scopes=data.get("scopes"), provider=data.get("provider"),
                ))
            except Exception as e:
                return self._json(200, {"ok": False, "error": str(e)})
            return self._json(200, res)
        if u.path == "/api/connect-link":
            try:
                res = _run(_mint_link(data.get("platform", ""), data.get("user", "master")))
            except Exception as e:
                return self._json(200, {"error": str(e)})
            return self._json(200, res)
        return self._json(404, {"error": "not found"})


def run(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    # fail fast if not configured
    try:
        settings.require_secret()
    except RuntimeError as e:
        print(f"[!] {e}")
        return
    srv = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print(f"\n  Мастер подключения открыт:  {url}\n  (Ctrl+C чтобы закрыть)\n")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Закрыто.")
        srv.shutdown()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
