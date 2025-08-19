# Исправление проблем с Playwright и Browser-automation MCP серверами

## Проблема
Два MCP сервера (`playwright` и `browser-automation`) не работали из-за:
1. Отсутствия npm пакетов
2. Неправильных путей в конфигурации
3. Отсутствия системных зависимостей для браузеров

## Решение

### 1. Установка npm пакетов
```bash
npm install @playwright/mcp @executeautomation/playwright-mcp-server
```

### 2. Установка системных зависимостей (требует sudo)
```bash
sudo apt-get update
sudo apt-get install -y libevent-2.1-7t64 libgstreamer-plugins-bad1.0-0 libflite1 libavif16 gstreamer1.0-libav
```

### 3. Установка браузеров Playwright
```bash
npx playwright install
```

### 4. Обновленная конфигурация в .mcp.json
```json
"playwright": {
  "command": "npx",
  "args": ["@playwright/mcp"],
  "transport": "stdio",
  "env": {},
  "description": "BOT_AI_V3 Playwright Browser Automation",
  "systemPrompt": "..."
},
"browser-automation": {
  "command": "npx",
  "args": ["@executeautomation/playwright-mcp-server"],
  "transport": "stdio",
  "env": {},
  "description": "BOT_AI_V3 Extended Browser Automation",
  "systemPrompt": "..."
}
```

## Статус
✅ Все зависимости установлены
✅ Конфигурация обновлена
✅ Браузеры Playwright установлены

## Проверка работы
После перезапуска claude-code серверы должны работать корректно.

Для проверки:
```bash
claude-code mcp list
```

## Дополнительные зависимости в package.json
Добавлены в проект:
- @playwright/mcp
- @executeautomation/playwright-mcp-server
- И все их зависимости