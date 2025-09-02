#!/bin/bash

echo "🚀 Настройка Claude Code GitHub App для BOT_AI_V3"
echo "================================================="

# Проверка авторизации
echo "✅ Проверка GitHub авторизации..."
if ! gh auth status >/dev/null 2>&1; then
    echo "❌ Требуется авторизация в GitHub"
    echo "Выполните: gh auth login"
    exit 1
fi

# Установка приложения через браузер
echo ""
echo "📱 Установка Claude Code GitHub App"
echo "1. Откройте в браузере: https://github.com/apps/claude-code-mcp/installations/select_target"
echo "2. Выберите репозиторий: obertruper/BOT_AI_V3"
echo "3. Нажмите 'Install'"
echo ""
echo "Нажмите Enter после установки приложения..."
read

# Проверка установки
echo "🔍 Проверка установки..."
INSTALLATIONS=$(gh api /user/installations --jq '.installations[].id' 2>/dev/null)

if [ -z "$INSTALLATIONS" ]; then
    echo "⚠️ Приложение не найдено. Проверьте установку вручную."
else
    echo "✅ Приложение установлено!"
fi

# Проверка секретов
echo ""
echo "🔐 Проверка GitHub Secrets..."
echo "Проверяем наличие ANTHROPIC_API_KEY..."

if gh secret list -R obertruper/BOT_AI_V3 | grep -q "ANTHROPIC_API_KEY"; then
    echo "✅ ANTHROPIC_API_KEY уже настроен"
else
    echo "⚠️ ANTHROPIC_API_KEY не найден"
    echo "Добавьте его: https://github.com/obertruper/BOT_AI_V3/settings/secrets/actions"
fi

# Проверка workflow
echo ""
echo "📋 Проверка Claude Code workflow..."
if [ -f ".github/workflows/claude-code.yml" ]; then
    echo "✅ Claude Code workflow найден"
else
    echo "❌ Claude Code workflow не найден"
fi

# Тестовый PR
echo ""
echo "🧪 Хотите создать тестовый PR для проверки Claude Code? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    BRANCH_NAME="test-claude-code-$(date +%s)"
    git checkout -b "$BRANCH_NAME"
    echo "# Test Claude Code" > test_claude_code.md
    git add test_claude_code.md
    git commit -m "test: Check Claude Code integration"
    git push origin "$BRANCH_NAME"

    gh pr create \
        --title "Test: Claude Code Integration" \
        --body "@claude Please review this test PR and confirm you're working correctly." \
        --base main

    echo "✅ Тестовый PR создан!"
    echo "Откройте PR и проверьте ответ от Claude"

    # Возврат на main
    git checkout main
fi

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "📝 Дальнейшие шаги:"
echo "1. Убедитесь, что ANTHROPIC_API_KEY добавлен в GitHub Secrets"
echo "2. При создании PR, Claude автоматически проверит код"
echo "3. Используйте @claude в комментариях для взаимодействия"
echo ""
echo "📚 Документация: https://github.com/anthropics/claude-code-action"
