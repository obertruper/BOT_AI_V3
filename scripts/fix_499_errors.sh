#!/bin/bash

# Скрипт исправления 499 ошибок в системе BOT Trading v3
# Автоматически запускает все исправления для решения проблем с 499 ошибками

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка наличия Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 не найден. Установите Python 3.8+"
        exit 1
    fi
    print_success "Python3 найден: $(python3 --version)"
}

# Активация виртуального окружения
activate_venv() {
    if [ -d "venv" ]; then
        print_status "Активация виртуального окружения..."
        source venv/bin/activate
        print_success "Виртуальное окружение активировано"
    else
        print_warning "Виртуальное окружение не найдено. Создайте его: python3 -m venv venv"
    fi
}

# Проверка зависимостей
check_dependencies() {
    print_status "Проверка зависимостей..."

    # Проверяем основные пакеты
    python3 -c "import asyncio, json, re" 2>/dev/null || {
        print_error "Отсутствуют необходимые зависимости. Установите: pip install asyncio"
        exit 1
    }

    print_success "Зависимости проверены"
}

# Создание необходимых директорий
create_directories() {
    print_status "Создание необходимых директорий..."

    mkdir -p logs
    mkdir -p config
    mkdir -p data/logs

    print_success "Директории созданы"
}

# Запуск основного скрипта исправления
run_main_fix() {
    print_status "Запуск основного скрипта исправления системных проблем..."

    if [ -f "scripts/fix_system_issues.py" ]; then
        python3 scripts/fix_system_issues.py
        print_success "Основной скрипт исправления завершен"
    else
        print_error "Файл scripts/fix_system_issues.py не найден"
        exit 1
    fi
}

# Запуск исправления WebSocket
run_websocket_fix() {
    print_status "Запуск исправления проблем с WebSocket..."

    if [ -f "scripts/fix_websocket_connections.py" ]; then
        python3 scripts/fix_websocket_connections.py
        print_success "Исправление WebSocket завершено"
    else
        print_warning "Файл scripts/fix_websocket_connections.py не найден"
    fi
}

# Запуск мониторинга 499 ошибок
run_monitoring() {
    print_status "Запуск мониторинга 499 ошибок..."

    if [ -f "scripts/monitor_499_errors.py" ]; then
        python3 scripts/monitor_499_errors.py
        print_success "Мониторинг 499 ошибок завершен"
    else
        print_warning "Файл scripts/monitor_499_errors.py не найден"
    fi
}

# Проверка результатов
check_results() {
    print_status "Проверка результатов исправления..."

    # Проверяем созданные файлы конфигурации
    config_files=(
        "config/websocket_optimizations.json"
        "config/http_optimizations.json"
        "config/async_optimizations.json"
        "config/optimized_websocket_config.json"
    )

    for file in "${config_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "Создан файл конфигурации: $file"
        else
            print_warning "Файл конфигурации не найден: $file"
        fi
    done

    # Проверяем созданные скрипты
    script_files=(
        "scripts/monitor_499_errors.py"
        "scripts/websocket_health_checker.py"
    )

    for file in "${script_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "Создан скрипт: $file"
        else
            print_warning "Скрипт не найден: $file"
        fi
    done
}

# Показ инструкций по использованию
show_instructions() {
    echo ""
    print_status "ИНСТРУКЦИИ ПО ИСПОЛЬЗОВАНИЮ:"
    echo ""
    echo "1. Мониторинг 499 ошибок в реальном времени:"
    echo "   python3 scripts/monitor_499_errors.py"
    echo ""
    echo "2. Проверка здоровья WebSocket соединений:"
    echo "   python3 scripts/websocket_health_checker.py"
    echo ""
    echo "3. Запуск системы с мониторингом:"
    echo "   ./start_with_logs.sh"
    echo ""
    echo "4. Проверка статуса системы:"
    echo "   ./check_status.sh"
    echo ""
    echo "5. Остановка всех процессов:"
    echo "   ./stop_all.sh"
    echo ""
    print_warning "ВАЖНО: Перезапустите систему после применения исправлений!"
}

# Основная функция
main() {
    echo "🚀 Запуск исправления 499 ошибок в системе BOT Trading v3"
    echo "=================================================="

    # Проверки
    check_python
    activate_venv
    check_dependencies
    create_directories

    # Запуск исправлений
    run_main_fix
    run_websocket_fix
    run_monitoring

    # Проверка результатов
    check_results

    # Показ инструкций
    show_instructions

    echo ""
    print_success "Исправление 499 ошибок завершено!"
    echo ""
    print_status "Следующие шаги:"
    echo "1. Перезапустите систему"
    echo "2. Запустите мониторинг: python3 scripts/monitor_499_errors.py"
    echo "3. Проверьте логи на наличие новых ошибок"
    echo "4. При необходимости запустите исправления повторно"
}

# Обработка сигналов
trap 'print_error "Скрипт прерван пользователем"; exit 1' INT TERM

# Запуск основной функции
main "$@"
