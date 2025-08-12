"""
Bybit Client для BOT_Trading v3.0

Мигрированный и улучшенный клиент Bybit API с поддержкой:
- Унифицированного интерфейса
- API v5 Bybit
- Асинхронных операций
- Расширенной обработки ошибок
- Автоматических повторных попыток
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import aiohttp

from core.exceptions import LeverageError
from core.logger import setup_logger

from ..base.api_key_manager import KeyType, get_key_manager

# from ..base.rate_limiter import RequestPriority, get_rate_limiter  # Заменено на EnhancedRateLimiter
from ..base.enhanced_rate_limiter import (  # Оптимизированный rate limiter
    EnhancedRateLimiter,
)
from ..base.exceptions import (
    APIError,
    AuthenticationError,
    ConnectionError,
    MarketDataError,
    OrderError,
    PositionError,
    RateLimitError,
    create_api_error_from_response,
    extract_retry_after,
    is_rate_limit_error,
)
from ..base.exchange_interface import BaseExchangeInterface, ExchangeCapabilities
from ..base.health_monitor import get_health_monitor
from ..base.models import (
    AccountInfo,
    Balance,
    ExchangeInfo,
    Instrument,
    Kline,
    Order,
    OrderBook,
    Position,
    Ticker,
    create_order_from_dict,
    create_position_from_dict,
)
from ..base.order_types import OrderRequest, OrderResponse, OrderStatus, OrderType


def clean_symbol(symbol: str) -> str:
    """Очищает символ от суффиксов для корректной работы с Bybit API"""
    if not symbol:
        return symbol

    # Удаляем суффикс .P для perpetual контрактов
    cleaned = symbol.replace(".P", "")
    return cleaned


def safe_float(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float с обработкой пустых строк"""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class BybitClient(BaseExchangeInterface):
    """
    Клиент для работы с Bybit API v5

    Реализует унифицированный интерфейс BaseExchangeInterface
    с полной поддержкой всех возможностей Bybit API.
    """

    def __init__(
        self, api_key: str, api_secret: str, sandbox: bool = False, timeout: int = 30
    ):
        super().__init__(api_key, api_secret, sandbox, timeout)

        # Логирование
        self.logger = setup_logger("bybit_client")

        # Инициализация оптимизированного rate limiter
        self.enhanced_limiter = EnhancedRateLimiter(
            exchange="bybit", enable_cache=True, cache_ttl=60, max_retries=3
        )

        # Определяем режим публичного доступа
        self.public_only = api_key == "public_access" and api_secret == "public_access"
        if self.public_only:
            self.logger.info("Bybit client initialized in public-only mode")

        # Bybit API URLs
        if sandbox:
            self.base_url = "https://api-testnet.bybit.com"
        else:
            self.base_url = "https://api.bybit.com"

        # Настройки HTTP
        self.session: Optional[aiohttp.ClientSession] = None
        self.retry_count = 3
        self.retry_delay = 1

        # Метрики
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_errors = []

        # Rate limiter - используем только enhanced версию
        # self.rate_limiter = get_rate_limiter()  # Удалено - используем enhanced_limiter

        # API Key manager
        self.key_manager = get_key_manager()

        # Health monitor
        self.health_monitor = get_health_monitor()

        # Регистрируем ключи в менеджере (если не публичный режим)
        if not self.public_only:
            self.key_manager.add_key(
                exchange_name="bybit",
                api_key=api_key,
                api_secret=api_secret,
                key_type=KeyType.MAIN,
            )

        # Добавляем биржу в мониторинг здоровья
        self.health_monitor.add_exchange("bybit")

        # Загружаем конфигурацию торговли
        self.hedge_mode = False
        self.default_leverage = 5
        self.trading_category = "linear"
        try:
            import yaml

            # Пытаемся загрузить настройки из system.yaml
            config_path = "config/system.yaml"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    system_config = yaml.safe_load(f)
                if system_config and "trading" in system_config:
                    trading_cfg = system_config["trading"]
                    self.hedge_mode = trading_cfg.get("hedge_mode", False)
                    self.default_leverage = trading_cfg.get("leverage", 5)
                    self.trading_category = trading_cfg.get("category", "linear")
                    self.logger.debug(
                        f"Trading config loaded: hedge_mode={self.hedge_mode}, leverage={self.default_leverage}, category={self.trading_category}"
                    )
        except Exception as e:
            self.logger.warning(f"Failed to load trading config, using defaults: {e}")

        # Кеш для инструментов
        self._instruments_cache: Dict[str, List[Instrument]] = {}
        self._cache_expiry: Dict[str, datetime] = {}

    # =================== БАЗОВЫЕ СВОЙСТВА ===================

    @property
    def name(self) -> str:
        return "bybit"

    @property
    def capabilities(self) -> ExchangeCapabilities:
        return ExchangeCapabilities(
            spot_trading=True,
            futures_trading=True,
            margin_trading=True,
            market_orders=True,
            limit_orders=True,
            stop_orders=True,
            stop_limit_orders=True,
            websocket_public=True,
            websocket_private=True,
            position_management=True,
            leverage_trading=True,
            max_leverage=100.0,
            min_order_size=0.001,
            max_order_size=1000000.0,
            rate_limit_public=120,  # requests per minute
            rate_limit_private=120,
        )

    # =================== ПОДКЛЮЧЕНИЕ ===================

    async def connect(self) -> bool:
        """Установка соединения с Bybit"""
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                self.session = aiohttp.ClientSession(timeout=timeout)

            # Тест соединения
            success = await self.test_connection()
            if success:
                self._connected = True
                self.logger.info("Successfully connected to Bybit")

            return success

        except Exception as e:
            self.logger.error(f"Failed to connect to Bybit: {e}")
            raise ConnectionError("bybit", reason=str(e))

    async def disconnect(self) -> None:
        """Отключение от Bybit"""
        if self.session:
            await self.session.close()
            self.session = None

        self._connected = False
        self.logger.info("Disconnected from Bybit")

    async def test_connection(self) -> bool:
        """Тестирование соединения"""
        try:
            response = await self._make_request("GET", "/v5/market/time")
            return response.get("retCode", -1) == 0
        except Exception:
            return False

    async def get_server_time(self) -> datetime:
        """Получение времени сервера"""
        try:
            response = await self._make_request("GET", "/v5/market/time")
            if response.get("retCode") == 0:
                timestamp = int(response.get("result", {}).get("timeSecond", 0))
                return datetime.fromtimestamp(timestamp)
        except Exception as e:
            self.logger.error(f"Failed to get server time: {e}")

        return datetime.now()

    # =================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===================

    def _generate_signature(self, params: Union[str, Dict], timestamp: str) -> str:
        """Генерация подписи для запроса"""
        recv_window = "5000"

        if isinstance(params, dict):
            # POST запрос
            param_str = json.dumps(params) if params else ""
            payload = timestamp + self.api_key + recv_window + param_str
        else:
            # GET запрос
            payload = timestamp + self.api_key + recv_window + (params or "")

        signature = hmac.new(
            bytes(self.api_secret, "utf-8"), bytes(payload, "utf-8"), hashlib.sha256
        ).hexdigest()

        return signature

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        auth: bool = False,
        priority: str = "normal",  # Изменено с RequestPriority
        use_cache: bool = True,  # Добавлен параметр для кэширования
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса с rate limiting, кэшированием и повторными попытками"""

        if not self.session:
            await self.connect()

        # Для GET запросов проверяем кэш (только для публичных эндпоинтов)
        if method == "GET" and use_cache and not auth:
            cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
            cached_result = self.enhanced_limiter.get_cached(cache_key)
            if cached_result is not None:
                self.logger.debug(f"Cache hit for {endpoint}")
                return cached_result

        # Применяем rate limiting
        # Используем enhanced rate limiter
        await self.enhanced_limiter.check_and_wait()

        try:
            url = f"{self.base_url}{endpoint}"
            headers = {}

            # Подготовка параметров
            query_string = ""
            json_data = None

            if params:
                if method == "GET":
                    query_string = urlencode(params)
                    url = f"{url}?{query_string}"
                else:
                    json_data = params

            # Аутентификация
            if auth:
                # В публичном режиме пропускаем аутентификацию
                if self.public_only:
                    self.logger.debug(
                        f"Skipping authentication for public-only mode: {endpoint}"
                    )
                else:
                    # Получаем актуальный ключ из менеджера
                    key_info = await self.key_manager.get_active_key("bybit")
                    if not key_info:
                        raise AuthenticationError("bybit", "NO_VALID_KEY")

                    timestamp = str(int(time.time() * 1000))
                    sign_params = (
                        json.dumps(params)
                        if method == "POST" and params
                        else query_string
                    )

                    # Используем ключи из менеджера
                    signature = hmac.new(
                        bytes(key_info.api_secret, "utf-8"),
                        bytes(
                            timestamp + key_info.api_key + "5000" + (sign_params or ""),
                            "utf-8",
                        ),
                        hashlib.sha256,
                    ).hexdigest()

                    headers.update(
                        {
                            "X-BAPI-API-KEY": key_info.api_key,
                            "X-BAPI-TIMESTAMP": timestamp,
                            "X-BAPI-SIGN": signature,
                            "X-BAPI-RECV-WINDOW": "5000",
                        }
                    )

            if method == "POST":
                headers["Content-Type"] = "application/json"

            # Выполнение запроса с exponential backoff
            for attempt in range(self.retry_count + 1):
                try:
                    self.request_count += 1
                    start_time = time.time()

                    if attempt > 0:
                        # Exponential backoff с jitter
                        base_delay = self.retry_delay * (2 ** (attempt - 1))
                        jitter = base_delay * 0.1 * (time.time() % 1)  # 10% jitter
                        delay = min(base_delay + jitter, 60)  # макс 60 секунд

                        await asyncio.sleep(delay)
                        self.logger.info(
                            f"Retry attempt {attempt} for {method} {endpoint} after {delay:.1f}s"
                        )

                    # Выполнение запроса
                    if method == "GET":
                        async with self.session.get(url, headers=headers) as response:
                            response_data = await response.json()
                            status_code = response.status
                            response_headers = dict(response.headers)
                    elif method == "POST":
                        async with self.session.post(
                            url, headers=headers, json=json_data
                        ) as response:
                            response_data = await response.json()
                            status_code = response.status
                            response_headers = dict(response.headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    response_time = time.time() - start_time

                    # Проверка HTTP статуса
                    if status_code != 200:
                        if status_code == 429:  # Rate limit
                            retry_after = extract_retry_after(
                                response_data, response_headers
                            )
                            # self.rate_limiter.record_error(  # Заменено на enhanced_limiter
                            self.logger.warning(
                                f"Rate limit error: {endpoint}, retry after {retry_after}"
                            )

                            if attempt < self.retry_count:
                                await asyncio.sleep(retry_after or 60)
                                continue

                            raise RateLimitError("bybit", retry_after=retry_after)

                        elif (
                            status_code in [500, 502, 503, 504]
                            and attempt < self.retry_count
                        ):
                            # Server errors - продолжаем попытки
                            # self.rate_limiter.record_error(  # Заменено на enhanced_limiter
                            self.logger.warning(
                                f"Rate limit error: {endpoint}, status {status_code}"
                            )
                            continue

                        raise APIError(
                            "bybit",
                            f"{method} {endpoint}",
                            status_code=status_code,
                            api_message=f"HTTP {status_code}",
                        )

                    # Проверка кода ответа Bybit
                    ret_code = response_data.get("retCode", 0)
                    if ret_code != 0:
                        ret_msg = response_data.get("retMsg", "Unknown error")

                        # Проверка на rate limit
                        if is_rate_limit_error(str(ret_code), "bybit"):
                            retry_after = extract_retry_after(
                                response_data, response_headers
                            )
                            # self.rate_limiter.record_error(  # Заменено на enhanced_limiter
                            self.logger.warning(
                                f"Rate limit error: {endpoint}, code {ret_code}, retry after {retry_after}"
                            )

                            if attempt < self.retry_count:
                                await asyncio.sleep(retry_after or 60)
                                continue

                            raise RateLimitError("bybit", retry_after=retry_after)

                        # Повторная попытка для определенных ошибок
                        retry_codes = [
                            10002,  # Invalid request
                            10006,  # Rate limit exceeded
                            10018,  # Request too frequent
                            20001,  # Order not exists
                            20022,  # Reduce-only rule not satisfied
                            20025,  # Position idx not match position mode
                            20027,  # Position size is zero
                            20033,  # Position is in liquidation
                        ]
                        if ret_code in retry_codes and attempt < self.retry_count:
                            # self.rate_limiter.record_error(  # Заменено на enhanced_limiter
                            self.logger.warning(
                                f"Rate limit error: {endpoint}, code {ret_code}"
                            )
                            continue

                        # Создание соответствующего исключения
                        # self.rate_limiter.record_error("bybit", endpoint, str(ret_code))  # Заменено
                        self.logger.warning(f"API error {ret_code} for {endpoint}")

                        # Записываем ошибку в Key Manager
                        if auth:
                            is_auth_error = str(ret_code) in [
                                "10003",
                                "10004",
                                "10005",
                            ]  # Auth errors
                            self.key_manager.record_request_failure(
                                "bybit", str(ret_code), is_auth_error
                            )

                        raise create_api_error_from_response(
                            "bybit", f"{method} {endpoint}", response_data, status_code
                        )

                    # Успешный ответ
                    self.success_count += 1
                    # self.rate_limiter.record_success("bybit", endpoint, response_time)  # Заменено
                    pass  # Enhanced limiter автоматически отслеживает успешные запросы
                    if auth:  # Записываем успех только для аутентифицированных запросов
                        self.key_manager.record_request_success("bybit")

                    # Кэшируем успешный GET результат (только для публичных эндпоинтов)
                    if method == "GET" and use_cache and not auth:
                        cache_key = (
                            f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
                        )
                        self.enhanced_limiter.cache_result(cache_key, response_data)
                        self.logger.debug(f"Cached result for {endpoint}")

                    return response_data

                except aiohttp.ClientError as e:
                    # self.rate_limiter.record_error("bybit", endpoint, "CLIENT_ERROR")  # Заменено
                    self.logger.error(f"Client error for {endpoint}")

                    if attempt < self.retry_count:
                        continue

                    self.error_count += 1
                    raise ConnectionError("bybit", reason=str(e))

                except (RateLimitError, AuthenticationError, APIError):
                    # Эти исключения уже обработаны выше
                    raise

                except Exception:
                    # self.rate_limiter.record_error("bybit", endpoint, "UNKNOWN_ERROR")  # Заменено
                    self.logger.error(f"Unknown error for {endpoint}")

                    if attempt < self.retry_count:
                        continue
                    raise

            # Если дошли сюда - все попытки неудачны
            self.error_count += 1
            # self.rate_limiter.record_error("bybit", endpoint, "ALL_RETRIES_FAILED")  # Заменено
            self.logger.error(f"All retries failed for {endpoint}")
            raise APIError(
                "bybit", f"{method} {endpoint}", api_message="All retry attempts failed"
            )

        except Exception:
            # Записываем ошибку в rate limiter для случаев, когда блок try не был выполнен
            # rate_limiter.record_error("bybit", endpoint, "UNKNOWN_ERROR")  # Заменено
            self.logger.error(f"Unknown error for {endpoint}")
            raise

    # =================== ИНФОРМАЦИЯ О БИРЖЕ ===================

    async def get_exchange_info(self) -> ExchangeInfo:
        """Получение информации о бирже"""
        try:
            server_time = await self.get_server_time()

            return ExchangeInfo(
                exchange_name="bybit",
                timezone="UTC",
                server_time=server_time,
                supported_order_types=["Market", "Limit", "StopMarket", "StopLimit"],
                supported_time_in_force=["GTC", "IOC", "FOK"],
                status="NORMAL",
            )
        except Exception as e:
            raise MarketDataError("bybit", "exchange_info", reason=str(e))

    async def get_instruments(self, category: Optional[str] = None) -> List[Instrument]:
        """Получение списка торговых инструментов"""
        try:
            category = category or "linear"

            # Проверка кеша
            cache_key = category
            if (
                cache_key in self._instruments_cache
                and cache_key in self._cache_expiry
                and datetime.now() < self._cache_expiry[cache_key]
            ):
                return self._instruments_cache[cache_key]

            params = {"category": category}
            response = await self._make_request(
                "GET", "/v5/market/instruments-info", params
            )

            instruments = []
            result = response.get("result", {})
            instruments_list = result.get("list", [])

            for item in instruments_list:
                instrument = Instrument(
                    symbol=item.get("symbol", ""),
                    base_currency=item.get("baseCoin", ""),
                    quote_currency=item.get("quoteCoin", ""),
                    category=category,
                    min_order_qty=float(
                        item.get("lotSizeFilter", {}).get("minOrderQty", "0")
                    ),
                    max_order_qty=float(
                        item.get("lotSizeFilter", {}).get("maxOrderQty", "1000000")
                    ),
                    qty_step=float(
                        item.get("lotSizeFilter", {}).get("qtyStep", "0.001")
                    ),
                    min_price=float(item.get("priceFilter", {}).get("minPrice", "0")),
                    max_price=float(
                        item.get("priceFilter", {}).get("maxPrice", "1000000")
                    ),
                    tick_size=float(
                        item.get("priceFilter", {}).get("tickSize", "0.01")
                    ),
                    status=item.get("status", "Trading"),
                    is_tradable=item.get("status") == "Trading",
                    max_leverage=float(
                        item.get("leverageFilter", {}).get("maxLeverage", "1")
                    ),
                    margin_trading=category in ["linear", "inverse"],
                )
                instruments.append(instrument)

            # Обновление кеша
            self._instruments_cache[cache_key] = instruments
            self._cache_expiry[cache_key] = datetime.now() + timedelta(hours=1)

            return instruments

        except Exception as e:
            raise MarketDataError("bybit", "instruments", reason=str(e))

    async def get_instrument_info(self, symbol: str) -> Instrument:
        """Получение информации о конкретном инструменте"""
        try:
            # Попробуем найти в кеше
            for cached_instruments in self._instruments_cache.values():
                for instrument in cached_instruments:
                    if instrument.symbol == clean_symbol(symbol):
                        return instrument

            # Если не найден в кеше, загружаем все инструменты
            instruments = await self.get_instruments("linear")
            for instrument in instruments:
                if instrument.symbol == clean_symbol(symbol):
                    return instrument

            # Попробуем spot категорию
            instruments = await self.get_instruments("spot")
            for instrument in instruments:
                if instrument.symbol == clean_symbol(symbol):
                    return instrument

            raise ValueError(f"Instrument {symbol} not found")

        except Exception as e:
            raise MarketDataError(
                "bybit", "instrument_info", symbol=symbol, reason=str(e)
            )

    # =================== АККАУНТ И БАЛАНСЫ ===================

    async def get_account_info(self) -> AccountInfo:
        """Получение информации об аккаунте"""
        try:
            params = {"accountType": "UNIFIED"}
            response = await self._make_request(
                "GET", "/v5/account/wallet-balance", params, auth=True
            )

            result = response.get("result", {})
            account_list = result.get("list", [])

            if not account_list:
                raise ValueError("No account data found")

            account_data = account_list[0]

            return AccountInfo(
                account_type="UNIFIED",
                account_id=account_data.get("accountIMRate", ""),
                total_equity=float(account_data.get("totalEquity", "0")),
                total_wallet_balance=float(account_data.get("totalWalletBalance", "0")),
                total_margin_balance=float(account_data.get("totalMarginBalance", "0")),
                available_balance=float(account_data.get("totalAvailableBalance", "0")),
                total_initial_margin=float(account_data.get("totalInitialMargin", "0")),
                total_maintenance_margin=float(
                    account_data.get("totalMaintenanceMargin", "0")
                ),
                can_trade=True,
                can_withdraw=True,
                can_deposit=True,
                last_update=datetime.now(),
            )

        except Exception as e:
            raise APIError("bybit", "get_account_info", api_message=str(e))

    async def get_balances(self, account_type: Optional[str] = None) -> List[Balance]:
        """Получение балансов аккаунта"""
        try:
            account_type = account_type or "UNIFIED"
            params = {"accountType": account_type}
            response = await self._make_request(
                "GET", "/v5/account/wallet-balance", params, auth=True
            )

            result = response.get("result", {})
            account_list = result.get("list", [])

            balances = []
            for account in account_list:
                coin_list = account.get("coin", [])
                for coin_data in coin_list:
                    balance = Balance(
                        currency=coin_data.get("coin", ""),
                        total=float(coin_data.get("walletBalance", "0")),
                        available=float(coin_data.get("transferBalance", "0")),
                        frozen=float(coin_data.get("locked", "0")),
                        account_type=account_type,
                        last_update=datetime.now(),
                    )
                    balances.append(balance)

            return balances

        except Exception as e:
            raise APIError("bybit", "get_balances", api_message=str(e))

    async def get_balance(
        self, currency: str, account_type: Optional[str] = None
    ) -> Balance:
        """Получение баланса конкретной валюты"""
        balances = await self.get_balances(account_type)

        for balance in balances:
            if balance.currency.upper() == currency.upper():
                return balance

        # Если баланс не найден, возвращаем нулевой баланс
        return Balance(
            currency=currency.upper(),
            total=0.0,
            available=0.0,
            frozen=0.0,
            account_type=account_type or "UNIFIED",
            last_update=datetime.now(),
        )

    # =================== РЫНОЧНЫЕ ДАННЫЕ ===================

    async def get_ticker(self, symbol: str) -> Ticker:
        """Получение тикера инструмента"""
        try:
            symbol = clean_symbol(symbol)
            params = {"category": "linear", "symbol": symbol}

            response = await self._make_request("GET", "/v5/market/tickers", params)
            result = response.get("result", {})
            ticker_list = result.get("list", [])

            if not ticker_list:
                raise ValueError(f"Ticker for {symbol} not found")

            ticker_data = ticker_list[0]

            return Ticker(
                symbol=symbol,
                last_price=float(ticker_data.get("lastPrice", "0")),
                bid_price=float(ticker_data.get("bid1Price", "0")),
                ask_price=float(ticker_data.get("ask1Price", "0")),
                high_24h=float(ticker_data.get("highPrice24h", "0")),
                low_24h=float(ticker_data.get("lowPrice24h", "0")),
                volume_24h=float(ticker_data.get("volume24h", "0")),
                price_change_24h=float(ticker_data.get("price24hPcnt", "0")) * 100,
                open_price=float(ticker_data.get("prevPrice24h", "0")),
                bid_size=float(ticker_data.get("bid1Size", "0")),
                ask_size=float(ticker_data.get("ask1Size", "0")),
                timestamp=datetime.now(),
            )

        except Exception as e:
            raise MarketDataError("bybit", "ticker", symbol=symbol, reason=str(e))

    async def get_tickers(self, category: Optional[str] = None) -> List[Ticker]:
        """Получение тикеров всех инструментов"""
        try:
            category = category or "linear"
            params = {"category": category}

            response = await self._make_request("GET", "/v5/market/tickers", params)
            result = response.get("result", {})
            ticker_list = result.get("list", [])

            tickers = []
            for ticker_data in ticker_list:
                ticker = Ticker(
                    symbol=ticker_data.get("symbol", ""),
                    last_price=float(ticker_data.get("lastPrice", "0")),
                    bid_price=float(ticker_data.get("bid1Price", "0")),
                    ask_price=float(ticker_data.get("ask1Price", "0")),
                    high_24h=float(ticker_data.get("highPrice24h", "0")),
                    low_24h=float(ticker_data.get("lowPrice24h", "0")),
                    volume_24h=float(ticker_data.get("volume24h", "0")),
                    price_change_24h=float(ticker_data.get("price24hPcnt", "0")) * 100,
                    open_price=float(ticker_data.get("prevPrice24h", "0")),
                    timestamp=datetime.now(),
                )
                tickers.append(ticker)

            return tickers

        except Exception as e:
            raise MarketDataError("bybit", "tickers", reason=str(e))

    async def get_orderbook(self, symbol: str, limit: int = 25) -> OrderBook:
        """Получение стакана ордеров"""
        try:
            symbol = clean_symbol(symbol)
            params = {
                "category": "linear",
                "symbol": symbol,
                "limit": min(limit, 50),  # Bybit максимум 50
            }

            response = await self._make_request("GET", "/v5/market/orderbook", params)
            result = response.get("result", {})

            from ..base.models import OrderBookEntry

            bids = []
            asks = []

            # Обработка bids
            for bid in result.get("b", []):
                if len(bid) >= 2:
                    bids.append(
                        OrderBookEntry(price=float(bid[0]), quantity=float(bid[1]))
                    )

            # Обработка asks
            for ask in result.get("a", []):
                if len(ask) >= 2:
                    asks.append(
                        OrderBookEntry(price=float(ask[0]), quantity=float(ask[1]))
                    )

            return OrderBook(
                symbol=symbol, bids=bids, asks=asks, timestamp=datetime.now()
            )

        except Exception as e:
            raise MarketDataError("bybit", "orderbook", symbol=symbol, reason=str(e))

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Kline]:
        """Получение свечных данных"""
        try:
            symbol = clean_symbol(symbol)

            # Конвертируем интервал в формат Bybit API
            bybit_interval = (
                interval.replace("m", "") if interval.endswith("m") else interval
            )

            params = {
                "category": "linear",
                "symbol": symbol,
                "interval": bybit_interval,  # Используем конвертированный интервал
                "limit": min(limit, 1000),  # Bybit максимум 1000
            }

            if start_time:
                params["start"] = int(start_time.timestamp() * 1000)
            if end_time:
                params["end"] = int(end_time.timestamp() * 1000)

            response = await self._make_request("GET", "/v5/market/kline", params)
            result = response.get("result", {})
            klines_data = result.get("list", [])

            klines = []
            for kline_data in klines_data:
                if len(kline_data) >= 6:
                    open_time = datetime.fromtimestamp(int(kline_data[0]) / 1000)
                    close_time = open_time + timedelta(minutes=1)  # Примерно

                    kline = Kline(
                        symbol=symbol,
                        interval=interval,
                        open_time=open_time,
                        close_time=close_time,
                        open_price=float(kline_data[1]),
                        high_price=float(kline_data[2]),
                        low_price=float(kline_data[3]),
                        close_price=float(kline_data[4]),
                        volume=float(kline_data[5]),
                        trades_count=int(float(kline_data[6]))
                        if len(kline_data) > 6
                        else 0,
                    )
                    klines.append(kline)

            return klines

        except Exception as e:
            raise MarketDataError("bybit", "klines", symbol=symbol, reason=str(e))

    # =================== УПРАВЛЕНИЕ ОРДЕРАМИ ===================

    def _get_position_idx(self, side: str, hedge_mode: Optional[bool] = None) -> int:
        """Определение position index для Bybit API"""
        # ИСПРАВЛЕНО: Аккаунт на самом деле в hedge mode, а не one-way
        # Hedge mode: 1=Buy/Long, 2=Sell/Short
        return 1 if side.upper() in ["BUY", "LONG"] else 2

    def _map_order_type_to_bybit(self, order_type: OrderType) -> str:
        """Маппинг типов ордеров к формату Bybit"""
        mapping = {
            OrderType.MARKET: "Market",
            OrderType.LIMIT: "Limit",
            OrderType.STOP_MARKET: "Market",
            OrderType.STOP_LIMIT: "Limit",
            OrderType.TAKE_PROFIT_MARKET: "Market",
            OrderType.TAKE_PROFIT_LIMIT: "Limit",
        }
        return mapping.get(order_type, "Market")

    def _map_bybit_order_status(self, bybit_status: str) -> OrderStatus:
        """Маппинг статусов ордеров Bybit к унифицированным"""
        mapping = {
            "New": OrderStatus.NEW,
            "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "Rejected": OrderStatus.REJECTED,
            "PartiallyFilledCanceled": OrderStatus.CANCELLED,
            "Untriggered": OrderStatus.PENDING,
            "Deactivated": OrderStatus.DEACTIVATED,
            "Triggered": OrderStatus.TRIGGERED,
            "Active": OrderStatus.NEW,
        }
        return mapping.get(bybit_status, OrderStatus.NEW)

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Размещение ордера"""
        try:
            # Валидация запроса
            validation_errors = order_request.validate()
            if validation_errors:
                return OrderResponse.error_response(
                    f"Validation failed: {'; '.join(validation_errors)}"
                )

            symbol = clean_symbol(order_request.symbol)
            position_idx = self._get_position_idx(order_request.side.value)

            # Устанавливаем leverage для символа (если задан)
            leverage = getattr(order_request, "leverage", self.default_leverage)
            if leverage and leverage > 0:
                try:
                    await self.set_leverage(symbol, leverage)
                except Exception as e:
                    self.logger.warning(f"Failed to set leverage for {symbol}: {e}")

            # Подготовка параметров
            params = {
                "category": self.trading_category,  # Используем category из конфигурации
                "symbol": symbol,
                "side": order_request.side.value,
                "orderType": self._map_order_type_to_bybit(order_request.order_type),
                "qty": str(order_request.quantity),
                "timeInForce": order_request.time_in_force.value,
            }

            # Добавляем positionIdx только если не 0 (Bybit игнорирует 0)
            if position_idx != 0:
                params["positionIdx"] = position_idx

            # Добавляем цену для лимитных ордеров
            if order_request.price is not None:
                params["price"] = str(order_request.price)

            # Добавляем стоп цену
            if order_request.stop_price is not None:
                params["triggerPrice"] = str(order_request.stop_price)

            # Дополнительные параметры
            if order_request.reduce_only:
                params["reduceOnly"] = True
            if order_request.close_on_trigger:
                params["closeOnTrigger"] = True
            if order_request.client_order_id:
                params["orderLinkId"] = order_request.client_order_id

            # SL/TP параметры
            if order_request.stop_loss is not None:
                params["stopLoss"] = str(order_request.stop_loss)
            if order_request.take_profit is not None:
                params["takeProfit"] = str(order_request.take_profit)

            # Добавляем exchange-специфичные параметры
            params.update(order_request.exchange_params)

            self.logger.info(
                f"Placing order: {symbol} {order_request.side.value} {order_request.quantity} {order_request.order_type.value}"
            )
            self.logger.info(f"Order params: {params}")

            # Выполнение запроса с высоким приоритетом для ордеров
            response = await self._make_request(
                "POST",
                "/v5/order/create",
                params,
                auth=True,
                priority="high",
            )

            result = response.get("result", {})
            order_id = result.get("orderId", "")

            if order_id:
                self.logger.info(f"Order placed successfully: {order_id}")
                return OrderResponse.success_response(
                    order_id=order_id,
                    symbol=symbol,
                    side=order_request.side,
                    order_type=order_request.order_type,
                    quantity=order_request.quantity,
                    client_order_id=order_request.client_order_id,
                    created_time=datetime.now(),
                )
            else:
                error_msg = response.get("retMsg", "Unknown error")
                return OrderResponse.error_response(error_msg)

        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            raise OrderError(
                "bybit", "placement", symbol=order_request.symbol, reason=str(e)
            )

    async def cancel_order(self, symbol: str, order_id: str) -> OrderResponse:
        """Отмена ордера"""
        try:
            symbol = clean_symbol(symbol)
            params = {"category": "linear", "symbol": symbol, "orderId": order_id}

            self.logger.info(f"Cancelling order: {order_id} for {symbol}")

            response = await self._make_request(
                "POST",
                "/v5/order/cancel",
                params,
                auth=True,
                priority="high",
            )
            result = response.get("result", {})

            cancelled_order_id = result.get("orderId", order_id)

            return OrderResponse.success_response(
                order_id=cancelled_order_id,
                symbol=symbol,
                side=None,
                order_type=None,
                quantity=0,
                status=OrderStatus.CANCELLED,
                updated_time=datetime.now(),
            )

        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            raise OrderError(
                "bybit", "cancellation", order_id=order_id, symbol=symbol, reason=str(e)
            )

    async def cancel_all_orders(
        self, symbol: Optional[str] = None
    ) -> List[OrderResponse]:
        """Отмена всех ордеров"""
        try:
            params = {"category": "linear"}

            if symbol:
                params["symbol"] = clean_symbol(symbol)

            self.logger.info(
                "Cancelling all orders" + (f" for {symbol}" if symbol else "")
            )

            response = await self._make_request(
                "POST",
                "/v5/order/cancel-all",
                params,
                auth=True,
                priority="critical",
            )
            result = response.get("result", {})

            # Bybit возвращает список отмененных ордеров
            cancelled_orders = result.get("list", [])
            responses = []

            for order_data in cancelled_orders:
                responses.append(
                    OrderResponse.success_response(
                        order_id=order_data.get("orderId", ""),
                        symbol=order_data.get("symbol", symbol or ""),
                        side=None,
                        order_type=None,
                        quantity=0,
                        status=OrderStatus.CANCELLED,
                        updated_time=datetime.now(),
                    )
                )

            return responses

        except Exception as e:
            self.logger.error(f"Failed to cancel all orders: {e}")
            raise OrderError("bybit", "cancel_all", symbol=symbol, reason=str(e))

    async def modify_order(
        self,
        symbol: str,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
    ) -> OrderResponse:
        """Модификация ордера"""
        try:
            symbol = clean_symbol(symbol)
            params = {"category": "linear", "symbol": symbol, "orderId": order_id}

            if quantity is not None:
                params["qty"] = str(quantity)
            if price is not None:
                params["price"] = str(price)

            if not quantity and not price:
                raise ValueError(
                    "Either quantity or price must be specified for order modification"
                )

            self.logger.info(
                f"Modifying order {order_id}: qty={quantity}, price={price}"
            )

            response = await self._make_request(
                "POST", "/v5/order/amend", params, auth=True
            )
            result = response.get("result", {})

            modified_order_id = result.get("orderId", order_id)

            return OrderResponse.success_response(
                order_id=modified_order_id,
                symbol=symbol,
                side=None,
                order_type=None,
                quantity=quantity or 0,
                price=price,
                updated_time=datetime.now(),
            )

        except Exception as e:
            self.logger.error(f"Failed to modify order {order_id}: {e}")
            raise OrderError(
                "bybit", "modification", order_id=order_id, symbol=symbol, reason=str(e)
            )

    async def get_order(self, symbol: str, order_id: str) -> Order:
        """Получение информации об ордере"""
        try:
            symbol = clean_symbol(symbol)
            params = {"category": "linear", "orderId": order_id}

            response = await self._make_request(
                "GET", "/v5/order/realtime", params, auth=True
            )
            result = response.get("result", {})
            order_list = result.get("list", [])

            if not order_list:
                from ..base.exceptions import OrderNotFoundError

                raise OrderNotFoundError("bybit", order_id, symbol)

            order_data = order_list[0]

            return create_order_from_dict(
                {
                    "orderId": order_data.get("orderId", ""),
                    "clientOrderId": order_data.get("orderLinkId"),
                    "symbol": order_data.get("symbol", ""),
                    "side": order_data.get("side", ""),
                    "orderType": order_data.get("orderType", ""),
                    "quantity": order_data.get("qty", "0"),
                    "price": order_data.get("price", "0"),
                    "filledQty": order_data.get("cumExecQty", "0"),
                    "orderStatus": order_data.get("orderStatus", "New"),
                    "timeInForce": order_data.get("timeInForce", "GTC"),
                    "avgPrice": order_data.get("avgPrice", "0"),
                    "reduceOnly": order_data.get("reduceOnly", False),
                    "createdTime": order_data.get("createdTime"),
                    "updatedTime": order_data.get("updatedTime"),
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to get order {order_id}: {e}")
            raise OrderError(
                "bybit", "lookup", order_id=order_id, symbol=symbol, reason=str(e)
            )

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Получение активных ордеров"""
        try:
            params = {"category": "linear"}

            if symbol:
                params["symbol"] = clean_symbol(symbol)
            else:
                # Bybit API требует один из параметров: symbol, settleCoin или baseCoin
                # Используем settleCoin для получения всех ордеров по USDT
                params["settleCoin"] = "USDT"

            response = await self._make_request(
                "GET", "/v5/order/realtime", params, auth=True
            )
            result = response.get("result", {})
            order_list = result.get("list", [])

            orders = []
            for order_data in order_list:
                order = create_order_from_dict(
                    {
                        "orderId": order_data.get("orderId", ""),
                        "clientOrderId": order_data.get("orderLinkId"),
                        "symbol": order_data.get("symbol", ""),
                        "side": order_data.get("side", ""),
                        "orderType": order_data.get("orderType", ""),
                        "quantity": safe_float(order_data.get("qty", "0")),
                        "price": safe_float(order_data.get("price", "0")),
                        "filledQty": safe_float(order_data.get("cumExecQty", "0")),
                        "orderStatus": order_data.get("orderStatus", "New"),
                        "timeInForce": order_data.get("timeInForce", "GTC"),
                        "avgPrice": safe_float(order_data.get("avgPrice", "0")),
                        "reduceOnly": order_data.get("reduceOnly", False),
                        "createdTime": order_data.get("createdTime"),
                        "updatedTime": order_data.get("updatedTime"),
                    }
                )
                orders.append(order)

            return orders

        except Exception as e:
            self.logger.error(f"Failed to get open orders: {e}")
            raise OrderError("bybit", "list", symbol=symbol, reason=str(e))

    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Order]:
        """Получение истории ордеров"""
        try:
            params = {"category": "linear", "limit": min(limit, 50)}  # Bybit limit

            if symbol:
                params["symbol"] = clean_symbol(symbol)
            if start_time:
                params["startTime"] = int(start_time.timestamp() * 1000)
            if end_time:
                params["endTime"] = int(end_time.timestamp() * 1000)

            response = await self._make_request(
                "GET", "/v5/order/history", params, auth=True
            )
            result = response.get("result", {})
            order_list = result.get("list", [])

            orders = []
            for order_data in order_list:
                order = create_order_from_dict(
                    {
                        "orderId": order_data.get("orderId", ""),
                        "clientOrderId": order_data.get("orderLinkId"),
                        "symbol": order_data.get("symbol", ""),
                        "side": order_data.get("side", ""),
                        "orderType": order_data.get("orderType", ""),
                        "quantity": safe_float(order_data.get("qty", "0")),
                        "price": safe_float(order_data.get("price", "0")),
                        "filledQty": safe_float(order_data.get("cumExecQty", "0")),
                        "orderStatus": order_data.get("orderStatus", "New"),
                        "timeInForce": order_data.get("timeInForce", "GTC"),
                        "avgPrice": safe_float(order_data.get("avgPrice", "0")),
                        "reduceOnly": order_data.get("reduceOnly", False),
                        "createdTime": order_data.get("createdTime"),
                        "updatedTime": order_data.get("updatedTime"),
                    }
                )
                orders.append(order)

            return orders

        except Exception as e:
            self.logger.error(f"Failed to get order history: {e}")
            raise OrderError("bybit", "history", symbol=symbol, reason=str(e))

    # =================== УПРАВЛЕНИЕ ПОЗИЦИЯМИ ===================

    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Получение открытых позиций"""
        try:
            params = {"category": "linear"}

            if symbol:
                params["symbol"] = clean_symbol(symbol)
            else:
                # Добавляем settleCoin для получения всех позиций
                params["settleCoin"] = "USDT"

            response = await self._make_request(
                "GET", "/v5/position/list", params, auth=True
            )
            result = response.get("result", {})

            # Обработка разных форматов ответа
            if isinstance(result, dict):
                positions_list = result.get("list", [])
            elif isinstance(result, list):
                positions_list = result
            else:
                positions_list = []

            positions = []
            for pos_data in positions_list:
                if not isinstance(pos_data, dict):
                    continue

                # Пропускаем позиции с нулевым размером
                size = float(pos_data.get("size", "0"))
                if size == 0:
                    continue

                position = create_position_from_dict(
                    {
                        "symbol": pos_data.get("symbol", ""),
                        "side": pos_data.get("side", "None"),
                        "size": str(size),
                        "entryPrice": pos_data.get("avgPrice", "0"),
                        "markPrice": pos_data.get("markPrice", "0"),
                        "unrealisedPnl": pos_data.get("unrealisedPnl", "0"),
                        "leverage": pos_data.get("leverage", "1"),
                        "positionMargin": pos_data.get("positionIM", "0"),
                        "liqPrice": (
                            pos_data.get("liqPrice", "0")
                            if pos_data.get("liqPrice", "0") != "0"
                            else None
                        ),
                        "stopLoss": (
                            pos_data.get("stopLoss", "0")
                            if pos_data.get("stopLoss", "0") != "0"
                            else None
                        ),
                        "takeProfit": (
                            pos_data.get("takeProfit", "0")
                            if pos_data.get("takeProfit", "0") != "0"
                            else None
                        ),
                        "positionMode": pos_data.get("positionMode", "MergedSingle"),
                        "autoAddMargin": pos_data.get("autoAddMargin", 0) == 1,
                        "createdTime": pos_data.get("createdTime"),
                        "updatedTime": pos_data.get("updatedTime"),
                    }
                )
                positions.append(position)

            return positions

        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            raise PositionError("bybit", "list", symbol or "all", reason=str(e))

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Получение конкретной позиции"""
        try:
            positions = await self.get_positions(symbol)

            # Ищем позицию с указанным символом
            for position in positions:
                if position.symbol == clean_symbol(symbol) and position.is_open:
                    return position

            # Возвращаем пустую позицию если не найдена
            from ..base.models import create_empty_position

            return create_empty_position(clean_symbol(symbol))

        except Exception as e:
            self.logger.error(f"Failed to get position for {symbol}: {e}")
            raise PositionError("bybit", "lookup", symbol, reason=str(e))

    async def close_position(
        self, symbol: str, quantity: Optional[float] = None
    ) -> OrderResponse:
        """Закрытие позиции"""
        try:
            # Получаем текущую позицию
            position = await self.get_position(symbol)

            if not position or not position.is_open:
                raise ValueError(f"No open position found for {symbol}")

            # Определяем сторону для закрытия
            close_side = "Sell" if position.is_long else "Buy"
            close_quantity = quantity or abs(position.size)

            # Создаем рыночный ордер для закрытия
            from ..base.order_types import OrderRequest, OrderSide, OrderType

            order_request = OrderRequest(
                symbol=symbol,
                side=OrderSide.SELL if close_side == "Sell" else OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=close_quantity,
                reduce_only=True,
                client_order_id=f"close_{symbol}_{int(time.time())}",
            )

            self.logger.info(
                f"Closing position: {symbol} {close_side} {close_quantity}"
            )

            return await self.place_order(order_request)

        except Exception as e:
            self.logger.error(f"Failed to close position for {symbol}: {e}")
            raise PositionError("bybit", "close", symbol, reason=str(e))

    async def set_leverage(self, symbol: str, leverage: float) -> bool:
        """Установка плеча для символа"""
        try:
            symbol = clean_symbol(symbol)
            params = {
                "category": self.trading_category,
                "symbol": symbol,
                "buyLeverage": str(leverage),
                "sellLeverage": str(leverage),
            }

            self.logger.info(f"Setting leverage for {symbol}: {leverage}x")

            response = await self._make_request(
                "POST", "/v5/position/set-leverage", params, auth=True
            )

            # Проверяем успешность операции
            ret_code = response.get("retCode", -1)
            if ret_code == 0:
                self.logger.info(f"Leverage set successfully for {symbol}: {leverage}x")
                return True
            else:
                error_msg = response.get("retMsg", "Unknown error")
                self.logger.error(f"Failed to set leverage: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to set leverage for {symbol}: {e}")
            raise LeverageError("bybit", symbol, leverage, reason=str(e))

    async def set_position_mode(self, symbol: str, hedge_mode: bool) -> bool:
        """Установка режима позиции (hedge/one-way)"""
        try:
            symbol = clean_symbol(symbol)
            mode = 3 if hedge_mode else 0  # 0=OneWay, 3=Hedge

            params = {"category": "linear", "symbol": symbol, "mode": mode}

            self.logger.info(
                f"Setting position mode for {symbol}: {'Hedge' if hedge_mode else 'One-Way'}"
            )

            response = await self._make_request(
                "POST", "/v5/position/switch-mode", params, auth=True
            )

            ret_code = response.get("retCode", -1)
            if ret_code == 0:
                self.logger.info(f"Position mode set successfully for {symbol}")
                return True
            else:
                error_msg = response.get("retMsg", "Unknown error")
                self.logger.error(f"Failed to set position mode: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to set position mode for {symbol}: {e}")
            raise PositionError("bybit", "set_mode", symbol, reason=str(e))

    async def set_stop_loss(
        self, symbol: str, stop_price: float, quantity: Optional[float] = None
    ) -> OrderResponse:
        """
        Установка Stop Loss для позиции

        Args:
            symbol: Торговый символ
            stop_price: Цена срабатывания stop loss
            quantity: Количество (если None, то для всей позиции)

        Returns:
            OrderResponse с результатом операции
        """
        try:
            symbol = clean_symbol(symbol)

            # Получаем текущую позицию для определения режима
            positions = await self.get_positions(symbol)
            if not positions:
                return OrderResponse.error_response("No position found for symbol")

            params = {
                "category": "linear",
                "symbol": symbol,
                "tpslMode": "Full",  # Полное закрытие позиции
                "stopLoss": str(stop_price),
                "positionIdx": 0,  # One-way mode по умолчанию
            }

            # Если есть позиция, определяем positionIdx
            position = positions[0]
            if hasattr(position, "side") and position.side:
                # Hedge mode
                params["positionIdx"] = 1 if position.side.upper() == "BUY" else 2

            self.logger.info(f"Setting stop loss for {symbol} at price {stop_price}")
            response = await self._make_request(
                "POST", "/v5/position/trading-stop", params, auth=True
            )

            if response.get("retCode") == 0:
                self.logger.info(f"Stop loss set successfully for {symbol}")
                return OrderResponse.success_response(
                    order_id=None,
                    status=OrderStatus.PENDING,
                    message="Stop loss set successfully",
                )
            else:
                error_msg = response.get("retMsg", "Unknown error")
                self.logger.error(f"Failed to set stop loss: {error_msg}")
                return OrderResponse.error_response(
                    f"Failed to set stop loss: {error_msg}"
                )

        except Exception as e:
            self.logger.error(f"Error setting stop loss for {symbol}: {e}")
            return OrderResponse.error_response(f"Error setting stop loss: {str(e)}")

    async def set_take_profit(
        self, symbol: str, take_price: float, quantity: Optional[float] = None
    ) -> OrderResponse:
        """
        Установка Take Profit для позиции

        Args:
            symbol: Торговый символ
            take_price: Цена срабатывания take profit
            quantity: Количество (если None, то для всей позиции)

        Returns:
            OrderResponse с результатом операции
        """
        try:
            symbol = clean_symbol(symbol)

            # Получаем текущую позицию для определения режима
            positions = await self.get_positions(symbol)
            if not positions:
                return OrderResponse.error_response("No position found for symbol")

            params = {
                "category": "linear",
                "symbol": symbol,
                "tpslMode": "Full",  # Полное закрытие позиции
                "takeProfit": str(take_price),
                "positionIdx": 0,  # One-way mode по умолчанию
            }

            # Если есть позиция, определяем positionIdx
            position = positions[0]
            if hasattr(position, "side") and position.side:
                # Hedge mode
                params["positionIdx"] = 1 if position.side.upper() == "BUY" else 2

            self.logger.info(f"Setting take profit for {symbol} at price {take_price}")
            response = await self._make_request(
                "POST", "/v5/position/trading-stop", params, auth=True
            )

            if response.get("retCode") == 0:
                self.logger.info(f"Take profit set successfully for {symbol}")
                return OrderResponse.success_response(
                    order_id=None,
                    status=OrderStatus.PENDING,
                    message="Take profit set successfully",
                )
            else:
                error_msg = response.get("retMsg", "Unknown error")
                self.logger.error(f"Failed to set take profit: {error_msg}")
                return OrderResponse.error_response(
                    f"Failed to set take profit: {error_msg}"
                )

        except Exception as e:
            self.logger.error(f"Error setting take profit for {symbol}: {e}")
            return OrderResponse.error_response(f"Error setting take profit: {str(e)}")

    async def modify_stop_loss(
        self, symbol: str, new_stop_price: float
    ) -> OrderResponse:
        """
        Модификация Stop Loss для позиции

        Args:
            symbol: Торговый символ
            new_stop_price: Новая цена срабатывания stop loss

        Returns:
            OrderResponse с результатом операции
        """
        return await self.set_stop_loss(symbol, new_stop_price)

    async def modify_take_profit(
        self, symbol: str, new_take_price: float
    ) -> OrderResponse:
        """
        Модификация Take Profit для позиции

        Args:
            symbol: Торговый символ
            new_take_price: Новая цена срабатывания take profit

        Returns:
            OrderResponse с результатом операции
        """
        return await self.set_take_profit(symbol, new_take_price)

    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Получение истории сделок - будет реализовано"""
        pass

    async def start_websocket(self, channels: List[str], callback: callable) -> bool:
        """Запуск WebSocket - будет реализовано"""
        pass

    async def stop_websocket(self) -> None:
        """Остановка WebSocket - будет реализовано"""
        pass

    async def subscribe_ticker(self, symbol: str, callback: callable) -> bool:
        """Подписка на тикер - будет реализовано"""
        pass

    async def subscribe_orderbook(self, symbol: str, callback: callable) -> bool:
        """Подписка на стакан - будет реализовано"""
        pass

    async def subscribe_trades(self, symbol: str, callback: callable) -> bool:
        """Подписка на сделки - будет реализовано"""
        pass

    async def subscribe_orders(self, callback: callable) -> bool:
        """Подписка на ордеры - будет реализовано"""
        pass

    async def subscribe_positions(self, callback: callable) -> bool:
        """Подписка на позиции - будет реализовано"""
        pass

    # =================== АЛИАСЫ ДЛЯ СОВМЕСТИМОСТИ ===================

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Dict = None,
    ) -> List[List]:
        """
        Метод для совместимости с ccxt интерфейсом

        Args:
            symbol: Торговый символ
            timeframe: Временной интервал
            since: Начальная временная метка в миллисекундах
            limit: Количество свечей
            params: Дополнительные параметры

        Returns:
            Список свечей в формате [timestamp, open, high, low, close, volume]
        """
        try:
            # Конвертируем параметры
            start_time = datetime.fromtimestamp(since / 1000) if since else None
            end_time = None
            if limit is None:
                limit = 500

            # Получаем данные
            klines = await self.get_klines(
                symbol=symbol,
                interval=timeframe,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )

            # Конвертируем в формат ccxt
            result = []
            for kline in klines:
                result.append(
                    [
                        int(kline.open_time.timestamp() * 1000),  # timestamp
                        kline.open_price,  # open
                        kline.high_price,  # high
                        kline.low_price,  # low
                        kline.close_price,  # close
                        kline.volume,  # volume
                    ]
                )

            # Сортируем по времени (от старых к новым)
            result.sort(key=lambda x: x[0])

            return result

        except Exception as e:
            self.logger.error(f"Ошибка fetch_ohlcv для {symbol}: {e}")
            raise

    # =================== HEALTH MONITORING ===================

    def get_health_status(self) -> Dict[str, Any]:
        """Получение статуса здоровья биржи"""
        status = self.health_monitor.get_exchange_status("bybit")

        if not status:
            return {
                "exchange": "bybit",
                "status": "unknown",
                "message": "Health monitoring not initialized",
            }

        return {
            "exchange": "bybit",
            "status": status.overall_status.value,
            "uptime": f"{status.uptime_percentage:.1f}%",
            "avg_latency": f"{status.avg_latency:.1f}ms",
            "consecutive_failures": status.consecutive_failures,
            "last_check": status.last_check.isoformat(),
            "checks": {
                check_type.value: {
                    "status": result.status.value,
                    "latency_ms": result.latency_ms,
                    "error": result.error_message,
                }
                for check_type, result in status.checks.items()
            },
            "is_healthy": status.is_healthy,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Получение метрик производительности"""
        # rate_limit_stats = self.rate_limiter.get_stats("bybit")  # Заменено
        rate_limit_stats = {
            "requests": 0,
            "remaining": 100,
        }  # Placeholder для enhanced limiter
        key_stats = self.key_manager.get_key_stats("bybit")
        health_status = self.get_health_status()

        return {
            "exchange": "bybit",
            "connection_stats": {
                "total_requests": self.request_count,
                "successful_requests": self.success_count,
                "error_count": self.error_count,
                "success_rate": f"{(self.success_count / max(self.request_count, 1)) * 100:.1f}%",
            },
            "rate_limiting": rate_limit_stats,
            "api_keys": key_stats,
            "health": health_status,
            "capabilities": {
                "spot_trading": self.capabilities.spot_trading,
                "futures_trading": self.capabilities.futures_trading,
                "max_leverage": self.capabilities.max_leverage,
                "rate_limit_private": self.capabilities.rate_limit_private,
            },
        }
