"""
策略工厂模式

负责动态创建和管理策略实例
"""

from typing import Dict, Any, Type, Optional
from ..core.base_strategy import BaseStrategy
from ..core.config import load_config


class StrategyFactory:
    """策略工厂"""

    def __init__(self, config_path: str = None):
        """初始化工厂

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = load_config(config_path) if config_path else load_config()

        # 策略类注册表
        self._strategy_classes = {}

        # 注册默认策略
        self._register_default_strategies()

    def _register_default_strategies(self):
        """注册默认策略"""
        try:
            from .strategies.etf_rotation import ETFRotationStrategy
            self.register_strategy('etf_rotation', ETFRotationStrategy)
        except ImportError as e:
            print(f"注册默认策略失败: {e}")

    def register_strategy(self, name: str, strategy_class: Type[BaseStrategy]):
        """注册策略类

        Args:
            name: 策略名称
            strategy_class: 策略类
        """
        self._strategy_classes[name] = strategy_class

    def create_strategy(self,
                       strategy_name: str,
                       config: Dict[str, Any] = None) -> Optional[BaseStrategy]:
        """创建策略实例

        Args:
            strategy_name: 策略名称
            config: 配置覆盖

        Returns:
            策略实例
        """
        if strategy_name not in self._strategy_classes:
            return None

        strategy_class = self._strategy_classes[strategy_name]

        # 合并配置
        strategy_config = self._merge_config(strategy_name, config)

        # 创建实例
        try:
            instance = strategy_class(strategy_config)
            return instance
        except Exception as e:
            print(f"创建策略 {strategy_name} 失败: {e}")
            return None

    def _merge_config(self, strategy_name: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """合并配置

        Args:
            strategy_name: 策略名称
            config: 配置覆盖

        Returns:
            合并后的配置
        """
        # 从配置文件中获取策略配置
        from ..core.config import get_strategy_config

        base_config = get_strategy_config(self.config, strategy_name)

        # 合并配置
        merged = base_config.copy()
        if config:
            merged.update(config)

        # 确保包含params
        if 'params' not in merged:
            merged['params'] = {}

        return merged

    def get_strategy_info(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """获取策略信息

        Args:
            strategy_name: 策略名称

        Returns:
            策略信息
        """
        from ..core.config import get_strategy_config

        return get_strategy_config(self.config, strategy_name)

    def list_strategies(self) -> Dict[str, Dict[str, Any]]:
        """列出所有已注册的策略

        Returns:
            策略信息字典
        """
        from ..core.config import get_strategies_config

        return get_strategies_config(self.config)

    def get_enabled_strategies(self) -> Dict[str, Dict[str, Any]]:
        """获取所有启用的策略

        Returns:
            启用的策略信息字典
        """
        from ..core.config import get_enabled_strategies

        return get_enabled_strategies(self.config)

    def batch_create_strategies(self,
                               strategy_configs: Dict[str, Dict[str, Any]]) -> Dict[str, BaseStrategy]:
        """批量创建策略

        Args:
            strategy_configs: 策略配置 {name: config}

        Returns:
            策略实例字典
        """
        instances = {}

        for name, config in strategy_configs.items():
            instance = self.create_strategy(name, config)
            if instance:
                instances[name] = instance

        return instances


class StrategyLoader:
    """策略加载器"""

    def __init__(self, config_path: str = None):
        """初始化加载器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.factory = StrategyFactory(config_path)

    def load_strategy(self,
                     strategy_name: str,
                     config: Dict[str, Any] = None) -> Optional[BaseStrategy]:
        """加载策略

        Args:
            strategy_name: 策略名称
            config: 配置覆盖

        Returns:
            策略实例
        """
        return self.factory.create_strategy(strategy_name, config)

    def load_all_enabled_strategies(self) -> Dict[str, BaseStrategy]:
        """加载所有启用的策略

        Returns:
            策略实例字典
        """
        enabled = self.factory.get_enabled_strategies()
        return self.factory.batch_create_strategies(enabled)

    def load_strategy_with_default(self,
                                  strategy_name: str,
                                  default_config: Dict[str, Any] = None) -> Optional[BaseStrategy]:
        """加载策略（使用默认配置）

        Args:
            strategy_name: 策略名称
            default_config: 默认配置

        Returns:
            策略实例
        """
        return self.factory.create_strategy(strategy_name, default_config)


def create_strategy_manager(config_path: str = None):
    """创建策略管理器的便捷函数

    Args:
        config_path: 配置文件路径

    Returns:
        策略管理器
    """
    from .strategy_manager import StrategyManager
    return StrategyManager(config_path)


def create_backtest_engine(config_path: str = None):
    """创建回测引擎的便捷函数

    Args:
        config_path: 配置文件路径

    Returns:
        回测引擎
    """
    from ..core.backtest_engine import BacktestEngine
    return BacktestEngine(config_path)


def create_signal_generator(config: Dict[str, Any] = None):
    """创建信号生成器的便捷函数

    Args:
        config: 配置字典

    Returns:
        信号生成器
    """
    from ..core.signal_generator import SignalGenerator
    return SignalGenerator(config)
