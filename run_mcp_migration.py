#!/usr/bin/env python3
"""
Автоматическая миграция на MCP
Сгенерировано: 2025-08-15 09:35:16
"""

import os
import re


def migrate_file(filepath: str):
    """Мигрировать один файл на MCP"""

    with open(filepath) as f:
        content = f.read()

    # Замена импортов
    content = re.sub(
        r"from database\.connections\.postgres import AsyncPGPool",
        "from utils.mcp.database_wrapper import AsyncPGPool",
        content,
    )

    # Создаем backup
    backup_path = filepath + ".backup"
    with open(backup_path, "w") as f:
        f.write(content)

    # Записываем измененный файл
    with open(filepath, "w") as f:
        f.write(content)

    print(f"✅ Мигрирован: {filepath}")
    print(f"   Backup: {backup_path}")


# Файлы для миграции
files_to_migrate = [
    "./ml/ml_prediction_logger.py",
    "./tests/integration/test_enhanced_sltp.py",
    "./test_fixed_model.py",
    "./scripts/deployment/start_bot.py",
    "./check_ml_data_quality_v2.py",
    "./restart_ml_clean.py",
    "./core/system/signal_deduplicator.py",
    "./check_balance_and_processes.py",
    "./scripts/check_dot_positions.py",
    "./migrate_to_mcp.py",
    "./analyze_ml_predictions.py",
    "./core/system/balance_manager.py",
    "./diagnose_sl_tp_issue.py",
    "./scripts/monitor_system_enhanced.py",
    "./fix_feature_engineering.py",
    "./analyze_ml_pipeline.py",
    "./core/system/data_manager.py",
    "./utils/checks/check_trading_config.py",
    "./trading/order_executor.py",
    "./utils/mcp/__init__.py",
    "./test_ml_predictions_analysis.py",
    "./core/system/process_monitor.py",
    "./database/connections/postgres.py",
    "./test_model_fixes.py",
    "./tests/scripts/generate_test_long_signal.py",
    "./test_final_system.py",
    "./utils/checks/check_signals_and_orders.py",
    "./restart_with_fixes.py",
    "./check_ml_data_quality.py",
    "./restart_ml_fresh.py",
    "./core/system/smart_data_manager.py",
    "./analyze_features.py",
    "./compare_features.py",
    "./demonstrate_mcp_usage.py",
    "./scripts/fix_database_schema.py",
    "./scripts/monitor_ml_trading.py",
    "./visualize_ml_predictions.py",
    "./core/signals/unified_signal_processor.py",
    "./analyze_signal_diversity.py",
    "./test_system_integration.py",
    "./scripts/run_system_tests.py",
    "./utils/checks/check_system_status.py",
    "./data/data_update_service.py",
    "./test_ml_logging.py",
    "./test_data_update.py",
    "./scripts/fix_duplicate_signals.py",
    "./load_fresh_data.py",
    "./scripts/monitoring/monitor_ml_realtime.py",
    "./utils/mcp/database_wrapper.py",
    "./tests/unit/test_system_integration.py",
    "./debug_ml_predictions.py",
    "./test_ml_logging_direct.py",
    "./test_model_predictions.py",
    "./scripts/fix_system_issues.py",
]

if __name__ == "__main__":
    print("🚀 Начало миграции на MCP...")

    for filepath in files_to_migrate:
        if os.path.exists(filepath):
            migrate_file(filepath)

    print("\n✅ Миграция завершена!")
    print("⚠️  Не забудьте протестировать изменения!")
