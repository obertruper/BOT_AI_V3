"""
Mock Services для Web Integration

Заглушки сервисов до их полной реализации в BOT_Trading v3.0.
Обеспечивают работоспособность веб-интерфейса на этапе разработки.

Mock сервисы:
- MockUserManager: Управление пользователями
- MockSessionManager: Управление сессиями
- MockStatsService: Статистика торговли
- MockAlertsService: Системные алерты
- MockLogsService: Логи системы
- MockStrategyRegistry: Реестр стратегий
- MockStrategyManager: Управление стратегиями
- MockBacktestEngine: Движок бэктестов
- MockPerformanceService: Сервис производительности
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid
import hashlib

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("mock_services", component="web_integration")

# =================== MOCK USER MANAGEMENT ===================

class MockUser:
    """Mock модель пользователя"""
    def __init__(self, user_id: str, username: str, email: str, role: str = "user"):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.is_active = True
        self.permissions = ["view_dashboard", "view_traders", "view_trades"]
        if role == "admin":
            self.permissions.extend(["manage_traders", "manage_system", "manage_users"])
        self.password_hash = self._hash_password("password123")
        self.created_at = datetime.now()
        self.last_login = None

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

class MockUserManager:
    """Mock менеджер пользователей"""
    
    def __init__(self):
        self.users = {
            "admin": MockUser("1", "admin", "admin@trading.local", "admin"),
            "trader": MockUser("2", "trader", "trader@trading.local", "trader"),
            "viewer": MockUser("3", "viewer", "viewer@trading.local", "viewer")
        }
        logger.info("MockUserManager инициализирован с 3 пользователями")

    async def authenticate_user(self, username: str, password: str) -> Optional[MockUser]:
        """Аутентификация пользователя"""
        user = self.users.get(username)
        if user and user.password_hash == hashlib.sha256(password.encode()).hexdigest():
            user.last_login = datetime.now()
            logger.info(f"Пользователь {username} успешно аутентифицирован")
            return user
        logger.warning(f"Неудачная попытка входа для пользователя {username}")
        return None

    async def get_user_by_username(self, username: str) -> Optional[MockUser]:
        """Получить пользователя по имени"""
        return self.users.get(username)

    async def get_user_by_id(self, user_id: str) -> Optional[MockUser]:
        """Получить пользователя по ID"""
        for user in self.users.values():
            if user.user_id == user_id:
                return user
        return None

    async def update_last_login(self, user_id: str):
        """Обновить время последнего входа"""
        for user in self.users.values():
            if user.user_id == user_id:
                user.last_login = datetime.now()
                break

    async def update_password(self, user_id: str, password_hash: str):
        """Обновить пароль пользователя"""
        for user in self.users.values():
            if user.user_id == user_id:
                user.password_hash = password_hash
                logger.info(f"Пароль обновлен для пользователя {user_id}")
                break

# =================== MOCK SESSION MANAGEMENT ===================

class MockSession:
    """Mock модель сессии"""
    def __init__(self, session_id: str, user_id: str, ip_address: str = "127.0.0.1"):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.ip_address = ip_address
        self.user_agent = "BOT_Trading Web Interface"
        self.is_current = True

class MockSessionManager:
    """Mock менеджер сессий"""
    
    def __init__(self):
        self.sessions: Dict[str, MockSession] = {}
        logger.info("MockSessionManager инициализирован")

    async def create_session(self, user_id: str, access_token: str, remember_me: bool = False) -> str:
        """Создать новую сессию"""
        session_id = str(uuid.uuid4())
        session = MockSession(session_id, user_id)
        self.sessions[session_id] = session
        logger.info(f"Создана сессия {session_id} для пользователя {user_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[MockSession]:
        """Получить сессию"""
        return self.sessions.get(session_id)

    async def get_user_sessions(self, user_id: str) -> List[MockSession]:
        """Получить все сессии пользователя"""
        return [session for session in self.sessions.values() if session.user_id == user_id]

    async def delete_session(self, session_id: str):
        """Удалить сессию"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Сессия {session_id} удалена")

    async def delete_user_sessions(self, user_id: str, exclude_current: bool = False):
        """Удалить все сессии пользователя"""
        sessions_to_delete = []
        for session_id, session in self.sessions.items():
            if session.user_id == user_id:
                if not (exclude_current and session.is_current):
                    sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            del self.sessions[session_id]
        
        logger.info(f"Удалено {len(sessions_to_delete)} сессий для пользователя {user_id}")

