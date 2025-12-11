"""
调试tushare ETF数据获取问题

检查为什么除了159985之外其他ETF都没有数据
"""

import tushare as ts
import pandas as pd
import os
import sys

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etf_rotation.env_loader import get_tushare_token


def test_fund_basic():
    """测试获取基金基本信息"""
    print("=" * 60)
    print("1. 测试 fund_basic 获取所有ETF")
    print("=" * 60)

    token = get_tushare_token()
    if not token:
        print("❌ 未设置TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    try:
        # 获取所有ETF
        df = pro.fund_basic(market='E')
        print(f"✅ 成功获取 {len(df)} 个基金")
        print("\n前20个基金:")
        for i in range(min(20, len(df))):
            row = df.iloc[i]
            print(f"  {row['ts_code']}: {row['name']}")

        # 查找我们需要的ETF
        target_codes = ['159985.SZ', '518880.SS', '515220.SS', '513100.SS']
        print(f"\n查找目标ETF:")
        for code in target_codes:
            matches = df[df['ts_code'] == code]
            if len(matches) > 0:
                print(f"  ✅ {code}: {matches.iloc[0]['name']}")
            else:
                print(f"  ❌ {code}: 未找到")

    except Exception as e:
        print(f"❌ 获取失败: {e}")


def test_index_basic():
    """测试获取指数信息（ETF可能是指数）"""
    print("\n" + "=" * 60)
    print("2. 测试 index_basic 获取指数（部分ETF可能是指数）")
    print("=" * 60)

    token = get_tushare_token()
    if not token:
        print("❌ 未设置TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    try:
        # 获取指数列表
        df = pro.index_basic(market='SSE')  # 上交所
        print(f"✅ 上交所指数: {len(df)} 个")
        print("\n前10个指数:")
        for i in range(min(10, len(df))):
            row = df.iloc[i]
            print(f"  {row['ts_code']}: {row['name']}")

        # 获取深交所指数
        df_szse = pro.index_basic(market='SZSE')
        print(f"\n✅ 深交所指数: {len(df_szse)} 个")
        print("\n前10个指数:")
        for i in range(min(10, len(df_szse))):
            row = df_szse.iloc[i]
            print(f"  {row['ts_code']}: {row['name']}")

    except Exception as e:
        print(f"❌ 获取失败: {e}")


def test_daily_data():
    """测试获取日线数据"""
    print("\n" + "=" * 60)
    print("3. 测试获取日线数据")
    print("=" * 60)

    token = get_tushare_token()
    if not token:
        print("❌ 未设置TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    test_codes = ['159985.SZ', '518880.SS']

    for code in test_codes:
        print(f"\n测试 {code}:")
        try:
            # 尝试 fund_daily
            df = pro.fund_daily(ts_code=code, start_date='20240101', end_date='20241231')
            print(f"  fund_daily: {len(df)} 条记录")
            if len(df) > 0:
                print(f"    最新: {df.iloc[0]['trade_date']} - {df.iloc[0]['close']}")
        except Exception as e:
            print(f"  fund_daily: ❌ {e}")

        try:
            # 尝试 index_daily
            df = pro.index_daily(ts_code=code, start_date='20240101', end_date='20241231')
            print(f"  index_daily: {len(df)} 条记录")
            if len(df) > 0:
                print(f"    最新: {df.iloc[0]['trade_date']} - {df.iloc[0]['close']}")
        except Exception as e:
            print(f"  index_daily: ❌ {e}")


def check_fund_type():
    """检查基金类型"""
    print("\n" + "=" * 60)
    print("4. 检查基金类型")
    print("=" * 60)

    token = get_tushare_token()
    if not token:
        print("❌ 未设置TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    try:
        df = pro.fund_basic(market='E')
        print(f"所有基金类型统计:")
        if 'type' in df.columns:
            type_counts = df['type'].value_counts()
            for type_name, count in type_counts.items():
                print(f"  {type_name}: {count} 个")
        else:
            print("  未找到 type 列")
            print("  可用列:", list(df.columns))

    except Exception as e:
        print(f"❌ 获取失败: {e}")


def main():
    """主函数"""
    print("🔍 tushare ETF数据获取调试")
    print()

    check_fund_type()
    test_fund_basic()
    test_index_basic()
    test_daily_data()

    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
