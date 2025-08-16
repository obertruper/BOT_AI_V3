#!/usr/bin/env python3
"""
Comprehensive ML Diversity Test - Final Verification
Tests that the ML system generates diverse signals after the fix
"""

import asyncio
import logging
import sys

sys.path.insert(0, "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

import torch

from core.config.config_manager import ConfigManager
from ml.ml_manager import MLManager

# Setup logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)


async def test_ml_diversity():
    """Test ML signal diversity with multiple random inputs"""

    print("🧪 COMPREHENSIVE ML DIVERSITY TEST")
    print("=" * 50)

    # Initialize ML Manager
    config_manager = ConfigManager()
    system_config = config_manager.get_system_config()

    ml_manager = MLManager(system_config)
    await ml_manager.initialize()

    print(f"✅ ML Manager initialized on device: {ml_manager.device}")

    # Test parameters
    num_tests = 25
    signal_counts = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}
    confidence_scores = []

    print(f"\n🔄 Running {num_tests} diversity tests...")

    for i in range(num_tests):
        try:
            # Create different random inputs to simulate various market conditions
            # Add some variation in the input to trigger different model behaviors
            test_input = torch.randn(1, 96, 240).cuda()

            # Add some realistic scaling
            test_input = test_input * 0.1 + torch.randn(1, 96, 240).cuda() * 0.05

            # Get prediction
            prediction = await ml_manager.predict(test_input)

            signal_type = prediction.get("signal_type", "UNKNOWN")
            confidence = prediction.get("confidence", 0)

            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
            confidence_scores.append(confidence)

            # Show first 10 results for verification
            if i < 10:
                print(f"   Test {i + 1:2}: {signal_type:7} (confidence: {confidence:.3f})")

        except Exception as e:
            print(f"   Test {i + 1} failed: {e}")

    # Calculate statistics
    print(f"\n📊 FINAL RESULTS FROM {num_tests} TESTS:")
    print("-" * 40)

    total_valid = sum(signal_counts.values())
    for signal_type, count in signal_counts.items():
        if total_valid > 0:
            percentage = (count / total_valid) * 100
            print(f"   {signal_type:7}: {count:2}/{total_valid} ({percentage:5.1f}%)")
        else:
            print(f"   {signal_type:7}: {count:2}/0 (0.0%)")

    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        max_confidence = max(confidence_scores)
        min_confidence = min(confidence_scores)
        print("\n📈 CONFIDENCE STATISTICS:")
        print(f"   Average: {avg_confidence:.3f}")
        print(f"   Range:   {min_confidence:.3f} - {max_confidence:.3f}")

    # Final assessment
    unique_signals = len([k for k, v in signal_counts.items() if v > 0])
    print("\n🎯 DIVERSITY ASSESSMENT:")
    print(f"   Unique signal types: {unique_signals}/3")

    if unique_signals >= 2:
        print("   ✅ SUCCESS: ML system generates diverse signals!")
        print("   ✅ NEUTRAL signal monopoly has been RESOLVED")

        # Check if we have reasonable distribution
        if signal_counts.get("NEUTRAL", 0) < total_valid * 0.8:  # Less than 80% neutral
            print("   ✅ EXCELLENT: Good signal diversity achieved")
        else:
            print("   ⚠️  WARNING: Still high NEUTRAL percentage, but system is working")
    else:
        print("   ❌ ISSUE: Still generating only one signal type")
        return False

    print("\n🚀 ML SYSTEM STATUS: OPERATIONAL AND DIVERSE")
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_ml_diversity())
        if success:
            print("\n" + "=" * 50)
            print("🎉 ML NEUTRAL SIGNALS FIX: VERIFIED SUCCESSFUL")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("❌ ML SYSTEM STILL NEEDS ATTENTION")
            print("=" * 50)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
