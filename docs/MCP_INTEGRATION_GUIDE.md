# 🎯 MCP Integration Guide for BOT_AI_V3

## 📋 Полная документация MCP серверов для веб-проверки системы

### 🚀 Активные MCP серверы (Декабрь 2024)

#### 1. **Puppeteer MCP** ✅

Автоматизация браузера для тестирования веб-интерфейса

**Доступные функции:**

```python
# Навигация
mcp__puppeteer__puppeteer_navigate(url, launchOptions={headless: true})

# Скриншоты
mcp__puppeteer__puppeteer_screenshot(name, selector=None, width=800, height=600, encoded=False)

# Взаимодействие с элементами
mcp__puppeteer__puppeteer_click(selector)
mcp__puppeteer__puppeteer_fill(selector, value)
mcp__puppeteer__puppeteer_select(selector, value)
mcp__puppeteer__puppeteer_hover(selector)

# Выполнение JavaScript
mcp__puppeteer__puppeteer_evaluate(script)
```

**Примеры использования для тестирования BOT_AI_V3:**

```python
# Проверка загрузки дашборда
await mcp__puppeteer__puppeteer_navigate("http://localhost:5173")
await mcp__puppeteer__puppeteer_screenshot("dashboard_loaded")

# Тест торговой панели
await mcp__puppeteer__puppeteer_fill("#quantity", "100")
await mcp__puppeteer__puppeteer_select("#leverage", "5")
await mcp__puppeteer__puppeteer_click("#buy-button")

# Проверка графиков
script = "return document.querySelector('.chart-container').offsetHeight > 0"
chart_visible = await mcp__puppeteer__puppeteer_evaluate(script)
```

#### 2. **PostgreSQL MCP** ✅

Прямое взаимодействие с базой данных (порт 5555!)

**Доступные функции:**

```python
# Выполнение запросов
mcp__postgres__query(sql, params=[])
mcp__postgres__execute(sql, params=[])

# Информация о схеме
mcp__postgres__list_schemas()
mcp__postgres__list_tables(schema="public")
mcp__postgres__describe_table(table, schema="public")
```

**Примеры для проверки данных:**

```python
# Проверка позиций
positions = await mcp__postgres__query(
    "SELECT * FROM positions WHERE status = 'open'"
)

# Проверка ML предсказаний
predictions = await mcp__postgres__query(
    "SELECT * FROM ml_predictions ORDER BY created_at DESC LIMIT 10"
)
```

#### 3. **SonarQube MCP** ✅

Анализ качества кода

**Доступные функции:**

```python
# Проекты и метрики
mcp__sonarqube__projects()
mcp__sonarqube__metrics()
mcp__sonarqube__issues(project_key, severities=["CRITICAL", "MAJOR"])

# Управление issues
mcp__sonarqube__markIssueFalsePositive(issue_key, comment)
mcp__sonarqube__assignIssue(issueKey, assignee)

# Качество кода
mcp__sonarqube__quality_gate_status(project_key)
mcp__sonarqube__measures_component(component, metric_keys)
```

#### 4. **Sequential Thinking MCP** ✅

Решение сложных задач пошагово

**Использование:**

```python
mcp__sequential-thinking__sequentialthinking(
    thought="Анализирую архитектуру веб-интерфейса",
    nextThoughtNeeded=True,
    thoughtNumber=1,
    totalThoughts=5
)
```

#### 5. **Memory MCP** ✅

Граф знаний для контекста

**Доступные функции:**

```python
# Создание сущностей
mcp__memory__create_entities(entities=[
    {"name": "WebInterface", "entityType": "Component", "observations": ["React frontend"]}
])

# Создание связей
mcp__memory__create_relations(relations=[
    {"from": "WebInterface", "to": "API", "relationType": "connects_to"}
])

# Поиск
mcp__memory__search_nodes(query="trading interface")
```

#### 6. **GitHub MCP** ✅

Интеграция с GitHub

**Доступные функции:**

```python
# Работа с репозиторием
mcp__github__get_file_contents(owner, repo, path, branch="main")
mcp__github__create_or_update_file(owner, repo, path, content, message, branch)

# Issues и PR
mcp__github__create_issue(owner, repo, title, body, labels)
mcp__github__create_pull_request(owner, repo, title, head, base, body)
```

