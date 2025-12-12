"""
风控模块

负责动态风控参数计算、止损止盈逻辑等
"""

import numpy as np
from typing import Dict, List, Tuple
from .utils import calculate_market_vol_quantile, judge_market_trend, format_percentage


class RiskManager:
    """风控管理器"""

    def __init__(self, params: Dict):
        """初始化风控参数"""
        self.stop_loss_base = params.get('stop_loss_base', 0.05)
        self.trailing_stop_base = params.get('trailing_stop_base', 0.05)
        self.take_profit_ratio = params.get('take_profit_ratio', 0.10)
        self.vol_quantile_window = params.get('vol_quantile_window', 60)

        # 动态风控参数（实时更新）
        self.dynamic_stop_loss = self.stop_loss_base
        self.dynamic_trailing_stop = self.trailing_stop_base
        self.dynamic_take_profit = self.take_profit_ratio

        # 市场风险相关
        self.market_risk_level = 'neutral'
        self.market_vol_quantile = 0.5
        self.total_position_ratio = 1.0

    def update_market_risk(self, benchmark_data) -> None:
        """更新市场风险状态"""
        try:
            benchmark_close = None

            # 检查数据类型并提取Close价格
            if hasattr(benchmark_data, 'columns'):
                # DataFrame情况
                if 'Close' in benchmark_data.columns:
                    benchmark_close = benchmark_data['Close']
                elif 'close' in benchmark_data.columns:
                    benchmark_close = benchmark_data['close']
                else:
                    raise ValueError("DataFrame中未找到Close或close列")
            elif hasattr(benchmark_data, 'get'):
                # 字典-like对象情况
                close_val = benchmark_data.get('Close')
                if close_val is not None:
                    benchmark_close = close_val
                else:
                    close_val = benchmark_data.get('close')
                    if close_val is not None:
                        benchmark_close = close_val
                    else:
                        raise ValueError("字典中未找到Close或close键")
            elif hasattr(benchmark_data, 'iloc'):
                # 已经是Series
                benchmark_close = benchmark_data
            else:
                raise ValueError(f"不支持的数据类型: {type(benchmark_data)}")

            # 确保是pandas Series
            if not hasattr(benchmark_close, 'iloc'):
                raise ValueError("提取的价格数据不是有效的pandas Series")

            # 清理数据：转换为数值类型并处理NaN
            if benchmark_close.dtype == 'object':
                # 如果是object类型，尝试转换为数值
                try:
                    benchmark_close = pd.to_numeric(benchmark_close, errors='coerce')
                except:
                    pass

            # 移除NaN值
            benchmark_close = benchmark_close.dropna()

            # 调试输出
            if hasattr(benchmark_close, 'iloc'):
                print(f"[DEBUG] 基准数据长度: {len(benchmark_close)}, 前5个值: {benchmark_close.iloc[:5].tolist()}")

            # 确保数据足够
            if len(benchmark_close) < 20:
                raise ValueError(f"有效价格数据不足: {len(benchmark_close)}")

            # 计算市场波动率分位
            returns = benchmark_close.pct_change().dropna()
            print(f"[DEBUG] 收益率长度: {len(returns)}, 前5个值: {returns.iloc[:5].tolist() if len(returns) > 0 else 'N/A'}")
            if len(returns) < 20:
                raise ValueError(f"收益率数据不足: {len(returns)}")

            self.market_vol_quantile = calculate_market_vol_quantile(returns, self.vol_quantile_window)

            # 动态调整风控参数
            self.dynamic_stop_loss = self.stop_loss_base * (1 + self.market_vol_quantile)
            self.dynamic_trailing_stop = self.trailing_stop_base * (1 + self.market_vol_quantile)
            self.dynamic_take_profit = self.take_profit_ratio * (1 - self.market_vol_quantile)

            # 判断市场风险等级
            self.market_risk_level = judge_market_trend(benchmark_close, self.market_vol_quantile)

            # 根据市场风险调整总仓位比例
            if self.market_risk_level == 'high_risk':
                self.total_position_ratio = 0.5  # 高风险降仓至50%
            elif self.market_risk_level == 'low_risk':
                self.total_position_ratio = 1.0  # 低风险满仓
            else:
                self.total_position_ratio = 0.8  # 中性市场80%仓位

        except Exception as e:
            print(f"更新市场风险失败: {e}")
            import traceback
            traceback.print_exc()
            # 使用默认值
            self.market_risk_level = 'neutral'
            self.total_position_ratio = 0.8
            self.market_vol_quantile = 0.5

    def check_stop_loss(
        self,
        symbol: str,
        current_price: float,
        cost_price: float,
        highest_price: float
    ) -> Tuple[bool, str]:
        """检查是否触发止损/止盈

        Returns:
            (should_sell, reason): 是否应该卖出及原因
        """
        try:
            # 成本止损
            loss_ratio = (current_price - cost_price) / cost_price
            if loss_ratio < -self.dynamic_stop_loss:
                return True, f"触发动态成本止损，亏损{format_percentage(loss_ratio)}"

            # 跟踪止损
            if highest_price > 0:
                drop_from_high = (current_price - highest_price) / highest_price
                if drop_from_high < -self.dynamic_trailing_stop:
                    return True, f"触发动态跟踪止损，回落{format_percentage(abs(drop_from_high))}"

            return False, ""

        except Exception as e:
            print(f"检查止损失败: {e}")
            return False, ""

    def check_take_profit(
        self,
        symbol: str,
        current_price: float,
        cost_price: float,
        highest_price: float
    ) -> Tuple[bool, float, str]:
        """检查是否触发止盈

        Returns:
            (should_reduce, new_position_ratio, reason): 是否应该减仓及新仓位比例
        """
        try:
            profit_ratio = (current_price - cost_price) / cost_price

            if profit_ratio > self.dynamic_take_profit:
                # 减半仓位
                return True, 0.5, f"触发动态止盈，盈利{format_percentage(profit_ratio)}"

            return False, 1.0, ""

        except Exception as e:
            print(f"检查止盈失败: {e}")
            return False, 1.0, ""

    def get_risk_status(self) -> Dict:
        """获取当前风险状态"""
        return {
            'market_risk_level': self.market_risk_level,
            'market_vol_quantile': self.market_vol_quantile,
            'total_position_ratio': self.total_position_ratio,
            'dynamic_stop_loss': self.dynamic_stop_loss,
            'dynamic_trailing_stop': self.dynamic_trailing_stop,
            'dynamic_take_profit': self.dynamic_take_profit,
        }

    def print_risk_status(self) -> None:
        """打印当前风险状态"""
        status = self.get_risk_status()
        print(f"\n=== 风险状态 ===")
        print(f"市场风险等级: {status['market_risk_level']}")
        print(f"市场波动率分位: {status['market_vol_quantile']:.2f}")
        print(f"总仓位比例: {status['total_position_ratio']:.0%}")
        print(f"动态止损: {status['dynamic_stop_loss']:.1%}")
        print(f"动态跟踪止损: {status['dynamic_trailing_stop']:.1%}")
        print(f"动态止盈: {status['dynamic_take_profit']:.1%}")
        print("================\n")
