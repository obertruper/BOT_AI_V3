# Claude Code SDK - Полное объяснение 🤖

## Что это такое? (Простыми словами)

**Claude Code SDK** - это мост между вашим Python кодом и Claude AI. Представьте, что у вас есть супер-умный помощник (Claude), и SDK - это способ дать ему руки, чтобы он мог не только советовать, но и делать.

### Аналогия из жизни:
- **Без SDK**: Вы спрашиваете у эксперта совет, он отвечает, а вы сами все делаете
- **С SDK**: Эксперт не только советует, но и сам выполняет работу на вашем компьютере

## Как это работает?

### 1. Архитектура системы

```
Ваш Python код
     ↓
Claude Code SDK (Python обертка)
     ↓
Claude CLI (командная строка)
     ↓
Claude AI API
     ↓
MCP серверы (расширения возможностей)
```

### 2. Основные компоненты

#### 🎮 Claude Code SDK
```python
from ai_agents import ClaudeCodeSDK

sdk = ClaudeCodeSDK()  # Это ваш пульт управления
```

#### ⚙️ Опции (настройки)
```python
options = ClaudeCodeOptions(
    model="sonnet",              # Какую модель использовать
    thinking_mode=ThinkingMode.THINK,  # Как глубоко думать
    allowed_tools=["Read", "Write"],   # Что можно делать
    max_turns=5                  # Сколько шагов можно сделать
)
```

#### 🛠️ Инструменты (Tools)
- **Read** - читать файлы
- **Write** - создавать файлы
- **Edit** - редактировать файлы
- **Bash** - выполнять команды
- **Task** - создавать подзадачи
- **TodoWrite** - управлять списком дел

#### 🧠 Режимы мышления
- **NORMAL** - быстрые ответы
- **THINK** - обдумывание перед ответом
- **THINK_HARD** - глубокий анализ
- **THINK_HARDER** - очень глубокий анализ
- **ULTRATHINK** - максимальное обдумывание

## MCP (Model Context Protocol) - Суперсилы для Claude

MCP серверы - это плагины, которые дают Claude дополнительные способности:

### 1. 📁 Filesystem MCP
Работа с файловой системой:
```python
# Claude может использовать:
mcp__filesystem__read_file      # Читать файлы
mcp__filesystem__write_file     # Писать файлы
mcp__filesystem__search_files   # Искать файлы
```

### 2. 🐙 GitHub MCP
Работа с GitHub:
```python
mcp__github__create_pr         # Создавать Pull Request
mcp__github__create_issue      # Создавать Issue
mcp__github__review_pr         # Ревью кода
```

### 3. 🧠 Sequential Thinking MCP
Пошаговое мышление для сложных задач:
```python
mcp__sequential-thinking__sequentialthinking
```

Это позволяет Claude:
- Думать пошагово
- Пересматривать предыдущие мысли
- Строить и проверять гипотезы
- Адаптировать план по ходу работы

### 4. 🌐 Browser MCP (Playwright/Puppeteer)
Автоматизация браузера:
```python
mcp__playwright__browser_navigate   # Открыть сайт
mcp__playwright__browser_click      # Кликнуть элемент
mcp__playwright__browser_type       # Ввести текст
```

## Практические примеры

### Пример 1: Простой анализ кода
```python
# Claude читает файл и дает рекомендации
result = await sdk.query(
    "Проанализируй main.py и найди потенциальные проблемы",
    options
)
```

**Что происходит:**
1. SDK отправляет задание Claude
2. Claude использует инструмент Read для чтения файла
3. Анализирует код
4. Возвращает список проблем и рекомендаций

### Пример 2: Автоматическое исправление
```python
# Claude находит и исправляет баги
result = await sdk.query(
    "Найди и исправь все ошибки импорта в проекте",
    ClaudeCodeOptions(
        allowed_tools=["Read", "Edit", "Grep"],
        permission_mode=PermissionMode.ACCEPT_EDITS
    )
)
```

**Что происходит:**
1. Grep - ищет все импорты
2. Read - читает файлы с ошибками
3. Edit - исправляет ошибки
4. Автоматически применяет изменения

