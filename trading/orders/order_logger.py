#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Order Logger Extension для детального логирования ордеров
"""

from datetime import datetime
from typing import Any, Dict

from core.logging.trade_logger import get_trade_logger


class OrderLogger:
    """Расширенное логирование для OrderManager"""

    def __init__(self):
        self.trade_logger = get_trade_logger()

    def log_order_lifecycle(self, order_id: str, stage: str, details: Dict[str, Any]):
        """
        Логирование полного жизненного цикла ордера

        Stages:
        - CREATED: Ордер создан в системе
        - VALIDATED: Ордер прошел валидацию
        - SUBMITTED: Ордер отправлен на биржу
        - ACCEPTED: Ордер принят биржей
        - PARTIALLY_FILLED: Частичное исполнение
        - FILLED: Полное исполнение
        - CANCELLED: Отменен
        - REJECTED: Отклонен биржей
        - EXPIRED: Истек срок
        """
        log_data = {
            "order_id": order_id,
            "stage": stage,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }

        # Эмоджи для разных стадий
        stage_emojis = {
            "CREATED": "📝",
            "VALIDATED": "✔️",
            "SUBMITTED": "📤",
            "ACCEPTED": "✅",
            "PARTIALLY_FILLED": "⚡",
            "FILLED": "💯",
            "CANCELLED": "🚫",
            "REJECTED": "❌",
            "EXPIRED": "⏰",
        }

        emoji = stage_emojis.get(stage, "📊")

        self.trade_logger.logger.info(f"{emoji} ORDER {stage}: {order_id}", **log_data)
        self.trade_logger._log_to_file("info", f"ORDER_{stage}", log_data)

    def log_order_validation(self, order: Dict, validation_results: Dict):
        """Логирование валидации ордера"""
        log_data = {
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "quantity": str(order.get("quantity", 0)),
            "validation": validation_results,
            "passed": validation_results.get("valid", False),
            "timestamp": datetime.now().isoformat(),
        }

        if validation_results.get("valid"):
            self.trade_logger.logger.debug(
                f"✅ Валидация пройдена: {order.get('symbol')}", **log_data
            )
        else:
            self.trade_logger.logger.warning(
                f"❌ Валидация не пройдена: {validation_results.get('reason')}",
                **log_data,
            )

        self.trade_logger._log_to_file("debug", "ORDER_VALIDATION", log_data)

    def log_order_risk_check(self, order: Dict, risk_results: Dict):
        """Логирование проверки риска для ордера"""
        log_data = {
            "symbol": order.get("symbol"),
            "position_size": str(order.get("quantity", 0) * order.get("price", 0)),
            "leverage": order.get("leverage"),
            "risk_percent": risk_results.get("risk_percent"),
            "max_allowed": risk_results.get("max_allowed"),
            "approved": risk_results.get("approved", False),
            "timestamp": datetime.now().isoformat(),
        }

        if risk_results.get("approved"):
            self.trade_logger.logger.info(
                f"✅ Риск проверен: {risk_results.get('risk_percent')}% из {risk_results.get('max_allowed')}%",
                **log_data,
            )
        else:
            self.trade_logger.logger.warning(
                f"⚠️ Риск превышен: {risk_results.get('risk_percent')}% > {risk_results.get('max_allowed')}%",
                **log_data,
            )

        self.trade_logger._log_to_file("info", "ORDER_RISK_CHECK", log_data)

    def log_order_execution_details(self, order_id: str, execution: Dict):
        """Детальное логирование исполнения ордера"""
        log_data = {
            "order_id": order_id,
            "exchange": execution.get("exchange"),
            "executed_qty": str(execution.get("executed_qty", 0)),
            "executed_price": str(execution.get("executed_price", 0)),
            "commission": str(execution.get("commission", 0)),
            "commission_asset": execution.get("commission_asset"),
            "slippage": str(execution.get("slippage", 0)),
            "execution_time_ms": execution.get("execution_time_ms"),
            "timestamp": datetime.now().isoformat(),
        }

        self.trade_logger.logger.info(
            f"📊 ИСПОЛНЕНИЕ: qty={execution.get('executed_qty')} @ {execution.get('executed_price')} "
            f"| Комиссия: {execution.get('commission')} {execution.get('commission_asset')} "
            f"| Slippage: {execution.get('slippage')}%",
            **log_data,
        )
        self.trade_logger._log_to_file("info", "ORDER_EXECUTION_DETAILS", log_data)

    def log_order_retry(self, order_id: str, attempt: int, reason: str):
        """Логирование повторной попытки отправки ордера"""
        log_data = {
            "order_id": order_id,
            "attempt": attempt,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        self.trade_logger.logger.warning(
            f"🔄 ПОВТОРНАЯ ПОПЫТКА #{attempt}: {reason}", **log_data
        )
        self.trade_logger._log_to_file("warning", "ORDER_RETRY", log_data)
