# 量化策略框架 v2.0

基于Backtrader的现代化量化策略框架，支持多种策略、回测引擎、信号生成和自动化参数优化。

## ✨ 核心特性

### 多策略支持
- **ETF轮动策略**：基于多因子模型的趋势跟踪策略
- **网格交易策略**：专为震荡市场设计的网格套利策略
- 支持策略注册、配置管理和动态切换

### 多因子模型
- **动量因子**：基于年化收益和判定系数
- **质量因子**：包含7个子因子（斜率R²、均线、RSRS、波动率、最大回撤、夏普比率、多周期均线）
- **动态风控**：基于市场波动率分位的动态参数调整

### 参数优化
- **网格搜索**：穷举所有参数组合，确保找到最优解
- **随机搜索**：高效采样，适合中等参数空间
- **贝叶斯优化**：智能搜索，适合大参数空间

### 统一输出管理
- 所有输出文件统一保存在 `output/` 目录
- 自动时间戳命名，避免文件覆盖
- 支持回测结果、参数优化、信号记录等

### 模块化架构
```
src/quant_strategies/
├── core/              # 核心模块
│   ├── base_strategy.py      # 策略基类
│   ├── backtest_engine.py    # 回测引擎
│   ├── signal_generator.py   # 信号生成器
│   ├── config.py            # 配置加载
│   ├── factors.py           # 因子计算
│   ├── risk_manager.py      # 风控管理
│   └── utils.py             # 工具函数
├── managers/          # 管理模块
│   ├── strategy_manager.py  # 策略管理
│   ├── strategy_factory.py  # 策略工厂
│   └── parameter_search.py  # 参数搜索
├── strategies/        # 策略实现
│   ├── etf_rotation.py      # ETF轮动策略
│   └── grid_trading.py      # 网格交易策略
```

## 📦 安装

### 环境要求
- Python 3.8+
- uv（推荐）或 pip

### 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

## ⚙️ 环境配置

### Tushare Token配置

项目使用tushare作为数据源，需要配置token：

#### 方法1：使用.env文件（推荐）

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑.env文件，填入你的token
# TUSHARE_TOKEN=你的真实token
```

#### 方法2：使用系统环境变量

```bash
# 设置环境变量
export TUSHARE_TOKEN='你的token'

# 或添加到 ~/.bashrc / ~/.zshrc
echo "export TUSHARE_TOKEN='你的token'" >> ~/.bashrc
source ~/.bashrc
```

#### 获取token

1. 访问 [tushare.pro](https://tushare.pro/) 注册账号（免费）
2. 登录后进入"个人中心" -> "接口Token"
3. 复制token并配置

**优先级**：系统环境变量 > .env文件 > 代码传入

## 📊 数据准备

### 下载数据

```bash
# 使用内置脚本下载数据（需先配置TUSHARE_TOKEN）
python data_fetcher.py
```

这将自动下载：
- 基准指数数据（沪深300：000300.SH）
- 所有配置的ETF数据

下载的数据保存在 `data/` 目录中，格式为CSV。

### 数据格式

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

策略需要以下ETF的历史数据：
- **商品类**：豆粕ETF、黄金ETF、煤炭ETF等
- **海外类**：纳指ETF、标普500ETF等
- **A股类**：A50ETF、创业板ETF等
- **科技类**：人工智能ETF、半导体ETF等

## 🏃 快速开始

### 1. 基本使用

```python
from quant_strategies import (
    load_config,
    create_backtest_engine,
    create_parameter_search
)

# 加载配置
config = load_config()

# 运行回测
engine = create_backtest_engine()
result = engine.run_backtest('etf_rotation', data_dict)

# 参数优化
searcher = create_parameter_search(
    'random',
    objective_func=your_objective_func,
    param_space=param_space
)
results = searcher.search(n_iterations=100)
```

### 2. 网格交易策略

```python
from quant_strategies import GridTradingStrategy

# 创建网格策略
strategy = GridTradingStrategy({
    'params': {
        'grid_count': 15,
        'grid_spacing': 0.015,
        'price_range_pct': 0.25,
        'take_profit_threshold': 0.12,
        'stop_loss_threshold': 0.18
    }
})
```

### 3. 参数优化

```python
from quant_strategies import GridSearch, RandomSearch, BayesianOptimization

# 定义参数空间
param_space = {
    'grid_count': [10, 15, 20],
    'grid_spacing': [0.01, 0.015, 0.02],
    'price_range_pct': [0.15, 0.2, 0.25]
}

# 网格搜索
searcher = GridSearch(objective_func, param_space)
results = searcher.search()

# 随机搜索
searcher = RandomSearch(objective_func, param_space, seed=42)
results = searcher.search(n_iterations=100)

# 贝叶斯优化
searcher = BayesianOptimization(objective_func, param_space)
results = searcher.search(n_iterations=50, n_initial_points=10)
```

## 📊 示例

### 运行策略

```bash
# ETF轮动策略
cd examples
python run_strategy.py

# 多策略演示
python multi_strategy_demo.py

# 参数优化演示
python parameter_optimization.py

