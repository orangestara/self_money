#!/usr/bin/env python
"""
量化策略框架 - 统一执行入口

提供简单的命令行接口来运行各种功能：
- 运行策略回测
- 参数优化
- 生成信号
- 创建模拟数据
- 查看帮助
"""

import sys
import os
import argparse

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 尝试导入依赖，失败时提供友好提示
try:
    from quant_strategies import (
        load_config,
        create_backtest_engine,
        create_strategy_manager,
        create_parameter_search,
        GridSearch,
        RandomSearch,
        BayesianOptimization,
        format_currency,
        format_percentage,
        get_etf_list
    )
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print("⚠️  警告：缺少必要的依赖库")
    print(f"错误信息：{e}")
    print("\n请运行以下命令安装依赖：")
    print("  uv sync")
    print("  或")
    print("  pip install -r requirements.txt")
    print("\n注意：某些功能（如创建模拟数据）仍可使用。\n")
    DEPENDENCIES_AVAILABLE = False

    # 创建占位符，避免后续代码报错
    def dummy_func(*args, **kwargs):
        print("错误：依赖库未安装，无法执行此功能")
        return None

    load_config = dummy_func
    create_backtest_engine = dummy_func
    create_strategy_manager = dummy_func
    create_parameter_search = dummy_func
    GridSearch = dummy_func
    RandomSearch = dummy_func
    BayesianOptimization = dummy_func
    format_currency = lambda x: f"{x:,.2f}"
    format_percentage = lambda x: f"{x*100:.2f}%"
    get_etf_list = lambda config: []



def download_real_data():
    """从Tushare下载真实数据"""
    print("\n=== 从Tushare下载真实数据 ===\n")

    # 检查依赖
    try:
        import tushare as ts
        import pandas as pd
    except ImportError:
        print("⚠️  错误：缺少 tushare 库")
        print("请先安装依赖：")
        print("  uv sync")
        print("  或")
        print("  pip install tushare pandas")
        return

    # 运行数据下载脚本
    script_path = os.path.join('src', 'quant_strategies', 'core', 'data_fetcher.py')

    if os.path.exists(script_path):
        import subprocess
        print("正在从Tushare下载数据...")
        print("(注意：需要先配置TUSHARE_TOKEN环境变量)\n")
        result = subprocess.run([sys.executable, script_path], capture_output=False)
        if result.returncode == 0:
            print("\n✓ 数据下载完成！")
        else:
            print("\n❌ 数据下载失败，请检查错误信息")
    else:
        print(f"错误：找不到 {script_path}")


def create_demo_data():
    """创建模拟数据"""
    print("\n=== 创建模拟数据 ===\n")

    # 检查依赖
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        print("⚠️  错误：缺少 pandas 和 numpy 库")
        print("请先安装依赖：")
        print("  uv sync")
        print("  或")
        print("  pip install pandas numpy")
        return

    # 运行模拟数据创建脚本
    script_path = os.path.join('examples', 'run_with_demo_data.py')

    if os.path.exists(script_path):
        import subprocess
        subprocess.run([sys.executable, script_path])
    else:
        print(f"错误：找不到 {script_path}")


def run_etf_rotation():
    """运行ETF轮动策略"""
    print("\n=== 运行ETF轮动策略 ===\n")

    # 加载配置
    config = load_config()
    from quant_strategies import get_etf_list

    # 获取ETF列表
    etf_list_config = get_etf_list(config)
    etf_list = [etf['symbol'] for etf in etf_list_config][:5]  # 只取前5个

    # 加载数据
    print("加载数据...")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples'))
    from run_strategy import load_etf_data

    data_dict = load_etf_data(etf_list, data_dir='data')

    if not data_dict:
        print("\n⚠️  没有找到数据文件！")
        print("请先运行：python run.py --create-demo-data")
        return

    # 运行回测
    print("\n运行回测...")
    engine = create_backtest_engine()
    result = engine.run_backtest('etf_rotation', data_dict)

    if 'error' in result:
        print(f"\n❌ 回测失败: {result['error']}")
        return

    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"\n最终资金: {format_currency(result.get('final_value', 0) or 0)}")
    print(f"总收益: {format_currency((result.get('final_value', 0) or 0) - 1000000)}")
    print(f"总收益率: {format_percentage((result.get('total_return', 0) or 0) / 100)}")
    sharpe_ratio = result.get('sharpe_ratio', 0) or 0
    print(f"夏普比率: {sharpe_ratio:.2f}")
    max_drawdown = result.get('max_drawdown', 0) or 0
    print(f"最大回撤: {format_percentage(max_drawdown)}")
    print(f"交易次数: {result.get('total_trades', 0) or 0}")
    win_rate = result.get('win_rate', 0) or 0
    print(f"胜率: {win_rate:.2%}")
    print("\n✓ 结果已自动保存到 output/results/ 目录")


