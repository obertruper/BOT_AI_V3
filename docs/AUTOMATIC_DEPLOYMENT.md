# Настройка автоматического деплоя

## Текущий статус системы

### ✅ Что уже работает автоматически

1. **CI/CD Pipeline** - при каждом push в main:
   - Запускаются все тесты
   - Проверка кода (linting, formatting)
   - Проверка на секреты
   - Сборка Docker образа

2. **Pre-commit hooks** - перед каждым коммитом:
   - Black (форматирование)
   - Ruff (линтер)
   - MyPy (типы)
   - Bandit (безопасность)
   - Detect-secrets

3. **Claude Code Review** - для Pull Requests:
   - Автоматический AI review кода
   - Ответы на @claude в комментариях

### ❌ Что НЕ работает (требует настройки)

**АВТОМАТИЧЕСКИЙ ДЕПЛОЙ НА СЕРВЕР**

## Как настроить автоматический деплой

### Вариант 1: GitHub Actions Deploy (рекомендуется)

1. Откройте GitHub репозиторий: <https://github.com/obertruper/BOT_AI_V3>

2. Перейдите в Settings → Secrets and variables → Actions

3. Добавьте следующие секреты:

```
STAGING_HOST     = IP адрес вашего сервера
STAGING_USER     = имя пользователя SSH
STAGING_SSH_KEY  = приватный SSH ключ (весь текст)
STAGING_PORT     = SSH порт (обычно 22)
```

4. Создайте файл `.github/workflows/auto-deploy.yml`:

```yaml
name: Auto Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          port: ${{ secrets.STAGING_PORT }}
          script: |
            cd /opt/bot_ai_v3
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            alembic upgrade head
            sudo systemctl restart bot-ai-v3
            echo "✅ Deployment complete!"
```

### Вариант 2: Webhook деплой

1. На сервере создайте webhook listener:

```bash
# /opt/bot_ai_v3/webhook_deploy.py
import subprocess
from flask import Flask, request

app = Flask(__name__)

@app.route('/deploy', methods=['POST'])
def deploy():
    if request.json.get('ref') == 'refs/heads/main':
        subprocess.run(['/opt/bot_ai_v3/deploy.sh'])
        return 'Deployed', 200
    return 'Skipped', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999)
```

2. В GitHub Settings → Webhooks добавьте:
   - URL: <http://your-server:9999/deploy>
   - Content type: application/json
   - Events: Push events

### Вариант 3: Использование GitHub Self-hosted Runner

1. На сервере установите runner:

```bash
cd /opt
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf actions-runner-linux-x64-2.311.0.tar.gz
./config.sh --url https://github.com/obertruper/BOT_AI_V3 --token YOUR_TOKEN
sudo ./svc.sh install
sudo ./svc.sh start
```

2. В workflow используйте:

```yaml
runs-on: self-hosted
```

## Проверка автоматического деплоя

После настройки:

```bash
# Сделайте тестовый коммит
git commit -m "test: Auto deploy" --allow-empty
git push origin main

# Проверьте в GitHub Actions
# Вкладка Actions → последний workflow должен показать Deploy

# На сервере проверьте
ssh user@server
journalctl -u bot-ai-v3 -n 50
```

## Безопасность

⚠️ ВАЖНО:

- Никогда не коммитьте SSH ключи в репозиторий
- Используйте только GitHub Secrets
- Ограничьте права SSH пользователя
- Используйте отдельный deploy ключ

## Откат при проблемах

```bash
# На сервере
cd /opt/bot_ai_v3
git log --oneline -5  # найдите стабильный коммит
git checkout <commit-hash>
sudo systemctl restart bot-ai-v3
```

## Текущая схема работы

```
[Разработчик]
    ↓ git push
[GitHub]
    ↓ автоматически
[CI/CD Tests] ✅ РАБОТАЕТ
    ↓ если тесты прошли
[Deploy to Server] ❌ ТРЕБУЕТ НАСТРОЙКИ СЕКРЕТОВ
    ↓
[Production]
```

## Контакты для помощи

Если нужна помощь с настройкой:

1. Проверьте логи: GitHub Actions → ваш workflow → логи
2. Документация: <https://docs.github.com/en/actions>
3. SSH деплой: <https://github.com/appleboy/ssh-action>
