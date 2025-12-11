# ETF轮动策略 - Backtrader版本

这是一个基于backtrader框架的ETF轮动策略，实现了聚宽平台上的多因子ETF轮动策略。

## 策略概述

本策略采用多因子模型进行ETF选择和轮动，包含以下核心功能：

### 1. 因子模型
- **动量因子**：基于年化收益和判定系数的组合
- **质量因子**：包含7个子因子
  - 斜率R²因子
  - 均线因子
  - RSRS因子
  - 波动率因子
  - 最大回撤得分
  - 夏普比率
  - 多周期均线因子

### 2. 动态风控
- 基于市场波动率分位的动态止损/止盈/跟踪止损
- 成本止损和跟踪止损结合使用
- 实时调整风控参数

### 3. 市场风险判断
- 基于沪深300指数的均线和波动率分位
- 分为高风险/低风险/中性市场三种状态
- 根据风险等级调整仓位比例

### 4. 风格分散
- ETF按风格分类：商品、海外、A股、科技
- 优先选择不同风格的ETF进行分散投资
- 最多持有3个标的

### 5. 调仓规则
- 每周一进行调仓
- 权重偏离超过5%时进行调仓
- 基于因子得分的动态权重分配

## 项目结构

```
self_money/
├── pyproject.toml          # uv项目配置
├── README.md               # 项目说明
├── config/
│   └── config.yaml         # 策略配置文件
├── data/                   # 数据文件目录
├── src/
│   └── etf_rotation/
│       ├── __init__.py
│       ├── strategy.py     # 主策略类
│       ├── factors.py      # 因子计算模块
│       ├── risk_manager.py # 风控模块
│       └── utils.py        # 工具函数
├── examples/
│   └── run_strategy.py     # 运行示例
└── tests/                  # 测试目录
```

## 安装依赖

使用uv管理项目依赖：

```bash
# 安装项目依赖
uv sync

# 安装开发依赖（可选）
uv sync --dev
```

## 数据准备

### 1. 安装tushare

项目使用tushare作为数据源，需要先注册获取token：

1. 访问 [tushare.pro](https://tushare.pro/) 注册账号
2. 登录后进入"个人中心" -> "接口Token"
3. 配置token（推荐使用.env文件）：

   ```bash
   # 复制环境变量模板
   cp .env.example .env

   # 编辑.env文件，填入你的token
   # TUSHARE_TOKEN=你的token
   ```

4. 或者设置系统环境变量：

   ```bash
   export TUSHARE_TOKEN='你的token'
   ```

   或添加到 ~/.bashrc / ~/.zshrc：

   ```bash
   echo "export TUSHARE_TOKEN='你的token'" >> ~/.bashrc
   source ~/.bashrc
   ```

### 2. 下载数据

策略需要以下ETF的历史数据：
- 商品类：豆粕ETF、黄金ETF、煤炭ETF等
- 海外类：纳指ETF、标普500ETF等
- A股类：A50ETF、创业板ETF等
- 科技类：人工智能ETF、半导体ETF等

#### 使用tushare下载（推荐）

项目已内置数据下载脚本：

```bash
# 下载数据（需要先设置TUSHARE_TOKEN）
python data_fetcher.py
```

或手动下载：

```python
from data_fetcher import TushareDataFetcher

# 初始化（需要先设置TUSHARE_TOKEN环境变量）
fetcher = TushareDataFetcher()

# 下载基准数据（沪深300）
fetcher.download_benchmark_data(
    ts_code='000300.SH',
    start_date='20200101',
    end_date='20241231'
)

# 批量下载ETF数据
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

fetcher.download_multiple_etfs(
    etf_list=etf_list,
    start_date='20200101',
    end_date='20241231',
    data_dir='data'
)
```

### 2. 数据格式

数据文件应为CSV格式，包含以下列：
- Date（日期，索引）
- Open（开盘价）
- High（最高价）
- Low（最低价）
- Close（收盘价）
- Volume（成交量）

示例：
```csv
Date,Open,High,Low,Close,Volume
2020-01-02,100.0,102.0,99.0,101.5,1500000
2020-01-03,101.5,103.0,100.5,102.0,1600000
...
```

## 运行策略

### 1. 基本运行

```bash
cd examples
python run_strategy.py
```

### 2. 自定义配置

修改 `config/config.yaml` 文件来自定义策略参数：

```yaml
# 因子计算参数
factor_params:
  momentum_window: 25  # 动量窗口
  slope_window: 20     # 斜率窗口
  ...

# 交易参数
trading_params:
  max_holdings: 3      # 最多持有3个标的
  score_threshold: 0    # 综合得分需>0才纳入候选
  ...

# 风控参数
risk_params:
  stop_loss_base: 0.05     # 基础止损比例
  take_profit_ratio: 0.10  # 基础止盈比例
  ...
```

### 3. 代码示例

```python
import backtrader as bt
from src.etf_rotation.strategy import ETFRotationStrategy

# 创建Cerebro引擎
cerebro = bt.Cerebro()

# 添加策略
cerebro.addstrategy(ETFRotationStrategy)

# 添加数据
for symbol in etf_symbols:
    data = bt.feeds.PandasData(dataname=data_df)
    cerebro.adddata(data, name=symbol)

# 设置初始资金
cerebro.broker.setcash(1000000)

# 运行回测
results = cerebro.run()
final_value = cerebro.broker.getvalue()
```

## 回测结果解读

策略运行后会输出以下指标：

- **总收益率**：最终收益与初始资金的比例
- **年化收益率**：平均每年的收益率
- **夏普比率**：风险调整后的收益指标
- **最大回撤**：最大回撤幅度和持续时间
- **胜率**：盈利交易的占比

## 策略优化建议

1. **因子参数优化**：
   - 调整动量窗口、斜率窗口等参数
   - 尝试不同的因子权重组合

2. **风控参数优化**：
   - 调整止损、止盈阈值
   - 优化动态风控的敏感度

3. **选股参数优化**：
   - 调整最多持有标的数量
   - 修改因子得分阈值

4. **调仓频率优化**：
   - 尝试不同的调仓频率
   - 调整权重偏离阈值

## 注意事项

1. **数据质量**：确保数据完整性和准确性
2. **交易成本**：考虑实际交易中的佣金和滑点
3. **市场环境**：策略在不同市场环境下的表现可能不同
4. **风险控制**：严格遵守风控规则，避免过度回撤

## 依赖库

- `backtrader`：量化交易框架
- `pandas`：数据处理
- `numpy`：数值计算
- `scipy`：科学计算
- `pyyaml`：配置文件
- `tushare`：财经数据接口（数据源）
- `matplotlib`：图表绘制

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题，请通过以下方式联系：
- Email: dev@example.com
- GitHub: https://github.com/your-repo
