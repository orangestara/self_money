"""
ETF轮动策略运行示例

展示如何使用backtrader运行ETF轮动策略
数据源：tushare
支持多策略系统
"""

import backtrader as bt
import pandas as pd
import os
import sys

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 导入新架构
from etf_rotation import (
    create_backtest_engine,
    load_config,
    get_etf_list,
    get_backtest_params,
    format_currency,
    format_percentage
)

# 使用标准的PandasData


def load_etf_data(symbols, data_dir='../data'):
    """加载ETF数据（从CSV文件）"""
    all_data = {}

    for symbol in symbols:
        try:
            filepath = os.path.join(data_dir, f"{symbol}.csv")

            if not os.path.exists(filepath):
                print(f"数据文件不存在: {filepath}")
                continue

            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            # 确保列名为大写（tushare格式）
            data.columns = [col.title() for col in data.columns]
            all_data[symbol] = data
            print(f"加载 {symbol}: {len(data)} 条记录")

        except Exception as e:
            print(f"加载{symbol}失败: {e}")
            continue

    return all_data


def run_backtest(data_dict, start_date, end_date, initial_cash=1000000):
    """运行回测 - 使用新的回测引擎"""
    print("\n" + "=" * 60)
    print("开始运行ETF轮动策略回测")
    print("=" * 60)

    # 创建回测引擎
    engine = create_backtest_engine()

    # 运行回测
    print("\n使用新的多策略回测引擎...")
    result = engine.run_backtest('etf_rotation', data_dict)

    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)

    if 'error' in result:
        print(f"\n回测失败: {result['error']}")
        print("=" * 60)
        return

    print(f"\n最终资金: {format_currency(result.get('final_value', 0))}")
    print(f"总收益: {format_currency(result.get('final_value', 0) - initial_cash)}")
    print(f"总收益率: {format_percentage(result.get('total_return', 0) / 100)}")
    print(f"年化收益率: {format_percentage(result.get('annualized_return', 0))}")
    print(f"夏普比率: {result.get('sharpe_ratio', 0):.2f}")
    print(f"最大回撤: {format_percentage(result.get('max_drawdown', 0))}")
    print(f"交易次数: {result.get('total_trades', 0)}")
    print(f"胜率: {result.get('win_rate', 0):.2%}")

    # 结果已自动保存到output文件夹

    print("\n" + "=" * 60)


def main():
    """主函数"""
    # 读取配置
    config = load_config()

    # ETF列表（转换为tushare格式）
    etf_list_config = get_etf_list(config)
    etf_list = [etf['symbol'] for etf in etf_list_config]

    # 回测参数
    backtest_params = get_backtest_params(config)
    start_date = backtest_params['start_date']
    end_date = backtest_params['end_date']
    initial_cash = backtest_params['initial_cash']

    # 数据目录
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

    # 检查数据是否存在
    print("\n检查数据文件...")
    data_files_exist = all(
        os.path.exists(os.path.join(data_dir, f"{symbol}.csv"))
        for symbol in etf_list[:5]  # 只检查前5个
    )

    if not data_files_exist:
        print("\n⚠️  数据文件不存在")
        print("\n请先使用tushare下载数据:")
        print("\n1. 安装tushare (已包含在依赖中)")
        print("2. 注册tushare账号: https://tushare.pro/")
        print("3. 获取token并设置环境变量:")
        print("   export TUSHARE_TOKEN='你的token'")
        print("4. 运行数据下载:")
        print(f"   cd .. && python data_fetcher.py")
        print("\n或者使用模拟数据进行演示...")

        # 使用模拟数据进行演示
        create_sample_data(etf_list[:5], start_date, end_date, data_dir)
        return

    # 加载数据
    print("\n加载数据...")
    data_dict = load_etf_data(etf_list, data_dir)

    if not data_dict:
        print("没有可用的数据文件")
        return

    # 运行回测
    run_backtest(data_dict, start_date, end_date, initial_cash)

    # 提示多策略功能
    print("\n" + "=" * 60)
    print("多策略系统已启用！")
    print("=" * 60)
    print("\n您还可以尝试以下示例:")
    print("1. python quick_start_multi_strategy.py - 快速开始多策略系统")
    print("2. python multi_strategy_demo.py - 完整的多策略演示")
    print("\n更多功能:")
    print("- 多策略回测")
    print("- 买入信号生成")
    print("- 策略比较分析")
    print("=" * 60)


def create_sample_data(symbols, start_date, end_date, data_dir):
    """创建示例数据（模拟数据）"""
    import numpy as np

    os.makedirs(data_dir, exist_ok=True)

    print("\n创建模拟数据用于演示...")

    # 创建日期范围
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    # 只保留工作日
    business_days = [d for d in date_range if d.weekday() < 5]

    for symbol in symbols[:5]:  # 只创建前5个ETF的模拟数据
        try:
            # 生成随机游走数据
            n_days = len(business_days)
            returns = np.random.normal(0.0005, 0.02, n_days)  # 日均收益0.05%，波动2%

            # 累计计算价格
            prices = [100.0]  # 起始价格100
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))

            # 生成OHLC数据
            data = []
            for i, (date, close) in enumerate(zip(business_days, prices)):
                # 模拟日内波动
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

    print("\n模拟数据创建完成！请重新运行程序进行回测。")


if __name__ == "__main__":
    main()
