"""broker-connect — headless setup/connect CLI (the web wizard `broker-wizard`
is the friendly alternative; both share the same engine).

    broker-connect wizard                         # launch the local web wizard
    broker-connect add-integration youtube --client-id X --client-secret Y
    broker-connect link youtube --user me         # print a "Login with ..." URL
    broker-connect wait youtube                    # poll until connected, save .env
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time

from .envfile import set_var
from .nango_client import NangoClient
from .platforms import PLATFORMS, callback_url
from .provisioning import find_connection, upsert_integration


async def _link(platform: str, user: str, email: str | None, name: str | None) -> int:
    meta = PLATFORMS.get(platform)
    provider = meta.provider if meta else platform
    async with NangoClient() as c:
        s = await c.create_connect_session(end_user_id=user, email=email, display_name=name,
                                           allowed_integrations=[provider or platform])
    if not s.get("connect_link"):
        print("No connect_link returned:", s, file=sys.stderr)
        return 1
    print(f"\nОткрой ссылку, войди и нажми «Разрешить»:\n\n  {s['connect_link']}\n")
    return 0


async def _add(platform: str, client_id: str, client_secret: str) -> int:
    print(f"Redirect URI для OAuth-приложения: {callback_url()}")
    res = await upsert_integration(platform, client_id, client_secret)
    if res.get("ok"):
        print(f"Интеграция {res['action']}: {res['unique_key']} (provider={res['provider']})")
        return 0
    print("Ошибка:", res.get("error"), file=sys.stderr)
    return 1


async def _wait(platform: str, timeout: int) -> int:
    meta = PLATFORMS.get(platform)
    key = meta.provider if meta else platform
    print(f"Жду подключения аккаунта {platform} (до {timeout}s)…")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        conn = await find_connection(key or platform)
        if conn and conn.get("connection_id"):
            path = set_var(f"NANGO_CONN_{platform.upper()}", conn["connection_id"])
            print(f"✅ Подключено: {conn['connection_id']} — сохранено в {path}")
            return 0
        await asyncio.sleep(3)
    print("Тайм-аут: подключение не найдено.", file=sys.stderr)
    return 1


def main() -> None:
    p = argparse.ArgumentParser(prog="broker-connect")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("wizard", help="launch the local web wizard")

    a = sub.add_parser("add-integration", help="create/update a Nango integration")
    a.add_argument("platform"); a.add_argument("--client-id", required=True)
    a.add_argument("--client-secret", required=True)

    l = sub.add_parser("link", help="mint a Connect UI link")
    l.add_argument("platform"); l.add_argument("--user", default="master")
    l.add_argument("--email", default=None); l.add_argument("--name", default=None)

    ww = sub.add_parser("wait", help="poll until connected, then save connection id")
    ww.add_argument("platform"); ww.add_argument("--timeout", type=int, default=300)

    args = p.parse_args()
    if args.cmd == "wizard":
        from .wizard.server import run
        run(); raise SystemExit(0)
    if args.cmd == "add-integration":
        raise SystemExit(asyncio.run(_add(args.platform, args.client_id, args.client_secret)))
    if args.cmd == "link":
        raise SystemExit(asyncio.run(_link(args.platform, args.user, args.email, args.name)))
    if args.cmd == "wait":
        raise SystemExit(asyncio.run(_wait(args.platform, args.timeout)))


if __name__ == "__main__":
    main()
