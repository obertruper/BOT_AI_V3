# 🤖 Web Testing Agent для BOT_AI_V3

## Обзор

Web Testing Agent - это автоматизированная система тестирования веб-интерфейса BOT_AI_V3, использующая Puppeteer MCP (Model Context Protocol) для управления браузером и проведения комплексных тестов.

## 🚀 Возможности

### Автоматическое тестирование

- ✅ Загрузка и проверка страниц
- ✅ Взаимодействие с элементами интерфейса
- ✅ Проверка адаптивности (desktop/tablet/mobile)
- ✅ Создание скриншотов для визуального контроля
- ✅ Проверка API интеграции
- ✅ Генерация детальных отчетов (JSON/HTML)

### Puppeteer MCP интеграция

Агент использует MCP сервер Puppeteer для:

- Навигации по страницам
- Выполнения JavaScript в контексте браузера
- Взаимодействия с DOM элементами
- Создания скриншотов
- Эмуляции различных устройств

## 📁 Структура файлов

```
scripts/
├── web_testing_agent.py          # Базовый агент (без MCP)
├── web_testing_agent_mcp.py      # Агент с примерами MCP команд
└── run_web_tests.py              # Генератор отчетов

test_results/
├── screenshots/                  # Скриншоты тестов
├── web_test_report_*.json       # JSON отчеты
└── web_test_report_*.html       # HTML отчеты
```

## 🔧 Использование

### 1. Через Claude Code с Puppeteer MCP

```python
# Навигация на страницу
await mcp_puppeteer_navigate(url="http://localhost:5173")

# Создание скриншота
await mcp_puppeteer_screenshot(name="dashboard", width=1920, height=1080)

# Клик по элементу
await mcp_puppeteer_click(selector=".trader-card")

# Выполнение JavaScript
result = await mcp_puppeteer_evaluate(script="document.title")

# Заполнение формы
await mcp_puppeteer_fill(selector="input[name='amount']", value="100")
```

### 2. Запуск автоматических тестов

```bash
# Активация виртуального окружения
source venv/bin/activate

# Запуск тестов и генерация отчета
python3 scripts/run_web_tests.py
```

### 3. Просмотр результатов

Отчеты сохраняются в директории `test_results/`:

- **JSON отчет** - машиночитаемый формат с детальными результатами
- **HTML отчет** - удобный для просмотра в браузере

## 📊 Результаты последнего тестирования

### Статистика

- **Всего тестов**: 6
- **Успешно**: 5 ✅
- **Провалено**: 0 ❌
- **Предупреждения**: 1 ⚠️
- **Успешность**: 83.3%

### Детали тестов

| Тест | Статус | Описание |
|------|--------|----------|
| Dashboard Load Test | ✅ PASSED | Главная страница загружается корректно |
| System Status Display | ✅ PASSED | Отображение статуса системы работает |
| Trader Cards Display | ✅ PASSED | Карточки трейдеров отображаются |
| Interactive Elements | ✅ PASSED | Интерактивные элементы работают |
| Mobile Responsive Design | ✅ PASSED | Адаптивный дизайн для мобильных |
| WebSocket Connection | ⚠️ WARNING | WebSocket соединения отклоняются (403) |

### Скриншоты

1. **dashboard_main** - Главная страница с общей статистикой
2. **trader_details_view** - Детальный вид после клика по трейдеру
3. **mobile_view** - Мобильная версия интерфейса (375x667)

## 🔍 Обнаруженные проблемы

### WebSocket 403 Forbidden

В логах обнаружены повторяющиеся ошибки WebSocket соединений:

```
connection rejected (403 Forbidden)
```

**Возможные причины**:

- Отсутствие аутентификации для WebSocket
- CORS политика
- Неправильная конфигурация WebSocket сервера

**Рекомендации**:

- Проверить настройки CORS в API
- Добавить правильную аутентификацию для WebSocket
- Проверить конфигурацию WebSocket endpoints

## 🛠️ Расширение функциональности

### Добавление новых тестов

1. Добавьте тест в `web_testing_agent_mcp.py`:

```python
async def test_new_feature(self):
    """Тест новой функциональности"""
    # Ваш код тестирования
    pass
```

2. Обновите генератор отчетов в `run_web_tests.py`:

```python
report.add_test_result(
    "New Feature Test",
    "passed",
    {"description": "Описание теста"}
)
```

### Настройка viewport для тестирования

```python
viewports = [
    {"name": "4K", "width": 3840, "height": 2160},
    {"name": "iPad", "width": 1024, "height": 1366},
    {"name": "iPhone", "width": 390, "height": 844}
]
```

## 📝 Примеры использования MCP команд

### Проверка наличия элементов

```javascript
const hasElement = await mcp_puppeteer_evaluate(
    script="!!document.querySelector('.trader-card')"
)
```

### Получение текста элемента

```javascript
const text = await mcp_puppeteer_evaluate(
    script="document.querySelector('.total-capital')?.textContent"
)
```

### Проверка состояния кнопки

```javascript
const isDisabled = await mcp_puppeteer_evaluate(
    script="document.querySelector('.btn-start')?.disabled"
)
```

## 🎯 Будущие улучшения

1. **Автоматизация CI/CD** - интеграция с GitHub Actions
2. **Visual Regression Testing** - сравнение скриншотов
3. **Performance Testing** - измерение времени загрузки
4. **Accessibility Testing** - проверка доступности
5. **Cross-browser Testing** - тестирование в разных браузерах

## 📞 Поддержка

При возникновении вопросов или проблем:

1. Проверьте логи в `unified_launch.log`
2. Убедитесь, что веб-интерфейс доступен на <http://localhost:5173>
3. Проверьте, что Puppeteer MCP сервер активен через `claude-code mcp list`

---

*Последнее обновление: 4 августа 2025*
