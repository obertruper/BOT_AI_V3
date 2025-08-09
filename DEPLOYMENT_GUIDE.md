# BOT Trading v3 - Deployment Guide

## 📋 Pre-deployment Checklist

Before deploying to production, ensure:

- [ ] All sensitive data removed from codebase
- [ ] Environment variables configured properly
- [ ] Database migrations tested
- [ ] ML models properly trained and saved
- [ ] Exchange API keys have appropriate permissions
- [ ] Risk limits configured conservatively

## 🚀 Deployment Options

### Option 1: Docker Deployment (Recommended)

```bash
# Build the Docker image
docker build -t bot-trading-v3:latest .

# Run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Option 2: VPS/Cloud Deployment

#### 1. Server Requirements

- Ubuntu 20.04+ or similar
- 4+ CPU cores
- 8GB+ RAM
- 50GB+ SSD storage
- GPU optional (for ML acceleration)

#### 2. Initial Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.8 python3-pip postgresql-15 redis-server nginx

# Clone repository
git clone https://github.com/obertruper/BOT_AI_V3.git
cd BOT_AI_V3

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

#### 3. Configure PostgreSQL

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE bot_trading_v3;
CREATE USER bot_user WITH ENCRYPTED PASSWORD 'your_secure_password'; -- pragma: allowlist secret
GRANT ALL PRIVILEGES ON DATABASE bot_trading_v3 TO bot_user;
EOF

# Run migrations
alembic upgrade head
```

#### 4. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env

# Set production values:
ENVIRONMENT=production
DATABASE_URL=postgresql://bot_user:your_secure_password@localhost:5555/bot_trading_v3  # pragma: allowlist secret
REDIS_URL=redis://localhost:6379
```

#### 5. Setup as System Service

```bash
# Copy service file
sudo cp bot-trading-v3.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable bot-trading-v3
sudo systemctl start bot-trading-v3

# Check status
sudo systemctl status bot-trading-v3
```

### Option 3: Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests and Helm charts.

## 🔒 Security Considerations

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 2. SSL/TLS Setup

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### 3. API Key Security

- Never commit API keys to repository
- Use environment variables or secrets management
- Rotate keys regularly
- Use IP whitelisting where possible

## 📊 Monitoring Setup

### 1. Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bot-trading'
    static_configs:
      - targets: ['localhost:9090']
```

### 2. Grafana Dashboards

Import provided dashboards from `monitoring/grafana/dashboards/`

### 3. Alerts Configuration

Configure alerts for:

- High CPU/Memory usage
- Database connection failures
- Exchange API errors
- Abnormal trading patterns
- Risk limit breaches

## 🔄 Continuous Deployment

### GitHub Actions Workflow

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/BOT_AI_V3
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            alembic upgrade head
            sudo systemctl restart bot-trading-v3
```

## 🔧 Post-Deployment Tasks

1. **Verify System Health**

   ```bash
   # Check all services
   python3 scripts/check_system_status.py

   # Test exchange connections
   python3 test_bybit_connection.py

   # Verify ML models
   python3 test_ml_predictions.py
   ```

2. **Configure Monitoring**
   - Set up alerts for critical metrics
   - Configure log aggregation
   - Enable performance profiling

3. **Initial Trading Setup**
   - Start with minimal position sizes
   - Enable only well-tested strategies
   - Monitor closely for first 24-48 hours

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running on port 5555
   - Verify credentials in .env
   - Check firewall rules

2. **ML Model Loading Error**
   - Ensure model files exist in `models/saved/`
   - Check CUDA/GPU compatibility
   - Verify Python package versions

3. **Exchange API Errors**
   - Verify API keys are valid
   - Check IP whitelist settings
   - Ensure proper API permissions

### Rollback Procedure

```bash
# Stop service
sudo systemctl stop bot-trading-v3

# Checkout previous version
git checkout <previous-commit-hash>

# Restart service
sudo systemctl start bot-trading-v3
```

## 📞 Support

For deployment assistance:

- GitHub Issues: <https://github.com/obertruper/BOT_AI_V3/issues>
- Documentation: <https://github.com/obertruper/BOT_AI_V3/docs>

---

Remember: Always test thoroughly in a staging environment before deploying to production!
