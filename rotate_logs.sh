#!/bin/bash

echo "=========================================="
echo "🔄 РОТАЦИЯ И ОЧИСТКА ЛОГОВ"
echo "=========================================="

# Создаем директорию для архивов
mkdir -p data/logs/archive

# Получаем текущую дату
CURRENT_DATE=$(date +%Y%m%d_%H%M%S)

# Архивируем старые логи
echo "📦 Архивирование старых логов..."

# Архивируем логи старше 1 дня
find data/logs -name "*.log" -type f -mtime +1 -exec mv {} data/logs/archive/ \; 2>/dev/null

# Архивируем большие файлы (>100MB)
for file in data/logs/*.log; do
    if [ -f "$file" ]; then
        SIZE=$(du -m "$file" | cut -f1)
        if [ "$SIZE" -gt 100 ]; then
            BASENAME=$(basename "$file" .log)
            gzip "$file"
            mv "$file.gz" "data/logs/archive/${BASENAME}_${CURRENT_DATE}.log.gz"
            echo "  📦 Архивирован: $file (${SIZE}MB)"
        fi
    fi
done

# Создаем новые пустые логи для текущего дня
TODAY=$(date +%Y%m%d)
touch "data/logs/bot_trading_${TODAY}.log"
touch "data/logs/launcher.log"
touch "data/logs/api.log"
touch "data/logs/frontend.log"

echo "✅ Новые файлы логов созданы"

# Очищаем старые архивы (старше 7 дней)
echo "🗑️ Удаление старых архивов..."
find data/logs/archive -name "*.gz" -type f -mtime +7 -delete 2>/dev/null
DELETED=$?
if [ $DELETED -eq 0 ]; then
    echo "  ✅ Старые архивы удалены"
fi

# Показываем статистику
echo ""
echo "📊 Статистика логов:"
echo "  • Активные логи:"
ls -lh data/logs/*.log 2>/dev/null | tail -5

echo ""
echo "  • Архивы:"
ARCHIVE_COUNT=$(find data/logs/archive -name "*.gz" 2>/dev/null | wc -l)
ARCHIVE_SIZE=$(du -sh data/logs/archive 2>/dev/null | cut -f1)
echo "    Файлов: $ARCHIVE_COUNT"
echo "    Размер: $ARCHIVE_SIZE"

echo ""
echo "✅ Ротация логов завершена!"
