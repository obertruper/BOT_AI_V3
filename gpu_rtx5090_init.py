#!/usr/bin/env python3
"""
Инициализация GPU для RTX 5090 с правильными настройками
"""

import os

# Критически важно: установить переменные окружения ДО импорта torch
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ["TORCH_CUDA_ARCH_LIST"] = "8.6;8.9;9.0;12.0"  # Включаем sm_120 для RTX 5090
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
os.environ["TORCH_COMPILE_DISABLE"] = "1"  # RTX 5090 пока не поддерживает torch.compile

# Отключаем JIT компиляцию для новых архитектур
os.environ["PYTORCH_JIT"] = "0"

# Для совместимости с новыми GPU
os.environ["CUDA_FORCE_PTX_JIT"] = "1"

import torch


def check_gpu_compatibility():
    """Проверка совместимости GPU с установленным PyTorch"""
    print("🔍 Проверка совместимости GPU RTX 5090...")
    print(f"PyTorch версия: {torch.__version__}")
    print(f"CUDA доступна: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"CUDA версия в PyTorch: {torch.version.cuda}")
        print(f"cuDNN версия: {torch.backends.cudnn.version()}")
        print(f"Количество GPU: {torch.cuda.device_count()}")

        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print(f"\nGPU {i}: {props.name}")
            print(f"  Compute Capability: {props.major}.{props.minor}")
            print(f"  Память: {props.total_memory / 1024**3:.1f} GB")
            print(f"  Multiprocessors: {props.multi_processor_count}")

            # Проверка на RTX 5090
            if props.major == 12 and props.minor == 0:
                print("  ✅ Обнаружен RTX 5090 (sm_120)")
                print("  ⚠️  Используется режим совместимости")
    else:
        print("❌ CUDA недоступна")

        # Дополнительная диагностика
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,compute_cap",
                    "--format=csv",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print("\n📊 Информация от nvidia-smi:")
                print(result.stdout)
        except Exception as e:
            print(f"Не удалось запустить nvidia-smi: {e}")


def test_gpu_operations():
    """Тест базовых операций на GPU"""
    print("\n🧪 Тест операций на GPU...")

    try:
        # Попытка создать тензор на GPU
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        print(f"Используемое устройство: {device}")

        if device.type == "cuda":
            # Простой тест
            x = torch.zeros(100, 100, device=device)
            y = torch.ones(100, 100, device=device)
            z = x + y

            print("✅ Базовые операции работают")
            print(f"   Результат суммы: {z[0, 0].item()}")

            # Тест матричного умножения
            a = torch.randn(1000, 1000, device=device)
            b = torch.randn(1000, 1000, device=device)
            c = torch.matmul(a, b)

            print("✅ Матричное умножение работает")
            print(f"   Форма результата: {c.shape}")

            # Использование памяти
            print("\n💾 Использование памяти GPU:")
            print(f"   Выделено: {torch.cuda.memory_allocated(0) / 1024**2:.1f} MB")
            print(
                f"   Зарезервировано: {torch.cuda.memory_reserved(0) / 1024**2:.1f} MB"
            )

        else:
            print("⚠️  Работаем на CPU")

    except Exception as e:
        print(f"❌ Ошибка при тестировании GPU: {e}")
        import traceback

        traceback.print_exc()


def get_gpu_init_code():
    """Возвращает код для инициализации GPU в других модулях"""
    return """
# Инициализация GPU для RTX 5090
import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['TORCH_CUDA_ARCH_LIST'] = '8.6;8.9;9.0;12.0'
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
os.environ['TORCH_COMPILE_DISABLE'] = '1'
os.environ['PYTORCH_JIT'] = '0'
os.environ['CUDA_FORCE_PTX_JIT'] = '1'
"""


if __name__ == "__main__":
    check_gpu_compatibility()
    test_gpu_operations()

    print("\n📝 Код для инициализации GPU (добавьте в начало файлов):")
    print(get_gpu_init_code())
