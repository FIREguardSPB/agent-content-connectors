# Personal Content Connectors

Агент-оркестратор постит в соцсети (YouTube, Instagram, VK, Дзен, …) **без ручной
возни с OAuth-токенами**. Ни ты, ни друг-фуд-стилист не ходите в консоль
разработчика — подключение аккаунта это «Войти через …» в пару кликов.

Для агентов: полный операционный плейбук — [`AGENTS.md`](AGENTS.md).

## Из чего состоит

```
[Ты/друг] ──"Войти через YouTube"──► [Nango Connect UI :3009]
                                            │  (обычный логин + Разрешить)
                                            ▼
                                 [Nango :3003  — OAuth + token store + refresh]
                                            │  (токен живёт ТОЛЬКО здесь)
[Агент] ──MCP tool──► [broker-connectors MCP] ──► [Nango Proxy] ──► [API платформы]
```

| Компонент | Где | Что делает |
|---|---|---|
| **Nango (self-hosted)** | [`nango/`](nango/) | Docker Compose: managed OAuth, хранение+refresh токенов, Connect UI. Токены не покидают твою машину. |
| **MCP-сервер** | [`mcp-server/`](mcp-server/) | Тонкая обёртка: инструменты `youtube_upload`, `instagram_post`, `vk_post`… Дёргает Nango Proxy, **сам токенов не видит**. |
| **Адаптеры** | [`mcp-server/…/adapters/`](mcp-server/src/broker_connectors/adapters/) | Для не-OAuth платформ (Дзен) — browser-automation, вне контура Nango. |
| **Confirmation-guard** | [`…/confirmation.py`](mcp-server/src/broker_connectors/confirmation.py) | Перед любым write-действием агент показывает превью и ждёт `confirm=true`. |
| **Само-расширение** | [`…/selfextend/`](mcp-server/src/broker_connectors/selfextend/) | Агент сам генерит недостающий инструмент по шаблону → sandbox → твоё ревью → активация. |

## Быстрый старт

```bash
# 1. Поднять Nango (один раз генерит секреты в nango/.env)
cd nango && ./setup.sh && docker compose up -d

# 2. Достать secret key окружения Nango -> mcp-server/.env
#    (см. nango/README.md — из дашборда :3003 или ./get-secret-key.sh)

# 3. Поставить MCP-сервер
cd ../mcp-server && uv venv && uv pip install -e ".[dev]" && python -m pytest -q

# 4. Подключить аккаунт — открывается веб-мастер (без терминала/конфигов/дашборда)
broker-wizard         # выбери платформу, вставь Client ID/Secret, жми "Подключить"

# 5. Подключить MCP-сервер к агенту (Claude Desktop/Code) — см. mcp-server/README.md
```

**Подключение для нетехнического человека** сведено к минимуму: `broker-wizard`
открывает страницу в браузере, где надо вставить два значения из OAuth-приложения и
нажать кнопку — мастер сам создаёт интеграцию в Nango, ловит подключение и сохраняет
настройку. Единственный ручной шаг на стороне платформы (создать OAuth-приложение)
расписан пошагово с актуальным UI в [`docs/USER_ACTIONS.md`](docs/USER_ACTIONS.md).

## Что делаешь ты, а что агент

Регистрация OAuth-приложения на платформе (Google Cloud Client, Meta App + App
Review, VK App) — **только вручную тобой**, это твой аккаунт разработчика и это
принципиально не автоматизируется (и не должно — [`docs/USER_ACTIONS.md`](docs/USER_ACTIONS.md)).
Всё остальное — подъём инфраструктуры, обёртки, подключение аккаунтов через
Connect UI, публикация с подтверждением, генерация новых инструментов — делает
агент/этот код.

## Статус

- ✅ Nango self-hosted: адаптированный compose (без конфликтов портов с `bot_postgres`/`bot_redis`)
- ✅ MCP-сервер, инструменты YouTube/Instagram/VK, connect-инструменты
- ✅ Confirmation-guard, PlatformAdapter + Дзен-заглушка
- ✅ Само-расширение (шаблон → sandbox → dry-run → ревью → promote)
- ✅ 27 офлайн-тестов на критерии готовности §8 — зелёные
- ⏳ Реальные OAuth-приложения и сквозное подключение аккаунта — за тобой ([`docs/USER_ACTIONS.md`](docs/USER_ACTIONS.md))

Подробнее — [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
