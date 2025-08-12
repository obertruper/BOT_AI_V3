#!/bin/bash

# Полный скрипт исправления 499 ошибок в системе BOT Trading v3
# Запускает все исправления и применяет их к файлам

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
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

# Создание необходимых директорий
create_directories() {
    print_status "Создание необходимых директорий..."

    mkdir -p logs
    mkdir -p config
    mkdir -p data/logs

    print_success "Директории созданы"
}

# Шаг 1: Анализ и создание исправлений
step1_analysis() {
    print_step "Шаг 1: Анализ проблем и создание исправлений"

    if [ -f "scripts/fix_system_issues.py" ]; then
        print_status "Запуск анализа системных проблем..."
        python3 scripts/fix_system_issues.py
        print_success "Анализ завершен"
    else
        print_error "Файл scripts/fix_system_issues.py не найден"
        exit 1
    fi
}

# Шаг 2: Исправление WebSocket
step2_websocket() {
    print_step "Шаг 2: Исправление проблем с WebSocket"

    if [ -f "scripts/fix_websocket_connections.py" ]; then
        print_status "Запуск исправления WebSocket..."
        python3 scripts/fix_websocket_connections.py
        print_success "Исправление WebSocket завершено"
    else
        print_warning "Файл scripts/fix_websocket_connections.py не найден"
    fi
}

# Шаг 3: Применение исправлений к файлам
step3_apply_fixes() {
    print_step "Шаг 3: Применение исправлений к файлам"

    if [ -f "scripts/apply_499_fixes.py" ]; then
        print_status "Применение исправлений к файлам..."
        python3 scripts/apply_499_fixes.py
        print_success "Применение исправлений завершено"
    else
        print_warning "Файл scripts/apply_499_fixes.py не найден"
    fi
}

# Шаг 4: Проверка результатов
step4_verification() {
    print_step "Шаг 4: Проверка результатов"

    print_status "Запуск мониторинга 499 ошибок..."
    if [ -f "scripts/monitor_499_errors.py" ]; then
        python3 scripts/monitor_499_errors.py
    else
        print_warning "Файл scripts/monitor_499_errors.py не найден"
    fi

    print_status "Проверка созданных файлов конфигурации..."

    config_files=(
        "config/websocket_optimizations.json"
        "config/http_optimizations.json"
        "config/async_optimizations.json"
        "config/optimized_websocket_config.json"
        "config/499_monitoring_config.json"
    )

    for file in "${config_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "✓ $file"
        else
            print_warning "✗ $file (не найден)"
        fi
    done

    print_status "Проверка созданных скриптов..."

    script_files=(
        "scripts/monitor_499_errors.py"
        "scripts/websocket_health_checker.py"
        "scripts/auto_fix_499_errors.py"
    )

    for file in "${script_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "✓ $file"
        else
            print_warning "✗ $file (не найден)"
        fi
    done
}

# Показ инструкций по использованию
show_instructions() {
    echo ""
    print_status "📋 ИНСТРУКЦИИ ПО ИСПОЛЬЗОВАНИЮ:"
    echo ""
    echo "🔍 Мониторинг 499 ошибок:"
    echo "   python3 scripts/monitor_499_errors.py"
    echo ""
    echo "🏥 Проверка здоровья WebSocket:"
    echo "   python3 scripts/websocket_health_checker.py"
    echo ""
    echo "🤖 Автоматическое исправление:"
    echo "   python3 scripts/auto_fix_499_errors.py"
    echo ""
    echo "🚀 Запуск системы с мониторингом:"
    echo "   ./start_with_logs.sh"
    echo ""
    echo "📊 Проверка статуса системы:"
    echo "   ./check_status.sh"
    echo ""
    echo "🛑 Остановка всех процессов:"
    echo "   ./stop_all.sh"
    echo ""
    print_warning "⚠️  ВАЖНО: Перезапустите систему после применения исправлений!"
    echo ""
    print_status "📁 Созданные файлы конфигурации:"
    echo "   • config/websocket_optimizations.json - оптимизации WebSocket"
    echo "   • config/http_optimizations.json - оптимизации HTTP"
    echo "   • config/async_optimizations.json - оптимизации асинхронных операций"
    echo "   • config/499_monitoring_config.json - конфигурация мониторинга"
    echo ""
    print_status "📄 Созданные скрипты:"
    echo "   • scripts/monitor_499_errors.py - мониторинг 499 ошибок"
    echo "   • scripts/websocket_health_checker.py - проверка здоровья WebSocket"
    echo "   • scripts/auto_fix_499_errors.py - автоматическое исправление"
}

# Основная функция
main() {
    echo "🚀 Полное исправление 499 ошибок в системе BOT Trading v3"
    echo "========================================================"
    echo ""

    # Проверки
    check_python
    activate_venv
    create_directories

    echo ""
    print_status "Начинаем процесс исправления 499 ошибок..."
    echo ""

    # Выполнение шагов
    step1_analysis
    echo ""
    step2_websocket
    echo ""
    step3_apply_fixes
    echo ""
    step4_verification
    echo ""

    # Показ инструкций
    show_instructions

    echo ""
    print_success "🎉 Полное исправление 499 ошибок завершено!"
    echo ""
    print_status "📋 Следующие шаги:"
    echo "1. Перезапустите систему: ./stop_all.sh && ./start_with_logs.sh"
    echo "2. Запустите мониторинг: python3 scripts/monitor_499_errors.py"
    echo "3. Проверьте логи на наличие новых ошибок"
    echo "4. При необходимости запустите исправления повторно"
    echo ""
    print_warning "💡 Совет: Запустите мониторинг в фоновом режиме для постоянного отслеживания"
}

# Обработка сигналов
trap 'print_error "Скрипт прерван пользователем"; exit 1' INT TERM

# Запуск основной функции
main "$@"
