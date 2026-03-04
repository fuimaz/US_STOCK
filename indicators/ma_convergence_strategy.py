"""
均线收敛策略指标

策略规则:
1. 日线交易
2. 买入条件:
   - 5日均线 < 20日均线
   - 10日均线 < 20日均线
   - |5日均线 - 10日均线| / 20日均线 <= 1% (5日与10日相差1%内)
   - 5日均线 >= 20日均线 * (1 - 1.5%) (5日均线低于20日均线1.5%以内)
   - 10日均线 >= 20日均线 * (1 - 1.5%) (10日均线低于20日均线1.5%以内)
3. 止损: 4%
4. 止盈: 峰值收益>=10%后回抽MA5止盈
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


def calculate_indicators(
    df: pd.DataFrame,
    ma5_period: int = 5,
    ma10_period: int = 10,
    ma20_period: int = 20,
    ma60_period: int = 60,
    ma120_period: int = 120,
    volume_ma_period: int = 20,
    boll_period: int = 20,
    boll_std: float = 2.0,
) -> pd.DataFrame:
    """
    计算策略所需的指标
    
    Args:
        df: 包含OHLCV数据的DataFrame
        ma5_period: 5日均线周期
        ma10_period: 10日均线周期
        ma20_period: 20日均线周期
        boll_period: 布林带周期
        boll_std: 布林带标准差倍数
    
    Returns:
        添加了指标的DataFrame
    """
    data = df.copy()
    
    # 确保有必要的列
    required_cols = ['Close', 'High', 'Low']
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # 计算均线
    data['ma5'] = data['Close'].rolling(window=ma5_period).mean()
    data['ma10'] = data['Close'].rolling(window=ma10_period).mean()
    data['ma20'] = data['Close'].rolling(window=ma20_period).mean()
    data['ma60'] = data['Close'].rolling(window=ma60_period).mean()
    data['ma120'] = data['Close'].rolling(window=ma120_period).mean()

    # Volume / liquidity indicators (optional; only if Volume exists)
    if 'Volume' in data.columns:
        data['vol_ma'] = data['Volume'].rolling(window=volume_ma_period).mean()
        data['vol_ratio'] = data['Volume'] / data['vol_ma']
        data['amount'] = data['Close'] * data['Volume']
        data['amount_ma'] = data['amount'].rolling(window=volume_ma_period).mean()
    
    # 计算布林带
    data['boll_middle'] = data['Close'].rolling(window=boll_period).mean()
    boll_std_val = data['Close'].rolling(window=boll_period).std()
    data['boll_upper'] = data['boll_middle'] + boll_std * boll_std_val
    data['boll_lower'] = data['boll_middle'] - boll_std * boll_std_val
    
    # 计算均线关系指标
    # 5日均线相对20日均线的位置
    data['ma5_vs_ma20_pct'] = (data['ma5'] - data['ma20']) / data['ma20'] * 100
    # 10日均线相对20日均线的位置
    data['ma10_vs_ma20_pct'] = (data['ma10'] - data['ma20']) / data['ma20'] * 100
    # 5日与10日均线的差距百分比
    data['ma5_ma10_diff_pct'] = abs(data['ma5'] - data['ma10']) / data['ma20'] * 100
    
    return data


def generate_signals(
    df: pd.DataFrame,
    stop_loss_enabled: bool = True,
    stop_loss_pct: float = 0.04,
    ma_diff_threshold: float = 1.0,  # 5日与10日均线相差阈值(%)
    ma_below_threshold: float = 1.5,  # 均线低于20日均线阈值(%)
    take_profit_trigger_pct: float = 0.10,  # 止盈触发：峰值收益>=10%后启动
    time_exit_enabled: bool = False,
    max_holding_days: int = 0,
    downtrend_filter_enabled: bool = True,  # 仅在长期下跌趋势中启用“下跌收敛”过滤
    downtrend_ma_fast: int = 60,
    downtrend_ma_slow: int = 120,
    volume_filter_enabled: bool = False,
    volume_filter_mode: str = "none",  # none|contraction|expansion|contraction_then_expansion
    volume_ma_period: int = 20,
    volume_ratio_max: float = 0.8,  # contraction: Volume <= vol_ma * ratio_max
    volume_ratio_min: float = 1.2,  # expansion: Volume >= vol_ma * ratio_min
    volume_setup_lookback: int = 5,  # contraction_then_expansion: lookback days for contraction setup (shifted by 1)
    volume_setup_ratio_max: float = 0.8,
    entry_volume_ratio_min: float = 1.5,
    slope20_lookback: int = 5,
    slope60_lookback: int = 10,
    slope_accel_lookback: int = 5,
    bb_width_lookback: int = 120,
    bb_width_quantile: float = 0.35,
    close_above_ma20_pct: float = 1.5,
) -> pd.DataFrame:
    """
    生成交易信号和仓位状态
    
    Args:
        df: 包含指标的DataFrame
        stop_loss_pct: 止损百分比
        ma_diff_threshold: 5日与10日均线相差阈值(%)
        ma_below_threshold: 均线低于20日均线阈值(%)
    
    Returns:
        添加了交易信号和仓位状态的DataFrame
    """
    data = df.copy()
    
    # 初始化列
    data['signal'] = 0  # 1=买入, -1=卖出, 0=无信号
    data['position'] = 0  # 1=多头, 0=空仓
    data['entry_price'] = np.nan
    data['stop_loss_price'] = np.nan
    data['exit_price'] = np.nan
    data['exit_reason'] = ''
    data['take_profit_price'] = np.nan  # 止盈参考线（MA5）
    
    # 买入条件（基础条件）:
    # 1. ma5 < ma20 (5日在20日下方)
    # 2. ma10 < ma20 (10日在20日下方)
    # 3. |ma5 - ma10| / ma20 <= ma_diff_threshold (5日与10日相差1%内)
    # 4. ma5 >= ma20 * (1 - ma_below_threshold/100) (5日低于20日1.5%以内)
    # 5. ma10 >= ma20 * (1 - ma_below_threshold/100) (10日低于20日1.5%以内)

    volume_condition = (data.get('Volume', 1) > 0)
    if 'Volume' in data.columns:
        if 'vol_ma' not in data.columns:
            data['vol_ma'] = data['Volume'].rolling(window=volume_ma_period).mean()
            data['vol_ratio'] = data['Volume'] / data['vol_ma']
        entry_volume_condition = (
            data['vol_ma'].notna()
            & (data['Volume'] >= data['vol_ma'] * float(entry_volume_ratio_min))
        )
    else:
        entry_volume_condition = False

    if volume_filter_enabled and ('Volume' in data.columns):

        vol_ratio = data['vol_ratio']
        mode = (volume_filter_mode or "none").strip().lower()
        if mode == "contraction":
            volume_condition = volume_condition & vol_ratio.notna() & (vol_ratio <= float(volume_ratio_max))
        elif mode == "expansion":
            volume_condition = volume_condition & vol_ratio.notna() & (vol_ratio >= float(volume_ratio_min))
        elif mode in ("contraction_then_expansion", "contract_breakout", "contract-breakout"):
            setup = (
                vol_ratio.rolling(window=volume_setup_lookback, min_periods=volume_setup_lookback)
                .mean()
                .shift(1)
            )
            volume_condition = (
                volume_condition
                & setup.notna()
                & vol_ratio.notna()
                & (setup <= float(volume_setup_ratio_max))
                & (vol_ratio >= float(volume_ratio_min))
            )
        elif mode == "none":
            pass
        else:
            raise ValueError(f"Unknown volume_filter_mode: {volume_filter_mode}")

    base_buy_condition = (
        (data['ma5'] < data['ma20']) &  # 5日在20日下方
        (data['ma10'] < data['ma20']) &  # 10日在20日下方
        (data['ma5_ma10_diff_pct'] <= ma_diff_threshold) &  # 5日与10日相差1%内
        (data['ma5_vs_ma20_pct'] >= -ma_below_threshold) &  # 5日低于20日1.5%以内
        (data['ma10_vs_ma20_pct'] >= -ma_below_threshold) &  # 10日低于20日1.5%以内
        (data['Close'] > data['ma20'] * (1.0 + float(close_above_ma20_pct) / 100.0)) &
        entry_volume_condition &
        volume_condition &
        (data['ma5'].notna()) & (data['ma10'].notna()) & (data['ma20'].notna())
    )

    # 在“长期下跌趋势”中，额外要求“下跌收敛/变缓”才允许买入；上涨/震荡不加该过滤
    if downtrend_filter_enabled:
        ma_fast_col = f"ma{downtrend_ma_fast}"
        ma_slow_col = f"ma{downtrend_ma_slow}"
        if ma_fast_col not in data.columns:
            data[ma_fast_col] = data['Close'].rolling(window=downtrend_ma_fast).mean()
        if ma_slow_col not in data.columns:
            data[ma_slow_col] = data['Close'].rolling(window=downtrend_ma_slow).mean()

        ma_fast = data[ma_fast_col]
        ma_slow = data[ma_slow_col]

        log_ma20 = np.log(data['ma20'])
        log_ma_fast = np.log(ma_fast)
        slope20 = (log_ma20 - log_ma20.shift(slope20_lookback)) / slope20_lookback
        slope_fast = (log_ma_fast - log_ma_fast.shift(slope60_lookback)) / slope60_lookback

        downtrend = (ma_fast < ma_slow) & (slope_fast < 0)

        if {'boll_upper', 'boll_lower', 'boll_middle'}.issubset(data.columns):
            bb_width = (data['boll_upper'] - data['boll_lower']) / data['boll_middle']
            bb_width_th = bb_width.rolling(window=bb_width_lookback, min_periods=bb_width_lookback).quantile(bb_width_quantile)
            vol_contract = bb_width_th.notna() & (bb_width <= bb_width_th)
        else:
            vol_contract = False

        down_decelerating = slope20.notna() & (slope20 < 0) & (slope20 > slope20.shift(slope_accel_lookback))
        downtrend_converging = down_decelerating & vol_contract

        data['buy_condition'] = base_buy_condition & (~downtrend | downtrend_converging)
    else:
        data['buy_condition'] = base_buy_condition
    
    # 状态变量
    position = 0
    entry_price = 0
    entry_ts: Optional[pd.Timestamp] = None
    stop_loss_price = 0
    take_profit_price = np.nan
    peak_price = 0.0
    peak_profit_pct = 0.0
    
    for i in range(len(data)):
        row = data.iloc[i]
        current_price = row['Close']
        current_date = data.index[i]
        
        if position == 0:
            # 空仓状态，检查买入信号
            if row['buy_condition']:
                # 买入开多
                position = 1
                entry_price = current_price
                entry_ts = current_date if isinstance(current_date, pd.Timestamp) else None
                # 止损: 买入价 * (1 - 4%)
                stop_loss_price = entry_price * (1 - stop_loss_pct) if stop_loss_enabled else np.nan
                # 止盈参考线：MA5（止盈触发逻辑参考 volume_breakout_strategy.py）
                peak_price = float(entry_price)
                peak_profit_pct = 0.0
                take_profit_price = row.get('ma5', np.nan)
                
                data.iloc[i, data.columns.get_loc('signal')] = 1
                data.iloc[i, data.columns.get_loc('position')] = 1
                data.iloc[i, data.columns.get_loc('exit_price')] = np.nan
                data.iloc[i, data.columns.get_loc('exit_reason')] = ''
                data.iloc[i, data.columns.get_loc('entry_price')] = entry_price
                data.iloc[i, data.columns.get_loc('stop_loss_price')] = stop_loss_price
                data.iloc[i, data.columns.get_loc('take_profit_price')] = take_profit_price
        else:
            # 持仓状态
            if not pd.isna(row.get('ma5', np.nan)):
                take_profit_price = row['ma5']
            data.iloc[i, data.columns.get_loc('position')] = 1
            data.iloc[i, data.columns.get_loc('entry_price')] = entry_price
            data.iloc[i, data.columns.get_loc('stop_loss_price')] = stop_loss_price
            data.iloc[i, data.columns.get_loc('take_profit_price')] = take_profit_price
            
            # 检查是否触发止损或止盈
            should_close = False
            close_reason = ''
            open_price = row['Open'] if 'Open' in data.columns else np.nan

            holding_days = 0
            if entry_ts is not None and isinstance(current_date, pd.Timestamp):
                holding_days = int((current_date - entry_ts).days)

            if pd.notna(row.get('High', np.nan)) and entry_price > 0:
                peak_price = max(peak_price, float(row['High']))
                peak_profit_pct = max(peak_profit_pct, peak_price / entry_price - 1.0)
            
            # 止损检查: 价格低于止损价
            if stop_loss_enabled and pd.notna(stop_loss_price):
                if not pd.isna(open_price) and open_price <= stop_loss_price:
                    should_close = True
                    close_reason = 'stop_loss_gap'
                elif row['Low'] <= stop_loss_price:
                    should_close = True
                    close_reason = 'stop_loss'

            # 时间退出：持仓时间过长且从未达到止盈触发条件（峰值收益 < take_profit_trigger_pct）
            if (
                (not should_close)
                and time_exit_enabled
                and int(max_holding_days) > 0
                and holding_days >= int(max_holding_days)
                and peak_profit_pct < float(take_profit_trigger_pct)
            ):
                should_close = True
                close_reason = 'time_exit'
            # 止盈：峰值收益达到阈值后，回抽跌破MA5
            if (not should_close) and peak_profit_pct >= take_profit_trigger_pct and pd.notna(row.get('ma5', np.nan)):
                ma5_val = float(row['ma5'])
                if current_price < ma5_val and peak_price > ma5_val:
                    should_close = True
                    close_reason = 'take_profit_ma5'
            
            if should_close:
                if close_reason == 'stop_loss_gap':
                    exit_price = open_price
                elif close_reason == 'stop_loss':
                    exit_price = stop_loss_price
                else:
                    exit_price = current_price

                position = 0
                entry_ts = None
                data.iloc[i, data.columns.get_loc('position')] = 0
                data.iloc[i, data.columns.get_loc('exit_price')] = exit_price
                data.iloc[i, data.columns.get_loc('exit_reason')] = close_reason
                data.iloc[i, data.columns.get_loc('signal')] = -1  # 卖出平仓
    
    return data


def get_strategy_params() -> Dict:
    """获取策略默认参数"""
    return {
        'ma5_period': 5,
        'ma10_period': 10,
        'ma20_period': 20,
        'ma60_period': 60,
        'ma120_period': 120,
        'volume_ma_period': 20,
        'boll_period': 20,
        'boll_std': 2.0,
        'stop_loss_enabled': True,
        'stop_loss_pct': 0.04,  # 止损4%
        'ma_diff_threshold': 1.0,  # 5日与10日均线相差1%内
        'ma_below_threshold': 1.5,  # 均线低于20日均线1.5%以内
        'take_profit_trigger_pct': 0.10,  # 峰值收益>=10%后启动MA5回抽止盈
        'time_exit_enabled': False,
        'max_holding_days': 0,
        'downtrend_filter_enabled': True,
        'downtrend_ma_fast': 60,
        'downtrend_ma_slow': 120,
        'volume_filter_enabled': False,
        'volume_filter_mode': 'none',
        'volume_ratio_max': 0.8,
        'volume_ratio_min': 1.2,
        'volume_setup_lookback': 5,
        'volume_setup_ratio_max': 0.8,
        'entry_volume_ratio_min': 1.5,
        'slope20_lookback': 5,
        'slope60_lookback': 10,
        'slope_accel_lookback': 5,
        'bb_width_lookback': 120,
        'bb_width_quantile': 0.35,
        'close_above_ma20_pct': 1.5,
    }


def get_strategy_name() -> str:
    """获取策略名称"""
    return "均线收敛策略 (MA Convergence)"


def get_strategy_description() -> str:
    """获取策略描述"""
    return """
    均线收敛策略
    
    买入条件:
    1. 5日均线 < 20日均线
    2. 10日均线 < 20日均线
    3. |5日均线 - 10日均线| / 20日均线 <= 1% (均线收敛)
    4. 5日均线 >= 20日均线 * 98.5% (5日低于20日1.5%以内)
    5. 10日均线 >= 20日均线 * 98.5% (10日低于20日1.5%以内)
    
     卖出条件:
     1. 止损: 买入价下跌4%
    2. 止盈: 峰值收益>=10%后，回抽跌破MA5
     """
