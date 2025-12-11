#!/usr/bin/env python
"""
测试文件：获取tushare所有ETF基本信息

功能：
1. 从tushare获取所有ETF的基本信息
2. 筛选有效的ETF（已上市的）
3. 分析ETF的上市时间、规模等信息
4. 保存结果到CSV文件
5. 生成分析报告

使用方法：
    python test_etf_info.py

输出：
- output/etf_basic_info.csv - 所有ETF基本信息
- output/etf_analysis_report.txt - 分析报告
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import tushare as ts
    import pandas as pd
    from quant_strategies import load_config
except ImportError as e:
    print(f"❌ 错误：缺少必要的依赖库")
    print(f"   {e}")
    print("\n请运行以下命令安装依赖：")
    print("   uv sync")
    print("   或")
    print("   pip install tushare pandas")
    sys.exit(1)


class ETFInfoFetcher:
    """ETF信息获取器"""

    def __init__(self, token: Optional[str] = None):
        """初始化ETF信息获取器

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
        """从环境变量或.env文件读取token"""
        # 优先级：环境变量 > .env文件
        token = os.getenv('TUSHARE_TOKEN')
        if token:
            return token

        # 尝试从.env文件读取
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key.strip() == 'TUSHARE_TOKEN':
                            return value.strip().strip('"\'')
        return None

    def get_all_etfs(self) -> pd.DataFrame:
        """获取所有ETF基本信息

        Returns:
            包含所有ETF信息的DataFrame
        """
        print("\n正在获取所有ETF基本信息...")
        print("=" * 60)

        try:
            # 使用fund_basic接口获取ETF信息
            # market='E'表示ETF
            df = self.pro.fund_basic(market='E', status='L')

            if df.empty:
                print("⚠️  未找到任何ETF信息")
                return pd.DataFrame()

            print(f"✓ 成功获取 {len(df)} 个ETF的基本信息")

            # 处理数据
            # df包含列: ts_code, name, management, custodian, fund_type, status,
            #             list_date, delist_date, issue_date
            df['list_date'] = pd.to_datetime(df['list_date'], format='%Y%m%d', errors='coerce')

            # 按上市日期排序
            df = df.sort_values('list_date', ascending=False)

            return df

        except Exception as e:
            print(f"❌ 获取ETF信息失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def filter_by_date(self, df: pd.DataFrame, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """根据上市日期筛选ETF

        Args:
            df: ETF信息DataFrame
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            筛选后的DataFrame
        """
        if df.empty:
            return df

        filtered_df = df.copy()

        if start_date:
            start = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df['list_date'] >= start]

        if end_date:
            end = pd.to_datetime(end_date)
            filtered_df = filtered_df[filtered_df['list_date'] <= end]

        return filtered_df

    def analyze_etfs(self, df: pd.DataFrame) -> Dict:
        """分析ETF信息

        Args:
            df: ETF信息DataFrame

        Returns:
            分析结果字典
        """
        if df.empty:
            return {}

        analysis = {
            'total_count': len(df),
            'date_range': {
                'earliest': df['list_date'].min(),
                'latest': df['list_date'].max()
            },
            'by_year': df['list_date'].dt.year.value_counts().sort_index().to_dict(),
            'by_type': df['fund_type'].value_counts().to_dict() if 'fund_type' in df.columns else {},
        }

        return analysis

    def save_results(self, df: pd.DataFrame, analysis: Dict, output_dir: str = 'output'):
        """保存结果到文件

        Args:
            df: ETF信息DataFrame
            analysis: 分析结果
            output_dir: 输出目录
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存CSV文件
        csv_file = os.path.join(output_dir, f'etf_basic_info_{timestamp}.csv')
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"✓ ETF基本信息已保存到: {csv_file}")

        # 生成分析报告
        report_file = os.path.join(output_dir, f'etf_analysis_report_{timestamp}.txt')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ETF基本信息分析报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # 总体统计
            f.write("一、总体统计\n")
            f.write("-" * 40 + "\n")
            f.write(f"ETF总数: {analysis['total_count']}\n")
            f.write(f"上市日期范围: {analysis['date_range']['earliest'].date()} 到 {analysis['date_range']['latest'].date()}\n\n")

            # 按年份统计
            f.write("二、按上市年份统计\n")
            f.write("-" * 40 + "\n")
            for year, count in analysis['by_year'].items():
                if pd.notna(year):
                    f.write(f"{int(year)}年: {count}个\n")
            f.write("\n")

            # 按类型统计
            if analysis['by_type']:
                f.write("三、按基金类型统计\n")
                f.write("-" * 40 + "\n")
                for etype, count in analysis['by_type'].items():
                    f.write(f"{etype}: {count}个\n")
                f.write("\n")

            # 最近上市的ETF
            f.write("四、最近上市的10个ETF\n")
            f.write("-" * 40 + "\n")
            recent_etfs = df.head(10)
            for _, etf in recent_etfs.iterrows():
                f.write(f"{etf['ts_code']} - {etf['name']} (上市日期: {etf['list_date'].date()})\n")
            f.write("\n")

            # 2020年前上市的ETF（适合回测）
            f.write("五、2020年前上市的ETF（适合回测）\n")
            f.write("-" * 40 + "\n")
            pre_2020_etfs = self.filter_by_date(df, end_date='2019-12-31')
            if not pre_2020_etfs.empty:
                for _, etf in pre_2020_etfs.iterrows():
                    f.write(f"{etf['ts_code']} - {etf['name']} (上市日期: {etf['list_date'].date()})\n")
                f.write(f"\n总计: {len(pre_2020_etfs)}个ETF适合回测\n")
            else:
                f.write("无2020年前上市的ETF\n")

        print(f"✓ 分析报告已保存到: {report_file}")

        return csv_file, report_file

    def generate_config_toml(self, df: pd.DataFrame, output_file: str = 'output/new_etf_config.toml'):
        """生成新的ETF配置文件

        Args:
            df: ETF信息DataFrame
            output_file: 输出文件路径
        """
        # 筛选2020年前上市的ETF
        pre_2020_etfs = self.filter_by_date(df, end_date='2019-12-31')

        if pre_2020_etfs.empty:
            print("⚠️  无2020年前上市的ETF，无法生成配置文件")
            return

        # 按类型分组
        categories = {
            'commodity': [],
            'overseas': [],
            'a_share': [],
            'tech': [],
            'other': []
        }

        # 简单的类型推断（基于名称关键词）
        for _, etf in pre_2020_etfs.iterrows():
            name = etf['name']
            code = etf['ts_code']

            etf_info = {
                'symbol': code,
                'name': name,
                'style': 'other'
            }

            # 根据名称关键词分类
            if any(keyword in name for keyword in ['商品', '黄金', '白银', '原油', '有色', '煤炭', '豆粕', '钢铁']):
                etf_info['style'] = 'commodity'
            elif any(keyword in name for keyword in ['纳指', '标普', '纳斯达克', '恒生', '港股', '海外', '全球']):
                etf_info['style'] = 'overseas'
            elif any(keyword in name for keyword in ['沪深', 'A股', '上证', '深证', '创业板', '中证', '50', '500', '1000']):
                etf_info['style'] = 'a_share'
            elif any(keyword in name for keyword in ['科技', '半导体', '芯片', '电子', '通信', '计算机', '互联网', '人工智能']):
                etf_info['style'] = 'tech'

            categories[etf_info['style']].append(etf_info)

        # 生成配置文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# ETF配置文件 - 自动生成\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 数据来源: tushare\n")
            f.write(f"# 说明: 只包含2020年前上市的ETF\n\n")

            f.write("# 基准指数\n")
            f.write("[benchmark]\n")
            f.write('symbol = "000300.SH"\n\n')

            f.write("# 回测参数\n")
            f.write("[backtest_params]\n")
            f.write('start_date = "2020-01-01"\n')
            f.write('end_date = "2024-12-31"\n')
            f.write('initial_cash = 1_000_000\n\n')

            f.write("# 防御性ETF组合\n")
            defensive_etfs = [etf['symbol'] for etf in categories['commodity'][:3]]
            f.write(f'defensive_etfs = {defensive_etfs}\n\n')

            f.write("# ETF池配置\n")
            for category, etfs in categories.items():
                if etfs:
                    f.write(f"\n# {category}类ETF\n")
                    for etf in etfs:
                        f.write('[[etf_list]]\n')
                        f.write(f'symbol = "{etf["symbol"]}"\n')
                        f.write(f'name = "{etf["name"]}"\n')
                        f.write(f'style = "{etf["style"]}"\n\n')

        print(f"✓ 新的ETF配置文件已生成: {output_file}")
        print(f"   包含 {len(pre_2020_etfs)} 个2020年前上市的ETF")
        print(f"   按类型分组: commodity({len(categories['commodity'])}), overseas({len(categories['overseas'])}), "
              f"a_share({len(categories['a_share'])}), tech({len(categories['tech'])})")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='获取tushare所有ETF基本信息',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--start-date', type=str,
                        help='开始日期 (YYYY-MM-DD)，筛选指定日期后上市的ETF')
    parser.add_argument('--end-date', type=str,
                        help='结束日期 (YYYY-MM-DD)，筛选指定日期前上市的ETF')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='输出目录 (默认: output)')
    parser.add_argument('--generate-config', action='store_true',
                        help='生成新的ETF配置文件')

    args = parser.parse_args()

    print("=" * 60)
    print("Tushare ETF基本信息获取工具")
    print("=" * 60)

    try:
        # 初始化获取器
        fetcher = ETFInfoFetcher()

        # 获取所有ETF信息
        all_etfs = fetcher.get_all_etfs()

        if all_etfs.empty:
            print("❌ 未获取到任何ETF信息")
            return

        # 筛选ETF
        filtered_etfs = fetcher.filter_by_date(all_etfs, args.start_date, args.end_date)

        print(f"\n筛选结果: {len(filtered_etfs)} 个ETF")

        # 分析数据
        analysis = fetcher.analyze_etfs(filtered_etfs)

        # 保存结果
        csv_file, report_file = fetcher.save_results(filtered_etfs, analysis, args.output_dir)

        # 生成配置文件
        if args.generate_config:
            config_file = os.path.join(args.output_dir, 'new_etf_config.toml')
            fetcher.generate_config_toml(filtered_etfs, config_file)

        # 输出摘要
        print("\n" + "=" * 60)
        print("获取完成")
        print("=" * 60)
        print(f"ETF总数: {analysis['total_count']}")
        print(f"上市日期范围: {analysis['date_range']['earliest'].date()} 到 {analysis['date_range']['latest'].date()}")
        print(f"\n输出文件:")
        print(f"  - {csv_file}")
        print(f"  - {report_file}")
        if args.generate_config:
            print(f"  - {config_file}")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
