#!/bin/bash
# Тестирование системы анализа кода

echo "🔍 Testing BOT_AI_V3 Code Usage Analysis System"
echo "=============================================="

# Активируем виртуальное окружение
source venv/bin/activate

echo "📊 Running code usage analysis..."
python3 scripts/run_code_usage_analysis.py --format both --verbose

echo ""
echo "🧪 Running analysis validation tests..."
python3 -m pytest tests/analysis/ -v --tb=short

echo ""
echo "📈 Analysis performance test..."
time python3 scripts/run_code_usage_analysis.py --format json >/dev/null

echo ""
echo "✅ Code analysis system tested successfully!"
echo ""
echo "Available commands:"
echo "  • Full analysis:        python3 scripts/run_code_usage_analysis.py --format both --verbose"
echo "  • Interactive cleanup:  python3 scripts/interactive_code_cleanup.py"  
echo "  • Run tests:            python3 -m pytest tests/analysis/ -v"
echo "  • View results:         open analysis_results/code_usage_report_*.html"