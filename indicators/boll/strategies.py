import pandas as pd
import numpy as np
from core.backtest_engine import BaseStrategy


class MovingAverageStrategy(BaseStrategy):
    """绉诲姩骞冲潎绾跨瓥鐣?""
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        """
        鍒濆鍖栫Щ鍔ㄥ钩鍧囩嚎绛栫暐
        
        Args:
            short_period: 鐭湡绉诲姩骞冲潎绾垮懆鏈?            long_period: 闀挎湡绉诲姩骞冲潎绾垮懆鏈?        """
        super().__init__(name=f"MA{short_period}-{long_period}")
        self.short_period = short_period
        self.long_period = long_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        鐢熸垚浜ゆ槗淇″彿
        
        绛栫暐閫昏緫锛?        - 褰撶煭鏈烳A涓婄┛闀挎湡MA鏃讹紝浜х敓涔板叆淇″彿锛堥噾鍙夛級
        - 褰撶煭鏈烳A涓嬬┛闀挎湡MA鏃讹紝浜х敓鍗栧嚭淇″彿锛堟鍙夛級
        
        Args:
            data: 鍖呭惈OHLCV鏁版嵁鐨凞ataFrame
        
        Returns:
            娣诲姞浜嗕俊鍙峰垪鐨凞ataFrame
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
    """RSI绛栫暐"""
    
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        """
        鍒濆鍖朢SI绛栫暐
        
        Args:
            period: RSI鍛ㄦ湡
            overbought: 瓒呬拱闃堝€?            oversold: 瓒呭崠闃堝€?        """
        super().__init__(name=f"RSI{period}")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        鐢熸垚浜ゆ槗淇″彿
        
        绛栫暐閫昏緫锛?        - 褰揜SI浣庝簬瓒呭崠闃堝€兼椂锛屼骇鐢熶拱鍏ヤ俊鍙?        - 褰揜SI楂樹簬瓒呬拱闃堝€兼椂锛屼骇鐢熷崠鍑轰俊鍙?        
        Args:
            data: 鍖呭惈OHLCV鏁版嵁鐨凞ataFrame
        
        Returns:
            娣诲姞浜嗕俊鍙峰垪鐨凞ataFrame
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
    """甯冩灄甯︾瓥鐣?""
    
    def __init__(self, period: int = 20, std_dev: float = 2):
        """
        鍒濆鍖栧竷鏋楀甫绛栫暐
        
        Args:
            period: 甯冩灄甯﹀懆鏈?            std_dev: 鏍囧噯宸€嶆暟
        """
        super().__init__(name=f"BB{period}")
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        鐢熸垚浜ゆ槗淇″彿
        
        绛栫暐閫昏緫锛?        - 褰撲环鏍艰Е鍙婁笅杞ㄦ椂锛屼骇鐢熶拱鍏ヤ俊鍙?        - 褰撲环鏍艰Е鍙婁笂杞ㄦ椂锛屼骇鐢熷崠鍑轰俊鍙?        
        Args:
            data: 鍖呭惈OHLCV鏁版嵁鐨凞ataFrame
        
        Returns:
            娣诲姞浜嗕俊鍙峰垪鐨凞ataFrame
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
    """MACD绛栫暐"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        鍒濆鍖朚ACD绛栫暐
        
        Args:
            fast_period: 蹇嚎鍛ㄦ湡
            slow_period: 鎱㈢嚎鍛ㄦ湡
            signal_period: 淇″彿绾垮懆鏈?        """
        super().__init__(name=f"MACD{fast_period}-{slow_period}")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        鐢熸垚浜ゆ槗淇″彿
        
        绛栫暐閫昏緫锛?        - 褰揗ACD绾夸笂绌夸俊鍙风嚎鏃讹紝浜х敓涔板叆淇″彿
        - 褰揗ACD绾夸笅绌夸俊鍙风嚎鏃讹紝浜х敓鍗栧嚭淇″彿
        
        Args:
            data: 鍖呭惈OHLCV鏁版嵁鐨凞ataFrame
        
        Returns:
            娣诲姞浜嗕俊鍙峰垪鐨凞ataFrame
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
    """鍛ㄥ竷鏋楀甫绛栫暐"""
    
    def __init__(self, period: int = 20, std_dev: float = 2):
        """
        鍒濆鍖栧懆甯冩灄甯︾瓥鐣?        
        Args:
            period: 甯冩灄甯﹀懆鏈燂紙鍛ㄦ暟锛?            std_dev: 鏍囧噯宸€嶆暟
        """
        super().__init__(name=f"WeeklyBoll{period}")
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        鐢熸垚浜ゆ槗淇″彿
        
        绛栫暐閫昏緫锛?        - 涓嬭穼鏈燂細K绾垮浜庡懆BOLL甯︿腑绾夸笅锛屼笖鍛↘鐨勬敹鐩樹环娌℃湁楂樹簬鍛˙OLL甯︿腑绾?        - 涓婅鏈燂細K绾跨殑鏀剁洏浠锋病鏈変綆浜庡懆BOLL甯︿綆绾?        - 涔板叆淇″彿锛氳繘鍏ヤ笅璺屾湡鍚庯紝鍛↘瓒呰繃BOLL甯︾殑楂樼嚎鍚庯紝鍥炶惤鍒癇OLL涓嚎闄勮繎涔板叆
        - 鍗栧嚭淇″彿锛氬懆K 3娆′綆浜庢垨闈犺繎BOLL甯﹀簳绾垮悗锛屾渶鍚庝竴娆¤秴鍑築OLL甯﹂珮绾挎椂鍗栧嚭
        
        Args:
            data: 鍖呭惈OHLCV鏁版嵁鐨凞ataFrame
        
        Returns:
            娣诲姞浜嗕俊鍙峰垪鐨凞ataFrame
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

