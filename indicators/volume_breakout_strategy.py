"""
成交量突破策略:
- 放量阳线(涨幅>0, 成交量放大) -> 做多
- 放量阴线(跌幅<0, 成交量放大) -> 做空
- 5%止损
- 突破日线MA5止盈(涨幅>10%后回抽MA5止盈)
"""
import pandas as pd
import numpy as np
from typing import Optional


class VolumeBreakoutStrategy:
    """
    成交量突破策略
    
    规则:
    1. 放量阳线(close > open AND volume > ma20_volume * 1.5) -> 开多
    2. 放量阴线(close < open AND volume > ma20_volume * 1.5) -> 开空
    3. 5%止损
    4. 涨幅>10%后回抽突破MA5止盈
    """
    
    name = "Volume Breakout Strategy"
    
    def __init__(
        self,
        volume_ma_period: int = 20,
        volume_ratio: float = 1.5,
        stop_loss_pct: float = 0.05,
        take_profit_trigger_pct: float = 0.10,
        ma_period: int = 5,
    ):
        """
        初始化策略参数
        
        Args:
            volume_ma_period: 成交量均线周期
            volume_ratio: 成交量放大倍数
            stop_loss_pct: 止损百分比
            take_profit_trigger_pct: 止盈触发涨幅
            ma_period: MA周期
        """
        self.volume_ma_period = volume_ma_period
        self.volume_ratio = volume_ratio
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_trigger_pct = take_profit_trigger_pct
        self.ma_period = ma_period
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            带有信号的DataFrame
        """
        data = df.copy()
        
        # 统一列名小写
        rename_map = {
            'Open': 'open', 'High': 'high', 'Low': 'low', 
            'Close': 'close', 'Volume': 'volume'
        }
        data.rename(columns=rename_map, inplace=True)
        
        # 计算基础指标
        data['change'] = data['close'].pct_change()  # 涨跌幅
        data['is_bullish'] = data['close'] > data['open']  # 是否阳线
        data['is_bearish'] = data['close'] < data['open']  # 是否阴线
        
        # 成交量均线
        data['volume_ma'] = data['volume'].rolling(window=self.volume_ma_period).mean()
        
        # 计算日内MA5 (使用日线周期数据计算)
        if 'datetime' in data.columns:
            data.set_index('datetime', inplace=True)
        
        # 计算MA5
        data['ma5'] = data['close'].rolling(window=self.ma_period).mean()
        
        # 判断放量: 成交量 > 均线 * 倍数
        data['volume_spike'] = data['volume'] > data['volume_ma'] * self.volume_ratio
        
        # 生成信号
        data['buy_signal'] = False
        data['sell_signal'] = False
        
        # 放量阳线 -> 做多
        data.loc[
            (data['is_bullish']) & 
            (data['volume_spike']) & 
            (data['volume_ma'].notna()),
            'buy_signal'
        ] = True
        
        # 放量阴线 -> 做空
        data.loc[
            (data['is_bearish']) & 
            (data['volume_spike']) & 
            (data['volume_ma'].notna()),
            'sell_signal'
        ] = True
        
        # 止损/止盈信号将在回测引擎中计算
        
        return data


class VolumeBreakoutStrategyIntraday(VolumeBreakoutStrategy):
    """
    适用于分钟数据的成交量突破策略
    使用日线周期计算MA5用于止盈判断
    """
    
    name = "Volume Breakout Intraday Strategy"
    
    def __init__(
        self,
        volume_ma_period: int = 20,
        volume_ratio: float = 1.5,
        stop_loss_pct: float = 0.05,
        take_profit_trigger_pct: float = 0.10,
        ma_period: int = 5,
    ):
        super().__init__(
            volume_ma_period=volume_ma_period,
            volume_ratio=volume_ratio,
            stop_loss_pct=stop_loss_pct,
            take_profit_trigger_pct=take_profit_trigger_pct,
            ma_period=ma_period,
        )
    
    def generate_signals(self, df: pd.DataFrame, daily_ma5: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            df: 分钟级OHLCV数据
            daily_ma5: 日线MA5序列(用于止盈判断)
            
        Returns:
            带有信号的DataFrame
        """
        data = df.copy()
        
        # 统一列名小写
        rename_map = {
            'Open': 'open', 'High': 'high', 'Low': 'low', 
            'Close': 'close', 'Volume': 'volume'
        }
        data.rename(columns=rename_map, inplace=True)
        
        # 确保索引是datetime
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'datetime' in data.columns:
                data['datetime'] = pd.to_datetime(data['datetime'])
                data.set_index('datetime', inplace=True)
        
        # 计算基础指标
        data['change'] = data['close'].pct_change()  # 涨跌幅
        data['is_bullish'] = data['close'] > data['open']  # 是否阳线
        data['is_bearish'] = data['close'] < data['open']  # 是否阴线
        
        # 成交量均线
        data['volume_ma'] = data['volume'].rolling(window=self.volume_ma_period).mean()
        
        # 计算日内MA5
        data['ma5'] = data['close'].rolling(window=self.ma_period).mean()
        
        # 判断放量: 成交量 > 均线 * 倍数
        data['volume_spike'] = data['volume'] > data['volume_ma'] * self.volume_ratio
        
        # 生成信号
        data['buy_signal'] = False
        data['sell_signal'] = False
        
        # 放量阳线 -> 做多
        data.loc[
            (data['is_bullish']) & 
            (data['volume_spike']) & 
            (data['volume_ma'].notna()),
            'buy_signal'
        ] = True
        
        # 放量阴线 -> 做空
        data.loc[
            (data['is_bearish']) & 
            (data['volume_spike']) & 
            (data['volume_ma'].notna()),
            'sell_signal'
        ] = True
        
        return data
