"""
参数优化示例

展示如何使用参数搜索功能优化策略参数
支持网格搜索、随机搜索和贝叶斯优化
"""

import sys
import os
import pandas as pd
import numpy as np

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from quant_strategies import (
    load_config,
    create_backtest_engine,
    create_parameter_search,
    GridSearch,
    RandomSearch,
    BayesianOptimization,
    ETFRotationStrategy,
    GridTradingStrategy
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


def create_demo_data(symbols, data_dir):
    """创建演示数据"""
    os.makedirs(data_dir, exist_ok=True)

    # 检查是否已有数据
    if all(os.path.exists(os.path.join(data_dir, f"{s}.csv")) for s in symbols):
        return

    print("创建演示数据...")

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
            print(f"创建{symbol}数据失败: {e}")


def demo_grid_search():
    """演示网格搜索"""
    print("\n" + "=" * 60)
    print("演示1: 网格搜索优化网格交易策略参数")
    print("=" * 60)

    # 加载配置和数据
    config = load_config()
    etf_list = config.get('etf_list', [])[:3]
    symbols = [etf['symbol'] for etf in etf_list]

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    create_demo_data(symbols, data_dir)
    data_dict = load_etf_data(symbols, data_dir)

    if not data_dict:
        print("没有可用的数据")
        return

    # 定义参数空间（网格搜索）
    param_space = {
        'grid_count': [5, 10, 15],
        'grid_spacing': [0.01, 0.02, 0.03],
        'price_range_pct': [0.15, 0.2, 0.25],
        'take_profit_threshold': [0.08, 0.1, 0.12],
        'stop_loss_threshold': [0.12, 0.15, 0.18]
    }

    print(f"\n参数空间:")
    for param, values in param_space.items():
        print(f"  {param}: {values}")

    # 创建目标函数
    def objective_func(params):
        """目标函数：运行网格交易策略回测"""
        try:
            engine = create_backtest_engine()
            # 使用策略管理器运行回测
            manager = create_strategy_manager()
            result = manager.run_single_strategy(
                strategy_name='grid_trading',
                data_dict=data_dict,
                start_date='2023-01-01',
                end_date='2024-12-31',
                initial_cash=1000000,
                config={'params': params}
            )

            if 'error' in result:
                return -np.inf

            # 返回总收益率
            return result.get('total_return', 0)

        except Exception as e:
            print(f"回测失败: {e}")
            return -np.inf

    # 执行网格搜索
    print("\n开始网格搜索...")
    searcher = GridSearch(
        objective_func=objective_func,
        param_space=param_space,
        maximize=True,
        n_jobs=1  # 网格搜索通常不使用并行
    )

    results = searcher.search()

    # 输出结果
    print(f"\n网格搜索结果:")
    print(f"最佳参数: {results['best_params']}")
    print(f"最佳分数: {results['best_score']:.2f}%")

    # 结果已自动保存到output文件夹


def demo_random_search():
    """演示随机搜索"""
    print("\n" + "=" * 60)
    print("演示2: 随机搜索优化ETF轮动策略参数")
    print("=" * 60)

    # 加载配置和数据
    config = load_config()
    etf_list = config.get('etf_list', [])[:3]
    symbols = [etf['symbol'] for etf in etf_list]

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    create_demo_data(symbols, data_dir)
    data_dict = load_etf_data(symbols, data_dir)

    if not data_dict:
        print("没有可用的数据")
        return

    # 定义参数空间（随机搜索）
    param_space = {
        'max_holdings': [2, 3, 4, 5],
        'score_threshold': [-0.1, 0, 0.1, 0.2],
        'min_positive_count': [5, 7, 10, 12]
    }

    print(f"\n参数空间:")
    for param, values in param_space.items():
        print(f"  {param}: {values}")

    # 创建目标函数
    def objective_func(params):
        """目标函数：运行ETF轮动策略回测"""
        try:
            engine = create_backtest_engine()
            result = engine.run_single_strategy(
                strategy_name='etf_rotation',
                data_dict=data_dict,
                start_date='2023-01-01',
                end_date='2024-12-31',
                config={'params': params}
            )

            if 'error' in result:
                return -np.inf

            # 返回夏普比率
            sharpe = result.get('sharpe_ratio', 0)
            return sharpe if sharpe is not None else 0

        except Exception as e:
            print(f"回测失败: {e}")
            return -np.inf

    # 执行随机搜索
    print("\n开始随机搜索（50次迭代）...")
    searcher = RandomSearch(
        objective_func=objective_func,
        param_space=param_space,
        maximize=True,
        n_jobs=1,
        seed=42
    )

    results = searcher.search(n_iterations=50)

    # 输出结果
    print(f"\n随机搜索结果:")
    print(f"最佳参数: {results['best_params']}")
    print(f"最佳分数（夏普比率）: {results['best_score']:.4f}")

    # 结果已自动保存到output文件夹

    # 显示结果分布
    df = searcher.get_results_dataframe()
    if not df.empty:
        print(f"\n结果统计:")
        print(f"平均分数: {df['score'].mean():.4f}")
        print(f"分数标准差: {df['score'].std():.4f}")
        print(f"最高分数: {df['score'].max():.4f}")
        print(f"最低分数: {df['score'].min():.4f}")


def demo_bayesian_optimization():
    """演示贝叶斯优化"""
    print("\n" + "=" * 60)
    print("演示3: 贝叶斯优化网格策略参数")
    print("=" * 60)

    # 加载配置和数据
    config = load_config()
    etf_list = config.get('etf_list', [])[:2]  # 减少数据量以加快速度
    symbols = [etf['symbol'] for etf in etf_list]

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    create_demo_data(symbols, data_dir)
    data_dict = load_etf_data(symbols, data_dir)

    if not data_dict:
        print("没有可用的数据")
        return

    # 定义参数空间（贝叶斯优化）
    param_space = {
        'grid_count': [8, 10, 12],
        'grid_spacing': [0.015, 0.02, 0.025],
        'price_range_pct': [0.18, 0.2, 0.22]
    }

    print(f"\n参数空间:")
    for param, values in param_space.items():
        print(f"  {param}: {values}")

    # 创建目标函数
    def objective_func(params):
        """目标函数：运行网格交易策略回测"""
        try:
            engine = create_backtest_engine()
            result = engine.run_single_strategy(
                strategy_name='grid_trading',
                data_dict=data_dict,
                start_date='2023-06-01',
                end_date='2024-12-31',  # 缩短回测期间
                config={'params': params}
            )

            if 'error' in result:
                return -np.inf

            # 返回风险调整后收益（夏普比率）
            sharpe = result.get('sharpe_ratio', 0)
            return sharpe if sharpe is not None else 0

        except Exception as e:
            return -np.inf

    # 执行贝叶斯优化
    print("\n开始贝叶斯优化（初始点10个，总迭代30次）...")
    searcher = BayesianOptimization(
        objective_func=objective_func,
        param_space=param_space,
        maximize=True,
        n_jobs=1
    )

    results = searcher.search(n_iterations=30, n_initial_points=10)

    # 输出结果
    print(f"\n贝叶斯优化结果:")
    print(f"最佳参数: {results['best_params']}")
    print(f"最佳分数（夏普比率）: {results['best_score']:.4f}")

    # 结果已自动保存到output文件夹


def demo_comparison():
    """演示不同搜索方法的比较"""
    print("\n" + "=" * 60)
    print("演示4: 比较不同搜索方法")
    print("=" * 60)

    # 定义相同的参数空间
    param_space = {
        'grid_count': [8, 10, 12],
        'grid_spacing': [0.015, 0.02, 0.025],
        'take_profit_threshold': [0.08, 0.1, 0.12]
    }

    print(f"\n参数空间: {param_space}")

    # 模拟数据
    config = load_config()
    etf_list = config.get('etf_list', [])[:2]
    symbols = [etf['symbol'] for etf in etf_list]

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    create_demo_data(symbols, data_dir)
    data_dict = load_etf_data(symbols, data_dir)

    if not data_dict:
        print("没有可用的数据")
        return

    # 目标函数
    def objective_func(params):
        try:
            engine = create_backtest_engine()
            result = engine.run_single_strategy(
                strategy_name='grid_trading',
                data_dict=data_dict,
                start_date='2023-06-01',
                end_date='2024-12-31',
                config={'params': params}
            )
            return result.get('total_return', 0) if 'error' not in result else -np.inf
        except:
            return -np.inf

    # 比较不同方法
    methods = [
        ('Grid Search', GridSearch(objective_func, param_space, maximize=True)),
        ('Random Search (20 iters)', RandomSearch(objective_func, param_space, maximize=True, seed=42)),
    ]

    print("\n开始比较...")
    comparison_results = {}

    for name, searcher in methods:
        print(f"\n运行 {name}...")
        if 'Grid' in name:
            results = searcher.search()
        else:
            results = searcher.search(n_iterations=20)

        comparison_results[name] = {
            'best_score': results['best_score'],
            'best_params': results['best_params'],
            'n_evaluations': len(searcher.results)
        }

    # 输出比较结果
    print("\n" + "=" * 60)
    print("比较结果")
    print("=" * 60)

    for name, result in comparison_results.items():
        print(f"\n{name}:")
        print(f"  评估次数: {result['n_evaluations']}")
        print(f"  最佳分数: {result['best_score']:.2f}")
        print(f"  最佳参数: {result['best_params']}")


def main():
    """主函数"""
    print("参数优化演示")
    print("=" * 60)

    # 演示1: 网格搜索
    demo_grid_search()

    # 演示2: 随机搜索
    demo_random_search()

    # 演示3: 贝叶斯优化
    demo_bayesian_optimization()

    # 演示4: 方法比较
    demo_comparison()

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)
    print("\n结果文件已保存:")
    print("- grid_search_results.json")
    print("- random_search_results.json")
    print("- bayesian_optimization_results.json")


if __name__ == "__main__":
    main()
