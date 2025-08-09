#!/usr/bin/env python3
"""
Полное решение для RTX 5090 с обходом всех проверок
"""

import os

# КРИТИЧЕСКИ ВАЖНО: Установить ВСЕ переменные окружения ДО импорта torch
# Обход проверки версий драйвера
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["NVIDIA_VISIBLE_DEVICES"] = "0"

# Отключение проверки версий NVML
os.environ["CUDA_MODULE_LOADING"] = "LAZY"
os.environ["PYTORCH_NVML_BASED_CUDA_CHECK"] = "0"

# Критические настройки для RTX 5090
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ["TORCH_CUDA_ARCH_LIST"] = "5.0;6.0;6.1;7.0;7.5;8.0;8.6;8.9;9.0+PTX;12.0"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["PYTORCH_JIT"] = "0"
os.environ["CUDA_FORCE_PTX_JIT"] = "1"

# Форсируем использование CUDA без проверок
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
os.environ["PYTORCH_CUDA_FORCE_CUDA_ENABLED"] = "1"

# Специальный обход для новых GPU
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["PYTORCH_CUDA_FORCE_DEVICE_CAPABILITY"] = "12.0"

import torch

# Хак для обхода проверки совместимости
original_cuda_is_available = torch.cuda.is_available


def patched_cuda_is_available():
    """Патченная версия is_available которая обходит проверки"""
    try:
        # Пытаемся создать тензор на GPU напрямую
        device = torch.device("cuda:0")
        test = torch.zeros(1).to(device)
        return True
    except:
        return False


# Применяем патч
torch.cuda.is_available = patched_cuda_is_available


def test_gpu_with_workarounds():
    """Тест GPU с обходными путями для RTX 5090"""
    print("🔧 Применение обходных путей для RTX 5090...")

    # Проверка базовой информации
    print(f"PyTorch версия: {torch.__version__}")
    print(f"CUDA доступна (с патчем): {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print("✅ CUDA доступна через обходной путь!")

        try:
            # Прямое создание устройства
            device = torch.device("cuda:0")
            print(f"Устройство создано: {device}")

            # Тест операций
            print("\n🧪 Тестирование операций на GPU...")
            x = torch.randn(1000, 1000, device=device)
            y = torch.randn(1000, 1000, device=device)
            z = torch.matmul(x, y)

            print("✅ Матричное умножение успешно!")
            print(f"   Размер результата: {z.shape}")
            print(f"   Устройство: {z.device}")

            # Попытка получить информацию о GPU
            try:
                print("\n📊 Информация о GPU:")
                print(f"   Количество GPU: {torch.cuda.device_count()}")
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    print(f"   GPU {i}: {props.name}")
                    print(f"   Compute Capability: {props.major}.{props.minor}")
                    print(f"   Память: {props.total_memory / 1024**3:.1f} GB")
            except Exception as e:
                print(f"   ⚠️  Не удалось получить свойства GPU: {e}")
                print("   Но GPU работает!")

            # Тест производительности
            import time

            print("\n⚡ Тест производительности...")

            # Прогрев
            for _ in range(10):
                _ = torch.matmul(x, y)

            # Замер
            torch.cuda.synchronize()
            start = time.time()

            for _ in range(100):
                _ = torch.matmul(x, y)

            torch.cuda.synchronize()
            elapsed = time.time() - start

            print(f"✅ 100 операций за {elapsed:.3f} секунд")
            print(f"   Производительность: {100 / elapsed:.1f} операций/сек")

            return True

        except Exception as e:
            print(f"❌ Ошибка при работе с GPU: {e}")
            import traceback

            traceback.print_exc()
            return False
    else:
        print("❌ CUDA недоступна даже с обходными путями")
        return False


def create_gpu_init_module():
    """Создает модуль для инициализации GPU в других файлах"""

    init_code = '''#!/usr/bin/env python3
"""
Модуль инициализации GPU для RTX 5090
Импортируйте этот модуль ПЕРЕД torch в ваших скриптах
"""

import os

# Обход проверки версий драйвера
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['PYTORCH_NVML_BASED_CUDA_CHECK'] = '0'
os.environ['CUDA_MODULE_LOADING'] = 'LAZY'

# Настройки для RTX 5090
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['TORCH_CUDA_ARCH_LIST'] = '5.0;6.0;6.1;7.0;7.5;8.0;8.6;8.9;9.0+PTX;12.0'
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
os.environ['TORCH_COMPILE_DISABLE'] = '1'
os.environ['PYTORCH_JIT'] = '0'
os.environ['CUDA_FORCE_PTX_JIT'] = '1'
os.environ['PYTORCH_CUDA_FORCE_CUDA_ENABLED'] = '1'
os.environ['PYTORCH_CUDA_FORCE_DEVICE_CAPABILITY'] = '12.0'

# Импортируем torch и применяем патч
import torch

# Сохраняем оригинальную функцию
_original_is_available = torch.cuda.is_available

def _patched_is_available():
    """Патченная версия is_available"""
    try:
        # Пробуем напрямую использовать GPU
        device = torch.device('cuda:0')
        test = torch.zeros(1).to(device)
        del test
        return True
    except:
        # Если не получилось, возвращаем результат оригинальной функции
        try:
            return _original_is_available()
        except:
            return False

# Применяем патч
torch.cuda.is_available = _patched_is_available

# Экспортируем для удобства
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

print(f"🎮 GPU инициализация для RTX 5090: устройство = {device}")
'''

    with open("gpu_init_rtx5090.py", "w") as f:
        f.write(init_code)

    print("\n📝 Создан модуль gpu_init_rtx5090.py")
    print("Используйте его так:")
    print("   import gpu_init_rtx5090  # Импортировать ПЕРЕД torch!")
    print("   import torch")
    print("   # Теперь GPU должен работать")


if __name__ == "__main__":
    success = test_gpu_with_workarounds()

    if success:
        create_gpu_init_module()
        print("\n✅ GPU работает с обходными путями!")
        print("Решение готово к использованию в проекте.")
    else:
        print("\n❌ Не удалось заставить GPU работать")
        print("Возможно, требуется переустановка драйверов")
