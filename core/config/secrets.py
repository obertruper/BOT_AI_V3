#!/usr/bin/env python3
"""Система управления секретами для BOT_AI_V3.

Обеспечивает безопасное хранение и доступ к секретным данным
с поддержкой различных бэкендов и маскированием в логах.
"""

import json
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

from core.exceptions import ConfigurationError


class SecretBackend(ABC):
    """Абстрактный класс для бэкендов хранения секретов."""

    @abstractmethod
    def get_secret(self, key: str) -> str | None:
        """Получает секрет по ключу."""
        pass

    @abstractmethod
    def set_secret(self, key: str, value: str) -> None:
        """Устанавливает секрет."""
        pass

    @abstractmethod
    def delete_secret(self, key: str) -> None:
        """Удаляет секрет."""
        pass

    @abstractmethod
    def list_secrets(self) -> list[str]:
        """Возвращает список всех ключей секретов."""
        pass


class EnvFileBackend(SecretBackend):
    """Бэкенд для хранения секретов в .env файле."""

    def __init__(self, env_file: Path | None = None):
        """Инициализирует бэкенд.

        Args:
            env_file: Путь к .env файлу. По умолчанию ищет в корне проекта.
        """
        if env_file is None:
            # Ищем .env в корне проекта
            project_root = Path(__file__).parent.parent.parent
            env_file = project_root / ".env"

        self.env_file = env_file
        self._load_env()

    def _load_env(self) -> None:
        """Загружает переменные из .env файла."""
        if self.env_file.exists():
            load_dotenv(self.env_file, override=True)

    def get_secret(self, key: str) -> str | None:
        """Получает секрет из переменной окружения."""
        return os.getenv(key)

    def set_secret(self, key: str, value: str) -> None:
        """Устанавливает секрет в переменную окружения и .env файл."""
        os.environ[key] = value
        self._update_env_file(key, value)

    def delete_secret(self, key: str) -> None:
        """Удаляет секрет из переменных окружения и .env файла."""
        if key in os.environ:
            del os.environ[key]
        self._remove_from_env_file(key)

    def list_secrets(self) -> list[str]:
        """Возвращает список всех секретных ключей."""
        # Определяем паттерны секретных ключей
        secret_patterns = [
            r".*_API_KEY$",
            r".*_API_SECRET$",
            r".*_PASSWORD$",
            r".*_TOKEN$",
            r".*_SECRET$",
            r"^JWT_.*",
            r"^DATABASE_URL$",
            r"^REDIS_URL$",
        ]

        secrets = []
        for key in os.environ:
            for pattern in secret_patterns:
                if re.match(pattern, key):
                    secrets.append(key)
                    break

        return sorted(secrets)

    def _update_env_file(self, key: str, value: str) -> None:
        """Обновляет .env файл с новым значением."""
        lines = []
        key_found = False

        if self.env_file.exists():
            with open(self.env_file) as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        lines.append(f"{key}={value}\n")
                        key_found = True
                    else:
                        lines.append(line)

        if not key_found:
            lines.append(f"{key}={value}\n")

        with open(self.env_file, "w") as f:
            f.writelines(lines)

    def _remove_from_env_file(self, key: str) -> None:
        """Удаляет ключ из .env файла."""
        if not self.env_file.exists():
            return

        lines = []
        with open(self.env_file) as f:
            for line in f:
                if not line.startswith(f"{key}="):
                    lines.append(line)

        with open(self.env_file, "w") as f:
            f.writelines(lines)


class EncryptedFileBackend(SecretBackend):
    """Бэкенд для хранения зашифрованных секретов в файле."""

    def __init__(self, secrets_file: Path | None = None, key_file: Path | None = None):
        """Инициализирует бэкенд.

        Args:
            secrets_file: Путь к файлу с зашифрованными секретами.
            key_file: Путь к файлу с ключом шифрования.
        """
        if secrets_file is None:
            project_root = Path(__file__).parent.parent.parent
            secrets_file = project_root / ".secrets.enc"

        if key_file is None:
            project_root = Path(__file__).parent.parent.parent
            key_file = project_root / ".secrets.key"

        self.secrets_file = secrets_file
        self.key_file = key_file
        self._cipher = self._get_or_create_cipher()
        self._secrets: dict[str, str] = self._load_secrets()

    def _get_or_create_cipher(self) -> Fernet:
        """Получает или создает ключ шифрования."""
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            # Устанавливаем права доступа только для владельца
            self.key_file.chmod(0o600)
            print(f"🔐 Создан новый ключ шифрования: {self.key_file}")

        return Fernet(key)

    def _load_secrets(self) -> dict[str, str]:
        """Загружает и расшифровывает секреты из файла."""
        if not self.secrets_file.exists():
            return {}

        try:
            with open(self.secrets_file, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self._cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())

        except Exception as e:
            print(f"⚠️ Ошибка загрузки секретов: {e}")
            return {}

    def _save_secrets(self) -> None:
        """Шифрует и сохраняет секреты в файл."""
        data = json.dumps(self._secrets).encode()
        encrypted_data = self._cipher.encrypt(data)

        with open(self.secrets_file, "wb") as f:
            f.write(encrypted_data)

        # Устанавливаем права доступа только для владельца
        self.secrets_file.chmod(0o600)

    def get_secret(self, key: str) -> str | None:
        """Получает расшифрованный секрет."""
        return self._secrets.get(key)

    def set_secret(self, key: str, value: str) -> None:
        """Устанавливает и шифрует секрет."""
        self._secrets[key] = value
        self._save_secrets()

    def delete_secret(self, key: str) -> None:
        """Удаляет секрет."""
        if key in self._secrets:
            del self._secrets[key]
            self._save_secrets()

    def list_secrets(self) -> list[str]:
        """Возвращает список всех ключей секретов."""
        return sorted(self._secrets.keys())