# =================== MOCK STATS SERVICE ===================

class MockStatsService:
    """Mock сервис статистики"""
    
    def __init__(self):
        logger.info("MockStatsService инициализирован")

    async def get_trading_stats(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Получить статистику торговли за период"""
        # Симуляция реальных данных
        hours_diff = (end_time - start_time).total_seconds() / 3600
        total_trades = int(hours_diff * 2)  # 2 сделки в час
        
        return {
            'total_trades': total_trades,
            'successful_trades': int(total_trades * 0.65),
            'failed_trades': int(total_trades * 0.35),
            'total_pnl': round(total_trades * 15.5, 2),
            'success_rate': 65.0,
            'avg_duration': 45.5
        }

# =================== MOCK ALERTS SERVICE ===================

class MockAlert:
    """Mock модель алерта"""
    def __init__(self, alert_id: str, level: str, component: str, message: str):
        self.id = alert_id
        self.level = level
        self.component = component
        self.message = message
        self.timestamp = datetime.now()
        self.resolved = False

class MockAlertsService:
    """Mock сервис алертов"""
    
    def __init__(self):
        self.alerts = [
            MockAlert("1", "warning", "trader_manager", "Трейдер BTCUSDT приостановлен из-за высокой волатильности"),
            MockAlert("2", "info", "exchange_bybit", "Успешное подключение к Bybit API"),
            MockAlert("3", "error", "ml_strategy", "Ошибка загрузки ML модели"),
        ]
        logger.info("MockAlertsService инициализирован с 3 алертами")

    async def get_alerts(self, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Получить алерты с фильтрами"""
        filtered_alerts = self.alerts
        
        if 'level' in filters:
            filtered_alerts = [a for a in filtered_alerts if a.level == filters['level']]
        
        if 'resolved' in filters:
            filtered_alerts = [a for a in filtered_alerts if a.resolved == filters['resolved']]
        
        result = []
        for alert in filtered_alerts[:limit]:
            result.append({
                'id': alert.id,
                'level': alert.level,
                'component': alert.component,
                'message': alert.message,
                'timestamp': alert.timestamp,
                'resolved': alert.resolved
            })
        
        return result

    async def resolve_alert(self, alert_id: str) -> bool:
        """Отметить алерт как решенный"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                logger.info(f"Алерт {alert_id} отмечен как решенный")
                return True
        return False

# =================== MOCK LOGS SERVICE ===================

class MockLogsService:
    """Mock сервис логов"""
    
    def __init__(self):
        logger.info("MockLogsService инициализирован")

    async def get_logs(self, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Получить логи с фильтрами"""
        # Симуляция логов
        logs = []
        for i in range(min(limit, 50)):
            logs.append({
                'timestamp': (datetime.now() - timedelta(minutes=i)).isoformat(),
                'level': 'INFO' if i % 3 != 0 else 'WARNING',
                'component': ['trader_manager', 'ml_strategy', 'bybit_client'][i % 3],
                'message': f"Mock log message {i + 1}",
                'logger_name': 'bot_trading.mock',
                'line_number': 100 + i
            })
        
        return logs

# =================== MOCK STRATEGY SERVICES ===================

class MockStrategy:
    """Mock модель стратегии"""
    def __init__(self, name: str, display_name: str, category: str):
        self.name = name
        self.display_name = display_name
        self.category = category
        self.description = f"Mock описание для {display_name}"
        self.status = "active"
        self.version = "1.0.0"
        self.default_parameters = {
            "risk_level": 0.02,
            "stop_loss": 0.05,
            "take_profit": 0.10
        }
        self.supported_exchanges = ["bybit", "binance"]
        self.risk_level = "medium"

class MockStrategyRegistry:
    """Mock реестр стратегий"""
    
    def __init__(self):
        self.strategies = {
            "ml_strategy": MockStrategy("ml_strategy", "ML Strategy", "ml"),
            "ema_crossover": MockStrategy("ema_crossover", "EMA Crossover", "indicator"),
            "grid_trading": MockStrategy("grid_trading", "Grid Trading", "grid")
        }
        logger.info("MockStrategyRegistry инициализирован с 3 стратегиями")

    def get_available_strategies(self) -> List[str]:
        """Получить список доступных стратегий"""
        return list(self.strategies.keys())

    def get_strategy_class(self, strategy_name: str) -> Optional[MockStrategy]:
        """Получить класс стратегии"""
        return self.strategies.get(strategy_name)

class MockStrategyManager:
    """Mock менеджер стратегий"""
    
    def __init__(self):
        logger.info("MockStrategyManager инициализирован")

    async def configure_strategy(self, trader_id: str, strategy_config: Dict[str, Any]) -> bool:
        """Настроить стратегию для трейдера"""
        logger.info(f"Настройка стратегии {strategy_config['strategy_name']} для трейдера {trader_id}")
        await asyncio.sleep(0.1)  # Симуляция асинхронной операции
        return True

# =================== MOCK BACKTEST ENGINE ===================

class MockBacktestEngine:
    """Mock движок бэктестов"""
    
    def __init__(self):
        self.backtests = {}
        logger.info("MockBacktestEngine инициализирован")

    async def start_backtest(self, backtest_config: Dict[str, Any]) -> str:
        """Запустить бэктест"""
        backtest_id = str(uuid.uuid4())
        
        # Симуляция результатов бэктеста
        result = {
            "backtest_id": backtest_id,
            "strategy_name": backtest_config["strategy_name"],
            "symbol": backtest_config["symbol"],
            "period": f"{backtest_config['start_date'].strftime('%Y-%m-%d')} - {backtest_config['end_date'].strftime('%Y-%m-%d')}",
            "total_return": 15.5,
            "sharpe_ratio": 1.2,
            "max_drawdown": -5.2,
            "win_rate": 65.0,
            "total_trades": 127,
            "avg_trade_duration": 45.5,
            "profit_factor": 1.8,
            "status": "completed",
            "created_at": datetime.now(),
            "completed_at": datetime.now()
        }
        
        self.backtests[backtest_id] = result
        logger.info(f"Создан бэктест {backtest_id} для стратегии {backtest_config['strategy_name']}")
        
        return backtest_id

    async def get_backtest_result(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """Получить результат бэктеста"""
        return self.backtests.get(backtest_id)

# =================== MOCK PERFORMANCE SERVICE ===================

class MockPerformanceService:
    """Mock сервис производительности"""
    
    def __init__(self):
        logger.info("MockPerformanceService инициализирован")

    async def get_strategy_summary(self, strategy_name: str) -> Dict[str, float]:
        """Получить краткую сводку производительности стратегии"""
        return {
            "total_pnl": 245.67,
            "win_rate": 65.5,
            "sharpe_ratio": 1.45,
            "max_drawdown": -8.2
        }

    async def get_strategy_detailed_metrics(self, strategy_name: str) -> Dict[str, float]:
        """Получить детальные метрики производительности"""
        return {
            "total_pnl": 245.67,
            "trades_count": 89,
            "win_rate": 65.5,
            "avg_win": 15.8,
            "avg_loss": -9.2,
            "max_drawdown": -8.2,
            "sharpe_ratio": 1.45,
            "sortino_ratio": 1.78,
            "calmar_ratio": 0.95,
            "var_95": -12.5
        }

    async def get_strategy_performance(self, strategy_name: str, period: str) -> Dict[str, Any]:
        """Получить производительность стратегии за период"""
        return await self.get_strategy_detailed_metrics(strategy_name)

# =================== UTILITY FUNCTIONS ===================

def create_all_mock_services() -> Dict[str, Any]:
    """Создать все mock сервисы"""
    logger.info("Создание всех mock сервисов")
    
    return {
        "user_manager": MockUserManager(),
        "session_manager": MockSessionManager(),
        "stats_service": MockStatsService(),
        "alerts_service": MockAlertsService(),
        "logs_service": MockLogsService(),
        "strategy_registry": MockStrategyRegistry(),
        "strategy_manager": MockStrategyManager(),
        "backtest_engine": MockBacktestEngine(),
        "performance_service": MockPerformanceService()
    }