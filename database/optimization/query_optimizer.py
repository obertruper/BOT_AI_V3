"""
Query Optimizer with prepared statements and query performance monitoring.

This module provides optimized query execution with caching, prepared statements,
and automatic query performance analysis for trading system database operations.
"""

import asyncio
import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncpg
from loguru import logger
import json
import re


@dataclass
class QueryMetrics:
    """Query execution metrics for performance monitoring."""
    query_hash: str
    query_template: str
    execution_count: int = 0
    total_time_ms: float = 0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0
    avg_time_ms: float = 0
    last_executed: Optional[datetime] = None
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update(self, execution_time_ms: float, cached: bool = False):
        """Update metrics with new execution."""
        self.execution_count += 1
        self.last_executed = datetime.now()
        
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            self.total_time_ms += execution_time_ms
            self.min_time_ms = min(self.min_time_ms, execution_time_ms)
            self.max_time_ms = max(self.max_time_ms, execution_time_ms)
            self.avg_time_ms = self.total_time_ms / (self.execution_count - self.cache_hits)
            self.recent_times.append(execution_time_ms)
    
    def add_error(self):
        """Record an error for this query."""
        self.error_count += 1
    
    def get_p95_time(self) -> float:
        """Get 95th percentile execution time."""
        if not self.recent_times:
            return 0
        sorted_times = sorted(self.recent_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]


@dataclass
class PreparedStatement:
    """Prepared statement cache entry."""
    statement_name: str
    query: str
    param_count: int
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    
    def mark_used(self):
        """Mark statement as used."""
        self.use_count += 1
        self.last_used = datetime.now()


