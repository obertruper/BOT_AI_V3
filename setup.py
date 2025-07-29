"""
BOT_Trading v3.0 Setup Script
Установка и настройка мульти-трейдер торговой системы
"""

from setuptools import setup, find_packages
import os

# Получение версии из файла версии
def get_version():
    """Получение версии из файла VERSION"""
    version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return f.read().strip()
    return '3.0.0'

# Чтение README файла
def get_long_description():
    """Получение длинного описания из README"""
    readme_file = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_file):
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "BOT_Trading v3.0 - Мульти-трейдер система автоматизированной торговли"

# Чтение зависимостей
def get_requirements():
    """Получение зависимостей из requirements.txt"""
    requirements = []
    req_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.append(line)
    return requirements

setup(
    name="bot-trading-v3",
    version=get_version(),
    author="OberTrading Team",
    author_email="support@obertrading.com",
    description="Мульти-трейдер система автоматизированной торговли криптовалютами",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/obertruper/BOT_Trading_v3",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=get_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "monitoring": [
            "prometheus-client>=0.17.0",
            "sentry-sdk>=1.28.0",
            "grafana-api>=1.0.3",
        ],
        "telegram": [
            "python-telegram-bot>=20.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bot-trading=main:main",
            "bot-trading-v3=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": [
            "config/*.yaml",
            "config/**/*.yaml",
            "models/**/*",
            "docs/*.md",
            "scripts/*.sh",
        ],
    },
    zip_safe=False,
    keywords=[
        "trading",
        "cryptocurrency",
        "bitcoin",
        "algorithmic-trading",
        "automated-trading",
        "machine-learning",
        "quantitative-finance",
        "bybit",
        "binance",
        "multi-exchange",
    ],
    project_urls={
        "Bug Reports": "https://github.com/obertruper/BOT_Trading_v3/issues",
        "Source": "https://github.com/obertruper/BOT_Trading_v3",
        "Documentation": "https://bot-trading-v3.readthedocs.io/",
    },
)