#### 7. **Filesystem MCP** ✅

Расширенная работа с файлами

**Доступные функции:**

```python
# Чтение и запись
mcp__filesystem__read_text_file(path)
mcp__filesystem__write_file(path, content)
mcp__filesystem__edit_file(path, edits)

# Навигация
mcp__filesystem__list_directory(path)
mcp__filesystem__directory_tree(path)
mcp__filesystem__search_files(path, pattern)
```

### 🧪 Специализированные агенты для веб-тестирования

#### **web-interface-tester** 🎯

Эксперт по тестированию веб-интерфейса BOT_AI_V3

**Возможности:**

- Автоматизированное тестирование UI с Puppeteer
- Проверка функциональности компонентов
- Тестирование real-time обновлений
- Валидация форм и взаимодействий

**Команда вызова:**

```
Use web-interface-tester agent to test the trading dashboard functionality
```

#### **ui-ux-analyzer** 🎨

Специалист по анализу UX/UI

**Возможности:**

- Анализ юзабилити интерфейса
- Проверка доступности (a11y)
- Оценка производительности UI
- Визуальная регрессия

**Команда вызова:**

```
Use ui-ux-analyzer agent to analyze trading interface usability
```

#### **api-integration-tester** 🔌

Эксперт по тестированию API интеграции

**Возможности:**

- Проверка REST эндпоинтов
- Тестирование WebSocket соединений
- Валидация данных API
- Проверка консистентности данных

**Команда вызова:**

```
Use api-integration-tester agent to validate API response times
```

### 📊 Сценарии комплексной проверки системы

#### 1. **Визуальная проверка интерфейса**

```python
# Навигация к главной странице
await mcp__puppeteer__puppeteer_navigate("http://localhost:5173")

# Скриншот дашборда
await mcp__puppeteer__puppeteer_screenshot("dashboard_initial", encoded=True)

# Проверка наличия ключевых элементов
elements_check = await mcp__puppeteer__puppeteer_evaluate("""
    return {
        header: !!document.querySelector('.header'),
        tradingPanel: !!document.querySelector('.trading-panel'),
        chart: !!document.querySelector('.chart-container'),
        positions: !!document.querySelector('.positions-table')
    }
""")

# Проверка темной темы
await mcp__puppeteer__puppeteer_click("#theme-toggle")
await mcp__puppeteer__puppeteer_screenshot("dashboard_dark_mode")
```

#### 2. **Проверка торговых операций**

```python
# Заполнение торговой формы
await mcp__puppeteer__puppeteer_select("#symbol", "BTCUSDT")
await mcp__puppeteer__puppeteer_fill("#quantity", "0.001")
await mcp__puppeteer__puppeteer_select("#leverage", "5")

# Проверка валидации
await mcp__puppeteer__puppeteer_fill("#quantity", "-1")
error_shown = await mcp__puppeteer__puppeteer_evaluate(
    "return !!document.querySelector('.error-message')"
)

# Отправка корректного ордера
await mcp__puppeteer__puppeteer_fill("#quantity", "0.001")
await mcp__puppeteer__puppeteer_click("#buy-button")

# Проверка обновления позиций
await asyncio.sleep(2)
positions_updated = await mcp__puppeteer__puppeteer_evaluate(
    "return document.querySelectorAll('.position-row').length > 0"
)
```

#### 3. **Проверка real-time данных**

```python
# Мониторинг обновления цен
initial_price = await mcp__puppeteer__puppeteer_evaluate(
    "return document.querySelector('.btc-price').textContent"
)

await asyncio.sleep(5)

updated_price = await mcp__puppeteer__puppeteer_evaluate(
    "return document.querySelector('.btc-price').textContent"
)

# Проверка WebSocket соединения
ws_status = await mcp__puppeteer__puppeteer_evaluate("""
    return window.wsConnection && window.wsConnection.readyState === 1
""")
```

#### 4. **Схематическая проверка архитектуры**

