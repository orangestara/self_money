"""
简短的策略测试

快速验证策略是否能正常运行
"""

import sys
import os
import pandas as pd
import numpy as np

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import backtrader as bt


def create_minimal_data(days=60):
    """创建最小测试数据"""
    dates = pd.date_range(start='2020-01-01', periods=days, freq='D')
    business_days = [d for d in dates if d.weekday() < 5]

    np.random.seed(42)
    prices = np.random.randn(len(business_days)).cumsum() + 100

    data = pd.DataFrame({
        'Open': prices * (1 + np.random.randn(len(prices)) * 0.001),
        'High': prices * (1 + np.abs(np.random.randn(len(prices))) * 0.01),
        'Low': prices * (1 - np.abs(np.random.randn(len(prices))) * 0.01),
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, len(prices)),
    }, index=business_days)

    return data


def test_strategy():
    """测试策略"""
    print("=" * 60)
    print("ETF轮动策略 - 快速测试")
    print("=" * 60)

    # 创建Cerebro
    cerebro = bt.Cerebro()

    # 添加策略
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from etf_rotation.strategy import ETFRotationStrategy
    cerebro.addstrategy(ETFRotationStrategy, log_level=1)

    # 添加数据
    symbols = ['159985.SZ', '518880.SS']
    for symbol in symbols:
        data = create_minimal_data(100)
        datafeed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(datafeed, name=symbol)
        print(f"✓ 添加数据: {symbol} ({len(data)} 条记录)")

    # 设置初始资金
    cerebro.broker.setcash(1000000)
    print(f"✓ 初始资金: 100万")

    # 运行
    print("\n开始回测...")
    print("-" * 60)

    try:
        results = cerebro.run()

        # 输出结果
        final_value = cerebro.broker.getvalue()
        total_return = (final_value / 1000000 - 1) * 100

        print("-" * 60)
        print(f"\n✓ 策略运行成功！")
        print(f"  最终资金: {final_value:,.2f}")
        print(f"  总收益率: {total_return:.2f}%")
        print("\n✓ 所有测试通过！")

    except Exception as e:
        print(f"\n✗ 策略运行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_strategy()
    exit(0 if success else 1)
