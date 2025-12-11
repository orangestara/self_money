"""
量化策略框架

提供统一的量化交易策略开发和回测框架
支持多种策略、回测引擎、信号生成和参数优化
"""

__version__ = "2.0.0"

# 核心模块
from .core.config import load_config, get_etf_list, get_backtest_params, get_benchmark_symbol
from .core.backtest_engine import BacktestEngine, SignalOnlyBacktest
from .core.signal_generator import SignalGenerator, Signal
from .core.factors import FactorCalculator
from .core.risk_manager import RiskManager
from .core.utils import format_currency, format_percentage, score_based_weighting

# 策略基类
from .core.base_strategy import BaseStrategy, SignalOnlyStrategy

# 管理模块
from .managers.strategy_manager import StrategyManager
from .managers.strategy_factory import StrategyFactory, StrategyLoader
from .managers.parameter_search import ParameterSearch, GridSearch, RandomSearch, BayesianOptimization, create_parameter_search
from .managers.strategy_factory import (
    create_strategy_manager,
    create_backtest_engine,
    create_signal_generator
)

# 策略实现
from .strategies.etf_rotation import ETFRotationStrategy
from .strategies.grid_trading import GridTradingStrategy

__all__ = [
    # 版本信息
    "__version__",

    # 核心模块
    "load_config",
    "get_etf_list",
    "get_backtest_params",
    "get_benchmark_symbol",
    "BacktestEngine",
    "SignalOnlyBacktest",
    "SignalGenerator",
    "Signal",
    "FactorCalculator",
    "RiskManager",
    "format_currency",
    "format_percentage",
    "score_based_weighting",

    # 策略基类
    "BaseStrategy",
    "SignalOnlyStrategy",

    # 管理模块
    "StrategyManager",
    "StrategyFactory",
    "StrategyLoader",
    "ParameterSearch",
    "GridSearch",
    "RandomSearch",
    "BayesianOptimization",

    # 策略实现
    "ETFRotationStrategy",
    "GridTradingStrategy",

    # 便捷函数
    "create_strategy_manager",
    "create_backtest_engine",
    "create_signal_generator",
    "create_parameter_search",
]
