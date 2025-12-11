"""
参数搜索模块

提供多种参数优化算法，包括网格搜索、随机搜索和贝叶斯优化
"""

from typing import Dict, List, Any, Optional, Callable, Tuple
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import itertools
import random
from dataclasses import dataclass
import json
import os
from datetime import datetime


@dataclass
class SearchResult:
    """搜索结果"""
    params: Dict[str, Any]
    score: float
    metrics: Dict[str, Any]
    timestamp: datetime


class ParameterSearch:
    """参数搜索基类"""

    def __init__(self,
                 objective_func: Callable,
                 param_space: Dict[str, Any],
                 maximize: bool = True,
                 n_jobs: int = 1):
        """初始化参数搜索

        Args:
            objective_func: 目标函数，接收参数字典返回分数
            param_space: 参数空间 {param_name: [values]}
            maximize: 是否最大化目标函数
            n_jobs: 并行作业数
        """
        self.objective_func = objective_func
        self.param_space = param_space
        self.maximize = maximize
        self.n_jobs = n_jobs
        self.results = []
        self.best_params = None
        self.best_score = None

    def search(self, n_iterations: int = 100) -> Dict[str, Any]:
        """执行参数搜索

        Args:
            n_iterations: 搜索迭代次数

        Returns:
            最佳参数和结果
        """
        raise NotImplementedError

    def _evaluate_params(self, params: Dict[str, Any]) -> SearchResult:
        """评估参数组合"""
        try:
            score = self.objective_func(params)
            if not self.maximize:
                score = -score

            result = SearchResult(
                params=params.copy(),
                score=score,
                metrics={'score': score},
                timestamp=datetime.now()
            )

            self.results.append(result)

            # 更新最佳结果
            if self.best_score is None or score > self.best_score:
                self.best_score = score
                self.best_params = params.copy()

            return result

        except Exception as e:
            print(f"评估参数失败 {params}: {e}")
            return SearchResult(
                params=params.copy(),
                score=-np.inf,
                metrics={'error': str(e)},
                timestamp=datetime.now()
            )

    def get_best_params(self) -> Optional[Dict[str, Any]]:
        """获取最佳参数"""
        return self.best_params

    def get_best_score(self) -> Optional[float]:
        """获取最佳分数"""
        return self.best_score

    def get_results_dataframe(self) -> pd.DataFrame:
        """获取结果DataFrame"""
        if not self.results:
            return pd.DataFrame()

        data = []
        for result in self.results:
            row = result.params.copy()
            row['score'] = result.score
            row['timestamp'] = result.timestamp
            row.update(result.metrics)
            data.append(row)

        return pd.DataFrame(data)

    def save_results(self, filepath: str = None):
        """保存搜索结果

        Args:
            filepath: 保存路径，默认为output/results/optimization_results.json
        """
        if filepath is None:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # 计算output目录路径
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(current_dir, 'output', 'results')
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, f'optimization_results_{timestamp}.json')

        results_data = []
        for result in self.results:
            results_data.append({
                'params': result.params,
                'score': result.score,
                'metrics': result.metrics,
                'timestamp': result.timestamp.isoformat()
            })

        output = {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'results': results_data,
            'param_space': self.param_space
        }

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"✓ 搜索结果已保存到: {filepath}")
        return filepath


class GridSearch(ParameterSearch):
    """网格搜索"""

    def search(self, n_iterations: int = None) -> Dict[str, Any]:
        """执行网格搜索

        Args:
            n_iterations: 忽略此参数，网格搜索使用所有组合

        Returns:
            搜索结果
        """
        # 生成所有参数组合
        param_names = list(self.param_space.keys())
        param_values = list(self.param_space.values())

        # 计算总组合数
        total_combinations = 1
        for values in param_values:
            total_combinations *= len(values)

        print(f"网格搜索开始，总共 {total_combinations} 个参数组合")

        # 生成所有组合
        all_combinations = list(itertools.product(*param_values))

        # 并行评估
        if self.n_jobs > 1:
            with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
                # 创建参数字典
                param_dicts = []
                for combo in all_combinations:
                    param_dict = dict(zip(param_names, combo))
                    param_dicts.append(param_dict)

                # 并行执行
                futures = [executor.submit(self._evaluate_params, params)
                          for params in param_dicts]

                # 收集结果
                for future in futures:
                    future.result()
        else:
            # 串行执行
            for combo in all_combinations:
                params = dict(zip(param_names, combo))
                self._evaluate_params(params)

        print(f"网格搜索完成，评估了 {len(self.results)} 个组合")
        print(f"最佳分数: {self.best_score:.4f}")
        print(f"最佳参数: {self.best_params}")

        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'results': self.results
        }


