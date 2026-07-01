# broker-connectors (MCP server)

Тонкая MCP-обёртка над self-hosted Nango. Инструменты по платформам дёргают Nango
Proxy; сырой OAuth-токен в этот слой не попадает.

## Установка и тесты
```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m pytest -q          # 27 офлайн-тестов (моки Nango)
```

## Конфигурация
Скопируй `.env.example` → `.env`, впиши `NANGO_SECRET_KEY` (из дашборда Nango,
Environment Settings — см. `../nango/README.md`). Остальное — дефолты.

## Запуск MCP-сервера
```bash
broker-mcp          # stdio-транспорт (для Claude Desktop/Code)
```

### Подключение к агенту-оркестратору
Claude Desktop / Claude Code — в конфиг MCP-серверов:
```json
{
  "mcpServers": {
    "broker-connectors": {
      "command": "/home/master/Projects/АГЕНТСКИЙ_БРОКЕР/mcp-server/.venv/bin/broker-mcp",
      "env": {
        "NANGO_HOST": "http://localhost:3003",
        "NANGO_SECRET_KEY": "<секрет окружения Nango>",
        "NANGO_CONN_YOUTUBE": "<connection id>"
      }
    }
  }
}
```

## Инструменты
| Инструмент | Тип | Платформа |
|---|---|---|
| `connect_account(platform, end_user_id, …)` | read | — мятит ссылку «Войти через …» |
| `list_connected_accounts(connection_id?)` | read | — метаданные соединений |
| `youtube_list_videos(max_results?, connection_id?)` | read | YouTube |
| `youtube_upload(file_path, title, …, confirm)` | **write** | YouTube |
| `instagram_list_media(ig_user_id, …)` | read | Instagram |
| `instagram_post(ig_user_id, image_url, caption?, confirm)` | **write** | Instagram |
| `vk_post(message, owner_id?, …, confirm)` | **write** | VK |
| `dzen_list_articles()` | read | Дзен (browser) |
| `dzen_publish_article(title, body, confirm)` | **write** | Дзен (browser) |

Любой **write** без `confirm=true` возвращает превью действия — агент показывает
его тебе, ты подтверждаешь, повтор с `confirm=true` реально выполняет.

## Подключить аккаунт

**Проще всего — веб-мастер** (без терминала/конфигов/дашборда):
```bash
broker-wizard          # откроет http://127.0.0.1:8765
```
Выбираешь платформу → вставляешь Client ID/Secret из OAuth-приложения → «Создать
интеграцию» → «Подключить» → входишь в попапе. Мастер сам создаёт интеграцию в
Nango через API, ловит подключение и пишет `NANGO_CONN_*` в `.env`. Пошаговый гайд
по созданию OAuth-приложения (актуальный UI Google/Meta/VK) — [`../docs/USER_ACTIONS.md`](../docs/USER_ACTIONS.md).

**Или headless-CLI** (то же самое из терминала):
```bash
broker-connect add-integration youtube --client-id X --client-secret Y  # печатает нужный Redirect URI
broker-connect link youtube --user me     # ссылка "Войти через ..."
broker-connect wait youtube               # ждёт вход и сохраняет connection id в .env
```

## Само-расширение (агент сам пишет недостающий инструмент, §7)
```python
from broker_connectors import selfextend as sx
import asyncio

asyncio.run(sx.preflight("threads"))          # решает: обёртка / нужен OAuth-app / адаптер
sx.scaffold_tool(tool_name="threads_post", platform="threads",
                 base_url="https://graph.threads.net",
                 path="v1.0/me/threads_publish", is_write=True, http_method="POST")
print(sx.review_diff("threads_post"))          # покажи человеку
asyncio.run(sx.dry_run("threads_list"))        # ТОЛЬКО read-инструменты
sx.promote("threads_post", approved=True)      # только после одобрения → в tools/, грузится при рестарте
```
Сгенерированный код лежит в `sandbox/` и прод-сервером **не грузится** до `promote`.

## Дзен (browser-automation, вне Nango)
У Дзена нет API управления статьями — адаптер водит реальный залогиненный
браузер (стек Hermes: patchright/playwright). Разово:
```bash
uv pip install patchright && patchright install chromium
python scripts/capture_dzen_session.py        # ручной логин → сохраняет сессию (cookies, не токен)
```
Без стека и без сохранённой сессии `dzen_*` честно вернут `adapter_unavailable`
с инструкцией, а не сделают вид, что запостили.

## Инвариант безопасности
`NangoClient` не имеет метода за credentials — токен физически не достаётся в этот
слой. Подтверждается тестом `test_client_has_no_credentials_fetch_method`.
