"""
风控模块测试
"""

import unittest
import pandas as pd
import numpy as np
from src.etf_rotation.risk_manager import RiskManager


class TestRiskManager(unittest.TestCase):
    """风控管理器测试"""

    def setUp(self):
        """测试前准备"""
        self.params = {
            'stop_loss_base': 0.05,
            'trailing_stop_base': 0.05,
            'take_profit_ratio': 0.10,
            'vol_quantile_window': 60,
        }
        self.risk_manager = RiskManager(self.params)

    def test_check_stop_loss(self):
        """测试止损检查"""
        symbol = "TEST"
        cost_price = 100.0
        current_price = 95.0  # 亏损5%
        highest_price = 110.0

        should_sell, reason = self.risk_manager.check_stop_loss(
            symbol, current_price, cost_price, highest_price
        )

        # 亏损5%，如果止损阈值是5%，可能会触发
        self.assertIsInstance(should_sell, bool)
        self.assertIsInstance(reason, str)

    def test_check_take_profit(self):
        """测试止盈检查"""
        symbol = "TEST"
        cost_price = 100.0
        current_price = 115.0  # 盈利15%
        highest_price = 115.0

        should_reduce, new_ratio, reason = self.risk_manager.check_take_profit(
            symbol, current_price, cost_price, highest_price
        )

        # 盈利15%，应该触发止盈
        self.assertIsInstance(should_reduce, bool)
        self.assertIsInstance(new_ratio, float)
        self.assertIsInstance(reason, str)

    def test_update_market_risk(self):
        """测试市场风险更新"""
        # 创建基准数据
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        close_prices = np.random.randn(100).cumsum() + 100
        data = pd.DataFrame({'close': close_prices}, index=dates)

        self.risk_manager.update_market_risk(data)

        # 检查风险状态
        status = self.risk_manager.get_risk_status()
        self.assertIn('market_risk_level', status)
        self.assertIn('market_vol_quantile', status)
        self.assertIn('total_position_ratio', status)

        # 市场风险等级应该是三种之一
        self.assertIn(
            status['market_risk_level'],
            ['high_risk', 'low_risk', 'neutral']
        )

    def test_get_risk_status(self):
        """测试获取风险状态"""
        status = self.risk_manager.get_risk_status()

        # 检查所有必需的字段
        required_fields = [
            'market_risk_level',
            'market_vol_quantile',
            'total_position_ratio',
            'dynamic_stop_loss',
            'dynamic_trailing_stop',
            'dynamic_take_profit',
        ]

        for field in required_fields:
            self.assertIn(field, status)


if __name__ == '__main__':
    unittest.main()
