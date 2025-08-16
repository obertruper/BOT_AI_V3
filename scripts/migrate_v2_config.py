#!/usr/bin/env python3
"""Миграция конфигурации из BOT Trading v2 в v3."""

import os
from datetime import datetime
from pathlib import Path

import yaml


def migrate_config():
    """Мигрирует конфигурацию из v2 в v3."""

    print("🔄 Миграция конфигурации из v2 в v3...")

    # Путь к конфигурации v2
    v2_config_path = Path("BOT_AI_V2/BOT_Trading/BOT_Trading/config.yaml")

    if not v2_config_path.exists():
        print("❌ Конфигурация v2 не найдена!")
        print(f"Ожидался файл: {v2_config_path}")
        return False

    # Читаем конфигурацию v2
    with open(v2_config_path) as f:
        v2_config = yaml.safe_load(f)

    print("✅ Конфигурация v2 загружена")

    # 1. Создаем/обновляем .env файл
    env_path = Path(".env")
    env_lines = []

    if env_path.exists():
        # Читаем существующий .env
        with open(env_path) as f:
            env_lines = f.readlines()

    # Функция для обновления или добавления переменной
    def update_env_var(name: str, value: str):
        for i, line in enumerate(env_lines):
            if line.startswith(f"{name}="):
                env_lines[i] = f"{name}={value}\n"
                return
        env_lines.append(f"{name}={value}\n")

    # Мигрируем API ключи
    if "BYBIT_API_KEY" in v2_config:
        update_env_var("BYBIT_API_KEY", v2_config["BYBIT_API_KEY"])
        update_env_var("BYBIT_API_SECRET", v2_config["BYBIT_API_SECRET"])
        print("✅ API ключи Bybit мигрированы")

    # Telegram конфигурация
    if "telegram_bot_token" in v2_config:
        update_env_var("TELEGRAM_BOT_TOKEN", v2_config["telegram_bot_token"])
        update_env_var("TELEGRAM_CHAT_ID", v2_config.get("telegram_chat_id", ""))
        print("✅ Telegram конфигурация мигрирована")

    # Параметры риска
    update_env_var("DEFAULT_LEVERAGE", str(v2_config.get("leverage", 5)))
    update_env_var("MAX_POSITION_SIZE", str(v2_config.get("position_size", 100)))
    update_env_var("RISK_LIMIT_PERCENTAGE", str(v2_config.get("risk_per_trade", 2)))

    # Сохраняем .env
    with open(env_path, "w") as f:
        f.writelines(env_lines)

    print("✅ Файл .env обновлен")

    # 2. Создаем конфигурацию трейдера для v3
    trader_config = {
        "trader_id": "main_trader",
        "name": "Main Trader (migrated from v2)",
        "exchange": "bybit",
        "trading_pairs": v2_config.get("symbols", ["BTCUSDT"]),
        "strategies": [],
        "risk_management": {
            "max_position_size": v2_config.get("position_size", 100),
            "max_daily_loss": v2_config.get("max_daily_loss", 500),
            "max_open_positions": v2_config.get("max_positions", 3),
            "leverage": v2_config.get("leverage", 5),
            "position_sizing": {
                "type": "fixed",
                "value": v2_config.get("position_size", 100),
            },
        },
        "order_management": {
            "default_order_type": "market",
            "slippage_tolerance": 0.001,
            "retry_attempts": 3,
            "retry_delay": 1,
        },
    }

    # Добавляем ML стратегию если были ML параметры в v2
    if "ml_model" in v2_config or "ml_settings" in v2_config:
        ml_strategy = {
            "name": "ml_strategy",
            "type": "ml_strategy.patchtst_strategy.PatchTSTStrategy",
            "enabled": True,
            "params": {
                "model_path": "models/saved/best_model_unified.pth",
                "lookback_window": 96,
                "prediction_horizon": 20,
                "confidence_threshold": 0.6,
                "use_xgboost_fallback": True,  # Для совместимости с v2
                "xgboost_model_path": "models/xgboost/",
            },
        }
        trader_config["strategies"].append(ml_strategy)
        print("✅ ML стратегия добавлена с поддержкой XGBoost")

    # Добавляем параметры SL/TP из v2
    if "enhanced_sl_tp" in v2_config:
        sl_tp = v2_config["enhanced_sl_tp"]
        trader_config["risk_management"]["stop_loss"] = {
            "enabled": sl_tp.get("enabled", True),
            "type": "trailing" if sl_tp.get("trailing_stop", {}).get("enabled") else "fixed",
            "value": sl_tp.get("stop_loss_percent", 2.0),
            "trailing_distance": sl_tp.get("trailing_stop", {}).get("callback_rate", 1.0),
        }

        trader_config["risk_management"]["take_profit"] = {
            "enabled": sl_tp.get("enabled", True),
            "type": "partial" if sl_tp.get("partial_take_profit", {}).get("enabled") else "fixed",
            "levels": [],
        }

        # Мигрируем partial take profit уровни
        if sl_tp.get("partial_take_profit", {}).get("enabled"):
            ptp = sl_tp["partial_take_profit"]
            for i, (level, percent) in enumerate(
                zip(
                    ptp.get("profit_levels", [2.0, 3.0, 5.0]),
                    ptp.get("close_percentages", [20, 30, 30]),
                    strict=False,
                )
            ):
                trader_config["risk_management"]["take_profit"]["levels"].append(
                    {"price_percent": level, "quantity_percent": percent}
                )

    # Добавляем параметры из v2 config
    trader_config["metadata"] = {
        "migrated_from": "v2",
        "migration_date": datetime.now().isoformat(),
        "original_config": "BOT_AI_V2/BOT_Trading/BOT_Trading/config.yaml",
        "v2_settings": {
            "mode": v2_config.get("mode", "paper"),
            "base_currency": v2_config.get("base_currency", "USDT"),
            "fixed_usdt_balance": v2_config.get("fixed_usdt_balance", 500),
            "hedge_mode": v2_config.get("hedge_mode", True),
        },
    }

    # Сохраняем конфигурацию трейдера
    trader_config_path = Path("config/traders/main_trader.yaml")
    trader_config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(trader_config_path, "w") as f:
        yaml.dump(trader_config, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Создан файл конфигурации трейдера: {trader_config_path}")

    # 3. Обновляем системную конфигурацию
    system_config_path = Path("config/system.yaml")
    if system_config_path.exists():
        with open(system_config_path) as f:
            system_config = yaml.safe_load(f)

        # Добавляем Telegram конфигурацию
        system_config["telegram"] = {
            "enabled": v2_config.get("telegram_notifications", True),
            "bot_token": "${TELEGRAM_BOT_TOKEN}",
            "chat_id": "${TELEGRAM_CHAT_ID}",
            "notifications": {"trades": True, "errors": True, "daily_summary": True},
            "error_threshold": v2_config.get("error_monitor", {}).get("threshold", 10),
            "error_window": v2_config.get("error_monitor", {}).get("window_minutes", 60),
        }

        # Обновляем версию
        system_config["bot_version"] = v2_config.get("bot_version", "3.0.0-alpha")

        with open(system_config_path, "w") as f:
            yaml.dump(system_config, f, default_flow_style=False, sort_keys=False)

        print("✅ Системная конфигурация обновлена")

    # 4. Создаем скрипт для проверки миграции
    check_script = """#!/usr/bin/env python3
\"\"\"Проверка результатов миграции конфигурации.\"\"\"

import os
import yaml
from pathlib import Path

def check_migration():
    print("🔍 Проверка миграции конфигурации...")

    # Проверяем .env
    if Path(".env").exists():
        print("✅ .env файл создан")

        required_vars = ["BYBIT_API_KEY", "TELEGRAM_BOT_TOKEN", "DEFAULT_LEVERAGE"]
        for var in required_vars:
            if os.getenv(var):
                print(f"  ✅ {var} установлен")
            else:
                print(f"  ⚠️  {var} не найден")
    else:
        print("❌ .env файл не найден")

    # Проверяем конфигурацию трейдера
    trader_config = Path("config/traders/main_trader.yaml")
    if trader_config.exists():
        print("✅ Конфигурация трейдера создана")

        with open(trader_config) as f:
            config = yaml.safe_load(f)

        print(f"  - Трейдер ID: {config['trader_id']}")
        print(f"  - Биржа: {config['exchange']}")
        print(f"  - Пары: {', '.join(config['trading_pairs'])}")
        print(f"  - Стратегий: {len(config['strategies'])}")
    else:
        print("❌ Конфигурация трейдера не найдена")

if __name__ == "__main__":
    check_migration()
"""

    check_path = Path("scripts/check_migration.py")
    check_path.write_text(check_script)
    os.chmod(check_path, 0o755)
    print("✅ Создан скрипт проверки: scripts/check_migration.py")

    print("\n✅ Миграция конфигурации завершена!")
    print("\n📝 Следующие шаги:")
    print("1. Проверьте .env файл и дополните недостающие ключи")
    print("2. Запустите проверку: python scripts/check_migration.py")
    print("3. При необходимости отредактируйте config/traders/main_trader.yaml")

    return True


if __name__ == "__main__":
    migrate_config()
