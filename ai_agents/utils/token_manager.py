"""
Менеджер для управления использованием токенов и оптимизации затрат
"""
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from collections import defaultdict
import hashlib
import tiktoken


@dataclass
class TokenUsage:
    """Информация об использовании токенов"""
    timestamp: datetime
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    agent: str
    task_id: Optional[str] = None
    cached: bool = False


@dataclass
class TokenBudget:
    """Бюджет токенов"""
    daily_limit: int = 1_000_000
    monthly_limit: int = 20_000_000
    per_task_limit: int = 100_000
    alert_threshold: float = 0.8  # Предупреждение при 80% использования


class PromptCache:
    """Кеш для промптов чтобы избежать повторных запросов"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, Tuple[str, float]] = {}
        self.hit_count = 0
        self.miss_count = 0
        
    def get(self, prompt: str, max_age: int = 3600) -> Optional[str]:
        """Получить результат из кеша"""
        prompt_hash = self._hash_prompt(prompt)
        
        # Проверяем память
        if prompt_hash in self.memory_cache:
            result, timestamp = self.memory_cache[prompt_hash]
            if time.time() - timestamp < max_age:
                self.hit_count += 1
                return result
                
        # Проверяем диск
        cache_file = self.cache_dir / f"{prompt_hash}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if time.time() - data['timestamp'] < max_age:
                    self.hit_count += 1
                    # Загружаем в память
                    self.memory_cache[prompt_hash] = (data['result'], data['timestamp'])
                    return data['result']
            except:
                pass
                
        self.miss_count += 1
        return None
        
    def set(self, prompt: str, result: str):
        """Сохранить результат в кеш"""
        prompt_hash = self._hash_prompt(prompt)
        timestamp = time.time()
        
        # Сохраняем в память
        self.memory_cache[prompt_hash] = (result, timestamp)
        
        # Сохраняем на диск
        cache_file = self.cache_dir / f"{prompt_hash}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'prompt': prompt[:500],  # Первые 500 символов для отладки
                'result': result,
                'timestamp': timestamp
            }, f, ensure_ascii=False, indent=2)
            
    def _hash_prompt(self, prompt: str) -> str:
        """Хешировать промпт"""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кеша"""
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': round(hit_rate * 100, 2),
            'memory_items': len(self.memory_cache),
            'disk_items': len(list(self.cache_dir.glob('*.json')))
        }


