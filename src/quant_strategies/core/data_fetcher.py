#!/usr/bin/env python
"""
Tushare数据获取脚本

从tushare下载ETF数据并保存为CSV格式
自动从config.toml读取ETF列表和日期范围
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 添加源码路径
# 将src目录添加到Python路径，以便导入quant_strategies模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    import tushare as ts
    import pandas as pd
    from quant_strategies import load_config, get_etf_list, get_backtest_params, get_benchmark_symbol
except ImportError as e:
    print(f"❌ 错误：缺少必要的依赖库")
    print(f"   {e}")
    print("\n请运行以下命令安装依赖：")
    print("   uv sync")
    print("   或")
    print("   pip install tushare pandas")
    sys.exit(1)


class TushareDataFetcher:
    """Tushare数据获取器"""

    def __init__(self, token: Optional[str] = None):
        """初始化数据获取器

        Args:
            token: Tushare token，如果不提供则从环境变量或.env文件读取
        """
        self.token = token or self._get_token()
        if not self.token:
            raise ValueError(
                "❌ 未找到Tushare Token！\n"
                "请设置环境变量 TUSHARE_TOKEN 或在.env文件中配置\n"
                "获取Token: https://tushare.pro/"
            )

        # 初始化tushare
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        print(f"✓ Tushare初始化成功")

    def _get_token(self) -> Optional[str]:
        """从环境变量或.env文件读取token

        Returns:
            token字符串或None
        """
        # 优先级：环境变量 > .env文件
        token = os.getenv('TUSHARE_TOKEN')
        if token:
            return token

        # 尝试从.env文件读取
        # 从core目录找到项目根目录
        # data_fetcher.py: /src/quant_strategies/core/data_fetcher.py
        # 项目根目录: / (需要三级父目录)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        env_file = os.path.join(project_root, '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key.strip() == 'TUSHARE_TOKEN':
                            return value.strip().strip('"\'')
        return None

    def get_stock_basic(self, ts_code: str) -> Optional[Dict]:
        """获取股票基本信息

        Args:
            ts_code: 股票代码，如 '159985.SZ'

        Returns:
            基本信息字典或None
        """
        try:
            df = self.pro.stock_basic(
                ts_code=ts_code,
                fields='ts_code,symbol,name,area,industry,market,exchange,list_status'
            )
            if not df.empty:
                return df.iloc[0].to_dict()
            return None
        except Exception as e:
            print(f"   ⚠️  获取 {ts_code} 基本信息失败: {e}")
            return None

    def download_daily_data(self, ts_code: str, start_date: str, end_date: str, retry: int = 3) -> Optional[pd.DataFrame]:
        """下载ETF日线数据（使用fund_nav接口）

        Args:
            ts_code: ETF代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            retry: 重试次数

        Returns:
            DataFrame或None
        """
        for attempt in range(retry):
            try:
                # 转换日期格式
                start = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d')
                end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')

                print(f"   下载 {ts_code} ({start} 到 {end})...", end=' ')

                # 使用tushare获取ETF净值数据（注意：ETF使用fund_nav而不是daily）
                df = self.pro.fund_nav(
                    ts_code=ts_code,
                    start_date=start,
                    end_date=end
                )

                if df.empty:
                    print("⚠️  无数据")
                    return None

                # 处理数据
                df['nav_date'] = pd.to_datetime(df['nav_date'], format='%Y%m%d')
                df.set_index('nav_date', inplace=True)
                df.sort_index(inplace=True)

                # 转换列名为标准OHLC格式
                # fund_nav 返回: nav_date, ts_code, unit_nav, accum_nav, adj_nav等
                # 转换为: Date, Open, High, Low, Close, Volume
                standardized_df = pd.DataFrame(index=df.index)
                standardized_df['Open'] = df['unit_nav']  # 使用单位净值作为价格
                standardized_df['High'] = df['unit_nav']
                standardized_df['Low'] = df['unit_nav']
                standardized_df['Close'] = df['unit_nav']
                standardized_df['Volume'] = 0  # ETF没有交易量数据
                standardized_df['Amount'] = 0  # ETF没有成交额数据

                print(f"✓ {len(standardized_df)} 条记录")
                return standardized_df

            except Exception as e:
                if attempt < retry - 1:
                    print(f"⚠️  第{attempt+1}次尝试失败: {e}")
                    import time
                    time.sleep(1)
                else:
                    print(f"❌ 下载失败: {e}")
                    return None

    def download_benchmark_data(self, ts_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """下载基准指数数据（沪深300等）

        Args:
            ts_code: 指数代码，如 '000300.SH'
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame或None
        """
        try:
            print(f"\n下载基准指数数据: {ts_code}")

            # 转换日期格式
            start = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d')
            end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')

            # 使用tushare获取指数数据
            df = self.pro.index_daily(
                ts_code=ts_code,
                start_date=start,
                end_date=end
            )

            if df.empty:
                print(f"   ⚠️  基准指数 {ts_code} 无数据")
                return None

            # 处理数据
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df.set_index('trade_date', inplace=True)
            df.sort_index(inplace=True)

            # 标准化列名（指数数据没有pre_close等列）
            df = df[['open', 'high', 'low', 'close', 'vol']].copy()
            df.columns = [col.title() for col in df.columns]

            print(f"   ✓ 基准指数 {ts_code}: {len(df)} 条记录")
            return df

        except Exception as e:
            print(f"   ❌ 下载基准指数失败: {e}")
            return None

    def download_all_etfs(self, etf_list: List[Dict], start_date: str, end_date: str, data_dir: str = 'data') -> Dict[str, str]:
        """下载所有ETF数据

        Args:
            etf_list: ETF配置列表
            start_date: 开始日期
            end_date: 结束日期
            data_dir: 数据保存目录

        Returns:
            {symbol: filepath} 字典
        """
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)

        downloaded = {}
        failed = []

        print(f"\n开始下载 {len(etf_list)} 个ETF的数据...")
        print("=" * 60)

        for i, etf in enumerate(etf_list, 1):
            symbol = etf['symbol']
            name = etf.get('name', '')
            style = etf.get('style', '')

            print(f"\n[{i}/{len(etf_list)}] {symbol} - {name} ({style})")

            # 检查是否已存在数据文件
            filepath = os.path.join(data_dir, f"{symbol}.csv")
            if os.path.exists(filepath):
                try:
                    existing_df = pd.read_csv(filepath, index_col=0, parse_dates=True)
                    if len(existing_df) > 0:
                        last_date = existing_df.index.max()
                        first_date = existing_df.index.min()

                        # 如果数据覆盖了所需范围，跳过下载
                        required_start = datetime.strptime(start_date, '%Y-%m-%d')
                        required_end = datetime.strptime(end_date, '%Y-%m-%d')

                        if first_date <= required_start and last_date >= required_end:
                            print(f"   ✓ 数据已存在且完整 ({first_date.date()} 到 {last_date.date()})")
                            downloaded[symbol] = filepath
                            continue
                        else:
                            print(f"   ⚠️  数据不完整，存在数据: {first_date.date()} 到 {last_date.date()}")
                            print(f"       需要: {required_start.date()} 到 {required_end.date()}")
                except Exception as e:
                    print(f"   ⚠️  读取现有数据失败: {e}")

            # 下载数据
            df = self.download_daily_data(symbol, start_date, end_date)

            if df is not None and not df.empty:
                # 保存数据
                df.to_csv(filepath)
                downloaded[symbol] = filepath
                print(f"   ✓ 已保存到: {filepath}")
            else:
                failed.append(symbol)

        # 输出总结
        print("\n" + "=" * 60)
        print(f"下载完成:")
        print(f"   ✓ 成功: {len(downloaded)} 个")
        print(f"   ✗ 失败: {len(failed)} 个")

        if failed:
            print(f"\n失败的ETF: {', '.join(failed)}")

        return downloaded

    def download_benchmark(self, symbol: str, start_date: str, end_date: str, data_dir: str = 'data') -> Optional[str]:
        """下载基准指数数据

        Args:
            symbol: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            data_dir: 数据目录

        Returns:
            文件路径或None
        """
        os.makedirs(data_dir, exist_ok=True)

        filepath = os.path.join(data_dir, f"{symbol}.csv")

        # 检查是否已存在完整数据
        if os.path.exists(filepath):
            try:
                existing_df = pd.read_csv(filepath, index_col=0, parse_dates=True)
                if len(existing_df) > 0:
                    last_date = existing_df.index.max()
                    first_date = existing_df.index.min()

                    required_start = datetime.strptime(start_date, '%Y-%m-%d')
                    required_end = datetime.strptime(end_date, '%Y-%m-%d')

                    if first_date <= required_start and last_date >= required_end:
                        print(f"\n✓ 基准指数 {symbol} 数据已存在且完整")
                        return filepath

            except Exception as e:
                print(f"\n⚠️  读取现有基准数据失败: {e}")

        # 下载数据
        df = self.download_benchmark_data(symbol, start_date, end_date)

        if df is not None and not df.empty:
            df.to_csv(filepath)
            print(f"✓ 已保存到: {filepath}")
            return filepath

        return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='从Tushare下载ETF数据',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--start-date', type=str,
                        help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                        help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--benchmark-only', action='store_true',
                        help='仅下载基准指数数据')
    parser.add_argument('--check-only', action='store_true',
                        help='仅检查数据完整性，不下载')

    args = parser.parse_args()

    print("=" * 60)
    print("Tushare ETF数据下载工具")
    print("=" * 60)

    try:
        # 加载配置
        config = load_config()

        # 获取参数
        backtest_params = get_backtest_params(config)
        start_date = args.start_date or backtest_params['start_date']
        end_date = args.end_date or backtest_params['end_date']

        etf_list = get_etf_list(config)
        benchmark_symbol = get_benchmark_symbol(config)

        print(f"\n配置信息:")
        print(f"   开始日期: {start_date}")
        print(f"   结束日期: {end_date}")
        print(f"   ETF数量: {len(etf_list)}")
        print(f"   基准指数: {benchmark_symbol}")

        # 初始化数据获取器
        fetcher = TushareDataFetcher()

        if args.check_only:
            print("\n检查数据完整性...")
            # TODO: 实现数据完整性检查
            print("   (功能开发中)")
            return

        if args.benchmark_only:
            print("\n下载基准指数数据...")
            fetcher.download_benchmark(benchmark_symbol, start_date, end_date)
            return

        # 下载基准指数
        print(f"\n{'='*60}")
        fetcher.download_benchmark(benchmark_symbol, start_date, end_date)

        # 下载所有ETF
        print(f"\n{'='*60}")
        downloaded = fetcher.download_all_etfs(etf_list, start_date, end_date)

        # 输出总结
        print(f"\n{'='*60}")
        print("数据下载总结")
        print(f"{'='*60}")
        print(f"基准指数: {benchmark_symbol}")
        print(f"ETF总数: {len(etf_list)}")
        print(f"成功下载: {len(downloaded)}")
        print(f"数据目录: {os.path.abspath('data')}")
        print(f"\n✓ 所有数据已保存到 data/ 目录")
        print(f"✓ 现在可以运行策略回测")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
