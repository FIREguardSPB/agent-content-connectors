"""One-time Dzen login capture.

Opens a real browser, you log into Dzen by hand, then we save the browser
*session* (cookies / storage state) — NOT a token — so the Dzen adapter can act
as you later. Run once; re-run when the session expires.

    python scripts/capture_dzen_session.py

Needs the Hermes browser stack in this venv:
    uv pip install patchright && patchright install chromium
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

SESSION_PATH = Path(
    os.environ.get("DZEN_SESSION_PATH", os.path.expanduser("~/.config/broker-connectors/dzen_session.json"))
)


def _load_playwright():
    try:
        from patchright.async_api import async_playwright  # type: ignore

        return async_playwright
    except Exception:
        from playwright.async_api import async_playwright  # type: ignore

        return async_playwright


async def main() -> None:
    async_playwright = _load_playwright()
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://dzen.ru/")
        print("\n>>> Log into Dzen in the opened window. When you see your feed/studio, "
              "come back here and press Enter.\n")
        await asyncio.get_event_loop().run_in_executor(None, input)
        await context.storage_state(path=str(SESSION_PATH))
        print(f"Saved session -> {SESSION_PATH}")
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
