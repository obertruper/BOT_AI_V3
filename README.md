# BOT Trading v3 - AI-Powered Cryptocurrency Trading Platform

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)
![Status](https://img.shields.io/badge/status-production-green.svg)

**High-performance algorithmic trading platform with ML predictions and multi-exchange support**

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

## 🌟 Features

### Core Capabilities

- **Multi-Exchange Support**: Seamless integration with 7+ exchanges (Bybit, Binance, OKX, etc.)
- **ML-Powered Predictions**: UnifiedPatchTST transformer model with 240+ features
- **Real-time Processing**: Handle 1000+ signals/sec with <50ms latency
- **Risk Management**: Advanced position sizing, stop-loss, and take-profit strategies
- **Enhanced SL/TP**: Partial take-profit, profit protection, and adaptive trailing stops

### Technical Highlights

- **Async Architecture**: Built on asyncio for maximum performance
- **Microservices Design**: Modular components with independent scaling
- **Real-time Monitoring**: Prometheus metrics and Grafana dashboards
- **Web Interface**: React 18 + TypeScript frontend with WebSocket updates
- **API-First**: FastAPI backend with comprehensive REST and WebSocket APIs

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 15+
- Redis (optional)
- CUDA-compatible GPU (optional, for ML acceleration)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/obertruper/BOT_AI_V3.git
cd BOT_AI_V3
```

2. **Set up Python environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Initialize database**

```bash
# Make sure PostgreSQL is running on port 5555
alembic upgrade head
```

5. **Launch the platform**

```bash
# Full system with all components
python3 unified_launcher.py

# Or specific modes:
python3 unified_launcher.py --mode=core  # Trading only
python3 unified_launcher.py --mode=api   # API/Web only
python3 unified_launcher.py --mode=ml    # Trading + ML
```

## 🏗️ Architecture

### System Overview

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│ UnifiedLauncher │────▶│ Orchestrator │────▶│ ProcessManager  │
└─────────────────┘     └──────────────┘     └─────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Trading Engine  │     │  ML Manager  │     │   API Server    │
└─────────────────┘     └──────────────┘     └─────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│    Exchanges    │     │  PostgreSQL  │     │    Frontend     │
└─────────────────┘     └──────────────┘     └─────────────────┘
```

### Key Components

- **UnifiedLauncher**: Central entry point managing all system processes
- **SystemOrchestrator**: Coordinates components and handles health checks
- **TradingEngine**: Core trading logic with signal processing
- **MLManager**: ML model inference and feature engineering
- **ExchangeManager**: Unified interface for multiple exchanges

## 📚 Documentation

### Configuration

- [System Configuration](docs/PORT_ARCHITECTURE.md) - Port assignments and architecture
- [ML Configuration](config/ml/ml_config.yaml) - ML model parameters
- [Risk Management](config/risk_management.yaml) - Risk settings

### Features

- [Enhanced SL/TP System](docs/ENHANCED_SLTP_V2_FEATURES.md) - Advanced order management
- [ML Signal System](docs/ML_SIGNAL_EVALUATION_SYSTEM.md) - ML prediction pipeline
- [Performance Optimization](docs/PERFORMANCE_OPTIMIZATION_REPORT.md) - Optimization guide

### Development

- [CLAUDE.md](CLAUDE.md) - AI assistant instructions
- [API Documentation](http://localhost:8080/api/docs) - Interactive API docs (when running)

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/unit/ml/

# Run with coverage
pytest --cov=. --cov-report=html

# Test enhanced SL/TP
python test_enhanced_sltp.py
```

## 🔧 Configuration

### Exchange Setup

Add your API credentials to `.env`:

```env
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
```

### Database Setup

Configure PostgreSQL connection:

```env
PGPORT=5555
PGUSER=your_user
PGPASSWORD=your_password
PGDATABASE=bot_trading_v3
```

### Trading Parameters

Adjust risk and position settings in `config/system.yaml`:

```yaml
risk_management:
  max_positions: 10
  position_size_percent: 2
  max_daily_loss: 0.05
```

## 📊 Performance

- **Throughput**: 1000+ signals per second
- **Latency**: <50ms order execution
- **ML Inference**: <20ms per prediction
- **Memory**: ~2GB typical usage
- **CPU**: 4-8 cores recommended

## 🔒 Security

- API keys stored securely in `.env` (never committed)
- Database credentials encrypted
- Rate limiting on all API endpoints
- Audit logging for all trading actions
- Secure WebSocket connections with authentication

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with PyTorch, FastAPI, and React
- Exchange integration via CCXT
- ML architecture inspired by PatchTST paper
- Community contributors and testers

## ⚠️ Disclaimer

This software is for educational and research purposes only. Cryptocurrency trading carries significant risks. Always test thoroughly with small amounts before using in production. The authors are not responsible for any financial losses incurred through the use of this software.

---

<div align="center">

**[Documentation](docs/)** • **[Issues](https://github.com/obertruper/BOT_AI_V3/issues)** • **[Discussions](https://github.com/obertruper/BOT_AI_V3/discussions)**

Made with ❤️ by the BOT Trading team

</div>
