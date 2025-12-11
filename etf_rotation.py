# 克隆自聚宽文章：https://www.joinquant.com/post/64296
# 标题：ETF加权轮动策略优化
# 作者：韭神~

from jqdata import *
import numpy as np
import pandas as pd
from scipy.stats import linregress
import math

# 基础设置
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    set_slippage(FixedSlippage(3/10000))
    set_order_cost(
        OrderCost(
            open_tax=0,
            close_tax=0,
            open_commission=2.5/10000,
            close_commission=2.5/10000,
            min_commission=0.2
        ),
        type='fund'
    )
    log.set_level('system', 'error')
    
    g.etf_list = [
        '159985.XSHE',  # 豆粕ETF
        '518880.XSHG',  # 黄金ETF
        '515220.XSHG',  # 煤炭ETF
        '516150.XSHG',  # 稀土ETF
        '159870.XSHE',  # 化工ETF
        '512400.XSHG',  # 有色金属ETF
        
        '513100.XSHG',  # 纳指ETF
        '513500.XSHG',  # 标普500ETF  
        '513090.XSHG',  # 香港证券ETF
        '513330.XSHG',  # 恒生互联网ETF
        
        '512050.XSHG',  # A50ETF        
        '159949.XSHE',  # 创业板ETF
        '512100.XSHG',  # 中证1000ETF
        '588000.XSHG',  # 科创50ETF        
        '588100.XSHG',  # 科创信息技术ETF

        '159819.XSHE',  # 人工智能ETF
        '512480.XSHG',  # 半导体ETF
        '510150.XSHG',  # 消费电子ETF
        '562500.XSHG',  # 机器人ETF
        
        '515790.XSHG',  # 光伏ETF
        '515880.XSHG',  # 通信ETF
        '159869.XSHE',  # 游戏ETF
        '159883.XSHE',  # 医疗器械ETF
    ]
    
    # 基础因子窗口参数
    g.momentum_window = 25  # 动量窗口
    g.slope_window = 20     # 斜率窗口
    g.ma_window = 20        # 均线窗口
    g.rsrs_window = 20      # RSRS窗口
    g.volatility_window = 20  # 波动率窗口
    
    # EPO优化参数
    g.epo_lambda = 10       # 风险厌恶系数
    g.epo_w = 0.2           # 收缩系数
    
    # 基础交易参数
    g.max_holdings = 3      # 最多持有3个标的
    g.score_threshold = 0    # 综合得分需>0才纳入候选
    g.min_positive_count = 7  # 综合得分大于0的ETF最小数量
    
    # 优化1：动态风控参数
    g.stop_loss_base = 0.05     # 基础止损比例
    g.trailing_stop_base = 0.05 # 基础跟踪止损比例
    g.take_profit_ratio = 0.10  # 基础止盈比例
    g.vol_quantile_window = 60  # 计算市场波动率的窗口
    g.dynamic_stop_loss = 0.05  # 动态止损比例（实时更新）
    g.dynamic_trailing_stop = 0.05 # 动态跟踪止损比例
    g.dynamic_take_profit = 0.10 # 动态止盈比例
    
    # 优化2：市场风险判断参数
    g.market_risk_level = 'neutral'  # 市场风险等级：high_risk/low_risk/neutral
    g.market_vol_quantile = 0.5      # 市场波动率分位
    g.total_position_ratio = 1.0     # 总仓位比例（高风险降仓）
    
    # 优化3：调仓频率参数
    g.rebalance_weekday = 0  # 每周一调仓（0=周一，6=周日）
    g.rebalance_threshold = 0.05  # 权重偏离>5%才调仓
    
    # 优化4：ETF风格分类（用于分散持仓）
    g.etf_style = {
        '159985.XSHE': 'commodity', '518880.XSHG': 'commodity',
        '515220.XSHG': 'commodity',  # 煤炭ETF
        '516150.XSHG': 'commodity',  # 稀土ETF
        '159870.XSHE': 'commodity',  # 化工ETF
        '512400.XSHG': 'commodity',  # 有色金属ETF
        
        '513100.XSHG': 'overseas', '513500.XSHG': 'overseas', 
        '513330.XSHG': 'overseas', '513090.XSHG': 'overseas',
        
        '512050.XSHG': 'a_share', '159949.XSHE': 'a_share', 
        '512100.XSHG': 'a_share', '588000.XSHG': 'a_share',
        
        '588100.XSHG': 'tech', '159819.XSHE': 'tech', 
        '512480.XSHG': 'tech', '510150.XSHG': 'tech', 
        '562500.XSHG': 'tech', '515790.XSHG': 'tech',  # 光伏ETF
        '515880.XSHG': 'tech',  # 通信ETF
        '159869.XSHE': 'tech',  # 游戏ETF
        '159883.XSHE': 'tech',  # 医疗器械ETF
    }
    
    # 原始风控参数（保留但被动态参数覆盖）
    g.drop_threshold = 0.05  # 单日跌幅超过5%则过滤
    g.volume_short_window = 5      # 短期成交量窗口
    g.volume_long_window = 20      # 长期成交量窗口
    g.volume_ratio_threshold = 1.5 # 成交量比率阈值
    g.volume_filter_threshold = 2.0 # 成交量过滤阈值
    
    # 防御性ETF组合（黄金、纳指、豆粕）
    g.defensive_etfs = ['518880.XSHG', '513100.XSHG', '159985.XSHE']
    
    # 记录持仓成本和最高价
    g.hold_cost = {}  # key: etf_code, value: 平均持仓成本
    g.hold_high = {}  # 记录持仓以来的最高价
    g.factor_scores = {}
    g.positive_count = 0  # 综合得分大于0的ETF数量
    
    run_daily(before_market_open, time='09:00')
    run_daily(market_open,  time='09:35')
    run_daily(update_hold_high, time='15:00')  # 收盘后更新最高价记录