class TokenManager:
    """Менеджер для управления токенами"""
    
    # Стоимость токенов в USD за 1M токенов
    PRICING = {
        'claude-3-5-haiku-20241022': {'input': 1.0, 'output': 5.0},
        'claude-3-5-sonnet-20241022': {'input': 3.0, 'output': 15.0},
        'claude-3-opus-20250514': {'input': 15.0, 'output': 75.0},
        'gpt-4o': {'input': 2.5, 'output': 10.0},
        'gpt-4o-mini': {'input': 0.15, 'output': 0.6}
    }
    
    def __init__(self, db_path: Optional[Path] = None, cache_dir: Optional[Path] = None):
        self.db_path = db_path or Path.home() / '.bot_trading' / 'token_usage.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.cache = PromptCache(cache_dir or Path.home() / '.bot_trading' / 'prompt_cache')
        self.budget = TokenBudget()
        self.current_usage: Dict[str, int] = defaultdict(int)
        
        self._init_db()
        self._load_current_usage()
        
    def _init_db(self):
        """Инициализировать базу данных"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    agent TEXT NOT NULL,
                    task_id TEXT,
                    cached BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON token_usage(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent ON token_usage(agent)
            """)
            
    def _load_current_usage(self):
        """Загрузить текущее использование за день"""
        today = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT SUM(total_tokens) 
                FROM token_usage 
                WHERE DATE(timestamp) = ?
            """, (today,))
            
            result = cursor.fetchone()[0]
            self.current_usage['daily'] = result or 0
            
    def count_tokens(self, text: str, model: str = "claude-3-opus-20250514") -> int:
        """Подсчитать количество токенов в тексте"""
        try:
            # Используем tiktoken для подсчета
            if 'gpt' in model:
                encoding = tiktoken.encoding_for_model("gpt-4")
            else:
                # Для Claude используем приблизительный подсчет
                encoding = tiktoken.get_encoding("cl100k_base")
                
            return len(encoding.encode(text))
        except:
            # Fallback: примерный подсчет
            return len(text) // 4
            
    def estimate_cost(self, prompt: str, expected_output_tokens: int, model: str) -> float:
        """Оценить стоимость запроса"""
        prompt_tokens = self.count_tokens(prompt, model)
        
        pricing = self.PRICING.get(model, self.PRICING['claude-3-opus-20250514'])
        
        input_cost = (prompt_tokens / 1_000_000) * pricing['input']
        output_cost = (expected_output_tokens / 1_000_000) * pricing['output']
        
        return input_cost + output_cost
        
    def can_afford(self, estimated_tokens: int, task_id: Optional[str] = None) -> Tuple[bool, str]:
        """Проверить, можем ли мы позволить себе запрос"""
        # Проверяем дневной лимит
        if self.current_usage['daily'] + estimated_tokens > self.budget.daily_limit:
            return False, f"Daily limit exceeded: {self.current_usage['daily']} + {estimated_tokens} > {self.budget.daily_limit}"
            
        # Проверяем лимит на задачу
        if task_id:
            task_usage = self._get_task_usage(task_id)
            if task_usage + estimated_tokens > self.budget.per_task_limit:
                return False, f"Task limit exceeded for {task_id}"
                
        return True, "OK"
        
    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        agent: str,
        task_id: Optional[str] = None,
        cached: bool = False
    ) -> TokenUsage:
        """Записать использование токенов"""
        total_tokens = prompt_tokens + completion_tokens
        
        # Вычисляем стоимость
        pricing = self.PRICING.get(model, self.PRICING['claude-3-opus-20250514'])
        cost = (prompt_tokens / 1_000_000) * pricing['input'] + \
               (completion_tokens / 1_000_000) * pricing['output']
               
        if cached:
            cost *= 0.1  # 90% скидка для кешированных запросов
            
        usage = TokenUsage(
            timestamp=datetime.now(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            agent=agent,
            task_id=task_id,
            cached=cached
        )
        
        # Сохраняем в БД
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO token_usage 
                (timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost_usd, agent, task_id, cached)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                usage.timestamp,
                usage.model,
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
                usage.cost_usd,
                usage.agent,
                usage.task_id,
                usage.cached
            ))
            
        # Обновляем текущее использование
        self.current_usage['daily'] += total_tokens
        
        # Проверяем пороги
        self._check_alerts()
        
        return usage
        
    def _get_task_usage(self, task_id: str) -> int:
        """Получить использование токенов для задачи"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT SUM(total_tokens) 
                FROM token_usage 
                WHERE task_id = ?
            """, (task_id,))
            
            result = cursor.fetchone()[0]
            return result or 0
            
    def _check_alerts(self):
        """Проверить пороги и отправить предупреждения"""
        daily_usage_pct = self.current_usage['daily'] / self.budget.daily_limit
        
        if daily_usage_pct >= self.budget.alert_threshold:
            print(f"⚠️  WARNING: Daily token usage at {daily_usage_pct:.1%} of limit!")
            
    def get_usage_report(self, period: str = 'daily') -> Dict[str, Any]:
        """Получить отчет об использовании"""
        if period == 'daily':
            start_date = datetime.now().date()
        elif period == 'weekly':
            start_date = datetime.now().date() - timedelta(days=7)
        elif period == 'monthly':
            start_date = datetime.now().date() - timedelta(days=30)
        else:
            raise ValueError(f"Unknown period: {period}")
            
        with sqlite3.connect(self.db_path) as conn:
            # Общая статистика
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost_usd) as total_cost,
                    SUM(CASE WHEN cached THEN 1 ELSE 0 END) as cached_requests
                FROM token_usage
                WHERE DATE(timestamp) >= ?
            """, (start_date,))
            
            stats = cursor.fetchone()
            
            # По агентам
            cursor = conn.execute("""
                SELECT 
                    agent,
                    COUNT(*) as requests,
                    SUM(total_tokens) as tokens,
                    SUM(cost_usd) as cost
                FROM token_usage
                WHERE DATE(timestamp) >= ?
                GROUP BY agent
                ORDER BY tokens DESC
            """, (start_date,))
            
            by_agent = {row[0]: {
                'requests': row[1],
                'tokens': row[2],
                'cost': row[3]
            } for row in cursor.fetchall()}
            
            # По моделям
            cursor = conn.execute("""
                SELECT 
                    model,
                    COUNT(*) as requests,
                    SUM(total_tokens) as tokens,
                    SUM(cost_usd) as cost
                FROM token_usage
                WHERE DATE(timestamp) >= ?
                GROUP BY model
                ORDER BY cost DESC
            """, (start_date,))
            
            by_model = {row[0]: {
                'requests': row[1],
                'tokens': row[2],
                'cost': row[3]
            } for row in cursor.fetchall()}
            
        return {
            'period': period,
            'start_date': str(start_date),
            'total_requests': stats[0],
            'total_tokens': stats[1],
            'total_cost_usd': round(stats[2], 2) if stats[2] else 0,
            'cached_requests': stats[3],
            'cache_hit_rate': self.cache.get_stats()['hit_rate'],
            'by_agent': by_agent,
            'by_model': by_model,
            'budget_usage': {
                'daily': f"{self.current_usage['daily'] / self.budget.daily_limit:.1%}",
                'daily_tokens': f"{self.current_usage['daily']:,} / {self.budget.daily_limit:,}"
            }
        }
        
    def optimize_model_selection(self, task_complexity: int, budget_conscious: bool = True) -> str:
        """Выбрать оптимальную модель на основе сложности задачи и бюджета"""
        if budget_conscious:
            if task_complexity <= 3:
                return 'claude-3-5-haiku-20241022'
            elif task_complexity <= 7:
                return 'claude-3-5-sonnet-20241022'
            else:
                return 'claude-3-opus-20250514'
        else:
            # Всегда используем лучшую модель
            return 'claude-3-opus-20250514'
            
    def batch_optimize(self, prompts: List[str]) -> List[List[str]]:
        """Оптимизировать батчи для минимизации токенов"""
        # Группируем похожие промпты
        batches = []
        current_batch = []
        current_tokens = 0
        max_batch_tokens = 50000  # Максимум токенов в батче
        
        for prompt in prompts:
            tokens = self.count_tokens(prompt)
            
            if current_tokens + tokens > max_batch_tokens:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [prompt]
                current_tokens = tokens
            else:
                current_batch.append(prompt)
                current_tokens += tokens
                
        if current_batch:
            batches.append(current_batch)
            
        return batches


