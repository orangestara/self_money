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
            # 使用tolist()转换为列表，然后转换为numpy数组
            close = np.array(data['Close'].tolist(), dtype=float)
            high = np.array(data['High'].tolist(), dtype=float)
            low = np.array(data['Low'].tolist(), dtype=float)
            volume = np.array(data['Volume'].tolist(), dtype=float)

            # 数据验证：检查是否有足够的有效数据
            if len(close) < 10:
                return {'composite': 0.0}

            # 过滤掉0值和NaN值
            valid_mask = (close > 0) & (~np.isnan(close)) & (~np.isinf(close))
            if not np.any(valid_mask) or np.sum(valid_mask) < 10:
                return {'composite': 0.0}

            close = close[valid_mask]
            high = high[valid_mask]
            low = low[valid_mask]
            volume = volume[valid_mask]

            # 成交量过滤
            vol_ratio = calculate_volume_ratio(volume, self.volume_short_window, self.volume_long_window)
            if vol_ratio > self.volume_filter_threshold:
                return {'composite': 0.0}

            # 跌幅过滤
            if len(close) >= 4:
                try:
                    # 安全计算收益率，避免除零
                    if close[-2] > 0:
                        day1_return = close[-1] / close[-2] - 1
                    else:
                        day1_return = 0.0

                    if close[-3] > 0:
                        day2_return = close[-2] / close[-3] - 1
                    else:
                        day2_return = 0.0

                    if close[-4] > 0:
                        day3_return = close[-3] / close[-4] - 1
                    else:
                        day3_return = 0.0

                    if (day1_return < -self.drop_threshold or
                        day2_return < -self.drop_threshold or
                        day3_return < -self.drop_threshold or
                        (day1_return + day2_return + day3_return) < -0.1):
                        return {'composite': 0.0}
                except Exception:
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
            # 确保所有价格都是正数
            if np.any(close <= 0):
                return 0.0

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
            if len(close) < self.slope_window:
                return 0.0
            x_slope = np.arange(self.slope_window)
            y_slope = close[-self.slope_window:]
            # 避免所有y值相同的情况
            if np.all(y_slope == y_slope[0]):
                slope_r2 = 0.0
            else:
                try:
                    slope, _, r_value, _, _ = linregress(x_slope, y_slope)
                    slope_r2 = slope * (r_value ** 2)
                except Exception:
                    slope_r2 = 0.0

            # 均线因子
            ma = np.mean(close[-self.ma_window:])
            ma_factor = 1 if close[-1] > ma else 0

            # RSRS因子
            beta_list = []
            for i in range(min(self.rsrs_window, 5)):
                h = high[-(self.rsrs_window - i)]
                l = low[-(self.rsrs_window - i)]
                # 避免l和h相同的情况
                if h != l:
                    try:
                        s, _, r, _, _ = linregress([0, 1], [l, h])
                        beta_list.append(s * r)
                    except Exception:
                        beta_list.append(0.0)
                else:
                    beta_list.append(0.0)
            rsrs = np.mean(beta_list) if beta_list else 0.0

            # 波动率因子
            close_window = close[-self.volatility_window:]
            if len(close_window) < 2:
                returns_vol = np.array([])
            else:
                try:
                    returns_vol = np.diff(close_window) / close_window[:-1]
                except Exception:
                    returns_vol = np.array([])
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
            import traceback
            traceback.print_exc()
            return 0.0