def update_hold_high(context):
    """收盘后更新持仓最高价记录"""
    current_data = get_current_data()
    
    for etf in list(context.portfolio.positions.keys()):
        current_price = current_data[etf].last_price
        if current_price is None or np.isnan(current_price):
            continue
            
        # 初始化或更新最高价
        if etf not in g.hold_high:
            g.hold_high[etf] = current_price
        else:
            g.hold_high[etf] = max(g.hold_high[etf], current_price)

def calculate_volume_ratio(volumes, short_window=5, long_window=20):
    """计算成交量比率（短期/长期均量）"""
    if len(volumes) < long_window:
        return 1.0
    try:
        ma_short = volumes.rolling(short_window).mean().iloc[-1]
        ma_long = volumes.rolling(long_window).mean().iloc[-1]
        return ma_short / ma_long if ma_long > 0 else 1.0
    except:
        return 1.0

def calculate_market_vol_quantile(context):
    """优化1：计算沪深300波动率分位（0~1，1代表波动率最高）"""
    try:
        hs300_data = get_price('000300.XSHG', count=g.vol_quantile_window, 
                              end_date=context.current_dt, frequency='daily', fields=['close'])
        if len(hs300_data) < 20:
            return 0.5
        hs300_returns = hs300_data['close'].pct_change().dropna()
        # 计算当前年化波动率
        current_vol = hs300_returns.std() * np.sqrt(250)
        # 计算过去60日波动率滚动序列
        vol_rolling = hs300_returns.rolling(20).std() * np.sqrt(250)
        vol_rolling = vol_rolling.dropna()
        if len(vol_rolling) == 0:
            return 0.5
        # 计算分位
        vol_quantile = (vol_rolling <= current_vol).sum() / len(vol_rolling)
        return vol_quantile
    except Exception as e:
        log.warn(f"计算市场波动率分位失败: {e}")
        return 0.5

def judge_market_trend(context):
    """优化2：判断市场趋势（高/中/低风险）"""
    try:
        hs300_data = get_price('000300.XSHG', count=60, 
                              end_date=context.current_dt, frequency='daily', fields=['close'])
        if len(hs300_data) < 60:
            return 'neutral'
        hs300_ma60 = hs300_data['close'].rolling(60).mean().iloc[-1]
        hs300_latest = hs300_data['close'].iloc[-1]
        # 高风险：跌破60日均线 + 波动率分位>0.8
        if hs300_latest < hs300_ma60 and g.market_vol_quantile > 0.8:
            return 'high_risk'
        # 低风险：站上60日均线 + 波动率分位<0.2
        elif hs300_latest > hs300_ma60 and g.market_vol_quantile < 0.2:
            return 'low_risk'
        # 中性：其他情况
        else:
            return 'neutral'
    except Exception as e:
        log.warn(f"判断市场趋势失败: {e}")
        return 'neutral'

