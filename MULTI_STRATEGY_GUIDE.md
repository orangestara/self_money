# 多策略系统使用指南

## 概述

本项目已扩展为支持多种量化策略的统一框架，包括：

- **多策略管理**: 注册、配置和管理多个策略
- **策略回测**: 统一的回测引擎，支持单个或多个策略
- **信号生成**: 买入/卖出信号生成和评估
- **策略工厂**: 动态创建和管理策略实例
- **配置驱动**: 通过TOML配置文件管理所有策略

## 架构设计

### 核心组件

```
etf_rotation/
├── base_strategy.py          # 策略基类
├── strategy_manager.py       # 策略管理器
├── strategy_factory.py       # 策略工厂
├── backtest_engine.py        # 回测引擎
├── signal_generator.py       # 信号生成器
├── config.py                 # 配置加载器
└── strategies/
    ├── __init__.py
    └── etf_rotation.py       # ETF轮动策略实现
```

### 类层次结构

```
BaseStrategy (抽象基类)
├── ETFRotationStrategy (ETF轮动策略)
└── SignalOnlyStrategy (信号策略)
```

## 快速开始

### 1. 基本回测

```python
from etf_rotation import create_backtest_engine

# 创建回测引擎
engine = create_backtest_engine()

# 运行ETF轮动策略
result = engine.run_backtest('etf_rotation', data_dict)

# 打印结果
print(f"总收益率: {result['total_return']:.2f}%")
```

### 2. 买入信号生成

```python
from etf_rotation import create_strategy_manager

# 创建策略管理器
manager = create_strategy_manager()

# 生成信号
signals = manager.generate_signals('etf_rotation', data_dict)

# 查看信号
for symbol, signal in signals['signals'].items():
    print(f"{symbol}: {signal['action']} (权重变化: {signal['weight_change']:.2%})")
```

### 3. 多策略回测

```python
from etf_rotation import BacktestEngine

engine = BacktestEngine()

# 运行多个策略
results = engine.run_multiple_strategies(
    strategy_names=['etf_rotation', 'mean_reversion'],
    data_dict=data_dict
)

# 比较策略
comparison = engine.compare_strategies(['etf_rotation', 'mean_reversion'])
print(comparison)
```

## 详细使用说明

### 策略基类 (BaseStrategy)

所有策略必须继承自`BaseStrategy`并实现以下抽象方法：

```python
class MyStrategy(BaseStrategy):
    @property
    def strategy_name(self) -> str:
        return "我的策略"

    @property
    def strategy_description(self) -> str:
        return "策略描述"

    def generate_signals(self) -> Dict[str, Any]:
        """生成买入/卖出信号"""
        # 实现信号生成逻辑
        pass

    def calculate_indicators(self, data) -> Dict[str, Any]:
        """计算技术指标"""
        # 实现指标计算
        pass

    def check_exit_conditions(self, symbol: str, data) -> Dict[str, Any]:
        """检查退出条件"""
        # 实现退出条件检查
        pass
```

### 策略管理器 (StrategyManager)

负责注册和管理多个策略：

```python
from etf_rotation import StrategyManager

manager = StrategyManager()

# 注册新策略
manager.register_strategy(
    name='my_strategy',
    strategy_class=MyStrategy,
    description='我的策略描述',
    config={'param1': value1}
)

# 列出所有策略
strategies = manager.list_strategies()
for name, info in strategies.items():
    print(f"{name}: {info['description']}")

# 启用/禁用策略
manager.enable_strategy('my_strategy')
manager.disable_strategy('my_strategy')
```

### 策略工厂 (StrategyFactory)

动态创建策略实例：

```python
from etf_rotation import StrategyFactory

factory = StrategyFactory()

# 创建策略实例
strategy = factory.create_strategy('etf_rotation', {
    'params': {
        'max_holdings': 2,
        'score_threshold': 0.1
    }
})

# 批量创建策略
instances = factory.batch_create_strategies({
    'etf_rotation': {'params': {...}},
    'mean_reversion': {'params': {...}}
})
```

### 回测引擎 (BacktestEngine)

统一的回测接口：

