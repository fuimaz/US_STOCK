import pandas as pd
import numpy as np
from backtest_engine import BaseStrategy


class MovingAverageStrategy(BaseStrategy):
    """移动平均线策略"""
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        """
        初始化移动平均线策略
        
        Args:
            short_period: 短期移动平均线周期
            long_period: 长期移动平均线周期
        """
        super().__init__(name=f"MA{short_period}-{long_period}")
        self.short_period = short_period
        self.long_period = long_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        策略逻辑：
        - 当短期MA上穿长期MA时，产生买入信号（金叉）
        - 当短期MA下穿长期MA时，产生卖出信号（死叉）
        
        Args:
            data: 包含OHLCV数据的DataFrame
        
        Returns:
            添加了信号列的DataFrame
        """
        df = data.copy()
        
        df[f'MA{self.short_period}'] = df['Close'].rolling(window=self.short_period).mean()
        df[f'MA{self.long_period}'] = df['Close'].rolling(window=self.long_period).mean()
        
        df['signal'] = 0
        
        ma_short = df[f'MA{self.short_period}']
        ma_long = df[f'MA{self.long_period}']
        
        df.loc[ma_short > ma_long, 'signal'] = 1
        df.loc[ma_short < ma_long, 'signal'] = -1
        
        df['signal'] = df['signal'].diff()
        
        df.loc[df['signal'] == 2, 'signal'] = 1
        df.loc[df['signal'] == -2, 'signal'] = -1
        
        return df


class RSIStrategy(BaseStrategy):
    """RSI策略"""
    
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        """
        初始化RSI策略
        
        Args:
            period: RSI周期
            overbought: 超买阈值
            oversold: 超卖阈值
        """
        super().__init__(name=f"RSI{period}")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        策略逻辑：
        - 当RSI低于超卖阈值时，产生买入信号
        - 当RSI高于超买阈值时，产生卖出信号
        
        Args:
            data: 包含OHLCV数据的DataFrame
        
        Returns:
            添加了信号列的DataFrame
        """
        df = data.copy()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['signal'] = 0
        
        df.loc[df['RSI'] < self.oversold, 'signal'] = 1
        df.loc[df['RSI'] > self.overbought, 'signal'] = -1
        
        df['signal'] = df['signal'].diff()
        
        df.loc[df['signal'] == 2, 'signal'] = 1
        df.loc[df['signal'] == -2, 'signal'] = -1
        
        return df


class BollingerBandsStrategy(BaseStrategy):
    """布林带策略"""
    
    def __init__(self, period: int = 20, std_dev: float = 2):
        """
        初始化布林带策略
        
        Args:
            period: 布林带周期
            std_dev: 标准差倍数
        """
        super().__init__(name=f"BB{period}")
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        策略逻辑：
        - 当价格触及下轨时，产生买入信号
        - 当价格触及上轨时，产生卖出信号
        
        Args:
            data: 包含OHLCV数据的DataFrame
        
        Returns:
            添加了信号列的DataFrame
        """
        df = data.copy()
        
        df['Middle'] = df['Close'].rolling(window=self.period).mean()
        df['Upper'] = df['Middle'] + df['Close'].rolling(window=self.period).std() * self.std_dev
        df['Lower'] = df['Middle'] - df['Close'].rolling(window=self.period).std() * self.std_dev
        
        df['signal'] = 0
        
        df.loc[df['Close'] <= df['Lower'], 'signal'] = 1
        df.loc[df['Close'] >= df['Upper'], 'signal'] = -1
        
        df['signal'] = df['signal'].diff()
        
        df.loc[df['signal'] == 2, 'signal'] = 1
        df.loc[df['signal'] == -2, 'signal'] = -1
        
        return df


class MACDStrategy(BaseStrategy):
    """MACD策略"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        初始化MACD策略
        
        Args:
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
        """
        super().__init__(name=f"MACD{fast_period}-{slow_period}")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        策略逻辑：
        - 当MACD线上穿信号线时，产生买入信号
        - 当MACD线下穿信号线时，产生卖出信号
        
        Args:
            data: 包含OHLCV数据的DataFrame
        
        Returns:
            添加了信号列的DataFrame
        """
        df = data.copy()
        
        ema_fast = df['Close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=self.slow_period, adjust=False).mean()
        
        df['MACD'] = ema_fast - ema_slow
        df['Signal'] = df['MACD'].ewm(span=self.signal_period, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']
        
        df['signal'] = 0
        
        df.loc[df['MACD'] > df['Signal'], 'signal'] = 1
        df.loc[df['MACD'] < df['Signal'], 'signal'] = -1
        
        df['signal'] = df['signal'].diff()
        
        df.loc[df['signal'] == 2, 'signal'] = 1
        df.loc[df['signal'] == -2, 'signal'] = -1
        
        return df


class WeeklyBollingerStrategy(BaseStrategy):
    """周布林带策略"""
    
    def __init__(self, period: int = 20, std_dev: float = 2):
        """
        初始化周布林带策略
        
        Args:
            period: 布林带周期（周数）
            std_dev: 标准差倍数
        """
        super().__init__(name=f"WeeklyBoll{period}")
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        策略逻辑：
        - 下跌期：K线处于周BOLL带中线下，且周K的收盘价没有高于周BOLL带中线
        - 上行期：K线的收盘价没有低于周BOLL带低线
        - 买入信号：进入下跌期后，周K超过BOLL带的高线后，回落到BOLL中线附近买入
        - 卖出信号：周K 3次低于或靠近BOLL带底线后，最后一次超出BOLL带高线时卖出
        
        Args:
            data: 包含OHLCV数据的DataFrame
        
        Returns:
            添加了信号列的DataFrame
        """
        df = data.copy()
        
        df['Middle'] = df['Close'].rolling(window=self.period).mean()
        df['Upper'] = df['Middle'] + df['Close'].rolling(window=self.period).std() * self.std_dev
        df['Lower'] = df['Middle'] - df['Close'].rolling(window=self.period).std() * self.std_dev
        
        df['signal'] = 0
        
        for i in range(len(df)):
            if i < self.period:
                df.loc[df.index[i], 'signal'] = 0
                continue
            
            current_close = df['Close'].iloc[i]
            current_middle = df['Middle'].iloc[i]
            current_upper = df['Upper'].iloc[i]
            current_lower = df['Lower'].iloc[i]
            
            if df['signal'].iloc[i-1] == 0:
                if current_close < current_middle:
                    df.loc[df.index[i], 'signal'] = -1
                else:
                    df.loc[df.index[i], 'signal'] = 1
            elif df['signal'].iloc[i-1] == -1:
                if current_close > current_upper:
                    df.loc[df.index[i], 'signal'] = 2
                else:
                    df.loc[df.index[i], 'signal'] = -1
            elif df['signal'].iloc[i-1] == 2:
                if abs(current_close - current_lower) < (current_upper - current_lower) * 0.1:
                    df.loc[df.index[i], 'signal'] = 1
                else:
                    df.loc[df.index[i], 'signal'] = 2
            elif df['signal'].iloc[i-1] == 1:
                if current_close < current_lower:
                    df.loc[df.index[i], 'signal'] = -1
                else:
                    df.loc[df.index[i], 'signal'] = 1
        
        return df
