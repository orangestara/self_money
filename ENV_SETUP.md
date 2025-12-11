# 环境变量配置指南

## 概述

本项目使用 `.env` 文件来管理敏感配置（如tushare token），避免将敏感信息硬编码在代码中或意外提交到GitHub。

## 安全特性

- ✅ `.env` 文件已添加到 `.gitignore`，不会被提交到Git
- ✅ 提供 `.env.example` 模板供用户参考
- ✅ 支持系统环境变量和 `.env` 文件两种方式
- ✅ 优先级：系统环境变量 > `.env` 文件 > 代码传入

## 快速开始

### 1. 复制环境变量模板

```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

打开 `.env` 文件，填入你的tushare token：

```bash
# tushare数据源配置
TUSHARE_TOKEN=你的真实token

# 可选配置
BACKTRADER_LOG_LEVEL=1
```

### 3. 运行程序

```bash
python data_fetcher.py
```

## 配置说明

### TUSHARE_TOKEN

- **必需**：tushare数据源访问令牌
- 获取方式：访问 https://tushare.pro/ 注册账号 → 个人中心 → 接口Token
- 优先级：系统环境变量 > `.env` 文件

### BACKTRADER_LOG_LEVEL（可选）

- **可选**：backtrader策略日志级别
- 取值：0（静默）、1（正常）、2（详细）
- 默认值：1

## 优先级说明

程序会按以下优先级查找 `TUSHARE_TOKEN`：

1. **系统环境变量**：`os.getenv('TUSHARE_TOKEN')`
2. **`.env`文件**：从项目根目录的 `.env` 文件读取
3. **代码传入**：直接传入 `TushareDataFetcher(token='your_token')`
4. **错误提示**：如果都未设置，抛出错误提示

## 最佳实践

### ✅ 推荐做法

1. **使用 `.env` 文件**：
   ```bash
   cp .env.example .env
   # 编辑 .env 文件填入真实token
   ```

2. **使用系统环境变量**（适合CI/CD）：
   ```bash
   export TUSHARE_TOKEN='your_token'
   ```

3. **混合使用**：
   - 在 `.env` 中设置默认token
   - 在CI/CD中用系统环境变量覆盖

### ❌ 不推荐做法

1. **硬编码在代码中**：泄露token风险
2. **提交 `.env` 到Git**：暴露敏感信息
3. **使用公共token**：可能被他人滥用

## 故障排除

### 问题1：提示未设置token

**解决方案**：
1. 确认已复制 `.env.example` 为 `.env`
2. 确认 `.env` 文件中设置了 `TUSHARE_TOKEN=你的token`
3. 或设置系统环境变量：`export TUSHARE_TOKEN='你的token'`

### 问题2：读取到错误的token

**可能原因**：
1. `.env` 文件路径错误（应在项目根目录）
2. `.env` 文件格式错误（应为 `KEY=VALUE` 格式）
3. 系统环境变量覆盖了 `.env` 文件

**解决方案**：
```bash
# 检查系统环境变量
echo $TUSHARE_TOKEN

# 检查.env文件
cat .env

# 临时清除系统环境变量测试
unset TUSHARE_TOKEN
python data_fetcher.py
```

### 问题3：token无效

**解决方案**：
1. 确认token未过期（重新登录tushare.pro获取新token）
2. 确认token有足够调用次数
3. 检查网络连接

## 高级用法

### 多个环境配置

创建不同环境的 `.env` 文件：

```bash
.env.development   # 开发环境
.env.production    # 生产环境
.env.staging       # 测试环境
```

### 在代码中指定.env文件

```python
from etf_rotation.env_loader import get_tushare_token

# 指定特定的.env文件
token = get_tushare_token(env_file='.env.production')
```

### 环境变量验证

```python
from etf_rotation.env_loader import get_tushare_token

token = get_tushare_token()
if not token:
    raise ValueError("请先配置 TUSHARE_TOKEN")
```

## 迁移指南

### 从系统环境变量迁移到.env文件

1. **查看当前设置**：
   ```bash
   echo $TUSHARE_TOKEN
   ```

2. **复制到.env文件**：
   ```bash
   echo "TUSHARE_TOKEN=$TUSHARE_TOKEN" > .env
   ```

3. **测试**：
   ```bash
   unset TUSHARE_TOKEN
   python data_fetcher.py
   ```

### 从代码迁移到.env文件

1. **移除硬编码的token**
2. **创建.env文件**
3. **使用 `get_tushare_token()` 函数**

## 参考资料

- [tushare官网](https://tushare.pro/)
- [Python-dotenv文档](https://github.com/theskumar/python-dotenv)
- [12-Factor App - 配置](https://12factor.net/config)
