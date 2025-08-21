# GEMINI.md (Обновленная версия)

Инструкции для Google Gemini CLI при работе с проектом BOT_AI_V3

## О проекте

BOT_AI_V3 - это автоматизированная торговая система с машинным обучением:
- **Технологии**: Python 3.12, FastAPI, PostgreSQL, React, Machine Learning (PyTorch)
- **Архитектура**: Микросервисная с асинхронным программированием
- **Биржи**: 7 криптобирж (Bybit, Binance, OKX, Gate.io, KuCoin, HTX, BingX)
- **ML**: UnifiedPatchTST transformer модель для прогнозирования цен

## Критически важное

1. **PostgreSQL порт 5555** - НЕ 5432! Всегда: `PGPORT=5555`
2. **Активация venv**: `source venv/bin/activate` перед ЛЮБОЙ командой. Проект использует Python 3.12.
3. **API ключи ТОЛЬКО в .env** - `pre-commit` хук с `detect-secrets` автоматически проверяет наличие секретов.
4. **Async/await везде** - использовать `async def`, `await`, `asyncio` для всех I/O операций
5. **Leverage 5x** - все позиции должны использовать 5x плечо (не 10x)

## Быстрый запуск

```bash
source venv/bin/activate
./start_with_logs_filtered.sh  # Запуск с фильтрованными логами
```

## Структура проекта