class SecretsManager:
    """Централизованный менеджер для управления секретами."""

    def __init__(self, backend: SecretBackend | None = None):
        """Инициализирует менеджер секретов.

        Args:
            backend: Бэкенд для хранения секретов.
                    По умолчанию используется EnvFileBackend.
        """
        self.backend = backend or EnvFileBackend()
        self._masked_patterns: set[re.Pattern] = self._create_mask_patterns()
        self._cache: dict[str, str | None] = {}
        self._required_secrets: dict[str, str] = self._define_required_secrets()

    def _create_mask_patterns(self) -> set[re.Pattern]:
        """Создает паттерны для маскирования секретов в логах."""
        patterns = [
            # API ключи и токены
            r"(['\"]?)([A-Za-z0-9]{32,})\1",
            r"(api[_-]?key|token|secret)['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9\-_]{20,})['\"]?",
            # Пароли
            r"(password|pwd)['\"]?\s*[:=]\s*['\"]?([^\s'\"]+)['\"]?",
            # JWT токены
            r"Bearer\s+([A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+)",
            # URL с credentials
            r"(https?|ftp)://([^:]+):([^@]+)@",
        ]
        return {re.compile(pattern, re.IGNORECASE) for pattern in patterns}

    def _define_required_secrets(self) -> dict[str, str]:
        """Определяет обязательные секреты и их описания."""
        return {
            # Биржи
            "BYBIT_API_KEY": "API ключ для Bybit",
            "BYBIT_API_SECRET": "API секрет для Bybit",
            "BINANCE_API_KEY": "API ключ для Binance",
            "BINANCE_API_SECRET": "API секрет для Binance",
            # База данных
            "DB_PASSWORD": "Пароль для PostgreSQL",
            # Уведомления
            "TELEGRAM_BOT_TOKEN": "Токен Telegram бота",
            "TELEGRAM_CHAT_ID": "ID чата Telegram",
            # Мониторинг
            "SENTRY_DSN": "DSN для Sentry",
        }

    def get(self, key: str, default: str | None = None, required: bool = False) -> str | None:
        """Получает секрет по ключу.

        Args:
            key: Ключ секрета.
            default: Значение по умолчанию.
            required: Является ли секрет обязательным.

        Returns:
            Значение секрета или default.

        Raises:
            ConfigurationError: Если обязательный секрет отсутствует.
        """
        # Проверяем кеш
        if key in self._cache:
            return self._cache[key]

        # Получаем из бэкенда
        value = self.backend.get_secret(key)

        if value is None:
            if required:
                raise ConfigurationError(
                    f"Обязательный секрет '{key}' не найден. "
                    f"Установите его в .env файле или через переменную окружения."
                )
            value = default

        # Кешируем результат
        self._cache[key] = value
        return value

    def set(self, key: str, value: str) -> None:
        """Устанавливает секрет.

        Args:
            key: Ключ секрета.
            value: Значение секрета.
        """
        self.backend.set_secret(key, value)
        self._cache[key] = value
        print(f"✅ Секрет '{key}' установлен")

    def delete(self, key: str) -> None:
        """Удаляет секрет.

        Args:
            key: Ключ секрета.
        """
        self.backend.delete_secret(key)
        if key in self._cache:
            del self._cache[key]
        print(f"🗑️ Секрет '{key}' удален")

    def list(self) -> list[str]:
        """Возвращает список всех секретов."""
        return self.backend.list_secrets()

    def validate_required(self) -> dict[str, bool]:
        """Проверяет наличие всех обязательных секретов.

        Returns:
            Словарь с результатами проверки для каждого секрета.
        """
        results = {}
        for key, description in self._required_secrets.items():
            value = self.get(key)
            results[key] = value is not None
            if not results[key]:
                print(f"⚠️ Отсутствует секрет: {key} - {description}")

        return results

    def mask_secrets_in_text(self, text: str) -> str:
        """Маскирует секреты в тексте для безопасного логирования.

        Args:
            text: Текст, который может содержать секреты.

        Returns:
            Текст с замаскированными секретами.
        """
        masked_text = text

        # Маскируем известные секреты
        for key in self.list():
            value = self.get(key)
            if value and len(value) > 4:
                # Оставляем первые 2 и последние 2 символа
                masked_value = f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
                masked_text = masked_text.replace(value, masked_value)

        # Применяем паттерны маскирования
        for pattern in self._masked_patterns:
            masked_text = pattern.sub(lambda m: self._mask_match(m), masked_text)

        return masked_text

    def _mask_match(self, match: re.Match) -> str:
        """Маскирует совпадение регулярного выражения.

        Args:
            match: Совпадение для маскирования.

        Returns:
            Замаскированная строка.
        """
        groups = match.groups()
        if len(groups) >= 2:
            # Маскируем вторую группу (обычно это значение)
            value = groups[-1]
            if len(value) > 4:
                masked = f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
                return match.group(0).replace(value, masked)
        return match.group(0)

    def export_template(self, output_path: Path) -> None:
        """Экспортирует шаблон .env файла с описаниями.

        Args:
            output_path: Путь для сохранения шаблона.
        """
        lines = [
            "# Шаблон конфигурации секретов для BOT_AI_V3\n",
            "# Скопируйте этот файл в .env и заполните значения\n",
            "\n",
        ]

        # Группируем секреты по категориям
        categories = {
            "Биржи": ["BYBIT", "BINANCE", "OKX", "GATEIO", "KUCOIN", "HTX", "BINGX"],
            "База данных": ["DB", "PGPORT", "PGUSER"],
            "Уведомления": ["TELEGRAM", "EMAIL", "DISCORD"],
            "Мониторинг": ["SENTRY", "PROMETHEUS"],
            "Общие": [],
        }

        for category, prefixes in categories.items():
            category_secrets = []
            for key, description in self._required_secrets.items():
                if any(key.startswith(prefix) for prefix in prefixes) or (category == "Общие" and not any(
                    key.startswith(p) for cat_prefixes in categories.values() for p in cat_prefixes
                )):
                    category_secrets.append((key, description))

            if category_secrets:
                lines.append(f"# === {category} ===\n")
                for key, description in sorted(category_secrets):
                    lines.append(f"# {description}\n")
                    lines.append(f"{key}=\n")
                lines.append("\n")

        with open(output_path, "w") as f:
            f.writelines(lines)

        print(f"✅ Шаблон .env экспортирован в {output_path}")

    def get_status_report(self) -> str:
        """Возвращает отчет о состоянии секретов.

        Returns:
            Форматированный отчет.
        """
        lines = ["=" * 50, "🔐 Отчет о состоянии секретов", "=" * 50]

        # Проверяем обязательные секреты
        validation_results = self.validate_required()

        configured = sum(1 for v in validation_results.values() if v)
        total = len(validation_results)

        lines.append("\n📊 Статистика:")
        lines.append(f"  - Настроено: {configured}/{total}")
        lines.append(f"  - Отсутствует: {total - configured}")

        # Детали по категориям
        lines.append("\n📋 Детали по категориям:")

        categories = {
            "Биржи": ["BYBIT", "BINANCE"],
            "База данных": ["DB"],
            "Уведомления": ["TELEGRAM"],
        }

        for category, prefixes in categories.items():
            category_results = {
                k: v
                for k, v in validation_results.items()
                if any(k.startswith(p) for p in prefixes)
            }
            if category_results:
                configured = sum(1 for v in category_results.values() if v)
                total = len(category_results)
                status = "✅" if configured == total else "⚠️"
                lines.append(f"  {status} {category}: {configured}/{total}")

        # Все установленные секреты (маскированные)
        all_secrets = self.list()
        if all_secrets:
            lines.append(f"\n🔑 Установленные секреты ({len(all_secrets)}):")
            for key in all_secrets[:10]:  # Показываем только первые 10
                value = self.get(key)
                if value:
                    masked = f"{value[:2]}{'*' * min(8, len(value) - 4)}{value[-2:] if len(value) > 4 else ''}"
                    lines.append(f"  - {key}: {masked}")
            if len(all_secrets) > 10:
                lines.append(f"  ... и еще {len(all_secrets) - 10}")

        lines.append("=" * 50)
        return "\n".join(lines)


# Глобальный экземпляр менеджера секретов
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Возвращает глобальный экземпляр менеджера секретов."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


# Удобные функции для быстрого доступа
def get_secret(key: str, default: str | None = None, required: bool = False) -> str | None:
    """Получает секрет по ключу."""
    return get_secrets_manager().get(key, default, required)


def set_secret(key: str, value: str) -> None:
    """Устанавливает секрет."""
    get_secrets_manager().set(key, value)


def mask_secrets(text: str) -> str:
    """Маскирует секреты в тексте."""
    return get_secrets_manager().mask_secrets_in_text(text)
