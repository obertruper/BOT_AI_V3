# Оптимальные параметры для стратегий фильтрации ML сигналов

## 📋 Рекомендуемая конфигурация для production

Основываясь на анализе и тестировании, рекомендуются следующие параметры для `config/ml/ml_config.yaml`:

```yaml
signal_filtering:
  # Активная стратегия по умолчанию (рекомендуется moderate)
  strategy: "moderate"
  
  # Веса таймфреймов [15m, 1h, 4h, 12h] - 4h основной для средне-срочной торговли
  timeframe_weights: [0.25, 0.25, 0.35, 0.15]
  main_timeframe_index: 2  # 4h - основной таймфрейм
  
  # КОНСЕРВАТИВНАЯ СТРАТЕГИЯ - для волатильных рынков
  # Ожидаемая доходность: 10-15% сигналов высочайшего качества
  conservative:
    min_timeframe_agreement: 3              # 3 из 4 ТФ должны согласиться
    required_confidence_per_timeframe: 0.62  # Понижено с 0.65 для реальности
    main_timeframe_required_confidence: 0.68 # Понижено с 0.70
    min_expected_return_pct: 0.007          # Понижено с 0.008 (0.7%)
    min_signal_strength: 0.65               # Понижено с 0.7
    max_risk_level: "MEDIUM"
    min_quality_score: 0.70                 # Понижено с 0.75
    
  # УМЕРЕННАЯ СТРАТЕГИЯ - основная для большинства случаев  
  # Ожидаемая доходность: 25-35% сигналов хорошего качества
  moderate:
    min_timeframe_agreement: 2              # 2 из 4 ТФ
    required_confidence_per_timeframe: 0.52  # Понижено с 0.55
    main_timeframe_required_confidence: 0.62 # Понижено с 0.65
    alternative_main_plus_one: true         # Альтернативный режим
    alternative_confidence_threshold: 0.72   # Понижено с 0.75
    min_expected_return_pct: 0.004          # Понижено с 0.005 (0.4%)
    min_signal_strength: 0.45               # Понижено с 0.5
    max_risk_level: "HIGH"
    min_quality_score: 0.55                 # Понижено с 0.60
    
  # АГРЕССИВНАЯ СТРАТЕГИЯ - для бокового рынка и скальпинга
  # Ожидаемая доходность: 45-60% сигналов приемлемого качества
  aggressive:
    min_timeframe_agreement: 1              # Достаточно основного ТФ
    required_confidence_per_timeframe: 0.42  # Понижено с 0.45
    main_timeframe_required_confidence: 0.52 # Понижено с 0.55
    min_expected_return_pct: 0.002          # Понижено с 0.003 (0.2%)
    min_signal_strength: 0.35               # Понижено с 0.4
    max_risk_level: "HIGH"
    min_quality_score: 0.40                 # Понижено с 0.45
    
  # Веса для расчета итогового качества сигнала (оптимизированы)
  quality_weights:
    agreement: 0.30        # Уменьшено с 0.35 - согласованность важна, но не критична
    confidence: 0.35       # Увеличено с 0.30 - уверенность модели приоритетна
    return_expectation: 0.25  # Увеличено с 0.20 - доходность критически важна
    risk_adjustment: 0.10  # Уменьшено с 0.15 - риск менее важен при хорошем R/R
    
  # Настройки логирования
  logging:
    log_rejection_reasons: true    # Всегда включено для диагностики
    log_quality_metrics: true      # Детальные метрики
    log_strategy_stats: false      # Отключить в production для производительности
```

## 🎯 Рекомендации по использованию стратегий

### 📈 Выбор стратегии по рыночным условиям

| Условия рынка | Рекомендуемая стратегия | Обоснование |
|---------------|------------------------|-------------|
| **Высокая волатильность (VIX >25)** | Conservative | Строгие фильтры, минимум ложных сигналов |
| **Нормальная волатильность (VIX 15-25)** | Moderate | Сбалансированный подход, оптимальное R/R |
| **Низкая волатильность (VIX <15)** | Aggressive | Максимальное покрытие возможностей |
| **Боковой тренд** | Aggressive | Больше возможностей для коротких движений |
| **Сильный тренд** | Conservative | Фокус на качественные сигналы по тренду |

### ⏰ Выбор стратегии по времени торговли

| Время торговли | Стратегия | Причина |
|----------------|-----------|---------|
| **Азиатская сессия** (22:00-08:00 UTC) | Aggressive | Низкая волатильность, скальпинг |
| **Европейская сессия** (07:00-16:00 UTC) | Moderate | Умеренная активность |
| **Американская сессия** (13:00-22:00 UTC) | Conservative | Высокая волатильность |
| **Новости/события** | Conservative | Непредсказуемость, нужна осторожность |

### 💰 Размер позиции по стратегии

