"""
工具函数测试
"""

import unittest
import pandas as pd
import numpy as np
from src.etf_rotation.utils import (
    calculate_volume_ratio,
    calculate_market_vol_quantile,
    judge_market_trend,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    score_based_weighting,
    format_currency,
    format_percentage,
)


class TestUtils(unittest.TestCase):
    """工具函数测试"""

    def test_calculate_volume_ratio(self):
        """测试成交量比率计算"""
        volumes = pd.Series([100, 110, 120, 130, 140, 150, 160, 170, 180, 190,
                            200, 210, 220, 230, 240, 250, 260, 270, 280, 290])

        ratio = calculate_volume_ratio(volumes, short_window=5, long_window=20)

        # 成交量比率应该是正数
        self.assertGreater(ratio, 0)

    def test_calculate_market_vol_quantile(self):
        """测试市场波动率分位计算"""
        # 创建收益率数据
        returns = pd.Series(np.random.randn(100) * 0.02)

        vol_quantile = calculate_market_vol_quantile(returns)

        # 分位值应该在0-1之间
        self.assertGreaterEqual(vol_quantile, 0)
        self.assertLessEqual(vol_quantile, 1)

    def test_judge_market_trend(self):
        """测试市场趋势判断"""
        # 创建上涨趋势的价格数据
        prices = pd.Series(np.cumsum(np.random.randn(100) * 0.01) + 100)

        trend = judge_market_trend(prices, vol_quantile=0.3)

        # 趋势应该是三种之一
        self.assertIn(trend, ['high_risk', 'low_risk', 'neutral'])

    def test_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        returns = np.array([0.01, 0.02, -0.05, 0.03, -0.02, 0.01])

        max_dd = calculate_max_drawdown(returns)

        # 最大回撤应该是负数
        self.assertLessEqual(max_dd, 0)

    def test_calculate_sharpe_ratio(self):
        """测试夏普比率计算"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01, 0.02])

        sharpe = calculate_sharpe_ratio(returns)

        # 夏普比率应该是数值
        self.assertIsInstance(sharpe, float)

    def test_score_based_weighting(self):
        """测试基于得分的加权"""
        scores = [1.0, 2.0, 3.0, 0.0, 1.5]

        weights = score_based_weighting(scores)

        # 权重和应该为1
        self.assertAlmostEqual(sum(weights), 1.0, places=5)

        # 所有权重应该为非负
        self.assertTrue(all(w >= 0 for w in weights))

        # 得分为0的项权重应该为0
        self.assertEqual(weights[3], 0)

    def test_format_currency(self):
        """测试货币格式化"""
        # 测试大额
        self.assertIn('亿', format_currency(100000000))

        # 测试中额
        self.assertIn('万', format_currency(50000))

        # 测试小额
        result = format_currency(1234.56)
        self.assertIn('1234', result)

    def test_format_percentage(self):
        """测试百分比格式化"""
        result = format_percentage(0.1234)

        # 应该包含百分号
        self.assertIn('%', result)

        # 数值应该正确
        self.assertIn('12.34', result)


if __name__ == '__main__':
    unittest.main()