class QueryOptimizer:
    """
    Advanced query optimizer with prepared statements and performance monitoring.
    
    Features:
    - Prepared statement caching and management
    - Query result caching for read operations
    - Query performance monitoring and alerts
    - Automatic query optimization suggestions
    - Slow query detection and logging
    """
    
    def __init__(
        self,
        pool: asyncpg.Pool,
        prepared_statement_ttl: int = 3600,  # 1 hour
        result_cache_ttl: int = 300,          # 5 minutes
        slow_query_threshold_ms: float = 100, # 100ms
        max_prepared_statements: int = 100
    ):
        """
        Initialize Query Optimizer.
        
        Args:
            pool: AsyncPG connection pool
            prepared_statement_ttl: TTL for prepared statements (seconds)
            result_cache_ttl: TTL for result cache (seconds)
            slow_query_threshold_ms: Threshold for slow query detection
            max_prepared_statements: Maximum cached prepared statements
        """
        self.pool = pool
        self.prepared_statement_ttl = prepared_statement_ttl
        self.result_cache_ttl = result_cache_ttl
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.max_prepared_statements = max_prepared_statements
        
        # Caches
        self._prepared_statements: Dict[str, PreparedStatement] = {}
        self._result_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._query_metrics: Dict[str, QueryMetrics] = {}
        
        # Locks for thread safety
        self._prep_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._metrics_lock = asyncio.Lock()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Background cleanup of expired cache entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_expired_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired_entries(self):
        """Clean up expired cache entries."""
        current_time = datetime.now()
        
        # Clean up prepared statements
        async with self._prep_lock:
            expired_statements = [
                key for key, stmt in self._prepared_statements.items()
                if (current_time - stmt.last_used).total_seconds() > self.prepared_statement_ttl
            ]
            
            for key in expired_statements:
                del self._prepared_statements[key]
                logger.debug(f"Expired prepared statement: {key}")
        
        # Clean up result cache
        async with self._cache_lock:
            expired_results = [
                key for key, (result, timestamp) in self._result_cache.items()
                if (current_time - timestamp).total_seconds() > self.result_cache_ttl
            ]
            
            for key in expired_results:
                del self._result_cache[key]
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for caching by replacing parameters with placeholders.
        
        Args:
            query: SQL query string
        
        Returns:
            Normalized query template
        """
        # Remove extra whitespace and normalize case
        normalized = re.sub(r'\s+', ' ', query.strip().upper())
        
        # Replace parameter placeholders with generic ones
        normalized = re.sub(r'\$\d+', '$N', normalized)
        
        return normalized
    
    def _compute_query_hash(self, query: str, params: tuple = ()) -> str:
        """
        Compute hash for query + parameters for caching.
        
        Args:
            query: SQL query
            params: Query parameters
        
        Returns:
            Hash string
        """
        query_normalized = self._normalize_query(query)
        params_str = json.dumps(params, default=str, sort_keys=True)
        combined = f"{query_normalized}::{params_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _compute_statement_hash(self, query: str) -> str:
        """
        Compute hash for prepared statement (query only).
        
        Args:
            query: SQL query
        
        Returns:
            Hash string
        """
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    async def _get_or_create_prepared_statement(
        self,
        conn: asyncpg.Connection,
        query: str
    ) -> str:
        """
        Get or create prepared statement for query.
        
        Args:
            conn: Database connection
            query: SQL query
        
        Returns:
            Prepared statement name
        """
        stmt_hash = self._compute_statement_hash(query)
        
        async with self._prep_lock:
            if stmt_hash in self._prepared_statements:
                stmt = self._prepared_statements[stmt_hash]
                stmt.mark_used()
                return stmt.statement_name
            
            # Check if we need to evict old statements
            if len(self._prepared_statements) >= self.max_prepared_statements:
                # Remove least recently used statement
                oldest_key = min(
                    self._prepared_statements.keys(),
                    key=lambda k: self._prepared_statements[k].last_used
                )
                del self._prepared_statements[oldest_key]
            
            # Create new prepared statement
            statement_name = f"stmt_{stmt_hash[:8]}"
            param_count = query.count('$')
            
            try:
                await conn.execute(f"PREPARE {statement_name} AS {query}")
                
                self._prepared_statements[stmt_hash] = PreparedStatement(
                    statement_name=statement_name,
                    query=query,
                    param_count=param_count,
                    created_at=datetime.now(),
                    last_used=datetime.now(),
                    use_count=1
                )
                
                logger.debug(f"Created prepared statement: {statement_name}")
                return statement_name
                
            except Exception as e:
                logger.warning(f"Failed to create prepared statement: {e}")
                # Fall back to direct execution
                return None
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """
        Get result from cache if available and not expired.
        
        Args:
            cache_key: Cache key
        
        Returns:
            Cached result or None
        """
        async with self._cache_lock:
            if cache_key in self._result_cache:
                result, timestamp = self._result_cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self.result_cache_ttl:
                    return result
                else:
                    # Expired, remove from cache
                    del self._result_cache[cache_key]
        return None
    
    async def _cache_result(self, cache_key: str, result: Any):
        """
        Cache query result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        async with self._cache_lock:
            self._result_cache[cache_key] = (result, datetime.now())
    
    async def _update_metrics(
        self,
        query: str,
        execution_time_ms: float,
        cached: bool = False,
        error: bool = False
    ):
        """
        Update query execution metrics.
        
        Args:
            query: SQL query
            execution_time_ms: Execution time in milliseconds
            cached: Whether result was cached
            error: Whether query resulted in error
        """
        query_hash = self._compute_statement_hash(query)
        query_template = self._normalize_query(query)
        
        async with self._metrics_lock:
            if query_hash not in self._query_metrics:
                self._query_metrics[query_hash] = QueryMetrics(
                    query_hash=query_hash,
                    query_template=query_template
                )
            
            metrics = self._query_metrics[query_hash]
            
            if error:
                metrics.add_error()
            else:
                metrics.update(execution_time_ms, cached)
            
            # Log slow queries
            if not cached and execution_time_ms > self.slow_query_threshold_ms:
                logger.warning(
                    f"Slow query detected: {execution_time_ms:.2f}ms - "
                    f"{query_template[:100]}..."
                )
    
    async def execute(
        self,
        query: str,
        *args,
        conn: Optional[asyncpg.Connection] = None,
        use_cache: bool = False,
        cache_key_override: Optional[str] = None
    ) -> str:
        """
        Execute query with optimization.
        
        Args:
            query: SQL query
            *args: Query parameters
            conn: Existing connection (optional)
            use_cache: Whether to use result caching
            cache_key_override: Custom cache key
        
        Returns:
            Query result status
        """
        start_time = time.time()
        cache_key = cache_key_override or self._compute_query_hash(query, args)
        
        # Check cache for read queries
        if use_cache and query.strip().upper().startswith('SELECT'):
            cached_result = await self._get_cached_result(cache_key)
            if cached_result is not None:
                await self._update_metrics(query, 0, cached=True)
                return cached_result
        
        # Execute query
        connection = conn or await self.pool.acquire()
        try:
            # Try to use prepared statement for frequent queries
            stmt_name = await self._get_or_create_prepared_statement(connection, query)
            
            if stmt_name:
                result = await connection.execute(f"EXECUTE {stmt_name}", *args)
            else:
                result = await connection.execute(query, *args)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Cache result if requested
            if use_cache and query.strip().upper().startswith('SELECT'):
                await self._cache_result(cache_key, result)
            
            await self._update_metrics(query, execution_time_ms)
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            await self._update_metrics(query, execution_time_ms, error=True)
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if not conn:  # Only release if we acquired it
                await self.pool.release(connection)
    
    async def fetch(
        self,
        query: str,
        *args,
        conn: Optional[asyncpg.Connection] = None,
        use_cache: bool = True,
        cache_key_override: Optional[str] = None
    ) -> List[asyncpg.Record]:
        """
        Fetch multiple records with optimization.
        
        Args:
            query: SQL query
            *args: Query parameters
            conn: Existing connection (optional)
            use_cache: Whether to use result caching
            cache_key_override: Custom cache key
        
        Returns:
            List of records
        """
        start_time = time.time()
        cache_key = cache_key_override or self._compute_query_hash(query, args)
        
        # Check cache
        if use_cache:
            cached_result = await self._get_cached_result(cache_key)
            if cached_result is not None:
                await self._update_metrics(query, 0, cached=True)
                return cached_result
        
        # Execute query
        connection = conn or await self.pool.acquire()
        try:
            # Try to use prepared statement
            stmt_name = await self._get_or_create_prepared_statement(connection, query)
            
            if stmt_name:
                result = await connection.fetch(f"EXECUTE {stmt_name}", *args)
            else:
                result = await connection.fetch(query, *args)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Cache result
            if use_cache:
                await self._cache_result(cache_key, result)
            
            await self._update_metrics(query, execution_time_ms)
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            await self._update_metrics(query, execution_time_ms, error=True)
            raise
        finally:
            if not conn:
                await self.pool.release(connection)
    
    async def fetchrow(
        self,
        query: str,
        *args,
        conn: Optional[asyncpg.Connection] = None,
        use_cache: bool = True,
        cache_key_override: Optional[str] = None
    ) -> Optional[asyncpg.Record]:
        """
        Fetch single record with optimization.
        
        Args:
            query: SQL query
            *args: Query parameters
            conn: Existing connection (optional)
            use_cache: Whether to use result caching
            cache_key_override: Custom cache key
        
        Returns:
            Single record or None
        """
        start_time = time.time()
        cache_key = cache_key_override or self._compute_query_hash(query, args)
        
        # Check cache
        if use_cache:
            cached_result = await self._get_cached_result(cache_key)
            if cached_result is not None:
                await self._update_metrics(query, 0, cached=True)
                return cached_result
        
        # Execute query
        connection = conn or await self.pool.acquire()
        try:
            # Try to use prepared statement
            stmt_name = await self._get_or_create_prepared_statement(connection, query)
            
            if stmt_name:
                result = await connection.fetchrow(f"EXECUTE {stmt_name}", *args)
            else:
                result = await connection.fetchrow(query, *args)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Cache result
            if use_cache:
                await self._cache_result(cache_key, result)
            
            await self._update_metrics(query, execution_time_ms)
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            await self._update_metrics(query, execution_time_ms, error=True)
            raise
        finally:
            if not conn:
                await self.pool.release(connection)
    
    async def fetchval(
        self,
        query: str,
        *args,
        conn: Optional[asyncpg.Connection] = None,
        use_cache: bool = True,
        cache_key_override: Optional[str] = None
    ) -> Any:
        """
        Fetch single value with optimization.
        
        Args:
            query: SQL query
            *args: Query parameters
            conn: Existing connection (optional)
            use_cache: Whether to use result caching
            cache_key_override: Custom cache key
        
        Returns:
            Single value
        """
        start_time = time.time()
        cache_key = cache_key_override or self._compute_query_hash(query, args)
        
        # Check cache
        if use_cache:
            cached_result = await self._get_cached_result(cache_key)
            if cached_result is not None:
                await self._update_metrics(query, 0, cached=True)
                return cached_result
        
        # Execute query
        connection = conn or await self.pool.acquire()
        try:
            # Try to use prepared statement
            stmt_name = await self._get_or_create_prepared_statement(connection, query)
            
            if stmt_name:
                result = await connection.fetchval(f"EXECUTE {stmt_name}", *args)
            else:
                result = await connection.fetchval(query, *args)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Cache result
            if use_cache:
                await self._cache_result(cache_key, result)
            
            await self._update_metrics(query, execution_time_ms)
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            await self._update_metrics(query, execution_time_ms, error=True)
            raise
        finally:
            if not conn:
                await self.pool.release(connection)
    
    async def get_query_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive query performance statistics.
        
        Returns:
            Query statistics dictionary
        """
        async with self._metrics_lock:
            metrics = list(self._query_metrics.values())
        
        if not metrics:
            return {"total_queries": 0, "metrics": []}
        
        # Calculate aggregate stats
        total_queries = sum(m.execution_count for m in metrics)
        total_errors = sum(m.error_count for m in metrics)
        total_cache_hits = sum(m.cache_hits for m in metrics)
        
        # Find slowest queries
        slowest_queries = sorted(
            metrics,
            key=lambda m: m.avg_time_ms,
            reverse=True
        )[:10]
        
        # Find most frequent queries
        most_frequent = sorted(
            metrics,
            key=lambda m: m.execution_count,
            reverse=True
        )[:10]
        
        return {
            "total_queries": total_queries,
            "total_errors": total_errors,
            "error_rate": (total_errors / total_queries * 100) if total_queries > 0 else 0,
            "cache_hits": total_cache_hits,
            "cache_hit_rate": (total_cache_hits / total_queries * 100) if total_queries > 0 else 0,
            "prepared_statements_count": len(self._prepared_statements),
            "cached_results_count": len(self._result_cache),
            "slowest_queries": [
                {
                    "template": m.query_template[:100],
                    "avg_time_ms": m.avg_time_ms,
                    "max_time_ms": m.max_time_ms,
                    "p95_time_ms": m.get_p95_time(),
                    "execution_count": m.execution_count
                }
                for m in slowest_queries
            ],
            "most_frequent_queries": [
                {
                    "template": m.query_template[:100],
                    "execution_count": m.execution_count,
                    "avg_time_ms": m.avg_time_ms,
                    "cache_hit_rate": (m.cache_hits / m.execution_count * 100) if m.execution_count > 0 else 0
                }
                for m in most_frequent
            ]
        }
    
    async def optimize_suggestions(self) -> List[Dict[str, Any]]:
        """
        Generate optimization suggestions based on query patterns.
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        async with self._metrics_lock:
            metrics = list(self._query_metrics.values())
        
        for metric in metrics:
            # Suggest indexing for slow frequent queries
            if (metric.execution_count > 100 and 
                metric.avg_time_ms > self.slow_query_threshold_ms):
                suggestions.append({
                    "type": "index_suggestion",
                    "query": metric.query_template[:100],
                    "reason": f"Slow frequent query ({metric.avg_time_ms:.2f}ms avg, {metric.execution_count} executions)",
                    "suggestion": "Consider adding indexes on frequently filtered columns"
                })
            
            # Suggest caching for repeated read queries
            if (metric.execution_count > 50 and 
                metric.cache_hits == 0 and 
                'SELECT' in metric.query_template):
                suggestions.append({
                    "type": "caching_suggestion",
                    "query": metric.query_template[:100],
                    "reason": f"Frequent read query with no caching ({metric.execution_count} executions)",
                    "suggestion": "Enable result caching for this query"
                })
        
        return suggestions
    
    async def cleanup(self):
        """Cleanup optimizer resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear caches
        async with self._prep_lock:
            self._prepared_statements.clear()
        
        async with self._cache_lock:
            self._result_cache.clear()
        
        logger.info("QueryOptimizer cleanup completed")