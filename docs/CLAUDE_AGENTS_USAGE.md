# Руководство по использованию Claude Code агентов в BOT_AI_V3

## Обзор системы агентов

В проекте BOT_AI_V3 настроена продвинутая система специализированных агентов Claude Code, каждый из которых является экспертом в определенной области. Агенты работают независимо, имеют свой контекст и могут запускаться параллельно.

## Когда использовать агентов

### 1. Trading Core Expert (`trading-core-expert`)

**Используйте когда:**

- Разрабатываете новую торговую стратегию
- Отлаживаете проблемы с исполнением ордеров
- Оптимизируете торговую логику
- Внедряете risk management правила
- Анализируете торговую производительность

**Примеры:**

```python
# Разработка новой стратегии
Task(
    description="Создать momentum стратегию",
    prompt="Разработай momentum trading стратегию которая использует RSI и MACD для входа в позиции на 15-минутном таймфрейме",
    subagent_type="trading-core-expert"
)

# Отладка проблем
Task(
    description="Исправить закрытие позиций",
    prompt="Позиции не закрываются автоматически при достижении stop-loss. Найди и исправь проблему в OrderManager",
    subagent_type="trading-core-expert"
)
```

### 2. Exchange Specialist (`exchange-specialist`)

**Используйте когда:**

- Добавляете поддержку новой биржи
- Исправляете проблемы с API биржи
- Оптимизируете WebSocket соединения
- Решаете проблемы с rate limits
- Нормализуете данные между биржами

**Примеры:**

```python
# Добавление новой биржи
Task(
    description="Добавить поддержку Kraken",
    prompt="Создай адаптер для биржи Kraken следуя паттерну других бирж в проекте",
    subagent_type="exchange-specialist"
)

# Решение проблем с WebSocket
Task(
    description="Исправить реконнект Binance",
    prompt="WebSocket Binance отключается и не переподключается автоматически. Реализуй надежный механизм реконнекта",
    subagent_type="exchange-specialist"
)
```

### 3. ML Optimizer (`ml-optimizer`)

**Используйте когда:**

- Улучшаете ML модель
- Добавляете новые признаки (features)
- Оптимизируете гиперпараметры
- Анализируете производительность модели
- Внедряете новые ML архитектуры

**Примеры:**

```python
# Оптимизация модели
Task(
    description="Улучшить точность PatchTST",
    prompt="Текущая F1 score 0.414. Проведи feature engineering и hyperparameter tuning для улучшения до 0.5+",
    subagent_type="ml-optimizer"
)

# Добавление новых признаков
Task(
    description="Добавить market microstructure features",
    prompt="Добавь признаки основанные на order book imbalance и bid-ask spread для улучшения предсказаний",
    subagent_type="ml-optimizer"
)
```

### 4. Security Guardian (`security-guardian`)

**Используйте когда:**

- Проводите security аудит
- Настраиваете защиту API ключей
- Проверяете на SQL инъекции
- Внедряете валидацию данных
- Настраиваете аутентификацию

**Примеры:**

```python
# Полный security аудит
Task(
    description="Security аудит системы",
    prompt="Проведи полный security аудит: проверь на утечки API ключей, SQL инъекции, XSS, и другие уязвимости",
    subagent_type="security-guardian"
)

# Защита endpoints
Task(
    description="Защитить API endpoints",
    prompt="Добавь rate limiting, валидацию входных данных и аутентификацию для всех критических API endpoints",
    subagent_type="security-guardian"
)
```

### 5. Performance Tuner (`performance-tuner`)

**Используйте когда:**

- API работает медленно
- Высокое использование памяти/CPU
- Нужна оптимизация БД запросов
- Настройка кеширования
- Профилирование кода

**Примеры:**

```python
# Оптимизация API
Task(
    description="Ускорить API endpoints",
    prompt="API endpoint /api/traders работает 2+ секунды. Профилируй и оптимизируй до <100ms",
    subagent_type="performance-tuner"
)

# Оптимизация памяти
Task(
    description="Уменьшить потребление памяти",
    prompt="Система использует 5GB RAM на трейдера. Найди memory leaks и оптимизируй до <2GB",
    subagent_type="performance-tuner"
)
```

## Параллельное выполнение агентов

Вы можете запускать несколько агентов параллельно для ускорения разработки:

