#!/usr/bin/env python3
"""ConfigLoader - загрузчик конфигурации с поддержкой профилей и переменных окружения.

Обеспечивает гибкую загрузку конфигурации из различных источников
с приоритетом: переменные окружения > профиль > базовая конфигурация.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from core.config.models import (
    RootConfig,
)
from core.exceptions import ConfigurationError


class ConfigLoader:
    """Загружает и объединяет конфигурацию из различных источников."""

    def __init__(self, config_dir: Path | None = None):
        """Инициализирует загрузчик конфигурации.

        Args:
            config_dir: Директория с конфигурационными файлами.
                       По умолчанию используется config/ в корне проекта.
        """
        if config_dir is None:
            # Определяем корень проекта (3 уровня вверх от текущего файла)
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = config_dir
        self._raw_config: dict[str, Any] = {}
        self._validated_config: RootConfig | None = None
        self._loaded_files: set[Path] = set()
        self._validation_warnings: list[str] = []

        # Загружаем переменные окружения из .env
        self._load_env_variables()

    def _load_env_variables(self) -> None:
        """Загружает переменные окружения из .env файла."""
        env_files = [
            self.config_dir.parent / ".env",  # Корень проекта
            self.config_dir.parent / ".env.local",  # Локальные переопределения
            Path.cwd() / ".env",  # Текущая директория
        ]

        for env_file in env_files:
            if env_file.exists():
                load_dotenv(env_file, override=True)
                print(f"✅ Загружены переменные окружения из {env_file}")

    def load(
        self,
        profile: str | None = None,
        additional_files: list[Path] | None = None,
    ) -> RootConfig:
        """Загружает и валидирует конфигурацию.

        Args:
            profile: Профиль окружения (dev, staging, prod).
                    Если не указан, определяется из переменной окружения.
            additional_files: Дополнительные файлы для загрузки.

        Returns:
            Валидированная конфигурация.

        Raises:
            ConfigurationError: При ошибках загрузки или валидации.
        """
        # Определяем профиль
        if profile is None:
            profile = os.getenv("APP_PROFILE", "development")

        # Очищаем предыдущую конфигурацию
        self._raw_config = {}
        self._loaded_files.clear()
        self._validation_warnings.clear()

        try:
            # 1. Загружаем базовую конфигурацию
            self._load_base_config()

            # 2. Загружаем доменные конфигурации
            self._load_domain_configs()

            # 3. Загружаем конфигурации бирж
            self._load_exchange_configs()

            # 4. Загружаем профиль окружения
            self._load_profile_config(profile)

            # 5. Загружаем дополнительные файлы
            if additional_files:
                for file_path in additional_files:
                    self._load_yaml_file(file_path)

            # 6. Применяем переменные окружения
            self._apply_env_overrides()

            # 7. Валидируем конфигурацию
            self._validate_config()

            # 8. Проверяем консистентность
            self._check_consistency()

            return self._validated_config

        except Exception as e:
            raise ConfigurationError(f"Ошибка загрузки конфигурации: {e}") from e

    def _load_base_config(self) -> None:
        """Загружает единый конфигурационный файл config.yaml."""
        config_file = self.config_dir / "config.yaml"

        if not config_file.exists():
            raise ConfigurationError(
                f"Единый конфигурационный файл {config_file} не найден. "
                "Убедитесь, что config/config.yaml существует."
            )

        self._load_yaml_file(config_file)

    def _load_domain_configs(self) -> None:
        """Загружает доменные конфигурации (отключено - используется единый файл)."""
        # Отключено - все конфигурации теперь в едином config.yaml
        pass

    def _load_exchange_configs(self) -> None:
        """Загружает конфигурации бирж (отключено - используется единый файл)."""
        # Отключено - все конфигурации теперь в едином config.yaml
        pass

    def _load_profile_config(self, profile: str) -> None:
        """Загружает конфигурацию профиля окружения (отключено - используется единый файл).

        Args:
            profile: Имя профиля (dev, staging, prod).
        """
        # Отключено - все конфигурации теперь в едином config.yaml
        # В будущем можно добавить поддержку профилей через переменные окружения
        if profile:
            print(f"ℹ️ Профиль {profile} игнорируется - используется единый config.yaml")

    def _load_yaml_file(self, file_path: Path) -> None:
        """Загружает YAML файл и объединяет с текущей конфигурацией.

        Args:
            file_path: Путь к YAML файлу.
        """
        if not file_path.exists():
            return

        if file_path in self._loaded_files:
            return  # Избегаем повторной загрузки

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

                # Заменяем переменные окружения
                content = self._substitute_env_vars(content)

                data = yaml.safe_load(content) or {}

            # Объединяем с существующей конфигурацией
            self._merge_configs(self._raw_config, data)
            self._loaded_files.add(file_path)

        except Exception as e:
            raise ConfigurationError(f"Ошибка загрузки {file_path}: {e}") from e

    def _substitute_env_vars(self, content: str) -> str:
        """Заменяет ${VAR_NAME} на значения из переменных окружения.

        Args:
            content: Содержимое YAML файла.

        Returns:
            Содержимое с замененными переменными.
        """
        import re

        pattern = r"\$\{([^}]+)\}"

        def replacer(match):
            var_name = match.group(1)
            # Поддержка значений по умолчанию: ${VAR:-default}
            if ":-" in var_name:
                var_name, default = var_name.split(":-", 1)
                return os.getenv(var_name, default)
            return os.getenv(var_name, match.group(0))

        return re.sub(pattern, replacer, content)

    def _merge_configs(self, base: dict[str, Any], update: dict[str, Any]) -> None:
        """Рекурсивно объединяет две конфигурации.

        Args:
            base: Базовая конфигурация (изменяется).
            update: Обновления для применения.
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def _apply_env_overrides(self) -> None:
        """Применяет переопределения из переменных окружения.

        Формат переменных: APP_SECTION__SUBSECTION__KEY
        Например: APP_TRADING__ORDERS__DEFAULT_LEVERAGE=10
        """
        prefix = "APP_"
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # Убираем префикс и разбиваем на части
            config_path = key[len(prefix) :].lower().split("__")

            # Применяем значение
            self._set_nested_value(self._raw_config, config_path, value)

    def _set_nested_value(self, config: dict[str, Any], path: list[str], value: str) -> None:
        """Устанавливает значение по вложенному пути.

        Args:
            config: Конфигурация для изменения.
            path: Путь к значению.
            value: Устанавливаемое значение.
        """
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Пытаемся преобразовать значение к правильному типу
        final_value = self._parse_value(value)
        current[path[-1]] = final_value

    def _parse_value(self, value: str) -> Any:
        """Преобразует строковое значение к правильному типу.

        Args:
            value: Строковое значение.

        Returns:
            Преобразованное значение.
        """
        # Булевы значения
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Числа
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Списки (разделенные запятыми)
        if "," in value:
            return [item.strip() for item in value.split(",")]

        return value

    def _validate_config(self) -> None:
        """Валидирует конфигурацию через Pydantic модели."""
        try:
            # Создаем экземпляр корневой модели
            self._validated_config = RootConfig(**self._raw_config)

        except ValidationError as e:
            errors = []
            for error in e.errors():
                location = " -> ".join(str(loc) for loc in error["loc"])
                msg = error["msg"]
                errors.append(f"{location}: {msg}")

            raise ConfigurationError("Ошибки валидации конфигурации:\n" + "\n".join(errors)) from e

    def _check_consistency(self) -> None:
        """Проверяет консистентность загруженной конфигурации."""
        if not self._validated_config:
            return

        warnings = self._validated_config.validate_consistency()
        if warnings:
            self._validation_warnings.extend(warnings)

        # Дополнительные проверки
        self._check_required_secrets()
        self._check_paths_exist()

    def _check_required_secrets(self) -> None:
        """Проверяет наличие необходимых секретов."""
        required_secrets = []

        # Проверяем API ключи для активных бирж
        if self._validated_config:
            exchanges = self._validated_config.exchanges.model_dump()
            for name, config in exchanges.items():
                if config.get("enabled") and not config.get("testnet"):
                    if not config.get("api_key"):
                        required_secrets.append(f"{name.upper()}_API_KEY")
                    if not config.get("api_secret"):
                        required_secrets.append(f"{name.upper()}_API_SECRET")

            # Проверяем пароль БД
            if not self._validated_config.database.password:
                required_secrets.append("DB_PASSWORD")

        if required_secrets:
            self._validation_warnings.append(f"Отсутствуют секреты: {', '.join(required_secrets)}")

    def _check_paths_exist(self) -> None:
        """Проверяет существование указанных путей."""
        if not self._validated_config:
            return

        ml_config = self._validated_config.ml
        if ml_config.enabled:
            if not ml_config.model.path.exists():
                self._validation_warnings.append(f"ML модель не найдена: {ml_config.model.path}")
            if not ml_config.model.scaler_path.exists():
                self._validation_warnings.append(f"Scaler не найден: {ml_config.model.scaler_path}")

    def get_validation_report(self) -> str:
        """Возвращает отчет о валидации конфигурации.

        Returns:
            Форматированный отчет.
        """
        lines = ["=" * 50, "📋 Отчет валидации конфигурации", "=" * 50]

        # Загруженные файлы
        lines.append("\n✅ Загруженные файлы:")
        for file_path in sorted(self._loaded_files):
            lines.append(f"  - {file_path.relative_to(self.config_dir.parent)}")

        # Основные параметры
        if self._validated_config:
            lines.append("\n📊 Основные параметры:")
            lines.append(f"  - Окружение: {self._validated_config.system.environment}")
            lines.append(f"  - Версия: {self._validated_config.system.version}")
            lines.append(f"  - БД порт: {self._validated_config.database.port}")
            lines.append(f"  - Leverage: {self._validated_config.trading.orders.default_leverage}x")
            lines.append(f"  - ML включен: {self._validated_config.ml.enabled}")

            # Активные биржи
            exchanges = self._validated_config.exchanges.model_dump()
            active_exchanges = [name for name, config in exchanges.items() if config.get("enabled")]
            if active_exchanges:
                lines.append(f"  - Активные биржи: {', '.join(active_exchanges)}")

        # Предупреждения
        if self._validation_warnings:
            lines.append("\n⚠️ Предупреждения:")
            for warning in self._validation_warnings:
                lines.append(f"  - {warning}")
        else:
            lines.append("\n✅ Предупреждений нет")

        lines.append("=" * 50)
        return "\n".join(lines)

    def export_config(self, output_path: Path, safe_mode: bool = True) -> None:
        """Экспортирует текущую конфигурацию в файл.

        Args:
            output_path: Путь для сохранения.
            safe_mode: Исключить секретные данные.
        """
        if not self._validated_config:
            raise ConfigurationError("Конфигурация не загружена")

        if safe_mode:
            config_dict = self._validated_config.get_frontend_safe_config()
        else:
            config_dict = self._validated_config.model_dump()

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, allow_unicode=True, sort_keys=False)

        print(f"✅ Конфигурация экспортирована в {output_path}")

    def watch_changes(self, callback) -> None:
        """Отслеживает изменения в конфигурационных файлах.

        Args:
            callback: Функция, вызываемая при изменении файлов.
        """
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            class ConfigChangeHandler(FileSystemEventHandler):
                def __init__(self, loader, callback):
                    self.loader = loader
                    self.callback = callback

                def on_modified(self, event):
                    if event.src_path.endswith(".yaml"):
                        print(f"🔄 Обнаружено изменение: {event.src_path}")
                        try:
                            # Перезагружаем конфигурацию
                            config = self.loader.load()
                            self.callback(config)
                        except Exception as e:
                            print(f"❌ Ошибка перезагрузки: {e}")

            handler = ConfigChangeHandler(self, callback)
            observer = Observer()
            observer.schedule(handler, str(self.config_dir), recursive=True)
            observer.start()
            print(f"👀 Отслеживание изменений в {self.config_dir}")
            return observer

        except ImportError:
            print("⚠️ Для отслеживания изменений установите watchdog: pip install watchdog")
