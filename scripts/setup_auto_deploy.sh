#!/bin/bash

echo "🚀 Настройка автоматического деплоя BOT_AI_V3"
echo "============================================="
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка необходимых инструментов
echo "📋 Проверка необходимых инструментов..."

# GitHub CLI
if command -v gh &> /dev/null; then
    echo -e "${GREEN}✅${NC} GitHub CLI установлен"
else
    echo -e "${YELLOW}⚠️${NC} GitHub CLI не установлен. Установка..."
    echo "${SUDO_PASSWORD:-your-password-here}" | sudo -S apt-get update && sudo -S apt-get install -y gh  # Используем переменную окружения
fi

# Git
if command -v git &> /dev/null; then
    echo -e "${GREEN}✅${NC} Git установлен"
else
    echo -e "${RED}❌${NC} Git не установлен"
    exit 1
fi

# Python
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✅${NC} Python установлен"
else
    echo -e "${RED}❌${NC} Python не установлен"
    exit 1
fi

echo ""
echo "🔐 Настройка GitHub Secrets для автоматического деплоя"
echo "------------------------------------------------------"
echo ""
echo "Для автоматического деплоя нужны следующие секреты:"
echo ""
echo "1. STAGING_HOST - IP адрес вашего сервера"
echo "2. STAGING_USER - SSH пользователь"
echo "3. STAGING_SSH_KEY - приватный SSH ключ"
echo "4. STAGING_PORT - SSH порт (обычно 22)"
echo ""
echo -e "${YELLOW}Хотите настроить их сейчас? (y/n)${NC}"
read -r setup_secrets

if [[ "$setup_secrets" == "y" ]]; then
    echo ""
    echo "Введите данные для деплоя:"
    echo ""
    
    # Запрос данных
    read -p "STAGING_HOST (IP сервера): " staging_host
    read -p "STAGING_USER (SSH пользователь) [$(whoami)]: " staging_user
    staging_user=${staging_user:-$(whoami)}
    read -p "STAGING_PORT (SSH порт) [22]: " staging_port
    staging_port=${staging_port:-22}
    
    echo ""
    echo "Для SSH ключа:"
    echo "1. Использовать существующий ~/.ssh/id_rsa"
    echo "2. Создать новый ключ для деплоя"
    echo "3. Указать путь к другому ключу"
    read -p "Выберите (1/2/3) [1]: " key_choice
    key_choice=${key_choice:-1}
    
    case $key_choice in
        1)
            if [ -f ~/.ssh/id_rsa ]; then
                ssh_key_path=~/.ssh/id_rsa
            else
                echo -e "${RED}❌${NC} Файл ~/.ssh/id_rsa не найден"
                exit 1
            fi
            ;;
        2)
            echo "Создание нового SSH ключа для деплоя..."
            ssh-keygen -t rsa -b 4096 -f ~/.ssh/bot_ai_v3_deploy -N "" -C "bot-ai-v3-deploy"
            ssh_key_path=~/.ssh/bot_ai_v3_deploy
            echo ""
            echo -e "${YELLOW}⚠️ ВАЖНО:${NC} Добавьте публичный ключ на сервер:"
            echo "cat ~/.ssh/bot_ai_v3_deploy.pub | ssh $staging_user@$staging_host 'cat >> ~/.ssh/authorized_keys'"
            echo ""
            echo "Нажмите Enter после добавления ключа..."
            read
            ;;
        3)
            read -p "Путь к SSH ключу: " ssh_key_path
            if [ ! -f "$ssh_key_path" ]; then
                echo -e "${RED}❌${NC} Файл не найден: $ssh_key_path"
                exit 1
            fi
            ;;
    esac
    
    # Добавление секретов в GitHub
    echo ""
    echo "📤 Добавление секретов в GitHub..."
    
    # Проверка авторизации
    if ! gh auth status &>/dev/null; then
        echo -e "${YELLOW}Требуется авторизация в GitHub${NC}"
        gh auth login
    fi
    
    # Добавление секретов
    echo "$staging_host" | gh secret set STAGING_HOST -R obertruper/BOT_AI_V3
    echo "$staging_user" | gh secret set STAGING_USER -R obertruper/BOT_AI_V3
    echo "$staging_port" | gh secret set STAGING_PORT -R obertruper/BOT_AI_V3
    cat "$ssh_key_path" | gh secret set STAGING_SSH_KEY -R obertruper/BOT_AI_V3
    
    echo -e "${GREEN}✅${NC} Секреты добавлены в GitHub!"
fi

echo ""
echo "📋 Проверка статуса системы..."
echo "------------------------------"

# Проверка workflows
echo ""
echo "GitHub Actions Workflows:"
gh workflow list -R obertruper/BOT_AI_V3 | grep -E "(CI Pipeline|Auto Deploy)" | while read -r line; do
    if echo "$line" | grep -q "active"; then
        echo -e "${GREEN}✅${NC} $line"
    else
        echo -e "${YELLOW}⚠️${NC} $line"
    fi
done

# Проверка секретов
echo ""
echo "GitHub Secrets:"
secrets=$(gh api /repos/obertruper/BOT_AI_V3/actions/secrets --jq '.secrets[].name' 2>/dev/null)

for required in "ANTHROPIC_API_KEY" "STAGING_HOST" "STAGING_USER" "STAGING_SSH_KEY" "STAGING_PORT"; do
    if echo "$secrets" | grep -q "^$required$"; then
        echo -e "${GREEN}✅${NC} $required"
    else
        echo -e "${RED}❌${NC} $required - не настроен"
    fi
done

echo ""
echo "🧪 Тестирование деплоя"
echo "---------------------"
echo ""
echo -e "${YELLOW}Хотите сделать тестовый коммит для проверки автодеплоя? (y/n)${NC}"
read -r test_deploy

if [[ "$test_deploy" == "y" ]]; then
    echo "Test deployment $(date)" >> .deploy_test
    git add .deploy_test
    git commit -m "test: Auto deployment check" --no-verify
    git push origin main
    
    echo ""
    echo "📊 Отслеживание статуса:"
    echo "1. GitHub Actions: https://github.com/obertruper/BOT_AI_V3/actions"
    echo "2. Последний workflow:"
    sleep 5
    gh run list -R obertruper/BOT_AI_V3 -L 1
fi

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "📝 Как работает система:"
echo "1. При push в main запускаются тесты"
echo "2. Если тесты прошли - автоматический деплой на сервер"
echo "3. Claude Code проверяет все Pull Requests"
echo ""
echo "🔍 Мониторинг:"
echo "- GitHub Actions: https://github.com/obertruper/BOT_AI_V3/actions"
echo "- Локальные логи: tail -f data/logs/bot_trading_*.log"
echo "- Статус системы: python3 unified_launcher.py --status"
echo ""
echo -e "${GREEN}🎉 Система полностью автоматизирована!${NC}"