# 🚀 Полная настройка MCP серверов для BOT_AI_V3

## ✅ Обновленная конфигурация

Все MCP серверы теперь настроены с правильными параметрами:

1. **Добавлен флаг `-y`** для автоматического подтверждения установки
2. **Memory сервер** - настроен путь для хранения данных
3. **GitHub сервер** - исправлено имя переменной окружения

## 📋 Что нужно сделать для полной работы

### 1. Создание GitHub Personal Access Token

1. Перейдите на <https://github.com/settings/tokens>
2. Нажмите **"Generate new token"** → **"Generate new token (classic)"**
3. Настройки токена:
   - **Note**: BOT_AI_V3 MCP Integration
   - **Expiration**: 90 days (или No expiration)
   - **Scopes** (выберите):
     - ✅ `repo` (Full control of private repositories)
     - ✅ `read:org` (Read org and team membership)
     - ✅ `read:user` (Read user profile data)
     - ✅ `gist` (Create gists)
4. Нажмите **"Generate token"**
5. **ВАЖНО**: Скопируйте токен сразу! (показывается только один раз)

### 2. Добавление токена в .env

```bash
# Откройте файл .env
nano .env

# Добавьте строку:
GITHUB_TOKEN=ghp_ваш_токен_здесь

# Сохраните и закройте (Ctrl+X, Y, Enter)
```

### 3. Проверка установки пакетов

```bash
# Проверим все MCP пакеты
npm list | grep "@modelcontextprotocol"

# Если какие-то отсутствуют, установите:
npm install @modelcontextprotocol/server-memory@latest
npm install @modelcontextprotocol/server-github@latest
```

### 4. Перезапуск Claude Code

```bash
# Остановите Claude Code (Ctrl+C)
# Запустите заново
claude-code
```

### 5. Проверка подключения

После перезапуска выполните команду `/mcp` в Claude Code.

Вы должны увидеть:

```
1. filesystem    ✔ connected
2. github        ✔ connected
3. memory        ✔ connected
4. postgres      ✔ connected
5. puppeteer     ✔ connected
6. sequential-thinking ✔ connected
```

## 🔍 Если что-то не работает

### GitHub сервер не подключается

- Проверьте, что токен добавлен в `.env`
- Убедитесь, что токен активен на GitHub
- Попробуйте: `echo $GITHUB_TOKEN` (должен показать токен)

### Memory сервер не подключается

- Проверьте права доступа: `ls -la ~/.claude/memory`
- Создайте файл вручную: `touch ~/.claude/memory/bot_ai_v3_memory.json`

### Общие проблемы

```bash
# Очистите npm кеш
npm cache clean --force

# Переустановите пакеты
rm -rf node_modules package-lock.json
npm install

# Проверьте логи Claude Code
tail -f ~/.claude/logs/latest.log
```

## 📦 Что делает каждый MCP сервер

1. **filesystem** - доступ к файлам проекта
2. **github** - работа с GitHub репозиториями, issues, PR
3. **memory** - долгосрочная память между сессиями
4. **postgres** - работа с базой данных BOT_AI_V3
5. **puppeteer** - автоматизация браузера для тестирования
6. **sequential-thinking** - последовательное решение сложных задач

## ✨ Готово

После выполнения всех шагов у вас будут работать все 6 MCP серверов, что даст полный функционал для:

- Автоматизации разработки
- Тестирования веб-интерфейса
- Работы с базой данных
- Интеграции с GitHub
- Сохранения контекста между сессиями

---

*Последнее обновление: 4 августа 2025*
