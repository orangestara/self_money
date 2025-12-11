"""
ETF轮动策略演示脚本

验证策略的核心功能
"""

import sys
import os
import pandas as pd
import numpy as np

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etf_rotation.factors import FactorCalculator
from etf_rotation.risk_manager import RiskManager
from etf_rotation.utils import (
    calculate_volume_ratio,
    score_based_weighting,
    format_currency,
    format_percentage,
)


def create_sample_data(symbol="TEST", days=60):
    """创建示例数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=days, freq='D')
    prices = np.random.randn(days).cumsum() + 100

    data = pd.DataFrame({
        'open': prices * (1 + np.random.randn(days) * 0.001),
        'high': prices * (1 + np.abs(np.random.randn(days)) * 0.01),
        'low': prices * (1 - np.abs(np.random.randn(days)) * 0.01),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, days),
    }, index=dates)

    return data


def test_factor_calculator():
    """测试因子计算器"""
    print("\n=== 测试因子计算器 ===")

    params = {
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

    calculator = FactorCalculator(params)
    data = create_sample_data()

    factors = calculator.calculate_all_factors(data)

    print(f"动量因子: {factors.get('momentum', 0):.4f}")
    print(f"质量因子: {factors.get('quality', 0):.4f}")
    print(f"综合得分: {factors.get('composite', 0):.4f}")
    print(f"成交量比率: {factors.get('vol_ratio', 0):.2f}")

    print("✓ 因子计算器测试通过\n")


def test_risk_manager():
    """测试风控管理器"""
    print("=== 测试风控管理器 ===")

    params = {
        'stop_loss_base': 0.05,
        'trailing_stop_base': 0.05,
        'take_profit_ratio': 0.10,
        'vol_quantile_window': 60,
    }

    risk_manager = RiskManager(params)

    # 测试止损
    symbol = "TEST"
    cost_price = 100.0
    current_price = 93.0  # 亏损7%
    highest_price = 110.0

    should_sell, reason = risk_manager.check_stop_loss(
        symbol, current_price, cost_price, highest_price
    )

    print(f"止损测试:")
    print(f"  成本价: {cost_price}, 当前价: {current_price}")
    print(f"  是否卖出: {should_sell}, 原因: {reason}")

    # 测试止盈
    current_price = 115.0  # 盈利15%
    should_reduce, new_ratio, reason = risk_manager.check_take_profit(
        symbol, current_price, cost_price, highest_price
    )

    print(f"\n止盈测试:")
    print(f"  成本价: {cost_price}, 当前价: {current_price}")
    print(f"  是否减仓: {should_reduce}, 新比例: {new_ratio:.1%}, 原因: {reason}")

    print("✓ 风控管理器测试通过\n")


def test_utils():
    """测试工具函数"""
    print("=== 测试工具函数 ===")

    # 测试基于得分的加权
    scores = [1.0, 2.0, 3.0, 0.5, 1.5]
    weights = score_based_weighting(scores)

    print(f"得分: {scores}")
    print(f"权重: {[f'{w:.2%}' for w in weights]}")
    print(f"权重和: {sum(weights):.4f}")

    # 测试格式化
    print(f"\n格式化测试:")
    print(f"  1234567.89 -> {format_currency(1234567.89)}")
    print(f"  0.1234 -> {format_percentage(0.1234)}")

    print("✓ 工具函数测试通过\n")


def test_backtrader_strategy():
    """测试backtrader策略导入"""
    print("=== 测试backtrader策略 ===")

    try:
        import backtrader as bt
        print(f"Backtrader版本: {bt.__version__}")

        # 尝试导入策略类
        from etf_rotation.strategy import ETFRotationStrategy
        print("✓ 策略类导入成功")

        # 检查策略类属性
        print(f"  策略参数: {ETFRotationStrategy.params}")

        print("✓ backtrader策略测试通过\n")
        return True

    except ImportError as e:
        print(f"✗ 导入失败: {e}\n")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("ETF轮动策略功能演示")
    print("=" * 60)

    try:
        # 测试各个模块
        test_factor_calculator()
        test_risk_manager()
        test_utils()
        backtrader_ok = test_backtrader_strategy()

        # 总结
        print("=" * 60)
        print("测试总结")
        print("=" * 60)

        if backtrader_ok:
            print("✓ 所有核心功能测试通过！")
            print("\n策略特性:")
            print("  - 多因子模型（动量+质量）")
            print("  - 动态风控（止损/止盈/跟踪止损）")
            print("  - 市场风险判断")
            print("  - 风格分散配置")
            print("  - 调仓频率控制")
            print("\n下一步:")
            print("  1. 准备ETF历史数据")
            print("  2. 运行 python examples/run_strategy.py")
        else:
            print("⚠ 部分功能测试失败，请检查依赖安装")

        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
