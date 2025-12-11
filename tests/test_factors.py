"""
因子计算模块测试
"""

import unittest
import numpy as np
import pandas as pd
from src.etf_rotation.factors import FactorCalculator


class TestFactorCalculator(unittest.TestCase):
    """因子计算器测试"""

    def setUp(self):
        """测试前准备"""
        self.params = {
            'momentum_window': 25,
            'slope_window': 20,
            'ma_window': 20,
            'rsrs_window': 20,
            'volatility_window': 20,
            'volume_short_window': 5,
            'volume_long_window': 20,
            'drop_threshold': 0.05,
            'volume_filter_threshold': 2.0,
        }
        self.calculator = FactorCalculator(self.params)

    def test_calculate_momentum_factor(self):
        """测试动量因子计算"""
        # 创建测试数据
        close = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        momentum = self.calculator._calculate_momentum_factor(close)

        # 动量因子应该为正（上升趋势）
        self.assertGreater(momentum, 0)

    def test_calculate_quality_factor(self):
        """测试质量因子计算"""
        # 创建测试数据
        close = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                         110, 111, 112, 113, 114, 115, 116, 117, 118, 119])
        high = close * 1.01
        low = close * 0.99

        quality = self.calculator._calculate_quality_factor(close, high, low)

        # 质量因子应该在0-1之间
        self.assertGreaterEqual(quality, 0)
        self.assertLessEqual(quality, 1)

    def test_calculate_all_factors(self):
        """测试所有因子计算"""
        # 创建完整的测试数据
        dates = pd.date_range(start='2020-01-01', periods=60, freq='D')
        data = pd.DataFrame({
            'close': np.random.randn(60).cumsum() + 100,
            'high': np.random.randn(60).cumsum() + 102,
            'low': np.random.randn(60).cumsum() + 98,
            'volume': np.random.randint(1000000, 10000000, 60),
        }, index=dates)

        factors = self.calculator.calculate_all_factors(data)

        # 检查返回结果
        self.assertIn('composite', factors)
        self.assertIn('momentum', factors)
        self.assertIn('quality', factors)

        # 综合得分应该在合理范围内
        self.assertIsInstance(factors['composite'], float)


if __name__ == '__main__':
    unittest.main()
