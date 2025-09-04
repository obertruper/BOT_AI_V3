"""
Реализация улучшенного менеджера SL/TP для реструктурированной версии проекта.

Этот модуль содержит расширенную логику управления стоп-лосс и тейк-профит ордерами,
включая трейлинг-стоп, защиту прибыли, многоуровневый частичный тейк-профит
и другие улучшенные функции.

Автор: Claude
"""

import json
import logging
import math

# sqlite3 не используется - только PostgreSQL
import threading
import time
import traceback
from datetime import datetime
from typing import Any

# Импортируем потокобезопасные репозитории
from db.repositories.sltp_repository_thread_safe import (
    SLTPRepositoryThreadSafe,
    get_sltp_repository_thread_safe,
)
from db.repositories.trade_repository_thread_safe import get_trade_repository_thread_safe

# Импортируем функции из менеджера инструментов
from trading.instrument_manager import (
    get_instrument_info,
    round_price,
    round_qty,
)

# Импортируем helper для записи в таблицу истории
from trading.sltp.db_helper import get_sltp_db_helper
from trading.sltp.helpers import (
    get_last_price,
    set_trading_stop,
    validate_sltp_prices,
)

# Настройка логирования
logger = logging.getLogger("enhanced_sltp_manager")


def log_info(message: str) -> None:
    """Логирование информационных сообщений"""
    logger.info(message)


def log_warn(message: str) -> None:
    """Логирование предупреждений"""
    logger.warning(message)


def log_error(message: str) -> None:
    """Логирование ошибок"""
    logger.error(message)


def log_debug(message: str) -> None:
    """Логирование отладочных сообщений"""
    logger.debug(message)


def log_exception(title: str, e: Exception, context: dict[str, Any] = None) -> None:
    """
    Расширенное логирование исключений с контекстом

    Args:
        title: Заголовок сообщения об ошибке
        e: Исключение
        context: Контекст, в котором произошла ошибка
    """
    logger.error(f"{title}: {e}")
    if context:
        logger.error(f"Контекст ошибки: {json.dumps(context, default=str)}")
    logger.error(f"Тип ошибки: {type(e).__name__}")
    logger.error(traceback.format_exc())


def get_position_idx(side: str) -> int:
    """
    Определяет правильный positionIdx для hedge/one-way режима

    Args:
        side: Сторона сделки (Buy/Sell)

    Returns:
        int: positionIdx (0 для one-way, 1 для Buy hedge, 2 для Sell hedge)
    """
    try:
        from core.config import get_config

        trading_config = get_config("trading", {})
        hedge_mode = trading_config.get("hedge_mode", False)

        if hedge_mode:
            # В hedge режиме: 1=Long/Buy, 2=Short/Sell
            pos_idx = 1 if side.upper() in ["BUY", "LONG"] else 2
            log_info(
                f"[get_position_idx] => Hedge режим активен для сделки - используем positionIdx={pos_idx}"
            )
        else:
            # В one-way режиме: всегда 0
            pos_idx = 0
            log_info(f"[get_position_idx] => One-way режим - используем positionIdx={pos_idx}")

        return pos_idx
    except Exception as e:
        log_error(f"[get_position_idx] => Ошибка определения positionIdx: {e}")
        return 0  # Fallback к one-way режиму


# Функция get_instrument_settings перенесена в модуль instrument_settings