def before_market_open(context):
    """计算因子值，优化计算效率"""
    log.info("===== 开始计算因子值 =====")
    g.factor_scores = {}
    g.positive_count = 0
    
    # 优化1：计算市场波动率分位，动态调整风控参数
    g.market_vol_quantile = calculate_market_vol_quantile(context)
    g.dynamic_stop_loss = g.stop_loss_base * (1 + g.market_vol_quantile)
    g.dynamic_trailing_stop = g.trailing_stop_base * (1 + g.market_vol_quantile)
    g.dynamic_take_profit = g.take_profit_ratio * (1 - g.market_vol_quantile)
    log.info(f"动态风控参数：止损{g.dynamic_stop_loss:.1%}, 跟踪止损{g.dynamic_trailing_stop:.1%}, 止盈{g.dynamic_take_profit:.1%}")
    
    # 优化2：判断市场风险等级
    g.market_risk_level = judge_market_trend(context)
    log.info(f"当前市场风险等级: {g.market_risk_level}, 波动率分位: {g.market_vol_quantile:.2f}")
    
    # 获取前一个交易日
    trade_days = get_trade_days(end_date=context.current_dt, count=2)
    if len(trade_days) < 2:
        log.warn("无法获取前一个交易日，跳过计算")
        return
    previous_trade_day = trade_days[-2]
    
    # 批量获取数据，减少API调用
    all_data = {}
    for etf in g.etf_list:
        try:
            # 获取历史数据（减少数据量）
            need_days = max(g.momentum_window, g.slope_window, g.rsrs_window, 
                           g.ma_window, g.volatility_window, g.volume_long_window) + 5
            data = get_price(etf, count=need_days, end_date=previous_trade_day, 
                            frequency='daily', fields=['close', 'high', 'low', 'volume'])
            if not data.empty:
                all_data[etf] = data
        except Exception as e:
            log.warn(f"获取 {etf} 数据失败: {e}")
            continue
    
    # 计算成交量比率
    volume_ratios = {}
    for etf, data in all_data.items():
        volumes = data['volume']
        volume_ratios[etf] = calculate_volume_ratio(volumes, g.volume_short_window, g.volume_long_window)
    
    # 计算因子值
    for etf, data in all_data.items():
        try:
            close = data['close'].values
            
            # 成交量过滤
            vol_ratio = volume_ratios.get(etf, 1.0)
            if vol_ratio > g.volume_filter_threshold:
                log.info(f"过滤 {etf}，成交量比率{vol_ratio:.2f}超过阈值{g.volume_filter_threshold}")
                g.factor_scores[etf] = {'composite': 0}
                continue
                
            # 跌幅过滤
            if len(close) >= 4:
                day1_return = close[-1] / close[-2] - 1
                day2_return = close[-2] / close[-3] - 1
                day3_return = close[-3] / close[-4] - 1
                if day1_return < -g.drop_threshold or day2_return < -g.drop_threshold or day3_return < -g.drop_threshold or (day1_return+day2_return+day3_return)<-0.1:
                    log.info(f"过滤 {etf}，近3日有单日跌幅超过{g.drop_threshold*100:.0f}%")
                    g.factor_scores[etf] = {'composite': 0}
                    continue
            
            high = data['high'].values
            low = data['low'].values
            
            # 1. 动量因子（年化收益和判定系数）
            y = np.log(close)
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            annualized_returns = math.pow(math.exp(slope), 250) - 1
            ss_res = np.sum((y - (slope * x + intercept)) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / (ss_tot + 1e-8))
            momentum = annualized_returns * r_squared
            
            # 2. 质量因子（优化3：加入抗回撤子因子）
            # 2.1 基础子因子
            x_slope = np.arange(g.slope_window)
            y_slope = close[-g.slope_window:]
            slope, _, r_value, _, _ = linregress(x_slope, y_slope)
            slope_r2 = slope * (r_value **2)
            
            ma = np.mean(close[-g.ma_window:])
            ma_factor = 1 if close[-1] > ma else 0
            
            beta_list = []
            for i in range(min(g.rsrs_window, 5)):
                h = high[-(g.rsrs_window - i)]
                l = low[-(g.rsrs_window - i)]
                s, _, r, _, _ = linregress([0, 1], [l, h])
                beta_list.append(s * r)
            rsrs = np.mean(beta_list)
            
            returns_vol = np.diff(close[-g.volatility_window:]) / close[-g.volatility_window:-1]
            volatility = np.std(returns_vol) if len(returns_vol) > 0 else 0
            volatility_factor = 1 / (1 + volatility)
            
            # 2.2 新增抗回撤子因子
            # 最大回撤得分
            cum_returns = np.cumprod(1 + returns_vol) - 1 if len(returns_vol) > 0 else np.array([0])
            peak = np.maximum.accumulate(cum_returns)
            drawdown = (cum_returns - peak) / (peak + 1e-8)
            max_drawdown = np.min(drawdown)
            max_drawdown_score = 1 / (1 + abs(max_drawdown))
            
            # 夏普比率得分
            sharpe = (np.mean(returns_vol) * 250 - 0.02) / (np.std(returns_vol) * np.sqrt(250)) if np.std(returns_vol) > 0 else 0
            sharpe_score = max(0, sharpe)
            
            # 多周期均线因子
            ma10 = np.mean(close[-10:]) if len(close)>=10 else ma
            multi_ma_factor = 1 if (close[-1] > ma10 and close[-1] > ma) else 0
            
            # 2.3 质量因子加权（7个子因子）
            quality = (0.15 * slope_r2) + (0.15 * ma_factor) + (0.15 * rsrs) + (0.15 * volatility_factor) + \
                      (0.2 * max_drawdown_score) + (0.15 * sharpe_score) + (0.05 * multi_ma_factor)
            
            # 3. 综合评分
            composite_score = momentum * quality
            
            g.factor_scores[etf] = {
                'momentum': momentum,
                'quality': quality,
                'composite': composite_score,
                'slope_r2': slope_r2,
                'ma_factor': ma_factor,
                'rsrs': rsrs,
                'volatility': volatility,
                'volume_ratio': vol_ratio,
                'max_drawdown_score': max_drawdown_score,
                'sharpe_score': sharpe_score
            }
            
            if composite_score > 0:
                g.positive_count += 1
            
        except Exception as e:
            log.warn(f"计算 {etf} 因子失败: {e}")
            continue
    
    log.info(f"综合得分大于0的ETF数量: {g.positive_count}")
    log.info("===== 因子计算完成 =====")

