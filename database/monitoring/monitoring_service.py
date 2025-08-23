"""
Database Monitoring Service for comprehensive health and performance tracking.

This service provides real-time monitoring of database operations, connection pool health,
and performance metrics critical for trading system reliability.
"""

import asyncio
import time
import psutil
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncpg
from loguru import logger
import json
from collections import deque, defaultdict


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    metric_path: str  # e.g., "pool.active_connections"
    operator: str     # >, <, >=, <=, ==, !=
    threshold: float
    severity: str     # info, warning, critical
    cooldown_seconds: int = 300  # 5 minutes
    enabled: bool = True
    last_triggered: Optional[datetime] = None


@dataclass
class Alert:
    """Alert instance."""
    rule_name: str
    severity: str
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class DatabaseMonitoringService:
    """
    Comprehensive database monitoring service for trading systems.
    
    Features:
    - Real-time connection pool monitoring
    - Query performance tracking
    - Health checks with alerting
    - Resource utilization monitoring
    - Custom metric collection
    - Performance trend analysis
    """
    
    def __init__(
        self,
        pool: asyncpg.Pool,
        check_interval: int = 30,        # seconds
        metric_retention: int = 7200,    # 2 hours of data points
        enable_alerts: bool = True
    ):
        """
        Initialize Database Monitoring Service.
        
        Args:
            pool: AsyncPG connection pool
            check_interval: Health check interval in seconds
            metric_retention: Number of metric data points to retain
            enable_alerts: Whether to enable alerting
        """
        self.pool = pool
        self.check_interval = check_interval
        self.metric_retention = metric_retention
        self.enable_alerts = enable_alerts
        
        # Monitoring data
        self._metrics_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=metric_retention)
        )
        self._alerts: deque = deque(maxlen=1000)  # Keep last 1000 alerts
        self._alert_rules: Dict[str, AlertRule] = {}
        self._health_checks: Dict[str, HealthCheck] = {}
        
        # Monitoring tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._alert_task: Optional[asyncio.Task] = None
        
        # Performance counters
        self._start_time = datetime.now()
        self._total_checks = 0
        self._failed_checks = 0
        
        # Custom metric collectors
        self._metric_collectors: Dict[str, Callable] = {}
        
        # Initialize default alert rules
        self._setup_default_alert_rules()
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules for critical metrics."""
        default_rules = [
            AlertRule(
                name="high_connection_usage",
                metric_path="pool.usage_percentage",
                operator=">=",
                threshold=90.0,
                severity="warning",
                cooldown_seconds=300
            ),
            AlertRule(
                name="critical_connection_usage",
                metric_path="pool.usage_percentage",
                operator=">=",
                threshold=95.0,
                severity="critical",
                cooldown_seconds=60
            ),
            AlertRule(
                name="no_free_connections",
                metric_path="pool.free_connections",
                operator="<=",
                threshold=1,
                severity="critical",
                cooldown_seconds=60
            ),
            AlertRule(
                name="high_query_error_rate",
                metric_path="queries.error_rate",
                operator=">=",
                threshold=5.0,  # 5%
                severity="warning",
                cooldown_seconds=180
            ),
            AlertRule(
                name="slow_avg_query_time",
                metric_path="queries.avg_execution_time_ms",
                operator=">=",
                threshold=500.0,  # 500ms
                severity="warning",
                cooldown_seconds=300
            ),
            AlertRule(
                name="database_connection_failure",
                metric_path="health.database_reachable",
                operator="==",
                threshold=0,  # 0 = false, 1 = true
                severity="critical",
                cooldown_seconds=60
            )
        ]
        
        for rule in default_rules:
            self._alert_rules[rule.name] = rule
    
    async def start_monitoring(self):
        """Start background monitoring tasks."""
        if not self._monitoring_task or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Database monitoring started")
        
        if self.enable_alerts and (not self._alert_task or self._alert_task.done()):
            self._alert_task = asyncio.create_task(self._alert_loop())
            logger.info("Database alerting started")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Database monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                await self._collect_all_metrics()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _alert_loop(self):
        """Alert evaluation loop."""
        while True:
            try:
                await self._evaluate_alert_rules()
                await asyncio.sleep(10)  # Check alerts more frequently
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert loop: {e}")
                await asyncio.sleep(5)
    
    async def _collect_all_metrics(self):
        """Collect all monitoring metrics."""
        timestamp = datetime.now()
        
        try:
            # Pool metrics
            pool_metrics = await self._collect_pool_metrics()
            self._store_metrics("pool", pool_metrics, timestamp)
            
            # Database health
            health_metrics = await self._collect_health_metrics()
            self._store_metrics("health", health_metrics, timestamp)
            
            # Query metrics (if available)
            query_metrics = await self._collect_query_metrics()
            self._store_metrics("queries", query_metrics, timestamp)
            
            # System metrics
            system_metrics = await self._collect_system_metrics()
            self._store_metrics("system", system_metrics, timestamp)
            
            # Custom metrics
            for name, collector in self._metric_collectors.items():
                try:
                    custom_metrics = await collector()
                    self._store_metrics(f"custom.{name}", custom_metrics, timestamp)
                except Exception as e:
                    logger.warning(f"Custom metric collector '{name}' failed: {e}")
            
            self._total_checks += 1
            
        except Exception as e:
            self._failed_checks += 1
            logger.error(f"Metric collection failed: {e}")
    
    async def _collect_pool_metrics(self) -> Dict[str, float]:
        """Collect connection pool metrics."""
        try:
            # Get pool statistics
            pool_size = getattr(self.pool, '_size', 0)
            free_connections = getattr(self.pool, '_free', None)
            free_count = free_connections.qsize() if free_connections else 0
            active_connections = pool_size - free_count
            
            usage_percentage = (active_connections / pool_size * 100) if pool_size > 0 else 0
            
            return {
                "total_connections": float(pool_size),
                "active_connections": float(active_connections),
                "free_connections": float(free_count),
                "usage_percentage": usage_percentage
            }
        except Exception as e:
            logger.error(f"Failed to collect pool metrics: {e}")
            return {"error": 1.0}
    
    async def _collect_health_metrics(self) -> Dict[str, float]:
        """Collect database health metrics."""
        metrics = {}
        
        # Test database connectivity
        try:
            start_time = time.time()
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            response_time_ms = (time.time() - start_time) * 1000
            metrics["database_reachable"] = 1.0
            metrics["response_time_ms"] = response_time_ms
            
        except Exception as e:
            metrics["database_reachable"] = 0.0
            metrics["response_time_ms"] = 9999.0
            logger.error(f"Database health check failed: {e}")
        
        # Check for long-running transactions
        try:
            async with self.pool.acquire() as conn:
                long_txns = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                    AND query_start < NOW() - INTERVAL '5 minutes'
                """)
                metrics["long_running_transactions"] = float(long_txns or 0)
        except Exception:
            metrics["long_running_transactions"] = 0.0
        
        # Check for locks
        try:
            async with self.pool.acquire() as conn:
                locks_count = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM pg_locks 
                    WHERE NOT granted
                """)
                metrics["blocked_queries"] = float(locks_count or 0)
        except Exception:
            metrics["blocked_queries"] = 0.0
        
        return metrics
    
    async def _collect_query_metrics(self) -> Dict[str, float]:
        """Collect query performance metrics."""
        # This would integrate with QueryOptimizer if available
        # For now, provide basic PostgreSQL stats
        
        try:
            async with self.pool.acquire() as conn:
                # Get query statistics from pg_stat_statements if available
                stats = await conn.fetchrow("""
                    SELECT 
                        COALESCE(SUM(calls), 0) as total_calls,
                        COALESCE(AVG(mean_exec_time), 0) as avg_execution_time_ms,
                        COALESCE(MAX(max_exec_time), 0) as max_execution_time_ms,
                        COALESCE(SUM(CASE WHEN calls = 0 THEN 1 ELSE 0 END), 0) as error_count
                    FROM pg_stat_statements
                    WHERE last_exec > NOW() - INTERVAL '1 hour'
                """)
                
                if stats:
                    total_calls = stats["total_calls"] or 0
                    error_count = stats["error_count"] or 0
                    error_rate = (error_count / total_calls * 100) if total_calls > 0 else 0
                    
                    return {
                        "total_calls": float(total_calls),
                        "avg_execution_time_ms": float(stats["avg_execution_time_ms"] or 0),
                        "max_execution_time_ms": float(stats["max_execution_time_ms"] or 0),
                        "error_count": float(error_count),
                        "error_rate": error_rate
                    }
        except Exception:
            # pg_stat_statements might not be available
            pass
        
        return {"queries_monitored": 0.0}
    
    async def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage for database directory
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_usage_percent": float(cpu_percent),
                "memory_usage_percent": float(memory.percent),
                "memory_available_gb": float(memory.available / (1024**3)),
                "disk_usage_percent": float(disk.percent),
                "disk_free_gb": float(disk.free / (1024**3))
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {"system_metrics_error": 1.0}
    
    def _store_metrics(self, category: str, metrics: Dict[str, float], timestamp: datetime):
        """Store metrics in history with timestamp."""
        for metric_name, value in metrics.items():
            key = f"{category}.{metric_name}"
            self._metrics_history[key].append({
                "timestamp": timestamp,
                "value": value
            })
    
    async def _evaluate_alert_rules(self):
        """Evaluate all alert rules against current metrics."""
        if not self.enable_alerts:
            return
        
        current_time = datetime.now()
        
        for rule_name, rule in self._alert_rules.items():
            if not rule.enabled:
                continue
            
            # Check cooldown
            if (rule.last_triggered and 
                (current_time - rule.last_triggered).total_seconds() < rule.cooldown_seconds):
                continue
            
            # Get current metric value
            current_value = self._get_current_metric_value(rule.metric_path)
            if current_value is None:
                continue
            
            # Evaluate condition
            triggered = self._evaluate_condition(current_value, rule.operator, rule.threshold)
            
            if triggered:
                alert = Alert(
                    rule_name=rule_name,
                    severity=rule.severity,
                    message=f"{rule.metric_path} {rule.operator} {rule.threshold} (current: {current_value})",
                    current_value=current_value,
                    threshold=rule.threshold,
                    timestamp=current_time
                )
                
                self._alerts.append(alert)
                rule.last_triggered = current_time
                
                # Log alert
                log_method = logger.critical if rule.severity == "critical" else logger.warning
                log_method(f"ALERT [{rule.severity.upper()}] {alert.message}")
    
    def _get_current_metric_value(self, metric_path: str) -> Optional[float]:
        """Get the most recent value for a metric path."""
        if metric_path not in self._metrics_history:
            return None
        
        history = self._metrics_history[metric_path]
        if not history:
            return None
        
        return history[-1]["value"]
    
    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Evaluate alert condition."""
        operators = {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y
        }
        
        return operators.get(operator, lambda x, y: False)(value, threshold)
    
    def add_alert_rule(self, rule: AlertRule):
        """Add custom alert rule."""
        self._alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """Remove alert rule."""
        if rule_name in self._alert_rules:
            del self._alert_rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
    
    def add_metric_collector(self, name: str, collector: Callable):
        """
        Add custom metric collector.
        
        Args:
            name: Collector name
            collector: Async function that returns Dict[str, float]
        """
        self._metric_collectors[name] = collector
        logger.info(f"Added custom metric collector: {name}")
    
    async def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status and metrics."""
        current_time = datetime.now()
        
        # Get latest metrics
        latest_metrics = {}
        for key, history in self._metrics_history.items():
            if history:
                latest_metrics[key] = history[-1]["value"]
        
        # Get recent alerts
        recent_alerts = [
            {
                "rule_name": alert.rule_name,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "current_value": alert.current_value,
                "threshold": alert.threshold
            }
            for alert in list(self._alerts)[-10:]  # Last 10 alerts
        ]
        
        # Determine overall health
        critical_alerts = [a for a in list(self._alerts)[-10:] if a.severity == "critical"]
        overall_health = HealthStatus.CRITICAL if critical_alerts else HealthStatus.HEALTHY
        
        return {
            "timestamp": current_time.isoformat(),
            "overall_health": overall_health.value,
            "uptime_seconds": (current_time - self._start_time).total_seconds(),
            "monitoring_stats": {
                "total_checks": self._total_checks,
                "failed_checks": self._failed_checks,
                "success_rate": ((self._total_checks - self._failed_checks) / self._total_checks * 100) 
                               if self._total_checks > 0 else 100
            },
            "current_metrics": latest_metrics,
            "recent_alerts": recent_alerts,
            "alert_rules_count": len(self._alert_rules),
            "enabled_rules": len([r for r in self._alert_rules.values() if r.enabled])
        }
    
    async def get_metrics_history(
        self,
        metric_path: str,
        minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get historical data for a specific metric.
        
        Args:
            metric_path: Metric path (e.g., "pool.active_connections")
            minutes: Minutes of history to return
        
        Returns:
            List of timestamped metric values
        """
        if metric_path not in self._metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        history = self._metrics_history[metric_path]
        
        return [
            {
                "timestamp": entry["timestamp"].isoformat(),
                "value": entry["value"]
            }
            for entry in history
            if entry["timestamp"] >= cutoff_time
        ]
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        current_status = await self.get_current_status()
        
        # Analyze trends
        trends = {}
        for key in ["pool.usage_percentage", "health.response_time_ms", "queries.avg_execution_time_ms"]:
            history = await self.get_metrics_history(key, minutes=30)
            if len(history) >= 2:
                recent_avg = sum(h["value"] for h in history[-5:]) / min(5, len(history))
                older_avg = sum(h["value"] for h in history[:5]) / min(5, len(history))
                trend = "increasing" if recent_avg > older_avg * 1.1 else "decreasing" if recent_avg < older_avg * 0.9 else "stable"
                trends[key] = {"trend": trend, "recent_avg": recent_avg, "older_avg": older_avg}
        
        return {
            "report_timestamp": datetime.now().isoformat(),
            "current_status": current_status,
            "trends": trends,
            "recommendations": await self._generate_recommendations()
        }
    
    async def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations based on metrics."""
        recommendations = []
        
        # Check pool usage
        pool_usage = self._get_current_metric_value("pool.usage_percentage")
        if pool_usage and pool_usage > 80:
            recommendations.append("Consider increasing connection pool size due to high usage")
        
        # Check response time
        response_time = self._get_current_metric_value("health.response_time_ms")
        if response_time and response_time > 100:
            recommendations.append("Database response time is elevated, check for slow queries")
        
        # Check long running transactions
        long_txns = self._get_current_metric_value("health.long_running_transactions")
        if long_txns and long_txns > 0:
            recommendations.append("Long-running transactions detected, review transaction boundaries")
        
        return recommendations