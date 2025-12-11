"""
使用模拟数据运行ETF轮动策略演示

当没有真实数据时，可以使用此脚本生成模拟数据进行演示
"""

import sys
import os
import pandas as pd
import numpy as np

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from run_strategy import run_backtest


def create_demo_etf_data(symbols, start_date='2020-01-01', end_date='2024-12-31', data_dir='../data'):
    """创建模拟ETF数据用于演示"""
    os.makedirs(data_dir, exist_ok=True)

    print("\n=== 创建模拟ETF数据 ===\n")

    # 创建日期范围（只保留工作日）
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    business_days = [d for d in date_range if d.weekday() < 5]

    created_files = []

    for symbol in symbols:
        try:
            print(f"创建 {symbol} 的模拟数据...", end=" ")

            # 设置随机种子确保可重复性
            np.random.seed(hash(symbol) % 2**32)

            n_days = len(business_days)
            # 生成随机游走价格数据
            returns = np.random.normal(0.0005, 0.02, n_days)  # 日均收益0.05%，波动2%

            # 累计计算价格（从100开始）
            prices = [100.0]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))

            # 生成OHLC数据
            data_list = []
            for i, (date, close) in enumerate(zip(business_days, prices)):
                # 模拟日内波动
                daily_vol = abs(np.random.normal(0, 0.005))
                high = close * (1 + daily_vol)
                low = close * (1 - daily_vol)

                # 开盘价基于前一日收盘价
                if i == 0:
                    open_price = close
                else:
                    open_price = prices[i-1] * (1 + np.random.normal(0, 0.002))

                # 成交量
                volume = np.random.randint(1000000, 10000000)

                data_list.append({
                    'Date': date,
                    'Open': round(open_price, 2),
                    'High': round(high, 2),
                    'Low': round(low, 2),
                    'Close': round(close, 2),
                    'Volume': volume,
                })

            df = pd.DataFrame(data_list)
            df.set_index('Date', inplace=True)

            # 保存数据
            filepath = os.path.join(data_dir, f"{symbol}.csv")
            df.to_csv(filepath)
            created_files.append(filepath)

            print(f"✓ ({len(df)} 条记录)")

        except Exception as e:
            print(f"✗ 失败: {e}")

    print(f"\n✓ 模拟数据创建完成！")
    print(f"  数据目录: {data_dir}")
    print(f"  创建文件: {len(created_files)} 个")

    return created_files


def main():
    """主函数"""
    print("=" * 60)
    print("ETF轮动策略 - 模拟数据演示")
    print("=" * 60)
    print("\n此演示将：")
    print("1. 生成8个ETF的模拟历史数据")
    print("2. 运行策略回测")
    print("3. 显示回测结果")
    print("\n注意：这是模拟数据，仅用于验证策略逻辑")
    print("=" * 60)

    # ETF列表（tushare格式）
    etf_list = [
        '159985.SZ',  # 豆粕ETF
        '518880.SS',  # 黄金ETF
        '515220.SS',  # 煤炭ETF
        '513100.SS',  # 纳指ETF
        '513500.SS',  # 标普500ETF
        '512050.SS',  # A50ETF
        '159949.SZ',  # 创业板ETF
        '588000.SS',  # 科创50ETF
    ]

    # 创建模拟数据
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    create_demo_etf_data(etf_list, data_dir=data_dir)

    # 加载数据
    print("\n加载模拟数据...")
    from run_strategy import load_etf_data
    data_dict = load_etf_data(etf_list, data_dir)

    if not data_dict:
        print("✗ 数据加载失败")
        return

    # 运行回测
    print("\n开始回测...")
    print("-" * 60)

    run_backtest(
        data_dict=data_dict,
        start_date='2020-01-01',
        end_date='2024-12-31',
        initial_cash=1000000
    )

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 注册 tushare.pro 账号获取免费token")
    print("2. 设置环境变量: export TUSHARE_TOKEN='你的token'")
    print("3. 运行真实数据: python data_fetcher.py")
    print("4. 运行真实回测: python run_strategy.py")


if __name__ == "__main__":
    main()
