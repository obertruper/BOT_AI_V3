# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CRITICAL - Always Check Before Actions

1. **PostgreSQL port 5555** - NOT 5432! Always: `PGPORT=5555`
2. **Activate venv first**: `source venv/bin/activate` before ANY command
3. **API keys ONLY in .env** - check before commit: `git diff --staged | grep -i "api_key\|secret"`
4. **Async/await everywhere** - use `async def`, `await`, `asyncio` for all I/O
5. **TodoWrite required** for tasks with 3+ steps

## Project Overview

BOT_AI_V3 - High-performance algorithmic cryptocurrency trading platform with ML predictions and multi-exchange support.

- **Scale**: 673 files, 207K+ lines, Python 3.8+, PostgreSQL 15+
- **Exchanges**: 7 exchanges (Bybit, Binance, OKX, Gate.io, KuCoin, HTX, BingX)
- **Trading**: 50+ pairs, hedge mode, 5x leverage, SL/TP integrated
- **ML**: UnifiedPatchTST model, 240+ features, GPU optimized (RTX 5090)

## Architecture & Core Flow

```
Entry Point: unified_launcher.py
     ↓
1. UnifiedLauncher starts all processes
2. SystemOrchestrator coordinates components
3. Strategies generate signals → TradingEngine processes
4. RiskManager validates → OrderManager creates orders
5. ExecutionEngine executes → Exchanges receive commands
6. Results → PostgreSQL:5555 database
```

**Key Files:**

- `unified_launcher.py:52` - System launcher
- `main.py:33` - Trading core application
- `core/system/orchestrator.py:44` - Component coordination
- `trading/engine.py:597` - Trading logic
- `ml/logic/patchtst_model.py` - ML model architecture

## Essential Commands

### Quick Start

```bash
cd BOT_AI_V3
source venv/bin/activate  # ALWAYS FIRST!
pip install -r requirements.txt
cp .env.example .env     # Add exchange API keys
alembic upgrade head     # Setup database
python3 unified_launcher.py  # Start everything
```

### Launch Modes

```bash
python3 unified_launcher.py              # Full system (trading + API + frontend)
python3 unified_launcher.py --mode=core  # Trading only
python3 unified_launcher.py --mode=api   # API/web only
python3 unified_launcher.py --mode=ml    # Trading + ML predictions
python3 unified_launcher.py --status     # Check system status
python3 unified_launcher.py --logs       # Follow logs
```

### Testing

```bash
# Quick test specific function
pytest tests/unit/test_trading_engine.py -k "test_signal_processing" -v

# All unit tests with coverage
pytest tests/unit/ --cov=. --cov-report=term-missing

# Integration tests
pytest tests/integration/ -v
```

### Code Quality (RUN BEFORE COMMIT)

```bash
black . && ruff check --fix .           # Format code
mypy . --ignore-missing-imports          # Type checking
git diff --staged | grep -i "api_key\|secret\|password"  # Check for secrets
```

### Database Operations

```bash
# Test connection (port 5555!)
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT version();"

# Alembic migrations
alembic upgrade head                          # Apply all
alembic revision --autogenerate -m "desc"     # Create new
alembic downgrade -1                          # Rollback last

# Direct async query
python3 -c "
from database.connections.postgres import AsyncPGPool
import asyncio
asyncio.run(AsyncPGPool.fetch('SELECT COUNT(*) FROM orders'))
"
```

### Debugging & Monitoring

```bash
# Real-time logs
tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep ERROR

# Check ports
lsof -i :8080  # API
lsof -i :5173  # Frontend
lsof -i :5555  # PostgreSQL

# Monitor processes
htop -p $(pgrep -f "python.*unified_launcher")

# Quick monitoring scripts
./start_with_logs.sh   # Start with log monitoring
./stop_all.sh          # Stop all components
```

## ML Trading System

### Signal Flow

```
ML Manager → UnifiedPatchTST model (GPU)
    ↓
ML Signal Processor (unique predictions/minute)
    ↓
Signal Scheduler → AI Signal Generator
    ↓
Trading Engine → Signal queue
    ↓
Order Manager → Exchanges
```

