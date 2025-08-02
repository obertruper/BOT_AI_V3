# Настройка локального подключения к PostgreSQL

## 📋 Конфигурация для проекта на /mnt/SSD

Проект BOT Trading v3 настроен для работы с **локальным PostgreSQL** через Unix socket.

### ✅ Текущие настройки

- **База данных**: `bot_trading_v3`
- **Пользователь**: `obertruper`
- **Пароль**: `ilpnqw1234`
- **Порт**: `5555` (нестандартный!)
- **Подключение**: через Unix socket (БЕЗ TCP/IP)

### 🔧 Важные файлы конфигурации

#### 1. `.env` - переменные окружения

```bash
# НЕ указываем PGHOST для локального подключения!
PGPORT=5555
PGUSER=obertruper
PGPASSWORD=ilpnqw1234
PGDATABASE=bot_trading_v3
```

#### 2. `.mcp.json` - настройки MCP postgres сервера

```json
"postgres": {
  "env": {
    "PGPORT": "${PGPORT:-5555}",
    "PGUSER": "${PGUSER:-obertruper}",
    "PGPASSWORD": "${PGPASSWORD:-ilpnqw1234}",
    "PGDATABASE": "${PGDATABASE:-bot_trading_v3}"
  }
}
```

### 📝 Примеры подключения в коде

#### Python с psycopg2

```python
import psycopg2

conn = psycopg2.connect(
    dbname='bot_trading_v3',
    user='obertruper',
    port='5555'
    # НЕ указываем host!
)
```

#### SQLAlchemy

```python
# Обратите внимание: @ без хоста означает локальное подключение
DATABASE_URL = "postgresql://obertruper@:5555/bot_trading_v3"
```

#### Asyncpg

```python
import asyncpg

conn = await asyncpg.connect(
    database='bot_trading_v3',
    user='obertruper',
    port=5555
    # НЕ указываем host!
)
```

### 🚀 Проверка подключения

Запустите тестовый скрипт:

```bash
python3 scripts/test_local_db.py
```

Или через psql:

```bash
psql -p 5555 -U obertruper -d bot_trading_v3
```

### ⚠️ Важные моменты

1. **НЕ указывайте host** в параметрах подключения - это заставит использовать TCP/IP вместо Unix socket
2. **Порт 5555** - нестандартный порт PostgreSQL в этой системе
3. **Unix socket** находится в `/var/run/postgresql/`
4. **Локальное подключение** работает быстрее и надежнее для проектов на том же диске

### 🔍 Отладка проблем

Если подключение не работает:

1. Проверьте что PostgreSQL запущен:

   ```bash
   systemctl status postgresql
   ```

2. Проверьте Unix socket:

   ```bash
   ls -la /var/run/postgresql/
   ```

3. Проверьте пользователя:

   ```bash
   psql -p 5555 -U postgres -c "\du"
   ```

---

*Последнее обновление: 29 июля 2025*