def simplified_epo_optimization(returns, composite_scores):
    """简化版EPO优化"""
    n = returns.shape[1]
    if len(returns) < 10 or n < 2:
        weights = np.array(composite_scores)
        return weights / (np.sum(weights) + 1e-10)
    try:
        vcov = returns.cov()
        variances = np.diag(vcov)
        inv_variances = 1 / (variances + 1e-10)
        s = np.array(composite_scores)
        weights = s * inv_variances
        weights = np.maximum(0, weights)
        sum_weights = np.sum(weights)
        if sum_weights > 0:
            return weights / sum_weights
        else:
            return np.ones(n) / n
    except Exception as e:
        log.warn(f"EPO优化失败: {e}，使用等权重")
        return np.ones(n) / n

def score_based_weighting(composite_scores):
    """基于综合得分的简单加权方法"""
    scores = np.array(composite_scores)
    scores = np.clip(scores, a_min=0, a_max=None)
    if np.sum(scores) == 0:
        return np.ones(len(scores)) / len(scores)
    weights = scores / np.sum(scores)
    return weights

def market_open(context):
    """执行交易逻辑：优化性能+新增风控/调仓规则"""
    log.info("===== 开始执行交易 =====")
    current_data = get_current_data()
    
    if not g.factor_scores:
        log.warn("没有可用的因子评分，不执行交易")
        return
    
    # 优化3：调仓频率控制（仅每周一或权重偏离超阈值时调仓）
    current_weekday = context.current_dt.weekday()
    if current_weekday != g.rebalance_weekday:
        # 检查权重偏离
        qualified_etfs = [(etf, score) for etf, score in g.factor_scores.items() if score['composite'] > g.score_threshold]
        target_weights = {}
        if qualified_etfs:
            sorted_etfs = sorted(qualified_etfs, key=lambda x: x[1]['composite'], reverse=True)
            target_list_temp = [etf for etf, _ in sorted_etfs[:g.max_holdings]]
            composite_scores_temp = [g.factor_scores[etf]['composite'] for etf in target_list_temp]
            weights_temp = score_based_weighting(composite_scores_temp)
            target_weights = dict(zip(target_list_temp, weights_temp))
        
        need_rebalance = False
        for etf in context.portfolio.positions:
            current_weight = context.portfolio.positions[etf].value / context.portfolio.total_value
            target_weight = target_weights.get(etf, 0)
            if abs(current_weight - target_weight) > g.rebalance_threshold:
                need_rebalance = True
                break
        if not need_rebalance:
            log.info("非调仓日且权重偏离未超阈值，跳过调仓")
            return
    
    # 1. 止损+止盈逻辑（优化1：动态参数）
    positions_to_sell = []
    for etf in list(context.portfolio.positions.keys()):
        if etf not in g.hold_cost:
            continue
        current_price = current_data[etf].last_price
        if current_price is None or np.isnan(current_price):
            continue
        
        # 成本止损（动态参数）
        loss_ratio = (current_price - g.hold_cost[etf]) / g.hold_cost[etf]
        if loss_ratio < -g.dynamic_stop_loss:
            positions_to_sell.append(etf)
            log.info(f"触发动态成本止损 {etf}, 成本: {g.hold_cost[etf]:.2f}, 当前价: {current_price:.2f}, 亏损: {loss_ratio*100:.2f}%")
            continue
        
        # 跟踪止损（动态参数）
        if etf in g.hold_high:
            highest_price = g.hold_high[etf]
            if highest_price > 0:
                drop_from_high = (current_price - highest_price) / highest_price
                if drop_from_high < -g.dynamic_trailing_stop:
                    positions_to_sell.append(etf)
                    log.info(f"触发动态跟踪止损 {etf}, 最高价: {highest_price:.2f}, 当前价: {current_price:.2f}, 回落: {drop_from_high*100:.2f}%")
                    if etf in g.hold_high:
                        del g.hold_high[etf]
                    continue
        
        # 修正：动态止盈（用order_target_value替代order_target_percent）
        profit_ratio = (current_price - g.hold_cost[etf]) / g.hold_cost[etf]
        if profit_ratio > g.dynamic_take_profit:
            position = context.portfolio.positions[etf]
            current_value = position.value  # 当前持仓市值
            target_value = current_value / 2  # 减半仓位
            order_target_value(etf, target_value)
            log.info(f"触发动态止盈 {etf}, 盈利: {profit_ratio:.1%}, 减半仓位（当前市值{current_value:.2f}→目标{target_value:.2f}）")
            g.hold_high[etf] = current_price  # 重置最高价
    
    # 批量卖出止损持仓
    for etf in positions_to_sell:
        order_target_value(etf, 0)
        log.info(f"卖出 {etf} (止损触发)")
        if etf in g.hold_cost:
            del g.hold_cost[etf]
        if etf in g.hold_high:
            del g.hold_high[etf]
    
    # 2. 筛选候选ETF
    qualified_etfs = [
        (etf, score) for etf, score in g.factor_scores.items()
        if score['composite'] > g.score_threshold
    ]
    
    # 3. 优化2：市场风险降仓+防御切换
    if g.positive_count < g.min_positive_count or g.market_risk_level == 'high_risk':
        log.info(f"市场高风险/优质ETF不足，切换防御组合+降仓至50%")
        target_list = g.defensive_etfs
        weights = [1/len(target_list)] * len(target_list)
        g.total_position_ratio = 0.5  # 高风险降仓至50%
    elif g.market_risk_level == 'low_risk':
        g.total_position_ratio = 1.0  # 低风险满仓
        if not qualified_etfs:
            log.warn("无符合条件的ETF，清空持仓")
            for etf in context.portfolio.positions:
                order_target_value(etf, 0)
                if etf in g.hold_cost:
                    del g.hold_cost[etf]
                if etf in g.hold_high:
                    del g.hold_high[etf]
            return
        # 优化4：风格分散筛选目标ETF
        sorted_etfs = sorted(qualified_etfs, key=lambda x: x[1]['composite'], reverse=True)
        target_list = []
        style_included = set()
        # 优先选不同风格的标的
        for etf, score in sorted_etfs:
            style = g.etf_style[etf]
            if style not in style_included or len(target_list) < 2:
                target_list.append(etf)
                style_included.add(style)
            if len(target_list) >= g.max_holdings:
                break
        # 补充至3只
        if len(target_list) < g.max_holdings:
            for etf, score in sorted_etfs:
                if etf not in target_list:
                    target_list.append(etf)
                    if len(target_list) >= g.max_holdings:
                        break
        log.info(f"本周优选ETF(风格分散): {target_list}")
        # 计算权重
        try:
            trade_days = get_trade_days(end_date=context.current_dt, count=2)
            if len(trade_days) < 2:
                weights = [1/len(target_list)] * len(target_list)
            else:
                previous_trade_day = trade_days[-2]
                price_data = get_price(target_list, count=30, end_date=previous_trade_day, 
                                      frequency='daily', fields=['close'])
                returns = price_data['close'].pct_change().dropna()
                composite_scores = [g.factor_scores[etf]['composite'] for etf in target_list]
                weights = score_based_weighting(composite_scores)
            log.info(f"权重分配: {dict(zip(target_list, weights))}")
        except Exception as e:
            log.warn(f"权重计算失败: {e}，使用等权重")
            weights = [1/len(target_list)] * len(target_list)
    else:
        g.total_position_ratio = 0.8  # 中性市场80%仓位
        if not qualified_etfs:
            log.warn("无符合条件的ETF，清空持仓")
            for etf in context.portfolio.positions:
                order_target_value(etf, 0)
                if etf in g.hold_cost:
                    del g.hold_cost[etf]
                if etf in g.hold_high:
                    del g.hold_high[etf]
            return
        # 优化4：风格分散筛选
        sorted_etfs = sorted(qualified_etfs, key=lambda x: x[1]['composite'], reverse=True)
        target_list = []
        style_included = set()
        for etf, score in sorted_etfs:
            style = g.etf_style[etf]
            if style not in style_included or len(target_list) < 2:
                target_list.append(etf)
                style_included.add(style)
            if len(target_list) >= g.max_holdings:
                break
        if len(target_list) < g.max_holdings:
            for etf, score in sorted_etfs:
                if etf not in target_list:
                    target_list.append(etf)
                    if len(target_list) >= g.max_holdings:
                        break
        log.info(f"本周优选ETF(风格分散): {target_list}")
        # 计算权重
        try:
            trade_days = get_trade_days(end_date=context.current_dt, count=2)
            if len(trade_days) < 2:
                weights = [1/len(target_list)] * len(target_list)
            else:
                previous_trade_day = trade_days[-2]
                price_data = get_price(target_list, count=30, end_date=previous_trade_day, 
                                      frequency='daily', fields=['close'])
                returns = price_data['close'].pct_change().dropna()
                composite_scores = [g.factor_scores[etf]['composite'] for etf in target_list]
                weights = score_based_weighting(composite_scores)
            log.info(f"权重分配: {dict(zip(target_list, weights))}")
        except Exception as e:
            log.warn(f"权重计算失败: {e}，使用等权重")
            weights = [1/len(target_list)] * len(target_list)
    
    # 4. 卖出不在目标列表的持仓
    positions_to_sell = [etf for etf in context.portfolio.positions if etf not in target_list]
    for etf in positions_to_sell:
        order_target_value(etf, 0)
        log.info(f"卖出 {etf} (不在优选列表)")
        if etf in g.hold_cost:
            del g.hold_cost[etf]
        if etf in g.hold_high:
            del g.hold_high[etf]
    
    # 5. 买入优选ETF（按总仓位比例）
    total_value = context.portfolio.total_value * g.total_position_ratio
    for i, etf in enumerate(target_list):
        if i >= len(weights):
            continue
        weight = weights[i]
        target_value = total_value * weight
        
        # 获取当前价格
        current_price = current_data[etf].last_price
        if not current_price or current_price <= 0 or np.isnan(current_price):
            log.warn(f"无效价格: {etf}, 跳过买入")
            continue
        
        # 计算购买数量（100股的整数倍）
        try:
            amount = int(target_value / current_price // 100) * 100
        except Exception as e:
            log.error(f"计算数量错误: {etf}, 错误: {str(e)}")
            continue
        
        if amount <= 0:
            log.warn(f"可买数量为0: {etf} (目标价值{target_value:.2f}, 价格{current_price:.2f})")
            continue
        
        # 执行买入
        order(etf, amount)
        log.info(f"买入 {etf}, 数量 {amount}, 目标价值 {target_value:.2f}, 总仓位比例 {g.total_position_ratio:.0%}")
        
        # 更新持仓成本
        if etf in context.portfolio.positions:
            position = context.portfolio.positions[etf]
            current_amount = position.total_amount
            current_cost = g.hold_cost.get(etf, current_price)
            # 计算加权平均成本
            new_cost = (current_cost * current_amount + current_price * amount) / (current_amount + amount)
        else:
            new_cost = current_price
        
        g.hold_cost[etf] = new_cost
        g.hold_high[etf] = current_price  # 初始化最高价
    
    log.info("===== 交易执行完成 =====")

def handle_data(context, data):
    """每分钟运行（如果需要实时监控）"""
    pass

def after_trading_end(context):
    """盘后运行"""
    pass