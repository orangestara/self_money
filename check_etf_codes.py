"""
检查和验证tushare ETF代码

tushare中：
- 指数代码使用 .SH（上交所）和 .SZ（深交所）
- 基金代码使用 .OF（场外基金）
- ETF可能有不同的格式

常见ETF代码：
- 159985.SZ: 豆粕ETF
- 518880.SS: 黄金ETF  <- 可能是 518880.SH
- 000300.SH: 沪深300指数  <- 不是 .SS
"""

import tushare as ts
import pandas as pd
import os
import sys

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etf_rotation.env_loader import get_tushare_token


def check_index_codes():
    """检查指数代码"""
    print("=" * 60)
    print("检查指数代码")
    print("=" * 60)

    token = get_tushare_token()
    if not token:
        print("❌ 未设置TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    # 测试不同的沪深300代码
    test_codes = ['000300.SH', '000300.SS', '000300.SZ']

    for code in test_codes:
        print(f"\n测试指数代码: {code}")
        try:
            df = pro.index_daily(ts_code=code, start_date='20241201', end_date='20241231')
            if len(df) > 0:
                print(f"  ✅ 成功: {len(df)} 条记录")
                print(f"  最新: {df.iloc[0]['trade_date']} - {df.iloc[0]['close']}")
            else:
                print(f"  ❌ 无数据")
        except Exception as e:
            print(f"  ❌ 错误: {e}")


def check_etf_codes():
    """检查ETF代码"""
    print("\n" + "=" * 60)
    print("检查ETF代码")
    print("=" * 60)

    token = get_tushare_token()
    if not token:
        print("❌ 未设置TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    # 测试不同的ETF代码格式
    test_codes = [
        ('159985.SZ', '159985.SZ'),  # 豆粕ETF
        ('518880.SS', '518880.SH'),  # 黄金ETF
        ('515220.SS', '515220.SH'),  # 煤炭ETF
        ('513100.SS', '513100.SH'),  # 纳指ETF
    ]

    for original, alternative in test_codes:
        print(f"\n测试ETF: {original} -> {alternative}")

        # 测试原代码
        try:
            df = pro.fund_daily(ts_code=original, start_date='20241201', end_date='20241231')
            if len(df) > 0:
                print(f"  ✅ {original}: {len(df)} 条记录")
            else:
                print(f"  ⚠️  {original}: 无数据")
        except Exception as e:
            print(f"  ❌ {original}: {str(e)[:50]}")

        # 测试替代代码
        if alternative != original:
            try:
                df = pro.fund_daily(ts_code=alternative, start_date='20241201', end_date='20241231')
                if len(df) > 0:
                    print(f"  ✅ {alternative}: {len(df)} 条记录")
                else:
                    print(f"  ⚠️  {alternative}: 无数据")
            except Exception as e:
                print(f"  ❌ {alternative}: {str(e)[:50]}")


def search_available_etfs():
    """搜索可用的ETF"""
    print("\n" + "=" * 60)
    print("搜索可用的ETF")
    print("=" * 60)

    token = get_tushare_token()
    if not token:
        print("❌ 未设置TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    try:
        # 获取所有基金
        df = pro.fund_basic(market='E')
        print(f"总共有 {len(df)} 个基金")

        # 筛选ETF（名字中包含ETF的）
        etfs = df[df['name'].str.contains('ETF', na=False)]
        print(f"找到 {len(etfs)} 个ETF")

        print("\n所有ETF列表:")
        for i, row in etfs.iterrows():
            print(f"  {row['ts_code']}: {row['name']}")

        return etfs

    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return None


def test_alternative_methods():
    """测试替代数据获取方法"""
    print("\n" + "=" * 60)
    print("测试替代数据获取方法")
    print("=" * 60)

    token = get_tushare_token()
    if not token:
        print("❌ 未设置TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    # 测试豆粕ETF 159985.SZ
    code = '159985.SZ'
    print(f"\n测试 {code} 的不同数据获取方法:")

    # 方法1: fund_daily
    try:
        df = pro.fund_daily(ts_code=code, start_date='20241201', end_date='20241231')
        print(f"  fund_daily: ✅ {len(df)} 条记录")
        if len(df) > 0:
            print(f"    最新: {df.iloc[0]['trade_date']} - {df.iloc[0]['close']}")
    except Exception as e:
        print(f"  fund_daily: ❌ {e}")

    # 方法2: index_daily (有些ETF可能是指数)
    try:
        df = pro.index_daily(ts_code=code, start_date='20241201', end_date='20241231')
        print(f"  index_daily: ✅ {len(df)} 条记录")
        if len(df) > 0:
            print(f"    最新: {df.iloc[0]['trade_date']} - {df.iloc[0]['close']}")
    except Exception as e:
        print(f"  index_daily: ❌ {e}")

    # 方法3: daily (通用日线数据)
    try:
        df = pro.daily(ts_code=code, start_date='20241201', end_date='20241231')
        print(f"  daily: ✅ {len(df)} 条记录")
        if len(df) > 0:
            print(f"    最新: {df.iloc[0]['trade_date']} - {df.iloc[0]['close']}")
    except Exception as e:
        print(f"  daily: ❌ {e}")


def main():
    """主函数"""
    print("🔍 检查tushare ETF代码问题")
    print()

    check_index_codes()
    check_etf_codes()
    test_alternative_methods()
    etfs = search_available_etfs()

    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

    if etfs is not None:
        print("\n💡 建议:")
        print("1. 使用基金代码时，确保代码正确")
        print("2. 沪深300指数使用 000300.SH 而不是 000300.SS")
        print("3. 如果ETF无数据，可能需要使用指数代码或检查代码是否存在")
        print("4. 建议先用 fund_basic 获取所有ETF，然后筛选需要的")


if __name__ == "__main__":
    main()
