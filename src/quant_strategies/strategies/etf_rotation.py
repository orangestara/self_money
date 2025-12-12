"""
ETF轮动策略实现

基于多因子模型的ETF轮动策略，包含动量因子、质量因子、
动态风控、市场风险判断等功能。
"""

from typing import Dict, List, Any
import pandas as pd
from ..core.base_strategy import BaseStrategy
from ..core.factors import FactorCalculator
from ..core.risk_manager import RiskManager
from ..core.config import (
    load_config,
    get_etf_list,
    get_factor_params,
    get_risk_params,
    get_trading_params,
    get_market_params,
    get_benchmark_symbol,
)
from ..core.utils import score_based_weighting


class ETFRotationStrategy(BaseStrategy):
    """ETF轮动策略 - 继承自BaseStrategy"""

    # 策略属性
    @property
    def strategy_name(self) -> str:
        return "ETF轮动策略"

    @property
    def strategy_description(self) -> str:
        return "基于多因子模型的ETF轮动策略，包含动量因子、质量因子、动态风控等功能"

    # 参数
    params = (
        ('rebalance_weekday', 0),  # 每周一调仓
        ('rebalance_threshold', 0.05),  # 权重偏离阈值
        ('max_holdings', 3),  # 最多持有3个标的
        ('score_threshold', 0),  # 综合得分阈值
        ('min_positive_count', 7),  # 综合得分大于0的ETF最小数量
        ('log_level', 1),  # 日志级别
    )

    def __init__(self, strategy_config: Dict[str, Any] = None):
        """初始化策略"""
        # 先初始化基类
        super().__init__(strategy_config)

        # 加载配置
        self._load_config()

        # 初始化组件
        self.factor_calculator = FactorCalculator(self.factor_params)
        self.risk_manager = RiskManager(self.risk_params)

        # ETF信息
        self.etf_symbols = [etf['symbol'] for etf in self.etf_list]
        self.etf_styles = {etf['symbol']: etf['style'] for etf in self.etf_list}
        self.positive_count = 0  # 综合得分大于0的ETF数量

        # 基准数据
        if self.etf_symbols:
            self.benchmark_symbol = get_benchmark_symbol(self.config)
            if self.benchmark_symbol in self.data_dict:
                self.benchmark_data = self.data_dict[self.benchmark_symbol]
            else:
                self.benchmark_data = list(self.data_dict.values())[0]

        # 更新参数
        if 'params' in self.strategy_config:
            for key, value in self.strategy_config['params'].items():
                setattr(self.p, key, value)

        # 日志输出
        if self.params.log_level > 0:
            self.log("=" * 50)
            self.log(f"策略: {self.strategy_name}")
            self.log(f"描述: {self.strategy_description}")
            self.log(f"ETF数量: {len(self.etf_list)}")
            self.log(f"最多持有: {self.p.max_holdings} 个标的")
            self.log(f"调仓日: 周{self.p.rebalance_weekday + 1}")
            self.log(f"风控参数:")
            self.log(f"  - 基础止损: {self.risk_params['stop_loss_base']:.1%}")
            self.log(f"  - 基础止盈: {self.risk_params['take_profit_ratio']:.1%}")
            self.log("=" * 50)

    def _load_config(self):
        """加载配置文件"""
        self.config = load_config()

        # 提取配置
        self.etf_list = get_etf_list(self.config)
        self.factor_params = get_factor_params(self.config)
        self.risk_params = get_risk_params(self.config)
        self.trading_params = get_trading_params(self.config)
        self.market_params = get_market_params(self.config)
        self.defensive_etfs = self.config.get('defensive_etfs', [])

    def generate_signals(self) -> Dict[str, Any]:
        """生成买入/卖出信号"""
        # 计算因子值
        self._calculate_factors()

        # 获取目标持仓
        target_positions = self._get_target_positions()

        # 生成信号
        signals = {}
        for symbol, weight in target_positions.items():
            current_weight = self.get_position_weight(symbol)

            if weight > current_weight + 0.01:  # 买入信号
                signals[symbol] = {
                    'action': 'buy',
                    'current_weight': current_weight,
                    'target_weight': weight,
                    'weight_change': weight - current_weight
                }
            elif weight < current_weight - 0.01:  # 卖出信号
                signals[symbol] = {
                    'action': 'sell',
                    'current_weight': current_weight,
                    'target_weight': weight,
                    'weight_change': weight - current_weight
                }
            else:
                signals[symbol] = {
                    'action': 'hold',
                    'current_weight': current_weight,
                    'target_weight': weight,
                    'weight_change': 0
                }

        return {
            'signals': signals,
            'positions': target_positions,
            'reason': self._get_signal_reason()
        }

    def _calculate_factors(self):
        """计算因子值"""
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
                self.log(f"计算{symbol}因子失败: {e}", level=0)
                continue

    def _update_market_risk(self):
        """更新市场风险状态"""
        try:
            # 获取基准数据
            if hasattr(self, 'benchmark_data'):
                benchmark_data = self._get_historical_data(self.benchmark_data, days=90)
                if benchmark_data is not None and len(benchmark_data) > 20:
                    # 检查基准数据是否有效（不能全为0）
                    close_prices = benchmark_data['Close']
                    if close_prices.sum() > 0 and close_prices.mean() > 0.001:
                        self.risk_manager.update_market_risk(benchmark_data)

                        if self.params.log_level > 1:
                            self.risk_manager.print_risk_status()
                    else:
                        # 如果基准数据无效（全为0或过小），跳过风险更新
                        if self.params.log_level > 2:
                            self.log(f"基准数据无效（全为0或过小），跳过风险更新", level=2)
                else:
                    # 如果基准数据不足，跳过风险更新
                    if self.params.log_level > 2:
                        self.log(f"基准数据不足，跳过风险更新", level=2)
        except Exception as e:
            self.log(f"更新市场风险失败: {e}", level=0)

    def _get_historical_data(self, data, days=60):
        """获取历史数据"""
        try:
            hist = []
            for i in range(min(days, len(data))):
                ago = i  # 从当前bar往回ago个bar
                if ago >= len(data):
                    break

                # 安全获取并转换数值
                def safe_float(val):
                    if val is None or val == 0:
                        return 0.0
                    if isinstance(val, (int, float)):
                        return float(val)
                    if isinstance(val, str):
                        try:
                            return float(val)
                        except:
                            return 0.0
                    # 处理array.array等情况
                    try:
                        return float(val)
                    except:
                        return 0.0

                hist.append({
                    'datetime': data.datetime.get(ago=-ago),
                    'Open': safe_float(data.open.get(ago=-ago)),
                    'High': safe_float(data.high.get(ago=-ago)),
                    'Low': safe_float(data.low.get(ago=-ago)),
                    'Close': safe_float(data.close.get(ago=-ago)),
                    'Volume': safe_float(data.volume.get(ago=-ago)),
                })

            if len(hist) < 10:
                return None

            df = pd.DataFrame(hist)
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)

            # 确保所有数值列都是float类型
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)

            return df

        except Exception as e:
            self.log(f"获取历史数据失败: {e}", level=0)
            import traceback
            traceback.print_exc()
            return None

    def _get_target_positions(self) -> Dict[str, float]:
        """获取目标持仓"""
        # 防御性切换
        if (self.positive_count < self.p.min_positive_count or
                self.risk_manager.market_risk_level == 'high_risk'):
            if self.params.log_level > 0:
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
            if self.params.log_level > 0:
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

        if self.params.log_level > 0:
            self.log(f"目标持仓: {target_positions}")

        return target_positions

    def _get_signal_reason(self) -> str:
        """获取信号生成原因"""
        if (self.positive_count < self.p.min_positive_count or
                self.risk_manager.market_risk_level == 'high_risk'):
            return "市场高风险或优质ETF不足，切换防御模式"

        if not self.factor_scores:
            return "因子数据不足"

        return "因子得分更新，触发调仓"

    def calculate_indicators(self, data) -> Dict[str, Any]:
        """计算技术指标"""
        try:
            hist_data = self._get_historical_data(data, days=60)
            if hist_data is None or len(hist_data) < 30:
                return {}

            return self.factor_calculator.calculate_all_factors(hist_data)
        except Exception as e:
            self.log(f"计算指标失败: {e}", level=0)
            return {}

    def check_exit_conditions(self, symbol: str, data) -> Dict[str, Any]:
        """检查退出条件"""
        if symbol not in self.hold_cost or symbol not in self.data_dict:
            return {'exit': False, 'reason': ''}

        position = self.positions[data]
        if position.size <= 0:
            return {'exit': False, 'reason': ''}

        current_price = position.price
        cost_price = self.hold_cost[symbol]
        highest_price = self.hold_high.get(symbol, current_price)

        # 检查止损
        should_sell, reason = self.risk_manager.check_stop_loss(
            symbol, current_price, cost_price, highest_price
        )
        if should_sell:
            return {'exit': True, 'reason': f"止损: {reason}"}

        # 检查止盈
        should_reduce, new_ratio, reason = self.risk_manager.check_take_profit(
            symbol, current_price, cost_price, highest_price
        )
        if should_reduce:
            return {'exit': True, 'reason': f"止盈: {reason}", 'reduce_ratio': new_ratio}

        return {'exit': False, 'reason': ''}

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

        # 每周一计算因子值
        if current_weekday == self.p.rebalance_weekday:
            self._calculate_factors()

        # 生成信号
        signals = self.generate_signals()

        # 风控检查
        self._check_risk_controls()

        # 执行交易
        self._execute_trading(signals)

    def _check_risk_controls(self):
        """风控检查"""
        positions_to_sell = []
        positions_to_reduce = []

        for data, position in self.positions.items():
            if position.size <= 0:
                continue

            # 获取symbol
            symbol = self.data_to_symbol.get(data)
            if symbol is None or symbol not in self.hold_cost:
                continue

            current_price = position.price
            cost_price = self.hold_cost[symbol]
            highest_price = self.hold_high.get(symbol, current_price)

            # 检查退出条件
            exit_info = self.check_exit_conditions(symbol, data)
            if exit_info['exit']:
                if 'reduce_ratio' in exit_info:
                    positions_to_reduce.append((symbol, exit_info['reduce_ratio']))
                else:
                    positions_to_sell.append(symbol)
                self.log(f"风控退出: {symbol}, {exit_info['reason']}")

        # 执行退出
        for symbol in positions_to_sell:
            data = self.data_dict.get(symbol)
            if data:
                self.order_target_percent(data, 0)
                if symbol in self.hold_cost:
                    del self.hold_cost[symbol]
                if symbol in self.hold_high:
                    del self.hold_high[symbol]

        for symbol, ratio in positions_to_reduce:
            data = self.data_dict.get(symbol)
            if data:
                current_value = self.broker.getvalue()
                target_value = current_value * ratio
                self.order_target_value(data, target_value)

    def _execute_trading(self, signals: Dict[str, Any]):
        """执行交易"""
        if 'positions' not in signals:
            return

        # 检查是否需要调仓
        if not self._should_rebalance(signals):
            return

        target_positions = signals['positions']

        # 卖出不在目标列表的持仓
        for data, position in self.positions.items():
            if position.size > 0:
                # 获取symbol
                symbol = self.data_to_symbol.get(data)
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

    def _should_rebalance(self, signals: Dict[str, Any]) -> bool:
        """判断是否需要调仓"""
        current_weekday = self.datas[0].datetime.date(0).weekday()

        # 每周调仓日
        if current_weekday == self.p.rebalance_weekday:
            return True

        # 权重偏离超阈值时调仓
        if 'positions' in signals:
            for symbol, target_weight in signals['positions'].items():
                current_weight = self.get_position_weight(symbol)
                if abs(current_weight - target_weight) > self.p.rebalance_threshold:
                    return True

        return False
