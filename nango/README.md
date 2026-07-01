# nango/ — self-hosted Nango

## Запуск
```bash
./setup.sh              # один раз: генерит .env с постоянным NANGO_ENCRYPTION_KEY
docker compose up -d
docker compose ps       # nango-db, nango-redis, nango-server — healthy
```
- API + дашборд: http://localhost:3003 (basic-auth: admin / пароль из `.env`)
- Connect UI: http://localhost:3009
- Postgres: host-порт **5433** (чтобы не конфликтовать с `bot_postgres` на 5432)
- Redis: только во внутренней сети (6379 на host занят `bot_redis`)

## Где взять secret key окружения (для mcp-server/.env)
1. Открой http://localhost:3003 → войди (admin / пароль из `.env`).
2. **Environment Settings** → скопируй **Secret Key**.
3. Впиши в `../mcp-server/.env` как `NANGO_SECRET_KEY`.

Скрипт-помощник (пробует достать из БД, иначе подсказывает дашборд):
```bash
./get-secret-key.sh
```

## Важно про ключ шифрования
`NANGO_ENCRYPTION_KEY` в `.env` — **постоянный**. Если его потерять/сменить,
сохранённые credentials станут нечитаемыми. `setup.sh` не перезаписывает
существующий `.env` специально по этой причине. Полный сброс = удалить `.env`
**и** `./nango-data/` (потеряешь все подключённые аккаунты).

## Провайдеры и интеграции
Список готовых провайдеров — в дашборде (Integrations → New) или в каталоге Nango.
Как завести OAuth-приложение и интеграцию под каждую платформу —
[`../docs/USER_ACTIONS.md`](../docs/USER_ACTIONS.md).
