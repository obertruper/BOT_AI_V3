#!/usr/bin/env python3
"""
Launcher для веб-интерфейса BOT_Trading v3.0

Удобный запуск веб-сервера с правильной настройкой путей и окружения.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Проверяем виртуальное окружение
if not hasattr(sys, "real_prefix") and not (
    hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
):
    print("❌ Виртуальное окружение не активировано!")
    print(f"   Current Python: {sys.executable}")
    print(f"   Expected: {project_root}/venv/bin/python")
    print("   Запустите: source venv/bin/activate")
    sys.exit(1)

print(f"✅ Используется Python из venv: {sys.executable}")

# Импортируем после добавления пути
from core.config.config_manager import ConfigManager
from core.shared_context import shared_context
from core.system.orchestrator import SystemOrchestrator
from web.api.main import start_web_server


def setup_environment():
    """Настройка переменных окружения для разработки"""
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("WEB_HOST", "0.0.0.0")
    os.environ.setdefault("WEB_PORT", "8083")


async def main():
    """Главная функция запуска"""
    parser = argparse.ArgumentParser(description="BOT_Trading v3.0 Web Interface")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8083, help="Port to bind to (default: 8083)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Настройка окружения
    setup_environment()

    print("🚀 Запуск BOT_Trading v3.0 Web Interface...")
    print(f"📍 URL: http://{args.host}:{args.port}")
    print(f"📖 API Docs: http://{args.host}:{args.port}/api/docs")
    print(f"🔧 Режим: {'DEBUG' if args.debug else 'PRODUCTION'}")

    embed_core = os.environ.get("EMBED_CORE", "false").lower() in ("1", "true", "yes")

    orchestrator = None
    trader_manager = None
    exchange_factory = None
    config_manager = None

    if embed_core:
        # Инициализируем Core в этом же процессе, чтобы веб работал в боевом режиме
        print("🧩 EMBED_CORE=TRUE: инициализация Core (SystemOrchestrator) внутри веб-процесса")
        config_manager = ConfigManager()
        await config_manager.initialize()
        orchestrator = SystemOrchestrator(config_manager)
        await orchestrator.initialize()
        # Сохраняем в shared_context, чтобы web.api.main смог получить оркестратор
        shared_context.set_orchestrator(orchestrator)
        trader_manager = getattr(orchestrator, "trader_manager", None)
        exchange_factory = getattr(orchestrator, "exchange_factory", None)

        # Запускаем core асинхронно (без блокировки запуска веб-сервера)
        asyncio.create_task(orchestrator.start())

    if args.reload:
        # Используем uvicorn напрямую для auto-reload
        import uvicorn

        uvicorn.run(
            "web.api.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=[str(project_root)],
            log_level="debug" if args.debug else "info",
        )
    else:
        # Используем нашу функцию запуска
        await start_web_server(
            host=args.host,
            port=args.port,
            orchestrator=orchestrator,
            trader_manager=trader_manager,
            exchange_factory=exchange_factory,
            config_manager=config_manager,
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Веб-сервер остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска веб-сервера: {e}")
        sys.exit(1)
