#!/bin/bash
echo "Остановка Metabase..."
docker-compose -f docker-compose.metabase.yml down
echo "✅ Metabase остановлен"