# 快速开始
python quick_start_multi_strategy.py
```

### 快速体验（模拟数据）

如果没有真实数据，可以使用模拟数据快速体验：

```bash
cd examples
python run_with_demo_data.py
```

### 完整回测示例

```python
from quant_strategies import (
    load_config,
    create_backtest_engine
)

# 加载配置
config = load_config()

# 加载数据（需要先下载）
data_dict = load_etf_data(['159985.SZ', '518880.SS'])

# 运行回测
engine = create_backtest_engine()
result = engine.run_backtest('etf_rotation', data_dict)

# 查看结果
print(f"总收益率: {result['total_return']:.2f}%")
print(f"夏普比率: {result['sharpe_ratio']:.2f}")
print(f"最大回撤: {result['max_drawdown']:.2f}%")
```

### 买入信号生成

```python
from quant_strategies import create_strategy_manager

# 创建策略管理器
manager = create_strategy_manager()

# 生成信号
signals = manager.generate_signals('etf_rotation', data_dict)

# 查看信号
if 'signals' in signals:
    for symbol, signal in signals['signals'].items():
        print(f"{symbol}: {signal['action']} "
              f"(权重变化: {signal['weight_change']:.2%})")
```

### 回测结果解读

回测完成后会显示以下指标：

```
最终资金: 1,234,567.89
总收益: 234,567.89
总收益率: 23.46%
年化收益率: 5.23%
夏普比率: 1.45
最大回撤: -8.76%
回撤时长: 45 天
交易次数: 128
胜率: 65.62%
```

**指标说明**：
- **总收益率**：整个回测期间的总回报
- **年化收益率**：平均每年的收益率
- **夏普比率**：风险调整后的收益，越高越好（>1为优秀）
- **最大回撤**：从峰值到谷底的最大跌幅，越小越好（<-20%需警惕）
- **胜率**：盈利交易的占比

### 输出文件

所有输出文件自动保存到 `output/` 目录：

```
output/
├── results/          # 结果文件
│   ├── backtest_results_20241211_120000.json
│   ├── optimization_results_20241211_120000.json
│   └── signals_20241211_120000.csv
├── charts/           # 图表文件
├── logs/             # 日志文件
└── reports/          # 报告文件
```

## 🔧 配置

### config.toml

```toml
[backtest_params]
start_date = "2020-01-01"
end_date = "2024-12-31"
initial_cash = 1000000

[strategies.etf_rotation]
enabled = true
description = "ETF轮动策略"
params = { max_holdings = 3, score_threshold = 0 }

[strategies.grid_trading]
enabled = true
description = "网格交易策略"
params = { grid_count = 10, grid_spacing = 0.02 }

[factor_params]
momentum_window = 25
slope_window = 20
ma_window = 20

[trading_params]
max_holdings = 3
score_threshold = 0
min_positive_count = 5

[risk_params]
stop_loss_base = 0.05
trailing_stop_base = 0.05
take_profit_ratio = 0.10
```

### 策略参数调整

#### ETF轮动策略

```toml
[strategies.etf_rotation.params]
max_holdings = 3              # 最多持有标的数量
score_threshold = 0           # 因子得分阈值，高于阈值才买入
min_positive_count = 5        # 至少有多少个正向因子
```

#### 网格交易策略

```toml
[strategies.grid_trading.params]
grid_count = 10               # 网格数量
grid_spacing = 0.02           # 网格间距（2%）
price_range_pct = 0.20        # 价格范围（±20%）
take_profit_threshold = 0.10  # 止盈阈值（10%）
stop_loss_threshold = 0.15    # 止损阈值（15%）
```

#### 因子参数

```toml
[factor_params]
momentum_window = 25          # 动量窗口，值越大越稳定但反应越慢
slope_window = 20             # 斜率窗口
ma_window = 20                # 均线窗口
rsrs_window = 20              # RSRS窗口
volatility_window = 20        # 波动率窗口
```

#### 风控参数

```toml
[risk_params]
stop_loss_base = 0.05         # 基础止损，值越小止损越频繁
trailing_stop_base = 0.05     # 基础跟踪止损
take_profit_ratio = 0.10      # 基础止盈，值越小止盈越频繁
```

## 📈 策略比较

| 特性 | ETF轮动策略 | 网格交易策略 |
|------|------------|-------------|
| 适用市场 | 趋势市场 | 震荡市场 |
| 交易频率 | 低（每周调仓） | 高（频繁买卖） |
| 持仓数量 | 3-5个标的 | 1-3个标的 |
| 风险控制 | 多因子风控 | 止盈止损 |
| 收益来源 | 因子选股 | 网格套利 |

## 🎯 适用场景

### ETF轮动策略
- 趋势性市场
- 中长期投资（6个月以上）
- 风险偏好中等

### 网格交易策略
- 震荡市场
- 中短期交易（1-3个月）
- 风险偏好保守

## 📚 文档

- [新框架指南](NEW_FRAMEWORK_GUIDE.md) - 完整的新架构说明
- [项目总结](PROJECT_SUMMARY.md) - 重构完成总结
- [快速开始](QUICKSTART.md) - 快速上手指南

## 🔍 核心模块

### 回测引擎 (BacktestEngine)
- 统一的策略回测接口
- 支持单策略和多策略
- 自动生成回测报告

### 信号生成器 (SignalGenerator)
- 买入/卖出信号生成
- 信号质量评估
- 历史信号记录

### 参数搜索 (ParameterSearch)
- 三种优化算法
- 并行计算支持
- 结果自动保存

## ⚙️ 高级功能

### 1. 自定义策略

```python
from quant_strategies import BaseStrategy

