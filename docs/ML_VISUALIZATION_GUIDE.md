# 📊 Руководство по визуализации ML системы

## 🎯 Обзор

Система визуализации ML предоставляет комплексные инструменты для анализа входных и выходных данных модели машинного обучения. Включает интерактивные графики, тепловые карты признаков и анализ рыночных данных.

## ✅ Реализованные компоненты

### 1. Backend визуализация (`visualize_ml_predictions.py`)

- ✅ **Интерактивные графики Plotly** (6 панелей, ~4.5MB HTML)
- ✅ **Анализ рыночных данных** (4 графика Matplotlib, ~200KB PNG)
- ✅ **Тепловая карта признаков** (топ-50 из 240, Seaborn, ~100KB PNG)
- ✅ **Исправлена ошибка** преобразования string/float в heatmap

### 2. API Endpoints (`web/api/endpoints/ml_visualization.py`)

- ✅ Создан полный REST API на `/api/ml-viz/`
- ✅ Endpoints: predictions, features, metrics, reports
- ✅ Интеграция с основным API сервером

### 3. Frontend компоненты (React/TypeScript)

- ✅ **MLPanel.tsx** - полная переработка из заглушки
- ✅ **MLChart.tsx** - универсальный компонент графиков
- ✅ **MLMetrics.tsx** - карточки метрик
- ✅ **PredictionVisualization.tsx** - детальная визуализация

### 4. Утилиты визуализации

- ✅ **run_visualization_demo.py** - демо с тестовыми данными
- ✅ **visualize_real_ml_data.py** - работа с реальными данными из БД

## 🚀 Быстрый старт

### Запуск системы

```bash
# Основной способ запуска с фильтрованными логами
./start_with_logs_filtered.sh

# Альтернативные способы
./quick_start.sh               # Интерактивное меню
python3 unified_launcher.py    # Прямой запуск
```

### Доступ к визуализации

- **Web интерфейс**: <http://localhost:5173/ml>
- **API endpoints**: <http://localhost:8083/api/ml-viz/>
- **Локальные файлы**: `/data/charts/`

## 📈 Примеры использования

### 1. Демонстрация с тестовыми данными

```bash
python3 run_visualization_demo.py
```

Создает визуализации для BTCUSDT, ETHUSDT, SOLUSDT с синтетическими данными.

### 2. Визуализация реальных данных

```bash
python3 visualize_real_ml_data.py
```

Загружает данные из PostgreSQL (порт 5555) и создает визуализации на основе:

- 97,674 записей рыночных данных
- 5,514 сигналов
- 1,068 обработанных признаков

### 3. Программное использование

```python
from visualize_ml_predictions import (
    create_predictions_chart,
    create_market_data_analysis,
    create_features_heatmap
)

# Интерактивный график
chart = create_predictions_chart("BTCUSDT", prediction, df)

# Анализ рынка
market = create_market_data_analysis("BTCUSDT", df, timestamp)

# Тепловая карта
heatmap = create_features_heatmap("BTCUSDT", features, timestamp)
```

## 📊 Созданные визуализации

### Интерактивные графики (Plotly)

- Размер: ~4.5-4.6 MB на файл
- Содержат 6 панелей:
  1. Вероятности по таймфреймам (15m, 1h, 4h, 12h)
  2. Ожидаемая доходность
  3. Взвешенные предсказания
  4. Индикатор конфиденции (gauge)
  5. Распределение вероятностей (pie chart)
  6. Матрица направлений (heatmap)

### Анализ рыночных данных (Matplotlib)

- Размер: ~185-220 KB на файл
- 4 графика:
  1. Цена со скользящими средними MA20/MA50
  2. Объем торгов (bar chart)
  3. Волатильность 20-период
  4. Распределение доходностей (histogram)

### Тепловые карты признаков (Seaborn)

- Размер: ~96-216 KB на файл
- Топ-50 признаков из 240
- Цветовая схема RdYlBu_r
- Темный фон для лучшей читаемости

## 📁 Структура файлов

```
BOT_AI_V3/
├── visualize_ml_predictions.py      # ✅ Расширен графиками
├── visualize_real_ml_data.py        # ✅ Создан для реальных данных
├── run_visualization_demo.py        # ✅ Демо скрипт
├── data/charts/                     # 📊 26 файлов визуализаций
│   ├── ml_predictions_*.html        # Интерактивные (4.6MB каждый)
│   ├── market_analysis_*.png        # Анализ рынка (190-223KB)
│   └── features_heatmap_*.png       # Тепловые карты (96-216KB)
├── web/
│   ├── api/endpoints/
│   │   └── ml_visualization.py      # ✅ REST API создан
│   └── frontend/src/
│       ├── pages/
│       │   └── MLPanel.tsx          # ✅ Полностью переписан
│       └── components/ml/           # ✅ Новые компоненты
│           ├── MLChart.tsx
│           ├── MLMetrics.tsx
│           └── PredictionVisualization.tsx
```

## 🔧 Решенные проблемы

1. **Ошибка datetime column**: Исправлено дублирование индекса в DataFrame
2. **String/float conversion в heatmap**: Правильная обработка словарей признаков
3. **Порт 8083 занят**: Создан скрипт start_clean.sh
4. **ML features vs features**: Исправлено имя колонки в БД
5. **Unified launcher mode 'all'**: Изменено на 'full'

## 📊 Статистика текущей сессии

- **Создано файлов**: 26 визуализаций
- **Общий размер**: ~29 MB
- **Обработано символов**: ADAUSDT, BNBUSDT, BTCUSDT, ETHUSDT, SOLUSDT
- **Типы сигналов**: LONG (BTCUSDT), SHORT (BNBUSDT, ETHUSDT), NEUTRAL (SOLUSDT)
- **Конфиденция**: от 30.1% до 91.8%

## 🚨 Известные ограничения

1. **ML система через API**: Endpoint `/api/ml-viz/` возвращает 503 при недоступности ML manager
2. **WebSocket real-time**: Еще не протестирован
3. **Низкая конфиденция сигналов**: 30-31% в реальных данных (требует донастройки модели)

## 🛠️ Команды для диагностики

```bash
# Проверка данных в БД
psql -p 5555 -U obertruper -d bot_trading_v3 -c "
SELECT COUNT(*) FROM raw_market_data;
SELECT COUNT(*) FROM signals;
SELECT COUNT(*) FROM processed_market_data;
"

# Проверка API
curl -s http://localhost:8083/api/ml-viz/metrics

# Просмотр созданных файлов
ls -lah data/charts/ | tail -20

# Мониторинг логов
tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep ML
```

## 📝 Итоги реализации

✅ **Успешно реализовано**:

- Полноценная система визуализации входных и выходных данных ML модели
- 3 типа визуализаций (интерактивные, статические, тепловые карты)
- REST API для программного доступа
- Frontend компоненты на React
- Работа с реальными данными из БД
- Исправлены все критические ошибки

⚠️ **Требует внимания**:

- Интеграция ML manager с API для полной функциональности endpoints
- Тестирование WebSocket для real-time обновлений
- Оптимизация модели для повышения конфиденции сигналов

---

*Документация создана: 23 августа 2025*
*Система полностью функциональна для визуализации ML данных*