class RandomSearch(ParameterSearch):
    """随机搜索"""

    def __init__(self,
                 objective_func: Callable,
                 param_space: Dict[str, Any],
                 maximize: bool = True,
                 n_jobs: int = 1,
                 seed: int = None):
        """初始化随机搜索

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            maximize: 是否最大化
            n_jobs: 并行数
            seed: 随机种子
        """
        super().__init__(objective_func, param_space, maximize, n_jobs)
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def search(self, n_iterations: int = 100) -> Dict[str, Any]:
        """执行随机搜索

        Args:
            n_iterations: 搜索迭代次数

        Returns:
            搜索结果
        """
        print(f"随机搜索开始，迭代 {n_iterations} 次")

        # 生成随机参数组合
        param_names = list(self.param_space.keys())
        param_values = list(self.param_space.values())

        if self.n_jobs > 1:
            with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
                futures = []

                for _ in range(n_iterations):
                    # 生成随机参数
                    params = {}
                    for name, values in zip(param_names, param_values):
                        params[name] = random.choice(values)

                    # 提交任务
                    future = executor.submit(self._evaluate_params, params)
                    futures.append(future)

                # 收集结果
                for future in futures:
                    future.result()
        else:
            # 串行执行
            for _ in range(n_iterations):
                # 生成随机参数
                params = {}
                for name, values in zip(param_names, param_values):
                    params[name] = random.choice(values)

                self._evaluate_params(params)

        print(f"随机搜索完成，评估了 {len(self.results)} 个组合")
        print(f"最佳分数: {self.best_score:.4f}")
        print(f"最佳参数: {self.best_params}")

        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'results': self.results
        }


class BayesianOptimization(ParameterSearch):
    """贝叶斯优化（简化版）"""

    def __init__(self,
                 objective_func: Callable,
                 param_space: Dict[str, Any],
                 maximize: bool = True,
                 n_jobs: int = 1):
        """初始化贝叶斯优化

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            maximize: 是否最大化
            n_jobs: 并行数
        """
        super().__init__(objective_func, param_space, maximize, n_jobs)
        self.evaluated_params = []
        self.evaluated_scores = []

    def search(self, n_iterations: int = 100, n_initial_points: int = 10) -> Dict[str, Any]:
        """执行贝叶斯优化

        Args:
            n_iterations: 总迭代次数
            n_initial_points: 初始随机评估点数

        Returns:
            搜索结果
        """
        print(f"贝叶斯优化开始，初始点数: {n_initial_points}, 总迭代: {n_iterations}")

        param_names = list(self.param_space.keys())
        param_values = list(self.param_space.values())

        # 第一阶段：随机评估
        print("第一阶段：随机评估...")
        for _ in range(n_initial_points):
            params = {}
            for name, values in zip(param_names, param_values):
                params[name] = random.choice(values)
            self._evaluate_params(params)

        # 第二阶段：贝叶斯优化
        print("第二阶段：贝叶斯优化...")
        for i in range(n_iterations - n_initial_points):
            # 选择下一个评估点（使用简单的探索策略）
            next_params = self._select_next_params(param_names, param_values)

            if next_params:
                self._evaluate_params(next_params)

            if (i + 1) % 10 == 0:
                print(f"  迭代 {i + 1}/{n_iterations - n_initial_points}, 当前最佳: {self.best_score:.4f}")

        print(f"贝叶斯优化完成，评估了 {len(self.results)} 个组合")
        print(f"最佳分数: {self.best_score:.4f}")
        print(f"最佳参数: {self.best_params}")

        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'results': self.results
        }

    def _select_next_params(self, param_names: List[str], param_values: List[List]) -> Optional[Dict[str, Any]]:
        """选择下一个评估点（简化版UCB）"""
        if len(self.results) < 2:
            return None

        # 简化的UCB策略：平衡探索和利用
        best_params = None
        best_ucb = -np.inf

        # 随机采样一些候选点
        n_candidates = 20
        for _ in range(n_candidates):
            params = {}
            for name, values in zip(param_names, param_values):
                params[name] = random.choice(values)

            # 计算UCB分数（简化）
            ucb_score = self._calculate_ucb(params)

            if ucb_score > best_ucb:
                best_ucb = ucb_score
                best_params = params

        return best_params

    def _calculate_ucb(self, params: Dict[str, Any]) -> float:
        """计算UCB分数"""
        # 找到最相似的已评估参数
        min_distance = np.inf
        best_score = 0

        for result in self.results:
            distance = self._calculate_distance(params, result.params)
            if distance < min_distance:
                min_distance = distance
                best_score = result.score

        # UCB = 利用项 + 探索项
        exploitation = best_score
        exploration = 1.0 / (min_distance + 1e-6)  # 距离越远，探索奖励越大

        return exploitation + 0.1 * exploration

    def _calculate_distance(self, params1: Dict[str, Any], params2: Dict[str, Any]) -> float:
        """计算参数距离"""
        if not params1 or not params2:
            return np.inf

        distances = []
        for key in params1.keys():
            if key in params2:
                val1, val2 = params1[key], params2[key]
                # 假设所有值都是数值类型
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    distances.append(abs(val1 - val2))
                else:
                    distances.append(0 if val1 == val2 else 1)

        return np.mean(distances) if distances else np.inf


