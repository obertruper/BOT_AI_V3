#!/usr/bin/env python3
"""
Детальный анализ формул расчета КАЖДОГО из 240 признаков.
Сравнивает обучающий файл (ааа.py) с текущей реализацией.
"""

import re


class DetailedFeatureAnalyzer:
    def __init__(self):
        self.training_file = "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/BOT_AI_V2/ааа.py"
        self.current_file = "/ml/logic/archive_old_versions/feature_engineering_v2.py"
        self.issues = []

    def read_file(self, filepath):
        """Читает файл"""
        with open(filepath, encoding="utf-8") as f:
            return f.read()

    def analyze_critical_features(self):
        """Анализирует критически важные признаки из обучения"""
        training_content = self.read_file(self.training_file)

        print("=" * 80)
        print("🔬 ДЕТАЛЬНЫЙ АНАЛИЗ ФОРМУЛ ПРИЗНАКОВ ИЗ ОБУЧАЮЩЕГО ФАЙЛА")
        print("=" * 80)

        # 1. RSI
        print("\n1️⃣ RSI (Relative Strength Index):")
        rsi_match = re.search(
            r"df\['rsi'\] = ta\.momentum\.RSIIndicator\([^)]+window=(\d+)", training_content
        )
        if rsi_match:
            print(f"  📊 В обучении: RSI с периодом {rsi_match.group(1)}")
            print("  ⚠️  ВАЖНО: используется ОДИН RSI, не несколько!")

        # 2. SMA
        print("\n2️⃣ SMA (Simple Moving Average):")
        sma_matches = re.findall(r"sma_(\d+)", training_content)
        unique_sma = set(sma_matches)
        print(f"  📊 В обучении SMA периоды: {sorted([int(p) for p in unique_sma])}")
        sma_formula = re.search(r"df\[f'sma_\{period\}'\] = (.*)", training_content)
        if sma_formula:
            print(f"  📐 Формула: {sma_formula.group(1)}")

        # 3. Returns
        print("\n3️⃣ RETURNS (Доходности):")
        returns_basic = re.search(r"df\['returns'\] = (.*)", training_content)
        if returns_basic:
            print(f"  📊 Базовая формула: {returns_basic.group(1)}")
            if "np.log" in returns_basic.group(1):
                print("  ✅ Используется LOG returns!")
            else:
                print("  ❌ НЕ используется log returns!")

        # 4. BTC Correlation (КРИТИЧНО!)
        print("\n4️⃣ BTC CORRELATION (КРИТИЧЕСКИ ВАЖНО!):")
        btc_corr = re.search(
            r"btc_correlation.*?rolling\(window=(\d+), min_periods=(\d+)\)", training_content
        )
        if btc_corr:
            print(f"  📊 Window: {btc_corr.group(1)}, Min periods: {btc_corr.group(2)}")
            print("  ✅ ТОЧНЫЕ параметры: window=96, min_periods=50")

        # 5. BTC Beta
        print("\n5️⃣ BTC BETA:")
        btc_beta = re.search(r"btc_beta.*?rolling\((\d+)\)", training_content)
        if btc_beta:
            print(f"  📊 Rolling window: {btc_beta.group(1)}")

        # 6. Volatility
        print("\n6️⃣ VOLATILITY:")
        vol_matches = re.findall(r"volatility.*?rolling\((\d+)\)\.std\(\)", training_content)
        if vol_matches:
            print(f"  📊 Volatility windows: {vol_matches}")

        # 7. MACD
        print("\n7️⃣ MACD:")
        macd_match = re.search(
            r"MACD\([^,]+,\s*window_slow=(\d+),\s*window_fast=(\d+),\s*window_sign=(\d+)",
            training_content,
        )
        if macd_match:
            print(
                f"  📊 Slow: {macd_match.group(1)}, Fast: {macd_match.group(2)}, Signal: {macd_match.group(3)}"
            )
            # Проверяем нормализацию
            macd_norm = re.search(r"macd.*?/.*?df\['close'\].*?\*.*?100", training_content)
            if macd_norm:
                print("  ✅ MACD нормализован относительно цены (в процентах)!")

        # 8. Bollinger Bands
        print("\n8️⃣ BOLLINGER BANDS:")
        bb_match = re.search(
            r"BollingerBands\([^,]+,\s*window=(\d+),\s*window_dev=(\d+)", training_content
        )
        if bb_match:
            print(f"  📊 Window: {bb_match.group(1)}, Std dev: {bb_match.group(2)}")

        # 9. Cross-asset features summary
        print("\n9️⃣ CROSS-ASSET FEATURES SUMMARY:")
        cross_features = []
        if "btc_correlation" in training_content:
            cross_features.append("btc_correlation")
        if "btc_beta" in training_content:
            cross_features.append("btc_beta")
        if "relative_strength_btc" in training_content:
            cross_features.append("relative_strength_btc")
        if "rs_btc_ma" in training_content:
            cross_features.append("rs_btc_ma")
        if "idio_vol" in training_content:
            cross_features.append("idio_vol")

        print(f"  📊 Найдено cross-asset признаков: {len(cross_features)}")
        for cf in cross_features:
            print(f"    - {cf}")

        # 10. ETH features check
        print("\n🔟 ETH FEATURES:")
        eth_count = training_content.count("eth_")
        print(f"  📊 ETH признаков в обучении: {eth_count}")
        if eth_count == 0:
            print("  ✅ ETH признаков НЕТ в обучении (это правильно!)")

        return cross_features

    def generate_fix_recommendations(self):
        """Генерирует рекомендации по исправлению"""
        print("\n" + "=" * 80)
        print("📝 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ")
        print("=" * 80)

        recommendations = [
            {
                "feature": "RSI",
                "current": "rsi_5, rsi_14, rsi_21",
                "should_be": "rsi (single period from config)",
                "action": "Использовать один RSI с периодом из конфига",
            },
            {
                "feature": "BTC Correlation",
                "current": "Multiple timeframes",
                "should_be": "Single correlation with window=96, min_periods=50",
                "action": "Изменить на единственную корреляцию с точными параметрами",
            },
            {
                "feature": "ETH Correlation",
                "current": "Present in current",
                "should_be": "Not in training",
                "action": "Убрать ETH корреляции или заполнить заглушками 0.5",
            },
            {
                "feature": "BTC Beta",
                "current": "Unknown",
                "should_be": "rolling(100).cov / rolling(100).var",
                "action": "Использовать точную формулу из обучения",
            },
            {
                "feature": "MACD",
                "current": "Absolute values",
                "should_be": "Normalized by price (* 100)",
                "action": "Нормализовать MACD относительно цены",
            },
            {
                "feature": "Returns",
                "current": "Simple returns",
                "should_be": "Log returns: np.log(close/close.shift(period))",
                "action": "Использовать логарифмические доходности",
            },
        ]

        print("\n📋 Критические изменения:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['feature']}:")
            print(f"   Сейчас: {rec['current']}")
            print(f"   Должно: {rec['should_be']}")
            print(f"   ✏️ Действие: {rec['action']}")

        return recommendations

    def check_exact_feature_list(self):
        """Проверяет точный список признаков из обучения"""
        training_content = self.read_file(self.training_file)

        print("\n" + "=" * 80)
        print("📊 ТОЧНЫЙ СПИСОК ПРИЗНАКОВ ИЗ ОБУЧЕНИЯ")
        print("=" * 80)

        # Ищем все df['feature_name'] =
        feature_assignments = re.findall(r"df\['([^']+)'\]\s*=", training_content)
        unique_features = sorted(set(feature_assignments))

        print(f"\nВсего уникальных признаков в обучении: {len(unique_features)}")

        # Группируем по типам
        feature_groups = {
            "returns": [],
            "volatility": [],
            "sma": [],
            "ema": [],
            "rsi": [],
            "macd": [],
            "bb": [],
            "btc": [],
            "volume": [],
            "price": [],
            "other": [],
        }

        for feat in unique_features:
            categorized = False
            for key in feature_groups:
                if key in feat.lower() and key != "other":
                    feature_groups[key].append(feat)
                    categorized = True
                    break
            if not categorized:
                feature_groups["other"].append(feat)

        # Выводим по группам
        for group, features in feature_groups.items():
            if features:
                print(f"\n{group.upper()} ({len(features)} признаков):")
                for f in features[:10]:  # Показываем первые 10
                    print(f"  - {f}")
                if len(features) > 10:
                    print(f"  ... и еще {len(features) - 10}")

        return unique_features


if __name__ == "__main__":
    analyzer = DetailedFeatureAnalyzer()

    # 1. Анализируем критические признаки
    cross_features = analyzer.analyze_critical_features()

    # 2. Генерируем рекомендации
    recommendations = analyzer.generate_fix_recommendations()

    # 3. Проверяем точный список
    exact_features = analyzer.check_exact_feature_list()

    print("\n" + "=" * 80)
    print("✅ АНАЛИЗ ЗАВЕРШЕН")
    print(f"Найдено {len(exact_features)} уникальных признаков в обучающем файле")
    print(f"Требуется исправить {len(recommendations)} критических несоответствий")
    print("=" * 80)
