"""
管理模块

包含策略管理、工厂和参数优化等功能
"""

from .strategy_manager import StrategyManager
from .strategy_factory import StrategyFactory, StrategyLoader, create_strategy_manager, create_backtest_engine, create_signal_generator
from .parameter_search import ParameterSearch, GridSearch, RandomSearch, BayesianOptimization, create_parameter_search

__all__ = [
    "StrategyManager",
    "StrategyFactory",
    "StrategyLoader",
    "create_strategy_manager",
    "create_backtest_engine",
    "create_signal_generator",
    "ParameterSearch",
    "GridSearch",
    "RandomSearch",
    "BayesianOptimization",
    "create_parameter_search",
]
