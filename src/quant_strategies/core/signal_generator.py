"""
买入信号生成器

负责生成、评估和管理买入信号
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class Signal:
    """信号数据类"""
    symbol: str
    action: str  # buy, sell, hold
    strength: float  # 信号强度 (0-1)
    score: float  # 综合得分
    reason: str  # 信号原因
    timestamp: datetime
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SignalGenerator:
    """买入信号生成器"""

    def __init__(self, config: Dict[str, Any] = None):
        """初始化信号生成器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.signal_history = []  # 信号历史
        self.signal_cache = {}  # 信号缓存

    def generate_signals(self,
                        strategy_signals: Dict[str, Dict[str, Any]],
                        current_positions: Dict[str, float] = None) -> List[Signal]:
        """生成综合买入信号

        Args:
            strategy_signals: 策略信号 {symbol: signal_info}
            current_positions: 当前持仓 {symbol: weight}

        Returns:
            信号列表
        """
        signals = []

        for symbol, signal_info in strategy_signals.items():
            if 'signals' not in signal_info:
                continue

            for symbol, details in signal_info['signals'].items():
                # 提取信号信息
                action = details.get('action', 'hold')
                strength = abs(details.get('weight_change', 0))
                score = details.get('target_weight', 0)
                reason = signal_info.get('reason', '')

                # 创建信号
                signal = Signal(
                    symbol=symbol,
                    action=action,
                    strength=strength,
                    score=score,
                    reason=reason,
                    timestamp=datetime.now(),
                    metadata={
                        'current_weight': details.get('current_weight', 0),
                        'target_weight': details.get('target_weight', 0),
                        'weight_change': details.get('weight_change', 0)
                    }
                )

                signals.append(signal)

        # 过滤和排序信号
        filtered_signals = self._filter_signals(signals)
        sorted_signals = self._rank_signals(filtered_signals)

        # 记录信号历史
        self.signal_history.append({
            'timestamp': datetime.now(),
            'signals': sorted_signals
        })

        return sorted_signals

    def _filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """过滤信号"""
        filtered = []

        for signal in signals:
            # 过滤条件
            if signal.action == 'hold':
                continue

            # 只保留强信号
            if signal.strength < 0.01:
                continue

            # 买入信号强度过滤
            if signal.action == 'buy' and signal.strength < 0.02:
                continue

            # 卖出信号强度过滤
            if signal.action == 'sell' and signal.strength < 0.01:
                continue

            filtered.append(signal)

        return filtered

    def _rank_signals(self, signals: List[Signal]) -> List[Signal]:
        """对信号进行排序"""
        # 按得分和强度排序
        sorted_signals = sorted(
            signals,
            key=lambda x: (x.score, x.strength),
            reverse=True
        )

        return sorted_signals

    def get_buy_signals(self, signals: List[Signal]) -> List[Signal]:
        """获取买入信号"""
        return [s for s in signals if s.action == 'buy']

    def get_sell_signals(self, signals: List[Signal]) -> List[Signal]:
        """获取卖出信号"""
        return [s for s in signals if s.action == 'sell']

    def evaluate_signals(self, signals: List[Signal]) -> Dict[str, Any]:
        """评估信号质量

        Args:
            signals: 信号列表

        Returns:
            评估结果
        """
        if not signals:
            return {
                'total_count': 0,
                'buy_count': 0,
                'sell_count': 0,
                'avg_strength': 0,
                'avg_score': 0,
                'signal_quality': 0
            }

        buy_signals = self.get_buy_signals(signals)
        sell_signals = self.get_sell_signals(signals)

        avg_strength = np.mean([s.strength for s in signals])
        avg_score = np.mean([s.score for s in signals])

        # 信号质量评分
        quality_score = self._calculate_signal_quality(signals)

        return {
            'total_count': len(signals),
            'buy_count': len(buy_signals),
            'sell_count': len(sell_signals),
            'avg_strength': avg_strength,
            'avg_score': avg_score,
            'signal_quality': quality_score,
            'top_buy_signals': buy_signals[:5],  # 前5个买入信号
            'top_sell_signals': sell_signals[:5]  # 前5个卖出信号
        }

    def _calculate_signal_quality(self, signals: List[Signal]) -> float:
        """计算信号质量评分"""
        if not signals:
            return 0.0

        # 评分因子
        # 1. 信号强度分布
        strengths = [s.strength for s in signals]
        strength_score = np.mean(strengths) if strengths else 0

        # 2. 得分分布
        scores = [s.score for s in signals]
        score_score = np.mean(scores) if scores else 0

        # 3. 买入/卖出比例
        buy_count = len(self.get_buy_signals(signals))
        total_count = len(signals)
        buy_ratio = buy_count / total_count if total_count > 0 else 0

        # 4. 信号一致性
        consistency_score = 1 - np.std(strengths) if len(strengths) > 1 else 1

        # 综合评分 (0-1)
        quality = (
            strength_score * 0.3 +
            min(score_score, 1) * 0.3 +
            buy_ratio * 0.2 +
            consistency_score * 0.2
        )

        return min(quality, 1.0)

    def get_signal_summary(self) -> Dict[str, Any]:
        """获取信号摘要"""
        if not self.signal_history:
            return {'message': '暂无信号历史'}

        latest = self.signal_history[-1]
        signals = latest['signals']

        evaluation = self.evaluate_signals(signals)

        return {
            'timestamp': latest['timestamp'],
            'total_signals': evaluation['total_count'],
            'buy_signals': evaluation['buy_count'],
            'sell_signals': evaluation['sell_count'],
            'signal_quality': evaluation['signal_quality'],
            'top_signals': signals[:10],  # 前10个信号
            'evaluation': evaluation
        }

    def print_signal_report(self, signals: List[Signal]):
        """打印信号报告"""
        if not signals:
            print("\n当前无有效信号")
            return

        print("\n" + "=" * 60)
        print("买入信号报告")
        print("=" * 60)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"信号总数: {len(signals)}")

        # 买入信号
        buy_signals = self.get_buy_signals(signals)
        if buy_signals:
            print(f"\n买入信号 ({len(buy_signals)}):")
            print("-" * 60)
            for i, signal in enumerate(buy_signals[:10], 1):
                print(f"{i}. {signal.symbol}")
                print(f"   强度: {signal.strength:.2%}")
                print(f"   得分: {signal.score:.4f}")
                print(f"   原因: {signal.reason}")
                print()

        # 卖出信号
        sell_signals = self.get_sell_signals(signals)
        if sell_signals:
            print(f"\n卖出信号 ({len(sell_signals)}):")
            print("-" * 60)
            for i, signal in enumerate(sell_signals[:10], 1):
                print(f"{i}. {signal.symbol}")
                print(f"   强度: {signal.strength:.2%}")
                print(f"   原因: {signal.reason}")
                print()

        print("=" * 60)

    def save_signals(self, filepath: str = None):
        """保存信号到文件

        Args:
            filepath: 保存路径，默认为output/results/signals.csv
        """
        if filepath is None:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # 计算output目录路径
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(current_dir, 'output', 'results')
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, f'signals_{timestamp}.csv')

        data = []
        for entry in self.signal_history:
            for signal in entry['signals']:
                data.append({
                    'timestamp': entry['timestamp'].isoformat(),
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'strength': signal.strength,
                    'score': signal.score,
                    'reason': signal.reason,
                    **signal.metadata
                })

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        print(f"✓ 信号已保存到: {filepath}")
        return filepath

    def load_signals(self, filepath: str):
        """从文件加载信号"""
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 重建信号历史
        for timestamp, group in df.groupby('timestamp'):
            signals = []
            for _, row in group.iterrows():
                signal = Signal(
                    symbol=row['symbol'],
                    action=row['action'],
                    strength=row['strength'],
                    score=row['score'],
                    reason=row['reason'],
                    timestamp=pd.to_datetime(row['timestamp']),
                    metadata={k: v for k, v in row.items()
                             if k not in ['timestamp', 'symbol', 'action',
                                         'strength', 'score', 'reason']}
                )
                signals.append(signal)

            self.signal_history.append({
                'timestamp': timestamp,
                'signals': signals
            })

        print(f"已加载 {len(self.signal_history)} 条信号记录")