class EnhancedSLTPManager:
    """
    Улучшенный менеджер стоп-лосс и тейк-профит ордеров.

    Предоставляет расширенные функции для управления SL/TP:
    - Трейлинг-стоп с адаптивным шагом
    - Защита прибыли с многоуровневыми правилами
    - Многоуровневый частичный тейк-профит
    - Динамический тейк-профит на основе волатильности
    - Временные корректировки SL/TP
    """

    # КРИТИЧЕСКИ ВАЖНО: НЕ содержит торговых значений!
    # Все торговые параметры ДОЛЖНЫ быть ТОЛЬКО в config.yaml
    BASE_SETTINGS = {
        "trailing_stop": {"enabled": False},
        "profit_protection": {"enabled": False},
        "partial_take_profit": {"enabled": False},
        "volatility_adjustment": {"enabled": False},
        "time_based_adjustment": {"enabled": False},
    }

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        sltp_repository: SLTPRepositoryThreadSafe | None = None,
        trade_repository=None,
        api_client=None,
    ):
        """
        Инициализирует улучшенный менеджер SL/TP ордеров.

        Args:
            config: Конфигурация для менеджера
            sltp_repository: Репозиторий для работы с SL/TP ордерами
            trade_repository: Репозиторий для работы с торговыми сделками
            api_client: Клиент API биржи
        """
        self.config = config or {}
        # Используем потокобезопасную версию репозитория SL/TP для избежания ошибок SQLite
        self.sltp_repository = sltp_repository or get_sltp_repository_thread_safe()

        # НОВЫЙ КОД: Проверяем и создаем таблицу для истории частичных закрытий
        try:
            settings = self.config.get("enhanced_sltp", {})
            if settings.get("partial_take_profit", {}).get("enabled", False):
                self._ensure_partial_tp_history_table()
                log_info("[__init__] => Проверена таблица для истории частичных закрытий")
        except Exception as e:
            log_error(f"[__init__] => Ошибка при инициализации таблицы истории: {e}")
            import traceback

            log_error(traceback.format_exc())
        self.trade_repository = trade_repository or get_trade_repository_thread_safe()
        self.api_client = api_client

        # Блокировка для потокобезопасности
        self._lock = threading.RLock()
        self._creation_lock = threading.RLock()

        # Инициализируем настройки
        self.settings = self._load_settings()

        # Логирование инициализации
        log_info("EnhancedSLTPManager инициализирован")

    def _load_settings(self) -> dict[str, Any]:
        """
        Загружает настройки улучшенного SL/TP из конфигурации.

        Returns:
            Dict[str, Any]: Настройки для улучшенного SL/TP
        """
        # Пытаемся получить настройки из основной конфигурации
        settings = self.config.get("enhanced_sltp", {})

        # Попытка загрузить отдельный файл конфигурации enhanced_sltp_config.yaml
        try:
            import os

            import yaml

            config_path = "enhanced_sltp_config.yaml"
            if os.path.exists(config_path):
                log_info(f"Обнаружен файл конфигурации {config_path}, пытаемся загрузить")
                with open(config_path, encoding="utf-8") as f:
                    enhanced_config = yaml.safe_load(f)

                if enhanced_config and "enhanced_sltp" in enhanced_config:
                    log_info(f"Загружена конфигурация из файла {config_path}")
                    # Заменяем настройки из основного конфига настройками из enhanced_sltp_config.yaml
                    settings = enhanced_config.get("enhanced_sltp", {})
        except Exception as e:
            log_warn(f"Ошибка при загрузке файла enhanced_sltp_config.yaml: {e}")

        # Логируем использование настроек из конфигурации
        if settings:
            log_info("Используются настройки из конфигурационного файла")

            # Проверяем наличие важных блоков настроек
            if "profit_protection" in settings:
                profit_protection = settings.get("profit_protection", {})
                log_info(
                    f"Загружены настройки защиты прибыли: breakeven_percent={profit_protection.get('breakeven_percent')}, "
                    + f"breakeven_offset={profit_protection.get('breakeven_offset')}"
                )

            if "trailing_stop" in settings:
                trailing_stop = settings.get("trailing_stop", {})
                log_info(
                    f"Загружены настройки трейлинг-стопа: activation_percent={trailing_stop.get('activation_percent')}, "
                    + f"step_percent={trailing_stop.get('step_percent')}"
                )

            if "partial_take_profit" in settings:
                partial_tp = settings.get("partial_take_profit", {})
                levels = partial_tp.get("levels", [])
                enabled = partial_tp.get("enabled", False)
                log_info(
                    f"Загружены настройки частичного закрытия: enabled={enabled}, levels={len(levels)}"
                )
                if levels:
                    for i, level in enumerate(levels):
                        log_info(
                            f"Уровень {i + 1}: процент={level.get('percent')}%, доля закрытия={level.get('close_ratio') * 100}%"
                        )
                    log_info(
                        f"Обновление SL после частичного закрытия: {partial_tp.get('update_sl_after_partial', False)}"
                    )
        else:
            log_warn(
                "Настройки в конфигурационном файле не найдены, используются значения по умолчанию"
            )

        # КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: НЕ используем дефолты для торговых параметров!
        # Только базовые настройки enabled/disabled, никаких торговых значений
        CRITICAL_SECTIONS = ["partial_take_profit", "profit_protection", "trailing_stop"]

        for key, default_value in self.BASE_SETTINGS.items():
            if key not in settings:
                log_error(
                    f"КРИТИЧЕСКАЯ ОШИБКА: Раздел {key} НЕ НАЙДЕН в конфигурации! Торговая система ОСТАНОВЛЕНА!"
                )
                if key in CRITICAL_SECTIONS:
                    raise ValueError(f"Отсутствует критически важная секция {key} в конфигурации")
                log_warn(f"Раздел {key} не найден в конфигурации, используются базовые значения")
                settings[key] = {"enabled": False}  # Только отключаем функцию
            elif isinstance(default_value, dict) and key not in CRITICAL_SECTIONS:
                # Для НЕ-торговых настроек дополняем только базовые параметры
                for sub_key, sub_value in default_value.items():
                    if sub_key not in settings[key] and sub_key in ["enabled", "max_updates"]:
                        log_debug(
                            f"Параметр {key}.{sub_key} не найден, используется базовое значение: {sub_value}"
                        )
                        settings[key][sub_key] = sub_value

        return settings

    def set_advanced_sltp(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        order_id: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Устанавливает улучшенные SL/TP для позиции.

        Args:
            symbol: Символ инструмента
            side: Сторона позиции (BUY/SELL)
            quantity: Количество в позиции
            entry_price: Цена входа
            stop_loss: Стоп-лосс цена (опционально)
            take_profit: Тейк-профит цена (опционально)
            order_id: ID ордера (опционально)
            settings: Настройки SL/TP для этой конкретной позиции (опционально)

        Returns:
            Dict[str, Any]: Результат установки SL/TP
        """
        log_info(
            f"[set_advanced_sltp] => Установка улучшенных SL/TP для {symbol} {side}, entry_price={entry_price}"
        )

        result = {"success": False, "message": "", "sl_order_id": None, "tp_order_id": None}

        with self._creation_lock:
            try:
                # Проверка валидности SL/TP цен
                validation_result = validate_sltp_prices(
                    symbol, side, entry_price, stop_loss, take_profit
                )

                if not validation_result["valid"]:
                    log_warn(
                        f"[set_advanced_sltp] => Невалидные цены SL/TP: {validation_result['message']}"
                    )
                    result["message"] = validation_result["message"]
                    return result

                # Используем стандартную функцию для установки SL/TP
                position_idx = get_position_idx(side)  # Определяем правильный positionIdx
                api_response = set_trading_stop(
                    symbol, side, position_idx, stop_loss, take_profit, order_id
                )

                if api_response and api_response.get("retCode") == 0:
                    log_info(
                        f"[set_advanced_sltp] => Успешно установлены базовые SL/TP для {symbol} {side}"
                    )

                    # Получаем ID ордеров
                    sl_order_id = api_response.get("result", {}).get("stopLoss", {}).get("orderId")
                    tp_order_id = (
                        api_response.get("result", {}).get("takeProfit", {}).get("orderId")
                    )

                    # Сохраняем информацию о SL/TP в репозиторий
                    sltp_data = {
                        "symbol": symbol,
                        "side": side,
                        "entry_price": entry_price,
                        "stop_loss_price": stop_loss,  # Используем правильное имя поля для PostgreSQL
                        "take_profit_price": take_profit,  # Используем правильное имя поля для PostgreSQL
                        "sl_order_id": sl_order_id,
                        "tp_order_id": tp_order_id,
                        "status": "active",
                        "settings": settings or {},
                        "quantity": quantity,
                    }

                    # Сохраняем в репозиторий
                    if order_id:
                        # Если есть order_id, то привязываем SL/TP к конкретной сделке
                        trade = self.trade_repository.get_by_order_id(order_id)
                        if trade:
                            sltp_data["trade_id"] = trade.id

                    # Сохраняем информацию в репозиторий
                    # FIX: Используем подходящий метод в зависимости от доступности
                    try:
                        if hasattr(self.sltp_repository, "create_or_update"):
                            self.sltp_repository.create_or_update(sltp_data, "trade_id")
                            log_info("[set_advanced_sltp] => Использован метод create_or_update")
                        elif hasattr(self.sltp_repository, "insert_or_update"):
                            self.sltp_repository.insert_or_update(sltp_data)
                            log_info("[set_advanced_sltp] => Использован метод insert_or_update")
                        else:
                            # Если нет ни того, ни другого, пробуем просто создать запись
                            self.sltp_repository.create(sltp_data)
                            log_info("[set_advanced_sltp] => Использован метод create")
                    except Exception as repo_error:
                        log_error(
                            f"[set_advanced_sltp] => Ошибка при создании/обновлении данных через репозиторий: {repo_error}"
                        )

                    result["success"] = True
                    result["message"] = "SL/TP ордера успешно установлены"
                    result["sl_order_id"] = sl_order_id
                    result["tp_order_id"] = tp_order_id
                else:
                    error_msg = api_response.get("retMsg", "Неизвестная ошибка")
                    log_error(f"[set_advanced_sltp] => Ошибка установки SL/TP: {error_msg}")
                    result["message"] = f"Ошибка API: {error_msg}"

                return result
            except Exception as e:
                log_error(f"[set_advanced_sltp] => Исключение при установке улучшенных SL/TP: {e}")
                log_error(traceback.format_exc())
                result["message"] = f"Исключение: {e!s}"
                return result

    def apply_trailing_stop(self, trade_id: int) -> bool:
        """
        Применяет трейлинг-стоп к позиции.

        Args:
            trade_id: ID сделки

        Returns:
            bool: True если трейлинг-стоп был применен, False в противном случае
        """
        log_info(f"[apply_trailing_stop] => Применение трейлинг-стопа к сделке {trade_id}")

        with self._lock:
            try:
                # Получаем информацию о сделке
                trade = self.trade_repository.get_by_id(trade_id)
                if not trade:
                    log_warn(f"[apply_trailing_stop] => Сделка с ID={trade_id} не найдена")
                    return False

                # Получаем настройки трейлинг-стопа
                settings = self.settings.get("trailing_stop", {})
                if not settings.get("enabled", False):
                    log_debug("[apply_trailing_stop] => Трейлинг-стоп отключен в настройках")
                    return False

                # Получаем текущую цену
                symbol = trade.symbol
                side = trade.side
                entry_price = trade.entry_price
                current_price = get_last_price(symbol)

                if current_price <= 0:
                    log_error(
                        f"[apply_trailing_stop] => Не удалось получить текущую цену для {symbol}"
                    )
                    return False

                # Получаем профит в процентах
                profit_percent = self._calculate_profit_percent(entry_price, current_price, side)

                # Проверяем условие активации трейлинг-стопа
                if profit_percent < settings.get("activation_percent", 0.5):
                    log_debug(
                        f"[apply_trailing_stop] => Профит {profit_percent:.2f}% недостаточен для активации трейлинг-стопа"
                    )
                    return False

                # Получаем текущий стоп-лосс
                current_sl = trade.stop_loss
                if not current_sl or current_sl <= 0:
                    log_warn(
                        f"[apply_trailing_stop] => Для сделки {trade_id} не установлен стоп-лосс"
                    )
                    return False

                # Проверяем ограничение на количество обновлений
                sltp = self.sltp_repository.get_by_trade_id(trade_id)
                update_count = 0
                if sltp and hasattr(sltp, "extra_data") and sltp.extra_data:
                    try:
                        extra_data = (
                            json.loads(sltp.extra_data)
                            if isinstance(sltp.extra_data, str)
                            else sltp.extra_data
                        )
                        update_count = extra_data.get("trailing_updates", 0)
                    except (json.JSONDecodeError, TypeError):
                        extra_data = {}
                        update_count = 0
                else:
                    extra_data = {}

                max_updates = settings.get("max_updates", 15)
                if update_count >= max_updates:
                    log_debug(
                        f"[apply_trailing_stop] => Достигнуто максимальное количество обновлений трейлинг-стопа ({max_updates}) для сделки {trade_id}"
                    )
                    return False

                # Рассчитываем новый уровень трейлинг-стопа с учетом символа инструмента
                new_sl = self._calculate_trailing_stop(
                    side, current_price, current_sl, settings, symbol
                )

                if not new_sl:
                    log_debug(
                        "[apply_trailing_stop] => Не удалось рассчитать новый уровень трейлинг-стопа"
                    )
                    return False

                # Проверяем, улучшает ли новый SL текущий
                # Для BUY позиций мы хотим максимально высокий SL (чтобы минимизировать потери)
                # Для SELL позиций мы хотим максимально низкий SL (но выше entry_price)
                if side.upper() == "BUY":
                    if new_sl <= current_sl:
                        log_debug(
                            f"[apply_trailing_stop] => Новый SL ({new_sl:.6f}) не лучше текущего ({current_sl:.6f}) для BUY"
                        )
                        return False
                else:  # SELL
                    # Для SELL SL должен быть ВЫШЕ entry_price и ниже current_sl (если уже был установлен)
                    if new_sl >= current_sl and current_sl > entry_price:
                        log_debug(
                            f"[apply_trailing_stop] => Новый SL ({new_sl:.6f}) не лучше текущего ({current_sl:.6f}) для SELL"
                        )
                        return False

                # Округляем цену с использованием менеджера инструментов
                new_sl = round_price(symbol, new_sl, round_up=False)

                log_info(
                    f"[apply_trailing_stop] => Обновление трейлинг-стопа {symbol} {side}: {current_sl:.4f} -> {new_sl:.4f}"
                )

                # Устанавливаем новый стоп-лосс (ВАЖНО: нужно передать и текущий TP!)
                current_tp = trade.take_profit
                log_info(f"[apply_trailing_stop] => Передаем в API: SL={new_sl}, TP={current_tp}")

                # Определяем positionIdx в зависимости от режима и стороны

                pos_idx = get_position_idx(side)

                result = set_trading_stop(
                    symbol=symbol,
                    side=side,
                    pos_idx=pos_idx,
                    stop_loss=new_sl,
                    take_profit=current_tp,
                    trade_id=trade_id,
                )

                # Проверяем результат
                success = result.get("retCode") == 0
                not_modified = result.get("retCode") == 34040 or (
                    result.get("retMsg") and "not modified" in result.get("retMsg", "")
                )

                if success or not_modified:
                    # Обновляем информацию в БД
                    sltp = self.sltp_repository.get_by_trade_id(trade_id)
                    if sltp:
                        # Обновляем счетчик trailing_updates
                        extra_data["trailing_updates"] = update_count + 1

                        # Создаем словарь с обновленными данными
                        sltp_update = {
                            "stop_loss_price": new_sl,  # Правильное имя поля для БД
                            "trailing_stop_price": new_sl,
                            "updated_at": datetime.now(),
                            "extra_data": json.dumps(extra_data),
                        }
                        # Обновляем через репозиторий
                        # Добавляем trade_id в данные для использования insert_or_update
                        sltp_update["trade_id"] = trade_id
                        # Используем метод insert_or_update вместо update для совместимости с потокобезопасным репозиторием
                        # FIX: Используем подходящий метод в зависимости от доступности
                        try:
                            if hasattr(self.sltp_repository, "create_or_update"):
                                result = self.sltp_repository.create_or_update(
                                    sltp_update, "trade_id"
                                )
                                log_info(
                                    "[apply_trailing_stop] => Использован метод create_or_update"
                                )
                            elif hasattr(self.sltp_repository, "insert_or_update"):
                                result = self.sltp_repository.insert_or_update(sltp_update)
                                log_info(
                                    "[apply_trailing_stop] => Использован метод insert_or_update"
                                )
                            else:
                                # Если нет ни того, ни другого, пробуем обновить
                                if hasattr(sltp, "id") and sltp.id:
                                    # Обновляем поля в объекте sltp
                                    for key, value in sltp_update.items():
                                        if hasattr(sltp, key):
                                            setattr(sltp, key, value)
                                    result = self.sltp_repository.update(sltp)
                                    log_info("[apply_trailing_stop] => Использован метод update")
                                else:
                                    log_error(
                                        "[apply_trailing_stop] => Не удалось найти подходящий метод для обновления"
                                    )
                                    result = False
                        except Exception as repo_error:
                            log_error(
                                f"[apply_trailing_stop] => Ошибка при обновлении данных через репозиторий: {repo_error}"
                            )
                            result = False

                        if not result:
                            log_error(
                                "[apply_trailing_stop] => Ошибка при обновлении SL через репозиторий"
                            )

                    # Обновляем сделку
                    trade_data = {"stop_loss": new_sl}
                    self.trade_repository.update(trade.id, trade_data)

                    log_info(
                        f"[apply_trailing_stop] => Успешно обновлен трейлинг-стоп: {new_sl:.4f} (обновление #{update_count + 1}/{max_updates})"
                    )
                    return True
                else:
                    log_error(
                        f"[apply_trailing_stop] => Ошибка при установке трейлинг-стопа: {result.get('retMsg', 'Unknown error')}"
                    )
                    return False
            except Exception as e:
                log_error(f"[apply_trailing_stop] => Ошибка: {e}")
                log_error(traceback.format_exc())
                return False

    def _calculate_profit_percent(
        self, entry_price: float, current_price: float, side: str
    ) -> float:
        """
        Рассчитывает текущий процент прибыли/убытка для позиции.

        Args:
            entry_price: Цена входа
            current_price: Текущая цена
            side: Сторона позиции (BUY/SELL)

        Returns:
            float: Процент прибыли/убытка
        """
        if entry_price <= 0 or current_price <= 0:
            return 0.0

        if side.upper() == "BUY":
            return ((current_price - entry_price) / entry_price) * 100.0
        else:  # SELL
            return ((entry_price - current_price) / entry_price) * 100.0

    def _calculate_trailing_stop(
        self,
        side: str,
        current_price: float,
        current_sl: float,
        settings: dict[str, Any],
        symbol: str | None = None,
    ) -> float | None:
        """
        Рассчитывает новый уровень трейлинг-стопа с учетом настроек инструмента.

        Args:
            side: Сторона позиции (BUY/SELL)
            current_price: Текущая цена
            current_sl: Текущий стоп-лосс
            settings: Настройки трейлинг-стопа
            symbol: Символ инструмента (опционально)

        Returns:
            Optional[float]: Новый уровень стоп-лосса или None, если нет изменений
        """
        # Получаем настройки инструмента заранее, чтобы использовать их на всех этапах расчета
        # Получаем информацию об инструменте
        instrument_info = get_instrument_info(symbol)
        tick_size = instrument_info.get("tick_size", 0.001)

        # Минимальное расстояние от текущей цены в процентах
        min_distance_percent = settings.get("min_distance", 0.3)

        # Устанавливаем максимальный процент изменения SL от текущей цены
        max_sl_change_percent = 5.0

        # Рассчитываем расстояние с учетом размера тика
        # Это обеспечит, что расстояние будет кратно размеру тика
        ticks_distance = math.ceil((current_price * min_distance_percent / 100.0) / tick_size)
        distance = ticks_distance * tick_size

        if side.upper() == "BUY":
            # Для длинной позиции трейлинг-стоп двигается вверх
            new_sl = current_price - distance

            # Проверяем, улучшает ли новый SL текущий
            if new_sl <= current_sl:
                return None

            # Проверяем на максимальное изменение
            min_allowed_sl = current_price * (1 - max_sl_change_percent / 100)
            if new_sl < min_allowed_sl:
                log_warn(
                    f"[_calculate_trailing_stop] => Новый SL {new_sl} слишком низок для {symbol}! Ограничиваем до {min_allowed_sl}"
                )
                ticks_min = math.floor(min_allowed_sl / tick_size)
                new_sl = ticks_min * tick_size

        else:  # SELL
            # Для короткой позиции трейлинг-стоп двигается вниз (вверх по цене)
            new_sl = current_price + distance

            # Для SELL SL должен быть ВЫШЕ текущей цены и ниже current_sl (если уже был установлен)
            if new_sl >= current_sl and current_sl > 0:
                return None

            # Проверяем на максимальное изменение
            max_allowed_sl = current_price * (1 + max_sl_change_percent / 100)
            if new_sl > max_allowed_sl:
                log_warn(
                    f"[_calculate_trailing_stop] => Новый SL {new_sl} слишком высок для {symbol}! Ограничиваем до {max_allowed_sl}"
                )
                ticks_max = math.ceil(max_allowed_sl / tick_size)
                new_sl = ticks_max * tick_size

        # Логика особой обработки для проблемных инструментов
        if symbol in ["GALAUSDT", "TRXUSDT", "MATICUSDT", "ENAUSDT"]:
            # Для проблемных инструментов с малым размером тика
            # используем строгое целочисленное округление в тиках
            log_info(f"[_calculate_trailing_stop] => Специальная обработка для {symbol}")

            # Вычисляем количество тиков и округляем
            if side.upper() == "SELL":
                ticks = math.ceil(new_sl / tick_size)
            else:  # BUY
                ticks = math.floor(new_sl / tick_size)

            # Преобразуем обратно в цену, кратную тику
            new_sl = ticks * tick_size

        else:
            # Для остальных инструментов - обычное округление
            if side.upper() == "SELL":
                # Для SELL округляем вверх (SL должен быть ВЫШЕ текущей цены)
                new_sl = math.ceil(new_sl / tick_size) * tick_size
            else:  # BUY
                # Для BUY округляем вниз (SL должен быть НИЖЕ текущей цены)
                new_sl = math.floor(new_sl / tick_size) * tick_size

        # Округляем цену с использованием правильного менеджера инструментов
        new_sl = round_price(symbol, new_sl, round_up=(side.upper() == "SELL"))

        log_info(
            f"[_calculate_trailing_stop] => Для {symbol} SL округлен с тиком {tick_size}: {new_sl}"
        )
        return new_sl

    def apply_profit_protection(self, trade_id: int) -> bool:
        """
        Применяет защиту прибыли к позиции.

        Args:
            trade_id: ID сделки

        Returns:
            bool: True если защита прибыли была применена, False в противном случае
        """
        log_info(f"[apply_profit_protection] => Применение защиты прибыли к сделке {trade_id}")

        # Получаем настройки hedge режима для правильной работы с positionIdx
        from core.config import get_config

        trading_config = get_config("trading", {})
        hedge_mode = trading_config.get("hedge_mode", False)
        if hedge_mode:
            log_info(
                f"[apply_profit_protection] => Hedge режим активен для сделки {trade_id} - используем positionIdx=1"
            )

        with self._lock:
            try:
                # Получаем информацию о сделке
                trade = self.trade_repository.get_by_id(trade_id)
                if not trade:
                    log_warn(f"[apply_profit_protection] => Сделка с ID={trade_id} не найдена")
                    return False

                # Получаем настройки защиты прибыли
                settings = self.settings.get("profit_protection", {})
                if not settings.get("enabled", False):
                    log_debug("[apply_profit_protection] => Защита прибыли отключена в настройках")
                    return False

                # Получаем текущую цену
                symbol = trade.symbol
                side = trade.side
                entry_price = trade.entry_price
                current_price = get_last_price(symbol)

                if current_price <= 0:
                    log_error(
                        f"[apply_profit_protection] => Не удалось получить текущую цену для {symbol}"
                    )
                    return False

                # Получаем профит в процентах
                profit_percent = self._calculate_profit_percent(entry_price, current_price, side)

                # Используем SL из БД вместо получения с биржи (избегаем проблем с кэшированными данными)
                current_sl = trade.stop_loss
                log_info(f"[apply_profit_protection] => Используем текущий SL из БД: {current_sl}")

                if not current_sl or current_sl <= 0:
                    log_warn(
                        f"[apply_profit_protection] => Для сделки {trade_id} не установлен стоп-лосс, пытаемся восстановить"
                    )

                    # Пытаемся восстановить SL из истории попыток
                    try:
                        from db.thread_safe_postgres import get_thread_safe_db

                        # Получаем последнюю успешную попытку установки SL
                        db = get_thread_safe_db()
                        result = db.execute_query(
                            """
                                                  SELECT message
                                                  FROM sltp_attempts
                                                  WHERE trade_id = %s
                                                    AND status = 'success'
                                                    AND message LIKE '%SL=%'
                                                  ORDER BY created_at DESC LIMIT 1
                                                  """,
                            (trade_id,),
                            fetch=True,
                            as_dict=True,
                        )

                        if result and len(result) > 0:
                            # Извлекаем SL из сообщения формата "SL/TP установлен: SL=0.2801, TP=..."
                            import re

                            try:
                                message = (
                                    result[0].get("message", "")
                                    if isinstance(result[0], dict)
                                    else str(result[0])
                                )
                            except (IndexError, AttributeError, TypeError):
                                message = str(result)
                            sl_match = re.search(r"SL=([0-9.]+)", message)
                            if sl_match:
                                original_sl = float(sl_match.group(1))
                                log_info(
                                    f"[apply_profit_protection] => Найден исходный SL: {original_sl}"
                                )

                                # Пересчитываем SL с правильным округлением
                                from trading.instrument_manager import round_price

                                if side.upper() == "SELL":
                                    # Для SELL округляем вверх
                                    corrected_sl = round_price(symbol, original_sl, round_up=True)
                                else:
                                    # Для BUY округляем вниз
                                    corrected_sl = round_price(symbol, original_sl, round_up=False)

                                log_info(
                                    f"[apply_profit_protection] => Пересчитанный SL с правильным округлением: {original_sl} -> {corrected_sl}"
                                )

                                # Устанавливаем исправленный SL
                                current_tp = getattr(trade, "take_profit", None)

                                # Определяем правильный positionIdx для hedge режима
                                pos_idx = get_position_idx(side)

                                restore_result = set_trading_stop(
                                    symbol=symbol,
                                    side=side,
                                    pos_idx=pos_idx,
                                    stop_loss=corrected_sl,
                                    take_profit=current_tp,
                                    trade_id=trade_id,
                                )

                                if restore_result.get("retCode") == 0:
                                    log_info(
                                        f"[apply_profit_protection] => Успешно восстановлен SL с правильным округлением: {corrected_sl}"
                                    )
                                    # Обновляем current_sl для дальнейших расчетов
                                    current_sl = corrected_sl

                                    # Обновляем в БД
                                    self.trade_repository.update(
                                        trade_id, {"stop_loss": corrected_sl}
                                    )
                                else:
                                    log_error(
                                        f"[apply_profit_protection] => Ошибка восстановления SL: {restore_result.get('retMsg')}"
                                    )
                                    return False
                            else:
                                log_warn(
                                    f"[apply_profit_protection] => Не удалось извлечь SL из сообщения: {message}"
                                )
                                return False
                        else:
                            log_warn(
                                f"[apply_profit_protection] => Не найдено записей об установке SL для trade_id={trade_id}"
                            )
                            return False

                    except Exception as e:
                        log_error(f"[apply_profit_protection] => Ошибка при восстановлении SL: {e}")
                        # НЕ возвращаем False - продолжаем работу и устанавливаем SL при достижении уровней
                        log_info(
                            "[apply_profit_protection] => Продолжаем без восстановления - установим SL при достижении уровня безубытка"
                        )
                        current_sl = 0.0

                # Если SL до сих пор не установлен (0.0) и достигнут уровень безубытка
                if current_sl == 0.0 and "breakeven_percent" in settings:
                    breakeven_trigger = settings["breakeven_percent"]
                    if profit_percent >= breakeven_trigger:
                        log_info(
                            f"[apply_profit_protection] => Достигнут уровень безубытка {breakeven_trigger}% при профите {profit_percent}%"
                        )

                        # Рассчитываем безубыток с учетом смещения
                        breakeven_offset = settings.get("breakeven_offset", 0.0)
                        if side.upper() == "SELL":
                            # Для SELL: SL выше цены входа
                            new_sl = entry_price * (1 + breakeven_offset / 100)
                        else:
                            # Для BUY: SL ниже цены входа
                            new_sl = entry_price * (1 - breakeven_offset / 100)

                        log_info(
                            f"[apply_profit_protection] => Устанавливаем SL в безубыток: {new_sl} (смещение {breakeven_offset}%)"
                        )

                        # Устанавливаем SL
                        current_tp = getattr(
                            trade, "take_profit", None
                        )  # Получаем текущий TP из сделки
                        pos_idx = get_position_idx(side)
                        result = set_trading_stop(
                            symbol=symbol,
                            side=side,
                            pos_idx=pos_idx,
                            stop_loss=new_sl,
                            take_profit=current_tp,
                            trade_id=trade_id,
                        )

                        if result.get("retCode") == 0:
                            log_info(
                                f"[apply_profit_protection] => ✅ Успешно установлен SL в безубыток: {new_sl}"
                            )
                            current_sl = new_sl
                            # Обновляем в БД
                            self.trade_repository.update(trade_id, {"stop_loss": new_sl})
                        else:
                            log_error(
                                f"[apply_profit_protection] => ❌ Ошибка установки SL в безубыток: {result.get('retMsg')}"
                            )
                            return False

                # Новый стоп-лосс для дальнейших уровней (если будем обновлять)
                new_sl = None

                # Проверяем уровни защиты прибыли (от большего к меньшему)
                if "lock_percent" in settings:
                    # Сортируем уровни по убыванию триггера
                    levels = sorted(
                        settings["lock_percent"], key=lambda x: x["trigger"], reverse=True
                    )

                    for level in levels:
                        trigger = level["trigger"]
                        lock = level["lock"]

                        if profit_percent >= trigger:
                            log_info(
                                f"[apply_profit_protection] => Активирован уровень защиты: {trigger}% -> фиксация {lock}%"
                            )

                            # Рассчитываем новый стоп-лосс на основе уровня фиксации прибыли
                            log_info(
                                f"[apply_profit_protection] => Расчет SL: entry={entry_price}, current={current_price}, lock={lock}%, profit={profit_percent}%"
                            )

                            if side.upper() == "BUY":
                                lock_amount = (current_price - entry_price) * (
                                    lock / profit_percent
                                )
                                new_sl = (
                                    entry_price + lock_amount
                                )  # Для BUY позиций SL устанавливается ВЫШЕ цены входа
                                log_info(
                                    f"[apply_profit_protection] => BUY: lock_amount={lock_amount:.6f}, new_sl={new_sl:.6f}"
                                )
                            else:  # SELL
                                lock_amount = (entry_price - current_price) * (
                                    lock / profit_percent
                                )
                                new_sl = (
                                    entry_price - lock_amount
                                )  # Для SELL позиций SL устанавливается НИЖЕ цены входа
                                log_info(
                                    f"[apply_profit_protection] => SELL: lock_amount={lock_amount:.6f}, new_sl={new_sl:.6f}"
                                )

                            log_warn(
                                f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 1: new_sl={new_sl}, продолжаем выполнение..."
                            )
                            break  # Используем самый высокий подходящий уровень

                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 2: После цикла уровней, new_sl={new_sl}"
                )

                # Проверяем условие безубытка, если не нашли уровень защиты
                if new_sl is None and profit_percent >= settings.get("breakeven_percent", 1.0):
                    log_info(
                        f"[apply_profit_protection] => Активирован безубыток (профит: {profit_percent:.2f}%)"
                    )

                    # Получаем смещение от цены входа (в %)
                    offset_percent = settings.get("breakeven_offset", 0.2)

                    # Рассчитываем новый стоп-лосс с учетом смещения
                    if side.upper() == "BUY":
                        # Для длинной позиции устанавливаем стоп ВЫШЕ цены входа на offset_percent
                        offset_amount = entry_price * (offset_percent / 100.0)
                        new_sl = entry_price + offset_amount
                    else:  # SELL
                        # Для короткой позиции устанавливаем стоп НИЖЕ цены входа на offset_percent
                        # ВАЖНО: для короткой позиции при безубытке SL должен быть НИЖЕ цены входа
                        offset_amount = entry_price * (offset_percent / 100.0)
                        new_sl = entry_price - offset_amount

                    log_info(
                        f"[apply_profit_protection] => Безубыток со смещением {offset_percent}% = {new_sl:.4f}"
                    )

                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 3: После безубытка, new_sl={new_sl}"
                )

                # Если не нашли подходящий уровень защиты
                if new_sl is None:
                    log_warn(
                        f"[apply_profit_protection] => Не найден подходящий уровень защиты для профита {profit_percent:.2f}%, settings={settings}"
                    )
                    return False

                log_warn(
                    "[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 4: Начинаем работу с SLTP репозиторием"
                )

                # Получаем информацию о SLTP из репозитория
                sltp = self.sltp_repository.get_by_trade_id(trade_id)
                update_count = 0
                last_applied_level = None
                current_level_name = "breakeven"  # По умолчанию безубыток

                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 5: SLTP получен, sltp={sltp is not None}"
                )

                # Определяем, какой уровень защиты сейчас достигнут согласно конфигурации
                # Проверяем уровни lock_percent (от большего к меньшему)
                if "lock_percent" in settings and profit_percent >= settings.get(
                    "breakeven_percent", 1.0
                ):
                    levels = sorted(
                        settings["lock_percent"], key=lambda x: x["trigger"], reverse=True
                    )
                    for level in levels:
                        if profit_percent >= level["trigger"]:
                            current_level_name = f"lock_{level['trigger']}"
                            break
                # Если профит меньше минимального trigger, но больше breakeven_percent - остается "breakeven"

                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 6: current_level_name={current_level_name}"
                )

                if sltp:
                    # Получаем информацию о количестве обновлений стоп-лосса
                    extra_data = sltp.extra_data or {}
                    update_count = extra_data.get("protection_updates", 0)
                    already_applied_levels = extra_data.get("applied_levels", [])
                    last_applied_level = extra_data.get("last_applied_level")

                    log_warn(
                        f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 7: already_applied_levels={already_applied_levels}"
                    )

                    # Если этот уровень уже был применен, логируем это для отладки
                    if current_level_name in already_applied_levels:
                        log_info(
                            f"[apply_profit_protection] => Уровень {current_level_name} уже был применен ранее (отладочная информация)"
                        )

                        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Для уже примененных уровней проверяем наличие записи в sltp_updates_history
                        # и создаем её через потокобезопасное соединение, если отсутствует (обратная совместимость)
                        try:
                            from db.thread_safe_postgres import get_thread_safe_db

                            db = get_thread_safe_db()

                            # Проверяем наличие записи для данного уровня
                            check_query = """
                                          SELECT COUNT(*) as count \
                                          FROM sltp_updates_history
                                          WHERE trade_id = %s \
                                            AND level_name = %s \
                                          """
                            check_result = db.execute_query(
                                check_query, (trade_id, current_level_name), fetch=True
                            )

                            if check_result and check_result[0]["count"] == 0:
                                # Записи нет, создаем её
                                history_query = """
                                                INSERT INTO sltp_updates_history
                                                    (trade_id, level_name, price, profit_percent, timestamp)
                                                VALUES (%s, %s, %s, %s, NOW()) \
                                                """
                                history_result = db.execute_query(
                                    history_query,
                                    (trade_id, current_level_name, new_sl, profit_percent),
                                    fetch=False,
                                )
                                if history_result is not False:
                                    log_info(
                                        f"[apply_profit_protection] => Создана недостающая запись в sltp_updates_history (обратная совместимость): trade_id={trade_id}, level={current_level_name}"
                                    )
                                else:
                                    log_error(
                                        f"[apply_profit_protection] => Не удалось создать недостающую запись в sltp_updates_history для trade_id={trade_id}"
                                    )
                            else:
                                log_info(
                                    f"[apply_profit_protection] => Запись для уровня {current_level_name} уже существует в sltp_updates_history"
                                )
                        except Exception as hist_error:
                            log_error(
                                f"[apply_profit_protection] => Ошибка при проверке/создании записи в sltp_updates_history (обратная совместимость): {hist_error}"
                            )

                log_warn(
                    "[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 8: Проверки пройдены, продолжаем к проверкам SL"
                )

                # Безопасное логирование переменных
                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 8.1: new_sl TYPE={type(new_sl)} VALUE={new_sl!r}"
                )
                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 8.2: current_sl TYPE={type(current_sl)} VALUE={current_sl!r}"
                )
                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 8.3: side TYPE={type(side)} VALUE={side!r}"
                )

                # Проверяем значения на None
                if new_sl is None:
                    log_error(
                        "[apply_profit_protection] => ОШИБКА: new_sl is None! Функция должна была завершиться раньше"
                    )
                    return False
                if current_sl is None:
                    log_error("[apply_profit_protection] => ОШИБКА: current_sl is None!")
                    return False
                if side is None:
                    log_error("[apply_profit_protection] => ОШИБКА: side is None!")
                    return False

                # Проверяем ограничение на максимальное количество обновлений
                # Но разрешаем переход на более высокие уровни защиты
                max_updates = settings.get("max_updates", 5)
                if sltp and update_count >= max_updates:
                    # Проверяем, является ли текущий уровень новым (более высоким)
                    already_applied_levels = (
                        sltp.extra_data.get("applied_levels", []) if sltp.extra_data else []
                    )
                    if current_level_name in already_applied_levels:
                        log_warn(
                            f"[apply_profit_protection] => Достигнуто максимальное количество обновлений ({max_updates}) и уровень {current_level_name} уже применялся"
                        )
                        return False
                    else:
                        log_info(
                            f"[apply_profit_protection] => Разрешаем обновление до нового уровня {current_level_name} несмотря на {update_count} обновлений"
                        )

                log_warn(
                    "[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 10: Проверка обновлений пройдена"
                )

                # Проверяем ограничения на цену SL относительно текущей цены рынка
                if side.upper() == "BUY":
                    # Проверяем, что стоп не выше текущей цены для BUY
                    if new_sl >= current_price:
                        log_warn(
                            f"[apply_profit_protection] => Рассчитанный SL ({new_sl:.6f}) выше текущей цены ({current_price:.6f})"
                        )
                        # Устанавливаем SL немного ниже текущей цены
                        new_sl = current_price * 0.995
                        log_info(
                            f"[apply_profit_protection] => Скорректирован SL до {new_sl:.6f} (0.5% ниже текущей цены)"
                        )
                else:  # SELL
                    # Проверяем, что стоп не ниже текущей цены для SELL
                    if new_sl <= current_price:
                        log_warn(
                            f"[apply_profit_protection] => Рассчитанный SL ({new_sl:.6f}) ниже текущей цены ({current_price:.6f})"
                        )
                        # Устанавливаем SL немного выше текущей цены
                        new_sl = current_price * 1.005
                        log_info(
                            f"[apply_profit_protection] => Скорректирован SL до {new_sl:.6f} (0.5% выше текущей цены)"
                        )

                log_info(
                    f"[apply_profit_protection] => Обновление SL: {current_sl:.6f} -> {new_sl:.6f} (профит: {profit_percent:.2f}%)"
                )

                # Используем универсальный метод округления цен
                from trading.instrument_manager import round_price

                # Устанавливаем максимальный процент изменения SL от текущей цены
                max_sl_change_percent = 5.0

                # Проверяем ограничения перед округлением
                if side.upper() == "SELL":
                    # Для SELL SL должен быть ВЫШЕ текущей цены
                    max_allowed_sl = current_price * (1 + max_sl_change_percent / 100)
                    if new_sl > max_allowed_sl:
                        log_warn(
                            f"[apply_profit_protection] => Новый SL {new_sl} слишком высок! Ограничиваем до {max_allowed_sl}"
                        )
                        new_sl = max_allowed_sl
                    # Округляем вверх для SELL
                    new_sl = round_price(symbol, new_sl, round_up=True)
                else:  # BUY
                    # Для BUY SL должен быть НИЖЕ текущей цены
                    min_allowed_sl = current_price * (1 - max_sl_change_percent / 100)
                    if new_sl < min_allowed_sl:
                        log_warn(
                            f"[apply_profit_protection] => Новый SL {new_sl} слишком низок! Ограничиваем до {min_allowed_sl}"
                        )
                        new_sl = min_allowed_sl
                    # Округляем вниз для BUY
                    new_sl = round_price(symbol, new_sl, round_up=False)

                log_info(
                    f"[apply_profit_protection] => Для {symbol} SL округлен универсальным методом: {new_sl}"
                )

                # Важная проверка: новый SL должен улучшать защиту прибыли
                sl_improved = False
                if side.upper() == "BUY":
                    # Для BUY новый SL должен быть ВЫШЕ текущего (защищает больше прибыли)
                    sl_improved = new_sl > current_sl
                    log_info(
                        f"[apply_profit_protection] => BUY: новый SL {new_sl:.6f} {'>' if sl_improved else '<='} текущий SL {current_sl:.6f}"
                    )
                else:  # SELL
                    # Для SELL новый SL должен быть НИЖЕ текущего (защищает больше прибыли)
                    sl_improved = new_sl < current_sl
                    log_info(
                        f"[apply_profit_protection] => SELL: новый SL {new_sl:.6f} {'<' if sl_improved else '>='} текущий SL {current_sl:.6f}"
                    )

                if not sl_improved:
                    log_warn(
                        f"[apply_profit_protection] => Новый SL {new_sl:.6f} не улучшает текущий {current_sl:.6f} для {side}, пропускаем обновление"
                    )
                    return False

                log_info(
                    f"[apply_profit_protection] => Обновляем SL для защиты прибыли: {current_sl:.4f} -> {new_sl:.4f}"
                )

                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 9: Вызываем set_trading_stop с SL={new_sl}"
                )

                # Устанавливаем новый стоп-лосс (ВАЖНО: нужно передать и текущий TP!)
                current_tp = trade.take_profit
                log_info(
                    f"[apply_profit_protection] => Передаем в API: SL={new_sl}, TP={current_tp}"
                )

                # Определяем правильный positionIdx для hedge режима
                pos_idx = get_position_idx(side)

                result = set_trading_stop(
                    symbol=symbol,
                    side=side,
                    pos_idx=pos_idx,
                    stop_loss=new_sl,
                    take_profit=current_tp,
                    trade_id=trade_id,
                )

                log_warn(
                    f"[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 10: set_trading_stop вернул: {result}"
                )

                # Проверяем результат (добавляем дополнительное логирование)
                import json

                log_info(
                    f"[apply_profit_protection] => Результат API запроса: {json.dumps(result, default=str)}"
                )
                success = result.get("retCode") == 0
                not_modified = result.get("retCode") == 34040 or (
                    result.get("retMsg") and "not modified" in result.get("retMsg", "")
                )

                if success:
                    log_info(
                        f"[apply_profit_protection] => API успешно обновил SL: {result.get('retMsg', 'OK')}"
                    )
                elif not_modified:
                    log_info(
                        f"[apply_profit_protection] => SL не изменен (уже установлен такой же): {result.get('retMsg', 'Not modified')}"
                    )

                # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Обновляем БД только при РЕАЛЬНОМ успехе API
                if success:
                    # Обновляем информацию в БД ТОЛЬКО при успешном изменении SL на бирже
                    sltp = self.sltp_repository.get_by_trade_id(trade_id)
                    if sltp:
                        # Обновляем счетчик обновлений стоп-лосса
                        extra_data = sltp.extra_data or {}
                        update_count = extra_data.get("protection_updates", 0) + 1
                        extra_data["protection_updates"] = update_count

                        # Сохраняем историю обновлений стоп-лосса
                        updates_history = extra_data.get("sl_updates_history", [])
                        updates_history.append(
                            {
                                "timestamp": time.time(),
                                "price": new_sl,
                                "profit_percent": float(
                                    profit_percent
                                ),  # Убедимся, что это float для JSON
                                "level": current_level_name,
                            }
                        )
                        extra_data["sl_updates_history"] = updates_history

                        # Добавляем текущий уровень в список примененных уровней
                        already_applied_levels = extra_data.get("applied_levels", [])
                        if current_level_name not in already_applied_levels:
                            already_applied_levels.append(current_level_name)
                        extra_data["applied_levels"] = already_applied_levels
                        extra_data["last_applied_level"] = current_level_name

                        # Логируем содержимое extra_data перед сохранением для отладки
                        log_info(
                            f"[apply_profit_protection] => Подготовленные extra_data: {json.dumps(extra_data, default=str)}"
                        )

                        # Создаем словарь с обновленными данными
                        sltp_update = {
                            "stop_loss_price": new_sl,  # Правильное имя поля для БД
                            "updated_at": datetime.now(),
                            "extra_data": json.dumps(extra_data),  # Явно конвертируем в JSON строку
                        }
                        # Обновляем через репозиторий
                        # Добавляем trade_id в данные для использования в репозитории
                        sltp_update["trade_id"] = trade_id
                        # Добавляем подробное логирование
                        log_info(
                            f"[apply_profit_protection] => Детали обновления: {json.dumps(sltp_update, default=str)}"
                        )

                        # FIX: Используем метод create_or_update вместо insert_or_update - так как в PostgreSQL репозитории нет insert_or_update
                        try:
                            # Проверяем наличие метода create_or_update в репозитории
                            if hasattr(self.sltp_repository, "create_or_update"):
                                result = self.sltp_repository.create_or_update(
                                    sltp_update, "trade_id"
                                )
                                log_info(
                                    "[apply_profit_protection] => Использован метод create_or_update"
                                )
                            elif hasattr(self.sltp_repository, "insert_or_update"):
                                # Использовать метод create_or_update, так как он есть в PostgresRepository
                                if hasattr(self.sltp_repository, "create_or_update"):
                                    result = self.sltp_repository.create_or_update(
                                        sltp_update, "trade_id"
                                    )
                                    log_info(
                                        "[apply_profit_protection] => Использован метод create_or_update"
                                    )
                                # Запасной вариант, если у репозитория есть insert_or_update
                                elif hasattr(self.sltp_repository, "insert_or_update"):
                                    result = self.sltp_repository.insert_or_update(sltp_update)
                                    log_info(
                                        "[apply_profit_protection] => Использован метод insert_or_update"
                                    )
                                else:
                                    log_error(
                                        "[apply_profit_protection] => Методы update/insert_or_update не найдены"
                                    )
                                    result = False
                                log_info(
                                    "[apply_profit_protection] => Использован метод insert_or_update"
                                )
                            else:
                                # Если нет ни того, ни другого, пробуем обновить
                                log_info(
                                    "[apply_profit_protection] => Методы create_or_update/insert_or_update не найдены, пробуем update"
                                )
                                # Обновляем поля в объекте sltp
                                for key, value in sltp_update.items():
                                    if hasattr(sltp, key):
                                        setattr(sltp, key, value)
                                result = self.sltp_repository.update(sltp)
                        except Exception as repo_error:
                            log_error(
                                f"[apply_profit_protection] => Ошибка при обновлении данных через репозиторий: {repo_error}"
                            )
                            result = False

                        # Используем потокобезопасное подключение к БД
                        try:
                            log_info("ОБНОВЛЕНИЕ SLTP ЧЕРЕЗ ПОТОКОБЕЗОПАСНЫЙ РЕПОЗИТОРИЙ")

                            from db.thread_safe_postgres import get_thread_safe_db

                            db = get_thread_safe_db()

                            # Обновляем extra_data в sltp_orders через потокобезопасное соединение
                            import json

                            update_query = """
                                           UPDATE sltp_orders
                                           SET extra_data = %s, \
                                               updated_at = NOW()
                                           WHERE trade_id = %s \
                                           """

                            # Выполняем обновление
                            result = db.execute_query(
                                update_query, (json.dumps(extra_data), trade_id), fetch=False
                            )

                            if result is not False:  # execute_query возвращает False при ошибке
                                log_info(
                                    f"[apply_profit_protection] => SLTP запись обновлена через потокобезопасное соединение для trade_id={trade_id}"
                                )

                                # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Создаем запись в sltp_updates_history через потокобезопасное соединение
                                try:
                                    history_query = """
                                                    INSERT INTO sltp_updates_history
                                                        (trade_id, level_name, price, profit_percent, timestamp)
                                                    VALUES (%s, %s, %s, %s, NOW()) ON CONFLICT DO NOTHING \
                                                    """
                                    history_result = db.execute_query(
                                        history_query,
                                        (trade_id, current_level_name, new_sl, profit_percent),
                                        fetch=False,
                                    )
                                    if history_result is not False:
                                        log_info(
                                            f"[apply_profit_protection] => Создана запись в sltp_updates_history через потокобезопасное соединение: trade_id={trade_id}, level={current_level_name}"
                                        )
                                    else:
                                        log_error(
                                            f"[apply_profit_protection] => Не удалось создать запись в sltp_updates_history для trade_id={trade_id}"
                                        )
                                except Exception as hist_error:
                                    log_error(
                                        f"[apply_profit_protection] => Ошибка при создании записи в sltp_updates_history: {hist_error}"
                                    )
                            else:
                                log_error(
                                    f"[apply_profit_protection] => Не удалось обновить SLTP запись для trade_id={trade_id}"
                                )

                        except Exception as e:
                            log_error(
                                f"[apply_profit_protection] => Ошибка при обновлении SLTP через потокобезопасное соединение: {e}"
                            )
                            import traceback

                            log_error(
                                f"[apply_profit_protection] => Трассировка: {traceback.format_exc()}"
                            )

                        if result:
                            log_info(
                                f"[apply_profit_protection] => Обновление #{update_count} для уровня {current_level_name} (макс. {settings.get('max_updates', 5)})"
                            )
                            # Проверяем, что данные действительно обновились
                            check_sltp = self.sltp_repository.get_by_trade_id(trade_id)
                            if check_sltp:
                                if check_sltp.extra_data:
                                    # Проверяем, является ли extra_data строкой JSON или словарем
                                    if isinstance(check_sltp.extra_data, str):
                                        try:
                                            json.loads(
                                                check_sltp.extra_data
                                            )  # Проверяем валидность JSON
                                            log_info(
                                                f"[apply_profit_protection] => Проверка обновления (extra_data как строка): {check_sltp.extra_data[:200]}..."
                                            )
                                        except json.JSONDecodeError:
                                            log_error(
                                                f"[apply_profit_protection] => extra_data не является валидным JSON: {check_sltp.extra_data[:200]}"
                                            )
                                    else:
                                        log_info(
                                            f"[apply_profit_protection] => Проверка обновления (extra_data как объект): {json.dumps(check_sltp.extra_data, default=str)}"
                                        )
                                else:
                                    log_error(
                                        "[apply_profit_protection] => Данные обновились, но extra_data пусто"
                                    )
                            else:
                                log_error(
                                    "[apply_profit_protection] => Не удалось получить данные SLTP после обновления"
                                )
                        else:
                            log_error(
                                f"[apply_profit_protection] => Ошибка при обновлении SL для уровня {current_level_name}"
                            )
                    else:
                        # Если запись SLTP не существует, создаем новую
                        extra_data = {
                            "protection_updates": 1,
                            "sl_updates_history": [
                                {
                                    "timestamp": time.time(),
                                    "price": new_sl,
                                    "profit_percent": float(
                                        profit_percent
                                    ),  # Убедимся, что это float для JSON
                                    "level": current_level_name,
                                }
                            ],
                            "applied_levels": [current_level_name],
                            "last_applied_level": current_level_name,
                        }

                        # Логируем содержимое extra_data перед сохранением для отладки
                        log_info(
                            f"[apply_profit_protection] => Подготовленные extra_data для новой записи: {json.dumps(extra_data, default=str)}"
                        )

                        sltp_data = {
                            "trade_id": trade_id,
                            "symbol": symbol,
                            "side": side,
                            "entry_price": entry_price,
                            "stop_loss_price": new_sl,  # Правильное имя поля для БД
                            "take_profit_price": trade.take_profit,  # Правильное имя поля для БД
                            "extra_data": json.dumps(extra_data),  # Явно конвертируем в JSON строку
                            "created_at": datetime.now(),
                            "updated_at": datetime.now(),
                        }

                        # В PostgreSQL репозитории метод называется create() вместо insert()
                        try:
                            from db.models import SLTPOrder

                            sltp_order = SLTPOrder.from_dict(sltp_data)
                            result_id = self.sltp_repository.create(sltp_order)
                            if result_id:
                                log_info(
                                    f"[apply_profit_protection] => Создана новая запись SLTP с ID {result_id}"
                                )
                            else:
                                log_error(
                                    "[apply_profit_protection] => Не удалось создать запись SLTP (ID не получен)"
                                )
                        except Exception as e:
                            log_error(f"[apply_profit_protection] => Ошибка при создании SLTP: {e}")
                            import traceback

                            log_error(
                                f"[apply_profit_protection] => Трассировка ошибки: {traceback.format_exc()}"
                            )

                    # Обновляем сделку
                    trade_data = {"stop_loss": new_sl}
                    self.trade_repository.update(trade.id, trade_data)

                    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Создаем запись в таблице sltp_updates_history
                    try:
                        db_helper = get_sltp_db_helper()
                        db_helper.log_sl_update(
                            trade_id, current_level_name, new_sl, profit_percent
                        )
                        log_info(
                            f"[apply_profit_protection] => Создана запись в sltp_updates_history: trade_id={trade_id}, level={current_level_name}"
                        )
                    except Exception as hist_error:
                        log_error(
                            f"[apply_profit_protection] => Ошибка при создании записи в sltp_updates_history: {hist_error}"
                        )

                    log_info(
                        f"[apply_profit_protection] => Успешно обновлен SL для защиты прибыли: {new_sl:.4f} (профит: {profit_percent:.2f}%)"
                    )
                    log_warn(
                        "[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 11: УСПЕШНОЕ ЗАВЕРШЕНИЕ! Возвращаем True"
                    )
                    return True
                elif not_modified:
                    # Если SL не изменился (код 34040), НЕ обновляем БД и НЕ считаем это успехом
                    log_warn(
                        "[apply_profit_protection] => SL не был изменен на бирже (код 34040) - НЕ обновляем applied_levels"
                    )
                    return False  # Возвращаем False чтобы система попробует снова позже
                else:
                    error_code = result.get("retCode", "Unknown")
                    error_msg = result.get("retMsg", "Unknown error")
                    log_error(
                        f"[apply_profit_protection] => Ошибка при установке SL: код {error_code}, сообщение: {error_msg}"
                    )
                    log_warn(
                        "[apply_profit_protection] => КРИТИЧЕСКАЯ ТОЧКА 12: КРИТИЧНАЯ ОШИБКА! Возвращаем False"
                    )
                    return False

            except Exception as e:
                import traceback

                log_error(f"[apply_profit_protection] => Ошибка: {e}")
                log_error(traceback.format_exc())
                return False

    # Функция _check_existing_pending_partial_tp удалена - дубликаты предотвращаются уникальным индексом

    def _ensure_partial_tp_history_table(self):
        """
        Проверяет существование таблицы partial_tp_history и создает ее при необходимости
        """
        try:
            # Проверяем существование таблицы
            check_query = """
                          SELECT EXISTS (SELECT \
                                         FROM information_schema.tables \
                                         WHERE table_schema = 'public' \
                                           AND table_name = 'partial_tp_history') \
                          """

            # Используем PostgreSQL коннектор
            from db.postgres_connector import get_postgres_connector

            db = get_postgres_connector()
            result = db.execute_query(check_query, fetch=True)
            table_exists = result[0]["exists"] if result else False

            if not table_exists:
                # Создаем таблицу
                create_table_query = """
                                     CREATE TABLE partial_tp_history \
                                     ( \
                                         id                  SERIAL PRIMARY KEY, \
                                         trade_id            INTEGER          NOT NULL, \
                                         level_percent       DOUBLE PRECISION NOT NULL, \
                                         close_ratio         DOUBLE PRECISION NOT NULL, \
                                         original_qty        DOUBLE PRECISION NOT NULL, \
                                         close_qty           DOUBLE PRECISION NOT NULL, \
                                         symbol              TEXT             NOT NULL, \
                                         side                TEXT             NOT NULL, \
                                         close_side          TEXT             NOT NULL, \
                                         current_price       DOUBLE PRECISION NOT NULL, \
                                         profit_percent      DOUBLE PRECISION NOT NULL, \
                                         entry_price         DOUBLE PRECISION NOT NULL, \
                                         exchange_qty_before DOUBLE PRECISION NOT NULL, \
                                         timestamp           TIMESTAMP        NOT NULL, \
                                         status              TEXT             NOT NULL, \
                                         order_id            TEXT, \
                                         error               TEXT, \
                                         created_at          TIMESTAMP DEFAULT NOW(), \
                                         updated_at          TIMESTAMP DEFAULT NOW()
                                     );
                                     CREATE INDEX idx_partial_tp_history_trade_id ON partial_tp_history (trade_id);
                                     CREATE INDEX idx_partial_tp_history_timestamp ON partial_tp_history (timestamp);
                                     CREATE INDEX idx_partial_tp_history_symbol ON partial_tp_history (symbol);
                                     CREATE INDEX idx_partial_tp_history_status ON partial_tp_history (status); \
                                     """

                db.execute_query(create_table_query, fetch=False)

                log_info(
                    "[_ensure_partial_tp_history_table] => Создана таблица partial_tp_history"
                )

        except Exception as e:
            log_error(f"[_ensure_partial_tp_history_table] => Ошибка при проверке таблицы: {e}")
            import traceback

            log_error(traceback.format_exc())

    def _save_partial_tp_history(self, history_entry):
        """
        Сохраняет запись в историю частичных закрытий

        Args:
            history_entry (dict): Данные о частичном закрытии
        """
        try:
            # Проверяем существование таблицы
            self._ensure_partial_tp_history_table()

            # Дополнительная проверка на дубликаты перед вставкой
            check_query = """
                          SELECT id \
                          FROM partial_tp_history
                          WHERE trade_id = %s \
                            AND level_percent = %s \
                            AND status = 'pending'
                            AND timestamp >= NOW() - INTERVAL '5 minutes'
                              LIMIT 1 \
                          """

            from db.thread_safe_postgres import get_thread_safe_db

            db = get_thread_safe_db()

            # Проверяем наличие дубликата
            check_result = db.execute_query(
                check_query, (history_entry.get("trade_id"), history_entry.get("level_percent"))
            )

            if check_result and len(check_result) > 0:
                log_warn(
                    f"[_save_partial_tp_history] => Найдена недавняя запись для trade_id={history_entry.get('trade_id')}, level={history_entry.get('level_percent')}%, пропускаем вставку"
                )
                return -1

            # Формируем SQL запрос для вставки
            query = """
                    INSERT INTO partial_tp_history (trade_id, level_percent, close_ratio, original_qty, close_qty, \
                                                    symbol, side, close_side, current_price, profit_percent, \
                                                    entry_price, exchange_qty_before, timestamp, status, order_id, \
                                                    error) \
                    VALUES (%s, %s, %s, %s, %s, \
                            %s, %s, %s, %s, %s, \
                            %s, %s, %s, %s, %s, %s) RETURNING id \
                    """

            # Подготавливаем параметры
            params = (
                history_entry.get("trade_id"),
                history_entry.get("level_percent"),
                history_entry.get("close_ratio"),
                history_entry.get("original_qty"),
                history_entry.get("close_qty"),
                history_entry.get("symbol"),
                history_entry.get("side"),
                history_entry.get("close_side"),
                history_entry.get("current_price"),
                history_entry.get("profit_percent"),
                history_entry.get("entry_price"),
                history_entry.get("exchange_qty_before"),
                datetime.fromtimestamp(history_entry.get("timestamp")),
                history_entry.get("status"),
                history_entry.get("order_id"),
                history_entry.get("error"),
            )

            # Выполняем запрос к базе данных
            record_id = None
            try:
                from db.thread_safe_postgres import get_thread_safe_db

                db = get_thread_safe_db()

                # Используем execute_query для выполнения запроса
                result = db.execute_query(query, params)
                if result and len(result) > 0:
                    record_id = result[0].get("id", 0)

                log_info(
                    f"[_save_partial_tp_history] => Запись сохранена в историю частичных закрытий, ID: {record_id}"
                )

            except Exception as e:
                error_str = str(e).lower()
                # Проверяем, является ли это ошибкой дубликата
                if "duplicate key" in error_str or "unique constraint" in error_str:
                    log_warn(
                        f"[_save_partial_tp_history] => Попытка сохранить дубликат частичного закрытия для trade_id={history_entry.get('trade_id')}, level={history_entry.get('level_percent')}%"
                    )
                    # Это не критичная ошибка, возвращаем -1 как индикатор дубликата
                    record_id = -1
                else:
                    log_error(f"[_save_partial_tp_history] => Ошибка при сохранении в историю: {e}")
                    import traceback

                    log_error(traceback.format_exc())
                    # Возвращаем 0 в случае ошибки
                    record_id = 0

            log_info(
                f"[_save_partial_tp_history] => Сохранена запись в историю частичных закрытий, ID: {record_id}"
            )
            return record_id

        except Exception as e:
            log_error(
                f"[_save_partial_tp_history] => Ошибка при сохранении в историю частичных закрытий: {e}"
            )
            import traceback

            log_error(traceback.format_exc())
            return None

    def _update_partial_tp_history(self, history_entry):
        """
        Обновляет запись в истории частичных закрытий

        Args:
            history_entry (dict): Данные о частичном закрытии
        """
        try:
            # Формируем SQL запрос для обновления
            # Используем более надежный способ - обновляем последнюю запись со статусом pending
            query = """
                    UPDATE partial_tp_history
                    SET status     = %s,
                        order_id   = %s,
                        error      = %s,
                        updated_at = NOW()
                    WHERE trade_id = %s
                      AND level_percent = %s
                      AND status = 'pending'
                      AND id = (SELECT id \
                                FROM partial_tp_history
                                WHERE trade_id = %s \
                                  AND level_percent = %s \
                                  AND status = 'pending'
                                ORDER BY created_at DESC \
                        LIMIT 1) \
                    """

            # Подготавливаем параметры (добавляем trade_id и level_percent дважды для подзапроса)
            params = (
                history_entry.get("status"),
                history_entry.get("order_id"),
                history_entry.get("error"),
                history_entry.get("trade_id"),
                history_entry.get("level_percent"),
                history_entry.get("trade_id"),  # Для подзапроса
                history_entry.get("level_percent"),  # Для подзапроса
            )

            # Выполняем запрос
            from db.thread_safe_postgres import get_thread_safe_db

            db = get_thread_safe_db()
            db.execute_query(query, params, fetch=False)

            # Для отладки - проверяем что именно мы обновляем
            # Обновляем статус и order_id в history_entry для последующего использования
            status = history_entry.get("status")
            order_id = history_entry.get("order_id")

            log_info(
                f"[_update_partial_tp_history] => Обновление записи в partial_tp_history: trade_id={history_entry.get('trade_id')}, "
                + f"level={history_entry.get('level_percent')}, status={status}, "
                + f"order_id={order_id}"
            )

            # Проверяем, действительно ли запись обновлена
            check_query = """
                          SELECT status, order_id \
                          FROM partial_tp_history
                          WHERE trade_id = %s \
                            AND level_percent = %s
                          ORDER BY created_at DESC LIMIT 1 \
                          """
            check_params = (history_entry.get("trade_id"), history_entry.get("level_percent"))
            check_result = db.execute_query(check_query, check_params)

            if check_result:
                actual_status = check_result[0].get("status")
                actual_order_id = check_result[0].get("order_id")
                log_info(
                    f"[_update_partial_tp_history] => Проверка после обновления: status={actual_status}, order_id={actual_order_id}"
                )

            log_info(
                f"[_update_partial_tp_history] => Успешно обновлена запись в partial_tp_history для trade_id={history_entry.get('trade_id')}"
            )

        except Exception as e:
            log_error(
                f"[_update_partial_tp_history] => Ошибка при обновлении истории частичных закрытий: {e}"
            )
            import traceback

            log_error(traceback.format_exc())

    def get_position(self, symbol, positions_from_exchange=None):
        """
        Найти позицию по символу среди переданных позиций.

        Args:
            symbol (str): Символ торговой пары
            positions_from_exchange: Список позиций с биржи (если не передан, возвращает None)

        Returns:
            dict: Информация о позиции или None, если позиция не найдена
        """
        if positions_from_exchange is None:
            log_warn(f"[get_position] => Позиции с биржи не переданы для {symbol}")
            return None

        try:
            positions = positions_from_exchange
            log_info(f"[get_position] => Получено {len(positions)} позиций для поиска {symbol}")

            # Логируем первые несколько позиций для диагностики
            if len(positions) > 0:
                for i, pos in enumerate(positions[:3]):  # Первые 3 позиции
                    if isinstance(pos, dict):
                        pos_symbol = pos.get("symbol", "N/A")
                        pos_side = pos.get("side", "N/A")
                        pos_size = pos.get("size", "N/A")
                        pos_idx = pos.get("positionIdx", pos.get("position_idx", "N/A"))
                        log_info(
                            f"[get_position] => Позиция #{i + 1}: {pos_symbol} {pos_side} size={pos_size} idx={pos_idx}"
                        )
                    else:
                        # Для объектов Position показываем реальные атрибуты
                        pos_symbol = getattr(pos, "symbol", "N/A")
                        pos_side = getattr(pos, "side", "N/A")
                        pos_size = getattr(pos, "size", "N/A")
                        pos_idx = getattr(pos, "position_idx", "N/A")
                        log_info(
                            f"[get_position] => Позиция #{i + 1}: {pos_symbol} {pos_side} size={pos_size} idx={pos_idx}"
                        )
            else:
                log_warn(f"[get_position] => Список позиций пуст для {symbol}")

            if not positions or len(positions) == 0:
                log_info(f"[get_position] => Позиция {symbol} не найдена на бирже")
                return None

            # Получаем настройки hedge режима
            from core.config import get_config

            trading_config = get_config("trading", {})
            hedge_mode = trading_config.get("hedge_mode", False)

            # Ищем позицию по нужному символу
            for position in positions:
                try:
                    # Безопасное получение значения symbol, поддержка как словарей, так и объектов
                    if isinstance(position, dict):
                        position_symbol = position.get("symbol", "")
                        # Проверяем оба варианта ключа: positionIdx (API) и position_idx (модель)
                        position_idx = position.get("positionIdx", position.get("position_idx", 0))
                        size = float(position.get("size", 0))
                        side = position.get("side", "")

                        if position_symbol == symbol:
                            # В hedge режиме проверяем правильный positionIdx (1=Buy, 2=Sell) и наличие стороны
                            if hedge_mode:
                                if (position_idx == 1 or position_idx == 2) and size > 0 and side:
                                    log_info(
                                        f"[get_position] => Найдена hedge позиция {symbol} idx={position_idx} side={side}: {position}"
                                    )
                                    return position
                            else:
                                # В one-way режиме просто проверяем размер
                                if size > 0:
                                    log_info(
                                        f"[get_position] => Найдена one-way позиция {symbol}: {position}"
                                    )
                                    return position
                    else:
                        # Если это объект, используем getattr (правильные имена атрибутов для Position)
                        position_symbol = getattr(position, "symbol", "")
                        position_idx = getattr(
                            position, "position_idx", 0
                        )  # Исправлено: position_idx вместо positionIdx
                        size = float(getattr(position, "size", 0))
                        side = getattr(position, "side", "")

                        if position_symbol == symbol:
                            # В hedge режиме проверяем правильный positionIdx (1=Buy, 2=Sell) и наличие стороны
                            if hedge_mode:
                                if (position_idx == 1 or position_idx == 2) and size > 0 and side:
                                    log_info(
                                        f"[get_position] => Найдена hedge позиция {symbol} idx={position_idx} side={side}: объект"
                                    )
                                    return position
                            else:
                                # В one-way режиме просто проверяем размер
                                if size > 0:
                                    log_info(
                                        f"[get_position] => Найдена one-way позиция {symbol}: объект"
                                    )
                                    return position
                except Exception as e:
                    log_error(f"[get_position] => Ошибка при обработке позиции: {e}")
                    continue

            log_info(f"[get_position] => Позиция {symbol} не найдена среди активных позиций")
            return None

        except Exception as e:
            log_error(f"[get_position] => Ошибка при получении позиции: {e}")
            return None

    def check_partial_tp(self, trade_id: int, exchange_positions=None) -> bool:
        """
        Проверяет и выполняет частичное закрытие позиции.

        Args:
            trade_id: ID сделки

        Returns:
            bool: True если было выполнено частичное закрытие, False в противном случае
        """
        log_info(f"[check_partial_tp] => Проверка частичного закрытия для сделки {trade_id}")
        log_info(
            "[check_partial_tp] => ВНИМАНИЕ: Используются ТОЛЬКО значения из config.yaml - никаких хардкод значений!"
        )

        # Проверяем hedge режим - в hedge режиме частичное закрытие может работать по-другому
        from core.config import get_config

        trading_config = get_config("trading", {})
        if trading_config.get("hedge_mode", False):
            log_info(
                f"[check_partial_tp] => Режим hedge активен для сделки {trade_id} - используем адаптированную логику"
            )

        with self._lock:
            try:
                # Получаем информацию о сделке
                trade = self.trade_repository.get_by_id(trade_id)
                if not trade:
                    log_warn(f"[check_partial_tp] => Сделка с ID={trade_id} не найдена")
                    return False

                # НОВЫЙ КОД: Проверяем статус сделки
                if trade.status not in ["OPEN", "open"]:
                    log_info(
                        f"[check_partial_tp] => Сделка {trade_id} уже закрыта (статус: {trade.status}), пропускаем"
                    )
                    return False

                # Получаем настройки частичного закрытия из config.yaml
                # Соответствует секции:
                #   partial_take_profit:
                #     enabled: true
                #     levels: ...
                settings = self.settings.get("partial_take_profit", {})

                # Включен ли функционал частичного закрытия
                if not settings.get("enabled", False):
                    log_debug(
                        "[check_partial_tp] => Частичное закрытие отключено в настройках (enabled: false)"
                    )
                    return False

                # Проверяем, что настроены уровни частичного закрытия
                if not settings.get("levels"):
                    log_debug(
                        "[check_partial_tp] => Не настроены уровни частичного закрытия (levels: [])"
                    )
                    return False

                # Получаем текущую цену
                symbol = trade.symbol
                side = trade.side
                entry_price = trade.entry_price
                current_price = get_last_price(symbol)

                if current_price <= 0:
                    log_error(
                        f"[check_partial_tp] => Не удалось получить текущую цену для {symbol}"
                    )
                    return False

                # НОВЫЙ КОД: Проверяем позицию на бирже перед попыткой закрытия
                if self.api_client is None:
                    log_error(
                        "[check_partial_tp] => API клиент не инициализирован. Невозможно проверить позицию на бирже"
                    )
                    return False

                # Получаем позицию с биржи (используем переданные позиции)
                exchange_position = self.get_position(symbol, exchange_positions)
                if not exchange_position:
                    log_warn(
                        f"[check_partial_tp] => Позиция {symbol} не найдена на бирже, пропускаем частичное закрытие"
                    )
                    return False

                # Безопасное получение size и side, поддерживает как словари, так и объекты
                try:
                    # Если это словарь, используем метод get
                    if isinstance(exchange_position, dict):
                        exchange_qty = float(exchange_position.get("size", 0))
                        exchange_side = exchange_position.get("side", "")
                    # Если это объект, используем getattr
                    else:
                        exchange_qty = float(getattr(exchange_position, "size", 0))
                        exchange_side = getattr(exchange_position, "side", "")
                except Exception as e:
                    log_error(f"[check_partial_tp] => Ошибка при получении данных из позиции: {e}")
                    log_warn(
                        f"[check_partial_tp] => Позиция {symbol} имеет неверный формат, пропускаем частичное закрытие"
                    )
                    return False

                # Проверяем размер позиции на бирже
                if exchange_qty <= 0:
                    log_warn(
                        f"[check_partial_tp] => Позиция {symbol} на бирже имеет нулевой размер: {exchange_qty}, пропускаем"
                    )
                    return False

                # Проверяем совпадение стороны позиции
                expected_exchange_side = "Buy" if side.upper() == "BUY" else "Sell"
                if exchange_side != expected_exchange_side:
                    log_warn(
                        f"[check_partial_tp] => Несоответствие сторон позиции: в БД {side}, на бирже {exchange_side}"
                    )
                    return False

                log_info(
                    f"[check_partial_tp] => Позиция {symbol} существует на бирже: сторона {exchange_side}, размер {exchange_qty}"
                )

                # Получаем текущее количество из БД и проверяем с биржей
                current_qty = trade.quantity
                if current_qty <= 0:
                    log_warn(f"[check_partial_tp] => Для сделки {trade_id} нулевое количество в БД")
                    return False

                # НОВЫЙ КОД: Используем минимальное из количества в БД и на бирже
                if exchange_qty < current_qty:
                    log_warn(
                        f"[check_partial_tp] => Количество на бирже ({exchange_qty}) меньше чем в БД ({current_qty}), используем биржевое"
                    )
                    current_qty = exchange_qty

                # Получаем профит в процентах
                profit_percent = self._calculate_profit_percent(entry_price, current_price, side)

                # Получаем уже выполненные уровни частичного закрытия
                sltp = self.sltp_repository.get_by_trade_id(trade_id)
                if not sltp:
                    executed_levels = []
                    log_info(
                        f"[check_partial_tp] => Не найдены данные SLTP для сделки {trade_id}, начинаем с пустого списка выполненных уровней"
                    )
                else:
                    try:
                        extra_data = sltp.extra_data or {}
                        partial_tp_executed_str = extra_data.get("partial_tp_executed", "[]")
                        executed_levels = (
                            json.loads(partial_tp_executed_str)
                            if isinstance(partial_tp_executed_str, str)
                            else partial_tp_executed_str
                        )
                        log_info(
                            f"[check_partial_tp] => Загружены выполненные уровни: {partial_tp_executed_str}"
                        )

                        if not isinstance(executed_levels, list):
                            log_warn(
                                f"[check_partial_tp] => Некорректный формат выполненных уровней: {type(executed_levels)}, сбрасываем в пустой список"
                            )
                            executed_levels = []

                        # НОВЫЙ КОД: Проверяем и исправляем статусы уровней при необходимости
                        for level in executed_levels:
                            if "status" not in level:
                                level["status"] = (
                                    "executed"  # Считаем все записи без статуса выполненными
                                )
                                log_info(
                                    f"[check_partial_tp] => Добавлен статус 'executed' для уровня {level.get('percent')}%"
                                )
                    except (json.JSONDecodeError, AttributeError) as e:
                        log_error(
                            f"[check_partial_tp] => Ошибка при загрузке выполненных уровней: {e}, {type(e)}"
                        )
                        executed_levels = []

                # Получаем уровни частичного закрытия из конфигурации
                # Эти уровни соответствуют настройкам в config.yaml:
                #   partial_take_profit:
                #     levels:
                #       - percent: 1.0
                #         close_ratio: 0.25
                #       - percent: 2.0
                #         close_ratio: 0.25
                #       - percent: 3.5
                #         close_ratio: 0.25
                levels = settings.get("levels", [])
                log_debug(
                    f"[check_partial_tp] => Уровни частичного закрытия из конфигурации: {levels}"
                )
                triggered_level = None

                # Сортируем уровни по убыванию процента, чтобы проверять сначала самые высокие уровни
                # Это гарантирует, что мы будем использовать самый высокий достигнутый уровень
                sorted_levels = sorted(levels, key=lambda x: x["percent"], reverse=True)
                log_debug(f"[check_partial_tp] => Отсортированные уровни: {sorted_levels}")

                # Логируем текущие исполненные уровни для отладки
                log_info(f"[check_partial_tp] => Всего выполненных уровней: {len(executed_levels)}")
                for i, executed in enumerate(executed_levels):
                    log_info(
                        f"[check_partial_tp] => Выполненный уровень #{i + 1}: {executed.get('percent')}%, статус: {executed.get('status')}"
                    )

                # Проверяем каждый уровень (от большего к меньшему)
                for level in sorted_levels:
                    level_percent = level["percent"]

                    # Проверяем, не был ли уже выполнен этот уровень
                    level_executed = False
                    recent_execution = False
                    for executed in executed_levels:
                        if executed.get("percent") == level_percent:
                            status = executed.get("status", "executed")

                            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Пропускаем только РЕАЛЬНО выполненные уровни
                            # Статус "recorded" означает только запись в БД, но НЕ исполнение на бирже
                            if status == "executed":
                                level_executed = True
                                log_info(
                                    f"[check_partial_tp] => Уровень {level_percent}% уже ИСПОЛНЕН на бирже, пропускаем"
                                )
                                break
                            elif status == "recorded":
                                # Записано в БД, но НЕ исполнено - нужно исполнить!
                                log_info(
                                    f"[check_partial_tp] => Уровень {level_percent}% записан но НЕ исполнен, продолжаем исполнение"
                                )
                                # НЕ устанавливаем level_executed = True
                                break
                            else:
                                # Неизвестный статус - пропускаем для безопасности
                                level_executed = True
                                log_warn(
                                    f"[check_partial_tp] => Уровень {level_percent}% имеет неизвестный статус '{status}', пропускаем"
                                )
                                break

                    if level_executed:
                        continue  # Пропускаем только РЕАЛЬНО выполненные уровни

                    # Проверяем, достигнут ли уровень профита из настроек
                    # Уровни определены в config.yaml:
                    #   partial_take_profit:
                    #     levels:
                    #       - percent: 1.2  <- это level_percent (текущие настройки COPE сервера)
                    #         close_ratio: 0.25
                    #       - percent: 2.4  <- следующий уровень
                    #         close_ratio: 0.25
                    if profit_percent >= level_percent:
                        log_info(
                            f"[check_partial_tp] => Достигнут уровень {level_percent}% (текущий профит: {profit_percent:.2f}%)"
                        )
                        triggered_level = level
                        break  # Используем самый высокий достигнутый уровень (сортировка по убыванию)

                # Если нет достигнутых уровней или все уже выполнены
                if triggered_level is None:
                    log_debug(
                        "[check_partial_tp] => Нет новых достигнутых уровней частичного закрытия"
                    )
                    return False

                # Рассчитываем количество для частичного закрытия
                # close_ratio берется напрямую из конфига
                close_ratio = triggered_level["close_ratio"]

                # ИСПРАВЛЕНИЕ: Используем ИЗНАЧАЛЬНЫЙ размер позиции, а не текущий!
                # Получаем изначальный размер из БД
                original_position_qty = trade.quantity
                close_qty = original_position_qty * close_ratio

                log_info(
                    f"[check_partial_tp] => Частичное закрытие от ИЗНАЧАЛЬНОГО размера: {close_qty:.4f} = {original_position_qty:.4f} * {close_ratio:.2f}"
                )
                log_info(
                    f"[check_partial_tp] => Текущий размер на бирже: {exchange_qty:.4f} (для сравнения)"
                )

                # Добавляем пояснение в лог
                log_debug(
                    f"[check_partial_tp] => Рассчитано количество для закрытия: {close_qty} ({close_ratio * 100:.0f}% от изначального объема {original_position_qty})"
                )

                if close_qty <= 0:
                    log_warn(
                        f"[check_partial_tp] => Слишком малое количество для частичного закрытия: {close_qty}"
                    )
                    return False

                log_info(
                    f"[check_partial_tp] => Активирован уровень {triggered_level['percent']}% -> закрытие {close_ratio * 100:.0f}% позиции"
                )

                # Определяем противоположную сторону для закрытия позиции
                close_side = "Sell" if side.upper() == "BUY" else "Buy"

                # Вычисляем точное количество для частичного закрытия с учетом округления
                # и минимального размера ордера для данного инструмента
                try:
                    # Проверяем инициализацию API клиента
                    if self.api_client is None:
                        log_error(
                            f"[check_partial_tp] => API клиент не инициализирован. Невозможно получить информацию об инструменте {symbol}"
                        )
                        return False

                    # Получаем информацию об инструменте для определения минимального шага и размера ордера
                    instrument_info = self.api_client.get_instrument_info(symbol)
                    if not instrument_info:
                        log_error(
                            f"[check_partial_tp] => Не удалось получить информацию об инструменте {symbol}"
                        )
                        return False

                    # Получаем правильные настройки шага и минимального количества напрямую из API
                    if instrument_info and "lotSizeFilter" in instrument_info:
                        lot_size_filter = instrument_info["lotSizeFilter"]
                        qty_step = float(lot_size_filter.get("qtyStep", "0.001"))
                        min_order_qty = float(lot_size_filter.get("minOrderQty", "0.001"))
                        log_info(
                            f"[check_partial_tp] => Получены настройки напрямую из API: шаг={qty_step}, мин={min_order_qty}"
                        )

                        # Проверяем минимальную стоимость ордера
                        min_notional_value = float(lot_size_filter.get("minNotionalValue", "5.0"))
                        log_info(
                            f"[check_partial_tp] => Минимальная стоимость ордера для {symbol}: {min_notional_value} USDT"
                        )
                    else:
                        # Если API не вернул информацию, используем предустановленные настройки
                        instrument_info = get_instrument_info(symbol)
                        qty_step = instrument_info.get("qty_step", 0.001)
                        min_order_qty = instrument_info.get("min_qty", 0.001)
                        min_notional_value = instrument_info.get("min_notional", 5.0)
                        log_info(
                            f"[check_partial_tp] => Используем настройки из функции get_instrument_info: шаг={qty_step}, мин={min_order_qty}"
                        )

                    # Определяем, требуется ли целочисленное значение
                    requires_whole_number = qty_step >= 1.0

                    # Логируем полученные настройки для отладки
                    log_info(
                        f"[check_partial_tp] => Настройки инструмента {symbol} (исправленные):"
                    )
                    log_info(f"    Шаг количества: {qty_step}, Мин. количество: {min_order_qty}")
                    log_info(f"    Требует целые числа: {requires_whole_number}")
                    log_info(f"    Исходное количество для закрытия: {close_qty}")

                    # Округляем количество в соответствии с требованиями инструмента,
                    # используя функцию round_to_step из централизованного модуля
                    original_qty = close_qty

                    # Используем функцию round_to_step для согласованного поведения по всей системе
                    # Функция гарантирует, что количество не превысит допустимый объем
                    close_qty = round_qty(symbol, close_qty, round_up=False)
                    close_qty = max(min_order_qty, close_qty)

                    # Проверяем и адаптируем для инструментов, требующих целых чисел
                    if requires_whole_number or symbol in ["GALAUSDT", "WIFUSDT", "ENAUSDT"]:
                        close_qty = max(int(min_order_qty), int(close_qty))
                        log_info(
                            f"[check_partial_tp] => {symbol} требует целое число: {original_qty} -> {close_qty}"
                        )

                    # Проверяем, не превышает ли количество максимально допустимое
                    # Для рыночных ордеров используем maxMktOrderQty, который обычно меньше
                    max_allowed_qty = instrument_info.get(
                        "max_market_qty", 50000
                    )  # Используем лимит для рыночных ордеров
                    if close_qty > max_allowed_qty:
                        log_warn(
                            f"[check_partial_tp] => Количество {close_qty} превышает максимально допустимое {max_allowed_qty}, ограничиваем"
                        )
                        close_qty = max_allowed_qty

                    # Специальная обработка для ALGO
                    if "ALGO" in symbol:
                        old_qty = close_qty
                        close_qty = math.floor(close_qty * 10) / 10  # Округляем до 0.1 для ALGO
                        if old_qty != close_qty:
                            log_warn(
                                f"[check_partial_tp] => ALGO требует шаг 0.1: {old_qty} -> {close_qty}"
                            )

                    log_info(
                        f"[check_partial_tp] => Финальное округленное количество: {original_qty} -> {close_qty} (шаг: {qty_step})"
                    )

                    # Проверяем минимальную стоимость ордера (minNotionalValue)
                    min_notional_value = instrument_info.get("min_notional", 5.0)
                    log_info(
                        f"[check_partial_tp] => Минимальная стоимость ордера для {symbol}: {min_notional_value} USDT"
                    )

                    # Рассчитываем стоимость ордера
                    order_value = close_qty * current_price
                    log_info(
                        f"[check_partial_tp] => Стоимость ордера: {order_value} USDT (минимум: {min_notional_value} USDT)"
                    )

                    if order_value < min_notional_value:
                        # Если стоимость меньше минимальной, пробуем увеличить количество
                        adjusted_qty = (
                            math.ceil(min_notional_value / current_price / qty_step) * qty_step
                        )
                        decimal_places = -int(math.log10(qty_step)) if qty_step < 1 else 0
                        adjusted_qty = round(adjusted_qty, decimal_places)

                        log_info(
                            f"[check_partial_tp] => Стоимость ордера меньше минимальной, увеличиваем количество до {adjusted_qty}"
                        )
                        close_qty = adjusted_qty

                    # Дополнительно проверяем, что количество соответствует требованиям биржи
                    log_info(
                        f"[check_partial_tp] => Окончательное количество для закрытия: {close_qty} (шаг: {qty_step}, мин.: {min_order_qty})"
                    )

                    if close_qty <= 0 or close_qty < min_order_qty:
                        log_warn(
                            f"[check_partial_tp] => Рассчитанное количество {close_qty} меньше минимального {min_order_qty}"
                        )
                        return False

                    # Дополнительная проверка минимального количества
                    min_order_qty = instrument_info.get("min_qty", 0.001)

                    # Специальная обработка для известных криптовалют со специфическими требованиями

                    # ETH требует минимум 0.01 контракта, независимо от API
                    if "ETH" in symbol and min_order_qty < 0.01:
                        old_min = min_order_qty
                        min_order_qty = 0.01
                        # Если текущее количество меньше минимального
                        if close_qty < min_order_qty:
                            log_warn(
                                f"[check_partial_tp] => ETH требует минимум 0.01: {close_qty} -> {min_order_qty}"
                            )
                            close_qty = min_order_qty
                        log_warn(
                            f"[check_partial_tp] => Для {symbol} используем минимум 0.01 (вместо {old_min} из API)"
                        )

                    # ALGO требует шаг строго 0.1
                    if "ALGO" in symbol:
                        # Проверяем соответствие шагу 0.1 с учетом потенциальных проблем с плавающей запятой
                        remainder = close_qty % 0.1
                        if remainder > 0.000001:  # Если есть остаток
                            old_qty = close_qty
                            # Округляем до ближайшего 0.1 вниз
                            close_qty = math.floor(close_qty * 10) / 10
                            log_warn(
                                f"[check_partial_tp] => ALGO требует строгого шага 0.1: корректируем {old_qty} -> {close_qty}"
                            )

                    if close_qty < min_order_qty:
                        log_warn(
                            f"[check_partial_tp] => Рассчитанное количество {close_qty} меньше минимального {min_order_qty}, увеличиваем"
                        )
                        close_qty = min_order_qty

                    # Специальная обработка для ETH контрактов, где API возвращает ошибку
                    # "The number of contracts exceeds minimum limit allowed"
                    # хотя количество соответствует минимальному требованию
                    if symbol == "ETHUSDT" and close_qty < 0.01:
                        log_warn(
                            f"[check_partial_tp] => ETH требует минимум 0.01 контракта несмотря на minOrderQty={min_order_qty}"
                        )
                        close_qty = 0.01  # Установить минимум для ETH на 0.01 контракта

                    # НОВЫЙ КОД: Проверка, что мы не пытаемся закрыть больше, чем доступно
                    if close_qty > exchange_qty:
                        log_warn(
                            f"[check_partial_tp] => Рассчитанное количество {close_qty} больше доступного {exchange_qty}, корректируем"
                        )
                        close_qty = math.floor(exchange_qty / qty_step) * qty_step

                        # Проверяем, что после округления количество все еще корректное
                        if close_qty < min_order_qty:
                            log_warn(
                                f"[check_partial_tp] => После коррекции количество слишком мало: {close_qty} < {min_order_qty}, отменяем закрытие"
                            )
                            return False

                    # Уникальный индекс idx_partial_tp_unique_simple автоматически предотвратит дубликаты

                    # Сохраняем информацию об операции в историю частичных закрытий
                    history_entry = {
                        "trade_id": trade_id,
                        "level_percent": triggered_level["percent"],
                        "close_ratio": close_ratio,
                        "original_qty": float(original_position_qty),  # Изначальный размер позиции
                        "close_qty": float(close_qty),
                        "symbol": symbol,
                        "side": side,
                        "close_side": close_side,
                        "current_price": float(current_price),
                        "profit_percent": float(profit_percent),
                        "entry_price": float(entry_price),
                        "exchange_qty_before": float(exchange_qty),
                        "timestamp": time.time(),
                        "status": "pending",
                    }

                    # Сохраняем данные в таблицу partial_tp_history
                    log_info("[check_partial_tp] => Сохраняем данные в историю частичных закрытий")
                    history_id = None
                    try:
                        history_id = self._save_partial_tp_history(history_entry)
                        if history_id == -1:
                            log_info(
                                f"[check_partial_tp] => Уровень {triggered_level['percent']}% уже записан для trade_id={trade_id}, но продолжаем исполнение ордера"
                            )
                            # НЕ возвращаем False - продолжаем исполнение ордера
                        else:
                            log_info(
                                f"[check_partial_tp] => Данные успешно сохранены в таблицу partial_tp_history, ID: {history_id}"
                            )
                    except Exception as history_error:
                        log_error(
                            f"[check_partial_tp] => Ошибка при сохранении в историю: {history_error}"
                        )
                        import traceback

                        log_error(f"[check_partial_tp] => Трассировка: {traceback.format_exc()}")
                        return False  # Если не можем сохранить в историю, не создаем ордер

                    # Создаем ордер для частичного закрытия
                    order_id = None

                    log_info(
                        f"[check_partial_tp] => Создаем ордер для частичного закрытия: {close_side} {close_qty} {symbol}"
                    )

                    # Проверяем корректность параметров для инструмента
                    # и коррекция для всех монет перед отправкой на биржу
                    try:
                        # Получаем информацию об инструменте напрямую из API
                        direct_info = self.api_client.get_instrument_info(symbol)
                        if direct_info and "lotSizeFilter" in direct_info:
                            lot_size_filter = direct_info["lotSizeFilter"]
                            api_qty_step = float(lot_size_filter.get("qtyStep", "0.001"))
                            api_min_qty = float(lot_size_filter.get("minOrderQty", "0.001"))

                            log_info(
                                f"[check_partial_tp] => Параметры {symbol} из API: шаг={api_qty_step}, мин.={api_min_qty}"
                            )

                            # Округляем в соответствии с шагом инструмента
                            original_qty = close_qty
                            close_qty = math.floor(close_qty / api_qty_step) * api_qty_step

                            # Округляем до правильного количества десятичных знаков
                            decimal_places = (
                                -int(math.log10(api_qty_step)) if api_qty_step < 1 else 0
                            )
                            close_qty = round(close_qty, decimal_places)

                            # Проверяем минимальное количество
                            if close_qty < api_min_qty:
                                log_warn(
                                    f"[check_partial_tp] => Количество {close_qty} меньше минимального {api_min_qty}, устанавливаем минимальное"
                                )
                                close_qty = api_min_qty

                            log_info(
                                f"[check_partial_tp] => Скорректированное количество {symbol}: {original_qty} -> {close_qty}"
                            )
                    except Exception as api_error:
                        log_error(
                            f"[check_partial_tp] => Ошибка при получении API данных: {api_error}"
                        )

                    # Создаем реальный ордер для частичного закрытия
                    log_info(
                        f"[check_partial_tp] => Создаем рыночный ордер: {close_side} {close_qty} {symbol} (reduce_only=True)"
                    )

                    # ИСПРАВЛЕНИЕ: Используем правильный вызов API в зависимости от типа клиента
                    client_type = type(self.api_client).__name__
                    log_info(f"[check_partial_tp] => Используется API клиент: {client_type}")

                    if hasattr(self.api_client, "place_order"):
                        # Для BybitAPIClient - используем place_order с hedge_mode
                        # КРИТИЧЕСКИ ВАЖНО: При частичном закрытии в hedge mode
                        # нужно использовать positionIdx исходной позиции!
                        original_pos_idx = get_position_idx(side)  # positionIdx исходной позиции
                        log_info(
                            f"[check_partial_tp] => Создание ордера через BybitAPIClient.place_order с hedge_mode=True, positionIdx={original_pos_idx}"
                        )

                        # Создаем ордер напрямую через API с правильным positionIdx
                        order_result = self.api_client._make_request(
                            "POST",
                            "/v5/order/create",
                            {
                                "category": "linear",
                                "symbol": symbol,
                                "side": close_side,
                                "orderType": "Market",
                                "qty": str(close_qty),
                                "timeInForce": "IOC",
                                "reduceOnly": True,
                                "positionIdx": original_pos_idx,  # Используем positionIdx исходной позиции!
                            },
                            auth=True,
                        )
                    else:
                        # Для ApiClient - используем create_market_order без hedge_mode
                        log_info(
                            "[check_partial_tp] => Создание ордера через ApiClient.create_market_order БЕЗ hedge_mode"
                        )
                        order_result = self.api_client.create_market_order(
                            symbol=symbol, side=close_side, quantity=close_qty, reduce_only=True
                        )

                    # Проверяем результат ордера (учитываем что теперь используем сырой API ответ)
                    order_id = None
                    if order_result and order_result.get("retCode") == 0:
                        order_id = order_result.get("result", {}).get("orderId")

                    if not order_id:
                        log_error(
                            f"[check_partial_tp] => Ошибка при создании ордера для частичного закрытия: {order_result}"
                        )

                        # НОВЫЙ КОД: Обновляем историю частичных закрытий с ошибкой
                        if "history_entry" in locals() and "history_id" in locals() and history_id:
                            history_entry["status"] = "error"
                            history_entry["error"] = (
                                str(order_result) if order_result else "Unknown error"
                            )
                            history_entry["id"] = history_id  # Добавляем ID для обновления
                            self._update_partial_tp_history(history_entry)

                        # НОВЫЙ КОД: Анализируем ошибку, чтобы понять, стоит ли продолжать
                        error_msg = str(order_result).lower() if order_result else ""

                        # Особая обработка ошибки для ETH
                        eth_min_limit_error = (
                            isinstance(error_msg, str)
                            and "the number of contracts exceeds minimum limit allowed"
                            in error_msg.lower()
                            and "ETH" in symbol
                        )

                        # Новая обработка для ошибки Qty invalid - повторяем с исправленным округлением
                        qty_invalid_error = "qty invalid" in error_msg.lower()

                        if eth_min_limit_error:
                            log_warn(
                                "[check_partial_tp] => Получена ошибка превышения минимального лимита для ETH, продолжаем операцию как успешную"
                            )
                            # В этом особом случае мы продолжим с установкой SL в безубыток
                        elif qty_invalid_error:
                            log_warn(
                                "[check_partial_tp] => Получена ошибка Qty invalid, пробуем исправить округление"
                            )

                            # Определяем правильное округление на основе информации из API
                            adjusted_qty = close_qty

                            # Получаем настройки напрямую из API для гарантированной точности
                            try:
                                # Получаем информацию об инструменте напрямую из API
                                direct_info = self.api_client.get_instrument_info(symbol)
                                if direct_info and "lotSizeFilter" in direct_info:
                                    lot_size_filter = direct_info["lotSizeFilter"]
                                    real_qty_step = float(lot_size_filter.get("qtyStep", "0.001"))
                                    real_min_qty = float(
                                        lot_size_filter.get("minOrderQty", "0.001")
                                    )

                                    log_warn(
                                        f"[check_partial_tp] => При ошибке получены параметры напрямую из API: шаг={real_qty_step}, мин={real_min_qty}"
                                    )

                                    # Округляем до правильного шага (ВСЕГДА берем значения из API)
                                    adjusted_qty = (
                                        math.floor(close_qty / real_qty_step) * real_qty_step
                                    )

                                    # Проверяем минимум
                                    if adjusted_qty < real_min_qty:
                                        log_warn(
                                            f"[check_partial_tp] => Исправляем количество до минимального: {adjusted_qty} -> {real_min_qty}"
                                        )
                                        adjusted_qty = real_min_qty

                                    log_warn(
                                        f"[check_partial_tp] => Точное исправление из API для {symbol}: {close_qty} -> {adjusted_qty} (шаг: {real_qty_step})"
                                    )
                                else:
                                    # Если не удалось получить данные из API, обращаемся к предустановленным настройкам
                                    # для известных монет
                                    if "ETH" in symbol:
                                        # ETH имеет шаг 0.01 и минимум 0.01
                                        adjusted_qty = math.floor(close_qty / 0.01) * 0.01
                                        adjusted_qty = max(adjusted_qty, 0.01)
                                        log_warn(
                                            f"[check_partial_tp] => Для ETH используем фиксированное значение шага 0.01: {close_qty} -> {adjusted_qty}"
                                        )
                                    elif "LTC" in symbol:
                                        # LTC имеет шаг 0.1 и минимум 0.1
                                        adjusted_qty = math.floor(close_qty / 0.1) * 0.1
                                        adjusted_qty = max(adjusted_qty, 0.1)
                                        log_warn(
                                            f"[check_partial_tp] => Для LTC используем фиксированное значение шага 0.1: {close_qty} -> {adjusted_qty}"
                                        )
                                    elif "ALGO" in symbol:
                                        # ALGO имеет шаг 0.1 и минимум 0.1
                                        adjusted_qty = math.floor(close_qty / 0.1) * 0.1
                                        adjusted_qty = max(adjusted_qty, 0.1)
                                        log_warn(
                                            f"[check_partial_tp] => Для ALGO используем фиксированное значение шага 0.1: {close_qty} -> {adjusted_qty}"
                                        )
                                    else:
                                        # Для остальных монет используем безопасное значение
                                        adjusted_qty = math.floor(
                                            close_qty
                                        )  # Целое число всегда безопасно
                                        log_warn(
                                            f"[check_partial_tp] => Используем целое число для неизвестной монеты: {close_qty} -> {adjusted_qty}"
                                        )
                            except Exception as api_error:
                                log_error(
                                    f"[check_partial_tp] => Ошибка при получении информации из модуля instrument_settings: {api_error}"
                                )
                                # Попытка исправить, используя известные значения из INSTRUMENT_SETTINGS
                                try:
                                    # Пытаемся получить настройки из предустановленной таблицы
                                    from trading.instrument_settings import (
                                        DEFAULT_INSTRUMENT_SETTINGS,
                                        INSTRUMENT_SETTINGS,
                                    )

                                    backup_settings = INSTRUMENT_SETTINGS.get(
                                        symbol, DEFAULT_INSTRUMENT_SETTINGS
                                    )
                                    backup_qty_step = backup_settings.get("qtyStep", 0.001)

                                    log_warn(
                                        f"[check_partial_tp] => Используем резервные настройки из таблицы: шаг={backup_qty_step}"
                                    )
                                    adjusted_qty = round_qty(symbol, close_qty, round_up=False)
                                    log_warn(
                                        f"[check_partial_tp] => Резервное исправление: {close_qty} -> {adjusted_qty}"
                                    )
                                except Exception:
                                    # Если не удалось получить из таблицы, используем известные правила для монет
                                    if "ALGO" in symbol:
                                        adjusted_qty = math.floor(close_qty * 10) / 10  # Шаг 0.1
                                        log_warn(
                                            f"[check_partial_tp] => Для ALGO используем аварийный шаг 0.1: {close_qty} -> {adjusted_qty}"
                                        )
                                    elif "ETH" in symbol:
                                        adjusted_qty = math.floor(close_qty * 100) / 100  # Шаг 0.01
                                        adjusted_qty = max(adjusted_qty, 0.01)  # Минимум 0.01
                                        log_warn(
                                            f"[check_partial_tp] => Для ETH используем аварийный шаг 0.01: {close_qty} -> {adjusted_qty}"
                                        )
                                    else:
                                        # Для остальных монет более агрессивно округляем вниз
                                        adjusted_qty = (
                                            math.floor(close_qty * 100) / 100
                                        )  # Округляем до сотых
                                        log_warn(
                                            f"[check_partial_tp] => Аварийное округление до сотых: {close_qty} -> {adjusted_qty}"
                                        )

                            # Пробуем ещё раз с исправленным количеством, если оно не меньше минимального
                            order_id_found = False  # Флаг успешного создания ордера

                            if adjusted_qty >= min_order_qty:
                                try:
                                    # Финальная проверка для ALGO перед повторной попыткой
                                    if "ALGO" in symbol:
                                        remainder = adjusted_qty % 0.1
                                        if remainder > 0.000001:  # Если есть остаток
                                            old_qty = adjusted_qty
                                            adjusted_qty = math.floor(adjusted_qty * 10) / 10
                                            log_warn(
                                                f"[check_partial_tp] => ФИНАЛЬНАЯ проверка перед retry для ALGO: {old_qty} -> {adjusted_qty}"
                                            )

                                    log_info(
                                        f"[check_partial_tp] => Повторная попытка с исправленным количеством: {close_side} {adjusted_qty} {symbol}"
                                    )
                                    # ИСПРАВЛЕНИЕ: Используем правильный вызов API для retry
                                    if hasattr(self.api_client, "place_order"):
                                        retry_result = self.api_client.place_order(
                                            symbol=symbol,
                                            side=close_side,
                                            qty=adjusted_qty,
                                            order_type="Market",
                                            reduce_only=True,
                                            hedge_mode=True,
                                        )
                                    else:
                                        retry_result = self.api_client.create_market_order(
                                            symbol=symbol,
                                            side=close_side,
                                            quantity=adjusted_qty,
                                            reduce_only=True,
                                        )

                                    if retry_result and retry_result.get("order_id"):
                                        order_id = retry_result.get("order_id")
                                        log_info(
                                            f"[check_partial_tp] => Успех после корректировки! Ордер: {order_id}"
                                        )

                                        # Обновляем запись в истории
                                        if "history_entry" in locals():
                                            history_entry["status"] = "executed"
                                            history_entry["order_id"] = order_id
                                            history_entry["close_qty"] = float(adjusted_qty)
                                            self._update_partial_tp_history(history_entry)

                                        # Отмечаем успех и обновляем количество для дальнейшей работы
                                        close_qty = adjusted_qty
                                        order_id_found = True
                                except Exception as retry_error:
                                    log_error(
                                        f"[check_partial_tp] => Ошибка при повторной попытке: {retry_error}"
                                    )

                            # Проверяем результат повторной попытки
                            if not order_id_found:
                                log_warn(
                                    "[check_partial_tp] => Не удалось исправить ошибку Qty invalid, отменяем операцию"
                                )
                                return False
                        elif "exceeds" in error_msg or "zero position" in error_msg:
                            log_warn(
                                "[check_partial_tp] => Критическая ошибка API при частичном закрытии, отменяем операцию"
                            )
                            return False

                        # Даже если API запрос не удался, мы продолжим и запишем событие в историю
                        log_info(
                            "[check_partial_tp] => Записываем информацию о частичном закрытии в историю, несмотря на ошибку API"
                        )
                    else:
                        # Ордер успешно создан
                        log_info(
                            f"[check_partial_tp] => ✅ УСПЕШНО создан ордер для частичного закрытия: {order_id}"
                        )
                        log_info(
                            f"[check_partial_tp] => ✅ Частичное закрытие выполнено: {close_side} {close_qty} {symbol} (positionIdx={original_pos_idx})"
                        )

                        # НОВЫЙ КОД: Обновляем историю частичных закрытий со статусом успеха
                        if "history_entry" in locals():
                            history_entry["status"] = "executed"
                            history_entry["order_id"] = order_id
                            self._update_partial_tp_history(history_entry)

                except Exception as e:
                    log_error(
                        f"[check_partial_tp] => Ошибка при выполнении частичного закрытия: {e}"
                    )
                    log_error(traceback.format_exc())

                    # НОВЫЙ КОД: Обновляем историю частичных закрытий с ошибкой
                    if "history_entry" in locals():
                        history_entry["status"] = "error"
                        history_entry["error"] = str(e)
                        self._update_partial_tp_history(history_entry)

                    # НОВЫЙ КОД: При серьезной ошибке прерываем операцию
                    return False

                # Создаем запись о выполненном уровне с информацией о созданном ордере
                executed_level = {
                    "percent": triggered_level["percent"],
                    "close_ratio": close_ratio,
                    "qty": close_qty,
                    "price": current_price,
                    "timestamp": time.time(),
                    "order_id": order_id if "order_id" in locals() and order_id else None,
                    "status": "executed" if "order_id" in locals() and order_id else "recorded",
                }

                # Добавляем выполненный уровень в историю
                executed_levels.append(executed_level)

                # НОВЫЙ КОД: Удаляем старые записи с тем же процентом
                # Оставляем только последнюю запись для каждого уровня
                unique_levels = {}
                for level in executed_levels:
                    percent = level.get("percent")
                    if percent not in unique_levels or level.get("timestamp", 0) > unique_levels[
                        percent
                    ].get("timestamp", 0):
                        unique_levels[percent] = level
                executed_levels = list(unique_levels.values())

                # Обновляем данные в репозитории
                if sltp:
                    extra_data = sltp.extra_data or {}
                    # НЕ сериализуем в JSON строку - храним как список
                    extra_data["partial_tp_executed"] = executed_levels
                    sltp.extra_data = extra_data
                    sltp.updated_at = time.time()
                    # Преобразовываем объект sltp в словарь для передачи в метод update
                    sltp_data = sltp.to_dict()
                    sltp_id = sltp_data.pop("id", None)
                    if sltp_id:
                        # Добавляем trade_id обратно в данные для использования insert_or_update
                        # trade_id содержится в sltp.trade_id
                        sltp_data["trade_id"] = sltp.trade_id
                        # Используем метод insert_or_update вместо update для совместимости с потокобезопасным репозиторием
                        # FIX: Используем подходящий метод в зависимости от доступности
                        try:
                            if hasattr(self.sltp_repository, "create_or_update"):
                                result = self.sltp_repository.create_or_update(
                                    sltp_data, "trade_id"
                                )
                                log_info(
                                    "[check_partial_tp] => Использован метод create_or_update"
                                )
                            elif hasattr(self.sltp_repository, "insert_or_update"):
                                result = self.sltp_repository.insert_or_update(sltp_data)
                                log_info(
                                    "[check_partial_tp] => Использован метод insert_or_update"
                                )
                            else:
                                # Если нет ни того, ни другого, пробуем обновить
                                if hasattr(sltp, "id") and sltp.id:
                                    # Обновляем поля в объекте sltp
                                    for key, value in sltp_data.items():
                                        if hasattr(sltp, key):
                                            setattr(sltp, key, value)
                                    result = self.sltp_repository.update(sltp)
                                    log_info("[check_partial_tp] => Использован метод update")
                                else:
                                    result = False
                                    log_error(
                                        "[check_partial_tp] => Не удалось найти подходящий метод для обновления"
                                    )
                        except Exception as repo_error:
                            log_error(
                                f"[check_partial_tp] => Ошибка при обновлении данных через репозиторий: {repo_error}"
                            )
                            result = False
                        if not result:
                            log_error(
                                "[check_partial_tp] => Ошибка при обновлении данных о частичном закрытии"
                            )
                        log_info(
                            f"[check_partial_tp] => Данные о частичном закрытии сохранены: {json.dumps(executed_levels)}"
                        )
                    else:
                        log_error(
                            "[check_partial_tp] => Не удалось сохранить данные о частичном закрытии: отсутствует ID"
                        )
                else:
                    # Если записи SLTP не существует, создаем новую
                    sltp_data = {
                        "trade_id": trade_id,
                        "symbol": symbol,
                        "side": side,
                        "entry_price": entry_price,
                        "stop_loss_price": None,  # Добавляем правильные имена полей для PostgreSQL
                        "take_profit_price": None,  # Добавляем правильные имена полей для PostgreSQL
                        # НЕ сериализуем executed_levels - храним как список
                        "extra_data": {"partial_tp_executed": executed_levels},
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    }
                    # В PostgreSQL репозитории метод называется create() вместо insert()
                    from db.models import SLTPOrder

                    sltp_order = SLTPOrder.from_dict(sltp_data)
                    self.sltp_repository.create(sltp_order)
                    log_info(
                        "[check_partial_tp] => Создана новая запись SLTP с данными о частичном закрытии"
                    )

                # Если нужно обновить SL после частичного закрытия
                if settings.get("update_sl_after_partial", False):
                    # КОНФЛИКТ-ФИХ: Проверяем, не установила ли profit_protection более выгодный SL
                    current_sltp = self.sltp_repository.get_by_trade_id(trade_id)
                    current_sl = current_sltp.stop_loss_price if current_sltp else None

                    # Устанавливаем SL в безубыток
                    if side.upper() == "SELL":
                        # Для Sell позиций безубыток на 0.1% ниже entry_price
                        breakeven_price = entry_price * 0.999
                        # Проверяем, не лучше ли текущий SL (для SELL меньший SL лучше)
                        if current_sl and current_sl < breakeven_price:
                            log_info(
                                f"[check_partial_tp] => Текущий SL {current_sl} лучше безубытка {breakeven_price}, пропускаем обновление"
                            )
                            return (
                                True  # Возвращаем True, так как частичное закрытие было выполнено
                            )
                    else:  # BUY
                        # Для Buy позиций безубыток на 0.1% выше entry_price
                        breakeven_price = entry_price * 1.001
                        # Проверяем, не лучше ли текущий SL (для BUY больший SL лучше)
                        if current_sl and current_sl > breakeven_price:
                            log_info(
                                f"[check_partial_tp] => Текущий SL {current_sl} лучше безубытка {breakeven_price}, пропускаем обновление"
                            )
                            return (
                                True  # Возвращаем True, так как частичное закрытие было выполнено
                            )

                    # Получаем настройки инструмента и размер тика для корректного округления стоп-лосса
                    instrument_info = get_instrument_info(symbol)
                    tick_size = instrument_info.get("tick_size", 0.001)

                    log_info(
                        f"[check_partial_tp] => Настройки инструмента {symbol} для SL: tick_size={tick_size}"
                    )

                    # Устанавливаем максимальный процент изменения SL от текущей цены
                    max_sl_change_percent = 5.0

                    # Логика особой обработки для проблемных инструментов
                    if symbol in ["GALAUSDT", "TRXUSDT", "MATICUSDT", "ENAUSDT"]:
                        # Для проблемных инструментов с малым размером тика
                        log_info(f"[check_partial_tp] => Специальная обработка для {symbol}")

                        # Вычисляем количество тиков и округляем
                        if side.upper() == "SELL":
                            ticks = math.ceil(breakeven_price / tick_size)
                            # Проверяем на максимальное изменение
                            max_allowed_sl = current_price * (1 + max_sl_change_percent / 100)
                            max_ticks = math.ceil(max_allowed_sl / tick_size)
                            if ticks > max_ticks:
                                log_warn(
                                    f"[check_partial_tp] => Новый SL {breakeven_price} слишком высок для {symbol}! Ограничиваем"
                                )
                                ticks = max_ticks
                        else:  # BUY
                            ticks = math.floor(breakeven_price / tick_size)
                            # Проверяем на максимальное изменение
                            min_allowed_sl = current_price * (1 - max_sl_change_percent / 100)
                            min_ticks = math.floor(min_allowed_sl / tick_size)
                            if ticks < min_ticks:
                                log_warn(
                                    f"[check_partial_tp] => Новый SL {breakeven_price} слишком низок для {symbol}! Ограничиваем"
                                )
                                ticks = min_ticks

                        # Преобразуем обратно в цену, кратную тику
                        breakeven_price = ticks * tick_size
                    else:
                        # Для остальных инструментов - обычное округление
                        if side.upper() == "SELL":
                            # Для SELL округляем вверх для безопасности (SL должен быть выше текущей цены)
                            breakeven_price = math.ceil(breakeven_price / tick_size) * tick_size
                            # Проверяем на максимальное изменение
                            max_allowed_sl = current_price * (1 + max_sl_change_percent / 100)
                            if breakeven_price > max_allowed_sl:
                                log_warn(
                                    f"[check_partial_tp] => Новый SL {breakeven_price} слишком высок! Ограничиваем до {max_allowed_sl}"
                                )
                                breakeven_price = math.ceil(max_allowed_sl / tick_size) * tick_size
                        else:  # BUY
                            # Для BUY округляем вниз для безопасности (SL должен быть ниже текущей цены)
                            breakeven_price = math.floor(breakeven_price / tick_size) * tick_size
                            # Проверяем на максимальное изменение
                            min_allowed_sl = current_price * (1 - max_sl_change_percent / 100)
                            if breakeven_price < min_allowed_sl:
                                log_warn(
                                    f"[check_partial_tp] => Новый SL {breakeven_price} слишком низок! Ограничиваем до {min_allowed_sl}"
                                )
                                breakeven_price = math.floor(min_allowed_sl / tick_size) * tick_size

                    # Округляем цену с использованием правильного менеджера инструментов
                    breakeven_price = round_price(
                        symbol, breakeven_price, round_up=(side.upper() == "SELL")
                    )

                    log_info(
                        f"[check_partial_tp] => Установка SL в безубыток после частичного закрытия: {breakeven_price} (тик: {tick_size})"
                    )

                    # Определяем правильный positionIdx для hedge режима
                    pos_idx = get_position_idx(side)

                    # Устанавливаем новый SL
                    result = set_trading_stop(
                        symbol=symbol,
                        side=side,
                        pos_idx=pos_idx,
                        stop_loss=breakeven_price,
                        trade_id=trade_id,
                    )

                    # Проверяем результат (добавляем дополнительное логирование)
                    log_info(
                        f"[apply_profit_protection] => Результат API запроса: {json.dumps(result, default=str)}"
                    )
                    success = result.get("retCode") == 0
                    not_modified = result.get("retCode") == 34040 or (
                        result.get("retMsg") and "not modified" in result.get("retMsg", "")
                    )

                    if success or not_modified:
                        # Обновляем информацию в БД
                        if sltp:
                            # Создаем словарь с обновленными данными
                            sltp_update = {
                                "stop_loss_price": breakeven_price,  # Правильное имя поля для БД
                                "updated_at": datetime.now(),
                            }
                            # Обновляем через репозиторий
                            # Добавляем trade_id в данные для использования insert_or_update
                            sltp_update["trade_id"] = trade_id
                            # FIX: Используем подходящий метод в зависимости от доступности
                            try:
                                if hasattr(self.sltp_repository, "create_or_update"):
                                    result = self.sltp_repository.create_or_update(
                                        sltp_update, "trade_id"
                                    )
                                    log_info(
                                        "[check_partial_tp] => Использован метод create_or_update"
                                    )
                                elif hasattr(self.sltp_repository, "insert_or_update"):
                                    result = self.sltp_repository.insert_or_update(sltp_update)
                                    log_info(
                                        "[check_partial_tp] => Использован метод insert_or_update"
                                    )
                                else:
                                    # Если нет ни того, ни другого, пробуем обновить
                                    result = False
                                    log_error(
                                        "[check_partial_tp] => Не удалось найти подходящий метод для обновления"
                                    )
                            except Exception as repo_error:
                                log_error(
                                    f"[check_partial_tp] => Ошибка при обновлении данных через репозиторий: {repo_error}"
                                )
                                result = False

                            if not result:
                                log_error(
                                    "[check_partial_tp] => Ошибка при обновлении SL после частичного закрытия"
                                )

                        # Обновляем сделку
                        trade_data = {"stop_loss": breakeven_price}
                        self.trade_repository.update(trade.id, trade_data)

                        log_info(
                            f"[check_partial_tp] => SL успешно перемещен в безубыток: {breakeven_price:.6f}"
                        )
                    else:
                        log_error(
                            f"[check_partial_tp] => Ошибка при установке SL в безубыток: {result.get('retMsg', 'Unknown error')}"
                        )

                return True

            except Exception as e:
                log_error(f"[check_partial_tp] => Ошибка: {e}")
                import traceback

                log_error(traceback.format_exc())
                return False

    def apply_enhanced_sltp(self, trade_id: int, exchange_positions=None) -> bool:
        """
        Применяет все улучшенные функции SL/TP к указанной сделке.

        Args:
            trade_id: ID сделки

        Returns:
            bool: True, если были применены какие-либо улучшения, False в противном случае
        """
        log_info(
            f"[apply_enhanced_sltp] => Применение улучшенных функций SL/TP к сделке {trade_id}"
        )

        with self._lock:
            try:
                # Флаги для отслеживания изменений
                changes_made = False

                # 1. Применяем трейлинг-стоп
                trailing_result = self.apply_trailing_stop(trade_id)
                if trailing_result:
                    changes_made = True
                    log_info(f"[apply_enhanced_sltp] => Трейлинг-стоп применен для {trade_id}")

                # 2. Проверяем многоуровневый частичный тейк-профит ПЕРЕД защитой прибыли
                partial_tp_result = self.check_partial_tp(trade_id, exchange_positions)
                if partial_tp_result:
                    changes_made = True
                    log_info(
                        f"[apply_enhanced_sltp] => Частичный тейк-профит применен для {trade_id}"
                    )

                # 3. Применяем защиту прибыли ПОСЛЕ частичного закрытия (более приоритетна)
                protection_result = self.apply_profit_protection(trade_id)
                if protection_result:
                    changes_made = True
                    log_info(f"[apply_enhanced_sltp] => Защита прибыли применена для {trade_id}")

                return changes_made

            except Exception as e:
                log_error(
                    f"[apply_enhanced_sltp] => Ошибка при применении улучшенных функций SL/TP: {e}"
                )
                log_error(traceback.format_exc())
                return False


# Создаем глобальный экземпляр для использования без необходимости создавать объект
_enhanced_sltp_manager = None


def get_enhanced_sltp_manager(
    config: dict[str, Any] | None = None, api_client=None
) -> EnhancedSLTPManager:
    """
    Возвращает глобальный экземпляр EnhancedSLTPManager.

    Args:
        config (Dict[str, Any], optional): Конфигурация для менеджера
        api_client: Клиент API биржи

    Returns:
        EnhancedSLTPManager: Экземпляр улучшенного менеджера SL/TP
    """
    global _enhanced_sltp_manager
    if _enhanced_sltp_manager is None:
        _enhanced_sltp_manager = EnhancedSLTPManager(config=config, api_client=api_client)
    return _enhanced_sltp_manager
