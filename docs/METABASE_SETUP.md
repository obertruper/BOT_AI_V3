# Metabase Setup Guide for BOT_AI_V3

## Overview

Metabase provides powerful visualization and analytics for ML predictions and trading performance.

## Quick Start

### 1. Installation

```bash
# Run setup script
chmod +x setup_metabase.sh
./setup_metabase.sh
```

### 2. Access Metabase

Open browser: <http://localhost:3000>

### 3. Initial Configuration

1. **Create Admin Account**
   - Email: <your-email@example.com>
   - Password: strong_password

2. **Connect Database**

   ```
   Type: PostgreSQL
   Host: host.docker.internal (or your server IP)
   Port: 5555
   Database: bot_trading_v3
   Username: obertruper
   Password: your_password
   ```

## Pre-built Dashboards

### 1. ML Predictions Dashboard

Shows real-time ML model performance:

- Prediction distribution by symbol
- Confidence levels over time
- Signal type breakdown (LONG/SHORT/NEUTRAL)
- Inference time metrics
- Risk scores

### 2. Trading Performance Dashboard

Tracks trading results:

- P&L by day/week/month
- Win rate by symbol
- Average profit per trade
- SL/TP effectiveness
- Position duration analysis

### 3. Signal Quality Dashboard

Analyzes signal generation:

- Signal strength distribution
- Conversion rate (signals → orders)
- Strategy performance comparison
- False signal analysis

### 4. Real-time Monitoring

Live system status:

- Active positions
- Recent predictions
- System performance metrics
- Error rates

### 5. Feature Importance Dashboard

ML model insights:

- Top important features
- Feature correlation with returns
- Feature stability over time

## Creating Custom Dashboards

### Step 1: Import SQL Views

```bash
# Connect to database
psql -p 5555 -U obertruper -d bot_trading_v3

# Import views
\i metabase_dashboards.sql
```

### Step 2: Create Dashboard in Metabase

1. Click "New" → "Dashboard"
2. Add questions/cards
3. Configure refresh rate (recommended: 1 minute for real-time)

### Example Questions

#### ML Prediction Accuracy

```sql
SELECT
    DATE_TRUNC('hour', datetime) as hour,
    AVG(signal_confidence) as avg_confidence,
    COUNT(*) as predictions
FROM ml_predictions
WHERE datetime >= NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;
```

#### Trading Performance

```sql
SELECT
    symbol,
    SUM(profit) as total_profit,
    COUNT(*) as trades,
    AVG(profit) as avg_profit
FROM trades
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY symbol
ORDER BY total_profit DESC;
```

#### SL/TP Error Detection

```sql
SELECT
    COUNT(*) FILTER (WHERE side = 'SELL' AND stop_loss <= price) as sl_errors,
    COUNT(*) FILTER (WHERE side = 'SELL' AND take_profit >= price) as tp_errors,
    COUNT(*) as total_short_orders
FROM orders
WHERE side = 'SELL'
    AND created_at >= NOW() - INTERVAL '24 hours';
```

## Visualization Best Practices

### 1. Time Series Charts

- Use for: Predictions over time, P&L trends
- Group by: Hour for intraday, Day for weekly views

### 2. Bar Charts

- Use for: Symbol comparison, Signal distribution
- Sort by: Performance metrics

### 3. Number Cards

- Use for: Key metrics (total profit, win rate, active positions)
- Set goals: Define target values

### 4. Tables

- Use for: Detailed position info, Recent predictions
- Enable: Conditional formatting for profit/loss

### 5. Funnel Charts

- Use for: Signal → Order → Trade conversion
- Track: Drop-off rates

## Alerts Setup

### Create Alerts for

1. **Low ML Confidence**

   ```sql
   SELECT AVG(signal_confidence)
   FROM ml_predictions
   WHERE datetime >= NOW() - INTERVAL '1 hour'
   HAVING AVG(signal_confidence) < 0.5
   ```

2. **SL/TP Errors**

   ```sql
   SELECT COUNT(*)
   FROM orders
   WHERE side = 'SELL'
     AND stop_loss <= price
     AND created_at >= NOW() - INTERVAL '10 minutes'
   HAVING COUNT(*) > 0
   ```

3. **High Risk Positions**

   ```sql
   SELECT COUNT(*)
   FROM ml_predictions
   WHERE risk_score > 0.8
     AND datetime >= NOW() - INTERVAL '1 hour'
   ```

## Performance Optimization

### 1. Database Indexes

Already created by metabase_dashboards.sql

### 2. Caching

- Enable caching for dashboards
- Set TTL: 60 seconds for real-time, 5 minutes for historical

### 3. Query Optimization

- Use materialized views for heavy calculations
- Limit date ranges in WHERE clauses

## Troubleshooting

### Issue: Can't connect to database

```bash
# Check PostgreSQL is running on port 5555
lsof -i :5555

# Test connection
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 1"
```

### Issue: Slow dashboards

```sql
-- Check query performance
EXPLAIN ANALYZE <your_query>;

-- Create missing indexes
CREATE INDEX idx_table_column ON table(column);
```

### Issue: Docker connection issues

```bash
# Use host IP instead of localhost
ip addr show | grep inet

# Or use Docker network
docker network inspect bridge
```

## Backup & Restore

### Backup Metabase

```bash
docker exec bot_metabase \
  pg_dump -U metabase metabase > metabase_backup.sql
```

### Restore Metabase

```bash
docker exec -i bot_postgres_metabase \
  psql -U metabase metabase < metabase_backup.sql
```

## Security

### 1. Enable HTTPS

- Update nginx.conf with SSL certificates
- Use Let's Encrypt for free certificates

### 2. Access Control

- Create groups: Admins, Traders, Viewers
- Set permissions per dashboard

### 3. API Access

```bash
# Generate API key in Admin → Settings → API Keys
curl -X GET \
  http://localhost:3000/api/card/1/query \
  -H 'X-Metabase-Session: your-session-token'
```

## Maintenance

### Daily Tasks

- Check active dashboards
- Review alert triggers
- Monitor query performance

### Weekly Tasks

- Update dashboard filters
- Archive old data
- Review user access

### Monthly Tasks

- Optimize slow queries
- Update documentation
- Backup configuration

---

*Last Updated: January 2025*
*Version: 1.0.0*
