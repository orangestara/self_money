"""
策略基类 - 所有策略的抽象基类

定义了策略必须实现的接口，包括信号生成、回测逻辑等
"""

import abc
import backtrader as bt
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime


class BaseStrategy(bt.Strategy):
    """策略基类 - 定义策略的通用接口"""

    # 默认参数（子类可以覆盖）
    params = (
        ('log_level', 1),  # 日志级别
        ('initial_cash', 1000000),  # 初始资金
    )

    def __init__(self, strategy_config: Dict[str, Any] = None):
        """初始化策略

        Args:
            strategy_config: 策略配置字典
        """
        # 保存策略配置
        self.strategy_config = strategy_config or {}

        # 策略状态
        self.factor_scores = {}  # 因子得分
        self.hold_cost = {}  # 持仓成本 {symbol: cost_price}
        self.hold_high = {}  # 持仓最高价 {symbol: highest_price}
        self.signal_history = []  # 信号历史
        self.trade_history = []  # 交易历史

        # 数据引用
        self.data_dict = {}
        for i, data in enumerate(self.datas):
            symbol = getattr(data._name, 'name', f"UNKNOWN_{i}")
            self.data_dict[symbol] = data

        # 日志
        self.log("策略初始化完成", level=1)

    @property
    @abc.abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @property
    @abc.abstractmethod
    def strategy_description(self) -> str:
        """策略描述"""
        pass

    @abc.abstractmethod
    def generate_signals(self) -> Dict[str, Any]:
        """生成买入/卖出信号

        Returns:
            Dict包含:
                - signals: {symbol: signal_dict}
                - positions: {symbol: target_weight}
                - reason: str
        """
        pass

    @abc.abstractmethod
    def calculate_indicators(self, data: bt.feeds.PandasData) -> Dict[str, Any]:
        """计算技术指标

        Args:
            data: 数据源

        Returns:
            指标字典
        """
        pass

    @abc.abstractmethod
    def check_exit_conditions(self, symbol: str, data: bt.feeds.PandasData) -> Dict[str, Any]:
        """检查退出条件

        Args:
            symbol: 标的代码
            data: 数据源

        Returns:
            退出信号字典
        """
        pass

    def get_position_weight(self, symbol: str) -> float:
        """获取当前持仓权重"""
        if symbol not in self.data_dict:
            return 0.0

        data = self.data_dict[symbol]
        if data not in self.positions or self.positions[data].size <= 0:
            return 0.0

        total_value = self.broker.getvalue()
        if total_value <= 0:
            return 0.0

        position_value = self.positions[data].size * self.positions[data].price
        return position_value / total_value

    def get_position_value(self, symbol: str) -> float:
        """获取当前持仓价值"""
        if symbol not in self.data_dict:
            return 0.0

        data = self.data_dict[symbol]
        if data not in self.positions or self.positions[data].size <= 0:
            return 0.0

        return self.positions[data].size * self.positions[data].price

    def update_position_cost(self, symbol: str, price: float):
        """更新持仓成本和最高价"""
        if symbol not in self.hold_cost:
            self.hold_cost[symbol] = price
            self.hold_high[symbol] = price
        else:
            self.hold_high[symbol] = max(self.hold_high[symbol], price)

    def log(self, txt, dt=None, level: int = 1):
        """日志输出"""
        if level <= self.params.log_level:
            dt = dt or self.datas[0].datetime.date(0) if self.datas else datetime.now()
            print(f'{dt.isoformat()} [{self.strategy_name}]: {txt}')

    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入: {order.data._name}, '
                    f'价格: {order.executed.price:.2f}, '
                    f'数量: {order.executed.size}, '
                    f'成本: {order.executed.value:.2f}'
                )
                # 更新持仓成本
                symbol = getattr(order.data._name, 'name', 'UNKNOWN')
                self.update_position_cost(symbol, order.executed.price)
            else:
                self.log(
                    f'卖出: {order.data._name}, '
                    f'价格: {order.executed.price:.2f}, '
                    f'数量: {order.executed.size}, '
                    f'收益: {order.executed.value:.2f}'
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'订单失败: {order.data._name}')

    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return

        symbol = getattr(trade.data._name, 'name', 'UNKNOWN')
        self.log(
            f'交易完成: {symbol}, '
            f'毛利: {trade.pnl:.2f}, '
            f'净利: {trade.pnlcomm:.2f}'
        )

        # 记录交易历史
        self.trade_history.append({
            'symbol': symbol,
            'pnl': trade.pnl,
            'pnlcomm': trade.pnlcomm,
            'date': self.datas[0].datetime.date(0) if self.datas else datetime.now()
        })

    def get_stats(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        total_trades = len(self.trade_history)
        total_pnl = sum(t['pnlcomm'] for t in self.trade_history)

        winning_trades = [t for t in self.trade_history if t['pnlcomm'] > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        return {
            'strategy_name': self.strategy_name,
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'final_value': self.broker.getvalue(),
            'total_return': (self.broker.getvalue() / self.broker.startingcash - 1) * 100
        }

    def stop(self):
        """策略结束回调"""
        self.log("=" * 50)
        self.log(f"策略: {self.strategy_name}")
        self.log(f"描述: {self.strategy_description}")
        self.log("=" * 50)
        self.log(f"初始资金: {self.broker.startingcash:,.2f}")
        self.log(f"最终资金: {self.broker.getvalue():,.2f}")
        self.log(f"总收益: {(self.broker.getvalue() / self.broker.startingcash - 1) * 100:.2f}%")
        self.log(f"交易次数: {len(self.trade_history)}")
        self.log("=" * 50)


class SignalOnlyStrategy(BaseStrategy):
    """仅生成信号的策略基类（不执行交易）"""

    def __init__(self, strategy_config: Dict[str, Any] = None):
        super().__init__(strategy_config)
        self.execute_trades = self.strategy_config.get('execute_trades', False)

    def next(self):
        """主逻辑 - 生成信号但不执行交易"""
        # 生成信号
        signals = self.generate_signals()

        if signals and 'signals' in signals:
            # 记录信号
            self.signal_history.append({
                'date': self.datas[0].datetime.date(0) if self.datas else datetime.now(),
                'signals': signals['signals']
            })

            # 如果需要执行交易，则下单
            if self.execute_trades:
                self._execute_signals(signals)

    def _execute_signals(self, signals: Dict[str, Any]):
        """执行信号交易"""
        if 'positions' not in signals:
            return

        for symbol, target_weight in signals['positions'].items():
            if symbol not in self.data_dict:
                continue

            data = self.data_dict[symbol]
            self.order_target_percent(data, target_weight)
