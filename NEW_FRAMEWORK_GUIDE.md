# 量化策略框架 v2.0 - 新架构指南

## 概述

本项目已完全重构为现代化的量化策略框架，采用模块化架构，支持多种策略、回测引擎、信号生成和自动化参数优化。

## 🚀 新架构特点

### 1. **清晰的目录结构**
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
└── data/              # 数据模块
    └── data_loader.py       # 数据加载
```

### 2. **核心功能**

- **多策略支持**: 统一的策略接口，支持策略注册和管理
- **网格交易策略**: 专为震荡市场设计的网格交易算法
- **参数优化**: 支持网格搜索、随机搜索和贝叶斯优化
- **信号生成**: 买入/卖出信号生成和评估
- **回测引擎**: 统一的回测接口，支持单策略和多策略

### 3. **新增策略类型**

#### 网格交易策略 (GridTradingStrategy)
```python
# 特点
- 在固定价格区间内设置买卖网格点
- 当价格触及网格线时自动执行交易
- 适合震荡市场，通过频繁买卖获利
- 支持动态调整网格参数

# 参数
- grid_count: 网格数量 (默认10)
- grid_spacing: 网格间距 (默认2%)
- price_range_pct: 价格范围 (默认±20%)
- take_profit_threshold: 止盈阈值 (默认10%)
- stop_loss_threshold: 止损阈值 (默认15%)
```

## 📊 快速开始

### 1. 基本使用

```python
from quant_strategies import (
    load_config,
    create_strategy_manager,
    create_backtest_engine,
    create_parameter_search
)

# 加载配置
config = load_config()

# 创建策略管理器
manager = create_strategy_manager()

# 运行策略回测
engine = create_backtest_engine()
result = engine.run_backtest('grid_trading', data_dict)

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

# 策略会自动：
# 1. 在价格区间内设置15个网格点
# 2. 当价格触及网格线时自动交易
# 3. 达到止盈/止损条件时退出
```

### 3. 参数优化

```python
# 定义参数空间
param_space = {
    'grid_count': [10, 15, 20],
    'grid_spacing': [0.01, 0.015, 0.02],
    'price_range_pct': [0.15, 0.2, 0.25],
    'take_profit_threshold': [0.08, 0.1, 0.12]
}

# 网格搜索（穷举所有组合）
from quant_strategies import GridSearch
searcher = GridSearch(objective_func, param_space)
results = searcher.search()

# 随机搜索（随机采样）
from quant_strategies import RandomSearch
searcher = RandomSearch(objective_func, param_space, seed=42)
results = searcher.search(n_iterations=100)

# 贝叶斯优化（智能搜索）
from quant_strategies import BayesianOptimization
searcher = BayesianOptimization(objective_func, param_space)
results = searcher.search(n_iterations=50, n_initial_points=10)
```

## 📁 统一输出管理

### 输出目录结构

所有输出文件统一保存在 `output/` 目录下，按类型自动分类：

```
output/
├── results/          # 结果文件
│   ├── backtest_results_YYYYMMDD_HHMMSS.json    # 回测结果
│   ├── optimization_results_YYYYMMDD_HHMMSS.json # 参数优化结果
│   └── signals_YYYYMMDD_HHMMSS.csv               # 信号记录
├── charts/           # 图表文件
├── logs/             # 日志文件
└── reports/          # 报告文件
```

### 自动保存

所有核心模块都已配置为自动保存输出文件，无需手动调用保存方法：

- **回测结果**: 运行回测后自动保存到 `output/results/`
- **参数优化**: 优化完成后自动保存结果
- **信号记录**: 信号生成后自动保存

### 便捷函数

```python
# 示例代码会自动处理保存，无需额外操作
engine = create_backtest_engine()
result = engine.run_backtest('grid_trading', data_dict)
# 结果已自动保存到 output/results/backtest_results_YYYYMMDD_HHMMSS.json
```

## 🔍 策略比较

### ETF轮动策略 vs 网格交易策略

| 特性 | ETF轮动策略 | 网格交易策略 |
|------|------------|-------------|
| 适用市场 | 趋势市场 | 震荡市场 |
| 交易频率 | 低（每周调仓） | 高（频繁买卖） |
| 持仓数量 | 3-5个标的 | 1-3个标的 |
| 风险控制 | 多因子风控 | 止盈止损 |
| 收益来源 | 因子选股 | 网格套利 |
| 数据需求 | 高（多因子） | 低（价格+成交量） |

### 最佳实践

```python
# 1. 网格策略适合场景
- 市场处于震荡状态
- 价格在固定区间内波动
- 成交量充足
- 交易成本较低

