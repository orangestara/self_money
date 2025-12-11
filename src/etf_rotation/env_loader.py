"""
环境变量加载器

支持从.env文件和系统环境变量读取配置
"""

import os
from typing import Optional


def load_env(env_file: Optional[str] = None) -> dict:
    """加载环境变量

    Args:
        env_file: .env文件路径，如果为None则自动查找当前目录的.env

    Returns:
        包含环境变量的字典
    """
    if env_file is None:
        env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')

    env_vars = {}

    # 如果文件存在，读取.env文件
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue

                # 解析 KEY=VALUE 格式
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    env_vars[key] = value

    return env_vars


def get_env(key: str, default: Optional[str] = None, env_file: Optional[str] = None) -> Optional[str]:
    """获取环境变量

    优先级：系统环境变量 > .env文件 > 默认值

    Args:
        key: 环境变量名
        default: 默认值
        env_file: .env文件路径

    Returns:
        环境变量值
    """
    # 首先尝试从系统环境变量获取
    value = os.getenv(key)
    if value is not None:
        return value

    # 然后尝试从.env文件获取
    env_vars = load_env(env_file)
    if key in env_vars:
        return env_vars[key]

    # 最后返回默认值
    return default


def get_tushare_token(env_file: Optional[str] = None) -> Optional[str]:
    """获取tushare token

    Args:
        env_file: .env文件路径

    Returns:
        tushare token或None
    """
    # 优先级：系统环境变量 > .env文件
    token = os.getenv('TUSHARE_TOKEN')
    if token:
        return token

    env_vars = load_env(env_file)
    return env_vars.get('TUSHARE_TOKEN')
