#!/bin/bash
# Скрипт запуска системы в боевом режиме

cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3

# Активация виртуального окружения
source venv/bin/activate

# Очистка старых логов
> /tmp/launcher_output.log
> /tmp/launcher_restart.log

# Проверка портов
if lsof -i :8080 > /dev/null 2>&1; then
    echo "⚠️  Порт 8080 занят, освобождаем..."
    lsof -i :8080 | grep LISTEN | awk '{print $2}' | xargs -r kill -9
    sleep 2
fi

# Запуск системы
echo "🚀 Запуск BOT_AI_V3 в боевом режиме..."
python3 unified_launcher.py --mode=ml

# Если скрипт завершился, значит что-то пошло не так
echo "❌ Система завершила работу"
