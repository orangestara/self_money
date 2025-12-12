"""
策略管理器 - 负责注册、管理和运行多个策略

支持策略注册、配置管理、信号收集等功能
"""

import os
import backtrader as bt
from typing import Dict, List, Any, Optional, Type
from datetime import datetime
import pandas as pd

from ..core.base_strategy import BaseStrategy, SignalOnlyStrategy
from ..core.config import load_config
from ..core.utils import format_currency, format_percentage


class StrategyManager:
    """策略管理器"""

    def __init__(self, config_path: str = None):
        """初始化策略管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = load_config(config_path) if config_path else load_config()

        # 策略注册表
        self.strategies = {}  # {name: strategy_info}
        self.strategy_classes = {}  # {name: class}

        # 策略实例
        self.strategy_instances = {}  # {name: instance}

        # 策略统计
        self.stats = {}  # {name: stats}

        # 初始化默认策略
        self._register_default_strategies()

    def _register_default_strategies(self):
        """注册默认策略"""
        try:
            from ..strategies import ETFRotationStrategy, GridTradingStrategy
            # 从策略配置中获取
            etf_config = self.config.get('strategies', {}).get('etf_rotation', {})
            grid_config = self.config.get('strategies', {}).get('grid_trading', {})

            self.register_strategy(
                name='etf_rotation',
                strategy_class=ETFRotationStrategy,
                description=etf_config.get('description', 'ETF轮动策略'),
                config=etf_config
            )

            self.register_strategy(
                name='grid_trading',
                strategy_class=GridTradingStrategy,
                description=grid_config.get('description', '网格交易策略'),
                config=grid_config
            )
        except ImportError as e:
            print(f"注册策略失败: {e}")

    def register_strategy(self,
                         name: str,
                         strategy_class: Type[BaseStrategy],
                         description: str = "",
                         config: Dict[str, Any] = None):
        """注册策略

        Args:
            name: 策略名称
            strategy_class: 策略类
            description: 策略描述
            config: 策略配置
        """
        self.strategy_classes[name] = strategy_class
        self.strategies[name] = {
            'name': name,
            'class': strategy_class,
            'description': description,
            'config': config or {},
            'enabled': True,
            'created_at': datetime.now()
        }

    def unregister_strategy(self, name: str):
        """注销策略"""
        if name in self.strategies:
            del self.strategies[name]
            if name in self.strategy_classes:
                del self.strategy_classes[name]
            if name in self.strategy_instances:
                del self.strategy_instances[name]
            if name in self.stats:
                del self.stats[name]

    def get_strategy(self, name: str) -> Optional[Dict[str, Any]]:
        """获取策略信息"""
        return self.strategies.get(name)

    def list_strategies(self, enabled_only: bool = False) -> Dict[str, Dict[str, Any]]:
        """列出所有策略

        Args:
            enabled_only: 是否只返回启用的策略

        Returns:
            策略信息字典 {name: info}
        """
        if enabled_only:
            return {name: info for name, info in self.strategies.items()
                    if info.get('enabled', False)}
        return self.strategies.copy()

    def enable_strategy(self, name: str):
        """启用策略"""
        if name in self.strategies:
            self.strategies[name]['enabled'] = True

    def disable_strategy(self, name: str):
        """禁用策略"""
        if name in self.strategies:
            self.strategies[name]['enabled'] = False

    def create_strategy(self,
                       name: str,
                       config: Dict[str, Any] = None) -> Optional[BaseStrategy]:
        """创建策略实例

        Args:
            name: 策略名称
            config: 覆盖配置

        Returns:
            策略实例
        """
        if name not in self.strategy_classes:
            return None

        strategy_info = self.strategies[name]
        strategy_class = strategy_info['class']
        strategy_config = strategy_info['config'].copy()

        # 合并配置
        if config:
            strategy_config.update(config)

        # 创建实例（注意：backtrader策略需要在有数据的情况下初始化）
        try:
            # 如果没有数据，返回一个配置对象而不是实例
            if not hasattr(self, '_has_data') or not self._has_data:
                # 创建一个轻量级的策略配置对象
                class StrategyConfig:
                    def __init__(self, config):
                        self.strategy_config = config
                        self.strategy_name = strategy_class.__name__
                        self.strategy_description = getattr(strategy_class, '__doc__', '')

                return StrategyConfig(strategy_config)

            instance = strategy_class(strategy_config)
            self.strategy_instances[name] = instance
            return instance
        except Exception as e:
            print(f"创建策略{name}失败: {e}")
            # 返回配置对象而不是None
            class StrategyConfig:
                def __init__(self, config):
                    self.strategy_config = config
                    self.strategy_name = strategy_class.__name__

            return StrategyConfig(strategy_config)

    def run_single_strategy(self,
                           strategy_name: str,
                           data_dict: Dict[str, pd.DataFrame],
                           start_date: str,
                           end_date: str,
                           initial_cash: float = 1000000,
                           config: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行单个策略

        Args:
            strategy_name: 策略名称
            data_dict: 数据字典 {symbol: DataFrame}
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            config: 策略配置

        Returns:
            回测结果
        """
        # 获取策略类
        if strategy_name not in self.strategy_classes:
            return {'error': f'策略 {strategy_name} 不存在'}

        strategy_class = self.strategy_classes[strategy_name]
        strategy_info = self.strategies[strategy_name]
        strategy_config = strategy_info['config'].copy()

        # 合并配置
        if config:
            strategy_config.update(config)

        # 创建Cerebro引擎
        cerebro = bt.Cerebro()

        # 添加策略（使用真正的策略类）
        cerebro.addstrategy(strategy_class, strategy_config)

        # 添加数据
        for symbol, data in data_dict.items():
            try:
                # 确保列名是大写的
                data.columns = [col.upper() if isinstance(col, str) else col for col in data.columns]

                # 创建PandasData并设置名称
                datafeed = bt.feeds.PandasData(dataname=data)
                # 显式设置名称属性
                datafeed._name = type('obj', (object,), {'name': symbol})()

                cerebro.adddata(datafeed, name=symbol)
            except Exception as e:
                print(f"添加数据{symbol}失败: {e}")
                continue

        # 设置初始资金
        cerebro.broker.setcash(initial_cash)

        # 设置佣金
        cerebro.broker.setcommission(commission=0.00025)

        # 设置滑点
        cerebro.slipspread = 0.0003
        cerebro.slippage = 0.0003

        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="timereturn")

        # 运行回测
        results = cerebro.run()

        # 获取结果
        strat = results[0]
        final_value = cerebro.broker.getvalue()

        # 收集统计信息
        stats = strat.get_stats()

        # 分析器结果
        if hasattr(strat, 'analyzers'):
            returns = strat.analyzers.returns.get_analysis()
            sharpe = strat.analyzers.sharpe.get_analysis()
            drawdown = strat.analyzers.drawdown.get_analysis()
            timereturn = strat.analyzers.timereturn.get_analysis()

            stats.update({
                'annualized_return': returns.get('rtot', 0),
                'sharpe_ratio': sharpe.get('sharperatio', 0),
                'max_drawdown': drawdown.get('max', {}).get('drawdown', 0) / 100,
                'drawdown_len': drawdown.get('max', {}).get('len', 0)
            })

            # 添加收益曲线数据
            if timereturn:
                returns_data = []
                for date, ret in timereturn.items():
                    if isinstance(date, (int, float)):
                        date = datetime.fromtimestamp(date).strftime('%Y-%m-%d')
                    returns_data.append({
                        'date': date,
                        'value': ret * 100
                    })
                stats['returns'] = returns_data

            # 添加回撤曲线数据
            if 'max' in drawdown and 'drawdown' in drawdown['max']:
                drawdown_data = []
                for key, value in drawdown['max'].items():
                    if 'drawdown' in key:
                        drawdown_data.append({
                            'date': key,
                            'value': value
                        })
                stats['drawdown'] = drawdown_data

        # 保存统计信息
        self.stats[strategy_name] = stats

        return stats

    def run_multiple_strategies(self,
                               strategy_configs: Dict[str, Dict[str, Any]],
                               data_dict: Dict[str, pd.DataFrame],
                               start_date: str,
                               end_date: str,
                               initial_cash: float = 1000000) -> Dict[str, Dict[str, Any]]:
        """运行多个策略

        Args:
            strategy_configs: 策略配置 {name: config}
            data_dict: 数据字典
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金

        Returns:
            所有策略的结果
        """
        results = {}

        for strategy_name, config in strategy_configs.items():
            # 检查策略是否启用
            strategy_info = self.get_strategy(strategy_name)
            if not strategy_info or not strategy_info.get('enabled', False):
                continue

            # 运行策略
            result = self.run_single_strategy(
                strategy_name,
                data_dict,
                start_date,
                end_date,
                initial_cash,
                config
            )
            results[strategy_name] = result

        return results

    def generate_signals(self,
                        strategy_name: str,
                        data_dict: Dict[str, pd.DataFrame],
                        config: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成买入信号

        Args:
            strategy_name: 策略名称
            data_dict: 数据字典
            config: 策略配置

        Returns:
            信号字典
        """
        strategy = self.create_strategy(strategy_name, config)
        if not strategy:
            return {'error': f'策略 {strategy_name} 不存在'}

        # 创建信号策略
        signal_strategy = SignalOnlyStrategy(strategy.strategy_config)

        # 设置数据
        cerebro = bt.Cerebro()
        for symbol, data in data_dict.items():
            datafeed = bt.feeds.PandasData(dataname=data)
            cerebro.adddata(datafeed, name=symbol)

        # 添加策略
        cerebro.addstrategy(signal_strategy)

        # 运行
        results = cerebro.run()

        # 获取信号
        signals = results[0].signal_history

        return {
            'strategy_name': strategy_name,
            'signals': signals,
            'latest_signals': signals[-1] if signals else None
        }

    def compare_strategies(self, strategy_names: List[str]) -> pd.DataFrame:
        """比较策略表现

        Args:
            strategy_names: 策略名称列表

        Returns:
            比较结果DataFrame
        """
        data = []
        for name in strategy_names:
            if name in self.stats:
                stats = self.stats[name]
                data.append({
                    'strategy_name': name,
                    'total_return': stats.get('total_return', 0),
                    'sharpe_ratio': stats.get('sharpe_ratio', 0),
                    'max_drawdown': stats.get('max_drawdown', 0),
                    'total_trades': stats.get('total_trades', 0),
                    'win_rate': stats.get('win_rate', 0)
                })

        return pd.DataFrame(data)

    def print_strategy_summary(self):
        """打印策略摘要"""
        print("\n" + "=" * 60)
        print("策略管理摘要")
        print("=" * 60)

        print(f"\n已注册策略数量: {len(self.strategies)}")
        print(f"已运行策略数量: {len(self.stats)}")

        for name, info in self.strategies.items():
            status = "✓ 启用" if info.get('enabled', False) else "✗ 禁用"
            print(f"  - {name}: {info.get('description', '')} [{status}]")

        if self.stats:
            print("\n策略表现:")
            for name, stats in self.stats.items():
                print(f"\n  {name}:")
                print(f"    总收益: {stats.get('total_return', 0):.2f}%")
                print(f"    夏普比率: {stats.get('sharpe_ratio', 0):.2f}")
                print(f"    最大回撤: {stats.get('max_drawdown', 0):.2f}%")
                print(f"    交易次数: {stats.get('total_trades', 0)}")
                print(f"    胜率: {stats.get('win_rate', 0):.2f}")

        print("=" * 60)
