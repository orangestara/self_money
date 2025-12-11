"""
多策略演示

展示如何使用多策略系统进行回测和信号生成
"""

import sys
import os
import pandas as pd

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from quant_strategies import (
    create_strategy_manager,
    create_backtest_engine,
    create_signal_generator,
    load_config
)


def load_etf_data(symbols, data_dir='../data'):
    """加载ETF数据"""
    all_data = {}

    for symbol in symbols:
        try:
            filepath = os.path.join(data_dir, f"{symbol}.csv")

            if not os.path.exists(filepath):
                print(f"数据文件不存在: {filepath}")
                continue

            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            data.columns = [col.title() for col in data.columns]
            all_data[symbol] = data
            print(f"加载 {symbol}: {len(data)} 条记录")

        except Exception as e:
            print(f"加载{symbol}失败: {e}")
            continue

    return all_data


def create_sample_data(symbols, start_date, end_date, data_dir):
    """创建示例数据"""
    import numpy as np

    os.makedirs(data_dir, exist_ok=True)

    print("\n创建模拟数据用于演示...")

    # 创建日期范围
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    business_days = [d for d in date_range if d.weekday() < 5]

    for symbol in symbols[:5]:
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

            print(f"创建模拟数据: {symbol} ({len(df)} 条记录)")

        except Exception as e:
            print(f"创建{symbol}模拟数据失败: {e}")

    print("\n模拟数据创建完成！")


def demo_single_strategy():
    """演示单策略回测"""
    print("\n" + "=" * 60)
    print("演示1: 单策略回测")
    print("=" * 60)

    # 加载配置
    config = load_config()
    etf_list = config.get('etf_list', [])[:5]  # 只用前5个ETF
    symbols = [etf['symbol'] for etf in etf_list]

    # 数据目录
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

    # 检查数据
    print("\n检查数据文件...")
    data_files_exist = all(
        os.path.exists(os.path.join(data_dir, f"{symbol}.csv"))
        for symbol in symbols
    )

    if not data_files_exist:
        print("数据文件不存在，创建模拟数据...")
        create_sample_data(symbols, '2020-01-01', '2024-12-31', data_dir)

    # 加载数据
    print("\n加载数据...")
    data_dict = load_etf_data(symbols, data_dir)

    if not data_dict:
        print("没有可用的数据文件")
        return

    # 创建回测引擎
    engine = create_backtest_engine()

    # 运行ETF轮动策略
    print("\n运行ETF轮动策略...")
    result = engine.run_backtest('etf_rotation', data_dict)

    # 打印结果
    if 'error' not in result:
        print(f"\n回测结果:")
        print(f"  最终资金: {result.get('final_value', 0):,.2f}")
        print(f"  总收益率: {result.get('total_return', 0):.2f}%")
        print(f"  夏普比率: {result.get('sharpe_ratio', 0):.2f}")
        print(f"  最大回撤: {result.get('max_drawdown', 0):.2f}%")
        print(f"  交易次数: {result.get('total_trades', 0)}")


def demo_signal_generation():
    """演示信号生成"""
    print("\n" + "=" * 60)
    print("演示2: 买入信号生成")
    print("=" * 60)

    # 加载配置
    config = load_config()
    etf_list = config.get('etf_list', [])[:5]
    symbols = [etf['symbol'] for etf in etf_list]

    # 数据目录
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

    # 检查数据
    data_files_exist = all(
        os.path.exists(os.path.join(data_dir, f"{symbol}.csv"))
        for symbol in symbols
    )

    if not data_files_exist:
        print("数据文件不存在，创建模拟数据...")
        create_sample_data(symbols, '2024-01-01', '2024-12-31', data_dir)

    # 加载数据
    data_dict = load_etf_data(symbols, data_dir)

    if not data_dict:
        print("没有可用的数据文件")
        return

    # 创建策略管理器
    manager = create_strategy_manager()

    # 生成信号
    print("\n生成买入信号...")
    signals = manager.generate_signals('etf_rotation', data_dict)

    # 打印信号
    if 'signals' in signals:
        latest_signals = signals['signals']
        print(f"\n当前信号数量: {len(latest_signals)}")

        for symbol, signal_info in latest_signals.items():
            action = signal_info.get('action', 'hold')
            weight_change = signal_info.get('weight_change', 0)
            reason = signals.get('reason', '')

            if action != 'hold':
                print(f"\n{symbol}:")
                print(f"  动作: {action}")
                print(f"  权重变化: {weight_change:.2%}")
                print(f"  原因: {reason}")


def demo_strategy_manager():
    """演示策略管理器"""
    print("\n" + "=" * 60)
    print("演示3: 策略管理器")
    print("=" * 60)

    # 创建策略管理器
    manager = create_strategy_manager()

    # 列出所有策略
    print("\n已注册的策略:")
    strategies = manager.list_strategies()
    for name, info in strategies.items():
        status = "✓ 启用" if info.get('enabled', False) else "✗ 禁用"
        print(f"  - {name}: {info.get('description', '')} [{status}]")

    # 启用/禁用策略
    print("\n启用ETF轮动策略...")
    manager.enable_strategy('etf_rotation')

    # 打印策略摘要
    manager.print_strategy_summary()


def demo_strategy_factory():
    """演示策略工厂"""
    print("\n" + "=" * 60)
    print("演示4: 策略工厂")
    print("=" * 60)

    from quant_strategies import StrategyFactory

    # 创建工厂
    factory = StrategyFactory()

    # 列出策略
    print("\n可用的策略:")
    strategies = factory.list_strategies()
    for name, info in strategies.items():
        print(f"  - {name}: {info.get('description', '')}")

    # 创建策略实例
    print("\n创建ETF轮动策略实例...")
    strategy = factory.create_strategy('etf_rotation')

    if strategy:
        print(f"  策略名称: {strategy.strategy_name}")
        print(f"  策略描述: {strategy.strategy_description}")


def main():
    """主函数"""
    print("多策略系统演示")
    print("=" * 60)

    # 演示1: 单策略回测
    demo_single_strategy()

    # 演示2: 信号生成
    demo_signal_generation()

    # 演示3: 策略管理器
    demo_strategy_manager()

    # 演示4: 策略工厂
    demo_strategy_factory()

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
