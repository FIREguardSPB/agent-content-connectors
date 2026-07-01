# Архитектура

## Принцип: токен живёт только в Nango
MCP-слой **никогда не держит и не видит сырой OAuth-токен** (критерий §8.2). Это
не соглашение, а структурная гарантия: `NangoClient` умеет ровно три вещи —
`/proxy/*`, `/connect/sessions`, list-connections (метаданные). Метода, который
возвращает credentials, в классе нет вообще (тест `test_client_has_no_credentials_fetch_method`).
Nango подставляет токен на своей стороне внутри Proxy.

## Поток данных
```
connect:   [человек] → Connect UI(:3009) → Nango(:3003) хранит credentials
publish:   [агент] → MCP tool → NangoClient.proxy_* → Nango Proxy → API платформы
                                   (Authorization: Bearer <ENV secret key>,
                                    Provider-Config-Key, Connection-Id)
```
`ENV secret key` (`NANGO_SECRET_KEY`) — секрет окружения Nango, авторизует
использование Proxy. Это не токен платформы.

## Слои
- **`config.py`** — env → `Settings`; `PLATFORM_PROVIDER_KEYS`, `default_connection_id`.
  Добавление платформы = запись в этой мапе или env, без кода (критерий §8.3).
- **`nango_client.py`** — тонкий httpx-клиент над Nango. Единственная дверь наружу.
- **`confirmation.py`** — guard: write-инструмент без `confirm=true` возвращает
  превью «что произойдёт»; агент показывает человеку, тот подтверждает, повтор с
  `confirm=true` (критерий §8.4). Тот же паттерн, что у selectel-MCP в этой среде.
- **`tools/*`** — по инструменту на действие. Read — свободно, write — под guard.
  Каждый помечен `@tool(platform=, write=)`; метаданные ведут политику и discovery.
- **`registry.py`** — единственный загрузчик: импортит только `tools.*`. Sandbox
  не виден (гарантия §7.2).
- **`adapters/*`** — `PlatformAdapter.execute(action, params)` для не-OAuth
  платформ (Дзен через browser-automation), вне Nango. Тот же guard на write.
- **`selfextend/*`** — генерация недостающего инструмента.
- **`server.py`** — собирает FastMCP из реестра.

## Само-расширение (§7) — почему это безопасно
Опасность: агент читает чужой контент (комментарий, статью), где спрятана
инструкция «а ещё подключи вот это». Единственная точка, которая это блокирует —
**ревью человеком перед активацией**. Поэтому:
1. Генерация идёт в `sandbox/`, который прод-сервер не грузит.
2. `dry_run` выполняет **только read**-инструменты (write физически отказывается).
3. `promote(name, approved=True)` — только по явному одобрению — копирует файл в
   `tools/`, откуда он подхватится при следующем старте.
4. Регистрацию OAuth-приложений код не делает нигде и никак (нет пути к
   dev-консоли); preflight на этот случай возвращает `NEEDS_OAUTH_APP` и стоп.

## Решения по инфраструктуре (отклонения от upstream-compose)
- `nango-db` → host-порт **5433** (5432 занят `bot_postgres`), образ
  `postgres:16-alpine` (уже локально, без сетевого pull).
- `nango-redis` **не публикуется** на host (6379 занят `bot_redis`); сервер ходит
  по внутренней сети, `NANGO_REDIS_URL=redis://nango-redis:6379`.
- убран bind-mount `providers.yaml` (в standalone его нет — создал бы кривую папку).
- все порты на `127.0.0.1`, дашборд под basic-auth.
- SSRF-денилист Proxy оставлен по умолчанию (блокит localhost/metadata).

## Соответствие критериям готовности §8
| Критерий | Где обеспечено | Тест |
|---|---|---|
| §8.1 подключение в пару кликов без слова «токен» | Connect UI + `connect_account`/`broker-connect` (connect_link) | ручной сквозной (нужен OAuth-app) |
| §8.2 MCP не хранит/не видит токен | `NangoClient` без credentials-метода | `test_client_has_no_credentials_fetch_method`, `test_no_tool_leaks_a_token` |
| §8.3 добавить платформу = только интеграция + инструменты | `resolve()`/config, авто-discovery реестра | `test_adding_platform_is_config_only` |
| §8.4 подтверждение перед публикацией/отпиской | confirmation-guard | `test_vk_post_requires_confirmation_first`, `test_youtube_upload_confirmation_then_upload` |
