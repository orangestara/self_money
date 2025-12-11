"""
配置加载器 - 使用TOML格式
"""
import os
import sys
from typing import Any, Dict

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def load_config(config_path: str = None) -> Dict[str, Any]:
    """加载TOML配置文件

    Args:
        config_path: 配置文件路径，默认从项目根目录的config.toml加载

    Returns:
        配置字典
    """
    if config_path is None:
        # 从 src/quant_strategies/core/config.py 到项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
        config_path = os.path.join(project_root, 'config.toml')

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'rb') as f:  # tomllib需要二进制模式
        config = tomllib.load(f)

    return config


def get_etf_list(config: Dict[str, Any]) -> list:
    """从配置中获取ETF列表"""
    return config.get('etf_list', [])


def get_benchmark_symbol(config: Dict[str, Any]) -> str:
    """获取基准指数代码"""
    return config.get('benchmark', {}).get('symbol', '000300.SH')


def get_backtest_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取回测参数"""
    return config.get('backtest_params', {})


def get_factor_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取因子参数"""
    return config.get('factor_params', {})


def get_trading_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取交易参数"""
    return config.get('trading_params', {})


def get_risk_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取风控参数"""
    return config.get('risk_params', {})


def get_market_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取市场参数"""
    return config.get('market_params', {})


def get_epo_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取EPO优化参数"""
    return config.get('epo_params', {})


def get_cost_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取交易成本参数"""
    return config.get('cost_params', {})


def get_defensive_etfs(config: Dict[str, Any]) -> list:
    """获取防御性ETF列表"""
    return config.get('defensive_etfs', [])


def get_strategies_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取多策略配置"""
    return config.get('strategies', {})


def get_strategy_config(config: Dict[str, Any], strategy_name: str) -> Dict[str, Any]:
    """获取单个策略配置"""
    strategies = get_strategies_config(config)
    return strategies.get(strategy_name, {})


def get_strategy_params(config: Dict[str, Any], strategy_name: str) -> Dict[str, Any]:
    """获取策略参数"""
    strategy = get_strategy_config(config, strategy_name)
    return strategy.get('params', {})


def is_strategy_enabled(config: Dict[str, Any], strategy_name: str) -> bool:
    """检查策略是否启用"""
    strategy = get_strategy_config(config, strategy_name)
    return strategy.get('enabled', False)


def get_enabled_strategies(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取所有启用的策略"""
    strategies = get_strategies_config(config)
    return {name: info for name, info in strategies.items() if info.get('enabled', False)}
