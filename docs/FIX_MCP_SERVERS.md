# 🔧 Исправление MCP серверов

## Текущий статус

| MCP Server | Статус | Проблема |
|------------|--------|----------|
| filesystem | ✅ connected | - |
| postgres | ✅ connected | - |
| puppeteer | ✅ connected | - |
| github | ❌ failed | Отсутствует GITHUB_TOKEN |
| memory | ❌ failed | Возможная проблема с инициализацией |

## Решения

### 1. Исправление GitHub MCP

GitHub MCP требует персональный токен доступа для работы с GitHub API.

#### Шаг 1: Создание GitHub токена

1. Перейдите на <https://github.com/settings/tokens>
2. Нажмите "Generate new token" → "Generate new token (classic)"
3. Дайте токену имя (например, "BOT_AI_V3 MCP")
4. Выберите разрешения:
   - `repo` (полный доступ к репозиториям)
   - `read:org` (чтение организаций)
   - `read:user` (чтение информации пользователя)
5. Нажмите "Generate token"
6. Скопируйте токен (он показывается только один раз!)

#### Шаг 2: Добавление токена в .env

```bash
# Добавьте в файл .env
GITHUB_TOKEN=ghp_ваш_токен_здесь
```

#### Шаг 3: Перезапуск Claude Code

```bash
# Остановите Claude Code (Ctrl+C)
# Запустите снова
claude-code
```

### 2. Исправление Memory MCP

Memory MCP может не работать из-за проблем с путями или правами доступа.

#### Вариант 1: Проверка прав доступа

```bash
# Создайте директорию для memory storage
mkdir -p ~/.claude/memory
chmod 755 ~/.claude/memory
```

#### Вариант 2: Обновление конфигурации

Обновите `.mcp.json`:

```json
"memory": {
  "command": "npx",
  "args": ["@modelcontextprotocol/server-memory"],
  "transport": "stdio",
  "env": {
    "MEMORY_STORAGE_PATH": "${HOME}/.claude/memory"
  }
}
```

#### Вариант 3: Переустановка

```bash
# Переустановите memory server
npm uninstall @modelcontextprotocol/server-memory
npm install @modelcontextprotocol/server-memory
```

### 3. Альтернативное решение - Отключение проблемных серверов

Если серверы не критичны для работы, можно временно их отключить.

Создайте файл `.mcp-minimal.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3"],
      "transport": "stdio",
      "env": {}
    },
    "postgres": {
      "command": "npx",
      "args": ["mcp-postgres-server"],
      "transport": "stdio",
      "env": {
        "PGPORT": "${PGPORT:-5555}",
        "PGUSER": "${PGUSER:-obertruper}",
        "PGPASSWORD": "${PGPASSWORD:-ilpnqw1234}",
        "PGDATABASE": "${PGDATABASE:-bot_trading_v3}"
      }
    },
    "puppeteer": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-puppeteer"],
      "transport": "stdio",
      "env": {}
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sequential-thinking"],
      "transport": "stdio",
      "env": {}
    }
  }
}
```

И переименуйте файлы:

```bash
mv .mcp.json .mcp-full.json
mv .mcp-minimal.json .mcp.json
```

## Проверка после исправления

После применения исправлений:

1. Перезапустите Claude Code
2. Выполните команду `/mcp`
3. Все активные серверы должны показывать статус "✔ connected"

## Диагностика проблем

Если проблемы остаются, проверьте логи:

```bash
# Логи Claude Code
tail -f ~/.claude/logs/latest.log

# Проверка npm пакетов
npm list | grep "@modelcontextprotocol"

# Проверка переменных окружения
env | grep -E "(GITHUB|MEMORY)"
```

## Важные замечания

1. **GitHub токен** - храните его безопасно, не коммитьте в репозиторий
2. **Memory MCP** - не критичен для основной работы, можно работать без него
3. **Перезапуск** - после изменения `.mcp.json` требуется перезапуск Claude Code

---

*Последнее обновление: 4 августа 2025*
