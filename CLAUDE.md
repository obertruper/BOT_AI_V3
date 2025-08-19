# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Requirements

1. **PostgreSQL port 5555** - NOT 5432! Always: `PGPORT=5555`
2. **Activate venv first**: `source venv/bin/activate` before ANY command
3. **API keys ONLY in .env** - check before commit: `git diff --staged | grep -i "api_key\|secret"`
4. **Async/await everywhere** - use `async def`, `await`, `asyncio` for all I/O operations
5. **Leverage 5x** - All positions must use 5x leverage (not 10x)

## Quick Start Commands

### Interactive Startup (Recommended)
```bash
./quick_start.sh               # Interactive menu with system checks
./start_with_logs_filtered.sh  # Start with colored filtered logs
./start_with_logs.sh           # Start with full log monitoring
./stop_all.sh                  # Stop all system components
```

### Manual Launch
```bash
# Environment setup
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add exchange API keys
alembic upgrade head  # Setup database

# Launch modes
python3 unified_launcher.py              # Full system (trading + API + frontend)
python3 unified_launcher.py --mode=core  # Trading only
python3 unified_launcher.py --mode=ml    # Trading + ML predictions
python3 unified_launcher.py --mode=api   # API/web only
python3 unified_launcher.py --status     # Check system status
python3 unified_launcher.py --logs       # Follow logs
```

## Development Commands

### Code Quality (RUN BEFORE COMMIT)
```bash
black . && ruff check --fix .                            # Format and fix
mypy . --ignore-missing-imports                          # Type checking
git diff --staged | grep -i "api_key\|secret\|password"  # Check for secrets
```

### Testing
```bash
# Unit tests
pytest tests/unit/ -v                                    # All unit tests
pytest tests/unit/ --cov=. --cov-report=term-missing    # With coverage
pytest tests/unit/test_trading_engine.py -k "test_signal_processing" -v  # Single test

# Integration tests
pytest tests/integration/ -v                             # All integration tests
pytest -m integration                                    # Only integration marker
pytest -m "not slow"                                     # Skip slow tests
pytest -m requires_db                                    # Only database tests

# Advanced testing
python3 scripts/master_test_runner.py --full-analysis    # Complete code chain analysis
python3 scripts/code_chain_analyzer.py                   # Dependency graph analysis
python3 scripts/full_chain_tester.py --chain=trading     # Test specific workflow
python3 scripts/coverage_monitor.py --realtime           # Real-time coverage monitoring
```

### Database Operations
```bash
# Connection (port 5555!)
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT version();"

# Migrations
alembic upgrade head                          # Apply all
alembic revision --autogenerate -m "desc"     # Create new
alembic downgrade -1                          # Rollback last

# Direct async query
python3 -c "from database.connections.postgres import AsyncPGPool; import asyncio; asyncio.run(AsyncPGPool.fetch('SELECT COUNT(*) FROM orders'))"
```

### Monitoring & Debugging
```bash
# Real-time monitoring
tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep ERROR
htop -p $(pgrep -f "python.*unified_launcher")

# System checks
python utils/checks/check_all_positions.py    # Verify positions & leverage
python utils/checks/check_balance.py          # Check account balance
python test_ml_uniqueness.py                  # Verify ML predictions unique
python quick_uniqueness_check.py              # Analyze prediction diversity

# Port monitoring
lsof -i :8083  # API Server
lsof -i :8084  # REST API
lsof -i :8085  # WebSocket
lsof -i :8086  # Webhook
lsof -i :5173  # Frontend
lsof -i :5555  # PostgreSQL
```

## Architecture Overview

### System Entry & Coordination
```
unified_launcher.py (Entry Point)
    ↓
SystemOrchestrator (core/system/orchestrator.py)
    ├── TradingEngine (trading/engine.py:597)
    ├── RiskManager (risk_management/manager.py)
    ├── MLManager (ml/ml_manager.py)
    └── ExchangeManager (exchanges/manager.py)
```

### Data Flow Pipeline
```
Market Data (7 Exchanges via CCXT)
    ↓
Feature Engineering (240 indicators)
    ↓
ML Model (UnifiedPatchTST) → 20 predictions/minute
    ↓
Signal Processor (5min cache, deduplication)
    ↓
Trading Engine → Risk Validation
    ↓
Order Manager → Exchange Execution (with SL/TP)
    ↓
PostgreSQL:5555 (async persistence)
```

### Key Components

**Trading Core** (`trading/`)
- `engine.py:597` - Signal processing, order management
- `order_manager.py` - Order lifecycle states
- `strategies/optimized_strategy.py` - ML strategy implementation

**ML Pipeline** (`ml/`)
- `logic/patchtst_model.py` - Transformer model architecture
- `logic/feature_engineering_v2.py` - 240 features generation  
- `ml_manager.py` - ML model management with torch.compile optimization
- 🚀 **torch.compile**: 7.7x ускорение инференса на RTX 5090 (1.5ms vs 11.8ms)

**Risk Management** (`risk_management/`)
- 5x leverage enforcement
- 2% risk per trade ($500 fixed balance)
- Automatic SL/TP calculation

**Database Layer** (`database/`)
- PostgreSQL port 5555 (CRITICAL)
- `connections/postgres.py` - AsyncPGPool for async operations
- SQLAlchemy 2.0 with async support

**Exchange Integration** (`exchanges/`)
- 7 exchanges: Bybit, Binance, OKX, Gate.io, KuCoin, HTX, BingX
- Unified CCXT interface with async adapters
- Hedge mode position management

## Configuration

### Files
- `config/trading.yaml` - Trading parameters (leverage, risk, SL/TP)
- `config/system.yaml` - System settings (ports, intervals, timeouts)
- `config/ml/ml_config.yaml` - ML model configuration
- `.env` - API keys and secrets (NEVER commit)

### Critical .env Variables
```
PGPORT=5555
PGUSER=obertruper
PGDATABASE=bot_trading_v3
BYBIT_API_KEY=xxx
BYBIT_API_SECRET=xxx
DEFAULT_LEVERAGE=5
MAX_POSITION_SIZE=1000
RISK_LIMIT_PERCENTAGE=2
```

## Database Schema

**Core Tables:**
- `orders` - Order states (pending, open, filled, cancelled)
- `trades` - Executed trades with PnL tracking
- `signals` - Trading signals from strategies/ML
- `raw_market_data` - OHLCV candle data
- `processed_market_data` - 240+ ML features

## Service Endpoints

- **Frontend**: http://localhost:5173
- **API Server**: http://localhost:8083
- **API Docs**: http://localhost:8083/api/docs
- **REST API**: http://localhost:8084
- **WebSocket**: http://localhost:8085
- **Webhook**: http://localhost:8086
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## MCP Servers (Model Context Protocol)

Active servers:
- `postgres` - Database access (port 5555)
- `filesystem` - File operations
- `puppeteer` - Browser automation
- `playwright` - Advanced browser testing
- `sonarqube` - Code quality analysis
- `sequential-thinking` - Complex problem solving
- `memory` - Knowledge graph persistence
- `github` - Repository management

## Common Issues & Solutions

**Import errors**: `source venv/bin/activate && pip install -r requirements.txt`

**DB connection failed**: Verify PostgreSQL on port 5555: `sudo systemctl status postgresql`

**ML predictions not unique**: Check cache in `ml/ml_signal_processor.py` (5min TTL)

**Leverage incorrect**: Run `python utils/fixes/fix_all_leverage.py`

**Missing SL/TP**: Verify order creation in `trading/order_manager.py`

**Port conflicts**: Use `./start_with_logs_filtered.sh` which handles port resolution