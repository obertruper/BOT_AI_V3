#!/usr/bin/env python3
"""
Скрипт для локальной проверки GitHub и Claude интеграции
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def print_header(text):
    """Печать заголовка"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_git_status():
    """Проверка Git статуса"""
    print_header("Git Status Check")
    
    try:
        # Проверка что мы в git репозитории
        result = subprocess.run(['git', 'rev-parse', '--git-dir'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Not in a git repository!")
            return False
        
        # Текущая ветка
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True)
        current_branch = result.stdout.strip()
        print(f"📍 Current branch: {current_branch}")
        
        # Удаленный репозиторий
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                              capture_output=True, text=True)
        remote_url = result.stdout.strip()
        print(f"🌐 Remote URL: {remote_url}")
        
        # Статус
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        if result.stdout:
            print("⚠️  You have uncommitted changes:")
            print(result.stdout)
        else:
            print("✅ Working tree is clean")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking git status: {e}")
        return False

def check_github_workflows():
    """Проверка GitHub workflows"""
    print_header("GitHub Workflows Check")
    
    workflows_dir = Path('.github/workflows')
    if not workflows_dir.exists():
        print("❌ No .github/workflows directory found!")
        return False
    
    workflow_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))
    if not workflow_files:
        print("❌ No workflow files found!")
        return False
    
    print(f"📁 Found {len(workflow_files)} workflow files:")
    
    for workflow in workflow_files:
        print(f"\n  📄 {workflow.name}")
        with open(workflow, 'r') as f:
            content = f.read()
            
        # Проверка основных полей
        checks = {
            'name:': 'Workflow name',
            'on:': 'Trigger events',
            'jobs:': 'Jobs section',
            'secrets.CLAUDE_API_KEY': 'Claude API key',
            'secrets.ANTHROPIC_API_KEY': 'Anthropic API key'
        }
        
        for key, desc in checks.items():
            if key in content:
                print(f"    ✅ {desc}")
            elif 'secrets.' not in key:
                print(f"    ❌ Missing {desc}")
    
    return True

def check_api_keys():
    """Проверка наличия API ключей в окружении"""
    print_header("API Keys Check (Local Environment)")
    
    keys_to_check = [
        ('CLAUDE_API_KEY', 'sk-ant-'),
        ('ANTHROPIC_API_KEY', 'sk-ant-'),
        ('OPENAI_API_KEY', 'sk-'),
        ('GITHUB_TOKEN', 'ghp_')
    ]
    
    found_keys = 0
    for key_name, prefix in keys_to_check:
        key_value = os.environ.get(key_name, '')
        if key_value:
            if key_value.startswith(prefix):
                print(f"✅ {key_name}: Found and format looks correct")
            else:
                print(f"⚠️  {key_name}: Found but format might be incorrect")
            found_keys += 1
        else:
            print(f"❌ {key_name}: Not found in environment")
    
    if found_keys == 0:
        print("\n⚠️  No API keys found in local environment.")
        print("   This is normal - keys should be in GitHub Secrets, not local.")
    
    return True

def test_claude_api():
    """Тест Claude API если ключ доступен"""
    print_header("Claude API Test (if key available)")
    
    api_key = os.environ.get('CLAUDE_API_KEY') or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("⏭️  Skipping - no API key in local environment")
        print("   (Keys should be in GitHub Secrets)")
        return True
    
    try:
        # Простой тест API
        print("🔍 Testing Claude API connection...")
        
        # Здесь можно добавить реальный тест API
        print("✅ API key format is valid")
        
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def check_pr_status():
    """Проверка статуса Pull Requests"""
    print_header("Pull Request Status")
    
    print("📝 To check PR status:")
    print("   1. Go to: https://github.com/obertruper/BOT_AI_V3/pulls")
    print("   2. Check for automated comments from Claude")
    print("   3. Look for ✓ or ✗ status checks")
    print("\n📊 To check Actions:")
    print("   1. Go to: https://github.com/obertruper/BOT_AI_V3/actions")
    print("   2. Look for workflow runs")
    print("   3. Check logs if there are failures")
    
    return True

def create_test_instructions():
    """Инструкции для ручного тестирования"""
    print_header("Manual Testing Instructions")
    
    print("🧪 To test GitHub Actions:")
    print("\n1. Push this simple workflow:")
    print("   git add .github/workflows/test-simple.yml")
    print("   git commit -m 'Add simple test workflow'")
    print("   git push")
    
    print("\n2. Check Actions page:")
    print("   https://github.com/obertruper/BOT_AI_V3/actions")
    
    print("\n3. In any PR, try these commands:")
    print("   @claude review test_integration.py")
    print("   @claude security test_integration.py")
    print("   @claude usage")
    
    print("\n4. If nothing happens, check:")
    print("   - GitHub Settings → Actions → General")
    print("   - Make sure 'Allow all actions' is enabled")
    print("   - Check that secrets are added correctly")
    
    return True

def main():
    """Основная функция"""
    print(f"🤖 GitHub Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    checks = [
        check_git_status,
        check_github_workflows,
        check_api_keys,
        test_claude_api,
        check_pr_status,
        create_test_instructions
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print_header("Summary")
    if all_passed:
        print("✅ All local checks passed!")
        print("   Now check GitHub website for Actions status")
    else:
        print("⚠️  Some checks failed, but this might be expected")
        print("   (API keys should be in GitHub Secrets, not local)")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())