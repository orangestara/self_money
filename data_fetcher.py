"""
使用tushare下载ETF数据

tushare是一个免费的开源财经数据接口包
官网：https://tushare.pro/
注册账号后可以免费获取token

使用.env文件管理敏感配置：
1. 复制 .env.example 为 .env
2. 在 .env 中设置 TUSHARE_TOKEN=your_token
3. 确保 .env 不被提交到Git（已在.gitignore中忽略）
"""

import tushare as ts
import pandas as pd
import os
import sys
from datetime import datetime
import time

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etf_rotation.env_loader import get_tushare_token


class TushareDataFetcher:
    """tushare数据获取器"""

    def __init__(self, token=None):
        """初始化

        Args:
            token: tushare的访问令牌，如果没有则依次尝试：
                   1. 系统环境变量 TUSHARE_TOKEN
                   2. .env文件中的 TUSHARE_TOKEN
                   3. 抛出错误提示
        """
        if token is None:
            token = get_tushare_token()

        if token is None:
            raise ValueError(
                "请设置tushare token:\n"
                "1. 访问 https://tushare.pro/ 注册账号\n"
                "2. 获取token\n"
                "3. 创建 .env 文件（复制 .env.example）\n"
                "4. 在 .env 中设置: TUSHARE_TOKEN='your_token'\n"
                "   或设置系统环境变量: export TUSHARE_TOKEN='your_token'\n"
                "   或在代码中传入: TushareDataFetcher(token='your_token')"
            )

        ts.set_token(token)
        self.pro = ts.pro_api()

    def get_stock_basic(self):
        """获取股票基本信息"""
        try:
            # 获取ETF列表
            df = self.pro.fund_basic(market='E')
            return df
        except Exception as e:
            print(f"获取ETF基本信息失败: {e}")
            return None

    def download_etf_data(self, ts_code, start_date, end_date, data_dir='data'):
        """下载单个ETF的历史数据

        Args:
            ts_code: tushare格式的代码，如 '159985.SZ'
            start_date: 开始日期，格式 '20200101'
            end_date: 结束日期，格式 '20241231'
            data_dir: 数据保存目录
        """
        try:
            print(f"正在下载 {ts_code}...")

            # 尝试不同的数据获取方法
            df = None

            # 方法1: 尝试 fund_daily (基金日线数据)
            try:
                df = self.pro.fund_daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
                if df is not None and not df.empty:
                    print(f"  ✓ 使用 fund_daily 获取到 {len(df)} 条记录")
            except Exception as e:
                print(f"  ⚠️  fund_daily 失败: {str(e)[:50]}")
                df = None

            # 方法2: 如果 fund_daily 失败，尝试 index_daily (指数日线数据)
            if df is None or df.empty:
                try:
                    df = self.pro.index_daily(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                    if df is not None and not df.empty:
                        print(f"  ✓ 使用 index_daily 获取到 {len(df)} 条记录")
                except Exception as e:
                    print(f"  ⚠️  index_daily 失败: {str(e)[:50]}")
                    df = None

            # 方法3: 如果都失败，尝试 daily (通用日线数据)
            if df is None or df.empty:
                try:
                    df = self.pro.daily(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                    if df is not None and not df.empty:
                        print(f"  ✓ 使用 daily 获取到 {len(df)} 条记录")
                except Exception as e:
                    print(f"  ⚠️  daily 失败: {str(e)[:50]}")
                    df = None

            if df is None or df.empty:
                print(f"  ❌ 所有方法都失败，{ts_code} 无数据")
                return None

            # 按日期排序
            df = df.sort_values('trade_date')
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df.set_index('trade_date', inplace=True)

            # 重命名列（兼容不同的数据格式）
            rename_dict = {
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'vol': 'Volume',
                'amount': 'Amount'
            }
            # 只重命名存在的列
            for old_col, new_col in rename_dict.items():
                if old_col in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)

            # 确保有必要的列
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"  ⚠️  缺少列: {missing_cols}")

            # 保存数据
            os.makedirs(data_dir, exist_ok=True)
            filename = f"{ts_code}.csv"
            filepath = os.path.join(data_dir, filename)
            df.to_csv(filepath)

            print(f"  ✓ 成功保存 {len(df)} 条记录到 {filepath}")

            # 避免请求过于频繁
            time.sleep(0.2)

            return df

        except Exception as e:
            print(f"  ❌ 下载 {ts_code} 失败: {e}")
            return None

    def download_benchmark_data(self, ts_code='000300.SH', start_date='20200101', end_date='20241231', data_dir='data'):
        """下载基准指数数据（沪深300）"""
        try:
            print(f"正在下载基准指数 {ts_code}...")

            # 使用 index_daily 获取指数数据
            df = self.pro.index_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                print(f"  ❌ {ts_code} 无数据")
                return None

            # 按日期排序
            df = df.sort_values('trade_date')
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df.set_index('trade_date', inplace=True)

            # 重命名列
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'vol': 'Volume',
                'amount': 'Amount'
            }, inplace=True)

            # 保存数据
            os.makedirs(data_dir, exist_ok=True)
            filename = f"{ts_code}.csv"
            filepath = os.path.join(data_dir, filename)
            df.to_csv(filepath)

            print(f"  ✓ 成功下载 {len(df)} 条记录")

            return df

        except Exception as e:
            print(f"  ❌ 下载基准指数失败: {e}")
            return None

    def download_multiple_etfs(self, etf_list, start_date, end_date, data_dir='data'):
        """批量下载ETF数据

        Args:
            etf_list: ETF代码列表，格式 ['159985.SZ', '518880.SS', ...]
            start_date: 开始日期
            end_date: 结束日期
            data_dir: 数据保存目录
        """
        success_count = 0
        failed_list = []

        print(f"\n开始批量下载 {len(etf_list)} 个ETF的数据...")
        print(f"时间范围: {start_date} 到 {end_date}")
        print("-" * 60)

        for i, ts_code in enumerate(etf_list, 1):
            print(f"[{i}/{len(etf_list)}]", end=" ")
            result = self.download_etf_data(ts_code, start_date, end_date, data_dir)
            if result is not None:
                success_count += 1
            else:
                failed_list.append(ts_code)

        print("-" * 60)
        print(f"下载完成！成功: {success_count}, 失败: {len(failed_list)}")

        if failed_list:
            print(f"失败的ETF: {', '.join(failed_list)}")

        return success_count


def main():
    """主函数 - 演示如何使用"""
    print("=" * 60)
    print("tushare ETF数据下载器")
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

    # 检查token
    try:
        # 创建数据获取器
        fetcher = TushareDataFetcher()
        print(f"✓ tushare初始化成功")

        # 下载基准数据（沪深300）
        fetcher.download_benchmark_data(
            ts_code='000300.SH',
            start_date='20200101',
            end_date='20241231'
        )

        # 批量下载ETF数据
        fetcher.download_multiple_etfs(
            etf_list=etf_list,
            start_date='20200101',
            end_date='20241231',
            data_dir='data'
        )

        print("\n✓ 数据下载完成！")
        print("下一步运行: python examples/run_strategy.py")

    except Exception as e:
        print(f"\n✗ 运行失败: {e}")
        print("\n可能的原因:")
        print("1. token无效或已过期")
        print("2. 网络连接问题")
        print("3. 请求频率过高（tushare有调用限制）")


if __name__ == "__main__":
    main()
