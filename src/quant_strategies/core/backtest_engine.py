"""
策略回测引擎

提供统一的策略回测接口，支持单个策略和多个策略的回测
"""

import backtrader as bt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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

        # 输出目录 - 计算到项目根目录
        current_dir = os.path.dirname(os.path.dirname(__file__))  # core/
        parent_dir = os.path.dirname(current_dir)  # quant_strategies/
        project_root = os.path.dirname(parent_dir)  # src/
        self.output_dir = os.path.join(project_root, '..', 'output')
        self.output_dir = os.path.abspath(self.output_dir)
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

        # 保存到文件
        self._save_result(strategy_name, result)

        # 绘制图表
        self._plot_result(strategy_name, result)

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

    def _save_result(self, strategy_name: str, result: Dict[str, Any]):
        """保存回测结果到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{strategy_name}_result_{timestamp}.json"
        filepath = os.path.join(self.output_dir, 'results', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        print(f"✓ 结果已保存到: {filepath}")

    def _plot_result(self, strategy_name: str, result: Dict[str, Any]):
        """绘制回测结果图表"""
        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

            # 创建图表
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'{strategy_name} 策略回测结果', fontsize=16, fontweight='bold')

            # 1. 收益曲线
            ax1 = axes[0, 0]
            if 'returns' in result and isinstance(result['returns'], list) and len(result['returns']) > 0:
                try:
                    dates = []
                    values = []
                    for item in result['returns']:
                        if isinstance(item, dict) and 'date' in item and 'value' in item:
                            # 处理日期格式，支持 "2020-01-01 00:00:00" 和 "2020-01-01"
                            date_str = item['date'].split(' ')[0]  # 只取日期部分
                            dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
                            values.append(item['value'] or 0.0)
                    if dates and values:
                        ax1.plot(dates, values, linewidth=2, color='blue', label='策略收益')
                        ax1.set_title('累计收益曲线')
                        ax1.set_ylabel('累计收益 (%)')
                        ax1.grid(True, alpha=0.3)
                        ax1.legend()
                    else:
                        raise ValueError("Invalid data format")
                except Exception as e:
                    ax1.text(0.5, 0.5, f'收益数据格式错误\n{str(e)[:50]}...', ha='center', va='center', transform=ax1.transAxes)
                    ax1.set_title('累计收益曲线')
            else:
                ax1.text(0.5, 0.5, '收益数据不可用', ha='center', va='center', transform=ax1.transAxes)
                ax1.set_title('累计收益曲线')

            # 2. 回撤曲线
            ax2 = axes[0, 1]
            if 'drawdown' in result and isinstance(result['drawdown'], list) and len(result['drawdown']) > 0:
                try:
                    dates = []
                    drawdowns = []
                    for item in result['drawdown']:
                        if isinstance(item, dict) and 'date' in item and 'value' in item:
                            dates.append(datetime.strptime(item['date'], '%Y-%m-%d'))
                            drawdowns.append(item['value'])
                    if dates and drawdowns:
                        ax2.fill_between(dates, drawdowns, 0, alpha=0.3, color='red', label='回撤')
                        ax2.set_title('回撤曲线')
                        ax2.set_ylabel('回撤 (%)')
                        ax2.grid(True, alpha=0.3)
                        ax2.legend()
                    else:
                        raise ValueError("Invalid data format")
                except Exception:
                    ax2.text(0.5, 0.5, '回撤数据格式错误', ha='center', va='center', transform=ax2.transAxes)
                    ax2.set_title('回撤曲线')
            else:
                ax2.text(0.5, 0.5, '回撤数据不可用', ha='center', va='center', transform=ax2.transAxes)
                ax2.set_title('回撤曲线')

            # 3. 持仓变化
            ax3 = axes[1, 0]
            if 'positions' in result and isinstance(result['positions'], list) and len(result['positions']) > 0:
                try:
                    dates = []
                    positions = []
                    for item in result['positions']:
                        if isinstance(item, dict) and 'date' in item and 'value' in item:
                            dates.append(datetime.strptime(item['date'], '%Y-%m-%d'))
                            positions.append(item['value'])
                    if dates and positions:
                        ax3.plot(dates, positions, linewidth=2, color='green', label='持仓数量')
                        ax3.set_title('持仓变化')
                        ax3.set_ylabel('持仓数量')
                        ax3.grid(True, alpha=0.3)
                        ax3.legend()
                    else:
                        raise ValueError("Invalid data format")
                except Exception:
                    ax3.text(0.5, 0.5, '持仓数据格式错误', ha='center', va='center', transform=ax3.transAxes)
                    ax3.set_title('持仓变化')
            else:
                ax3.text(0.5, 0.5, '持仓数据不可用', ha='center', va='center', transform=ax3.transAxes)
                ax3.set_title('持仓变化')

            # 4. 统计信息
            ax4 = axes[1, 1]
            ax4.axis('off')

            # 安全获取值，避免None
            final_value = result.get('final_value', 0) or 0
            total_return = result.get('total_return', 0) or 0
            annualized_return = result.get('annualized_return', 0) or 0
            sharpe_ratio = result.get('sharpe_ratio', 0) or 0
            max_drawdown = result.get('max_drawdown', 0) or 0
            total_trades = result.get('total_trades', 0) or 0
            win_rate = result.get('win_rate', 0) or 0

            stats_text = f"""
最终资金: {format_currency(final_value)}
总收益: {format_currency(final_value - 1000000)}
总收益率: {format_percentage(total_return / 100)}
年化收益率: {format_percentage(annualized_return)}
夏普比率: {sharpe_ratio:.2f}
最大回撤: {format_percentage(max_drawdown)}
交易次数: {total_trades}
胜率: {win_rate:.2%}
            """
            ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes, fontsize=11,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

            # 调整布局
            plt.tight_layout()

            # 保存图表
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_filename = f"{strategy_name}_chart_{timestamp}.png"
            chart_filepath = os.path.join(self.output_dir, 'charts', chart_filename)
            plt.savefig(chart_filepath, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存到: {chart_filepath}")

            # 显示图表（如果在交互式环境中）
            plt.close(fig)

        except Exception as e:
            print(f"绘制图表失败: {e}")
            import traceback
            traceback.print_exc()


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
