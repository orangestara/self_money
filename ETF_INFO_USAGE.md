# ETF基本信息获取工具使用说明

## 功能介绍

`test_etf_info.py` 是一个用于获取tushare所有ETF基本信息的测试工具。它可以帮助您：

1. **获取所有ETF信息**：从tushare获取所有ETF的基本信息
2. **按日期筛选**：根据上市日期筛选ETF
3. **数据分析**：分析ETF的上市时间、类型分布等
4. **生成配置文件**：自动生成新的ETF配置文件
5. **导出多种格式**：支持CSV和文本报告

## 安装依赖

```bash
pip install tushare pandas
# 或
uv sync
```

## 使用方法

### 基本用法

```bash
# 获取所有ETF信息
python test_etf_info.py

# 查看帮助
python test_etf_info.py --help
```

### 高级用法

```bash
# 筛选2020年前上市的ETF（适合回测）
python test_etf_info.py --end-date 2019-12-31

# 筛选指定时间范围内的ETF
python test_etf_info.py --start-date 2018-01-01 --end-date 2019-12-31

# 生成新的ETF配置文件
python test_etf_info.py --generate-config

# 指定输出目录
python test_etf_info.py --output-dir ./my_output

# 组合使用：筛选+生成配置文件
python test_etf_info.py --end-date 2019-12-31 --generate-config --output-dir ./etf_data
```

## 输出文件

### 1. CSV文件 (etf_basic_info_YYYYMMDD_HHMMSS.csv)

包含所有ETF的详细信息：
- `ts_code`: ETF代码
- `name`: ETF名称
- `management`: 管理公司
- `custodian`: 托管银行
- `fund_type`: 基金类型
- `list_date`: 上市日期
- `status`: 状态
- 等等...

### 2. 分析报告 (etf_analysis_report_YYYYMMDD_HHMMSS.txt)

包含数据分析结果：
- 总体统计
- 按上市年份统计
- 按基金类型统计
- 最近上市的ETF
- 适合回测的ETF列表

### 3. 配置文件 (new_etf_config.toml) [可选]

自动生成的ETF配置文件：
- 基准指数配置
- 回测参数
- 按类型分组的ETF列表
- 适合直接替换现有的config.toml

## 示例输出

### 控制台输出
```
============================================================
Tushare ETF基本信息获取工具
============================================================
✓ Tushare初始化成功

正在获取所有ETF基本信息...
============================================================
✓ 成功获取 1803 个ETF的基本信息

筛选结果: 513 个ETF
✓ ETF基本信息已保存到: output/etf_basic_info_20251211_212339.csv
✓ 分析报告已保存到: output/etf_analysis_report_20251211_212339.txt

============================================================
获取完成
============================================================
ETF总数: 513
上市日期范围: 2004-12-20 到 2019-12-31
```

### 分析报告示例
```
================================================================================
ETF基本信息分析报告
================================================================================
生成时间: 2025-12-11 21:23:39

一、总体统计
----------------------------------------
ETF总数: 513
上市日期范围: 2004-12-20 到 2019-12-31

二、按上市年份统计
----------------------------------------
2004年: 1个
2005年: 10个
...
2019年: 101个

三、按基金类型统计
----------------------------------------
股票型: 402个
混合型: 58个
债券型: 35个
...
```

## 实际应用场景

### 1. 更新ETF列表

```bash
# 获取最新ETF信息
python test_etf_info.py --generate-config

# 查看生成的配置文件
cat output/new_etf_config.toml

# 替换现有配置
cp output/new_etf_config.toml config.toml
```

### 2. 研究ETF发展历史

```bash
# 获取所有ETF信息并查看分析报告
python test_etf_info.py

# 查看各年份上市的ETF数量
cat output/etf_analysis_report_*.txt
```

### 3. 选择回测标的

```bash
# 获取2020年前上市的ETF（确保有足够的历史数据）
python test_etf_info.py --end-date 2019-12-31

# 查看分析报告中的"适合回测的ETF"部分
cat output/etf_analysis_report_*.txt
```

### 4. 特定时间段研究

```bash
# 研究2018-2019年上市的ETF
python test_etf_info.py --start-date 2018-01-01 --end-date 2019-12-31

# 分析这两年新发行的ETF特点
cat output/etf_analysis_report_*.txt
```

## 注意事项

1. **需要tushare token**：确保已在.env文件中配置TUSHARE_TOKEN
2. **网络连接**：需要稳定的网络连接访问tushare API
3. **数据量**：全部ETF数据量较大，获取可能需要一些时间
4. **输出目录**：默认输出到`output/`目录，可通过`--output-dir`参数修改

## 扩展功能

### 查看CSV数据

```bash
# 查看CSV文件前几行
head -5 output/etf_basic_info_*.csv

# 统计ETF数量
wc -l output/etf_basic_info_*.csv

# 使用pandas分析数据
python -c "
import pandas as pd
df = pd.read_csv('output/etf_basic_info_*.csv')
print(f'ETF总数: {len(df)}')
print(f'基金类型分布:')
print(df['fund_type'].value_counts())
"
```

## 故障排除

### 错误：未找到Tushare Token
- 检查.env文件是否存在
- 确认TUSHARE_TOKEN已正确设置
- 参考README.md中的环境配置说明

### 错误：网络连接失败
- 检查网络连接
- 确认tushare服务正常
- 稍后重试

### 错误：权限不足
- 确保对输出目录有写权限
- 尝试使用其他输出目录

## 相关文件

- `test_etf_info.py`: 主程序
- `output/etf_basic_info_*.csv`: ETF数据
- `output/etf_analysis_report_*.txt`: 分析报告
- `output/new_etf_config.toml`: 生成的配置文件
- `config.toml`: 现有配置文件

## 更新日志

### v1.0.0 (2025-12-11)
- ✅ 初始版本发布
- ✅ 支持获取所有ETF基本信息
- ✅ 支持按日期筛选
- ✅ 支持生成分析报告
- ✅ 支持生成配置文件
