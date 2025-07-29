#!/usr/bin/env python3
"""
Система сбора длинных ответов от AI через MCP Playwright
Обрабатывает streaming ответы, скроллинг, пагинацию

Автор: BOT Trading v3 Team
"""

import asyncio
import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

# MCP Playwright imports
from mcp__playwright__browser_snapshot import mcp__playwright__browser_snapshot
from mcp__playwright__browser_take_screenshot import mcp__playwright__browser_take_screenshot
from mcp__playwright__browser_scroll import mcp__playwright__browser_scroll
from mcp__playwright__browser_press_key import mcp__playwright__browser_press_key
from mcp__playwright__browser_wait_for import mcp__playwright__browser_wait_for

logger = logging.getLogger(__name__)

@dataclass
class ResponseChunk:
    """Фрагмент ответа AI"""
    timestamp: datetime
    content: str
    chunk_number: int
    is_complete: bool = False
    metadata: Dict = None

@dataclass
class AIResponse:
    """Полный ответ AI системы"""
    ai_system: str
    chat_id: str
    full_content: str
    chunks: List[ResponseChunk]
    start_time: datetime
    end_time: Optional[datetime] = None
    is_streaming: bool = True
    word_count: int = 0
    estimated_tokens: int = 0

class ResponseCollector:
    """Система сбора длинных ответов от AI"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        
        # Селекторы для разных AI систем
        self.ai_selectors = {
            "chatgpt": {
                "response_container": "[data-testid*='conversation']",
                "message_elements": "[data-message-author-role='assistant']",
                "typing_indicator": "[data-testid='typing']", 
                "stop_button": "[data-testid='stop-button']",
                "scroll_container": "main"
            },
            "grok": {
                "response_container": "[data-testid='conversation']",
                "message_elements": "[data-testid='message']",
                "typing_indicator": ".typing-indicator",
                "stop_button": "button[aria-label='Stop']",
                "scroll_container": "main"
            },
            "claude": {
                "response_container": "[data-testid='conversation']", 
                "message_elements": "[data-testid='message']",
                "typing_indicator": ".loading-indicator",
                "stop_button": "[data-testid='stop-button']",
                "scroll_container": "main"
            }
        }
    
    def _default_config(self) -> Dict:
        """Дефолтная конфигурация"""
        return {
            "max_wait_time": 300,        # 5 минут максимум ожидания
            "chunk_interval": 3,         # Проверка каждые 3 секунды
            "streaming_timeout": 30,     # Таймаут для streaming
            "scroll_step": 500,          # Пикселей скролла за раз
            "max_chunks": 100,           # Максимум чанков
            "min_response_length": 50,   # Минимальная длина ответа
            "completion_keywords": [     # Ключевые слова завершения
                "completed", "finished", "done", "final",
                "завершено", "готово", "финал"
            ]
        }
    
    async def collect_ai_response(
        self, 
        ai_system: str, 
        chat_id: str,
        expected_length: str = "medium"
    ) -> AIResponse:
        """
        Сбор полного ответа от AI системы
        
        Args:
            ai_system: Название AI системы (chatgpt/grok/claude)
            chat_id: ID чата
            expected_length: Ожидаемая длина (short/medium/long/very_long)
        
        Returns:
            AIResponse с полным содержимым
        """
        logger.info(f"Начало сбора ответа от {ai_system}, chat: {chat_id}")
        
        response = AIResponse(
            ai_system=ai_system,
            chat_id=chat_id,
            full_content="",
            chunks=[],
            start_time=datetime.now()
        )
        
        # Настройки в зависимости от ожидаемой длины
        collection_config = self._get_collection_config(expected_length)
        
        try:
            # Ждем начала ответа
            await self._wait_for_response_start(ai_system)
            
            # Определяем тип ответа (streaming или статический)
            is_streaming = await self._detect_streaming_response(ai_system)
            response.is_streaming = is_streaming
            
            if is_streaming:
                # Собираем streaming ответ по частям
                await self._collect_streaming_response(response, collection_config)
            else:
                # Собираем статический ответ
                await self._collect_static_response(response, collection_config)
            
            # Финализируем ответ
            await self._finalize_response(response)
            
            logger.info(f"Ответ от {ai_system} собран: {response.word_count} слов, "
                       f"{len(response.chunks)} чанков")
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка сбора ответа от {ai_system}: {e}")
            response.full_content = f"ERROR: Не удалось собрать ответ - {e}"
            response.end_time = datetime.now()
            return response
    
    def _get_collection_config(self, expected_length: str) -> Dict:
        """Конфигурация сбора в зависимости от ожидаемой длины"""
        configs = {
            "short": {
                "max_wait": 60,          # 1 минута
                "chunk_interval": 2,     # Каждые 2 секунды  
                "max_chunks": 10
            },
            "medium": {
                "max_wait": 180,         # 3 минуты
                "chunk_interval": 3,     # Каждые 3 секунды
                "max_chunks": 30
            },
            "long": {
                "max_wait": 300,         # 5 минут
                "chunk_interval": 4,     # Каждые 4 секунды
                "max_chunks": 60
            },
            "very_long": {
                "max_wait": 600,         # 10 минут
                "chunk_interval": 5,     # Каждые 5 секунд
                "max_chunks": 100
            }
        }
        return configs.get(expected_length, configs["medium"])
    
    async def _wait_for_response_start(self, ai_system: str):
        """Ожидание начала ответа от AI"""
        selectors = self.ai_selectors[ai_system]
        
        # Ждем появления нового сообщения или индикатора печати
        await asyncio.sleep(2)  # Даем время на начало ответа
        
        # Проверяем индикатор печати
        try:
            await mcp__playwright__browser_wait_for(
                text="typing", 
                time=10
            )
        except:
            # Если нет индикатора печати, ждем просто появления текста
            await asyncio.sleep(3)
    
    async def _detect_streaming_response(self, ai_system: str) -> bool:
        """Определение streaming ответа"""
        selectors = self.ai_selectors[ai_system]
        
        # Делаем два snapshot с интервалом
        snapshot1 = await mcp__playwright__browser_snapshot()
        await asyncio.sleep(2)
        snapshot2 = await mcp__playwright__browser_snapshot()
        
        # Если контент изменился - это streaming
        return len(snapshot2) != len(snapshot1)
    
    async def _collect_streaming_response(
        self, 
        response: AIResponse, 
        config: Dict
    ):
        """Сбор streaming ответа по частям"""
        logger.info(f"Сбор streaming ответа от {response.ai_system}")
        
        chunk_number = 0
        last_content = ""
        stable_count = 0
        max_stable = 3  # Количество стабильных итераций для завершения
        
        start_time = time.time()
        
        while (time.time() - start_time) < config["max_wait"]:
            try:
                # Получаем текущий snapshot
                snapshot = await mcp__playwright__browser_snapshot()
                
                # Извлекаем текст ответа
                current_content = self._extract_response_text(snapshot, response.ai_system)
                
                # Если контент изменился
                if current_content != last_content and len(current_content) > len(last_content):
                    chunk = ResponseChunk(
                        timestamp=datetime.now(),
                        content=current_content,
                        chunk_number=chunk_number,
                        metadata={"snapshot_length": len(snapshot)}
                    )
                    
                    response.chunks.append(chunk)
                    last_content = current_content
                    chunk_number += 1
                    stable_count = 0
                    
                    logger.debug(f"Chunk {chunk_number}: +{len(current_content)} символов")
                    
                    # Автопрокрутка если ответ длинный
                    if len(current_content) > 2000:
                        await self._auto_scroll_response(response.ai_system)
                    
                else:
                    # Контент не изменился
                    stable_count += 1
                    
                    # Если стабильно несколько итераций - ответ завершен
                    if stable_count >= max_stable:
                        logger.info(f"Ответ стабилизирован, завершаем сбор")
                        break
                
                # Проверяем индикаторы завершения
                if self._is_response_complete(snapshot, response.ai_system):
                    logger.info(f"Обнаружен индикатор завершения ответа")
                    break
                
                # Проверяем максимальное количество чанков
                if chunk_number >= config["max_chunks"]:
                    logger.warning(f"Достигнуто максимальное количество чанков: {config['max_chunks']}")
                    break
                
                # Пауза между итерациями
                await asyncio.sleep(config["chunk_interval"])
                
            except Exception as e:
                logger.error(f"Ошибка в итерации сбора: {e}")
                await asyncio.sleep(2)
                continue
        
        # Финальный контент
        response.full_content = last_content
    
    async def _collect_static_response(
        self, 
        response: AIResponse, 
        config: Dict
    ):
        """Сбор статического ответа"""
        logger.info(f"Сбор статического ответа от {response.ai_system}")
        
        # Ждем завершения генерации
        await asyncio.sleep(5)
        
        # Собираем весь ответ за раз с возможной прокруткой
        full_content = await self._collect_with_scrolling(response.ai_system)
        
        # Создаем один chunk
        chunk = ResponseChunk(
            timestamp=datetime.now(),
            content=full_content,
            chunk_number=0,
            is_complete=True
        )
        
        response.chunks.append(chunk)
        response.full_content = full_content
    
    async def _collect_with_scrolling(self, ai_system: str) -> str:
        """Сбор ответа с автоматической прокруткой"""
        selectors = self.ai_selectors[ai_system]
        
        all_content = ""
        last_height = 0
        
        for scroll_attempt in range(10):  # Максимум 10 прокруток
            # Получаем текущий контент
            snapshot = await mcp__playwright__browser_snapshot()
            current_content = self._extract_response_text(snapshot, ai_system)
            
            if len(current_content) > len(all_content):
                all_content = current_content
            
            # Скроллим вниз
            await mcp__playwright__browser_press_key(key="PageDown")
            await asyncio.sleep(1)
            
            # Проверяем, изменилась ли высота
            new_snapshot = await mcp__playwright__browser_snapshot()
            if len(new_snapshot) == last_height:
                break  # Больше нечего скроллить
            
            last_height = len(new_snapshot)
        
        return all_content
    
    async def _auto_scroll_response(self, ai_system: str):
        """Автоматическая прокрутка для длинных ответов"""
        try:
            await mcp__playwright__browser_press_key(key="End")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.debug(f"Не удалось прокрутить: {e}")
    
    def _extract_response_text(self, snapshot: str, ai_system: str) -> str:
        """Извлечение текста ответа из snapshot"""
        # Простое извлечение последнего сообщения от AI
        # В реальности здесь будет более сложная логика парсинга
        
        # Ищем паттерны сообщений AI
        ai_patterns = {
            "chatgpt": r'assistant"[^>]*>([^<]+)',
            "grok": r'ai-message[^>]*>([^<]+)',
            "claude": r'assistant[^>]*>([^<]+)'
        }
        
        pattern = ai_patterns.get(ai_system, r'([^<]+)')
        
        try:
            matches = re.findall(pattern, snapshot, re.DOTALL | re.IGNORECASE)
            if matches:
                # Берем последний (самый свежий) ответ
                return matches[-1].strip()
        except Exception as e:
            logger.debug(f"Ошибка извлечения текста: {e}")
        
        # Fallback: ищем просто текст после ключевых слов
        fallback_patterns = [
            r"(?:ответ|response|reply)[:\s]*([^<\n]{100,})",
            r"(?:решение|solution)[:\s]*([^<\n]{100,})"
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, snapshot, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[-1].strip()
        
        # Крайний fallback: берем видимый текст
        visible_text = re.sub(r'<[^>]+>', '', snapshot)
        lines = visible_text.split('\n')
        content_lines = [line.strip() for line in lines if len(line.strip()) > 50]
        
        if content_lines:
            return '\n'.join(content_lines[-10:])  # Последние 10 строк
        
        return "Не удалось извлечь ответ"
    
    def _is_response_complete(self, snapshot: str, ai_system: str) -> bool:
        """Проверка завершения ответа"""
        # Проверяем отсутствие индикаторов печати
        typing_indicators = ["typing", "generating", "loading", "thinking"]
        
        for indicator in typing_indicators:
            if indicator.lower() in snapshot.lower():
                return False
        
        # Проверяем ключевые слова завершения
        completion_keywords = self.config["completion_keywords"]
        
        for keyword in completion_keywords:
            if keyword.lower() in snapshot.lower():
                return True
        
        return True
    
    async def _finalize_response(self, response: AIResponse):
        """Финализация ответа"""
        response.end_time = datetime.now()
        
        # Подсчет статистики
        response.word_count = len(response.full_content.split())
        response.estimated_tokens = int(response.word_count * 1.3)  # Примерная оценка
        
        # Отмечаем последний chunk как завершенный
        if response.chunks:
            response.chunks[-1].is_complete = True
        
        logger.info(f"Ответ от {response.ai_system} финализирован: "
                   f"{response.word_count} слов, {response.estimated_tokens} токенов")
    
    async def collect_multiple_responses(
        self, 
        ai_systems: List[str], 
        chat_ids: Dict[str, str],
        expected_length: str = "medium"
    ) -> Dict[str, AIResponse]:
        """Параллельный сбор ответов от нескольких AI систем"""
        logger.info(f"Параллельный сбор ответов от {len(ai_systems)} AI систем")
        
        # Запускаем сбор параллельно
        tasks = [
            self.collect_ai_response(ai_system, chat_ids[ai_system], expected_length)
            for ai_system in ai_systems
            if ai_system in chat_ids
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        result = {}
        for i, ai_system in enumerate(ai_systems):
            if ai_system in chat_ids:
                if isinstance(responses[i], AIResponse):
                    result[ai_system] = responses[i]
                else:
                    logger.error(f"Ошибка сбора ответа от {ai_system}: {responses[i]}")
                    # Создаем пустой ответ с ошибкой
                    result[ai_system] = AIResponse(
                        ai_system=ai_system,
                        chat_id=chat_ids[ai_system],
                        full_content=f"ERROR: {responses[i]}",
                        chunks=[],
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        is_streaming=False
                    )
        
        return result


# Интеграция с основной системой кросс-верификации
class EnhancedResponseHandler:
    """Улучшенный обработчик ответов для автоматизированной кросс-верификации"""
    
    def __init__(self):
        self.collector = ResponseCollector()
    
    async def enhanced_send_task_to_all_chats(
        self, 
        task,
        expected_length: str = "long"
    ) -> Dict[str, str]:
        """
        Улучшенная отправка с умным сбором длинных ответов
        
        Args:
            task: CrossVerificationTask
            expected_length: Ожидаемая длина ответов
        
        Returns:
            Dict с полными ответами от каждой AI системы
        """
        logger.info(f"Улучшенная отправка задачи {task.task_id} с ожиданием {expected_length} ответов")
        
        # Сначала отправляем запросы (используем существующую логику)
        # Затем умно собираем ответы
        
        chat_ids = {ai_system: session.chat_id 
                   for ai_system, session in task.chat_sessions.items()}
        
        # Собираем ответы через улучшенную систему
        ai_responses = await self.collector.collect_multiple_responses(
            list(chat_ids.keys()),
            chat_ids,
            expected_length
        )
        
        # Конвертируем в формат для основной системы
        responses = {}
        for ai_system, ai_response in ai_responses.items():
            responses[ai_system] = ai_response.full_content
            
            # Сохраняем детальную информацию в сессии
            if ai_system in task.chat_sessions:
                session = task.chat_sessions[ai_system]
                session.responses.append(ai_response.full_content)
                session.status = "responded"
                
                # Добавляем метаданные
                session.metadata = {
                    "word_count": ai_response.word_count,
                    "estimated_tokens": ai_response.estimated_tokens,
                    "chunks_count": len(ai_response.chunks),
                    "was_streaming": ai_response.is_streaming,
                    "collection_time": (ai_response.end_time - ai_response.start_time).total_seconds()
                }
        
        return responses