### Пример 3: Sequential Thinking для архитектуры
```python
# Claude продумывает сложную архитектуру
result = await sdk.query("""
    Используй Sequential Thinking чтобы:
    1. Проанализировать текущую архитектуру
    2. Найти проблемы
    3. Предложить улучшения
    4. Создать план рефакторинга
""", options_with_mcp)
```

**Что происходит:**
1. **Thought 1**: "Сначала изучу структуру проекта..."
2. **Thought 2**: "Вижу проблему с циклическими зависимостями..."
3. **Thought 3**: "Нужно пересмотреть thought 2, я ошибся..."
4. **Thought 4**: "Теперь ясно, предлагаю план..."

## Реальные use cases в BOT Trading v3

### 1. 🔍 Code Review Agent
```python
from ai_agents import review_code

# Автоматическое ревью при каждом коммите
review = await review_code("trading/strategies/new_strategy.py")
# Claude проверит: безопасность, производительность, стиль кода
```

### 2. 🧪 Test Generator
```python
from ai_agents import generate_tests

# Генерация тестов для новой функции
tests = await generate_tests("risk_management/calculator.py")
# Claude создаст: unit тесты, edge cases, fixtures
```

### 3. 🚀 Autonomous Developer
```python
from ai_agents import autonomous_development

# Claude сам реализует фичу от начала до конца
result = await autonomous_development("""
    Добавь систему уведомлений о критических событиях:
    - Email алерты
    - Telegram уведомления
    - Логирование в БД
""")
```

### 4. 🏗️ Architecture Analyzer
```python
from ai_agents import analyze_project_architecture

# Анализ всей архитектуры проекта
analysis = await analyze_project_architecture()
# Найдет: циклические зависимости, code smells, узкие места
```

## Как это экономит время?

### Без Claude Code SDK:
1. Вы пишете код (30 мин)
2. Ищете баги (20 мин)
3. Пишете тесты (40 мин)
4. Делаете ревью (15 мин)
5. Исправляете (20 мин)
**Итого: 2+ часа**

### С Claude Code SDK:
1. Описываете задачу (5 мин)
2. Claude все делает (10-15 мин)
3. Вы проверяете результат (10 мин)
**Итого: 30 минут**

## Безопасность и контроль

### Permission Modes (режимы разрешений):
- **DEFAULT** - спрашивает разрешение на важные действия
- **ACCEPT_EDITS** - автоматически применяет изменения
- **BYPASS_PERMISSIONS** - полная автономия (осторожно!)
- **PLAN** - только планирует, не выполняет

### Token Management (управление токенами):
```python
# Проверка бюджета
can_afford, reason = sdk.token_manager.can_afford(10000)

# Отчет об использовании
usage = sdk.get_token_usage()
print(f"Потрачено: ${usage['total_cost_usd']:.2f}")
```

## Лучшие практики

### ✅ DO:
1. Начинайте с простых задач
2. Используйте правильный thinking mode
3. Ограничивайте allowed_tools только нужными
4. Проверяйте результаты перед применением
5. Используйте кеширование для экономии

### ❌ DON'T:
1. Не давайте полный доступ без контроля
2. Не используйте ULTRATHINK для простых задач
3. Не игнорируйте token usage
4. Не запускайте на production без тестов

## Интеграция с другими AI

### Cross-verification (перекрестная проверка):
```python
from ai_agents import SmartCrossVerifier

verifier = SmartCrossVerifier()

# Claude предлагает решение
claude_solution = await sdk.query("Оптимизируй алгоритм сортировки")

# Проверяем через GPT-4 и Groq
verified = await verifier.cross_verify(
    prompt="Проверь это решение",
    reference_response=claude_solution,
    verify_with=["gpt-4", "groq"]
)
```

## Заключение

Claude Code SDK - это не просто инструмент, это полноценный AI-помощник разработчика, который:
- 🤖 Понимает контекст вашего проекта
- 🛠️ Может выполнять реальные действия
- 🧠 Думает пошагово над сложными задачами
- 🔄 Интегрируется с другими инструментами
- 📊 Экономит время и повышает качество кода

Начните с простых задач и постепенно доверяйте более сложные. Claude Code SDK - это будущее разработки, доступное уже сегодня!