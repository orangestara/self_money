# 量化策略框架 v2.0

基于Backtrader的现代化量化策略框架，支持多种策略、回测引擎、信号生成和自动化参数优化。

## 🚀 核心特性

### 多策略支持
- **ETF轮动策略**：基于多因子模型的趋势跟踪策略
- **网格交易策略**：专为震荡市场设计的网格套利策略
- 支持策略注册、配置管理和动态切换

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
```

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

## 📞 支持

如有问题，请查看：
1. 项目文档
2. 示例代码
3. GitHub Issues

---

**量化策略框架 v2.0** - 让量化交易更简单！
