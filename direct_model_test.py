#!/usr/bin/env python3

# Отключаем CUDA для теста
import os
import time
from pathlib import Path

import torch

os.environ["CUDA_VISIBLE_DEVICES"] = ""

from ml.logic.patchtst_model import create_unified_model

print("Создаем модель...")
model_config = {
    "model": {
        "input_size": 240,
        "output_size": 20,
        "context_window": 96,
        "patch_len": 16,
        "stride": 8,
        "d_model": 256,
        "n_heads": 4,
        "e_layers": 3,
        "d_ff": 512,
        "dropout": 0.1,
        "temperature_scaling": True,
        "temperature": 2.0,
    }
}

model = create_unified_model(model_config)
print("Модель создана")

# Загружаем веса
model_path = Path("models/saved/best_model_20250728_215703.pth")
print(f"Загружаем веса из {model_path}...")
checkpoint = torch.load(model_path, map_location="cpu")
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()
print("Веса загружены")

# Тестовые данные
print("Создаем тестовые данные...")
test_data = torch.randn(1, 96, 240)

# Предсказание
print("Делаем предсказание...")
start_time = time.time()
with torch.no_grad():
    outputs = model(test_data)
elapsed = time.time() - start_time

print(f"Предсказание выполнено за {elapsed:.3f} сек")
outputs_np = outputs.numpy()[0]
print(f"Форма выходов: {outputs_np.shape}")
print(f"Направления (4-8): {outputs_np[4:8]}")

# Проверяем разнообразие
unique_vals = len(set([round(v, 1) for v in outputs_np[4:8]]))
print(f"Уникальных направлений: {unique_vals} из 4")

if unique_vals == 1:
    print("⚠️ Все направления одинаковые!")
else:
    print("✅ Направления разнообразные")

print("Тест завершен")
