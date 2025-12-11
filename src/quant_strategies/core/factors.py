"""
因子计算模块

包含动量因子、质量因子等各类因子的计算方法
"""

import numpy as np
import pandas as pd
import math
from scipy.stats import linregress
from typing import Dict, Tuple
from .utils import (
    calculate_volume_ratio,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
)


class FactorCalculator:
    """因子计算器"""

    def __init__(self, params: Dict):
        """初始化参数"""
        self.momentum_window = params.get('momentum_window', 25)
        self.slope_window = params.get('slope_window', 20)
        self.ma_window = params.get('ma_window', 20)
        self.rsrs_window = params.get('rsrs_window', 20)
        self.volatility_window = params.get('volatility_window', 20)
        self.volume_short_window = params.get('volume_short_window', 5)
        self.volume_long_window = params.get('volume_long_window', 20)

        self.drop_threshold = params.get('drop_threshold', 0.05)
        self.volume_filter_threshold = params.get('volume_filter_threshold', 2.0)

    def calculate_all_factors(
        self, data: pd.DataFrame
    ) -> Dict:
        """计算所有因子"""
        try:
            close = data['close'].values
            high = data['high'].values
            low = data['low'].values
            volume = data['volume']

            # 成交量过滤
            vol_ratio = calculate_volume_ratio(volume, self.volume_short_window, self.volume_long_window)
            if vol_ratio > self.volume_filter_threshold:
                return {'composite': 0.0}

            # 跌幅过滤
            if len(close) >= 4:
                day1_return = close[-1] / close[-2] - 1
                day2_return = close[-2] / close[-3] - 1
                day3_return = close[-3] / close[-4] - 1
                if (day1_return < -self.drop_threshold or
                    day2_return < -self.drop_threshold or
                    day3_return < -self.drop_threshold or
                    (day1_return + day2_return + day3_return) < -0.1):
                    return {'composite': 0.0}

            # 1. 动量因子（年化收益和判定系数）
            momentum = self._calculate_momentum_factor(close)

            # 2. 质量因子（包含多个子因子）
            quality = self._calculate_quality_factor(close, high, low)

            # 3. 综合评分
            composite_score = momentum * quality

            return {
                'momentum': momentum,
                'quality': quality,
                'composite': composite_score,
                'vol_ratio': vol_ratio,
            }

        except Exception as e:
            print(f"计算因子失败: {e}")
            return {'composite': 0.0}

    def _calculate_momentum_factor(self, close: np.ndarray) -> float:
        """计算动量因子"""
        try:
            y = np.log(close)
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            annualized_returns = math.pow(math.exp(slope), 250) - 1
            ss_res = np.sum((y - (slope * x + intercept)) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / (ss_tot + 1e-8))
            momentum = annualized_returns * r_squared
            return momentum
        except:
            return 0.0

    def _calculate_quality_factor(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> float:
        """计算质量因子"""
        try:
            # 2.1 基础子因子
            # 斜率R²因子
            x_slope = np.arange(self.slope_window)
            y_slope = close[-self.slope_window:]
            slope, _, r_value, _, _ = linregress(x_slope, y_slope)
            slope_r2 = slope * (r_value ** 2)

            # 均线因子
            ma = np.mean(close[-self.ma_window:])
            ma_factor = 1 if close[-1] > ma else 0

            # RSRS因子
            beta_list = []
            for i in range(min(self.rsrs_window, 5)):
                h = high[-(self.rsrs_window - i)]
                l = low[-(self.rsrs_window - i)]
                s, _, r, _, _ = linregress([0, 1], [l, h])
                beta_list.append(s * r)
            rsrs = np.mean(beta_list)

            # 波动率因子
            returns_vol = np.diff(close[-self.volatility_window:]) / close[-self.volatility_window:-1]
            volatility = np.std(returns_vol) if len(returns_vol) > 0 else 0
            volatility_factor = 1 / (1 + volatility)

            # 2.2 新增抗回撤子因子
            # 最大回撤得分
            max_drawdown = calculate_max_drawdown(returns_vol)
            max_drawdown_score = 1 / (1 + abs(max_drawdown))

            # 夏普比率得分
            sharpe = calculate_sharpe_ratio(returns_vol)
            sharpe_score = max(0, sharpe)

            # 多周期均线因子
            ma10 = np.mean(close[-10:]) if len(close) >= 10 else ma
            multi_ma_factor = 1 if (close[-1] > ma10 and close[-1] > ma) else 0

            # 2.3 质量因子加权（7个子因子）
            quality = (
                0.15 * slope_r2 +
                0.15 * ma_factor +
                0.15 * rsrs +
                0.15 * volatility_factor +
                0.2 * max_drawdown_score +
                0.15 * sharpe_score +
                0.05 * multi_ma_factor
            )

            return quality

        except Exception as e:
            print(f"计算质量因子失败: {e}")
            return 0.0
