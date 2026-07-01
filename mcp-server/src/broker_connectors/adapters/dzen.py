"""Yandex Dzen adapter — browser-automation, because Dzen has no public article API (§3).

Dzen exposes no OAuth/API for managing articles, so this adapter drives a real
logged-in browser session using the existing Hermes automation stack
(patchright / browser-use). Credentials here are a saved *session* (cookies /
storage state) captured once at a manual login — not an OAuth token — so this
path lives entirely outside the Nango contour.

This is a working skeleton: it wires the contract, the confirmation-guard, and
the session-state handoff, and fails LOUDLY and clearly if the browser stack or
a saved session isn't present, rather than pretending to post.
"""
from __future__ import annotations

import os
from typing import Any

from .base import AdapterUnavailable, PlatformAdapter

# Where the one-time-captured Dzen session (storage state) lives. Capture it with
# scripts/capture_dzen_session.py (documented in README), never checked in.
DZEN_SESSION_PATH = os.environ.get(
    "DZEN_SESSION_PATH", os.path.expanduser("~/.config/broker-connectors/dzen_session.json")
)
DZEN_STUDIO_URL = "https://dzen.ru/profile/editor"


def _load_browser_stack():
    """Import the Hermes browser-automation stack lazily.

    patchright is a stealth Playwright fork; we prefer it, then fall back to
    playwright. Raises AdapterUnavailable with actionable guidance if neither is
    installed — this machine does not currently ship the stack.
    """
    try:
        from patchright.async_api import async_playwright  # type: ignore

        return async_playwright
    except Exception:
        try:
            from playwright.async_api import async_playwright  # type: ignore

            return async_playwright
        except Exception as exc:  # pragma: no cover - environment dependent
            raise AdapterUnavailable(
                "Dzen adapter needs the Hermes browser stack (patchright or playwright). "
                "Install it in this venv (`uv pip install patchright && patchright install chromium`) "
                "and capture a Dzen session first."
            ) from exc


class DzenAdapter(PlatformAdapter):
    platform = "dzen"
    write_actions = {"publish_article"}

    def actions(self) -> list[str]:
        return ["list_articles", "publish_article"]

    def _ensure_session(self) -> str:
        if not os.path.isfile(DZEN_SESSION_PATH):
            raise AdapterUnavailable(
                f"No saved Dzen session at {DZEN_SESSION_PATH}. Run the one-time login capture "
                "(scripts/capture_dzen_session.py) — you log in by hand once, we store the browser "
                "session (cookies), not a token."
            )
        return DZEN_SESSION_PATH

    async def _do(self, action: str, params: dict[str, Any]) -> Any:
        session_path = self._ensure_session()
        async_playwright = _load_browser_stack()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=session_path)
            page = await context.new_page()
            try:
                if action == "list_articles":
                    await page.goto(DZEN_STUDIO_URL, wait_until="networkidle")
                    # Selectors intentionally left to the operator to confirm against the
                    # live studio DOM, which Yandex changes often. Return what we can see.
                    titles = await page.eval_on_selector_all(
                        "[class*='article'] [class*='title'], article h2",
                        "els => els.map(e => e.textContent.trim()).filter(Boolean)",
                    )
                    return {"status": "ok", "platform": "dzen", "articles": titles}

                if action == "publish_article":
                    # Real publishing drives the editor UI. Kept explicit and guarded:
                    # confirmation already happened in execute(); this is the real action.
                    title = params.get("title", "")
                    body = params.get("body", "")
                    if not title or not body:
                        return {"status": "error", "message": "title and body are required"}
                    await page.goto(DZEN_STUDIO_URL, wait_until="networkidle")
                    # The concrete editor automation (fill title/body, click publish) is
                    # operator-verified against the live DOM; see README 'Dzen'.
                    return {
                        "status": "needs_operator_selectors",
                        "message": "Browser session loaded and editor opened. Fill the editor "
                        "selectors for the current Dzen DOM to complete automated publish.",
                        "title": title,
                    }
                return {"status": "error", "message": f"unhandled action {action!r}"}
            finally:
                await context.close()
                await browser.close()