# Singleton экземпляр
_token_manager_instance = None


def get_token_manager() -> TokenManager:
    """Получить singleton экземпляр TokenManager"""
    global _token_manager_instance
    if _token_manager_instance is None:
        _token_manager_instance = TokenManager()
    return _token_manager_instance


if __name__ == "__main__":
    # Тестирование
    manager = get_token_manager()
    
    # Проверяем подсчет токенов
    test_text = "Это тестовый текст для проверки подсчета токенов."
    tokens = manager.count_tokens(test_text)
    print(f"Tokens in test text: {tokens}")
    
    # Оценка стоимости
    cost = manager.estimate_cost(test_text, 100, "claude-3-5-haiku-20241022")
    print(f"Estimated cost: ${cost:.4f}")
    
    # Записываем использование
    usage = manager.record_usage(
        model="claude-3-5-haiku-20241022",
        prompt_tokens=50,
        completion_tokens=150,
        agent="test_agent",
        task_id="test_task_001"
    )
    print(f"Recorded usage: {usage.total_tokens} tokens, ${usage.cost_usd:.4f}")
    
    # Получаем отчет
    report = manager.get_usage_report('daily')
    print(f"\nDaily report:")
    print(json.dumps(report, indent=2))
    
    # Статистика кеша
    cache_stats = manager.cache.get_stats()
    print(f"\nCache stats: {cache_stats}")