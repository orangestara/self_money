"""
核心模块

包含策略框架的核心组件
"""

from .config import load_config, get_etf_list, get_backtest_params, get_strategies_config
from .backtest_engine import BacktestEngine, SignalOnlyBacktest
from .signal_generator import SignalGenerator, Signal
from .factors import FactorCalculator
from .risk_manager import RiskManager
from .utils import format_currency, format_percentage, score_based_weighting
from .base_strategy import BaseStrategy, SignalOnlyStrategy

__all__ = [
    "load_config",
    "get_etf_list",
    "get_backtest_params",
    "get_strategies_config",
    "BacktestEngine",
    "SignalOnlyBacktest",
    "SignalGenerator",
    "Signal",
    "FactorCalculator",
    "RiskManager",
    "format_currency",
    "format_percentage",
    "score_based_weighting",
    "BaseStrategy",
    "SignalOnlyStrategy",
]
