# MCP Setup Guide для BOT_AI_V3

## 🚀 Быстрый старт

### 1. Установка npm зависимостей для MCP серверов

```bash
# В корне проекта
npm install

# Или установка конкретных MCP серверов
npm install @modelcontextprotocol/server-filesystem
npm install @modelcontextprotocol/server-puppeteer
npm install @modelcontextprotocol/server-sequential-thinking
npm install @modelcontextprotocol/server-memory
npm install @modelcontextprotocol/server-github
npm install mcp-postgres-server
```

### 2. Настройка переменных окружения

Добавьте в `.env` файл:

```bash
# PostgreSQL для MCP
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=your_password
PGDATABASE=bot_trading_v3

# GitHub token для MCP
GITHUB_TOKEN=your_github_token
```

### 3. Перезапуск Claude Code

После изменения `.mcp.json` необходимо перезапустить Claude Code:

```bash
# Выход из текущей сессии
exit

# Повторный запуск
claude
```

### 4. Проверка подключения MCP серверов

```bash
# В Claude Code
/mcp

# Должны увидеть список активных серверов:
# ✔ filesystem
# ✔ postgres
# ✔ puppeteer
# ✔ sequential-thinking
# ✔ memory
# ✔ github
```

## 📦 Описание MCP серверов

### filesystem

- **Назначение**: Работа с файловой системой проекта
- **Функции**: Чтение, запись, поиск файлов
- **Путь**: Ограничен директорией проекта

### postgres

- **Назначение**: Работа с базой данных PostgreSQL
- **Функции**: Выполнение SQL запросов, просмотр схем и таблиц
- **Требования**: Настроенное подключение к БД

### puppeteer

- **Назначение**: Браузерная автоматизация
- **Функции**: Скриншоты, навигация, взаимодействие с веб-страницами
- **Использование**: Тестирование веб-интерфейса, парсинг

### sequential-thinking

- **Назначение**: Последовательное мышление для сложных задач
- **Функции**: Пошаговое решение проблем
- **Использование**: Архитектурные решения, отладка

### memory

- **Назначение**: Сохранение контекста между сессиями
- **Функции**: Запоминание важной информации
- **Использование**: Долгосрочные проекты

### github

- **Назначение**: Интеграция с GitHub API
- **Функции**: Работа с PR, issues, репозиториями
- **Требования**: GitHub token

## 🔧 Устранение проблем

### Ошибка "server failed"

1. Проверьте установлены ли npm пакеты
2. Проверьте переменные окружения
3. Убедитесь в правильности путей в `.mcp.json`

### Ошибка парсинга конфигурации

- Убедитесь, что используется ключ `mcpServers` вместо `servers`
- Проверьте валидность JSON

### PostgreSQL не подключается

1. Проверьте запущен ли PostgreSQL: `systemctl status postgresql`
2. Проверьте credentials в `.env`
3. Убедитесь, что база данных существует

## 📝 Дополнительные настройки

### Добавление нового MCP сервера

1. Установите npm пакет:

```bash
npm install @modelcontextprotocol/server-name
```

2. Добавьте в `.mcp.json`:

```json
"server-name": {
  "command": "npx",
  "args": ["@modelcontextprotocol/server-name"],
  "transport": "stdio",
  "env": {}
}
```

3. Перезапустите Claude Code

### Настройка хуков Claude Code

Создайте `.claude/hooks.json`:

```json
{
  "pre-commit": {
    "command": "pre-commit run --all-files",
    "blocking": true
  },
  "post-file-change": {
    "*.py": "black {file} && ruff check {file}"
  }
}
```

## 📚 Полезные ссылки

- [MCP Documentation](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Available MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Creating Custom MCP Servers](https://docs.anthropic.com/en/docs/claude-code/mcp/creating-servers)
