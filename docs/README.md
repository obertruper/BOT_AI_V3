# 📚 BOT_AI_V3 Documentation

Полная документация по проекту BOT Trading v3 - мульти-трейдерной платформе для автоматической торговли криптовалютой с AI-интеграцией.

## 📂 Структура документации

### 📋 Основная документация

- [**COMPLETE_DEVELOPMENT_SETUP.md**](./COMPLETE_DEVELOPMENT_SETUP.md) - Полное руководство по настройке окружения разработки
- [**PROJECT_CONTEXT.md**](./PROJECT_CONTEXT.md) - Контекст проекта и архитектура
- [**CLAUDE.md**](../CLAUDE.md) - Инструкции для Claude Code (в корне проекта)

### 🔧 Setup & Configuration

#### [`setup/`](./setup/) - Настройка окружения

- [**MCP_SETUP.md**](./setup/MCP_SETUP.md) - Настройка MCP серверов
- [**SETUP_COMPLETE.md**](./setup/SETUP_COMPLETE.md) - Итоговая конфигурация
- [**test_precommit.md**](./setup/test_precommit.md) - Тестирование pre-commit хуков

### 🎣 Hooks & Automation

#### [`hooks/`](./hooks/) - Claude Code хуки

- [**CLAUDE_CODE_HOOKS_SETUP.md**](./hooks/CLAUDE_CODE_HOOKS_SETUP.md) - Настройка хуков Claude Code

### 🐙 GitHub Integration

#### [`github/`](./github/) - GitHub интеграция

- [**GITHUB_PRIVATE_REPO_SETUP.md**](./github/GITHUB_PRIVATE_REPO_SETUP.md) - Настройка приватного репозитория
- [**README_GITHUB_SETUP.md**](./github/README_GITHUB_SETUP.md) - GitHub Actions и CI/CD
- [**test_pr_verification.md**](./github/test_pr_verification.md) - Тестирование PR верификации

### 🤖 AI Agents Documentation

- [**CLAUDE_CODE_AGENTS.md**](./CLAUDE_CODE_AGENTS.md) - Подробное руководство по Claude Code агентам
- [**CLAUDE_AGENTS_SETUP.md**](./CLAUDE_AGENTS_SETUP.md) - Установка и настройка агентов
- [**HEALTH_CHECK_IMPLEMENTATION.md**](./HEALTH_CHECK_IMPLEMENTATION.md) - Реализация health check системы

#### [`AI_VERIFICATION_REPORTS/`](./AI_VERIFICATION_REPORTS/) - Отчеты AI агентов

- Отчеты кросс-верификации от различных AI моделей
- Архитектурные анализы
- Рекомендации по оптимизации

#### Доступные Claude Code агенты

- **Разработка**: code-architect, feature-developer, code-reviewer, debug-specialist, refactor-expert, docs-maintainer
- **Торговля**: strategy-optimizer, risk-analyzer, exchange-specialist
- **Инфраструктура**: performance-tuner, test-architect, security-auditor
- **Координация**: agent-manager

## 🚀 Быстрый старт

1. **Новичок в проекте?** Начните с [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)
2. **Настройка окружения?** Читайте [COMPLETE_DEVELOPMENT_SETUP.md](./COMPLETE_DEVELOPMENT_SETUP.md)
3. **Работа с Claude Code?** См. [CLAUDE.md](../CLAUDE.md) и [CLAUDE_CODE_HOOKS_SETUP.md](./hooks/CLAUDE_CODE_HOOKS_SETUP.md)
4. **Claude Code Agents?** Изучите [CLAUDE_CODE_AGENTS.md](./CLAUDE_CODE_AGENTS.md) и [CLAUDE_AGENTS_SETUP.md](./CLAUDE_AGENTS_SETUP.md)
5. **GitHub интеграция?** Изучите документы в [github/](./github/)

## 📋 Навигация по категориям

### Для разработчиков

- [Настройка окружения разработки](./COMPLETE_DEVELOPMENT_SETUP.md)
- [Pre-commit хуки](./setup/test_precommit.md)
- [MCP серверы](./setup/MCP_SETUP.md)

### Для DevOps

- [GitHub Actions](./github/README_GITHUB_SETUP.md)
- [CI/CD настройка](./github/test_pr_verification.md)
- [Деплой чеклисты](./../.claude/commands/deploy-check.md)

### Для AI/ML инженеров

- [Claude Code агенты](./CLAUDE_CODE_AGENTS.md)
- [Настройка агентов](./CLAUDE_AGENTS_SETUP.md)
- [AI верификация](./AI_VERIFICATION_REPORTS/)
- [Claude Code интеграция](./hooks/CLAUDE_CODE_HOOKS_SETUP.md)
- [Слэш-команды](./../.claude/commands/)

## 🔍 Поиск по документации

```bash
# Поиск по всей документации
grep -r "искомый текст" docs/

# Поиск в конкретной категории
grep -r "hooks" docs/hooks/

# Поиск markdown файлов
find docs -name "*.md" -type f
```

## 📝 Соглашения

1. **Язык**: Документация на русском языке
2. **Форматирование**: Markdown с GitHub-flavored extensions
3. **Структура**: Иерархическая с категориями
4. **Именование**: UPPER_CASE для основных документов, lower_case для вспомогательных

## 🔄 Обновление документации

При изменении функциональности обновите соответствующие документы:

1. Основная функциональность → [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)
2. Процессы разработки → [COMPLETE_DEVELOPMENT_SETUP.md](./COMPLETE_DEVELOPMENT_SETUP.md)
3. Инструкции Claude → [CLAUDE.md](../CLAUDE.md)
4. GitHub workflows → документы в [github/](./github/)

---

*Последнее обновление: 29 июля 2025*
