#!/bin/bash
# Критический скрипт для RTX 5090 - ТОЧНАЯ КОПИЯ из рабочего проекта
echo "🚀 Установка PyTorch Nightly для RTX 5090 (sm_120)"

# Активация виртуального окружения
source venv/bin/activate

# Удаление текущей версии PyTorch
pip uninstall -y torch torchvision torchaudio

# Очистка pip cache
pip cache purge

# Установка PyTorch Nightly с поддержкой CUDA 12.8 и sm_120
python -m pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

echo "✅ PyTorch Nightly установлен для RTX 5090"