```
.
├── agents
│   ├── frontend_status_agent.py
│   ├── __init__.py
│   ├── README.md
│   └── testing_agent.py
├── ai_agents
│   ├── agent_manager.py
│   ├── agents
│   │   ├── architect_agent.py
│   │   ├── autonomous_developer.py
│   │   └── __init__.py
│   ├── automated_cross_verification.py
│   ├── browser_ai_interface.py
│   ├── claude_code_sdk.py
│   ├── CLAUDE_SDK_FIXES.md
│   ├── cli_cross_verification.py
│   ├── configs
│   │   ├── cross_verification_config.yaml
│   │   └── mcp_servers.yaml
│   ├── CROSS_VERIFICATION_GUIDE.md
│   ├── cross_verification_system.py
│   ├── examples
│   │   ├── __init__.py
│   │   └── usage_example.py
│   ├── __init__.py
│   ├── quick_cross_verify.py
│   ├── README.md
│   ├── response_collector.py
│   ├── template_cross_verify.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── mcp_manager.py
│   │   └── token_manager.py
│   └── workflow_templates.py
├── alembic
│   └── versions
│       ├── add_position_tracking_tables.py
│       └── create_ml_predictions_table.py
├── alembic.ini
├── analysis_results
│   ├── analysis_warnings.txt
│   ├── full_chain_test_results.json
│   └── last_background_analysis.txt
├── api
│   ├── grpc
│   │   ├── __init__.py
│   │   └── protos
│   ├── __init__.py
│   ├── rest
│   │   ├── __init__.py
│   │   └── v1
│   ├── webhook
│   │   └── __init__.py
│   └── websocket
│       └── __init__.py
├── bot-trading-v3.service
├── CHANGELOG.md
├── check_system.sh
├── CLAUDE.md
├── config
│   ├── async_optimizations.json
│   ├── enhanced_sltp_recommended.yaml
│   ├── environments
│   │   └── __init__.py
│   ├── exchanges
│   │   └── __init__.py
│   ├── http_optimizations.json
│   ├── __init__.py
│   ├── logging.yaml
│   ├── ml
│   │   ├── ml_config.yaml
│   │   └── ml_config.yaml.backup
│   ├── production_safety.yaml
│   ├── risk_management.yaml
│   ├── strategies
│   │   ├── __init__.py
│   │   └── ml_signal.yaml
│   ├── system.yaml
│   ├── test_trading.yaml
│   ├── traders
│   │   ├── __init__.py
│   │   ├── ml_production.yaml
│   │   ├── ml_trader_example.yaml
│   │   └── multi_crypto_trader.yaml
│   ├── traders.yaml
│   ├── trading.yaml
│   └── websocket_optimizations.json
├── CONTRIBUTING.md
├── core
│   ├── cache
│   │   └── market_data_cache.py
│   ├── config
│   │   ├── config_manager.py
│   │   ├── __init__.py
│   │   └── validation.py
│   ├── exceptions.py
│   ├── __init__.py
│   ├── logger.py
│   ├── logging
│   │   ├── formatters.py
│   │   ├── __init__.py
│   │   ├── logger_factory.py
│   │   └── trade_logger.py
│   ├── orchestrator
│   │   └── __init__.py
│   ├── shared_context.py
│   ├── signals
│   │   ├── __init__.py
│   │   └── unified_signal_processor.py
│   ├── system
│   │   ├── balance_manager.py
│   │   ├── data_manager.py
│   │   ├── health_checker.py
│   │   ├── health_monitor.py
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── performance_cache.py
│   │   ├── process_manager.py
│   │   ├── process_monitor.py
│   │   ├── rate_limiter.py
│   │   ├── signal_deduplicator.py
│   │   ├── smart_data_manager.py
│   │   └── worker_coordinator.py
│   └── traders
│       ├── __init__.py
│       ├── trader_context.py
│       ├── trader_factory.py
│       └── trader_manager.py
├── cursor_setup.sh
├── database
│   ├── connections
│   │   ├── __init__.py
│   │   └── postgres.py
│   ├── __init__.py
│   ├── migrations
│   │   ├── env.py
│   │   ├── __init__.py
│   │   ├── script.py.mako
│   │   └── versions
│   ├── models
│   │   ├── base_models.py
│   │   ├── __init__.py
│   │   ├── market_data.py
│   │   ├── ml_predictions.py
│   │   └── signal.py
│   └── repositories
│       ├── __init__.py
│       ├── signal_repository_fixed.py
│       ├── signal_repository.py
│       └── trade_repository.py
├── demonstrate_mcp_usage.py
├── demo_strategy_switching.py
├── DEPLOYMENT_GUIDE.md
├── deploy_test.txt
├── diagnose_sl_tp_issue.py
├── docker-compose.metabase.yml
├── docs
│   ├── 100_PERCENT_COVERAGE_PLAN.md
│   ├── 499_ERRORS_SOLUTION.md
│   ├── AGENTS_TROUBLESHOOTING.md
│   ├── AI_COLLABORATION_REAL_WORLD.md
│   ├── AI_CROSS_VERIFICATION_DEMO.md
│   ├── AI_CROSS_VERIFICATION_SYSTEM.md
│   ├── AI_INTEGRATION_COMPLETE.md
│   ├── AI_RESPONSES
│   │   ├── ChatGPT_Scalping_Strategy_Full.md
│   │   ├── Grok_Scalping_Strategy_Full.md
│   │   └── Synthesized_Scalping_Strategy.md
│   ├── AI_VERIFICATION_OPTIMIZATION.md
│   ├── AI_VERIFICATION_REPORTS
│   │   └── INDICATOR_STRATEGY_CROSS_VERIFICATION.md
│   ├── api
│   │   └── __init__.py
│   ├── API_ERRORS_FIXED.md
│   ├── architecture
│   │   └── __init__.py
│   ├── AUTOMATIC_DEPLOYMENT.md
│   ├── CLAUDE_AGENTS_SETUP.md
│   ├── CLAUDE_AGENTS_USAGE.md
│   ├── CLAUDE_CODE_AGENTS.md
│   ├── CLAUDE_CODE_SDK_EXPLAINED.md
│   ├── CLAUDE_CODE_SETUP.md
│   ├── CODE_QUALITY.md
│   ├── CODE_USAGE_ANALYSIS_GUIDE.md
│   ├── COMPLETE_DEVELOPMENT_SETUP.md
│   ├── COMPLETE_MIGRATION_ROADMAP.md
│   ├── COMPLETE_PROJECT_STRUCTURE.md
│   ├── COMPLETE_STRUCTURE_UPDATE_SUMMARY.md
│   ├── CONFIGURATION_ANALYSIS.md
│   ├── CONFIGURATION_GUIDE.md
│   ├── CROSS_VERIFICATION_UPDATE_SUMMARY.md
│   ├── DATABASE_LOCAL_SETUP.md
│   ├── DATABASE_MIGRATION_V2_TO_V3.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEPLOYMENT.md
│   ├── development
│   │   └── __init__.py
│   ├── diagrams
│   │   ├── monitoring_alerts.mermaid
│   │   ├── signal_flow.mermaid
│   │   ├── system_architecture.mermaid
│   │   └── worker_coordination.mermaid
│   ├── DOTUSDT_ANALYSIS_REPORT.md
│   ├── ENHANCED_RESPONSE_COLLECTION.md
│   ├── ENHANCED_RISK_MANAGEMENT_GUIDE.md
│   ├── ENHANCED_SLTP_V2_FEATURES.md
│   ├── ERROR_FIXES_COMPLETE.md
│   ├── FEATURE_ENGINEERING.md
│   ├── FILE_STRUCTURE.md
│   ├── FINAL_CLEANUP_REPORT.md
│   ├── FIX_MCP_SERVERS.md
│   ├── github
│   │   ├── GITHUB_PRIVATE_REPO_SETUP.md
│   │   ├── README_GITHUB_SETUP.md
│   │   └── test_pr_verification.md
│   ├── GPU_STATUS.md
│   ├── HEALTH_CHECK_IMPLEMENTATION.md
│   ├── HEDGE_MODE_GUIDE.md
│   ├── hooks
│   │   └── CLAUDE_CODE_HOOKS_SETUP.md
│   ├── __init__.py
│   ├── LAUNCH_ML_TRADING.md
│   ├── LAUNCH_PLAN.md
│   ├── LEVERAGE_FIX_COMPLETE.md
│   ├── MCP_EXPANSION_IDEAS.md
│   ├── MCP_INTEGRATION_GUIDE.md
│   ├── MCP_ML_INTEGRATION_PLAN.md
│   ├── MCP_SETUP_COMPLETE.md
│   ├── MCP_STATUS.md
│   ├── METABASE_SETUP.md
│   ├── migration
│   │   └── __init__.py
│   ├── MIGRATION_GUIDE.md
│   ├── MIGRATION_PLAN_RU.md
│   ├── MIGRATION_PLAN_V2_TO_V3.md
│   ├── ML_CACHE_SYSTEM.md
│   ├── ML_CONFIDENCE_FIX.md
│   ├── ML_DATA_LOGGING_ENHANCEMENT.md
│   ├── ML_DIRECTION_CLASSES_FIX.md
│   ├── ML_FIXES_SUMMARY.md
│   ├── ML_INTEGRATION.md
│   ├── ML_INTEGRATION_ROADMAP.md
│   ├── ML_INTEGRATION_STATUS.md
│   ├── ML_LOGGING_AND_VISUALIZATION.md
│   ├── ML_LOGGING.md
│   ├── ML_MODEL_LOADING_FIX.md
│   ├── ML_SIGNAL_EVALUATION_SYSTEM.md
│   ├── ML_SYSTEM.md
│   ├── ML_TASKS_BREAKDOWN.md
│   ├── ML_TRADER_SETUP.md
│   ├── ML_TUNING_GUIDE.md
│   ├── MONITORING_GUIDE.md
│   ├── OPTIMIZATION_COMPLETE.md
│   ├── PERFORMANCE_OPTIMIZATION_REPORT.md
│   ├── PERMANENT_ACCESS_SOLUTIONS.md
│   ├── PLAYWRIGHT_BROWSER_PERSISTENCE.md
│   ├── PLAYWRIGHT_MCP_USAGE.md
│   ├── PORT_ARCHITECTURE.md
│   ├── PROJECT_CONTEXT.md
│   ├── QUICK_INTEGRATION_GUIDE.md
│   ├── QUICK_START_COMMANDS.md
│   ├── README.md
│   ├── REAL_AI_BROWSER_INTEGRATION.md
│   ├── REALTIME_ML_SYSTEM.md
│   ├── RUSSIAN_TESTING_GUIDE.md
│   ├── setup
│   │   ├── MCP_SETUP.md
│   │   ├── SETUP_COMPLETE.md
│   │   └── test_precommit.md
│   ├── SIGNAL_GENERATION_GUIDE.md
│   ├── SLTP_COMPLETE_SUMMARY.md
│   ├── SLTP_FIXES_IMPLEMENTED.md
│   ├── SLTP_IMPLEMENTATION_SUMMARY.md
│   ├── SLTP_INTEGRATION_COMPLETE.md
│   ├── SLTP_SYSTEM_COMPLETE_GUIDE.md
│   ├── SLTP_TROUBLESHOOTING.md
│   ├── solutions
│   │   ├── FINAL_TEST_REPORT.md
│   │   ├── LEVERAGE_SOLUTION.md
│   │   ├── LOG_FIXES_REPORT_2025_08_10.md
│   │   ├── SLTP_COMPLETE_SUMMARY.md
│   │   └── SLTP_SOLUTION.md
│   ├── SSH_CONNECTION_INSTRUCTIONS.md
│   ├── STRATEGY_DEVELOPMENT_PLAN.md
│   ├── SYSTEM_COMPONENTS_RU.md
│   ├── SYSTEM_MONITORING.md
│   ├── SYSTEM_STATUS_REPORT.md
│   ├── TAILSCALE_QUICK_START.md
│   ├── TAILSCALE_SETUP.md
│   ├── templates
│   │   └── AI_VERIFICATION_TEMPLATE.md
│   ├── TESTING_COMPLETE_GUIDE.md
│   ├── TESTING_DOCUMENTATION.md
│   ├── TEST_STRUCTURE.md
│   ├── UNIFIED_SYSTEM.md
│   ├── UNIFIED_TESTING_GUIDE.md
│   ├── UNIFIED_TEST_SYSTEM.md
│   ├── USER_GUIDE.md
│   ├── USER_GUIDE_RU.md
│   ├── user_guides
│   │   └── __init__.py
│   └── WEB_TESTING_AGENT.md
├── examples
│   ├── ai_browser_collaboration.py
│   ├── claude_sdk_demo.py
│   ├── enhanced_risk_management_example.py
│   └── real_ai_browser_demo.py
├── exchanges
│   ├── base
│   │   ├── api_key_manager.py
│   │   ├── enhanced_rate_limiter.py
│   │   ├── exceptions.py
│   │   ├── exchange_interface.py
│   │   ├── health_monitor.py
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── order_types.py
│   │   ├── rate_limiter.py
│   │   └── websocket_base.py
│   ├── binance
│   │   └── __init__.py
│   ├── bitget
│   │   └── __init__.py
│   ├── bybit
│   │   ├── adapter.py
│   │   ├── bybit_exchange.py
│   │   ├── client.py
│   │   └── __init__.py
│   ├── exchange_manager.py
│   ├── factory.py
│   ├── gateio
│   │   └── __init__.py
│   ├── huobi
│   │   └── __init__.py
│   ├── __init__.py
│   ├── kucoin
│   │   └── __init__.py
│   ├── okx
│   │   └── __init__.py
│   └── registry.py
├── fix_and_restart_system.sh
├── fix_postgres_simple.sh
├── fix_rtx5090_pytorch.sh
├── GEMINI.md
├── indicators
│   ├── calculator
│   │   ├── indicator_calculator.py
│   │   └── __init__.py
│   ├── custom
│   │   └── __init__.py
│   ├── data_provider
│   │   └── __init__.py
│   ├── __init__.py
│   ├── legacy
│   │   └── __init__.py
│   └── technical
│       └── __init__.py
├── __init__.py
├── integrated_start.py
├── interactive_trading.py
├── launch_with_gpu.sh
├── lib
│   ├── external
│   │   ├── aiohttp_async.md
│   │   ├── binance_api_docs.md
│   │   ├── bybit_api_docs.md
│   │   ├── ccxt_docs.md
│   │   ├── fastapi_patterns.md
│   │   ├── __init__.py
│   │   ├── last_update.json
│   │   ├── okx_api_docs.md
│   │   ├── pandas_analysis.md
│   │   ├── postgresql_tuning.md
│   │   ├── prometheus_metrics.md
│   │   ├── pydantic_validation.md
│   │   ├── redis_caching.md
│   │   └── uvicorn_deployment.md
│   ├── __init__.py
│   ├── README.md
│   ├── reference
│   │   └── __init__.py
│   ├── standards
│   │   └── __init__.py
│   └── technical
│       └── __init__.py
├── LICENSE
├── logs -> data/logs
├── main.py
├── Makefile
├── mcp_config.json
├── metabase_dashboards.sql
├── metabase_data
│   ├── metabase.db.mv.db
│   └── metabase.db.trace.db
├── metabase_host_mode.yml
├── metabase_simple.yml
├── migrate_to_mcp.py
├── ml
│   ├── config
│   │   └── features_240.py
│   ├── features
│   │   └── __init__.py
│   ├── __init__.py
│   ├── logic
│   │   ├── indicator_integration.py
│   │   ├── __init__.py
│   │   ├── patchtst_model.py
│   │   ├── patchtst_unified.py
│   │   ├── patchtst_usage_example.py
│   │   ├── README_FEATURE_ENGINEERING.md
│   │   ├── README.md
│   │   └── signal_quality_analyzer.py
│   ├── ml_manager.py
│   ├── ml_prediction_logger.py
│   ├── ml_signal_processor.py
│   ├── model_adapter.py
│   ├── models
│   │   ├── ensemble
│   │   ├── __init__.py
│   │   ├── neural
│   │   ├── saved
│   │   └── xgboost
│   ├── README.md
│   ├── realtime_indicator_calculator.py
│   ├── signal_scheduler.py
│   ├── strategies
│   └── training
│       └── __init__.py
├── ml_predictions_diversity_test.json
├── models
│   └── saved
│       ├── best_model_20250728_215703.pth
│       ├── best_model_v2.pth
│       ├── config.pkl
│       ├── config.yaml
│       ├── data_scaler.pkl
│       └── data_scaler_v2.pkl
├── monitoring
│   ├── alerts
│   │   └── __init__.py
│   ├── dashboards
│   │   └── __init__.py
│   ├── health
│   │   └── __init__.py
│   ├── __init__.py
│   ├── metrics
│   │   └── __init__.py
│   └── telegram
│       ├── bot.py
│       └── __init__.py
├── monitor_logs.sh
├── monitor_ml_realtime.sh
├── monitor_signal_balance.py
├── nginx
│   ├── nginx.conf
│   └── ssl
├── notifications
│   └── telegram
│       ├── __init__.py
│       └── telegram_service.py
├── orchestrator_main.py
├── package.json
├── package-lock.json
├── project_structure_visualization.html
├── pyproject.toml
├── pytest.ini
├── pytorch_rtx5090
├── QUICK_START.md
├── quick_start.sh
├── README.md
├── README_RU.md
├── requirements.txt
├── restart_and_check.sh
├── restart_system.sh
├── risk_management
│   ├── calculators.py
│   ├── enhanced_calculator.py
│   ├── __init__.py
│   ├── manager.py
│   ├── ml_risk_adapter.py
│   ├── portfolio
│   │   └── __init__.py
│   ├── position
│   │   └── __init__.py
│   └── sltp
│       └── __init__.py
├── rotate_logs.sh
├── run_comprehensive_tests.py
├── run_mcp_migration.py
├── run_tests.py
├── scripts
│   ├── apply_499_fixes.py
│   ├── check_agents.py
│   ├── check_bybit_balance.py
│   ├── check_bybit_position_mode.py
│   ├── check_config.py
│   ├── check_data_availability.py
│   ├── check_dot_positions.py
│   ├── check_min_order_sizes.py
│   ├── check_ml_database.py
│   ├── check_ml_db_simple.py
│   ├── check_ml_model.py
│   ├── check_secrets.py
│   ├── check_v3_readiness.py
│   ├── code_chain_analyzer.py
│   ├── complete_499_fix.sh
│   ├── coverage_monitor.py
│   ├── create_ml_trader.py
│   ├── demo_health_check.py
│   ├── demo_ml_trader.py
│   ├── deployment
│   │   ├── __init__.py
│   │   ├── start_all.sh
│   │   ├── start_bot.py
│   │   ├── start_multi_crypto_trading.py
│   │   ├── start_production.sh
│   │   ├── start_with_logs.sh
│   │   └── stop_all.sh
│   ├── docs_downloader.py
│   ├── enhanced_dashboard_generator.py
│   ├── fix_499_errors.sh
│   ├── fix_database_schema.py
│   ├── fix_db_config.py
│   ├── fix_duplicate_signals.py
│   ├── fix_logger_calls.py
│   ├── fix_system_issues.py
│   ├── fix_websocket_connections.py
│   ├── full_chain_tester.py
│   ├── generate_all_tests.sh
│   ├── generate_business_tests.py
│   ├── generate_debug_logs.py
│   ├── health_check.py
│   ├── __init__.py
│   ├── interactive_code_cleanup.py
│   ├── load_3months_data.py
│   ├── load_historical_data.py
│   ├── load_historical_data_quick.py
│   ├── maintenance
│   │   └── __init__.py
│   ├── migrate_v2_config.py
│   ├── migrate_v2_data.py
│   ├── migration
│   │   ├── __init__.py
│   │   └── migrate_from_v2.py
│   ├── monitor_499_errors.py
│   ├── monitoring
│   │   ├── __init__.py
│   │   ├── monitor_live_trading.py
│   │   └── monitor_ml_realtime.py
│   ├── monitor_ml_signals.py
│   ├── monitor_ml_trading.py
│   ├── monitor_system_enhanced.py
│   ├── monitor_system.py
│   ├── monitor_trading_metrics.py
│   ├── pre_commit_check.py
│   ├── prepare_model_config.py
│   ├── quick_ml_test.py
│   ├── quick_ml_trader.py
│   ├── quick_start.sh
│   ├── quick_test_runner.py
│   ├── run_checks.sh
│   ├── run_ml_strategy.py
│   ├── run_system_tests.py
│   ├── run_web_tests.py
│   ├── server_setup.sh
│   ├── setup_auto_deploy.sh
│   ├── setup_database.sh
│   ├── setup_github_app.sh
│   ├── setup_local_server.sh
│   ├── setup_pre_commit.sh
│   ├── smart_test_manager.py
│   ├── start_trading.py
│   ├── start_v3.sh
│   ├── sync_to_linux_server.sh
│   ├── sync_via_tailscale.sh
│   ├── test_code_analysis.sh
│   ├── unified_test_orchestrator.py
│   ├── unified_test_runner.py
│   ├── unused_code_remover.py
│   ├── update_docs.sh
│   ├── verify_claude_setup.py
│   ├── verify_migration.py
│   ├── visualize_db.py
│   ├── visual_web_test.py
│   ├── web_testing_agent_mcp.py
│   └── web_testing_agent.py
├── setup_metabase.sh
├── setup.py
├── setup_v3_based_on_v2.py
├── start_with_checks.sh
├── start_with_logs_filtered.sh
├── start_with_logs.sh
├── stop_all.sh
├── stop_metabase.sh
├── strategies
│   ├── arbitrage_strategy
│   │   └── __init__.py
│   ├── base
│   │   ├── base_strategy.py
│   │   ├── indicator_strategy_base.py
│   │   ├── __init__.py
│   │   └── strategy_abc.py
│   ├── factory.py
│   ├── grid_strategy
│   │   └── __init__.py
│   ├── indicator_strategy
│   │   ├── config
│   │   ├── core
│   │   ├── indicators
│   │   ├── INDICATOR_STRATEGY_DOCUMENTATION.md
│   │   ├── __init__.py
│   │   ├── risk_management
│   │   └── scoring
│   ├── __init__.py
│   ├── manager.py
│   ├── ml_strategy
│   │   ├── __init__.py
│   │   ├── ml_signal_strategy.py
│   │   ├── model_manager.py
│   │   ├── patchtst_config.yaml
│   │   ├── patchtst_strategy.py
│   │   └── README.md
│   ├── registry.py
│   └── scalping_strategy
│       └── __init__.py
├── sync_to_server.sh
├── temp_pg_hba.conf
├── testing
│   ├── demo_page.html
│   ├── run_web_tests.py
│   ├── web_test_agent_puppeteer.py
│   └── web_test_agent.py
├── TESTING_GUIDE.md
├── tests
│   ├── analysis
│   │   ├── test_code_analyzer_validation.py
│   │   └── test_code_usage_analyzer.py
│   ├── comprehensive_signal_order_tests.py
│   ├── conftest.py
│   ├── fixtures
│   │   ├── dynamic_sltp_fixtures.py
│   │   ├── __init__.py
│   │   └── ml_fixtures.py
│   ├── forced_signal_order_creation.py
│   ├── __init__.py
│   ├── integration
│   │   ├── api
│   │   ├── database
│   │   ├── end_to_end
│   │   ├── exchanges
│   │   ├── __init__.py
│   │   ├── test_api_web_integration.py
│   │   ├── test_complete_trading.py
│   │   ├── test_core_system_integration.py
│   │   ├── test_database_api_integration.py
│   │   ├── test_dynamic_sltp_e2e.py
│   │   ├── test_dynamic_sltp_integration.py
│   │   ├── test_end_to_end_workflows.py
│   │   ├── test_enhanced_logging.py
│   │   ├── test_enhanced_sltp_fixed.py
│   │   ├── test_enhanced_sltp.py
│   │   ├── test_exchange_trading_integration.py
│   │   ├── test_real_trading.py
│   │   ├── test_sltp_integration.py
│   │   ├── test_trading_ml_integration.py
│   │   ├── test_web_interface_puppeteer.py
│   │   └── test_websocket_realtime_integration.py
│   ├── performance
│   │   ├── __init__.py
│   │   ├── test_api_response.py
│   │   ├── test_database_queries.py
│   │   ├── test_dynamic_sltp_performance.py
│   │   ├── test_ml_inference.py
│   │   └── test_trading_latency.py
│   ├── README.md
│   ├── scripts
│   │   ├── demo_system_work.py
│   │   ├── generate_test_long_signal.py
│   │   └── generate_test_signal.py
│   ├── strategies
│   │   └── test_patchtst_strategy.py
│   ├── test_dashboard.html
│   ├── test_health_check.py
│   ├── trading_system_monitor.py
│   └── unit
│       ├── core
│       ├── database
│       ├── exchanges
│       ├── __init__.py
│       ├── ml
│       ├── risk_management
│       ├── strategies
│       ├── test_basic_functionality.py
│       ├── test_core_orchestrator.py
│       ├── test_core_system_comprehensive.py
│       ├── test_database_connections.py
│       ├── test_database_simple.py
│       ├── test_database_wrapper.py
│       ├── test_engine.py
│       ├── test_exceptions.py
│       ├── test_exchange_interface.py
│       ├── test_exchange_manager.py
│       ├── test_exchanges_basic.py
│       ├── test_exchanges_comprehensive.py
│       ├── test_factory.py
│       ├── test_feature_engineering_production.py
│       ├── test_helpers.py
│       ├── test_imports_only.py
│       ├── test___init__.py
│       ├── test_launcher.py
│       ├── test_logger.py
│       ├── test_main_application.py
│       ├── test_main.py
│       ├── test_mass_test_generator.py
│       ├── test_ml_api.py
│       ├── test_ml_manager_comprehensive.py
│       ├── test_ml_manager_enhanced.py
│       ├── test_ml_manager.py
│       ├── test_ml_prediction_logger.py
│       ├── test_ml_simple.py
│       ├── test_model_adapter.py
│       ├── test_optimized_strategy.py
│       ├── test_order_executor.py
│       ├── test_order_manager.py
│       ├── test_postgres.py
│       ├── test_realtime_indicator_calculator.py
│       ├── test_registry.py
│       ├── test_shared_context.py
│       ├── test_signal_repository.py
│       ├── test_signal_scheduler.py
│       ├── test_simple_working.py
│       ├── test_sltp_integration.py
│       ├── test_system_components.py
│       ├── test_system_integration.py
│       ├── test_system_orchestrator.py
│       ├── test_test_github_integration.py
│       ├── test_test_ml_signals_direct.py
│       ├── test_trade_repository.py
│       ├── test_trading_engine_comprehensive.py
│       ├── test_trading_engine.py
│       ├── test_trading_simple.py
│       ├── test_training_exact_features.py
│       ├── test_unified_launcher.py
│       ├── test_utilities_and_indicators.py
│       ├── test_verify_migration.py
│       ├── test_visualize_db.py
│       ├── test_web_api_comprehensive.py
│       ├── test_web_orchestrator_bridge.py
│       ├── test_working_basic.py
│       ├── trading
│       └── utils
├── test_trading_log.txt
├── trading
│   ├── engine.py
│   ├── execution
│   │   ├── executor.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── order_executor.py
│   ├── orders
│   │   ├── dynamic_sltp_calculator.py
│   │   ├── __init__.py
│   │   ├── order_logger.py
│   │   ├── order_manager.py
│   │   ├── partial_tp_manager.py
│   │   └── sltp_integration.py
│   ├── positions
│   │   ├── __init__.py
│   │   └── position_manager.py
│   ├── position_tracker.py
│   ├── signals
│   │   ├── ai_signal_generator.py
│   │   ├── __init__.py
│   │   └── signal_processor.py
│   └── sltp
│       ├── enhanced_manager.py
│       ├── __init__.py
│       ├── models.py
│       ├── sltp_logger.py
│       └── utils.py
├── tsconfig.json
├── unified_launcher.py
├── users
│   ├── __init__.py
│   ├── models
│   │   └── __init__.py
│   ├── repositories
│   │   └── __init__.py
│   └── services
│       └── __init__.py
├── utils
│   ├── checks
│   │   ├── check_all_balances.py
│   │   ├── check_all_positions.py
│   │   ├── check_api_keys.py
│   │   ├── check_api_keys_status.py
│   │   ├── check_balance.py
│   │   ├── check_ml_signals.py
│   │   ├── check_ml_status.py
│   │   ├── check_order_status.py
│   │   ├── check_position_mode.py
│   │   ├── check_positions_and_orders.py
│   │   ├── check_positions_and_sltp.py
│   │   ├── check_signals_and_orders.py
│   │   ├── check_system_status.py
│   │   ├── check_trading_config.py
│   │   └── check_trading_status.py
│   ├── helpers.py
│   ├── __init__.py
│   ├── math
│   │   └── __init__.py
│   ├── mcp
│   │   ├── database_wrapper.py
│   │   └── __init__.py
│   ├── network
│   │   └── __init__.py
│   ├── security
│   │   └── __init__.py
│   └── time
│       └── __init__.py
├── VERSION
├── view_logs.sh
├── visualize_ml_predictions.py
└── web
    ├── api
    │   ├── endpoints
    │   ├── main.py
    │   ├── ml_api.py
    │   ├── models
    │   ├── services
    │   └── websocket
    ├── config
    │   └── web_config.yaml
    ├── frontend
    │   ├── index.html
    │   ├── package.json
    │   ├── package-lock.json
    │   ├── postcss.config.js
    │   ├── README.md
    │   ├── src
    │   ├── tailwind.config.js
    │   ├── tsconfig.json
    │   ├── tsconfig.node.json
    │   └── vite.config.ts
    ├── integration
    │   ├── data_adapters.py
    │   ├── dependencies.py
    │   ├── event_bridge.py
    │   ├── __init__.py
    │   ├── mock_services.py
    │   ├── web_integration.py
    │   └── web_orchestrator_bridge.py
    └── launcher.py

## Ключевые файлы

- `unified_launcher.py` - Главная точка входа
- `pyproject.toml` - Зависимости и конфигурация инструментов
- `config/trading.yaml` - Настройки торговли
- `config/system.yaml` - Системные настройки
- `.env` - API ключи и секреты
- `CLAUDE.md` - Подробная документация

## Команды разработки

### Качество кода (ОБЯЗАТЕЛЬНО перед коммитом)

В проекте используется `pre-commit` для автоматической проверки и форматирования кода перед каждым коммитом. Он запускает `black`, `ruff`, `mypy`, `isort` и другие утилиты.

**1. Первоначальная настройка:**
```bash
pip install pre-commit
pre-commit install
```

**2. Ручной запуск всех проверок:**
Эта команда выполнит все настроенные проверки для всех файлов проекта.
```bash
pre-commit run --all-files
```
Это гарантирует, что ваш код соответствует стандартам проекта. Проверки также включают поиск секретов (`detect-secrets`) и проверку безопасности (`bandit`).

### Тестирование
Конфигурация тестов находится в `pyproject.toml`.

**Запуск всех тестов:**
```bash
pytest
```

**Запуск только unit или integration тестов:**
```bash
pytest -m unit -v
pytest -m integration -v
```

### База данных (порт 5555!)
```bash
psql -p 5555 -U obertruper -d bot_trading_v3
alembic upgrade head
```

## Порты сервисов

- **8083** - API Server (главный)
- **8084** - REST API
- **8085** - WebSocket
- **8086** - Webhook
- **5173** - Frontend (React)
- **5555** - PostgreSQL (КРИТИЧНО!)
- **9090** - Prometheus
- **3000** - Grafana

## Стиль работы с кодом

- **Всегда async/await** для I/O операций
- **Type hints** обязательны (`mypy` проверяет их)
- **Логирование** через factory pattern
- **Обработка ошибок** с детальными сообщениями
- **Тесты** для критической функциональности (`pytest`)
- **Документация** в коде и README
- **Форматирование** кода (`black`) и **линтинг** (`ruff`) - автоматически через `pre-commit`.
- **Коммиты** в стиле Conventional Commits (`commitizen`).

## MCP серверы

Активные серверы:
- postgres (порт 5555)
- filesystem
- puppeteer
- sonarqube
- sequential-thinking
- memory
- github

## Особенности работы

1. Система использует hedge mode для позиций
2. Риск-менеджмент: 2% на сделку, $500 баланс
3. ML предсказания: 20 в минуту, кэширование 5 мин
4. Все логи в `/mnt/SSD/data/logs/`
5. torch.compile для ускорения ML (7.7x прирост)

## При проблемах

- Проверить активацию venv: `which python` (должен быть `.../venv/bin/python`)
- Проверить порт PostgreSQL: `echo $PGPORT`
- Проверить процессы: `./start_with_logs_filtered.sh`
- Логи: `tail -f data/logs/bot_trading_*.log`

## История и контекст проекта

- **Наследие V2**: Текущая торговая архитектура (`core/` и `trading/`) является значительно переработанной и улучшенной версией `V2_bot`. Анализ кода в директории `V2_bot` может дать представление об эволюции системы.
- **Оценка LLM**: В проекте была изменена модель оценки LLM. Необходимо исследовать, как это повлияло на связанные с AI функции, особенно в `ai_agents/` и `ml/`.