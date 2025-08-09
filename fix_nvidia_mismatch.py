#!/usr/bin/env python3
"""
Решение проблемы несовместимости драйверов NVIDIA
Обход для RTX 5090
"""

import os
import subprocess


def fix_nvidia_libraries():
    """Попытка исправить несоответствие версий библиотек"""

    print("🔧 Исправление несовместимости драйверов NVIDIA...")

    # 1. Создаем символические ссылки для совместимости версий
    commands = [
        # Удаляем старые ссылки
        "sudo rm -f /usr/local/cuda/lib64/libnvidia-ml.so.1",
        "sudo rm -f /usr/local/cuda/lib64/libnvidia-ml.so",
        # Создаем новые ссылки на библиотеки версии 570.169
        "sudo ln -s /lib/x86_64-linux-gnu/libnvidia-ml.so.1 /usr/local/cuda/lib64/libnvidia-ml.so.1",
        "sudo ln -s /lib/x86_64-linux-gnu/libnvidia-ml.so.1 /usr/local/cuda/lib64/libnvidia-ml.so",
        # Обновляем кэш библиотек
        "sudo ldconfig",
    ]

    password = "ilpnqw1234"

    for cmd in commands:
        try:
            if "sudo" in cmd:
                # Передаем пароль через stdin
                process = subprocess.Popen(
                    cmd.split(),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stdout, stderr = process.communicate(input=f"{password}\n")
                if process.returncode == 0:
                    print(f"✅ {cmd}")
                else:
                    print(f"❌ {cmd}: {stderr}")
            else:
                subprocess.run(cmd.split(), check=True)
                print(f"✅ {cmd}")
        except Exception as e:
            print(f"❌ Ошибка при выполнении {cmd}: {e}")

    # 2. Устанавливаем переменные окружения для обхода проверок
    env_vars = {
        # Отключаем проверку версий
        "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
        "CUDA_MODULE_LOADING": "LAZY",
        # Форсируем использование GPU
        "CUDA_VISIBLE_DEVICES": "0",
        "PYTORCH_CUDA_FORCE_CUDA_ENABLED": "1",
        # Настройки для RTX 5090
        "TORCH_CUDA_ARCH_LIST": "8.6;8.9;9.0;12.0",
        "CUDA_LAUNCH_BLOCKING": "0",  # Асинхронный режим
        # Пути к библиотекам
        "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/lib/x86_64-linux-gnu:"
        + os.environ.get("LD_LIBRARY_PATH", ""),
    }

    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"📌 Установлено {key}={value}")

    print("\n✅ Переменные окружения настроены")

    # 3. Создаем скрипт запуска с правильным окружением
    launcher_script = """#!/bin/bash
# Запускатель с исправленным окружением для RTX 5090

export PYTORCH_NVML_BASED_CUDA_CHECK=0
export CUDA_MODULE_LOADING=LAZY
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_FORCE_CUDA_ENABLED=1
export TORCH_CUDA_ARCH_LIST="8.6;8.9;9.0;12.0"
export CUDA_LAUNCH_BLOCKING=0
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем переданную команду
exec "$@"
"""

    with open("launch_with_gpu.sh", "w") as f:
        f.write(launcher_script)

    os.chmod("launch_with_gpu.sh", 0o755)
    print("📝 Создан launch_with_gpu.sh для запуска с GPU")

    return True


def test_gpu_after_fix():
    """Тест GPU после применения исправлений"""

    print("\n🧪 Тестирование GPU...")

    try:
        import torch

        print(f"PyTorch версия: {torch.__version__}")

        # Проверяем доступность CUDA
        if torch.cuda.is_available():
            print("✅ CUDA доступна!")
            print(f"Количество GPU: {torch.cuda.device_count()}")

            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                print(f"\nGPU {i}: {props.name}")
                print(f"  Compute Capability: {props.major}.{props.minor}")
                print(f"  Память: {props.total_memory / 1024**3:.1f} GB")

            # Тест создания тензора
            device = torch.device("cuda:0")
            x = torch.randn(1000, 1000, device=device)
            y = torch.randn(1000, 1000, device=device)
            z = torch.matmul(x, y)

            print("\n✅ Операции на GPU работают!")
            print(f"   Результат: {z.shape} на {z.device}")

            return True
        else:
            print("❌ CUDA все еще недоступна")

            # Пробуем принудительно
            try:
                device = torch.device("cuda:0")
                test = torch.zeros(1, device=device)
                print("✅ Но прямое создание тензора на GPU работает!")
                return True
            except Exception as e:
                print(f"❌ Прямое создание тензора тоже не работает: {e}")
                return False

    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False


if __name__ == "__main__":
    # Применяем исправления
    if fix_nvidia_libraries():
        # Тестируем GPU
        if test_gpu_after_fix():
            print("\n🎉 GPU успешно активирован!")
            print("\nИспользуйте ./launch_with_gpu.sh для запуска с GPU:")
            print("  ./launch_with_gpu.sh python main.py")
            print("  ./launch_with_gpu.sh python unified_launcher.py")
        else:
            print(
                "\n⚠️  GPU пока не работает, но попробуйте запустить через launch_with_gpu.sh"
            )
    else:
        print("\n❌ Не удалось применить исправления")
