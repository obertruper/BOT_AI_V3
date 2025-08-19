#!/bin/bash
# Автоматизированное тестирование BOT_AI_V3
set -e

echo "🤖 Запуск автоматизированного тестирования..."

# Активируем окружение
source venv/bin/activate
export PYTHONPATH="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3:$PYTHONPATH"
export PGPORT=5555

# Быстрая проверка системы
echo "📊 Базовая проверка покрытия..."
python3 -m pytest tests/ --cov=. --cov-report=term-missing --quiet

# Проверка критических цепочек
echo "🔗 Проверка критических цепочек..."
python3 scripts/full_chain_tester.py --quick

# Анализ производительности
echo "⚡ Анализ производительности..."
python3 -m pytest tests/ -m performance --quiet

echo "✅ Автоматизированная проверка завершена!"
