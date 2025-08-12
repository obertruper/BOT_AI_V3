#!/bin/bash
# Скрипт установки расширений для Cursor IDE

echo "🚀 Установка расширений для Cursor IDE..."
echo "----------------------------------------"

# Основные расширения
extensions=(
  "claudedev.claude-dev"
  "ms-python.python"
  "ms-python.vscode-pylance"
  "ms-python.debugpy"
  "ms-python.black-formatter"
  "charliermarsh.ruff"
  "ms-python.mypy-type-checker"
  "mtxr.sqltools"
  "mtxr.sqltools-driver-pg"
  "eamodio.gitlens"
  "github.vscode-pull-request-github"
  "ms-azuretools.vscode-docker"
  "redhat.vscode-yaml"
  "dotenv.dotenv-vscode"
  "yzhang.markdown-all-in-one"
  "esbenp.prettier-vscode"
  "humao.rest-client"
  "gruntfuggly.todo-tree"
  "christian-kohler.path-intellisense"
  "usernamehw.errorlens"
)

# Проверка наличия команды cursor или code
if command -v cursor &> /dev/null; then
    CMD="cursor"
elif command -v code &> /dev/null; then
    CMD="code"
    echo "⚠️  Cursor не найден, используем VS Code команды"
else
    echo "❌ Ни Cursor, ни VS Code не найдены в системе"
    echo "Установите расширения вручную через Marketplace"
    exit 1
fi

# Установка расширений
for ext in "${extensions[@]}"; do
    echo "📦 Устанавливаем: $ext"
    $CMD --install-extension "$ext" 2>/dev/null || echo "   ⚠️  Не удалось установить $ext"
done

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📝 Дополнительные шаги:"
echo "1. Перезапустите Cursor"
echo "2. Откройте настройки (Cmd/Ctrl + ,)"
echo "3. Проверьте, что Python интерпретатор указывает на ./venv/bin/python"
echo "4. Убедитесь, что Claude Dev настроен с вашим API ключом"
echo ""
echo "🔧 MCP серверы:"
echo "- filesystem (работа с файлами)"
echo "- postgres (БД на порту 5555)"
echo "- puppeteer (браузерная автоматизация)"
echo "- sequential-thinking (сложные рассуждения)"
echo "- memory (контекст между сессиями)"
echo "- github (работа с репозиторием)"
echo "- sonarqube (качество кода)"
