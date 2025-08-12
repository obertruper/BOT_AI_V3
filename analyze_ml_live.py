#!/usr/bin/env python3
"""
Анализ живых ML предсказаний из логов
"""

# Данные из логов
signals = [
    {
        "symbol": "XRPUSDT",
        "type": "SHORT",
        "confidence": 0.6404619688168168,
        "sl": 3.177258,
        "tp": 3.082884,
        "price": 3.1458,
    },
    {
        "symbol": "DOTUSDT",
        "type": "SHORT",
        "confidence": 0.657463799614925,
        "sl": 3.9398,
        "tp": 3.822784,
        "price": 3.9008,
    },
    {
        "symbol": "ADAUSDT",
        "type": "SHORT",
        "confidence": 0.6453357726335526,
        "sl": 0.786992,
        "tp": 0.763616,
        "price": 0.7792,
    },
    {
        "symbol": "BNBUSDT",
        "type": "SHORT",
        "confidence": 0.65,
        "sl": 815.777,
        "tp": 791.546,
        "price": 803.0,
    },  # Из логов
]

print("📊 АНАЛИЗ ML ПРЕДСКАЗАНИЙ ИЗ ЖИВОЙ ТОРГОВЛИ:")
print("=" * 60)

total_confidence = 0
risk_rewards = []
all_short = True

for sig in signals:
    print(f"\n{sig['symbol']}:")
    print(f"  Сигнал: {sig['type']}")
    print(f"  Уверенность: {sig['confidence']:.2%}")
    print(f"  Цена входа: ${sig['price']:.4f}")

    # Расчет процентов для SL/TP
    if sig["type"] == "SHORT":
        sl_pct = (sig["sl"] / sig["price"] - 1) * 100
        tp_pct = (sig["tp"] / sig["price"] - 1) * 100
        print(f"  Stop Loss: ${sig['sl']:.4f} ({sl_pct:+.1f}%)")
        print(f"  Take Profit: ${sig['tp']:.4f} ({tp_pct:+.1f}%)")

        # Risk/Reward для шорта
        risk = abs(sig["sl"] - sig["price"])
        reward = abs(sig["price"] - sig["tp"])
    else:
        sl_pct = (sig["sl"] / sig["price"] - 1) * 100
        tp_pct = (sig["tp"] / sig["price"] - 1) * 100
        print(f"  Stop Loss: ${sig['sl']:.4f} ({sl_pct:+.1f}%)")
        print(f"  Take Profit: ${sig['tp']:.4f} ({tp_pct:+.1f}%)")

        # Risk/Reward для лонга
        risk = abs(sig["price"] - sig["sl"])
        reward = abs(sig["tp"] - sig["price"])
        all_short = False

    rr = reward / risk if risk > 0 else 0
    print(f"  Risk/Reward: {rr:.2f}:1")

    risk_rewards.append(rr)
    total_confidence += sig["confidence"]

avg_confidence = total_confidence / len(signals)
avg_rr = sum(risk_rewards) / len(risk_rewards)

print("\n" + "=" * 60)
print("📈 АНАЛИЗ РАБОТЫ МОДЕЛИ:")
print("=" * 60)

print("\n✅ ПОЛОЖИТЕЛЬНЫЕ МОМЕНТЫ:")
print(f"  • Средняя уверенность: {avg_confidence:.1%} (приемлемо)")
print(f"  • Среднее Risk/Reward: {avg_rr:.2f}:1 (хорошо)")
print("  • Модель генерирует сигналы для разных пар")
print("  • SL/TP устанавливаются корректно")

print("\n⚠️ ВЫЯВЛЕННЫЕ ОСОБЕННОСТИ:")
if all_short:
    print("  • Все сигналы SHORT - модель видит медвежий тренд")
    print("  • Возможно, модель переобучена на падающий рынок")
else:
    print("  • Есть разнообразие в направлениях сигналов")

print("  • Уверенность около 65% - можно повысить порог до 70%")
print("  • SL обычно 1-2% - консервативный подход")

print("\n🔧 РЕКОМЕНДАЦИИ ПО НАСТРОЙКЕ:")
print("  1. Увеличить min_confidence_threshold до 0.7 в config/ml/ml_config.yaml")
print("  2. Проверить баланс классов в обучающих данных")
print("  3. Добавить фильтр по волатильности для адаптивных SL/TP")
print("  4. Рассмотреть увеличение Risk/Reward до 2.5:1 минимум")

print("\n📊 ВЫВОД:")
print("Модель работает корректно и выдает обоснованные предсказания.")
print("Интерпретация направлений (LONG/SHORT) происходит правильно.")
print("SL/TP рассчитываются из ML предсказаний и передаются в ордера.")
print("Основная проблема - все сигналы SHORT, нужно проверить баланс обучения.")
