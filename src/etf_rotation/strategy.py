"""
ETF轮动策略 - backtrader版本

基于多因子模型的ETF轮动策略，包含动量因子、质量因子、
动态风控、市场风险判断等功能。
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import yaml
import os
from collections import defaultdict

from .factors import FactorCalculator
from .risk_manager import RiskManager
from .utils import (
    score_based_weighting,
    get_weekday,
    format_currency,
    format_percentage,
)


class ETFRotationStrategy(bt.Strategy):
    """ETF轮动策略"""

    params = (
        ('rebalance_weekday', 0),  # 每周一调仓
        ('rebalance_threshold', 0.05),  # 权重偏离阈值
        ('max_holdings', 3),  # 最多持有3个标的
        ('score_threshold', 0),  # 综合得分阈值
        ('min_positive_count', 7),  # 综合得分大于0的ETF最小数量
        ('log_level', 1),  # 日志级别
    )

    def __init__(self):
        """初始化策略"""
        # 加载配置
        self._load_config()

        # 初始化组件
        self.factor_calculator = FactorCalculator(self.factor_params)
        self.risk_manager = RiskManager(self.risk_params)

        # 策略状态
        self.factor_scores = {}  # 因子得分
        self.positive_count = 0  # 综合得分大于0的ETF数量
        self.hold_cost = {}  # 持仓成本 {symbol: cost_price}
        self.hold_high = {}  # 持仓最高价 {symbol: highest_price}

        # ETF信息
        self.etf_symbols = [etf['symbol'] for etf in self.etf_list]
        self.etf_styles = {etf['symbol']: etf['style'] for etf in self.etf_list}

        # 数据引用
        self.data_dict = {}
        for i, data in enumerate(self.datas):
            symbol = self.etf_symbols[i] if i < len(self.etf_symbols) else f"UNKNOWN_{i}"
            self.data_dict[symbol] = data

        # 基准数据（通常是第一个或最后一个）
        if self.etf_symbols:
            self.benchmark_symbol = '000300.SS'
            # 如果基准数据在列表中，使用它；否则使用第一个ETF作为近似基准
            if self.benchmark_symbol in self.data_dict:
                self.benchmark_data = self.data_dict[self.benchmark_symbol]
            else:
                self.benchmark_data = list(self.data_dict.values())[0]

        # 日志输出
        if self.p.log_level > 0:
            print("\n=== ETF轮动策略初始化完成 ===")
            print(f"ETF数量: {len(self.etf_list)}")
            print(f"最多持有: {self.p.max_holdings} 个标的")
            print(f"调仓日: 周{self.p.rebalance_weekday + 1}")
            print(f"风控参数:")
            print(f"  - 基础止损: {self.risk_params['stop_loss_base']:.1%}")
            print(f"  - 基础止盈: {self.risk_params['take_profit_ratio']:.1%}")
            print("=" * 40)

    def _load_config(self):
        """加载配置文件"""
        # 获取项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 从 src/etf_rotation/strategy.py 到项目根目录
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        config_path = os.path.join(project_root, 'config', 'config.yaml')

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 提取配置
        self.etf_list = config['etf_list']
        self.factor_params = config['factor_params']
        self.risk_params = config['risk_params']
        self.trading_params = config['trading_params']
        self.market_params = config['market_params']
        self.defensive_etfs = config['defensive_etfs']

        # 更新策略参数
        self.p.max_holdings = self.trading_params['max_holdings']
        self.p.score_threshold = self.trading_params['score_threshold']
        self.p.min_positive_count = self.trading_params['min_positive_count']
        self.p.rebalance_weekday = self.market_params['rebalance_weekday']
        self.p.rebalance_threshold = self.market_params['rebalance_threshold']

    def log(self, txt, dt=None):
        """日志输出"""
        if self.p.log_level > 0:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')

    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入执行: {order.data._name}, '
                    f'价格: {order.executed.price:.2f}, '
                    f'数量: {order.executed.size}, '
                    f'成本: {order.executed.value:.2f}'
                )
            else:
                self.log(
                    f'卖出执行: {order.data._name}, '
                    f'价格: {order.executed.price:.2f}, '
                    f'数量: {order.executed.size}, '
                    f'收益: {order.executed.value:.2f}'
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'订单取消/拒绝: {order.data._name}')

    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return

        self.log(
            f'交易完成: {trade.data._name}, '
            f'毛利: {trade.pnl:.2f}, '
            f'净利: {trade.pnlcomm:.2f}'
        )

    def prenext(self):
        """数据不足时的回调"""
        pass

    def next(self):
        """主逻辑"""
        # 跳过初始数据不足的时期
        if len(self.data) < max(
            self.factor_params['momentum_window'],
            self.factor_params['slope_window'],
            self.factor_params['rsrs_window'],
            self.factor_params['ma_window'],
            self.factor_params['volatility_window'],
            self.risk_params['vol_quantile_window']
        ):
            return

        current_date = self.datas[0].datetime.date(0)
        current_weekday = current_date.weekday()

        # 每天计算因子值（只在需要调仓时使用）
        if current_weekday == self.p.rebalance_weekday:
            self._calculate_factors()

        # 执行交易逻辑
        self._execute_trading()

    def _calculate_factors(self):
        """计算因子值"""
        if self.p.log_level > 1:
            self.log("开始计算因子值")

        self.factor_scores = {}
        self.positive_count = 0

        # 更新市场风险状态
        self._update_market_risk()

        # 计算每个ETF的因子
        for symbol, data in self.data_dict.items():
            try:
                # 获取历史数据
                hist_data = self._get_historical_data(data, days=60)
                if hist_data is None or len(hist_data) < 30:
                    continue

                # 计算因子
                factors = self.factor_calculator.calculate_all_factors(hist_data)

                if factors['composite'] > 0:
                    self.positive_count += 1

                self.factor_scores[symbol] = factors

            except Exception as e:
                print(f"计算{symbol}因子失败: {e}")
                continue

        if self.p.log_level > 1:
            self.log(f"因子计算完成，综合得分>0的ETF数量: {self.positive_count}")

    def _update_market_risk(self):
        """更新市场风险状态"""
        try:
            # 获取基准数据
            if hasattr(self, 'benchmark_data'):
                benchmark_data = self._get_historical_data(self.benchmark_data, days=90)
                if benchmark_data is not None:
                    self.risk_manager.update_market_risk(benchmark_data)

                    if self.p.log_level > 1:
                        self.risk_manager.print_risk_status()
        except Exception as e:
            print(f"更新市场风险失败: {e}")

    def _get_historical_data(self, data, days=60) -> pd.DataFrame:
        """获取历史数据"""
        try:
            # 在backtrader中，我们需要从当前数据点向前获取数据
            # 由于没有直接的history方法，我们模拟获取数据
            hist = []
            for i in range(min(days, len(data))):
                idx = len(data) - 1 - i
                if idx < 0:
                    break
                hist.append({
                    'datetime': data.datetime.get(idx),
                    'open': data.open[idx],
                    'high': data.high[idx],
                    'low': data.low[idx],
                    'close': data.close[idx],
                    'volume': data.volume[idx],
                })

            if len(hist) < 10:
                return None

            df = pd.DataFrame(hist)
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
            return df

        except Exception as e:
            print(f"获取历史数据失败: {e}")
            return None

    def _execute_trading(self):
        """执行交易逻辑"""
        # 检查是否需要调仓
        if not self._should_rebalance():
            return

        # 风控检查：止损止盈
        self._check_risk_controls()

        # 获取目标持仓
        target_positions = self._get_target_positions()

        # 调整持仓
        self._rebalance_portfolio(target_positions)

    def _should_rebalance(self) -> bool:
        """判断是否需要调仓"""
        current_weekday = self.datas[0].datetime.date(0).weekday()

        # 每周调仓日
        if current_weekday == self.p.rebalance_weekday:
            return True

        # 权重偏离超阈值时调仓
        if self.factor_scores:
            current_weights = self._get_current_weights()
            target_weights = self._get_target_weights()

            for symbol in current_weights:
                current_weight = current_weights.get(symbol, 0)
                target_weight = target_weights.get(symbol, 0)
                if abs(current_weight - target_weight) > self.p.rebalance_threshold:
                    return True

        return False

    def _check_risk_controls(self):
        """风控检查"""
        positions_to_sell = []
        positions_to_reduce = []

        for data, position in self.positions.items():
            if position.size <= 0:
                continue

            # 获取symbol
            symbol = None
            for sym, dat in self.data_dict.items():
                if dat is data:
                    symbol = sym
                    break

            if symbol is None or symbol not in self.hold_cost:
                continue

            current_price = position.price
            cost_price = self.hold_cost[symbol]
            highest_price = self.hold_high.get(symbol, current_price)

            # 检查止损
            should_sell, reason = self.risk_manager.check_stop_loss(
                symbol, current_price, cost_price, highest_price
            )
            if should_sell:
                positions_to_sell.append(symbol)
                self.log(f"止损: {symbol}, {reason}")
                continue

            # 检查止盈
            should_reduce, new_ratio, reason = self.risk_manager.check_take_profit(
                symbol, current_price, cost_price, highest_price
            )
            if should_reduce:
                positions_to_reduce.append((symbol, new_ratio))
                self.log(f"止盈: {symbol}, {reason}")

        # 执行卖出
        for symbol in positions_to_sell:
            data = self.data_dict.get(symbol)
            if data:
                self.order_target_percent(data, 0)
            if symbol in self.hold_cost:
                del self.hold_cost[symbol]
            if symbol in self.hold_high:
                del self.hold_high[symbol]

        # 执行减仓
        for symbol, ratio in positions_to_reduce:
            data = self.data_dict.get(symbol)
            if data:
                current_value = self.broker.getvalue()
                target_value = current_value * ratio
                self.order_target_value(data, target_value)

    def _get_target_positions(self) -> Dict[str, float]:
        """获取目标持仓"""
        # 防御性切换
        if (self.positive_count < self.p.min_positive_count or
                self.risk_manager.market_risk_level == 'high_risk'):
            if self.p.log_level > 0:
                self.log(f"市场高风险/优质ETF不足，切换防御组合")
            return {symbol: 1.0 / len(self.defensive_etfs)
                    for symbol in self.defensive_etfs}

        # 正常选股
        if not self.factor_scores:
            return {}

        qualified_etfs = [
            (symbol, score) for symbol, score in self.factor_scores.items()
            if score['composite'] > self.p.score_threshold
        ]

        if not qualified_etfs:
            if self.p.log_level > 0:
                self.log("无符合条件的ETF")
            return {}

        # 风格分散选择
        sorted_etfs = sorted(qualified_etfs, key=lambda x: x[1]['composite'], reverse=True)
        target_list = []
        style_included = set()

        # 优先选择不同风格
        for symbol, score in sorted_etfs:
            style = self.etf_styles.get(symbol, 'unknown')
            if style not in style_included or len(target_list) < 2:
                target_list.append(symbol)
                style_included.add(style)
            if len(target_list) >= self.p.max_holdings:
                break

        # 补充至目标数量
        if len(target_list) < self.p.max_holdings:
            for symbol, score in sorted_etfs:
                if symbol not in target_list:
                    target_list.append(symbol)
                    if len(target_list) >= self.p.max_holdings:
                        break

        # 计算权重
        scores = [self.factor_scores[symbol]['composite'] for symbol in target_list]
        weights = score_based_weighting(scores)

        target_positions = {}
        for i, symbol in enumerate(target_list):
            if i < len(weights):
                target_positions[symbol] = weights[i]

        # 应用总仓位比例
        total_ratio = self.risk_manager.total_position_ratio
        for symbol in target_positions:
            target_positions[symbol] *= total_ratio

        if self.p.log_level > 0:
            self.log(f"目标持仓: {target_positions}")

        return target_positions

    def _get_current_weights(self) -> Dict[str, float]:
        """获取当前权重"""
        total_value = self.broker.getvalue()
        if total_value <= 0:
            return {}

        weights = {}
        for data, position in self.positions.items():
            if position.size > 0:
                # 获取symbol
                symbol = None
                for sym, dat in self.data_dict.items():
                    if dat is data:
                        symbol = sym
                        break
                if symbol:
                    position_value = position.size * position.price
                    weights[symbol] = position_value / total_value

        return weights

    def _get_target_weights(self) -> Dict[str, float]:
        """获取目标权重"""
        if not self.factor_scores:
            return {}

        qualified_etfs = [
            (symbol, score) for symbol, score in self.factor_scores.items()
            if score['composite'] > self.p.score_threshold
        ]

        if not qualified_etfs:
            return {}

        sorted_etfs = sorted(qualified_etfs, key=lambda x: x[1]['composite'], reverse=True)
        target_list = [symbol for symbol, _ in sorted_etfs[:self.p.max_holdings]]
        scores = [self.factor_scores[symbol]['composite'] for symbol in target_list]
        weights = score_based_weighting(scores)

        return dict(zip(target_list, weights))

    def _rebalance_portfolio(self, target_positions: Dict[str, float]):
        """重新平衡投资组合"""
        # 卖出不在目标列表的持仓
        for data, position in self.positions.items():
            if position.size > 0:
                # 获取symbol
                symbol = None
                for sym, dat in self.data_dict.items():
                    if dat is data:
                        symbol = sym
                        break

                if symbol and symbol not in target_positions:
                    self.order_target_percent(data, 0)
                    self.log(f"卖出: {symbol} (不在目标列表)")
                    if symbol in self.hold_cost:
                        del self.hold_cost[symbol]
                    if symbol in self.hold_high:
                        del self.hold_high[symbol]

        # 买入目标持仓
        for symbol, target_weight in target_positions.items():
            data = self.data_dict.get(symbol)
            if data:
                self.order_target_percent(data, target_weight)

                # 更新持仓成本和最高价
                if data in self.positions and self.positions[data].size > 0:
                    position = self.positions[data]
                    cost_price = position.price
                    self.hold_cost[symbol] = cost_price
                    self.hold_high[symbol] = cost_price

    def stop(self):
        """策略结束时的回调"""
        if self.p.log_level > 0:
            final_value = self.broker.getvalue()
            total_return = (final_value / self.broker.startingcash - 1) * 100
            self.log(f"\n=== 策略结束 ===")
            self.log(f"初始资金: {format_currency(self.broker.startingcash)}")
            self.log(f"最终资金: {format_currency(final_value)}")
            self.log(f"总收益率: {total_return:.2f}%")
            self.log("=" * 40)
