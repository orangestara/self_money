"""
工具函数模块
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from scipy.stats import linregress


def calculate_volume_ratio(volumes: pd.Series, short_window: int = 5, long_window: int = 20) -> float:
    """计算成交量比率（短期/长期均量）"""
    if len(volumes) < long_window:
        return 1.0
    try:
        ma_short = volumes.rolling(short_window).mean().iloc[-1]
        ma_long = volumes.rolling(long_window).mean().iloc[-1]
        return ma_short / ma_long if ma_long > 0 else 1.0
    except:
        return 1.0


def calculate_market_vol_quantile(returns: pd.Series, window: int = 60) -> float:
    """计算市场波动率分位（0~1，1代表波动率最高）"""
    try:
        if len(returns) < 20:
            return 0.5

        # 计算当前年化波动率
        current_vol = returns.std() * np.sqrt(250)

        # 计算过去波动率滚动序列
        vol_rolling = returns.rolling(20).std() * np.sqrt(250)
        vol_rolling = vol_rolling.dropna()

        if len(vol_rolling) == 0:
            return 0.5

        # 计算分位
        vol_quantile = (vol_rolling <= current_vol).sum() / len(vol_rolling)
        return vol_quantile
    except Exception as e:
        print(f"计算市场波动率分位失败: {e}")
        return 0.5


def judge_market_trend(prices: pd.Series, vol_quantile: float) -> str:
    """判断市场趋势（高/中/低风险）"""
    try:
        if len(prices) < 60:
            return 'neutral'

        ma60 = prices.rolling(60).mean().iloc[-1]
        latest = prices.iloc[-1]

        # 高风险：跌破60日均线 + 波动率分位>0.8
        if latest < ma60 and vol_quantile > 0.8:
            return 'high_risk'
        # 低风险：站上60日均线 + 波动率分位<0.2
        elif latest > ma60 and vol_quantile < 0.2:
            return 'low_risk'
        # 中性：其他情况
        else:
            return 'neutral'
    except Exception as e:
        print(f"判断市场趋势失败: {e}")
        return 'neutral'


def calculate_max_drawdown(returns: np.ndarray) -> float:
    """计算最大回撤"""
    try:
        cum_returns = np.cumprod(1 + returns) - 1
        peak = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - peak) / (peak + 1e-8)
        return np.min(drawdown)
    except:
        return 0.0


def calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
    """计算夏普比率"""
    try:
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        excess_returns = np.mean(returns) * 250 - risk_free_rate
        volatility = np.std(returns) * np.sqrt(250)
        return excess_returns / volatility
    except:
        return 0.0


def score_based_weighting(scores: List[float]) -> np.ndarray:
    """基于综合得分的简单加权方法"""
    scores_array = np.array(scores)
    scores_array = np.clip(scores_array, a_min=0, a_max=None)

    if np.sum(scores_array) == 0:
        return np.ones(len(scores_array)) / len(scores_array)

    weights = scores_array / np.sum(scores_array)
    return weights


def simplified_epo_optimization(returns: pd.DataFrame, composite_scores: List[float]) -> np.ndarray:
    """简化版EPO优化"""
    n = len(composite_scores)

    if len(returns) < 10 or n < 2:
        weights = np.array(composite_scores)
        return weights / (np.sum(weights) + 1e-10)

    try:
        vcov = returns.cov()
        variances = np.diag(vcov)
        inv_variances = 1 / (variances + 1e-10)
        s = np.array(composite_scores)
        weights = s * inv_variances
        weights = np.maximum(0, weights)
        sum_weights = np.sum(weights)

        if sum_weights > 0:
            return weights / sum_weights
        else:
            return np.ones(n) / n
    except Exception as e:
        print(f"EPO优化失败: {e}，使用等权重")
        return np.ones(n) / n


def format_currency(value: float) -> str:
    """格式化货币显示"""
    if abs(value) >= 1e8:
        return f"{value/1e8:.2f}亿"
    elif abs(value) >= 1e4:
        return f"{value/1e4:.2f}万"
    else:
        return f"{value:.2f}"


def format_percentage(value: float) -> str:
    """格式化百分比显示"""
    return f"{value*100:.2f}%"