def run_grid_trading():
    """运行网格交易策略"""
    print("\n=== 运行网格交易策略 ===\n")

    # 加载配置
    config = load_config()
    from quant_strategies import get_etf_list

    # 获取ETF列表
    etf_list_config = get_etf_list(config)
    etf_list = [etf['symbol'] for etf in etf_list_config][:3]  # 只取前3个

    # 加载数据
    print("加载数据...")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples'))
    from run_strategy import load_etf_data

    data_dict = load_etf_data(etf_list, data_dir='data')

    if not data_dict:
        print("\n⚠️  没有找到数据文件！")
        print("请先运行：python run.py --create-demo-data")
        return

    # 运行回测
    print("\n运行回测...")
    engine = create_backtest_engine()
    result = engine.run_backtest('grid_trading', data_dict)

    if 'error' in result:
        print(f"\n❌ 回测失败: {result['error']}")
        return

    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"\n最终资金: {format_currency(result.get('final_value', 0) or 0)}")
    print(f"总收益: {format_currency((result.get('final_value', 0) or 0) - 1000000)}")
    print(f"总收益率: {format_percentage((result.get('total_return', 0) or 0) / 100)}")
    sharpe_ratio = result.get('sharpe_ratio', 0) or 0
    print(f"夏普比率: {sharpe_ratio:.2f}")
    max_drawdown = result.get('max_drawdown', 0) or 0
    print(f"最大回撤: {format_percentage(max_drawdown)}")
    print(f"交易次数: {result.get('total_trades', 0) or 0}")
    win_rate = result.get('win_rate', 0) or 0
    print(f"胜率: {win_rate:.2%}")
    print("\n✓ 结果已自动保存到 output/results/ 目录")


def run_parameter_optimization():
    """运行参数优化演示"""
    print("\n=== 运行参数优化演示 ===\n")

    # 运行参数优化脚本
    script_path = os.path.join('examples', 'parameter_optimization.py')

    if os.path.exists(script_path):
        import subprocess
        subprocess.run([sys.executable, script_path])
    else:
        print(f"错误：找不到 {script_path}")


def run_multi_strategy_demo():
    """运行多策略演示"""
    print("\n=== 运行多策略演示 ===\n")

    # 运行多策略演示脚本
    script_path = os.path.join('examples', 'multi_strategy_demo.py')

    if os.path.exists(script_path):
        import subprocess
        subprocess.run([sys.executable, script_path])
    else:
        print(f"错误：找不到 {script_path}")


def show_help():
    """显示帮助信息"""
    print("""
量化策略框架 v2.0 - 统一执行入口

用法:
  python run.py [命令]

命令:
  --help, -h              显示此帮助信息
  --create-demo-data      创建模拟数据（用于测试）
  --download-real-data    从Tushare下载真实数据
  --run-etf               运行ETF轮动策略
  --run-grid              运行网格交易策略
  --optimize-params       运行参数优化演示
  --demo-multi            运行多策略演示
  --all                   运行所有演示（创建数据 + ETF策略 + 网格策略）

示例:
  # 创建模拟数据
  python run.py --create-demo-data

  # 下载真实数据（需要配置Tushare Token）
  python run.py --download-real-data

  # 运行ETF轮动策略
  python run.py --run-etf

  # 运行网格交易策略
  python run.py --run-grid

  # 运行完整演示
  python run.py --all

注意:
  - 首次使用请先运行 --create-demo-data 创建模拟数据
  - 如需使用真实数据，请先配置Tushare Token，然后运行 --download-real-data
  - 所有结果会保存在 output/ 目录中
""")


def run_all():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("运行完整演示")
    print("=" * 60)

    # 1. 创建模拟数据
    create_demo_data()

    print("\n" + "=" * 60)

    # 2. 运行ETF轮动策略
    run_etf_rotation()

    print("\n" + "=" * 60)

    # 3. 运行网格交易策略
    run_grid_trading()

    print("\n" + "=" * 60)
    print("✓ 完整演示完成！")
    print("=" * 60)
    print("\n所有结果文件已保存到 output/ 目录")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='量化策略框架 v2.0 - 统一执行入口',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--create-demo-data', action='store_true',
                        help='创建模拟数据（用于测试）')
    parser.add_argument('--download-real-data', action='store_true',
                        help='从Tushare下载真实数据')
    parser.add_argument('--run-etf', action='store_true',
                        help='运行ETF轮动策略')
    parser.add_argument('--run-grid', action='store_true',
                        help='运行网格交易策略')
    parser.add_argument('--optimize-params', action='store_true',
                        help='运行参数优化演示')
    parser.add_argument('--demo-multi', action='store_true',
                        help='运行多策略演示')
    parser.add_argument('--all', action='store_true',
                        help='运行所有演示')

    args = parser.parse_args()

    # 如果没有参数，显示帮助
    if not any(vars(args).values()):
        show_help()
        return

    # 执行相应命令
    if args.create_demo_data:
        create_demo_data()

    if args.download_real_data:
        download_real_data()

    if args.run_etf:
        run_etf_rotation()

    if args.run_grid:
        run_grid_trading()

    if args.optimize_params:
        run_parameter_optimization()

    if args.demo_multi:
        run_multi_strategy_demo()

    if args.all:
        run_all()


if __name__ == '__main__':
    main()