# 2. ETF轮动策略适合场景
- 市场有明确趋势
- 多因子数据充足
- 长期投资目标
- 风险承受能力中等
```

## 🛠️ 高级功能

### 1. 自定义策略

```python
from quant_strategies import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    @property
    def strategy_name(self) -> str:
        return "我的自定义策略"

    @property
    def strategy_description(self) -> str:
        return "描述我的策略"

    def generate_signals(self) -> Dict[str, Any]:
        # 实现信号生成逻辑
        pass

    def calculate_indicators(self, data) -> Dict[str, Any]:
        # 实现指标计算
        pass

    def check_exit_conditions(self, symbol: str, data) -> Dict[str, Any]:
        # 实现退出条件
        pass
```

### 2. 多策略组合

```python
# 同时运行多个策略
engine = create_backtest_engine()
results = engine.run_multiple_strategies(
    strategy_names=['etf_rotation', 'grid_trading'],
    data_dict=data_dict
)

# 比较策略表现
comparison = engine.compare_strategies(['etf_rotation', 'grid_trading'])
print(comparison)
```

### 3. 信号分析

```python
from quant_strategies import SignalGenerator

generator = SignalGenerator()
signals = generator.generate_signals(strategy_signals)

# 评估信号质量
evaluation = generator.evaluate_signals(signals)
print(f"信号质量: {evaluation['signal_quality']:.2%}")

# 生成信号报告
generator.print_signal_report(signals)
```

## 📈 性能优化

### 1. 并行参数搜索

```python
# 使用多进程并行搜索
searcher = GridSearch(
    objective_func,
    param_space,
    n_jobs=4  # 使用4个进程
)
```

### 2. 缓存计算结果

```python
class MyStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        self._indicator_cache = {}

    def calculate_indicators(self, data):
        if data not in self._indicator_cache:
            self._indicator_cache[data] = self._compute_indicators(data)
        return self._indicator_cache[data]
```

### 3. 数据预处理

```python
# 预处理数据以提高性能
def preprocess_data(data_dict):
    for symbol, df in data_dict.items():
        # 计算常用指标
        df['returns'] = df['Close'].pct_change()
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['volatility'] = df['returns'].rolling(20).std()
    return data_dict
```

## 🔧 配置管理

### 1. TOML配置

```toml
# config.toml

[strategies.etf_rotation]
enabled = true
name = "ETF轮动策略"
description = "基于多因子模型的ETF轮动策略"
params = { max_holdings = 3, score_threshold = 0 }

[strategies.grid_trading]
enabled = true
name = "网格交易策略"
description = "基于价格区间的网格交易策略"
params = { grid_count = 10, grid_spacing = 0.02 }
```

### 2. 动态配置

```python
# 运行时修改参数
engine = create_backtest_engine()
result = engine.run_backtest(
    'grid_trading',
    data_dict,
    config_overrides={
        'params': {
            'grid_count': 20,
            'grid_spacing': 0.015
        }
    }
)
```

## 📚 示例代码

### 1. 完整回测示例

```python
import sys
sys.path.insert(0, 'src')

from quant_strategies import (
    load_config,
    create_backtest_engine
)

# 加载数据
config = load_config()
data_dict = load_your_data()

# 运行回测
engine = create_backtest_engine()
result = engine.run_backtest('grid_trading', data_dict)

# 查看结果
print(f"总收益率: {result['total_return']:.2f}%")
print(f"夏普比率: {result['sharpe_ratio']:.2f}")
print(f"最大回撤: {result['max_drawdown']:.2f}%")
```

### 2. 参数优化示例

```python
from quant_strategies import RandomSearch

# 定义目标函数
def objective_func(params):
    engine = create_backtest_engine()
    result = engine.run_backtest('grid_trading', data_dict, config_overrides={'params': params})
    return result.get('total_return', 0)

