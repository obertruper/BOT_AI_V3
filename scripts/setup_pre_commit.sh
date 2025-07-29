#!/bin/bash

# Скрипт для установки и настройки pre-commit хуков

echo "🔧 Настройка pre-commit хуков для проекта BOT_AI_V3..."

# Проверка наличия виртуального окружения
if [ -d "venv" ]; then
    echo "✅ Найдено виртуальное окружение venv/"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "✅ Найдено виртуальное окружение .venv/"
    source .venv/bin/activate
else
    echo "⚠️  Виртуальное окружение не найдено. Создаём новое..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Установка pre-commit
echo "📦 Установка pre-commit..."
pip install pre-commit

# Установка хуков
echo "🔗 Установка git хуков..."
pre-commit install
pre-commit install --hook-type commit-msg

# Установка дополнительных зависимостей для хуков
echo "📦 Установка дополнительных зависимостей для хуков..."
pip install black ruff mypy bandit detect-secrets isort commitizen
pip install types-requests types-PyYAML types-redis types-aiofiles

# Создание базового файла для detect-secrets
echo "🔐 Создание базового файла для detect-secrets..."
detect-secrets scan > .secrets.baseline

# Первый запуск pre-commit для проверки
echo "🏃 Первый запуск pre-commit для проверки..."
pre-commit run --all-files || true

echo "✅ Настройка pre-commit завершена!"
echo ""
echo "📝 Использование:"
echo "  - Хуки будут автоматически запускаться при каждом коммите"
echo "  - Для ручного запуска: pre-commit run --all-files"
echo "  - Для обновления хуков: pre-commit autoupdate"
echo ""
echo "⚡ Совет: добавьте pre-commit в requirements-dev.txt для других разработчиков"