### ML Testing & Monitoring

```bash
python3 test_ml_uniqueness.py   # Verify unique predictions
tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep -E "returns_15m"
python3 quick_uniqueness_check.py  # Analyze predictions
```

## Configuration Files

### Core Configs

- `config/trading.yaml` - Trading parameters (leverage, risk, SL/TP)
- `config/system.yaml` - System settings (timeouts, intervals)
- `config/ml/ml_config.yaml` - ML model parameters

### Environment Variables (.env)

```bash
# PostgreSQL (CRITICAL: port 5555!)
PGPORT=5555
PGUSER=obertruper
PGDATABASE=bot_trading_v3

# Exchange API (at least one required)
BYBIT_API_KEY=xxx
BYBIT_API_SECRET=xxx

# Trading defaults
DEFAULT_LEVERAGE=5
MAX_POSITION_SIZE=1000
RISK_LIMIT_PERCENTAGE=2
```

## Database Schema

### Main Tables

- `orders` - Order states (pending, open, filled, cancelled)
- `trades` - Executed trades with PnL
- `signals` - Trading signals from strategies/ML
- `raw_market_data` - OHLCV candle data
- `processed_market_data` - ML features (240+ indicators)

### Connection Examples

```python
# Async (preferred)
from database.connections.postgres import AsyncPGPool
trades = await AsyncPGPool.fetch("SELECT * FROM trades WHERE symbol=$1", "BTCUSDT")

# SQLAlchemy async
from database.connections import get_async_db
async with get_async_db() as db:
    result = await db.execute(select(Order).where(Order.status == "open"))
```

## Development Standards

### Code Style

- **Async-first**: All I/O operations must be async
- **Type hints**: Required for all functions
- **Docstrings**: Google style for public methods
- **Imports**: Absolute paths from project root
- **Testing**: 80% coverage minimum for new code

### Pre-commit Checklist

1. `source venv/bin/activate`
2. `black . && ruff check --fix .`
3. `mypy . --ignore-missing-imports`
4. `pytest tests/unit/ -v`
5. Check for secrets: `git diff --staged | grep -i "api_key\|secret"`

## Common Issues & Fixes

### Import Errors

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### DB Connection Failed

```bash
# Check PostgreSQL on port 5555
psql -p 5555 -U obertruper -d bot_trading_v3
```

### ML Predictions Not Unique

- Check caching in `ml/ml_signal_processor.py`
- Cache TTL should be 5 minutes max
- Verify data hash in cache key

### Position/Order Issues

- Verify hedge mode: `python3 utils/checks/check_all_positions.py`
- Check leverage (should be 5x)
- Ensure SL/TP passed during order creation

## Service URLs

- **Frontend**: <http://localhost:5173>
- **API**: <http://localhost:8080>
- **API Docs**: <http://localhost:8080/api/docs>
- **Prometheus**: <http://localhost:9090>
- **Grafana**: <http://localhost:3000>

## Project Structure

```
BOT_AI_V3/
├── unified_launcher.py    # Main entry point
├── main.py               # Trading core
├── .env                  # Secrets (NEVER commit)
├── config/               # YAML configurations
├── core/                 # Core business logic
│   └── system/          # Orchestrator, process manager
├── trading/             # Trading engine & logic
├── exchanges/           # Exchange integrations (7)
├── ml/                  # ML components
│   └── logic/          # Model & feature engineering
├── database/            # DB layer
│   └── connections/    # Async/sync pools
├── web/                 # API & Frontend
├── tests/              # Unit & integration tests
├── scripts/            # Utility scripts
│   └── deployment/    # Deployment scripts
├── utils/              # Helper utilities
│   ├── checks/        # System checks
│   └── fixes/         # Fix scripts
└── data/              # Runtime data
    └── logs/         # Log files
```

## Version & Status

- **Version**: 3.0.0
- **Status**: Production Ready
- **Last Updated**: January 11, 2025
