#!/usr/bin/env python3
"""
Синглтон для BybitClient - единая точка доступа к клиенту Bybit
Гарантирует использование одного экземпляра с правильными настройками
"""

import os
from typing import Optional
from threading import Lock
from .client import BybitClient
from core.logger import setup_logger

logger = setup_logger("bybit_singleton")


class BybitClientSingleton:
    """Синглтон для управления единственным экземпляром BybitClient"""
    
    _instance: Optional[BybitClient] = None
    _lock: Lock = Lock()
    
    @classmethod
    def get_instance(cls, api_key: str = None, api_secret: str = None, sandbox: bool = False) -> BybitClient:
        """
        Получить единственный экземпляр BybitClient
        
        Args:
            api_key: API ключ (используется только при первом создании)
            api_secret: API секрет (используется только при первом создании)
            sandbox: Использовать тестнет (используется только при первом создании)
            
        Returns:
            Единственный экземпляр BybitClient с правильными настройками
        """
        if cls._instance is None:
            with cls._lock:
                # Двойная проверка для thread safety
                if cls._instance is None:
                    # Если ключи не переданы, используем из окружения
                    if not api_key:
                        api_key = os.getenv("BYBIT_API_KEY", "public_access")
                    if not api_secret:
                        api_secret = os.getenv("BYBIT_API_SECRET", "public_access")
                    
                    # Создаём единственный экземпляр
                    cls._instance = BybitClient(
                        api_key=api_key,
                        api_secret=api_secret,
                        sandbox=sandbox
                    )
                    
                    logger.info(
                        f"✅ Создан единственный экземпляр BybitClient "
                        f"(hedge_mode={cls._instance.hedge_mode}, "
                        f"leverage={cls._instance.default_leverage})"
                    )
        else:
            if api_key or api_secret:
                logger.warning(
                    "⚠️ Попытка создать новый клиент с другими ключами игнорирована. "
                    "Используется существующий экземпляр."
                )
        
        return cls._instance
    
    @classmethod
    def reset(cls):
        """
        Сбросить синглтон (используется только для тестов)
        """
        with cls._lock:
            if cls._instance:
                logger.info("🔄 Сброс синглтона BybitClient")
            cls._instance = None


def get_bybit_client(api_key: str = None, api_secret: str = None, sandbox: bool = False) -> BybitClient:
    """
    Удобная функция для получения клиента Bybit
    
    Всегда возвращает один и тот же экземпляр с правильными настройками
    """
    return BybitClientSingleton.get_instance(api_key, api_secret, sandbox)