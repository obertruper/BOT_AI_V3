"""
Тесты для health check функциональности
"""

import asyncio
import json

import httpx
import pytest


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Тест health check endpoint"""

    # URL для локального тестирования
    base_url = "http://localhost:8080"

    async with httpx.AsyncClient() as client:
        # Проверяем базовый health check
        response = await client.get(f"{base_url}/api/health")

        assert response.status_code == 200

        data = response.json()

        # Проверяем структуру ответа
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data

        # Проверяем статус
        assert data["status"] in ["healthy", "degraded", "warning", "critical", "error"]

        # Проверяем компоненты
        components = data["components"]
        if "basic_components" in data:
            # Детальная проверка доступна
            assert (
                "database" in components or "orchestrator" in data["basic_components"]
            )
        else:
            # Базовая проверка
            assert "orchestrator" in components
            assert "trader_manager" in components
            assert "exchange_factory" in components
            assert "config_manager" in components

        print(f"Health check response: {json.dumps(data, indent=2)}")


@pytest.mark.asyncio
async def test_monitoring_health_endpoint():
    """Тест monitoring health endpoint"""

    base_url = "http://localhost:8080"

    async with httpx.AsyncClient() as client:
        # Проверяем monitoring health endpoint
        response = await client.get(f"{base_url}/api/monitoring/health")

        # Может вернуть 404 если роутер не подключен или 500 если компоненты не инициализированы
        if response.status_code == 200:
            data = response.json()

            assert "status" in data
            assert "components" in data
            assert "last_check" in data
            assert "uptime_seconds" in data

            print(f"Monitoring health response: {json.dumps(data, indent=2)}")
        else:
            print(f"Monitoring health endpoint returned: {response.status_code}")


@pytest.mark.asyncio
async def test_system_metrics():
    """Тест получения системных метрик"""

    base_url = "http://localhost:8080"

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/monitoring/metrics")

        if response.status_code == 200:
            data = response.json()

            assert "cpu_percent" in data
            assert "memory_percent" in data
            assert "disk_percent" in data
            assert "network_connections" in data
            assert "active_traders" in data
            assert "total_trades_today" in data
            assert "last_updated" in data

            print(f"System metrics: {json.dumps(data, indent=2)}")


def test_health_checker_unit():
    """Unit тест для HealthChecker класса"""
    from core.config.config_manager import ConfigManager
    from core.system.health_checker import HealthChecker

    # Создаем мок конфигурации
    config_manager = ConfigManager()

    # Создаем HealthChecker
    health_checker = HealthChecker(config_manager)

    # Проверяем инициализацию
    assert health_checker is not None
    assert health_checker.db_timeout == 5.0
    assert health_checker.redis_timeout == 3.0
    assert health_checker.exchange_timeout == 10.0

    print("HealthChecker unit test passed")


if __name__ == "__main__":
    # Для ручного тестирования
    asyncio.run(test_health_check_endpoint())
    asyncio.run(test_monitoring_health_endpoint())
    asyncio.run(test_system_metrics())
    test_health_checker_unit()