```python
# Параллельная разработка новой функции
tasks = [
    Task(
        description="Создать API endpoint",
        prompt="Создай REST API endpoint для новой grid trading стратегии",
        subagent_type="trading-core-expert"
    ),
    Task(
        description="Создать frontend компонент",
        prompt="Создай React компонент для настройки grid trading параметров",
        subagent_type="general-purpose"
    ),
    Task(
        description="Написать тесты",
        prompt="Напиши unit и integration тесты для grid trading стратегии",
        subagent_type="test-architect"
    ),
    Task(
        description="Проверить безопасность",
        prompt="Проверь новый код grid trading на уязвимости",
        subagent_type="security-guardian"
    )
]
```

## Цепочки агентов (Agent Chains)

Для сложных задач используйте последовательные цепочки агентов:

### Пример: Полная интеграция новой биржи

```python
# Шаг 1: Реализация
Task(
    description="Реализовать Deribit адаптер",
    prompt="Создай полный адаптер для биржи Deribit с поддержкой spot и futures trading",
    subagent_type="exchange-specialist"
)

# Шаг 2: Тестирование
Task(
    description="Протестировать Deribit интеграцию",
    prompt="Напиши comprehensive тесты для Deribit адаптера включая mock тесты и integration тесты",
    subagent_type="test-architect"
)

# Шаг 3: Безопасность
Task(
    description="Security проверка Deribit",
    prompt="Проверь Deribit адаптер на безопасность: API ключи, валидация, rate limits",
    subagent_type="security-guardian"
)

# Шаг 4: Оптимизация
Task(
    description="Оптимизировать Deribit производительность",
    prompt="Оптимизируй Deribit адаптер: batch операции, кеширование, connection pooling",
    subagent_type="performance-tuner"
)

# Шаг 5: Документация
Task(
    description="Документировать Deribit",
    prompt="Создай полную документацию для Deribit интеграции с примерами использования",
    subagent_type="docs-maintainer"
)
```

## Кастомные команды (Slash Commands)

Для частых операций используйте готовые команды:

### `/check-exchange-health`

Проверяет состояние всех подключенных бирж:

```
/check-exchange-health
```

### `/analyze-trading-performance [период]`

Анализирует производительность стратегий:

```
/analyze-trading-performance last_7_days
/analyze-trading-performance 2025-01-01:2025-01-31
```

### `/security-scan`

Запускает полный security аудит:

```
/security-scan
```

### `/optimize-ml-model [параметры]`

Оптимизирует ML модель:

```
/optimize-ml-model --epochs 100 --learning-rate 0.001
```

## Best Practices

### 1. Выбирайте правильного агента

- Не используйте `general-purpose` для специализированных задач
- Используйте domain-specific агентов для лучших результатов

### 2. Предоставляйте контекст

- Включайте примеры кода
- Указывайте файлы для изменения
- Описывайте желаемый результат

### 3. Используйте параллелизм

- Запускайте независимые задачи параллельно
- Максимум 10 параллельных агентов

### 4. Проверяйте результаты

- Всегда review код от агентов
- Запускайте тесты после изменений
- Используйте security-guardian для критичного кода

### 5. Итеративная разработка

- Начинайте с простых задач
- Постепенно усложняйте
- Используйте feedback loop

## Troubleshooting

### Агент не понимает контекст проекта

- Убедитесь что CLAUDE.md актуален
- Укажите конкретные файлы в prompt
- Используйте примеры из кодовой базы

### Агент генерирует неоптимальный код

- Используйте performance-tuner после
- Укажите performance requirements в prompt
- Приведите примеры оптимального кода

### Агент не следует архитектуре проекта

- Укажите на паттерны в существующем коде
- Ссылайтесь на архитектурные принципы из CLAUDE.md
- Используйте code-reviewer после генерации

## Метрики эффективности

Отслеживайте эффективность использования агентов:

1. **Скорость разработки**: Сколько задач выполнено за день
2. **Качество кода**: Количество багов на 1000 строк
3. **Покрытие тестами**: % кода покрытого тестами
4. **Security score**: Количество уязвимостей найденных
5. **Performance gains**: Улучшение latency/throughput

## Заключение

Система агентов Claude Code в BOT_AI_V3 позволяет значительно ускорить разработку при сохранении высокого качества кода. Используйте специализированных агентов для их областей expertise, комбинируйте их в цепочки для сложных задач, и всегда проверяйте результаты.

При возникновении вопросов обращайтесь к CLAUDE.md или используйте `/help` команду.
