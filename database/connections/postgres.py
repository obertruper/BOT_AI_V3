#!/usr/bin/env python3
"""
PostgreSQL подключение для BOT Trading v3

Использует локальное подключение через Unix socket на порту 5555.
Поддерживает как синхронное (SQLAlchemy), так и асинхронное (asyncpg) подключение.
"""

import os
from contextlib import asynccontextmanager, contextmanager

import asyncpg
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Импорт TransactionManager для интеграции
from database.connections.transaction_manager import TransactionManager

# Загружаем переменные окружения
load_dotenv()

# Параметры подключения из .env
DB_USER = os.getenv("PGUSER", "obertruper")
DB_PASSWORD = os.getenv("PGPASSWORD", "your-password-here")  # Заменено для безопасности
DB_NAME = os.getenv("PGDATABASE", "bot_trading_v3")
DB_PORT = os.getenv("PGPORT", "5555")

# Connection strings для локального подключения (без host!)
# Обратите внимание на формат: @ без хоста означает Unix socket
SYNC_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@:{DB_PORT}/{DB_NAME}"
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@:{DB_PORT}/{DB_NAME}"

# Для прямого подключения через asyncpg (без SQLAlchemy)
ASYNCPG_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:{DB_PORT}/{DB_NAME}"

# Базовый класс для моделей
Base = declarative_base()

# Синхронный движок и сессии с оптимизированным пулом
engine = create_engine(
    SYNC_DATABASE_URL,
    pool_size=10,  # Уменьшаем размер пула для избежания "remaining connection slots"
    max_overflow=5,  # Разрешаем немного overflow
    pool_timeout=30,  # Таймаут ожидания соединения
    pool_recycle=3600,  # Переиспользование соединений каждый час
    pool_pre_ping=True,  # Проверка соединения перед использованием
    echo=False,  # Установите True для отладки SQL запросов
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Асинхронный движок и сессии с оптимизированным пулом
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=10,  # Уменьшаем размер пула
    max_overflow=5,  # Разрешаем немного overflow
    pool_timeout=30,  # Таймаут ожидания соединения
    pool_recycle=3600,  # Переиспользование соединений каждый час
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@contextmanager
def get_db() -> Session:
    """
    Контекстный менеджер для синхронных сессий.

    Использование:
        with get_db() as db:
            result = db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db():
    """
    Асинхронный контекстный менеджер для получения сессии.

    Использование:
        async with get_async_db() as db:
            result = await db.execute(select(Model))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class AsyncPGPool:
    """Пул соединений для прямой работы с asyncpg (без SQLAlchemy)"""

    _pool: asyncpg.Pool | None = None
    _transaction_manager: TransactionManager | None = None

    @classmethod
    async def init_pool(cls) -> asyncpg.Pool:
        """Инициализировать пул соединений asyncpg с оптимизированными параметрами"""
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                ASYNCPG_URL,
                min_size=5,  # Уменьшаем минимальный размер
                max_size=10,  # Уменьшаем максимальный размер для избежания "remaining connection slots"
                max_inactive_connection_lifetime=300,  # Закрываем неактивные соединения через 5 минут
                command_timeout=60,
            )
        return cls._pool

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Получить или создать пул соединений asyncpg с оптимизированными параметрами"""
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                ASYNCPG_URL,
                min_size=5,  # Уменьшаем минимальный размер
                max_size=10,  # Уменьшаем максимальный размер
                max_inactive_connection_lifetime=300,  # Закрываем неактивные соединения через 5 минут
                command_timeout=60,
            )
        return cls._pool

    @classmethod
    async def close_pool(cls):
        """Закрыть пул соединений"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            cls._transaction_manager = None

    @classmethod
    async def get_transaction_manager(cls) -> TransactionManager:
        """Получить экземпляр TransactionManager"""
        if cls._transaction_manager is None:
            pool = await cls.get_pool()
            cls._transaction_manager = TransactionManager(pool)
        return cls._transaction_manager

    @classmethod
    async def execute(cls, query: str, *args):
        """Выполнить запрос"""
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            return await connection.execute(query, *args)

    @classmethod
    async def fetch(cls, query: str, *args):
        """Выполнить запрос и получить все результаты"""
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            return await connection.fetch(query, *args)

    @classmethod
    async def fetchrow(cls, query: str, *args):
        """Выполнить запрос и получить одну строку"""
        pool = await cls.get_pool()
        async with pool.acquire() as connection:
            return await connection.fetchrow(query, *args)


def init_db():
    """Инициализация БД - создание всех таблиц"""
    Base.metadata.create_all(bind=engine)
    print("✅ База данных инициализирована")


async def init_async_db():
    """Асинхронная инициализация БД"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных инициализирована (async)")


def test_connection():
    """Тест подключения к БД"""
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database(), current_user"))
            db, user = result.fetchone()
            print("✅ Подключение успешно!")
            print(f"   База данных: {db}")
            print(f"   Пользователь: {user}")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False


async def test_async_connection():
    """Асинхронный тест подключения"""
    try:
        pool = await AsyncPGPool.get_pool()
        result = await AsyncPGPool.fetchrow("SELECT current_database(), current_user")
        print("✅ Асинхронное подключение успешно!")
        print(f"   База данных: {result['current_database']}")
        print(f"   Пользователь: {result['current_user']}")
        return True
    except Exception as e:
        print(f"❌ Ошибка асинхронного подключения: {e}")
        return False
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    print("🔍 Тестирование подключения к PostgreSQL...")
    print(f"📊 Параметры: DB={DB_NAME}, User={DB_USER}, Port={DB_PORT}")

    # Синхронный тест
    test_connection()

    # Асинхронный тест
    import asyncio

    asyncio.run(test_async_connection())
