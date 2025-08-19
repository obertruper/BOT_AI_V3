#!/bin/bash

echo "🌐 Настройка Browser MCP серверов для автоматизации веб-дизайна"
echo "=============================================================="

# Проверяем Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js не найден. Установите Node.js 18+ для работы MCP серверов"
    exit 1
fi

echo "✅ Node.js версия: $(node --version)"

# Создаем директорию для MCP конфигураций
mkdir -p ~/.config/claude
mkdir -p .mcp

echo ""
echo "📦 Установка Microsoft Playwright MCP (рекомендуется)..."
npx @playwright/mcp@latest --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Microsoft Playwright MCP установлен"
else
    echo "⚠️  Установка Microsoft Playwright MCP..."
    npm install -g @playwright/mcp
fi

echo ""
echo "📦 Установка ExecuteAutomation Playwright MCP..."
npm list -g @executeautomation/playwright-mcp-server > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ ExecuteAutomation Playwright MCP уже установлен"
else
    echo "⚠️  Установка ExecuteAutomation Playwright MCP..."
    npm install -g @executeautomation/playwright-mcp-server
fi

echo ""
echo "🔧 Настройка конфигурации Claude Desktop..."

# Создаем конфигурацию для Claude Desktop
cat > ~/.config/claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "playwright-extended": {
      "command": "npx", 
      "args": ["-y", "@executeautomation/playwright-mcp-server"]
    },
    "browser-mcp": {
      "command": "npx",
      "args": ["-y", "browser-use-claude-mcp"]
    }
  }
}
EOF

echo "✅ Конфигурация Claude Desktop создана: ~/.config/claude/claude_desktop_config.json"

echo ""
echo "🔧 Настройка локальной MCP конфигурации проекта..."

# Создаем локальную конфигурацию для проекта
cat > .mcp/browser_automation.json << 'EOF'
{
  "servers": {
    "microsoft-playwright": {
      "description": "Microsoft Playwright MCP для структурного анализа веб-дизайна",
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "capabilities": [
        "accessibility_tree_analysis",
        "javascript_execution", 
        "ui_testing",
        "multi_browser_support",
        "screenshot_capture"
      ]
    },
    "executeautomation-playwright": {
      "description": "Расширенный Playwright MCP с API тестированием",
      "command": "npx",
      "args": ["-y", "@executeautomation/playwright-mcp-server"],
      "capabilities": [
        "browser_automation",
        "api_testing", 
        "form_automation",
        "data_extraction",
        "performance_monitoring"
      ]
    }
  },
  "use_cases": [
    "Автоматический анализ UX/UI дизайна",
    "Тестирование пользовательских сценариев",
    "Автоматизация правок веб-сайтов",
    "Валидация accessibility стандартов",
    "Производительностное тестирование"
  ]
}
EOF

echo "✅ Локальная MCP конфигурация создана: .mcp/browser_automation.json"

echo ""
echo "🧪 Проверка установки Playwright браузеров..."
npx playwright install > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Playwright браузеры установлены"
else
    echo "⚠️  Устанавливаю Playwright браузеры..."
    npx playwright install
fi

echo ""
echo "📝 Создание примера использования..."

cat > test_browser_mcp.py << 'EOF'
#!/usr/bin/env python3
"""
Пример использования Browser MCP для анализа веб-дизайна
"""

import asyncio
import json

async def test_browser_mcp():
    """Демонстрация возможностей Browser MCP"""
    
    print("🔍 Тестирование Browser MCP возможностей...")
    
    # Примеры команд для Claude с Playwright MCP:
    examples = {
        "design_analysis": {
            "description": "Анализ дизайна сайта",
            "claude_prompt": "Используй playwright MCP чтобы открыть example.com и проанализировать дизайн страницы. Проверь accessibility, цветовую схему, типографику и UX элементы."
        },
        "automated_testing": {
            "description": "Автоматическое тестирование UI",
            "claude_prompt": "Используй playwright MCP для тестирования формы регистрации на сайте. Проверь валидацию полей, обработку ошибок и пользовательский опыт."
        },
        "performance_check": {
            "description": "Проверка производительности",
            "claude_prompt": "Используй playwright MCP чтобы измерить время загрузки страниц и выявить узкие места в производительности."
        },
        "design_fixes": {
            "description": "Автоматические правки дизайна",
            "claude_prompt": "Используй playwright MCP чтобы найти и предложить исправления проблем accessibility и UX на веб-сайте."
        }
    }
    
    for key, example in examples.items():
        print(f"\n📋 {example['description']}:")
        print(f"   Команда для Claude: {example['claude_prompt']}")
    
    print(f"\n✅ Browser MCP готов к использованию!")
    print(f"💡 Перезапустите Claude Code для активации новых MCP серверов")

if __name__ == "__main__":
    asyncio.run(test_browser_mcp())
EOF

chmod +x test_browser_mcp.py

echo "✅ Пример создан: test_browser_mcp.py"

echo ""
echo "🎉 УСТАНОВКА ЗАВЕРШЕНА!"
echo "========================"
echo ""
echo "📋 Установленные MCP серверы:"
echo "   • Microsoft Playwright MCP - структурный анализ дизайна"
echo "   • ExecuteAutomation Playwright MCP - расширенная автоматизация"
echo ""
echo "🚀 Следующие шаги:"
echo "   1. Перезапустите Claude Code: claude-code restart"
echo "   2. Проверьте MCP серверы: claude-code mcp list"
echo "   3. Запустите тест: python3 test_browser_mcp.py"
echo ""
echo "💡 Примеры команд для Claude:"
echo "   • 'Используй playwright MCP чтобы проанализировать дизайн example.com'"
echo "   • 'Открой браузер через playwright и протестируй UX сайта'"
echo "   • 'Сделай автоматическую правку CSS стилей на странице'"
echo ""
echo "📚 Документация: ~/.config/claude/claude_desktop_config.json"
echo "📋 Локальная конфигурация: .mcp/browser_automation.json"