```python
# Создание графа компонентов в Memory MCP
await mcp__memory__create_entities(entities=[
    {"name": "Frontend", "entityType": "Layer", "observations": ["React", "TypeScript", "Port 5173"]},
    {"name": "API_Server", "entityType": "Layer", "observations": ["FastAPI", "Port 8083"]},
    {"name": "WebSocket", "entityType": "Layer", "observations": ["Real-time", "Port 8085"]},
    {"name": "PostgreSQL", "entityType": "Database", "observations": ["Port 5555", "TimescaleDB"]},
    {"name": "ML_System", "entityType": "Component", "observations": ["PatchTST", "GPU inference"]}
])

# Создание связей
await mcp__memory__create_relations(relations=[
    {"from": "Frontend", "to": "API_Server", "relationType": "sends_requests"},
    {"from": "Frontend", "to": "WebSocket", "relationType": "subscribes"},
    {"from": "API_Server", "to": "PostgreSQL", "relationType": "queries"},
    {"from": "ML_System", "to": "PostgreSQL", "relationType": "stores_predictions"},
    {"from": "API_Server", "to": "ML_System", "relationType": "gets_signals"}
])

# Визуализация архитектуры
architecture = await mcp__memory__read_graph()
```

#### 5. **Проверка производительности**

```python
# Замер времени загрузки
performance_metrics = await mcp__puppeteer__puppeteer_evaluate("""
    const perf = window.performance.timing;
    return {
        pageLoadTime: perf.loadEventEnd - perf.navigationStart,
        domContentLoaded: perf.domContentLoadedEventEnd - perf.navigationStart,
        firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0
    }
""")

# Проверка использования памяти
memory_usage = await mcp__puppeteer__puppeteer_evaluate("""
    if (window.performance.memory) {
        return {
            usedJSHeapSize: window.performance.memory.usedJSHeapSize,
            totalJSHeapSize: window.performance.memory.totalJSHeapSize
        }
    }
    return null;
""")
```

### 🔧 Конфигурация для полной проверки

#### package.json scripts для тестирования

```json
{
  "scripts": {
    "test:web": "pytest tests/integration/test_web_interface_puppeteer.py -v",
    "test:api": "pytest tests/integration/test_api_web_integration.py -v",
    "test:visual": "python scripts/visual_regression_test.py",
    "test:performance": "python scripts/performance_test.py",
    "test:full": "npm run test:web && npm run test:api && npm run test:visual"
  }
}
```

#### Docker-compose для тестового окружения

```yaml
version: '3.8'
services:
  postgres-test:
    image: postgres:15
    ports:
      - "5555:5432"
    environment:
      POSTGRES_DB: bot_trading_v3_test
      POSTGRES_USER: obertruper
      POSTGRES_PASSWORD: test_password

  frontend-test:
    build: ./web/frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8083

  api-test:
    build: .
    ports:
      - "8083:8083"
      - "8085:8085"
    environment:
      - PGPORT=5555
      - TESTING=true
```

### 📈 Метрики для мониторинга

#### Ключевые показатели

- **Page Load Time**: < 2s
- **First Contentful Paint**: < 1s
- **API Response Time**: < 100ms
- **WebSocket Latency**: < 50ms
- **ML Inference Time**: < 20ms
- **UI Update Frequency**: 10 FPS minimum
- **Memory Usage**: < 100MB
- **CPU Usage**: < 30%

### 🚦 Чеклист проверки системы

- [ ] Frontend загружается корректно
- [ ] Все UI компоненты отображаются
- [ ] Торговая панель функционирует
- [ ] Графики обновляются в реальном времени
- [ ] WebSocket соединение стабильно
- [ ] API отвечает быстро
- [ ] Данные консистентны между API и WS
- [ ] ML сигналы доставляются вовремя
- [ ] Позиции отображаются корректно
- [ ] История ордеров доступна
- [ ] Темная тема работает
- [ ] Мобильная версия адаптивна
- [ ] Ошибки обрабатываются корректно
- [ ] Производительность в норме
- [ ] Безопасность соблюдена

---

📅 **Обновлено**: Декабрь 2024
🔖 **Версия**: 2.0
👤 **Автор**: BOT_AI_V3 Development Team
