#!/bin/bash
# Script to run OpenAI Codex CLI for BOT_AI_V3

echo "🤖 OpenAI Codex CLI для BOT_AI_V3"
echo "=================================="
echo ""
echo "Для начала работы с Codex необходимо:"
echo ""
echo "1. Если у вас есть ChatGPT Plus/Pro/Team:"
echo "   📝 Выполните: codex login"
echo "   Откроется браузер для авторизации через ChatGPT"
echo ""
echo "2. Если у вас есть OpenAI API ключ:"
echo "   📝 Выполните: export OPENAI_API_KEY='ваш-ключ-здесь'"
echo "   Затем запустите: codex"
echo ""
echo "После авторизации вы сможете использовать Codex для:"
echo "- Генерации кода: codex 'напиши функцию для расчета RSI'"
echo "- Отладки: codex 'исправь ошибки в trading/engine.py'"
echo "- Рефакторинга: codex 'оптимизируй этот код для производительности'"
echo "- Тестов: codex 'напиши тесты для dynamic_sltp_calculator.py'"
echo ""
echo "💡 Полезные команды:"
echo "  codex --help              # Справка"
echo "  codex --model gpt-4o      # Использовать конкретную модель"
echo "  codex --read-only         # Режим только чтения (безопаснее)"
echo "  codex exec 'команда'      # Выполнить команду неинтерактивно"
echo ""
echo "📂 Текущая директория: $(pwd)"
echo ""
echo "Нажмите Enter для запуска Codex или Ctrl+C для выхода..."
read

# Запускаем Codex
codex
