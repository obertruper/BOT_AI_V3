# Настройка Claude Code для приватного репозитория

## Проблема
Claude Code GitHub App не может автоматически получить доступ к приватному репозиторию `obertruper/BOT_AI_V3`.

## Решение

### 1. Настройка GitHub Secrets

1. Перейдите на https://github.com/obertruper/BOT_AI_V3/settings/secrets/actions
2. Добавьте следующие секреты:

   - **CLAUDE_API_KEY**
     - Получите ключ на https://console.anthropic.com/
     - Добавьте как секрет репозитория

### 2. Использование ручного workflow

Я создал альтернативный workflow `.github/workflows/claude-code-manual.yml`, который:
- Работает с приватными репозиториями
- Использует Claude API напрямую
- Автоматически комментирует PR с результатами ревью

### 3. Создание Personal Access Token (опционально)

Если нужен расширенный доступ:

1. Перейдите на https://github.com/settings/tokens/new
2. Создайте токен с правами:
   - `repo` (полный доступ к приватным репозиториям)
   - `workflow` (обновление GitHub Actions workflows)
3. Добавьте токен как секрет `PERSONAL_ACCESS_TOKEN`

### 4. Тестирование

Создайте тестовый PR:

```bash
git checkout -b test-claude-review
echo "# Test Claude Review" >> TEST_REVIEW.md
git add TEST_REVIEW.md
git commit -m "Test: Claude Code review on private repo"
git push origin test-claude-review
```

Затем создайте Pull Request на GitHub.

## Альтернативы

### Вариант А: Сделать репозиторий публичным
```bash
# На GitHub: Settings → General → Change visibility → Make public
```

### Вариант Б: Использовать Claude Code локально
Вместо GitHub интеграции, используйте Claude Code напрямую в вашей IDE для:
- Code review
- Генерации тестов
- Рефакторинга
- Документации

### Вариант В: GitHub App с расширенными правами
1. Создайте собственное GitHub App: https://github.com/settings/apps/new
2. Настройте права для приватных репозиториев
3. Установите в ваш репозиторий

## Проверка статуса

```bash
# Проверка workflows
gh workflow list

# Просмотр последних запусков
gh run list

# Проверка секретов (не показывает значения)
gh secret list
```