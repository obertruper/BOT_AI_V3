# Deployment Guide for BOT_AI_V3

## Overview

This document describes the deployment process for BOT_AI_V3 cryptocurrency trading platform.

## Deployment Flow

### 1. Local Development

```bash
# Make changes
git add .
git commit -m "feat: Your feature description"

# Pre-commit hooks run automatically:
# - Code formatting (Black, isort)
# - Linting (Ruff, MyPy)
# - Security checks
# - Secret detection
```

### 2. Push to GitHub

```bash
git push origin main
```

### 3. Automatic CI/CD Pipeline

When you push to `main`, the following runs automatically:

#### CI Pipeline ✅

- Pre-commit validation
- Security scanning (Bandit, Semgrep)
- Secret detection
- Unit tests with coverage
- Integration tests
- Code quality checks
- Docker build

#### Test Workflows ✅

- Simple test workflow
- Secret verification
- Claude Code review (for PRs)

### 4. Manual Deployment

Currently, deployment requires manual triggering or SSH access.

#### Option A: GitHub Actions Deploy (if configured)

```bash
# Requires these secrets in GitHub:
# - STAGING_HOST
# - STAGING_USER
# - STAGING_SSH_KEY
# - STAGING_PORT
```

#### Option B: Manual SSH Deploy

```bash
# Connect to server
ssh user@your-server

# Navigate to project
cd /opt/bot_ai_v3

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Restart services
sudo systemctl restart bot-ai-v3
sudo systemctl status bot-ai-v3
```

## Production Deployment

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ on port 5555
- Redis (optional)
- NVIDIA GPU with CUDA (for ML)

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env

# Required variables:
PGPORT=5555
PGUSER=your_user
PGPASSWORD=your_password
PGDATABASE=bot_trading_v3
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret
```

### Service Configuration

Create systemd service file:

```ini
# /etc/systemd/system/bot-ai-v3.service
[Unit]
Description=BOT_AI_V3 Trading System
After=network.target postgresql.service

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/bot_ai_v3
Environment="PATH=/opt/bot_ai_v3/venv/bin"
ExecStart=/opt/bot_ai_v3/venv/bin/python unified_launcher.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable bot-ai-v3

# Start service
sudo systemctl start bot-ai-v3

# Check status
sudo systemctl status bot-ai-v3

# View logs
journalctl -u bot-ai-v3 -f
```

## Monitoring

### Health Check

```bash
# Check system status
curl http://localhost:8080/api/health

# Check active processes
python3 unified_launcher.py --status

# View logs
tail -f data/logs/bot_trading_$(date +%Y%m%d).log
```

### Performance Monitoring

- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>
- API Docs: <http://localhost:8080/api/docs>

## Rollback Procedure

If deployment fails:

```bash
# Stop service
sudo systemctl stop bot-ai-v3

# Checkout previous version
git checkout HEAD~1

# Reinstall dependencies
pip install -r requirements.txt

# Rollback database if needed
alembic downgrade -1

# Restart service
sudo systemctl start bot-ai-v3
```

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Failed**
   - Verify port 5555 is correct
   - Check PostgreSQL is running: `sudo systemctl status postgresql`

2. **Import Errors**
   - Activate venv: `source venv/bin/activate`
   - Reinstall deps: `pip install -r requirements.txt`

3. **ML Model Issues**
   - Check GPU: `nvidia-smi`
   - Verify CUDA: `python -c "import torch; print(torch.cuda.is_available())"`

4. **Service Won't Start**
   - Check logs: `journalctl -u bot-ai-v3 -n 100`
   - Verify permissions: `ls -la /opt/bot_ai_v3`

## Security Notes

- Never commit `.env` file
- Use GitHub Secrets for CI/CD
- Rotate API keys regularly
- Monitor for suspicious activity
- Keep dependencies updated

## Contact

For deployment issues, check:

1. GitHub Issues
2. docs/TROUBLESHOOTING.md
3. Logs in data/logs/

---

Last Updated: January 2025
Version: 3.0.0
