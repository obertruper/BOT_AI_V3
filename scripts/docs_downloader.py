#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система автоматического скачивания и обновления технической документации

Скачивает актуальную документацию из официальных источников:
- CCXT library documentation
- FastAPI documentation
- PostgreSQL documentation
- Prometheus documentation
- И другие библиотеки, используемые в проекте

Использование:
    python scripts/docs_downloader.py --update-all
    python scripts/docs_downloader.py --library ccxt
    python scripts/docs_downloader.py --check-updates
"""

import os
import sys
import json
import asyncio
import aiohttp
import argparse
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Добавляем корневую папку проекта в Python path
sys.path.append(str(Path(__file__).parent.parent))

from lib import EXTERNAL_PATH

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentationDownloader:
    """Менеджер скачивания и обновления документации"""
    
    def __init__(self):
        self.lib_path = Path(EXTERNAL_PATH)
        self.config_file = self.lib_path / "docs_config.json"
        self.last_update_file = self.lib_path / "last_update.json"
        self.session = None
        
        # Конфигурация источников документации
        self.sources = {
            # === Основные библиотеки ===
            "ccxt": {
                "name": "CCXT Cryptocurrency Trading Library",
                "urls": [
                    "https://raw.githubusercontent.com/ccxt/ccxt/master/README.md",
                    "https://raw.githubusercontent.com/ccxt/ccxt/master/wiki/Manual.md",
                    "https://raw.githubusercontent.com/ccxt/ccxt/master/wiki/Install.md"
                ],
                "output_file": "ccxt_docs.md",
                "update_frequency": 7  # дней
            },
            "fastapi": {
                "name": "FastAPI Web Framework",
                "urls": [
                    "https://raw.githubusercontent.com/tiangolo/fastapi/master/README.md"
                ],
                "github_docs": "https://api.github.com/repos/tiangolo/fastapi/contents/docs",
                "output_file": "fastapi_patterns.md",
                "update_frequency": 7
            },
            "pydantic": {
                "name": "Pydantic Data Validation",
                "urls": [
                    "https://raw.githubusercontent.com/pydantic/pydantic/main/README.md"
                ],
                "output_file": "pydantic_validation.md",
                "update_frequency": 7
            },
            "uvicorn": {
                "name": "Uvicorn ASGI Server",
                "urls": [
                    "https://raw.githubusercontent.com/encode/uvicorn/master/README.md"
                ],
                "output_file": "uvicorn_deployment.md", 
                "update_frequency": 14
            },
            
            # === Биржи ===
            "binance_api": {
                "name": "Binance API Documentation",
                "urls": [
                    "https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md",
                    "https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/web-socket-streams.md"
                ],
                "output_file": "binance_api_docs.md",
                "update_frequency": 7
            },
            "bybit_api": {
                "name": "Bybit API Documentation", 
                "urls": [
                    "https://raw.githubusercontent.com/bybit-exchange/docs/main/README.md",
                    "https://raw.githubusercontent.com/bybit-exchange/pybit/master/README.md"
                ],
                "output_file": "bybit_api_docs.md",
                "update_frequency": 7
            },
            "okx_api": {
                "name": "OKX API Documentation",
                "urls": [
                    "https://raw.githubusercontent.com/okx/go-wallet-sdk/main/README.md",
                    "https://raw.githubusercontent.com/okx/js-wallet-sdk/main/README.md"
                ],
                "output_file": "okx_api_docs.md", 
                "update_frequency": 7
            },
            
            # === Базы данных ===
            "postgresql": {
                "name": "PostgreSQL Database",
                "urls": [
                    "https://raw.githubusercontent.com/postgres/postgres/master/README"
                ],
                "output_file": "postgresql_tuning.md",
                "update_frequency": 30
            },
            "redis": {
                "name": "Redis In-Memory Database",
                "urls": [
                    "https://raw.githubusercontent.com/redis/redis/unstable/README.md"
                ],
                "output_file": "redis_caching.md",
                "update_frequency": 14
            },
            
            # === Мониторинг ===
            "prometheus": {
                "name": "Prometheus Monitoring",
                "urls": [
                    "https://raw.githubusercontent.com/prometheus/prometheus/master/README.md"
                ],
                "output_file": "prometheus_metrics.md",
                "update_frequency": 14
            },
            "grafana": {
                "name": "Grafana Dashboards",
                "urls": [
                    "https://raw.githubusercontent.com/grafana/grafana/main/README.md"
                ],
                "output_file": "grafana_dashboards.md",
                "update_frequency": 14
            },
            
            # === ML и Analytics ===
            "pandas": {
                "name": "Pandas Data Analysis",
                "urls": [
                    "https://raw.githubusercontent.com/pandas-dev/pandas/main/README.md"
                ],
                "output_file": "pandas_analysis.md",
                "update_frequency": 14
            },
            "numpy": {
                "name": "NumPy Mathematical Computing",
                "urls": [
                    "https://raw.githubusercontent.com/numpy/numpy/main/README.md"
                ],
                "output_file": "numpy_computing.md",
                "update_frequency": 21
            },
            "sklearn": {
                "name": "Scikit-learn Machine Learning",
                "urls": [
                    "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/README.rst"
                ],
                "output_file": "sklearn_ml.md",
                "update_frequency": 14
            },
            
            # === WebSocket и Async ===
            "websockets": {
                "name": "WebSockets Library",
                "urls": [
                    "https://raw.githubusercontent.com/python-websockets/websockets/main/README.rst"
                ],
                "output_file": "websockets_realtime.md",
                "update_frequency": 14
            },
            "aiohttp": {
                "name": "Aiohttp Async HTTP Client/Server",
                "urls": [
                    "https://raw.githubusercontent.com/aio-libs/aiohttp/master/README.rst"
                ],
                "output_file": "aiohttp_async.md",
                "update_frequency": 7
            },
            "asyncio": {
                "name": "Python Asyncio Documentation",
                "urls": [
                    "https://raw.githubusercontent.com/python/cpython/main/Lib/asyncio/README"
                ],
                "output_file": "asyncio_patterns.md",
                "update_frequency": 30
            },
            
            # === Testing ===
            "pytest": {
                "name": "Pytest Testing Framework",
                "urls": [
                    "https://raw.githubusercontent.com/pytest-dev/pytest/main/README.rst"
                ],
                "output_file": "pytest_testing.md",
                "update_frequency": 14
            },
            
            # === Security ===
            "cryptography": {
                "name": "Cryptography Library",
                "urls": [
                    "https://raw.githubusercontent.com/pyca/cryptography/main/README.rst"
                ],
                "output_file": "cryptography_security.md",
                "update_frequency": 14
            },
            
            # === DevOps ===
            "docker": {
                "name": "Docker Containerization",
                "urls": [
                    "https://raw.githubusercontent.com/docker/docs/main/README.md"
                ],
                "output_file": "docker_deployment.md",
                "update_frequency": 21
            }
        }
    
    async def __aenter__(self):
        """Async context manager вход"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'BOT-Trading-v3-Docs-Downloader/1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager выход"""
        if self.session:
            await self.session.close()
    
    def load_last_update_info(self) -> Dict:
        """Загрузка информации о последнем обновлении"""
        if self.last_update_file.exists():
            try:
                with open(self.last_update_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Ошибка чтения файла обновлений: {e}")
        return {}
    
    def save_last_update_info(self, info: Dict):
        """Сохранение информации о последнем обновлении"""
        try:
            with open(self.last_update_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения файла обновлений: {e}")
    
    def needs_update(self, library: str) -> bool:
        """Проверка необходимости обновления библиотеки"""
        last_updates = self.load_last_update_info()
        
        if library not in last_updates:
            return True
        
        last_update = datetime.fromisoformat(last_updates[library]['timestamp'])
        frequency = self.sources[library]['update_frequency']
        
        return datetime.now() - last_update > timedelta(days=frequency)
    
    async def download_content(self, url: str) -> Optional[str]:
        """Скачивание контента по URL"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"Успешно скачано: {url}")
                    return content
                else:
                    logger.warning(f"Ошибка {response.status} при скачивании: {url}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка скачивания {url}: {e}")
            return None
    
    async def download_library_docs(self, library: str) -> bool:
        """Скачивание документации для конкретной библиотеки"""
        if library not in self.sources:
            logger.error(f"Неизвестная библиотека: {library}")
            return False
        
        source = self.sources[library]
        logger.info(f"Скачивание документации: {source['name']}")
        
        all_content = []
        all_content.append(f"# {source['name']} - Локальная документация")
        all_content.append(f"**Скачано**: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        all_content.append(f"**Автоматическое обновление**: каждые {source['update_frequency']} дней")
        all_content.append("")
        
        # Скачивание основных URL
        for i, url in enumerate(source['urls']):
            content = await self.download_content(url)
            if content:
                all_content.append(f"## Документ {i+1}: {url}")
                all_content.append("")
                all_content.append(content)
                all_content.append("")
                all_content.append("---")
                all_content.append("")
        
        # Если есть GitHub API для документации
        if 'github_docs' in source:
            docs_content = await self.download_github_docs(source['github_docs'])
            if docs_content:
                all_content.extend(docs_content)
        
        # Сохранение в файл
        output_path = self.lib_path / source['output_file']
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_content))
            
            # Обновление информации о последнем обновлении
            last_updates = self.load_last_update_info()
            last_updates[library] = {
                'timestamp': datetime.now().isoformat(),
                'files_count': len(source['urls']),
                'output_file': source['output_file'],
                'content_hash': hashlib.md5('\n'.join(all_content).encode()).hexdigest()
            }
            self.save_last_update_info(last_updates)
            
            logger.info(f"Документация {library} сохранена в {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения документации {library}: {e}")
            return False
    
    async def download_github_docs(self, api_url: str) -> List[str]:
        """Скачивание документации через GitHub API"""
        try:
            async with self.session.get(api_url) as response:
                if response.status == 200:
                    files = await response.json()
                    docs_content = []
                    
                    for file_info in files[:10]:  # Ограничиваем количество файлов
                        if file_info['name'].endswith('.md'):
                            file_content = await self.download_content(file_info['download_url'])
                            if file_content:
                                docs_content.append(f"## {file_info['name']}")
                                docs_content.append("")
                                docs_content.append(file_content)
                                docs_content.append("")
                    
                    return docs_content
        except Exception as e:
            logger.error(f"Ошибка скачивания через GitHub API: {e}")
        
        return []
    
    async def update_all_libraries(self, force: bool = False):
        """Обновление всех библиотек"""
        logger.info("Начало обновления всех библиотек")
        
        updated_count = 0
        for library in self.sources.keys():
            if force or self.needs_update(library):
                if await self.download_library_docs(library):
                    updated_count += 1
            else:
                logger.info(f"Библиотека {library} не требует обновления")
        
        logger.info(f"Обновлено библиотек: {updated_count}")
    
    def check_updates_needed(self) -> List[str]:
        """Проверка каких библиотек требуют обновления"""
        return [lib for lib in self.sources.keys() if self.needs_update(lib)]
    
    def get_status(self) -> Dict:
        """Получение статуса всех библиотек"""
        last_updates = self.load_last_update_info()
        status = {}
        
        for library in self.sources.keys():
            if library in last_updates:
                last_update = datetime.fromisoformat(last_updates[library]['timestamp'])
                needs_update = self.needs_update(library)
                status[library] = {
                    'last_update': last_update.strftime('%d.%m.%Y %H:%M'),
                    'needs_update': needs_update,
                    'output_file': last_updates[library].get('output_file', 'unknown'),
                    'files_count': last_updates[library].get('files_count', 0)
                }
            else:
                status[library] = {
                    'last_update': 'Никогда',
                    'needs_update': True,
                    'output_file': self.sources[library]['output_file'],
                    'files_count': 0
                }
        
        return status


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Менеджер документации BOT Trading v3')
    parser.add_argument('--update-all', action='store_true', 
                       help='Обновить всю документацию')
    parser.add_argument('--force', action='store_true',
                       help='Принудительное обновление (игнорировать время последнего обновления)')
    parser.add_argument('--library', type=str,
                       help='Обновить конкретную библиотеку')
    parser.add_argument('--check-updates', action='store_true',
                       help='Проверить какие библиотеки требуют обновления')
    parser.add_argument('--status', action='store_true',
                       help='Показать статус всех библиотек')
    
    args = parser.parse_args()
    
    async with DocumentationDownloader() as downloader:
        if args.status:
            status = downloader.get_status()
            print("\n=== Статус документации ===")
            for library, info in status.items():
                print(f"{library:15} | Последнее обновление: {info['last_update']:16} | "
                      f"Требует обновления: {'ДА' if info['needs_update'] else 'НЕТ':3} | "
                      f"Файлов: {info['files_count']}")
        
        elif args.check_updates:
            updates_needed = downloader.check_updates_needed()
            if updates_needed:
                print(f"Требуют обновления: {', '.join(updates_needed)}")
            else:
                print("Все библиотеки актуальны")
        
        elif args.library:
            await downloader.download_library_docs(args.library)
        
        elif args.update_all:
            await downloader.update_all_libraries(force=args.force)
        
        else:
            # По умолчанию проверяем и обновляем только те, что требуют обновления
            updates_needed = downloader.check_updates_needed()
            if updates_needed:
                print(f"Обновляем: {', '.join(updates_needed)}")
                await downloader.update_all_libraries()
            else:
                print("Вся документация актуальна")


if __name__ == "__main__":
    asyncio.run(main())