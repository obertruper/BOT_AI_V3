# 🎨 BOT Trading v3 - Web Interface

Современный веб-интерфейс для управления криптовалютными торговыми ботами.

## 🚀 Возможности

### Dashboard (Главная панель)

- Обзор всех активных трейдеров
- Общий капитал и P&L
- Системные метрики (CPU, память)
- Real-time обновления через WebSocket

### Traders (Управление трейдерами)

- Создание новых трейдеров
- Настройка стратегий
- Управление рисками
- Включение/выключение трейдеров

### Positions (Позиции)

- Текущие открытые позиции
- Нереализованный P&L
- Управление SL/TP
- История закрытых позиций

### Orders (Ордера)

- Активные ордера
- История исполненных ордеров
- Отмена ордеров
- Создание новых ордеров

### Analytics (Аналитика)

- Графики производительности
- Статистика по трейдерам
- Анализ рисков
- Экспорт отчетов

### Settings (Настройки)

- Настройки API ключей
- Управление биржами
- Системные настройки
- Уведомления

## 🛠️ Технологический стек

- **React 18** - современный UI фреймворк
- **TypeScript** - типизация
- **Vite** - быстрая сборка
- **Tailwind CSS** - стилизация
- **Zustand** - state management
- **React Query** - управление серверным состоянием
- **Recharts** - графики и визуализация
- **WebSocket** - real-time обновления

## 📦 Установка и запуск

### 1. Установка зависимостей

```bash
cd web/frontend
npm install
```

### 2. Запуск в режиме разработки

```bash
npm run dev
```

Интерфейс будет доступен по адресу: <http://localhost:5173>

### 3. Сборка для production

```bash
npm run build
```

### 4. Предпросмотр production сборки

```bash
npm run preview
```

## ⚙️ Конфигурация

### API настройки

Отредактируйте файл `src/api/client.ts`:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws';
```

### Переменные окружения

Создайте файл `.env.local`:

```env
VITE_API_URL=http://localhost:8080/api
VITE_WS_URL=ws://localhost:8080/ws
```

## 🎨 UI компоненты

### Базовые компоненты (Radix UI)

- Button
- Card
- Dialog
- Dropdown Menu
- Select
- Switch
- Tabs
- Toast
- Tooltip

### Кастомные компоненты

- TradingChart - графики торговли
- PositionCard - карточка позиции
- TraderCard - карточка трейдера
- MetricCard - карточка метрики

## 📱 Адаптивность

Интерфейс полностью адаптивен и поддерживает:

- 📱 Мобильные устройства
- 📋 Планшеты
- 💻 Десктопы
- 🖥️ Широкие экраны

## 🔄 Real-time обновления

WebSocket подключение обеспечивает:

- Обновления позиций в реальном времени
- Статус трейдеров
- Системные метрики
- Уведомления о сделках

## 🎯 Использование

### Первый запуск

1. Запустите backend:

   ```bash
   python main.py
   python web/launcher.py
   ```

2. Запустите frontend:

   ```bash
   cd web/frontend
   npm run dev
   ```

3. Откройте <http://localhost:5173>

### Создание трейдера

1. Перейдите в раздел "Traders"
2. Нажмите "Create New Trader"
3. Заполните форму:
   - Имя трейдера
   - Биржа
   - Торговая пара
   - Стратегия
   - Параметры риска
4. Нажмите "Create"

### Мониторинг

Dashboard автоматически обновляется каждые 5 секунд или в реальном времени через WebSocket.

## 🐛 Известные проблемы

1. При первом запуске может потребоваться обновить страницу
2. WebSocket reconnect может занять до 5 секунд
3. В mock режиме некоторые функции недоступны

## 🚀 Roadmap

- [ ] Dark/Light theme toggle
- [ ] Multi-language support
- [ ] Mobile app (React Native)
- [ ] Advanced charting (TradingView)
- [ ] Backtesting UI
- [ ] Strategy builder
- [ ] Social trading features

## 📝 Лицензия

MIT License

---

Разработано с ❤️ для BOT Trading v3
