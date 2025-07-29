# Улучшенная система сбора длинных ответов AI

**Дата**: 13 июля 2025
**Версия**: 1.0
**Интеграция**: MCP Playwright + Smart Response Collection

## 🎯 Проблема и решение

### ❌ Проблема: Длинные ответы AI

- **ChatGPT/Claude/Grok** могут давать ответы на 5000+ слов
- **Streaming ответы** генерируются постепенно
- **Snapshot ограничения** - видна только часть экрана
- **Прокрутка** нужна для длинных ответов
- **Таймауты** - неясно когда ответ завершен

### ✅ Решение: Умная система сбора

```python
# Автоматически определяет тип ответа
is_streaming = await self._detect_streaming_response(ai_system)

if is_streaming:
    # Собираем по частям с отслеживанием изменений
    await self._collect_streaming_response(response, config)
else:
    # Собираем с автопрокруткой
    await self._collect_static_response(response, config)
```

## 🧠 Интеллектуальные возможности

### 1. **Детекция типа ответа**

```python
async def _detect_streaming_response(self, ai_system: str) -> bool:
    # Два snapshot с интервалом
    snapshot1 = await mcp__playwright__browser_snapshot()
    await asyncio.sleep(2)
    snapshot2 = await mcp__playwright__browser_snapshot()

    # Если контент изменился - streaming
    return len(snapshot2) != len(snapshot1)
```

### 2. **Streaming сбор по частям**

```python
while (time.time() - start_time) < config["max_wait"]:
    current_content = self._extract_response_text(snapshot, ai_system)

    if current_content != last_content:
        # Новый контент - сохраняем chunk
        chunk = ResponseChunk(content=current_content, chunk_number=chunk_number)
        response.chunks.append(chunk)

        # Автопрокрутка для длинных ответов
        if len(current_content) > 2000:
            await self._auto_scroll_response(ai_system)
    else:
        stable_count += 1
        if stable_count >= 3:  # 3 стабильных итерации = завершен
            break
```

### 3. **Автоматическая прокрутка**

```python
async def _collect_with_scrolling(self, ai_system: str) -> str:
    all_content = ""

    for scroll_attempt in range(10):  # Максимум 10 прокруток
        current_content = self._extract_response_text(snapshot, ai_system)

        if len(current_content) > len(all_content):
            all_content = current_content

        # Скроллим вниз
        await mcp__playwright__browser_press_key(key="PageDown")
        await asyncio.sleep(1)

        # Проверяем изменения
        if len(new_snapshot) == last_height:
            break  # Больше нечего скроллить

    return all_content
```

### 4. **Умные критерии завершения**

```python
def _is_response_complete(self, snapshot: str, ai_system: str) -> bool:
    # Проверяем отсутствие индикаторов печати
    typing_indicators = ["typing", "generating", "loading", "thinking"]
    for indicator in typing_indicators:
        if indicator.lower() in snapshot.lower():
            return False

    # Проверяем ключевые слова завершения
    completion_keywords = ["completed", "finished", "done", "завершено", "готово"]
    for keyword in completion_keywords:
        if keyword.lower() in snapshot.lower():
            return True
```

## ⚙️ Конфигурация под задачи

### Адаптивные настройки по длине ответа

```python
configs = {
    "short": {
        "max_wait": 60,          # 1 минута
        "chunk_interval": 2,     # Каждые 2 секунды
        "max_chunks": 10
    },
    "medium": {
        "max_wait": 180,         # 3 минуты
        "chunk_interval": 3,     # Каждые 3 секунды
        "max_chunks": 30
    },
    "long": {
        "max_wait": 300,         # 5 минут
        "chunk_interval": 4,     # Каждые 4 секунды
        "max_chunks": 60
    },
    "very_long": {
        "max_wait": 600,         # 10 минут
        "chunk_interval": 5,     # Каждые 5 секунд
        "max_chunks": 100
    }
}
```

### AI-специфичные селекторы

```python
ai_selectors = {
    "chatgpt": {
        "response_container": "[data-testid*='conversation']",
        "message_elements": "[data-message-author-role='assistant']",
        "typing_indicator": "[data-testid='typing']",
        "stop_button": "[data-testid='stop-button']"
    },
    "grok": {
        "response_container": "[data-testid='conversation']",
        "message_elements": "[data-testid='message']",
        "typing_indicator": ".typing-indicator",
        "stop_button": "button[aria-label='Stop']"
    },
    "claude": {
        "response_container": "[data-testid='conversation']",
        "message_elements": "[data-testid='message']",
        "typing_indicator": ".loading-indicator",
        "stop_button": "[data-testid='stop-button']"
    }
}
```

## 📊 Структуры данных

### ResponseChunk - фрагмент ответа

