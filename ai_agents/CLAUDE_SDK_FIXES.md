# Исправления Claude Code SDK Integration

## Дата: 13 июля 2025

### Проблемы и решения

#### 1. ❌ Ошибка пути к Claude CLI
**Проблема**: `FileNotFoundError: [Errno 2] No such file or directory: 'claude'`
- Claude CLI установлен как shell alias в `/Users/ruslan/.claude/local/claude`
- Python subprocess не видит shell aliases

**Решение**:
- Добавлен метод `_find_claude_cli()` для поиска Claude в нескольких местах
- Сохранение найденного пути в `self.claude_cmd`
- Использование полного пути вместо "claude"

#### 2. ❌ Неправильные значения PermissionMode
**Проблема**: `AttributeError: type object 'PermissionMode' has no attribute 'ASK'`
- Устаревшие значения enum для PermissionMode

**Решение**:
- Обновлены значения PermissionMode:
  - `ACCEPT_EDITS = "acceptEdits"`
  - `BYPASS_PERMISSIONS = "bypassPermissions"`  
  - `DEFAULT = "default"`
  - `PLAN = "plan"`
- Заменен `PermissionMode.ASK` на `PermissionMode.DEFAULT`

#### 3. ❌ Неправильный параметр CLI
**Проблема**: `error: unknown option '--allowed-tool'`
- Claude CLI ожидает `--allowedTools` вместо `--allowed-tool`

**Решение**:
- Изменен параметр с `--allowed-tool` на `--allowedTools`

#### 4. ❌ Неправильная передача prompt
**Проблема**: `Error: Input must be provided either through stdin or as a prompt argument`
- Claude CLI требует передачу prompt через stdin

**Решение**:
- Убран prompt из аргументов командной строки
- Добавлен `stdin=asyncio.subprocess.PIPE`
- Передача prompt через `communicate(input=prompt.encode())`

#### 5. ❌ Неправильное имя модели
**Проблема**: `Invalid model name: claude-3-opus-20250514`
- Claude CLI использует aliases вместо полных имен

**Решение**:
- Изменена модель по умолчанию на `"sonnet"`
- Добавлен комментарий о доступных aliases: "opus", "sonnet", "haiku"

### Результаты тестирования

✅ **Все тесты пройдены успешно!**

1. **SDK Connection**: Успешная инициализация и выполнение запросов
2. **Agent Creation**: Все типы агентов создаются корректно
3. **MCP Integration**: Все MCP серверы загружены и настроены
4. **Token Management**: Система управления токенами работает
5. **Caching**: Кеширование функционирует правильно

### Файлы изменены

1. `/ai_agents/claude_code_sdk.py`:
   - Добавлен `_find_claude_cli()` 
   - Обновлен PermissionMode enum
   - Изменен параметр на `--allowedTools`
   - Добавлена передача через stdin
   - Модель изменена на alias "sonnet"

2. `/ai_agents/agent_manager.py`:
   - PermissionMode.ASK → PermissionMode.DEFAULT
   - Модель изменена на "sonnet"

3. `/ai_agents/agents/autonomous_developer.py`:
   - PermissionMode.ASK → PermissionMode.DEFAULT

### Рекомендации

1. **Выбор модели**: Используйте aliases ("opus", "sonnet", "haiku") в зависимости от задачи
2. **Permissions**: Для автономной разработки используйте `ACCEPT_EDITS`
3. **MCP серверы**: Все 7 серверов активны и готовы к использованию

### Использование

```python
from ai_agents import ClaudeCodeSDK, ClaudeCodeOptions

# Инициализация SDK
sdk = ClaudeCodeSDK(use_package_auth=True)

# Простой запрос
result = await sdk.query("Ваш запрос", ClaudeCodeOptions(
    model="opus",  # или "sonnet", "haiku"
    thinking_mode=ThinkingMode.THINK
))
```

---

**Статус**: ✅ Claude Code SDK полностью интегрирован и работает без ошибок!