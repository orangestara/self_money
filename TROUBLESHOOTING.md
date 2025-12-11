# 问题诊断与修复指南

## 问题描述

用户报告："除了159985外其余的都没有数据"

## 问题分析

经过检查，发现以下问题：

### 1. 基准指数代码错误

**问题**: 配置文件中使用了 `000300.SS` 作为沪深300指数代码
**正确代码**: `000300.SH`

**原因**:
- tushare中 `.SH` 表示上海证券交易所
- `.SS` 不是有效的后缀

**修复**: 将 `config/config.yaml` 中的基准代码改为 `000300.SH`

### 2. ETF数据获取方法单一

**问题**: 只使用 `fund_daily` 接口获取数据，成功率低

**修复**: 增加多种数据获取方法：
1. `fund_daily` - 基金日线数据
2. `index_daily` - 指数日线数据（ETF可能是指数）
3. `daily` - 通用日线数据

### 3. 错误处理不够完善

**问题**: 缺乏详细的错误信息和重试机制

**修复**: 增加详细的错误日志和多种数据源尝试

## 修复内容

### 1. 配置文件修复

```yaml
# 修复前
benchmark: "000300.SS"

# 修复后
benchmark: "000300.SH"
```

### 2. data_fetcher.py 增强

```python
def download_etf_data(self, ts_code, start_date, end_date, data_dir='data'):
    # 尝试多种数据获取方法
    df = None

    # 方法1: fund_daily
    try:
        df = self.pro.fund_daily(ts_code=ts_code, ...)
        if df is not None and not df.empty:
            print(f"✓ 使用 fund_daily 获取到 {len(df)} 条记录")
    except Exception as e:
        print(f"⚠️ fund_daily 失败: {str(e)[:50]}")

    # 方法2: index_daily
    if df is None or df.empty:
        try:
            df = self.pro.index_daily(ts_code=ts_code, ...)
            if df is not None and not df.empty:
                print(f"✓ 使用 index_daily 获取到 {len(df)} 条记录")
        except Exception as e:
            print(f"⚠️ index_daily 失败: {str(e)[:50]}")

    # 方法3: daily
    if df is None or df.empty:
        try:
            df = self.pro.daily(ts_code=ts_code, ...)
            if df is not None and not df.empty:
                print(f"✓ 使用 daily 获取到 {len(df)} 条记录")
        except Exception as e:
            print(f"⚠️ daily 失败: {str(e)[:50]}")

    if df is None or df.empty:
        print(f"❌ 所有方法都失败，{ts_code} 无数据")
        return None
```

### 3. 错误处理改进

- 详细的错误日志
- 多种数据源尝试
- 兼容性列名重命名
- 数据完整性检查

## 验证修复

### 测试脚本

创建了以下测试脚本：

1. `debug_tushare.py` - 调试tushare数据获取问题
2. `check_etf_codes.py` - 检查ETF代码有效性
3. `test_data_fetcher.py` - 测试修复后的功能

### 运行测试

```bash
# 测试修复后的功能
python test_data_fetcher.py

# 检查ETF代码
python check_etf_codes.py

# 调试tushare问题
python debug_tushare.py
```

## 使用指南

### 1. 设置token

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，设置真实token
TUSHARE_TOKEN=your_real_token
```

### 2. 下载数据

```bash
# 下载基准指数和ETF数据
python data_fetcher.py
```

### 3. 验证数据

检查 `data/` 目录中的CSV文件：
- `000300.SH` - 沪深300指数
- `159985.SZ` - 豆粕ETF
- `518880.SS` - 黄金ETF
- 等等...

## 常见问题

### Q1: 为什么还是下载不到数据？

**可能原因**:
1. token无效或过期
2. 网络连接问题
3. tushare API调用次数超限
4. ETF代码不存在

**解决方案**:
```bash
# 检查token是否有效
echo $TUSHARE_TOKEN

# 重新获取token（访问 https://tushare.pro/）

# 检查网络连接
ping www.tushare.pro

# 检查API调用次数
# 登录tushare.pro查看调用统计
```

### Q2: 为什么有些ETF有数据，有些没有？

**原因**:
- 部分ETF可能不存在于tushare数据库中
- 部分ETF可能使用不同的代码格式
- 部分ETF可能是指数而不是基金

**解决方案**:
```python
# 获取所有可用的ETF
from data_fetcher import TushareDataFetcher

fetcher = TushareDataFetcher()
etfs = fetcher.get_stock_basic()
print(etfs[['ts_code', 'name']])
```

### Q3: 如何验证数据质量？

**检查方法**:
1. 检查CSV文件是否存在
2. 检查数据行数是否合理（应该有数百到数千条）
3. 检查数据时间范围是否正确
4. 检查是否有缺失值

```bash
# 检查文件
ls -la data/

# 检查数据
head data/159985.SZ.csv
wc -l data/*.csv
```

## 性能优化

### 1. 并行下载

当前是串行下载，可以考虑并行：

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(fetcher.download_etf_data, code, ...) for code in etf_list]
    results = [future.result() for future in futures]
```

### 2. 增量更新

避免重复下载已有数据：

```python
def should_download(ts_code, start_date):
    """检查是否需要下载"""
    filepath = f"data/{ts_code}.csv"
    if not os.path.exists(filepath):
        return True

    # 检查最后一条记录的日期
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    last_date = df.index[-1]
    return last_date < start_date
```

## 相关文件

- `data_fetcher.py` - 主要数据下载脚本
- `config/config.yaml` - 配置文件
- `src/etf_rotation/env_loader.py` - 环境变量加载器
- `test_data_fetcher.py` - 功能测试
- `debug_tushare.py` - 问题调试
- `check_etf_codes.py` - ETF代码检查

## 参考资料

- [tushare官方文档](https://tushare.pro/document)
- [tushare ETF数据获取](https://tushare.pro/document/2?doc_id=149)
- [指数数据获取](https://tushare.pro/document/2?doc_id=141)
