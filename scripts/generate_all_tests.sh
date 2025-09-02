#!/bin/bash

# Скрипт для генерации ВСЕХ тестов и достижения 100% покрытия
# Запускать из корня проекта: ./scripts/generate_all_tests.sh

set -e  # Остановка при ошибке

echo "🚀 Запуск массовой генерации тестов для BOT_AI_V3"
echo "=================================================="
echo ""

# Активируем виртуальное окружение
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Установка тестовых зависимостей
echo "📦 Установка зависимостей для тестирования..."
pip install -q pytest pytest-cov pytest-asyncio pytest-mock hypothesis faker pytest-benchmark

# Создание директорий
echo "📁 Создание структуры тестов..."
mkdir -p tests/{unit,integration,e2e,performance,fixtures,mocks}
mkdir -p tests/unit/{trading,ml,exchanges,strategies,database,core,web,utils}

# Фаза 1: Генерация критических тестов
echo ""
echo "🔴 Фаза 1: Критические компоненты (trading, ml)"
echo "-------------------------------------------------"
python3 scripts/mass_test_generator.py --priority critical --workers $(nproc)

# Проверка покрытия после фазы 1
echo "📊 Проверка покрытия после Фазы 1..."
pytest tests/unit/trading tests/unit/ml -q --cov=trading --cov=ml --cov-report=term | tail -5

# Фаза 2: Высокий приоритет
echo ""
echo "🟠 Фаза 2: Высокий приоритет (exchanges, strategies)"
echo "-----------------------------------------------------"
python3 scripts/mass_test_generator.py --priority high --workers $(nproc)

# Фаза 3: Средний приоритет
echo ""
echo "🟡 Фаза 3: Средний приоритет (database, core)"
echo "----------------------------------------------"
python3 scripts/mass_test_generator.py --priority medium --workers $(nproc)

# Фаза 4: Остальные модули
echo ""
echo "🟢 Фаза 4: Остальные модули (web, utils)"
echo "-----------------------------------------"
python3 scripts/mass_test_generator.py --module web --workers $(nproc)
python3 scripts/mass_test_generator.py --module utils --workers $(nproc)

# Фаза 5: Интеграционные тесты
echo ""
echo "🔄 Фаза 5: Интеграционные тесты"
echo "--------------------------------"
python3 scripts/smart_test_manager.py generate --update

# Генерация дашборда
echo ""
echo "📊 Генерация дашборда с метриками..."
python3 scripts/smart_test_manager.py dashboard

# Финальная проверка покрытия
echo ""
echo "🎯 ФИНАЛЬНАЯ ПРОВЕРКА ПОКРЫТИЯ"
echo "==============================="

# Запуск всех тестов с покрытием
pytest tests/ --cov=. --cov-report=term --cov-report=html --cov-report=json -q

# Анализ результатов
echo ""
python3 -c "
import json
import sys

with open('coverage.json', 'r') as f:
    data = json.load(f)

total = data.get('totals', {})
line_cov = total.get('percent_covered', 0)
num_statements = total.get('num_statements', 0)
missing_lines = total.get('missing_lines', 0)

print('📈 РЕЗУЛЬТАТЫ ПОКРЫТИЯ:')
print('=' * 40)
print(f'✅ Покрытие строк: {line_cov:.1f}%')
print(f'📊 Всего строк: {num_statements:,}')
print(f'❌ Не покрыто строк: {missing_lines:,}')
print()

if line_cov >= 95:
    print('🎉 ОТЛИЧНО! Покрытие превышает 95%!')
elif line_cov >= 80:
    print('👍 Хорошо! Покрытие превышает 80%')
elif line_cov >= 60:
    print('⚠️ Требуется больше тестов (покрытие {:.1f}%)'.format(line_cov))
else:
    print('❌ Критично низкое покрытие!')
    sys.exit(1)
"

# Открытие HTML отчёта
echo ""
echo "📂 HTML отчёт сохранён в: htmlcov/index.html"
echo "📊 Дашборд доступен в: tests/test_dashboard.html"

# Подсчёт созданных тестов
TEST_COUNT=$(find tests -name "test_*.py" -type f | wc -l)
echo ""
echo "✅ Создано тестовых файлов: $TEST_COUNT"

# Создание отчёта
cat > tests/generation_summary.md << EOF
# Отчёт о генерации тестов

**Дата**: $(date)

## Статистика

- Тестовых файлов создано: $TEST_COUNT
- Покрытие достигнуто: См. coverage.json
- Время выполнения: $(date)

## Следующие шаги

1. Проверить провалившиеся тесты
2. Добавить специфичные проверки
3. Запустить интеграционные тесты

## Команды

\`\`\`bash
# Запуск всех тестов
pytest tests/

# Только unit тесты
pytest tests/unit/

# С покрытием
pytest tests/ --cov=. --cov-report=html
\`\`\`
EOF

echo ""
echo "📄 Отчёт сохранён в: tests/generation_summary.md"
echo ""
echo "✅ Генерация завершена успешно!"
echo ""
echo "💡 Рекомендации:"
echo "  1. Запустите тесты: pytest tests/ -v"
echo "  2. Исправьте провалившиеся тесты"
echo "  3. Добавьте специфичные проверки для вашей бизнес-логики"
echo "  4. Настройте CI/CD для автоматического запуска"
