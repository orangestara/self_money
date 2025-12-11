"""
策略回测引擎

提供统一的策略回测接口，支持单个策略和多个策略的回测
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import json

from ..managers.strategy_manager import StrategyManager
from ..core.signal_generator import SignalGenerator, Signal
from ..core.config import (
    load_config,
    get_backtest_params,
    get_cost_params,
    get_enabled_strategies,
)
from ..core.utils import format_currency, format_percentage


class BacktestEngine:
    """回测引擎"""

    def __init__(self, config_path: str = None):
        """初始化回测引擎

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = load_config(config_path) if config_path else load_config()
        self.backtest_params = get_backtest_params(self.config)
        self.cost_params = get_cost_params(self.config)

        # 输出目录
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'output')
        os.makedirs(os.path.join(self.output_dir, 'results'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'charts'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'reports'), exist_ok=True)

        # 策略管理器
        self.strategy_manager = StrategyManager(config_path)

        # 信号生成器
        self.signal_generator = SignalGenerator(self.config)

        # 回测结果
        self.results = {}

    def run_backtest(self,
                    strategy_name: str = None,
                    data_dict: Dict[str, pd.DataFrame] = None,
                    config_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行回测

        Args:
            strategy_name: 策略名称，None表示运行所有启用的策略
            data_dict: 数据字典
            config_overrides: 配置覆盖

        Returns:
            回测结果
        """
        # 如果没有指定策略，运行所有启用的策略
        if strategy_name is None:
            return self.run_multiple_strategies(
                list(get_enabled_strategies(self.config).keys()),
                data_dict,
                config_overrides
            )

        # 运行单个策略
        return self.run_single_strategy(strategy_name, data_dict, config_overrides)

    def run_single_strategy(self,
                           strategy_name: str,
                           data_dict: Dict[str, pd.DataFrame] = None,
                           config_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """运行单个策略回测

        Args:
            strategy_name: 策略名称
            data_dict: 数据字典
            config_overrides: 配置覆盖

        Returns:
            回测结果
        """
        # 合并配置
        strategy_config = {}
        if config_overrides:
            strategy_config.update(config_overrides)

        # 运行回测
        result = self.strategy_manager.run_single_strategy(
            strategy_name,
            data_dict,
            self.backtest_params['start_date'],
            self.backtest_params['end_date'],
            self.backtest_params['initial_cash'],
            strategy_config
        )

        # 保存结果
        self.results[strategy_name] = result

        return result

    def run_multiple_strategies(self,
                               strategy_names: List[str],
                               data_dict: Dict[str, pd.DataFrame] = None,
                               config_overrides: Dict[str, Any] = None) -> Dict[str, Dict[str, Any]]:
        """运行多个策略回测

        Args:
            strategy_names: 策略名称列表
            data_dict: 数据字典
            config_overrides: 配置覆盖

        Returns:
            所有策略的回测结果
        """
        results = {}

        for strategy_name in strategy_names:
            print(f"\n运行策略: {strategy_name}")
            result = self.run_single_strategy(
                strategy_name,
                data_dict,
                config_overrides
            )
            results[strategy_name] = result

        # 保存结果
        self.results.update(results)

        return results

    def generate_signals(self,
                        strategy_name: str = None,
                        data_dict: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """生成信号

        Args:
            strategy_name: 策略名称，None表示生成所有策略的信号
            data_dict: 数据字典

        Returns:
            信号结果
        """
        if strategy_name:
            # 生成单个策略的信号
            return self.strategy_manager.generate_signals(
                strategy_name,
                data_dict
            )

        # 生成所有启用策略的信号
        all_signals = {}
        enabled_strategies = get_enabled_strategies(self.config)

        for name in enabled_strategies.keys():
            signals = self.strategy_manager.generate_signals(name, data_dict)
            all_signals[name] = signals

        # 综合所有信号
        combined_signals = self._combine_signals(all_signals)

        return combined_signals

    def _combine_signals(self, strategy_signals: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个策略的信号

        Args:
            strategy_signals: 策略信号字典

        Returns:
            合并后的信号
        """
        # 收集所有symbol的信号
        all_symbols = set()
        for signals in strategy_signals.values():
            if 'signals' in signals:
                for symbol in signals['signals'].keys():
                    all_symbols.add(symbol)

        # 合并信号
        combined = {}
        for symbol in all_symbols:
            symbol_signals = []

            for strategy_name, signals in strategy_signals.items():
                if 'signals' in signals and symbol in signals['signals']:
                    symbol_signals.append({
                        'strategy': strategy_name,
                        'signal': signals['signals'][symbol]
                    })

            if symbol_signals:
                # 计算综合信号
                combined[symbol] = self._calculate_combined_signal(symbol_signals)

        return {
            'combined_signals': combined,
            'individual_signals': strategy_signals
        }

    def _calculate_combined_signal(self, symbol_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算单个标的的综合信号

        Args:
            symbol_signals: 标的所有策略的信号

        Returns:
            综合信号
        """
        if not symbol_signals:
            return {'action': 'hold', 'score': 0, 'strength': 0}

        # 计算加权平均得分
        total_score = 0
        total_weight = 0
        actions = []

        for item in symbol_signals:
            signal = item['signal']
            weight = signal.get('weight_change', 0)

            if signal.get('action') == 'buy':
                total_score += signal.get('target_weight', 0) * abs(weight)
                actions.append('buy')
            elif signal.get('action') == 'sell':
                total_score -= signal.get('target_weight', 0) * abs(weight)
                actions.append('sell')

            total_weight += abs(weight)

        if total_weight > 0:
            avg_score = total_score / total_weight
        else:
            avg_score = 0

        # 决定最终动作
        if avg_score > 0.01:
            action = 'buy'
        elif avg_score < -0.01:
            action = 'sell'
        else:
            action = 'hold'

        return {
            'action': action,
            'score': avg_score,
            'strength': total_weight,
            'strategy_count': len(symbol_signals)
        }

    def compare_strategies(self, strategy_names: List[str] = None) -> pd.DataFrame:
        """比较策略表现

        Args:
            strategy_names: 策略名称列表，None表示比较所有已运行的策略

        Returns:
            比较结果DataFrame
        """
        if strategy_names is None:
            strategy_names = list(self.results.keys())

        return self.strategy_manager.compare_strategies(strategy_names)

    def print_backtest_report(self):
        """打印回测报告"""
        if not self.results:
            print("暂无回测结果")
            return

        print("\n" + "=" * 80)
        print("回测报告")
        print("=" * 80)
        print(f"回测期间: {self.backtest_params['start_date']} 至 {self.backtest_params['end_date']}")
        print(f"初始资金: {format_currency(self.backtest_params['initial_cash'])}")
        print()

        for name, result in self.results.items():
            print(f"\n策略: {name}")
            print("-" * 60)
            if 'error' in result:
                print(f"错误: {result['error']}")
                continue

            print(f"最终资金: {format_currency(result.get('final_value', 0))}")
            print(f"总收益率: {format_percentage(result.get('total_return', 0) / 100)}")
            print(f"夏普比率: {result.get('sharpe_ratio', 0):.2f}")
            print(f"最大回撤: {format_percentage(result.get('max_drawdown', 0))}")
            print(f"交易次数: {result.get('total_trades', 0)}")
            print(f"胜率: {result.get('win_rate', 0):.2%}")

        print("\n" + "=" * 80)

        # 自动保存结果
        self.save_results()

    def save_results(self, filepath: str = None):
        """保存回测结果

        Args:
            filepath: 保存路径，默认为output/results/backtest_results.json
        """
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(self.output_dir, 'results', f'backtest_results_{timestamp}.json')

        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # 准备可序列化的数据
        serializable_results = {}
        for name, result in self.results.items():
            serializable_results[name] = {}
            for key, value in result.items():
                if isinstance(value, (int, float, str, dict, list)):
                    serializable_results[name][key] = value
                else:
                    serializable_results[name][key] = str(value)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        print(f"✓ 回测结果已保存到: {filepath}")
        return filepath

    def load_results(self, filepath: str):
        """加载回测结果

        Args:
            filepath: 文件路径
        """
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            self.results = json.load(f)

        print(f"已加载 {len(self.results)} 个策略的回测结果")


class SignalOnlyBacktest:
    """仅生成信号不回测的轻量级回测"""

    def __init__(self, config: Dict[str, Any] = None):
        """初始化

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.signals = []

    def run(self,
            strategy_signals: Dict[str, Dict[str, Any]],
            data_dict: Dict[str, pd.DataFrame] = None) -> List[Signal]:
        """运行信号生成

        Args:
            strategy_signals: 策略信号
            data_dict: 数据字典

        Returns:
            信号列表
        """
        from ..core.signal_generator import SignalGenerator

        generator = SignalGenerator(self.config)
        signals = generator.generate_signals(strategy_signals)

        self.signals = signals

        return signals
