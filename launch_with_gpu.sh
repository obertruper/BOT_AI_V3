#!/bin/bash
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
