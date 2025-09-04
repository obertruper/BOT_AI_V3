"""
Runtime-флаги конфигурации с единым источником правды для переключателей.

Назначение: предоставить централизованный доступ к важным параметрам
в рантайме (без разрозненных чтений ENV/YAML по коду).

Сейчас реализован единый флаг hedge_mode для торговли на биржах.
"""

from __future__ import annotations

import os

from core.config.config_manager import get_global_config_manager

_HEDGE_MODE_OVERRIDE: bool | None = None


def set_hedge_mode(value: bool) -> None:
    """Устанавливает runtime-override для hedge_mode."""
    global _HEDGE_MODE_OVERRIDE
    _HEDGE_MODE_OVERRIDE = bool(value)


def get_hedge_mode() -> bool:
    """Возвращает актуальное значение hedge_mode.

    Приоритет источников:
    1) Runtime-override (set_hedge_mode)
    2) ConfigManager: key "trading.hedge_mode" (config/config.yaml)
    3) ENV BYBIT_HEDGE_MODE
    4) Значение по умолчанию: True
    """
    if _HEDGE_MODE_OVERRIDE is not None:
        return _HEDGE_MODE_OVERRIDE

    try:
        cm = get_global_config_manager()
        val = cm.get_config("trading.hedge_mode", None)
        if isinstance(val, bool):
            return val
    except Exception:
        # Если ConfigManager недоступен, идём дальше
        pass

    env_value = os.getenv("BYBIT_HEDGE_MODE", "true").lower()
    if env_value in ("true", "1", "yes", "on"):
        return True
    if env_value in ("false", "0", "no", "off"):
        return False

    return True