def create_parameter_search(search_type: str = 'grid',
                          objective_func: Callable = None,
                          param_space: Dict[str, Any] = None,
                          **kwargs) -> ParameterSearch:
    """创建参数搜索器的便捷函数

    Args:
        search_type: 搜索类型 ('grid', 'random', 'bayesian')
        objective_func: 目标函数
        param_space: 参数空间
        **kwargs: 其他参数

    Returns:
        参数搜索器实例
    """
    if objective_func is None or param_space is None:
        raise ValueError("objective_func 和 param_space 不能为空")

    search_type = search_type.lower()

    if search_type == 'grid':
        return GridSearch(objective_func, param_space, **kwargs)
    elif search_type == 'random':
        return RandomSearch(objective_func, param_space, **kwargs)
    elif search_type == 'bayesian':
        return BayesianOptimization(objective_func, param_space, **kwargs)
    else:
        raise ValueError(f"不支持的搜索类型: {search_type}")


def optimize_strategy_parameters(strategy_class,
                                data_dict: Dict[str, pd.DataFrame],
                                param_space: Dict[str, Any],
                                search_type: str = 'random',
                                n_iterations: int = 100,
                                metric: str = 'total_return',
                                **kwargs) -> Dict[str, Any]:
    """优化策略参数的便捷函数

    Args:
        strategy_class: 策略类
        data_dict: 数据字典
        param_space: 参数空间
        search_type: 搜索类型
        n_iterations: 迭代次数
        metric: 优化指标
        **kwargs: 其他参数

    Returns:
        优化结果
    """
    from ..core.backtest_engine import BacktestEngine

    def objective_func(params: Dict[str, Any]) -> float:
        """目标函数：运行回测并返回指标"""
        try:
            engine = BacktestEngine()
            result = engine.run_single_strategy(
                strategy_name='temp_strategy',
                data_dict=data_dict,
                start_date='2020-01-01',
                end_date='2024-12-31',
                config={'params': params}
            )

            if 'error' in result:
                return -np.inf

            # 返回指定的指标
            return result.get(metric, 0)

        except Exception as e:
            print(f"回测失败: {e}")
            return -np.inf

    # 创建搜索器
    searcher = create_parameter_search(
        search_type=search_type,
        objective_func=objective_func,
        param_space=param_space,
        **kwargs
    )

    # 执行搜索
    results = searcher.search(n_iterations=n_iterations)

    return results
