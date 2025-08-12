#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SL/TP Logger для детального отслеживания операций со стоп-лоссами и тейк-профитами
"""

from datetime import datetime
from typing import Dict, List

from core.logging.trade_logger import get_trade_logger


class SLTPLogger:
    """Детальное логирование всех операций SL/TP"""

    def __init__(self):
        self.trade_logger = get_trade_logger()

    def log_sltp_calculation(self, position: Dict, sl_config: Dict, tp_config: Dict):
        """Логирование расчета SL/TP"""
        log_data = {
            "symbol": position.get("symbol"),
            "side": position.get("side"),
            "entry_price": str(position.get("entry_price", 0)),
            "sl_config": {
                "percent": sl_config.get("percent"),
                "price": str(sl_config.get("price", 0)),
                "distance_points": str(sl_config.get("distance", 0)),
            },
            "tp_config": {
                "percent": tp_config.get("percent"),
                "price": str(tp_config.get("price", 0)),
                "risk_reward": tp_config.get("risk_reward_ratio"),
            },
            "timestamp": datetime.now().isoformat(),
        }

        self.trade_logger.logger.info(
            f"📐 РАСЧЕТ SL/TP: {position.get('symbol')} | "
            f"Entry: {position.get('entry_price')} | "
            f"SL: {sl_config.get('price')} (-{sl_config.get('percent')}%) | "
            f"TP: {tp_config.get('price')} (+{tp_config.get('percent')}%)",
            **log_data,
        )
        self.trade_logger._log_to_file("info", "SLTP_CALCULATION", log_data)

    def log_partial_tp_setup(self, position_id: str, levels: List[Dict]):
        """Логирование настройки частичных TP"""
        log_data = {
            "position_id": position_id,
            "levels_count": len(levels),
            "levels": [],
            "timestamp": datetime.now().isoformat(),
        }

        for i, level in enumerate(levels, 1):
            level_data = {
                "level": i,
                "price": str(level.get("price", 0)),
                "percent": level.get("percent"),
                "close_ratio": level.get("close_ratio"),
                "quantity": str(level.get("quantity", 0)),
            }
            log_data["levels"].append(level_data)

            self.trade_logger.logger.info(
                f"   📊 TP{i}: {level.get('price')} (+{level.get('percent')}%) "
                f"→ закрыть {level.get('close_ratio') * 100}% ({level.get('quantity')})"
            )

        self.trade_logger._log_to_file("info", "PARTIAL_TP_SETUP", log_data)

    def log_partial_tp_execution(
        self,
        position_id: str,
        level: int,
        executed_qty: float,
        executed_price: float,
        remaining_qty: float,
    ):
        """Логирование исполнения частичного TP"""
        log_data = {
            "position_id": position_id,
            "level": level,
            "executed_qty": str(executed_qty),
            "executed_price": str(executed_price),
            "remaining_qty": str(remaining_qty),
            "timestamp": datetime.now().isoformat(),
        }

        self.trade_logger.logger.info(
            f"✅ ЧАСТИЧНЫЙ TP{level} ИСПОЛНЕН: "
            f"Закрыто {executed_qty} @ {executed_price} | "
            f"Осталось: {remaining_qty}",
            **log_data,
        )
        self.trade_logger._log_to_file("info", "PARTIAL_TP_EXECUTED", log_data)

    def log_sl_adjustment(
        self,
        position_id: str,
        reason: str,
        old_sl: float,
        new_sl: float,
        entry_price: float,
    ):
        """Логирование корректировки SL"""
        log_data = {
            "position_id": position_id,
            "reason": reason,
            "old_sl": str(old_sl),
            "new_sl": str(new_sl),
            "entry_price": str(entry_price),
            "improvement": str(new_sl - old_sl) if new_sl > old_sl else str(0),
            "timestamp": datetime.now().isoformat(),
        }

        # Определяем тип корректировки
        if new_sl == entry_price:
            adjustment_type = "БЕЗУБЫТОК"
            emoji = "🔒"
        elif new_sl > entry_price:
            adjustment_type = "ЗАЩИТА ПРИБЫЛИ"
            emoji = "💰"
        elif new_sl > old_sl:
            adjustment_type = "УЛУЧШЕНИЕ"
            emoji = "📈"
        else:
            adjustment_type = "КОРРЕКТИРОВКА"
            emoji = "📝"

        self.trade_logger.logger.info(
            f"{emoji} SL {adjustment_type}: {old_sl} → {new_sl} | {reason}", **log_data
        )
        self.trade_logger._log_to_file("info", "SL_ADJUSTMENT", log_data)

    def log_trailing_stop_state(self, position_id: str, state: Dict):
        """Логирование состояния trailing stop"""
        log_data = {
            "position_id": position_id,
            "activated": state.get("activated", False),
            "current_price": str(state.get("current_price", 0)),
            "entry_price": str(state.get("entry_price", 0)),
            "current_sl": str(state.get("current_sl", 0)),
            "highest_price": str(state.get("highest_price", 0)),
            "profit_percent": state.get("profit_percent", 0),
            "updates_count": state.get("updates_count", 0),
            "timestamp": datetime.now().isoformat(),
        }

        if state.get("activated"):
            self.trade_logger.logger.debug(
                f"📊 TRAILING STATE: Активен | "
                f"Цена: {state.get('current_price')} | "
                f"SL: {state.get('current_sl')} | "
                f"Макс: {state.get('highest_price')} | "
                f"Обновлений: {state.get('updates_count')}",
                **log_data,
            )

        # В файл пишем реже, только значимые изменения
        if state.get("updates_count", 0) % 5 == 0:  # Каждое 5-е обновление
            self.trade_logger._log_to_file("debug", "TRAILING_STOP_STATE", log_data)

    def log_profit_protection(self, position_id: str, protection_level: Dict):
        """Логирование защиты прибыли"""
        log_data = {
            "position_id": position_id,
            "profit_percent": protection_level.get("profit_percent"),
            "locked_profit": protection_level.get("locked_profit"),
            "new_sl": str(protection_level.get("new_sl", 0)),
            "protection_type": protection_level.get("type"),  # breakeven, partial, full
            "timestamp": datetime.now().isoformat(),
        }

        self.trade_logger.logger.info(
            f"🛡️ ЗАЩИТА ПРИБЫЛИ: {protection_level.get('type')} | "
            f"Прибыль: {protection_level.get('profit_percent')}% | "
            f"Защищено: {protection_level.get('locked_profit')}% | "
            f"Новый SL: {protection_level.get('new_sl')}",
            **log_data,
        )
        self.trade_logger._log_to_file("info", "PROFIT_PROTECTION", log_data)

    def log_sltp_error(
        self, position_id: str, operation: str, error: str, context: Dict = None
    ):
        """Логирование ошибок SL/TP"""
        log_data = {
            "position_id": position_id,
            "operation": operation,
            "error": error,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.trade_logger.logger.error(
            f"❌ ОШИБКА SL/TP [{operation}]: {error}", **log_data
        )
        self.trade_logger._log_to_file("error", "SLTP_ERROR", log_data)

    def log_sltp_api_response(
        self, position_id: str, api_call: str, request: Dict, response: Dict
    ):
        """Логирование API вызовов для SL/TP"""
        log_data = {
            "position_id": position_id,
            "api_call": api_call,
            "request": request,
            "response": response,
            "success": response.get("retCode") == 0 if "retCode" in response else False,
            "timestamp": datetime.now().isoformat(),
        }

        if log_data["success"]:
            self.trade_logger.logger.debug(
                f"✅ API SL/TP: {api_call} успешно", **log_data
            )
        else:
            self.trade_logger.logger.warning(
                f"⚠️ API SL/TP: {api_call} | Код: {response.get('retCode')} | {response.get('retMsg')}",
                **log_data,
            )

        self.trade_logger._log_to_file("debug", "SLTP_API_CALL", log_data)
