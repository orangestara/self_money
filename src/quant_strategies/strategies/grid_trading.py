"""
网格交易策略

基于价格区间网格的交易策略，适合震荡市场
策略特点：
1. 在指定价格区间内设置多个买卖网格点
2. 当价格触及网格线时自动执行交易
3. 适合震荡市场，通过频繁买卖获利
4. 支持动态调整网格参数
"""

from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from ..core.base_strategy import BaseStrategy


class GridTradingStrategy(BaseStrategy):
    """网格交易策略"""

    @property
    def strategy_name(self) -> str:
        return "网格交易策略"

    @property
    def strategy_description(self) -> str:
        return "基于价格区间的网格交易策略，适合震荡市场，通过在固定价格区间内设置买卖网格获利"

    # 默认参数
    params = (
        ('grid_count', 10),  # 网格数量
        ('grid_spacing', 0.02),  # 网格间距（百分比）
        ('price_range_pct', 0.2),  # 价格范围（当前价格的±百分比）
        ('rebalance_interval', 5),  # 调仓间隔（天）
        ('take_profit_threshold', 0.1),  # 止盈阈值
        ('stop_loss_threshold', 0.15),  # 止损阈值
        ('max_position_ratio', 0.3),  # 单个标的的最大仓位比例
        ('min_volume', 1000000),  # 最小成交量过滤
        ('log_level', 1),
    )

    def __init__(self, strategy_config: Dict[str, Any] = None):
        """初始化策略"""
        # 先初始化基类
        super().__init__(strategy_config)

        # 网格配置
        self.grid_levels = []  # 网格价格水平
        self.grid_positions = {}  # 每个网格的持仓 {price_level: position_size}
        self.current_grid_center = None  # 当前网格中心价格
        self.total_position_value = 0  # 总持仓价值
        self.unrealized_pnl = 0  # 未实现盈亏

        # 策略状态
        self.last_rebalance_day = 0  # 上次调仓日期
        self.price_history = []  # 价格历史
        self.trade_history = []  # 交易历史

        # 从配置更新参数
        if 'params' in self.strategy_config:
            for key, value in self.strategy_config['params'].items():
                setattr(self.p, key, value)

        # 初始化网格
        self._initialize_grid()

        # 日志
        self.log(f"网格交易策略初始化完成", level=1)
        self.log(f"网格数量: {self.p.grid_count}", level=1)
        self.log(f"网格间距: {self.p.grid_spacing:.2%}", level=1)
        self.log(f"价格范围: ±{self.p.price_range_pct:.2%}", level=1)

    def _initialize_grid(self):
        """初始化网格"""
        # 获取当前价格作为网格中心
        if len(self.data) > 0:
            current_price = self.data.close[0]
            self.current_grid_center = current_price

            # 计算价格范围
            price_range = self.p.price_range_pct
            min_price = current_price * (1 - price_range)
            max_price = current_price * (1 + price_range)

            # 创建网格水平
            self.grid_levels = np.linspace(min_price, max_price, self.p.grid_count)

            # 初始化网格持仓
            for price in self.grid_levels:
                self.grid_positions[price] = 0

            self.log(f"网格范围: {min_price:.2f} - {max_price:.2f}", level=2)

    def generate_signals(self) -> Dict[str, Any]:
        """生成买入/卖出信号"""
        signals = {}
        positions = {}

        # 获取当前价格
        current_price = self.data.close[0]
        self.price_history.append(current_price)

        # 检查是否需要重新调整网格
        if self._should_rebalance():
            self._rebalance_grid()

        # 生成交易信号
        for price_level, position_size in self.grid_positions.items():
            price_diff = current_price - price_level

            # 买入信号：价格接近或触及网格线
            if abs(price_diff) < current_price * self.p.grid_spacing * 0.5:
                if position_size < self.p.max_position_ratio:
                    signals[price_level] = {
                        'action': 'buy',
                        'target_weight': self.p.max_position_ratio,
                        'price_level': price_level,
                        'current_price': current_price,
                        'signal_strength': abs(price_diff) / current_price
                    }

            # 卖出信号：价格上涨到网格线上方
            elif price_diff > 0 and position_size > 0:
                signals[price_level] = {
                    'action': 'sell',
                    'target_weight': 0,
                    'price_level': price_level,
                    'current_price': current_price,
                    'signal_strength': price_diff / current_price
                }

        # 转换为持仓权重
        for symbol in self.data_dict.keys():
            # 计算该标的所有网格的总权重
            total_weight = sum(
                abs(pos) for pos in self.grid_positions.values()
            ) / len(self.data_dict)

            # 限制最大权重
            total_weight = min(total_weight, self.p.max_position_ratio)

            if total_weight > 0.01:  # 只在有权重变化时添加
                positions[symbol] = total_weight

        return {
            'signals': signals,
            'positions': positions,
            'reason': '网格交易信号生成'
        }

    def _should_rebalance(self) -> bool:
        """判断是否需要重新调整网格"""
        # 检查调仓间隔
        if len(self.data) - self.last_rebalance_day >= self.p.rebalance_interval:
            return True

        # 检查价格偏离
        if self.current_grid_center is None:
            return True

        current_price = self.data.close[0]
        price_deviation = abs(current_price - self.current_grid_center) / self.current_grid_center

        # 如果价格偏离超过20%，重新调整网格
        if price_deviation > 0.2:
            return True

        return False

    def _rebalance_grid(self):
        """重新调整网格"""
        current_price = self.data.close[0]
        self.current_grid_center = current_price

        # 重新计算价格范围
        price_range = self.p.price_range_pct
        min_price = current_price * (1 - price_range)
        max_price = current_price * (1 + price_range)

        # 重新创建网格水平
        new_grid_levels = np.linspace(min_price, max_price, self.p.grid_count)

        # 保留原有持仓（简化处理，实际应该重新分配）
        self.grid_levels = new_grid_levels
        self.last_rebalance_day = len(self.data)

        self.log(f"网格重新调整: {min_price:.2f} - {max_price:.2f}", level=2)

    def calculate_indicators(self, data) -> Dict[str, Any]:
        """计算技术指标"""
        try:
            # 获取历史数据
            hist_data = self._get_historical_data(data, days=30)
            if hist_data is None or len(hist_data) < 10:
                return {}

            close_prices = hist_data['close'].values

            # 计算指标
            indicators = {
                'price': close_prices[-1] if len(close_prices) > 0 else 0,
                'sma_5': np.mean(close_prices[-5:]) if len(close_prices) >= 5 else 0,
                'sma_20': np.mean(close_prices[-20:]) if len(close_prices) >= 20 else 0,
                'volatility': np.std(close_prices[-20:]) if len(close_prices) >= 20 else 0,
                'rsi': self._calculate_rsi(close_prices, 14),
                'grid_position': self._calculate_grid_position(close_prices[-1]),
                'grid_density': len([p for p in self.grid_positions.values() if p > 0]) / len(self.grid_positions)
            }

            return indicators

        except Exception as e:
            self.log(f"计算指标失败: {e}", level=0)
            return {}

    def _calculate_rsi(self, prices: np.ndarray, window: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < window + 1:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-window:])
        avg_loss = np.mean(losses[-window:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_grid_position(self, current_price: float) -> float:
        """计算当前价格在网格中的位置"""
        if self.grid_levels is None or len(self.grid_levels) == 0:
            return 0.5

        min_price = min(self.grid_levels)
        max_price = max(self.grid_levels)

        if max_price == min_price:
            return 0.5

        position = (current_price - min_price) / (max_price - min_price)
        return max(0, min(1, position))

    def check_exit_conditions(self, symbol: str, data) -> Dict[str, Any]:
        """检查退出条件"""
        if symbol not in self.data_dict:
            return {'exit': False, 'reason': ''}

        position = self.positions[data]
        if position.size <= 0:
            return {'exit': False, 'reason': ''}

        current_price = position.price
        market_price = self.data_dict[symbol].close[0]

        # 计算未实现盈亏
        unrealized_pnl_pct = (market_price - current_price) / current_price

        # 止盈检查
        if unrealized_pnl_pct >= self.p.take_profit_threshold:
            return {
                'exit': True,
                'reason': f"止盈: {unrealized_pnl_pct:.2%}",
                'exit_type': 'take_profit'
            }

        # 止损检查
        if unrealized_pnl_pct <= -self.p.stop_loss_threshold:
            return {
                'exit': True,
                'reason': f"止损: {unrealized_pnl_pct:.2%}",
                'exit_type': 'stop_loss'
            }

        return {'exit': False, 'reason': ''}

    def _get_historical_data(self, data, days=30):
        """获取历史数据"""
        try:
            hist = []
            for i in range(min(days, len(data))):
                ago = i  # 从当前bar往回ago个bar
                if ago >= len(data):
                    break
                hist.append({
                    'datetime': data.datetime.get(ago=-ago),
                    'Open': data.open.get(ago=-ago),
                    'High': data.high.get(ago=-ago),
                    'Low': data.low.get(ago=-ago),
                    'Close': data.close.get(ago=-ago),
                    'Volume': data.volume.get(ago=-ago),
                })

            if len(hist) < 5:
                return None

            df = pd.DataFrame(hist)
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
            return df

        except Exception as e:
            self.log(f"获取历史数据失败: {e}", level=0)
            return None

    def next(self):
        """主逻辑"""
        # 跳过初始数据不足的时期
        if len(self.data) < 10:
            return

        current_date = self.datas[0].datetime.date(0)
        current_weekday = current_date.weekday()

        # 生成信号
        signals = self.generate_signals()

        # 检查退出条件
        self._check_exit_conditions()

        # 执行交易
        self._execute_trading(signals)

        # 记录网格状态
        if current_weekday == 0:  # 每周一记录
            self._log_grid_status()

    def _check_exit_conditions(self):
        """检查所有持仓的退出条件"""
        positions_to_close = []

        for data, position in self.positions.items():
            if position.size <= 0:
                continue

            # 获取symbol
            symbol = None
            for sym, dat in self.data_dict.items():
                if dat is data:
                    symbol = sym
                    break

            if symbol is None:
                continue

            # 检查退出条件
            exit_info = self.check_exit_conditions(symbol, data)
            if exit_info.get('exit', False):
                positions_to_close.append((symbol, exit_info))

        # 执行退出
        for symbol, exit_info in positions_to_close:
            data = self.data_dict.get(symbol)
            if data:
                self.order_target_percent(data, 0)
                self.log(f"退出交易: {symbol}, {exit_info['reason']}", level=1)

    def _execute_trading(self, signals: Dict[str, Any]):
        """执行交易"""
        if 'positions' not in signals:
            return

        # 获取成交量过滤
        for symbol, target_weight in signals['positions'].items():
            if symbol not in self.data_dict:
                continue

            data = self.data_dict[symbol]

            # 成交量过滤
            current_volume = data.volume[0]
            if current_volume < self.p.min_volume:
                continue

            # 执行交易
            self.order_target_percent(data, target_weight)

    def _log_grid_status(self):
        """记录网格状态"""
        if len(self.grid_levels) == 0:
            return

        current_price = self.data.close[0]
        grid_position = self._calculate_grid_position(current_price)
        active_grids = len([p for p in self.grid_positions.values() if p > 0])

        self.log(f"网格状态 - 当前价格: {current_price:.2f}, "
                f"网格位置: {grid_position:.2%}, "
                f"活跃网格: {active_grids}/{len(self.grid_levels)}", level=2)

    def get_grid_stats(self) -> Dict[str, Any]:
        """获取网格统计信息"""
        if len(self.grid_levels) == 0:
            return {}

        current_price = self.data.close[0] if len(self.data) > 0 else 0

        return {
            'grid_count': len(self.grid_levels),
            'current_price': current_price,
            'grid_center': self.current_grid_center,
            'active_positions': len([p for p in self.grid_positions.values() if p > 0]),
            'total_position_value': self.total_position_value,
            'unrealized_pnl': self.unrealized_pnl,
            'grid_utilization': len([p for p in self.grid_positions.values() if p > 0]) / len(self.grid_levels)
        }

    def stop(self):
        """策略结束回调"""
        super().stop()

        # 输出网格统计
        stats = self.get_grid_stats()
        if stats:
            self.log(f"\n=== 网格统计 ===")
            self.log(f"网格数量: {stats['grid_count']}")
            self.log(f"当前价格: {stats['current_price']:.2f}")
            self.log(f"活跃仓位: {stats['active_positions']}")
            self.log(f"网格利用率: {stats['grid_utilization']:.2%}")
            self.log("=" * 50)
