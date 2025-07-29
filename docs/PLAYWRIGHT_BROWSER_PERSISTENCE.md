# Подключение к существующему браузеру в Playwright MCP

## Проблема

При каждом запуске Claude Code с Playwright MCP создается новый экземпляр браузера, что приводит к:
- Потере авторизации в AI системах (ChatGPT, Grok, Claude)
- Необходимости каждый раз заново входить в аккаунты
- Потере истории чатов и контекста
- Дополнительному времени на загрузку

## Исправления в документации

### 1. Обновлена ссылка на Grok

**Было**: `grok.x.ai`, `x.com/i/grok`
**Стало**: `grok.com`

Файлы обновлены:
- ✅ `docs/REAL_AI_BROWSER_INTEGRATION.md` - уже правильная ссылка
- ✅ `ai_agents/configs/mcp_servers.yaml` - исправлено в allowed_sites

### 2. Конфигурация для persistent браузера

В `ai_agents/configs/mcp_servers.yaml` добавлена поддержка постоянного профиля:

```yaml
playwright:
  name: "playwright"
  enabled: true
  config:
    browser: "chrome"
    channel: "chrome"
    headless: false
    timeout: 60000
    use_system_browser: true
    # Новые опции для persistence:
    user_data_dir: "/Users/ruslan/Library/Caches/claude-mcp-browser-profile"
    reuse_existing: true
    connect_timeout: 30000
```

## Решения для подключения к существующему браузеру

### Вариант 1: Использование постоянного профиля

**Концепция**: Создать отдельный профиль браузера только для Claude, который сохраняет cookies и авторизацию.

```yaml
# В mcp_servers.yaml
playwright:
  config:
    user_data_dir: "/Users/ruslan/Library/Caches/claude-mcp-browser"
    persistent_context: true
    reuse_context: true
```

**Преимущества**:
- ✅ Сохранение авторизации между сессиями
- ✅ Сохранение истории чатов
- ✅ Быстрый старт (не нужно заново логиниться)

**Недостатки**:
- ⚠️ Требует изменения MCP сервера
- ⚠️ Может конфликтовать с основным браузером

### Вариант 2: Подключение к уже запущенному браузеру

**Концепция**: Запустить Chrome с remote debugging и подключаться к нему.

```bash
# Запуск Chrome с remote debugging
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/claude-chrome

# В конфигурации MCP
playwright:
  config:
    connect_over_cdp: true
    cdp_endpoint: "http://localhost:9222"
```

**Преимущества**:
- ✅ Полный контроль над браузером
- ✅ Можно использовать любой профиль
- ✅ Работает с уже авторизованными аккаунтами

**Недостатки**:
- ⚠️ Требует ручного запуска браузера
- ⚠️ Может быть нестабильно

### Вариант 3: Использование session storage

**Концепция**: Сохранение cookies и localStorage после каждой сессии.

```python
# Псевдокод для сохранения сессии
async def save_browser_session():
    cookies = await page.context.cookies()
    storage = await page.evaluate("() => localStorage")
    
    with open("browser_session.json", "w") as f:
        json.dump({"cookies": cookies, "storage": storage}, f)

async def restore_browser_session():
    with open("browser_session.json", "r") as f:
        session = json.load(f)
    
    await page.context.add_cookies(session["cookies"])
    await page.evaluate(f"localStorage.clear(); {session['storage']}")
```

## Текущее состояние

### ✅ Исправлено:
1. Ссылка на Grok изменена с `grok.x.ai` на `grok.com`
2. Конфигурация MCP обновлена для поддержки `grok.com`

### 🔄 В разработке:
1. Система persistence для браузерных сессий
2. Автоматическое сохранение авторизации
3. Подключение к уже запущенному браузеру

### 📋 Требуется:
1. Тестирование с реальными AI системами
2. Доработка MCP сервера для persistence
3. Создание скриптов для управления браузерными сессиями

## Временное решение

До реализации полной persistence системы:

1. **Запустите браузер вручную** с профилем:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/Users/ruslan/Library/Caches/claude-browser \
  --no-first-run \
  --no-default-browser-check
```

2. **Авторизуйтесь во всех AI системах** (ChatGPT, Grok, Claude)

3. **Оставьте браузер открытым** между сессиями Claude

4. **Используйте команды MCP** для подключения к уже открытым вкладкам

## Планы на развитие

1. **Phase 1**: Создание утилиты для управления persistent браузером
2. **Phase 2**: Интеграция с MCP сервером для автоматического подключения
3. **Phase 3**: AI-assisted session management (автовосстановление авторизации)

---

*Документ обновлен: 13 июля 2025*
*Статус: В процессе реализации*