"""
Indicator Strategy - ">@3>20O AB@0B538O =0 >A=>25 B5E=8G5A:8E 8=48:0B>@>2
5@A8O 2.0 A <0B@8F59 A:>@8=30 8 AI->?B8<870F859
"""

from .core import IndicatorStrategy, SignalGenerator
from .scoring import DynamicWeightCalculator, ScoringEngine, WeightManager

# -:A?>@B >A=>2=>3> :;0AA0 AB@0B5388
__all__ = [
    "DynamicWeightCalculator",
    "IndicatorStrategy",
    "ScoringEngine",
    "SignalGenerator",
    "WeightManager",
]

# 5B040==K5 AB@0B5388
__version__ = "2.0.0"
__author__ = "BOT Trading Team"
__description__ = "><?;5:A=0O AB@0B538O =0 >A=>25 B5E=8G5A:8E 8=48:0B>@>2 4;O ?>78F89 1-7 4=59"