# 定义参数空间
param_space = {
    'grid_count': [8, 10, 12, 15],
    'grid_spacing': [0.01, 0.015, 0.02, 0.025],
    'price_range_pct': [0.15, 0.2, 0.25, 0.3]
}

# 执行优化
searcher = RandomSearch(objective_func, param_space, maximize=True, seed=42)
results = searcher.search(n_iterations=200)

print(f"最佳参数: {results['best_params']}")
print(f"最佳分数: {results['best_score']:.2f}%")
```

### 3. 多策略比较示例

```python
# 比较不同策略
strategies = ['etf_rotation', 'grid_trading']
results = {}

for strategy in strategies:
    engine = create_backtest_engine()
    result = engine.run_backtest(strategy, data_dict)
    results[strategy] = result

# 输出比较结果
for strategy, result in results.items():
    print(f"\n{strategy}:")
    print(f"  总收益率: {result['total_return']:.2f}%")
    print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"  最大回撤: {result['max_drawdown']:.2f}%")
```

## 🎯 最佳实践

### 1. 策略开发

- **继承BaseStrategy**: 所有策略必须继承自BaseStrategy
- **实现抽象方法**: 必须实现generate_signals、calculate_indicators、check_exit_conditions
- **配置驱动**: 使用配置文件管理策略参数
- **日志记录**: 使用self.log()记录重要信息

### 2. 回测最佳实践

```python
# 1. 验证数据质量
assert all(len(data) > 100 for data in data_dict.values()), "数据不足"

# 2. 使用合理的初始资金
initial_cash = 1_000_000

# 3. 包含交易成本
cerebro.broker.setcommission(commission=0.00025)
cerebro.slippage = 0.0003

# 4. 添加分析器
cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

# 5. 保存结果
engine.save_results('backtest_results.json')
```

### 3. 参数优化最佳实践

```python
# 1. 定义合理的参数空间
param_space = {
    'grid_count': [5, 8, 10, 12, 15],  # 不要太多值
    'grid_spacing': [0.01, 0.015, 0.02, 0.025, 0.03]
}

# 2. 使用交叉验证
def objective_func(params):
    # 计算多个期间的分数
    scores = []
    for start_date in ['2020-01-01', '2021-01-01', '2022-01-01']:
        result = run_backtest(start_date, params)
        scores.append(result['total_return'])
    return np.mean(scores)  # 返回平均分数

# 3. 保存优化结果
searcher.save_results('optimization_results.json')

# 4. 分析结果分布
df = searcher.get_results_dataframe()
print(df.describe())
```

## 📖 示例文件

- `examples/parameter_optimization.py`: 参数优化完整示例
- `examples/multi_strategy_demo.py`: 多策略演示
- `examples/quick_start_multi_strategy.py`: 快速开始指南

## 🔜 未来规划

- [ ] 添加更多策略类型（均值回归、动量、统计套利等）
- [ ] 集成机器学习模型进行参数优化
- [ ] 支持实时交易
- [ ] 添加组合优化模块
- [ ] 支持更多数据源（Wind、东方财富等）
- [ ] 添加风险预算管理
- [ ] 支持多资产组合优化

## 📝 更新日志

### v2.0.0 (2024-12-11)
- ✅ 完全重构项目架构
- ✅ 实现网格交易策略
- ✅ 添加参数优化模块
- ✅ 支持多种搜索算法
- ✅ 优化目录结构
- ✅ 更新配置管理
- ✅ 添加详细文档

### v1.0.0 (之前版本)
- ✅ ETF轮动策略
- ✅ 基础回测框架
- ✅ 因子计算
- ✅ 风控管理

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 提交规范

1. **代码风格**: 遵循PEP 8
2. **类型提示**: 添加完整的类型注解
3. **文档**: 包含详细的docstring
4. **测试**: 提供测试用例
5. **示例**: 添加使用示例

### 开发流程

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/quant-strategies.git

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -e .

# 4. 运行测试
pytest tests/

# 5. 提交代码
git commit -m "feat: add new strategy"
git push origin feature/new-strategy
```

## 📄 许可证

MIT License

## 📞 联系方式

- Email: dev@example.com
- GitHub: https://github.com/your-repo/quant-strategies

---

**感谢使用量化策略框架 v2.0！** 🎉
