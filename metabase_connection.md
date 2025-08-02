# Параметры подключения Metabase к PostgreSQL

## 🔧 Настройки подключения

### Для Metabase GUI

- **Database type**: PostgreSQL
- **Name**: BOT Trading v3
- **Host**: localhost
- **Port**: 5555
- **Database name**: bot_trading_v3
- **Username**: obertruper
- **Password**: ilpnqw1234

### Важно

- ✅ Используйте **localhost** (не 127.0.0.1)
- ✅ Порт **5555** (не стандартный 5432!)
- ✅ SSL можно отключить для локального подключения

### Connection string для Metabase

```
postgres://obertruper:ilpnqw1234@localhost:5555/bot_trading_v3
```

### Проверка подключения в терминале

```bash
# Должно работать:
PGPASSWORD=ilpnqw1234 psql -h localhost -p 5555 -U obertruper -d bot_trading_v3 -c '\dt'
```

### Если Metabase в Docker

```yaml
environment:
  - MB_DB_TYPE=postgres
  - MB_DB_DBNAME=bot_trading_v3
  - MB_DB_PORT=5555
  - MB_DB_USER=obertruper
  - MB_DB_PASS=ilpnqw1234
  - MB_DB_HOST=host.docker.internal  # или IP хоста
```

### Альтернатива - DBeaver/pgAdmin

Те же параметры работают для любого GUI клиента PostgreSQL.
