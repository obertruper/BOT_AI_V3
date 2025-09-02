#!/usr/bin/env python3
"""Диагностика множественных процессов системы"""

import psutil
import os
from collections import defaultdict
from pathlib import Path

def analyze_processes():
    """Анализ всех процессов связанных с BOT_AI_V3"""
    
    bot_processes = []
    process_groups = defaultdict(list)
    
    # Поиск всех python процессов
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid', 'status']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline', [])
                cmdline_str = ' '.join(cmdline) if cmdline else ''
                
                # Проверяем связь с BOT_AI_V3
                if 'BOT_AI_V3' in cmdline_str:
                    parent_pid = proc.info.get('ppid', 0)
                    
                    # Определяем тип процесса
                    process_type = "Unknown"
                    if 'unified_launcher' in cmdline_str:
                        process_type = "Main Launcher"
                    elif 'main.py' in cmdline_str:
                        process_type = "Trading Engine"
                    elif 'uvicorn' in cmdline_str:
                        process_type = "API Server"
                    elif 'web/api' in cmdline_str:
                        process_type = "Web API"
                    elif 'multiprocessing' in cmdline_str:
                        process_type = "Worker Process"
                    elif 'asyncio' in cmdline_str:
                        process_type = "Async Task"
                    elif any(x in cmdline_str for x in ['tensorflow', 'torch', 'ml']):
                        process_type = "ML Process"
                    
                    process_info = {
                        'pid': proc.info['pid'],
                        'ppid': parent_pid,
                        'type': process_type,
                        'status': proc.info.get('status', 'unknown'),
                        'cmdline': cmdline_str[:100] + ('...' if len(cmdline_str) > 100 else ''),
                        'memory_mb': proc.memory_info().rss / 1024 / 1024,
                        'cpu_percent': proc.cpu_percent(interval=0.1)
                    }
                    
                    bot_processes.append(process_info)
                    process_groups[process_type].append(process_info)
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return bot_processes, process_groups

def print_analysis():
    """Вывод анализа процессов"""
    
    processes, groups = analyze_processes()
    
    print("=" * 80)
    print("BOT_AI_V3 PROCESS ANALYSIS")
    print("=" * 80)
    
    if not processes:
        print("✅ Нет запущенных процессов BOT_AI_V3")
        return
    
    print(f"\n📊 Общая статистика:")
    print(f"   Всего процессов: {len(processes)}")
    print(f"   Типов процессов: {len(groups)}")
    
    total_memory = sum(p['memory_mb'] for p in processes)
    total_cpu = sum(p['cpu_percent'] for p in processes)
    print(f"   Общая память: {total_memory:.1f} MB")
    print(f"   Общая CPU: {total_cpu:.1f}%")
    
    # Анализ по группам
    print(f"\n📋 Процессы по типам:")
    for proc_type, procs in groups.items():
        print(f"\n   {proc_type} ({len(procs)} процессов):")
        for proc in procs[:5]:  # Показываем первые 5
            print(f"      PID {proc['pid']} (Parent: {proc['ppid']})")
            print(f"         Память: {proc['memory_mb']:.1f} MB, CPU: {proc['cpu_percent']:.1f}%")
            print(f"         Статус: {proc['status']}")
            
        if len(procs) > 5:
            print(f"      ... и еще {len(procs) - 5} процессов")
    
    # Поиск проблем
    print(f"\n⚠️ Потенциальные проблемы:")
    
    # Проверка зомби процессов
    zombies = [p for p in processes if p['status'] == 'zombie']
    if zombies:
        print(f"   ❌ Найдено {len(zombies)} zombie процессов!")
    
    # Проверка дубликатов
    duplicates = [t for t, procs in groups.items() if len(procs) > 5]
    if duplicates:
        print(f"   ⚠️ Возможное дублирование процессов: {', '.join(duplicates)}")
    
    # Проверка высокого потребления памяти
    high_mem = [p for p in processes if p['memory_mb'] > 500]
    if high_mem:
        print(f"   ⚠️ {len(high_mem)} процессов используют > 500 MB памяти")
    
    # Рекомендации
    print(f"\n💡 Рекомендации:")
    if len(processes) > 20:
        print("   1. Слишком много процессов! Проверьте настройку parallel_workers")
        print("   2. Рекомендуется уменьшить parallel_workers в config/config.yaml")
    
    if 'Worker Process' in groups and len(groups['Worker Process']) > 4:
        print("   3. Много воркеров. Установите parallel_workers: 2 для экономии ресурсов")
    
    if zombies:
        print("   4. Перезапустите систему для очистки zombie процессов")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    print_analysis()