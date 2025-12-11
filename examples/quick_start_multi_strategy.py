"""
快速开始 - 多策略系统

展示如何快速使用多策略系统进行策略回测和信号生成
"""

import sys
import os
import pandas as pd

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 导入核心模块
from quant_strategies import (
    create_backtest_engine,
    create_strategy_manager,
    create_signal_generator,
    load_config
)


def quick_start_example():
    """快速开始示例"""
    print("\n=== 快速开始示例 ===\n")

    # 步骤1: 加载配置
    print("1. 加载配置...")
    config = load_config()
    print(f"   ✓ 已加载 {len(config.get('etf_list', []))} 个ETF配置")

    # 步骤2: 创建回测引擎
    print("\n2. 创建回测引擎...")
    engine = create_backtest_engine()
    print("   ✓ 回测引擎创建成功")

    # 步骤3: 获取ETF列表
    print("\n3. 获取ETF列表...")
    etf_list = config.get('etf_list', [])[:3]  # 只用前3个
    symbols = [etf['symbol'] for etf in etf_list]
    print(f"   ✓ 准备回测的ETF: {symbols}")

    # 步骤4: 准备数据
    print("\n4. 准备数据...")
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

    # 创建模拟数据（实际使用时替换为真实数据）
    create_demo_data(symbols, data_dir)
    data_dict = load_demo_data(symbols, data_dir)
    print(f"   ✓ 已加载 {len(data_dict)} 个ETF数据")

    # 步骤5: 运行策略回测
    print("\n5. 运行策略回测...")
    result = engine.run_backtest('etf_rotation', data_dict)

    if 'error' not in result:
        print("\n   回测结果:")
        print(f"   - 最终资金: {result.get('final_value', 0):,.0f}")
        print(f"   - 总收益率: {result.get('total_return', 0):.2f}%")
        sharpe = result.get('sharpe_ratio', 0)
        if sharpe is not None:
            print(f"   - 夏普比率: {sharpe:.2f}")
        else:
            print(f"   - 夏普比率: N/A")
        print(f"   - 交易次数: {result.get('total_trades', 0)}")
    else:
        print(f"   ✗ 回测失败: {result['error']}")

    # 步骤6: 生成买入信号
    print("\n6. 生成买入信号...")
    manager = create_strategy_manager()
    signals = manager.generate_signals('etf_rotation', data_dict)

    if 'signals' in signals:
        buy_count = sum(1 for s in signals['signals'].values()
                       if s.get('action') == 'buy')
        sell_count = sum(1 for s in signals['signals'].values()
                        if s.get('action') == 'sell')

        print(f"   ✓ 买入信号: {buy_count} 个")
        print(f"   ✓ 卖出信号: {sell_count} 个")
        print(f"   ✓ 信号原因: {signals.get('reason', '')}")

    print("\n=== 示例完成 ===")


def create_demo_data(symbols, data_dir):
    """创建演示数据"""
    import numpy as np

    os.makedirs(data_dir, exist_ok=True)

    # 检查是否已有数据
    if all(os.path.exists(os.path.join(data_dir, f"{s}.csv")) for s in symbols):
        return

    print("   创建演示数据...")

    # 创建日期范围
    date_range = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    business_days = [d for d in date_range if d.weekday() < 5]

    for symbol in symbols:
        try:
            # 生成随机游走数据
            n_days = len(business_days)
            returns = np.random.normal(0.0005, 0.02, n_days)

            # 累计计算价格
            prices = [100.0]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))

            # 生成OHLC数据
            data = []
            for i, (date, close) in enumerate(zip(business_days, prices)):
                daily_vol = abs(np.random.normal(0, 0.01))
                high = close * (1 + daily_vol)
                low = close * (1 - daily_vol)
                open_price = prices[i-1] if i > 0 else close
                volume = np.random.randint(1000000, 10000000)

                data.append({
                    'Date': date,
                    'Open': open_price,
                    'High': high,
                    'Low': low,
                    'Close': close,
                    'Volume': volume,
                })

            df = pd.DataFrame(data)
            df.set_index('Date', inplace=True)

            # 保存数据
            filepath = os.path.join(data_dir, f"{symbol}.csv")
            df.to_csv(filepath)

        except Exception as e:
            print(f"   ✗ 创建{symbol}数据失败: {e}")


def load_demo_data(symbols, data_dir):
    """加载演示数据"""
    data_dict = {}

    for symbol in symbols:
        try:
            filepath = os.path.join(data_dir, f"{symbol}.csv")

            if not os.path.exists(filepath):
                continue

            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            data.columns = [col.title() for col in data.columns]
            data_dict[symbol] = data

        except Exception as e:
            print(f"   ✗ 加载{symbol}失败: {e}")

    return data_dict


def advanced_usage_example():
    """高级使用示例"""
    print("\n\n=== 高级使用示例 ===\n")

    # 使用策略管理器
    print("1. 使用策略管理器...")
    manager = create_strategy_manager()

    # 查看所有策略
    strategies = manager.list_strategies()
    print(f"   已注册策略: {list(strategies.keys())}")

    # 查看启用的策略
    enabled = manager.list_strategies(enabled_only=True)
    print(f"   启用策略: {list(enabled.keys())}")

    # 使用信号生成器
    print("\n2. 使用信号生成器...")
    generator = create_signal_generator()

    # 模拟策略信号
    strategy_signals = {
        '159985.SZ': {
            'signals': {
                '159985.SZ': {
                    'action': 'buy',
                    'current_weight': 0.0,
                    'target_weight': 0.3,
                    'weight_change': 0.3
                },
                '518880.SH': {
                    'action': 'sell',
                    'current_weight': 0.3,
                    'target_weight': 0.1,
                    'weight_change': -0.2
                }
            },
            'reason': '因子得分更新'
        }
    }

    signals = generator.generate_signals(strategy_signals)
    print(f"   生成信号数量: {len(signals)}")

    # 评估信号
    evaluation = generator.evaluate_signals(signals)
    print(f"   信号质量: {evaluation.get('signal_quality', 0):.2%}")

    # 使用回测引擎
    print("\n3. 使用回测引擎...")
    engine = create_backtest_engine()

    # 创建配置覆盖
    custom_config = {
        'params': {
            'max_holdings': 2,  # 最多持有2个标的
            'score_threshold': 0.1  # 提高得分阈值
        }
    }

    print("   ✓ 可通过config参数自定义策略参数")

    print("\n=== 高级示例完成 ===")


if __name__ == "__main__":
    # 运行快速开始示例
    quick_start_example()

    # 运行高级使用示例
    advanced_usage_example()

    print("\n\n更多详细信息请参考:")
    print("- examples/multi_strategy_demo.py (完整演示)")
    print("- README.md (项目说明)")
    print("- src/etf_rotation/ (源代码)")