class SignalEvaluator:
    """信号评估器"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def evaluate_signal_performance(self,
                                   signals: List[Signal],
                                   price_data: Dict[str, pd.DataFrame],
                                   holding_period: int = 20) -> Dict[str, float]:
        """评估信号表现

        Args:
            signals: 信号列表
            price_data: 价格数据 {symbol: DataFrame}
            holding_period: 持有期（天）

        Returns:
            表现指标
        """
        results = {
            'total_signals': len(signals),
            'avg_return': 0,
            'win_rate': 0,
            'avg_holding_period': 0,
            'signal_accuracy': 0
        }

        if not signals:
            return results

        returns = []
        correct_signals = 0

        for signal in signals:
            if signal.symbol not in price_data:
                continue

            df = price_data[signal.symbol]
            signal_date = signal.timestamp

            # 找到信号日期对应的数据
            try:
                signal_idx = df.index.get_loc(signal_date, method='ffill')
            except KeyError:
                continue

            # 获取信号后N天的价格
            end_idx = min(signal_idx + holding_period, len(df) - 1)
            if end_idx <= signal_idx:
                continue

            entry_price = df.iloc[signal_idx]['close']
            exit_price = df.iloc[end_idx]['close']
            holding_days = end_idx - signal_idx

            # 计算收益率
            if signal.action == 'buy':
                ret = (exit_price - entry_price) / entry_price
            else:  # sell
                ret = (entry_price - exit_price) / entry_price

            returns.append(ret)

            # 判断信号是否正确
            if (signal.action == 'buy' and ret > 0) or (signal.action == 'sell' and ret > 0):
                correct_signals += 1

        if returns:
            results['avg_return'] = np.mean(returns)
            results['win_rate'] = len([r for r in returns if r > 0]) / len(returns)
            results['avg_holding_period'] = holding_period
            results['signal_accuracy'] = correct_signals / len(signals)

        return results
