# \!/usr/bin/env python3
"""
Тест GPU с правильными настройками для CUDA 12.8
"""

import os
import sys

# Устанавливаем переменные окружения ДО импорта torch
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ["TORCH_CUDA_ARCH_LIST"] = (
    "8.6;8.9;9.0;12.0"  # Ampere, Ada, Hopper, RTX 5090 (sm_120)
)
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
os.environ["TORCH_COMPILE_DISABLE"] = "1"  # RTX 5090 пока не поддерживает torch.compile

import torch

print("🔍 Диагностика GPU/CUDA:")
print(f"PyTorch версия: {torch.__version__}")
print(f"CUDA доступна: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA версия: {torch.version.cuda}")
    print(f"cuDNN версия: {torch.backends.cudnn.version()}")
    print(f"Количество GPU: {torch.cuda.device_count()}")

    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f"\nGPU {i}: {props.name}")
        print(f"  Compute Capability: {props.major}.{props.minor}")
        print(f"  Память: {props.total_memory / 1024**3:.1f} GB")
        print(f"  Multiprocessors: {props.multi_processor_count}")
else:
    print("\n⚠️ CUDA недоступна через torch.cuda.is_available()")

# Тестируем прямое создание тензора
print("\n🧪 Тест создания GPU тензора:")
try:
    # Принудительно на cuda:0
    device = torch.device("cuda:0")
    tensor = torch.zeros(1, 1, device=device)
    print(f"✅ Тензор создан на {device}")
    print(f"   Устройство тензора: {tensor.device}")
except Exception as e:
    print(f"❌ Ошибка: {type(e).__name__}: {e}")

# Информация о системе
print("\n📊 Системная информация:")
print(f"Python: {sys.version}")
print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'не установлен')}")
print(f"CUDA_HOME: {os.environ.get('CUDA_HOME', 'не установлен')}")
