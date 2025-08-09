"""
Agents Package - Система автоматических агентов BOT_AI_V3

Содержит агентов для автоматического:
- Тестирования и диагностики
- Исправления ошибок
- Мониторинга системы
- Интеграции с Claude Code Agent System

Автор: Claude Code Agent System
Версия: 1.0.0
"""

from .testing_agent import ErrorPattern, TestingAgent

__all__ = ["TestingAgent", "ErrorPattern"]

__version__ = "1.0.0"
