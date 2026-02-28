"""
Equity Millipede 策略指标 (适用于A股分钟数据)

基于 Forex Factory - Building an equity millipede 策略改编

核心思想:
1. 顺势交易: 顺着主要趋势方向开仓
2. 入场时机: 在分钟K线开盘时顺势入场
3. 止损: 设置较宽的止损 (如5%)
4. 止盈: 让利润奔跑,使用移动止损或均线止盈

适应A股分钟数据:
- 使用日线趋势作为主要趋势判断
- 在分钟级别寻找顺势入场点
- 结合成交量放大确认信号
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


def calculate_indicators(
    df: pd.DataFrame,
    trend_ma_period: int = 20,      # 趋势判断均线周期 (分钟)
    volume_ma_period: int = 20,     # 成交量均线周期
    volume_ratio: float = 1.5,     # 成交量放大倍数
    stop_loss_pct: float = 0.05,   # 止损百分比
    take_profit_pct: float = 0.10, # 止盈触发百分比
) -> pd.DataFrame:
    """
    计算策略所需的指标
    
    Args:
        df: 包含OHLCV数据的DataFrame
        trend_ma_period: 趋势判断均线周期
        volume_ma_period: 成交量均线周期
        volume_ratio: 成交量放大倍数
        stop_loss_pct: 止损百分比
        take_profit_pct: 止盈触发百分比
        
    Returns:
        添加了指标的DataFrame
    """
    data = df.copy()
    
    # 基础价格数据
    data['change'] = data['Close'].pct_change()
    data['is_bullish'] = data['Close'] > data['Open']  # 阳线
    data['is_bearish'] = data['Close'] < data['Open']  # 阴线
    
    # 趋势指标 - 使用EMA判断趋势方向
    data['ema_fast'] = data['Close'].ewm(span=5, adjust=False).mean()
    data['ema_slow'] = data['Close'].ewm(span=trend_ma_period, adjust=False).mean()
    
    # 趋势方向: 1=上涨, -1=下跌, 0=震荡
    data['trend'] = 0
    data.loc[data['ema_fast'] > data['ema_slow'], 'trend'] = 1   # 上涨趋势
    data.loc[data['ema_fast'] < data['ema_slow'], 'trend'] = -1  # 下跌趋势
    
    # 趋势强度 (两条均线的距离)
    data['trend_strength'] = (data['ema_fast'] - data['ema_slow']) / data['ema_slow']
    
    # 成交量指标
    data['volume_ma'] = data['Volume'].rolling(window=volume_ma_period).mean()
    data['volume_ratio'] = data['Volume'] / data['volume_ma']
    data['volume_spike'] = data['volume_ratio'] > volume_ratio  # 放量信号
    
    # 动量指标
    data['momentum'] = data['Close'].pct_change(periods=5)
    
    # 布林带 (用于止盈判断)
    data['bb_middle'] = data['Close'].rolling(window=20).mean()
    bb_std = data['Close'].rolling(window=20).std()
    data['bb_upper'] = data['bb_middle'] + 2 * bb_std
    data['bb_lower'] = data['bb_middle'] - 2 * bb_std
    
    # 日线级别趋势 (通过resample获取)
    # 由于是分钟数据，我们使用过去N个周期的平均变化来确定大趋势
    data['price_change_cum'] = data['Close'].pct_change(periods=100)  # 约等于过去1-2小时的涨跌幅
    
    # 生成交易信号
    # 买入信号: 上涨趋势 + 放量阳线
    data['buy_signal'] = (
        (data['trend'] == 1) & 
        (data['volume_spike']) & 
        (data['is_bullish']) &
        (data['volume_ma'].notna())
    )
    
    # 卖出信号: 下跌趋势 + 放量阴线
    data['sell_signal'] = (
        (data['trend'] == -1) & 
        (data['volume_spike']) & 
        (data['is_bearish']) &
        (data['volume_ma'].notna())
    )
    
    return data


def generate_signals(
    df: pd.DataFrame,
    stop_loss_pct: float = 0.05,
    take_profit_pct: float = 0.10,
) -> pd.DataFrame:
    """
    生成交易信号和仓位状态
    
    Args:
        df: 包含指标的DataFrame
        stop_loss_pct: 止损百分比
        take_profit_pct: 止盈触发百分比
        
    Returns:
        添加了交易信号和仓位状态的DataFrame
    """
    data = df.copy()
    
    # 初始化
    data['signal'] = 0  # 1=买入, -1=卖出, 0=无信号
    data['position'] = 0  # 1=多头, -1=空头, 0=空仓
    data['entry_price'] = np.nan
    data['stop_loss'] = np.nan
    data['take_profit'] = np.nan
    
    # 状态变量
    position = 0
    entry_price = 0
    stop_loss_price = 0
    take_profit_price = 0
    
    signals = []
    
    for i in range(len(data)):
        row = data.iloc[i]
        current_price = row['Close']
        
        if position == 0:
            # 空仓状态，检查买入信号
            if row['buy_signal']:
                # 买入开多
                position = 1
                entry_price = current_price
                stop_loss_price = entry_price * (1 - stop_loss_pct)
                take_profit_price = entry_price * (1 + take_profit_pct)
                data.iloc[i, data.columns.get_loc('signal')] = 1
                data.iloc[i, data.columns.get_loc('position')] = 1
                data.iloc[i, data.columns.get_loc('entry_price')] = entry_price
                data.iloc[i, data.columns.get_loc('stop_loss')] = stop_loss_price
                data.iloc[i, data.columns.get_loc('take_profit')] = take_profit_price
            elif row['sell_signal']:
                # 卖出开空 (如果想做空的话)
                position = -1
                entry_price = current_price
                stop_loss_price = entry_price * (1 + stop_loss_pct)
                take_profit_price = entry_price * (1 - take_profit_pct)
                data.iloc[i, data.columns.get_loc('signal')] = -1
                data.iloc[i, data.columns.get_loc('position')] = -1
                data.iloc[i, data.columns.get_loc('entry_price')] = entry_price
                data.iloc[i, data.columns.get_loc('stop_loss')] = stop_loss_price
                data.iloc[i, data.columns.get_loc('take_profit')] = take_profit_price
        elif position == 1:
            # 多头持仓
            data.iloc[i, data.columns.get_loc('position')] = 1
            data.iloc[i, data.columns.get_loc('entry_price')] = entry_price
            data.iloc[i, data.columns.get_loc('stop_loss')] = stop_loss_price
            data.iloc[i, data.columns.get_loc('take_profit')] = take_profit_price
            
            # 检查是否触发止损或止盈
            should_close = False
            close_reason = ''
            
            # 止损
            if current_price <= stop_loss_price:
                should_close = True
                close_reason = 'stop_loss'
            # 止盈 (价格回落时)
            elif current_price >= take_profit_price:
                # 检查价格是否从高点回落
                if i > 0:
                    prev_high = data['High'].iloc[max(0, i-10):i].max()
                    if current_price < prev_high * 0.98:  # 从高点回落2%
                        should_close = True
                        close_reason = 'take_profit'
            
            # 趋势反转检查
            if row['trend'] == -1 and row['is_bearish']:
                should_close = True
                close_reason = 'trend_reversal'
            
            if should_close:
                position = 0
                data.iloc[i, data.columns.get_loc('position')] = 0
                data.iloc[i, data.columns.get_loc('signal')] = -1  # 卖出平仓
                
        elif position == -1:
            # 空头持仓
            data.iloc[i, data.columns.get_loc('position')] = -1
            data.iloc[i, data.columns.get_loc('entry_price')] = entry_price
            data.iloc[i, data.columns.get_loc('stop_loss')] = stop_loss_price
            data.iloc[i, data.columns.get_loc('take_profit')] = take_profit_price
            
            # 检查是否触发止损或止盈
            should_close = False
            
            if current_price >= stop_loss_price:
                should_close = True
                close_reason = 'stop_loss'
            elif current_price <= take_profit_price:
                if i > 0:
                    prev_low = data['Low'].iloc[max(0, i-10):i].min()
                    if current_price > prev_low * 1.02:
                        should_close = True
                        close_reason = 'take_profit'
            
            if row['trend'] == 1 and row['is_bullish']:
                should_close = True
                close_reason = 'trend_reversal'
            
            if should_close:
                position = 0
                data.iloc[i, data.columns.get_loc('position')] = 0
                data.iloc[i, data.columns.get_loc('signal')] = 1  # 买入平仓
    
    return data


def get_strategy_params() -> Dict:
    """获取策略默认参数"""
    return {
        'trend_ma_period': 20,       # 趋势判断均线周期
        'volume_ma_period': 20,      # 成交量均线周期
        'volume_ratio': 1.5,         # 成交量放大倍数
        'stop_loss_pct': 0.05,       # 止损5%
        'take_profit_pct': 0.10,     # 止盈10%
    }


def get_strategy_name() -> str:
    """获取策略名称"""
    return "Equity Millipede (Minutes)"


def get_strategy_description() -> str:
    """获取策略描述"""
    return """
    Equity Millipede 策略 (分钟级别)
    
    核心理念:
    - 顺势交易: 顺着主要趋势方向开仓
    - 入场时机: 在分钟K线开盘时顺势入场
    - 放量确认: 成交量明显放大时入场
    - 止损: 设置5%止损
    - 止盈: 10%后移动止损或趋势反转出场
    
    买入条件:
    1. 趋势为上涨 (快速EMA > 慢速EMA)
    2. 成交量放大 (大于20日均量的1.5倍)
    3. 阳线收盘
    
    卖出条件:
    1. 触发止损
    2. 触发止盈
    3. 趋势反转
    """