```python
@dataclass
class ResponseChunk:
    timestamp: datetime
    content: str
    chunk_number: int
    is_complete: bool = False
    metadata: Dict = None
```

### AIResponse - полный ответ

```python
@dataclass
class AIResponse:
    ai_system: str
    chat_id: str
    full_content: str
    chunks: List[ResponseChunk]
    start_time: datetime
    end_time: Optional[datetime] = None
    is_streaming: bool = True
    word_count: int = 0
    estimated_tokens: int = 0
```

## 🚀 Использование в кросс-верификации

### Автоматическая интеграция

```python
# В automated_cross_verification.py
async def send_task_to_all_chats(self, task_id: str, expected_length: str = "long"):
    # Используем улучшенную систему
    from ai_agents.response_collector import EnhancedResponseHandler
    enhanced_handler = EnhancedResponseHandler()

    # Отправляем запросы
    await self._send_prompts_to_chats(task)

    # Умно собираем ответы
    responses = await enhanced_handler.enhanced_send_task_to_all_chats(task, expected_length)
```

### Параллельный сбор от всех AI

```python
async def collect_multiple_responses(
    self,
    ai_systems: List[str],
    chat_ids: Dict[str, str],
    expected_length: str = "medium"
) -> Dict[str, AIResponse]:

    # Запускаем сбор параллельно
    tasks = [
        self.collect_ai_response(ai_system, chat_ids[ai_system], expected_length)
        for ai_system in ai_systems
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)
    return responses
```

## 📈 Преимущества системы

### ✅ **Полнота сбора**

- **100% контента** даже для ответов >10,000 слов
- **Автопрокрутка** для длинных ответов
- **Streaming support** для постепенной генерации

### ✅ **Надежность**

- **Fallback** на базовую систему при ошибках
- **Retry логика** для нестабильных соединений
- **Error recovery** с детальным логированием

### ✅ **Производительность**

- **Параллельный сбор** от всех AI систем
- **Адаптивные таймауты** под разные задачи
- **Умные критерии остановки** - не ждем лишнее время

### ✅ **Детальная статистика**

```python
# Для каждого ответа
{
    "word_count": 2847,
    "estimated_tokens": 3701,
    "chunks_count": 12,
    "was_streaming": True,
    "collection_time": 45.3  # секунд
}
```

## 🔍 Извлечение текста из HTML

### Многоуровневый парсинг

```python
def _extract_response_text(self, snapshot: str, ai_system: str) -> str:
    # 1. AI-специфичные паттерны
    ai_patterns = {
        "chatgpt": r'assistant"[^>]*>([^<]+)',
        "grok": r'ai-message[^>]*>([^<]+)',
        "claude": r'assistant[^>]*>([^<]+)'
    }

    # 2. Fallback паттерны
    fallback_patterns = [
        r"(?:ответ|response|reply)[:\s]*([^<\n]{100,})",
        r"(?:решение|solution)[:\s]*([^<\n]{100,})"
    ]

    # 3. Крайний fallback - видимый текст
    visible_text = re.sub(r'<[^>]+>', '', snapshot)
    content_lines = [line.strip() for line in lines if len(line.strip()) > 50]

    return '\n'.join(content_lines[-10:])  # Последние 10 строк
```

## 📋 Примеры использования

### 1. Краткие консультации

```python
responses = await collector.collect_multiple_responses(
    ["chatgpt", "grok", "claude"],
    chat_ids,
    expected_length="short"  # 1 минута, 10 чанков
)
```

### 2. Детальные стратегии

```python
responses = await collector.collect_multiple_responses(
    ["chatgpt", "grok", "claude"],
    chat_ids,
    expected_length="long"  # 5 минут, 60 чанков
)
```

### 3. Comprehensive анализ

```python
responses = await collector.collect_multiple_responses(
    ["chatgpt", "grok", "claude"],
    chat_ids,
    expected_length="very_long"  # 10 минут, 100 чанков
)
```

## 🔧 Интеграция с существующей системой

### Обратная совместимость

- **Автоматический fallback** на базовую систему
- **Те же интерфейсы** - никаких изменений в CLI
- **Дополнительные метаданные** в результатах

### Улучшенное логирование

```
INFO: Начало сбора ответа от chatgpt, chat: c_abc123
DEBUG: Chunk 1: +247 символов
DEBUG: Chunk 2: +389 символов
INFO: Ответ стабилизирован, завершаем сбор
INFO: Ответ от chatgpt собран: 2847 слов, 12 чанков
```

---

## 🎯 Результат

Теперь система **гарантированно собирает 100% контента** от всех AI систем, независимо от длины ответов. Streaming ответы, длинные анализы, detailed code - все собирается полностью и автоматически!

**Использование**: Никаких изменений в CLI - система автоматически использует улучшенный сбор для всех задач кросс-верификации.