```python
from etf_rotation import BacktestEngine

engine = BacktestEngine()

# 单策略回测
result = engine.run_single_strategy(
    'etf_rotation',
    data_dict,
    start_date='2020-01-01',
    end_date='2024-12-31',
    initial_cash=1000000
)

# 多策略回测
results = engine.run_multiple_strategies(
    strategy_names=['etf_rotation', 'mean_reversion'],
    data_dict=data_dict
)

# 生成信号
signals = engine.generate_signals('etf_rotation', data_dict)

# 比较策略
comparison = engine.compare_strategies(['etf_rotation', 'mean_reversion'])
```

### 信号生成器 (SignalGenerator)

生成和评估买入/卖出信号：

```python
from etf_rotation import SignalGenerator, Signal

generator = SignalGenerator()

# 生成信号
signals = generator.generate_signals(strategy_signals)

# 获取买入信号
buy_signals = generator.get_buy_signals(signals)

# 评估信号质量
evaluation = generator.evaluate_signals(signals)
print(f"信号质量: {evaluation['signal_quality']:.2%}")

# 打印信号报告
generator.print_signal_report(signals)
```

## 配置管理

### TOML配置格式

在`config.toml`中添加策略配置：

```toml
# 多策略配置
[strategies]
default_initial_cash = 1_000_000

[strategies.etf_rotation]
enabled = true
name = "ETF轮动策略"
description = "基于多因子模型的ETF轮动策略"
execute_trades = true
params = { max_holdings = 3, score_threshold = 0 }

[strategies.mean_reversion]
enabled = false
name = "均值回归策略"
description = "基于技术指标的均值回归策略"
execute_trades = false
params = { lookback = 20, entry_threshold = 2.0 }
```

### 配置加载

```python
from etf_rotation import load_config, get_strategy_config

config = load_config()

# 获取策略配置
strategy_config = get_strategy_config(config, 'etf_rotation')
print(f"策略名称: {strategy_config['name']}")

# 获取策略参数
params = strategy_config.get('params', {})
print(f"参数: {params}")

# 检查策略是否启用
enabled = strategy_config.get('enabled', False)
```

## 示例代码

### 示例1: 快速开始

```python
import sys
import os
import pandas as pd

from etf_rotation import (
    create_backtest_engine,
    create_strategy_manager,
    load_config
)

# 1. 加载配置
config = load_config()
etf_list = config.get('etf_list', [])[:3]
symbols = [etf['symbol'] for etf in etf_list]

# 2. 加载数据
data_dict = load_data(symbols)  # 您的数据加载函数

# 3. 运行回测
engine = create_backtest_engine()
result = engine.run_backtest('etf_rotation', data_dict)

print(f"总收益率: {result['total_return']:.2f}%")

# 4. 生成信号
manager = create_strategy_manager()
signals = manager.generate_signals('etf_rotation', data_dict)

print(f"信号数量: {len(signals['signals'])}")
```

### 示例2: 自定义策略

```python
from etf_rotation import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    @property
    def strategy_name(self) -> str:
        return "自定义策略"

    @property
    def strategy_description(self) -> str:
        return "我开发的自定义策略"

    def generate_signals(self) -> Dict[str, Any]:
        signals = {}
        for symbol, data in self.data_dict.items():
            # 计算移动平均
            close = data.close[0]
            ma20 = data.close.get(0, period=-20).mean()
            ma50 = data.close.get(0, period=-50).mean()

            if ma20 > ma50:
                signals[symbol] = {
                    'action': 'buy',
                    'target_weight': 0.1
                }
            elif ma20 < ma50:
                signals[symbol] = {
                    'action': 'sell',
                    'target_weight': 0
                }

        return {'signals': signals, 'positions': signals}

    def calculate_indicators(self, data) -> Dict[str, Any]:
        return {'ma20': data.close.get(0, period=-20).mean()}

    def check_exit_conditions(self, symbol: str, data) -> Dict[str, Any]:
        return {'exit': False, 'reason': ''}

# 注册策略
from etf_rotation import StrategyManager

manager = StrategyManager()
manager.register_strategy(
    'my_custom',
    MyCustomStrategy,
    '我的自定义策略'
)

manager.enable_strategy('my_custom')

# 运行策略
engine = create_backtest_engine()
result = engine.run_backtest('my_custom', data_dict)
```

