"""
测试环境变量加载功能
"""

import sys
import os

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etf_rotation.env_loader import get_tushare_token, get_env, load_env


def test_env_loader():
    """测试环境变量加载器"""
    print("=" * 60)
    print("测试环境变量加载功能")
    print("=" * 60)

    # 测试1：load_env
    print("\n1. 测试 load_env 函数")
    env_vars = load_env()
    print(f"   从.env文件加载的环境变量: {list(env_vars.keys())}")

    # 测试2：get_env
    print("\n2. 测试 get_env 函数")
    test_value = get_env('TUSHARE_TOKEN', default='未设置')
    print(f"   TUSHARE_TOKEN: {test_value}")

    # 测试3：get_tushare_token
    print("\n3. 测试 get_tushare_token 函数")
    token = get_tushare_token()
    print(f"   获取到的token: {token if token else '未设置'}")

    # 测试4：系统环境变量优先级
    print("\n4. 测试优先级（系统环境变量 > .env文件 > 默认值）")
    os.environ['TEST_VAR'] = 'system_value'
    with open('.env', 'w') as f:
        f.write('TEST_VAR=env_value\n')

    result = get_env('TEST_VAR', default='default_value')
    print(f"   系统环境变量设置后: {result}")

    # 清理
    if os.path.exists('.env'):
        os.remove('.env')
    if 'TEST_VAR' in os.environ:
        del os.environ['TEST_VAR']

    print("\n" + "=" * 60)
    print("✓ 环境变量加载功能测试完成")
    print("=" * 60)

    return token


def test_with_demo_env():
    """使用演示.env文件测试"""
    print("\n" + "=" * 60)
    print("使用演示.env文件测试")
    print("=" * 60)

    # 创建演示.env文件
    with open('.env', 'w') as f:
        f.write('# 这是一个演示配置\n')
        f.write('TUSHARE_TOKEN=demo_token_12345\n')
        f.write('BACKTRADER_LOG_LEVEL=1\n')

    print("\n已创建 .env 文件，内容如下:")
    with open('.env', 'r') as f:
        for line in f:
            print(f"  {line.rstrip()}")

    # 重新测试
    token = get_tushare_token()
    log_level = get_env('BACKTRADER_LOG_LEVEL', default='0')

    print(f"\n✓ 读取到 TUSHARE_TOKEN: {token}")
    print(f"✓ 读取到 BACKTRADER_LOG_LEVEL: {log_level}")

    # 清理
    if os.path.exists('.env'):
        os.remove('.env')

    print("\n✓ 演示测试完成，已清理 .env 文件")


if __name__ == "__main__":
    # 测试基本功能
    token = test_env_loader()

    # 如果没有token，运行演示测试
    if not token:
        test_with_demo_env()

    print("\n✅ 所有测试完成！")