```yaml
# Рекомендуемые размеры позиций
position_sizing:
  conservative:
    base_position_size: 1.0    # 100% от стандартного размера
    max_concurrent_positions: 3 # Максимум одновременных позиций
    
  moderate:
    base_position_size: 0.8    # 80% от стандартного размера  
    max_concurrent_positions: 5
    
  aggressive:
    base_position_size: 0.6    # 60% от стандартного размера
    max_concurrent_positions: 8
```

## 🔧 Программное управление стратегиями

### Автоматическое переключение стратегий

```python
import asyncio
from datetime import datetime, time

class StrategyScheduler:
    def __init__(self, ml_manager):
        self.ml_manager = ml_manager
    
    async def auto_switch_by_time(self):
        """Автоматическое переключение по времени суток"""
        current_time = datetime.utcnow().time()
        
        # Азиатская сессия - агрессивная
        if time(22, 0) <= current_time or current_time <= time(8, 0):
            await self.ml_manager.switch_filtering_strategy("aggressive")
            
        # Европейская сессия - умеренная  
        elif time(7, 0) <= current_time <= time(16, 0):
            await self.ml_manager.switch_filtering_strategy("moderate")
            
        # Американская сессия - консервативная
        elif time(13, 0) <= current_time <= time(22, 0):
            await self.ml_manager.switch_filtering_strategy("conservative")
    
    async def auto_switch_by_volatility(self, vix_level: float):
        """Переключение по уровню волатильности"""
        if vix_level > 25:
            await self.ml_manager.switch_filtering_strategy("conservative")
        elif vix_level > 15:
            await self.ml_manager.switch_filtering_strategy("moderate")
        else:
            await self.ml_manager.switch_filtering_strategy("aggressive")
```

### Мониторинг эффективности

```python
async def monitor_strategy_performance(ml_manager, interval_hours=24):
    """Мониторинг эффективности стратегии"""
    
    while True:
        stats = ml_manager.get_filtering_statistics()
        
        # Проверяем метрики эффективности
        pass_rate = float(stats['pass_rate'].rstrip('%')) / 100
        
        # Предупреждения
        if pass_rate < 0.05:  # Менее 5% сигналов проходят
            logger.warning("🚨 Слишком строгие фильтры - рассмотрите смягчение")
            
        elif pass_rate > 0.80:  # Более 80% сигналов проходят  
            logger.warning("⚠️ Слишком мягкие фильтры - рассмотрите ужесточение")
            
        else:
            logger.info(f"✅ Фильтрация работает нормально: {stats['pass_rate']} сигналов проходят")
        
        # Логируем топ причины отклонения
        if stats.get('top_rejection_reasons'):
            logger.info("📊 Топ причины отклонения:")
            for reason, count in stats['top_rejection_reasons'].items():
                logger.info(f"   {reason}: {count}")
        
        await asyncio.sleep(interval_hours * 3600)
```

## 📊 Метрики для мониторинга

### Ключевые показатели (KPI)

1. **Pass Rate (Процент прохождения)**: 15-40% в зависимости от стратегии
2. **Quality Distribution**: Распределение качества принятых сигналов
3. **Top Rejection Reasons**: Основные причины отклонения для оптимизации
4. **Strategy Switch Frequency**: Частота переключения стратегий

### Алерты для настройки

```python
# Критические алерты
if pass_rate < 0.03:  # <3%
    alert = "CRITICAL: Слишком строгие фильтры, торговля практически остановлена"
    
elif pass_rate > 0.90:  # >90%
    alert = "CRITICAL: Фильтры не работают, пропускают некачественные сигналы"
    
elif quality_distribution['low'] > 0.60:  # >60% низкого качества
    alert = "WARNING: Много сигналов низкого качества, проверьте пороги"
```

## 🚀 Внедрение в production

### Поэтапный план внедрения

1. **Фаза 1 (1-2 недели)**: Тестирование на demo счете
   - Запуск с moderate стратегией
   - Мониторинг всех метрик
   - Сбор статистики по причинам отклонения

2. **Фаза 2 (1 неделя)**: A/B тестирование стратегий  
   - Параллельное тестирование всех 3 стратегий
   - Сравнение производительности
   - Корректировка параметров

3. **Фаза 3 (ongoing)**: Production deployment
   - Запуск на реальном счете с умеренной стратегией
   - Автоматическое переключение по условиям
   - Continuous monitoring и оптимизация

### Checklist перед запуском

- [ ] Конфигурация загружена и протестирована
- [ ] Логирование настроено и работает  
- [ ] Метрики мониторинга настроены
- [ ] Алерты настроены для критических ситуаций
- [ ] Бэкап старой логики сохранен
- [ ] Тестирование на исторических данных проведено
- [ ] Документация обновлена

Эта конфигурация обеспечит оптимальный баланс между качеством сигналов и их количеством для различных рыночных условий.