### 示例3: 信号分析

```python
from etf_rotation import SignalGenerator

generator = SignalGenerator()

# 模拟策略信号
strategy_signals = {
    '159985.SZ': {
        'signals': {
            '159985.SZ': {
                'action': 'buy',
                'current_weight': 0.0,
                'target_weight': 0.3,
                'weight_change': 0.3
            }
        },
        'reason': '动量因子得分高'
    }
}

# 生成信号
signals = generator.generate_signals(strategy_signals)

# 评估信号
evaluation = generator.evaluate_signals(signals)
print(f"信号质量: {evaluation['signal_quality']:.2%}")
print(f"买入信号数量: {evaluation['buy_count']}")
print(f"卖出信号数量: {evaluation['sell_count']}")

# 打印报告
generator.print_signal_report(signals)

# 保存信号
generator.save_signals('signals.csv')
```

## 最佳实践

### 1. 策略开发

- **继承基类**: 所有策略必须继承自`BaseStrategy`
- **实现抽象方法**: 必须实现`generate_signals`、`calculate_indicators`、`check_exit_conditions`
- **配置驱动**: 使用配置文件管理策略参数
- **日志记录**: 使用`self.log()`记录重要信息

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

### 3. 信号生成

```python
# 1. 过滤弱信号
signals = [s for s in signals if s.strength > 0.02]

# 2. 排序信号
sorted_signals = sorted(signals, key=lambda x: x.score, reverse=True)

# 3. 限制信号数量
top_signals = sorted_signals[:5]

# 4. 评估信号质量
quality = generator.evaluate_signals(top_signals)
if quality['signal_quality'] < 0.5:
    print("信号质量较低，建议谨慎使用")
```

### 4. 性能优化

```python
# 1. 缓存计算结果
class MyStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        self._indicator_cache = {}

    def calculate_indicators(self, data):
        # 缓存指标计算结果
        if data not in self._indicator_cache:
            self._indicator_cache[data] = self._compute_indicators(data)
        return self._indicator_cache[data]

# 2. 使用向量化计算
import numpy as np
import pandas as pd

def calculate_ma(data, window):
    return pd.Series(data).rolling(window).mean().iloc[-1]
```

## 常见问题

### Q1: 如何添加新的策略？

A1: 按照以下步骤：
1. 继承`BaseStrategy`类
2. 实现所有抽象方法
3. 在`StrategyManager`中注册策略
4. 在`config.toml`中添加配置

### Q2: 如何比较多个策略？

A2: 使用`BacktestEngine.compare_strategies()`方法：
```python
engine = BacktestEngine()
results = engine.run_multiple_strategies(['etf_rotation', 'mean_reversion'], data_dict)
comparison = engine.compare_strategies(['etf_rotation', 'mean_reversion'])
print(comparison)
```

### Q3: 如何保存和加载回测结果？

A3: 使用`save_results()`和`load_results()`方法：
```python
# 保存
engine.save_results('results.json')

# 加载
engine.load_results('results.json')
```

### Q4: 如何自定义信号评估？

A4: 继承`SignalEvaluator`类：
```python
class MySignalEvaluator(SignalEvaluator):
    def evaluate_signal_performance(self, signals, price_data, holding_period):
        # 自定义评估逻辑
        pass
```

## 扩展阅读

- [Backtrader文档](https://www.backtrader.com/)
- [Pandas用户指南](https://pandas.pydata.org/docs/user_guide/)
- [量化交易策略开发](https://github.com/quantopian/research_public)

## 贡献指南

欢迎贡献新的策略实现！请遵循以下规范：

1. 策略必须继承自`BaseStrategy`
2. 实现所有必需的抽象方法
3. 包含完整的文档字符串
4. 提供使用示例
5. 通过单元测试

提交Pull Request时，请确保：
- 代码风格符合PEP 8
- 包含类型提示
- 添加适当的注释
- 提供测试用例
