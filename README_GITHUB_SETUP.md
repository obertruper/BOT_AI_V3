# GitHub Setup для BOT Trading v3

## Статус настройки

✅ **Git репозиторий инициализирован**
- Создан локальный Git репозиторий
- Настроен .gitignore файл
- Сделан initial commit
- Ветка переименована в `main`

## Следующие шаги для полной интеграции с GitHub

### 1. Создайте репозиторий на GitHub

1. Перейдите на https://github.com/new
2. Создайте новый репозиторий с именем `BOT_AI_V3` или `BOT_Trading_v3`
3. **НЕ** инициализируйте с README, .gitignore или лицензией (они уже есть)

### 2. Подключите удаленный репозиторий

```bash
# Замените YOUR_USERNAME на ваш GitHub username
git remote add origin https://github.com/YOUR_USERNAME/BOT_AI_V3.git

# Или если используете SSH
git remote add origin git@github.com:YOUR_USERNAME/BOT_AI_V3.git
```

### 3. Отправьте код на GitHub

```bash
git push -u origin main
```

### 4. Настройте GitHub Secrets

Для работы Claude Code Actions необходимо добавить секреты в репозиторий:

1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте новый секрет:
   - Name: `CLAUDE_API_KEY`
   - Value: Ваш Claude API ключ

### 5. Установите Claude Code GitHub App

После создания репозитория на GitHub, выполните команду:
```bash
/install-github-app
```

Или настройте вручную по инструкции:
https://github.com/anthropics/claude-code-action/#manual-setup-direct-api

## Структура GitHub Actions

Уже настроены следующие workflows:

- `.github/workflows/ai_code_review.yml` - существующий workflow для AI ревью
- `.github/workflows/claude-code.yml` - новый workflow для Claude Code интеграции

## Рекомендации

1. **Приватный репозиторий**: Рекомендуется сделать репозиторий приватным, так как это торговый бот
2. **Branch Protection**: Настройте защиту main ветки с обязательным code review
3. **Secrets**: Никогда не коммитьте API ключи и секреты (уже настроен .gitignore)

## Проверка

После настройки вы можете проверить интеграцию:

```bash
# Проверка удаленного репозитория
git remote -v

# Проверка статуса
git status

# Создание тестового PR для проверки Claude Code
git checkout -b test-claude-integration
echo "# Test" >> test.md
git add test.md
git commit -m "Test Claude Code integration"
git push origin test-claude-integration
```

Затем создайте Pull Request на GitHub и Claude Code автоматически проведет ревью.