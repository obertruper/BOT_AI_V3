#!/usr/bin/env python3
"""
Детальное логирование сигналов с техническими индикаторами
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class SignalDetailsLogger:
    """Класс для детального логирования торговых сигналов"""

    @staticmethod
    def log_signal_details(
        symbol: str, signal_data: dict[str, Any], market_data: pd.DataFrame = None
    ):
        """
        Логирование детальной информации о сигнале

        Args:
            symbol: Символ торговой пары
            signal_data: Данные сигнала от ML модели
            market_data: DataFrame с рыночными данными и индикаторами
        """

        # Извлекаем основные параметры
        signal_type = signal_data.get("signal_type", "NEUTRAL")
        signal_strength = signal_data.get("signal_strength", 0)
        confidence = signal_data.get("confidence", 0)

        # Извлекаем предсказания по таймфреймам
        returns_15m = signal_data.get("returns_15m", 0)
        returns_1h = signal_data.get("returns_1h", 0)
        returns_4h = signal_data.get("returns_4h", 0)
        returns_12h = signal_data.get("returns_12h", 0)

        # Извлекаем направления
        dir_15m = signal_data.get("direction_15m", "NEUTRAL")
        dir_1h = signal_data.get("direction_1h", "NEUTRAL")
        dir_4h = signal_data.get("direction_4h", "NEUTRAL")
        dir_12h = signal_data.get("direction_12h", "NEUTRAL")

        # Извлекаем уверенности
        conf_15m = signal_data.get("confidence_15m", 0)
        conf_1h = signal_data.get("confidence_1h", 0)
        conf_4h = signal_data.get("confidence_4h", 0)
        conf_12h = signal_data.get("confidence_12h", 0)

        # Извлекаем технические индикаторы из последней строки market_data
        tech_indicators = {}
        if market_data is not None and not market_data.empty:
            last_row = market_data.iloc[-1]

            # Основные индикаторы
            tech_indicators = {
                "RSI": last_row.get("rsi_14", 0),
                "MACD": last_row.get("macd", 0),
                "MACD_Signal": last_row.get("macd_signal", 0),
                "BB_Upper": last_row.get("bb_upper", 0),
                "BB_Lower": last_row.get("bb_lower", 0),
                "BB_Position": last_row.get("bb_position", 0),
                "SMA_20": last_row.get("sma_20", 0),
                "SMA_50": last_row.get("sma_50", 0),
                "EMA_12": last_row.get("ema_12", 0),
                "EMA_26": last_row.get("ema_26", 0),
                "ATR": last_row.get("atr_14", 0),
                "Volume": last_row.get("volume", 0),
                "Volume_SMA": last_row.get("volume_sma_20", 0),
                "Price": last_row.get("close", 0),
            }

        # Формируем детальный лог
        signal_emoji = "🟢" if signal_type == "LONG" else "🔴" if signal_type == "SHORT" else "⚪"

        log_message = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       📊 ДЕТАЛЬНЫЙ АНАЛИЗ СИГНАЛА {symbol:<10s}             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ {signal_emoji} СИГНАЛ: {signal_type:<8s} | Сила: {signal_strength:.2f} | Уверенность: {confidence:.2%}      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ 📈 ПРЕДСКАЗАНИЯ ПО ТАЙМФРЕЙМАМ:                                              ║
║   15m: {dir_15m:<8s} | Доход: {returns_15m:+.4f} | Уверенность: {conf_15m:.2%}         ║
║   1h:  {dir_1h:<8s} | Доход: {returns_1h:+.4f} | Уверенность: {conf_1h:.2%}          ║
║   4h:  {dir_4h:<8s} | Доход: {returns_4h:+.4f} | Уверенность: {conf_4h:.2%}          ║
║   12h: {dir_12h:<8s} | Доход: {returns_12h:+.4f} | Уверенность: {conf_12h:.2%}         ║
╠══════════════════════════════════════════════════════════════════════════════╣"""

        if tech_indicators:
            log_message += f"""
║ 📊 ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ:                                                   ║
║   • RSI(14):        {tech_indicators.get('RSI', 0):>6.2f}  {'🔴 Перепродан' if tech_indicators.get('RSI', 50) < 30 else '🟢 Перекуплен' if tech_indicators.get('RSI', 50) > 70 else '⚪ Нейтрально'}        ║
║   • MACD:           {tech_indicators.get('MACD', 0):>6.4f}  {'🟢 Бычий' if tech_indicators.get('MACD', 0) > tech_indicators.get('MACD_Signal', 0) else '🔴 Медвежий'}              ║
║   • BB Position:    {tech_indicators.get('BB_Position', 0):>6.2f}  {'🔴 У нижней' if tech_indicators.get('BB_Position', 0) < -2 else '🟢 У верхней' if tech_indicators.get('BB_Position', 0) > 2 else '⚪ В канале'}         ║
║   • ATR(14):        {tech_indicators.get('ATR', 0):>6.4f}  {'⚡ Высокая волатильность' if tech_indicators.get('ATR', 0) > tech_indicators.get('Price', 1) * 0.02 else '😴 Низкая волатильность'}   ║
║   • Volume Ratio:   {(tech_indicators.get('Volume', 0) / max(tech_indicators.get('Volume_SMA', 1), 1)):>6.2f}x  {'📈 Повышенный' if tech_indicators.get('Volume', 0) > tech_indicators.get('Volume_SMA', 0) * 1.5 else '📉 Пониженный'}          ║"""

        # Добавляем рекомендации
        sl_pct = signal_data.get("stop_loss_pct", 0)
        tp_pct = signal_data.get("take_profit_pct", 0)
        risk_level = signal_data.get("risk_level", "UNKNOWN")
        quality_score = signal_data.get("quality_score", 0)

        log_message += f"""
╠══════════════════════════════════════════════════════════════════════════════╣
║ 🎯 РЕКОМЕНДАЦИИ:                                                             ║
║   • Stop Loss:      {sl_pct*100 if sl_pct else 0:>5.2f}%                                                     ║
║   • Take Profit:    {tp_pct*100 if tp_pct else 0:>5.2f}%                                                     ║
║   • Риск:           {risk_level:<10s}                                            ║
║   • Качество:       {quality_score:.2%}                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⚙️ ФИЛЬТРЫ КАЧЕСТВА:                                                         ║
║   • Стратегия:      {signal_data.get('filter_strategy', 'moderate'):<12s}                                      ║
║   • Пройдено:       {'✅ ДА' if signal_data.get('passed_quality_filters', False) else '❌ НЕТ'}                                                 ║"""

        if not signal_data.get("passed_quality_filters", False):
            reasons = signal_data.get("rejection_reasons", [])
            if reasons:
                log_message += f"""
║   • Причины отказа: {'; '.join(reasons[:2]):<50s}  ║"""

        log_message += """
╚══════════════════════════════════════════════════════════════════════════════╝"""

        logger.info(log_message)

        # Краткий лог для быстрого просмотра
        brief_log = f"📊 {symbol} | {signal_emoji} {signal_type} | Сила: {signal_strength:.2f} | Уверенность: {confidence:.2%}"
        if tech_indicators:
            brief_log += f" | RSI: {tech_indicators.get('RSI', 0):.1f} | MACD: {'🟢' if tech_indicators.get('MACD', 0) > tech_indicators.get('MACD_Signal', 0) else '🔴'}"

        logger.info(brief_log)

        return log_message


# Глобальный экземпляр логгера сигналов
signal_logger = SignalDetailsLogger()