class MyStrategy(BaseStrategy):
    @property
    def strategy_name(self):
        return "我的策略"

    def generate_signals(self):
        # 自定义信号生成逻辑
        return signals

    def calculate_indicators(self, data):
        # 自定义指标计算
        return indicators
```

### 2. 组合策略

```python
# 组合多种策略
engine = create_backtest_engine()
results = engine.run_backtest(None, data_dict)  # 运行所有启用策略
```

### 3. 实时信号生成

```python
# 仅生成信号，不执行交易
from quant_strategies import SignalOnlyBacktest

backtest = SignalOnlyBacktest()
signals = backtest.run(strategy_signals, data_dict)
```

## 📝 更新日志

### v2.0.0 (2024-12-11)
- ✅ 全新模块化架构
- ✅ 支持多策略系统
- ✅ 新增网格交易策略
- ✅ 新增参数优化模块
- ✅ 统一输出管理
- ✅ 精简代码库

### v1.0.0
- ✅ ETF轮动策略
- ✅ 多因子模型
- ✅ 动态风控

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 💡 提示

1. **数据准备**: 确保数据完整性和准确性
2. **参数优化**: 使用参数搜索找到最优参数
3. **风险管理**: 严格遵守风控规则
4. **回测验证**: 多市场环境下验证策略表现

## ❓ 常见问题

### Q: tushare token如何获取？
A: 访问 https://tushare.pro/ 注册账号（免费），登录后在"个人中心" -> "接口Token"中获取。每日有免费调用次数限制。

### Q: 如何配置token？
A: 推荐使用.env文件：
1. 复制 `.env.example` 为 `.env`
2. 在 `.env` 中设置 `TUSHARE_TOKEN=你的token`
3. 或者设置系统环境变量 `export TUSHARE_TOKEN='你的token'`

### Q: 数据下载失败？
A:
1. 检查是否正确设置了 `TUSHARE_TOKEN`（系统环境变量或.env文件）
2. 检查网络连接
3. 确认token是否有效（未过期）
4. 检查tushare调用次数是否超限

### Q: 回测结果不理想？
A: 尝试调整风控参数，或者使用更长的时间周期（至少3年）。

### Q: 如何添加新的ETF？
A: 修改`config.toml`中的`etf_list`部分，添加新的ETF代码和风格分类，然后重新下载数据。

### Q: 如何保存回测结果？
A: 结果会自动保存到`output/results/`目录，无需手动保存。

### Q: 提示未设置token？
A:
1. 确认已复制 `.env.example` 为 `.env`
2. 确认 `.env` 文件中设置了 `TUSHARE_TOKEN=你的token`
3. 或设置系统环境变量：`export TUSHARE_TOKEN='你的token'`

## 💡 策略优化建议

### 1. 因子参数优化

尝试不同的窗口期组合：

```toml
[factor_params]
momentum_window = 15     # 更敏感的动量
slope_window = 30        # 更平滑的质量
ma_window = 30
```

### 2. 风控参数优化

更严格的风控：

```toml
[risk_params]
stop_loss_base = 0.03    # 3%止损
take_profit_ratio = 0.08 # 8%止盈
```

### 3. 选股参数优化

更严格的选股：

```toml
[strategies.etf_rotation.params]
score_threshold = 0.1    # 只选得分>0.1的ETF
max_holdings = 2         # 减少到2只提高集中度
```

### 4. 参数优化

使用参数搜索找到最优参数：

```python
from quant_strategies import GridSearch

# 定义参数空间
param_space = {
    'max_holdings': [2, 3, 4],
    'score_threshold': [0, 0.05, 0.1],
    'stop_loss_base': [0.03, 0.05, 0.07]
}

# 执行优化
searcher = GridSearch(objective_func, param_space)
results = searcher.search()
```

## ⚠️ 注意事项

1. **数据质量**：确保数据完整性和准确性
2. **交易成本**：考虑实际交易中的佣金和滑点
3. **市场环境**：策略在不同市场环境下的表现可能不同
4. **风险控制**：严格遵守风控规则，避免过度回撤
5. **参数调优**：避免过拟合，使用样本外数据验证
6. **资金管理**：合理配置仓位，分散投资风险

## 📚 扩展阅读

- [backtrader官方文档](https://www.backtrader.com/)
- [量化交易入门](https://www.joinquant.com/)
- [多因子模型介绍](https://zhuanlan.zhihu.com/p/426896463)
- [tushare官网](https://tushare.pro/)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 支持

如有问题，请查看：
1. 项目文档（本文档）
2. 示例代码（examples目录）
3. GitHub Issues

---

**量化策略框架 v2.0** - 让量化交易更简单！
