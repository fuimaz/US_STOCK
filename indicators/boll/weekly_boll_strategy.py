import pandas as pd
import numpy as np
from core.backtest_engine import BaseStrategy


class WeeklyBollingerStrategy(BaseStrategy):
    """鍛ㄥ竷鏋楀甫绛栫暐"""
    
    def __init__(self, period: int = 20, std_dev: float = 2, middle_threshold: float = 0.05):
        """
        鍒濆鍖栧懆甯冩灄甯︾瓥鐣?        
        Args:
            period: 甯冩灄甯﹀懆鏈燂紙鍛ㄦ暟锛?            std_dev: 鏍囧噯宸€嶆暟
            middle_threshold: 涓嚎闄勮繎鐨勯槇鍊硷紙鐧惧垎姣旓級
        """
        super().__init__(name=f"WeeklyBoll{period}")
        self.period = period
        self.std_dev = std_dev
        self.middle_threshold = middle_threshold
    
    def _resample_to_weekly(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        灏嗘棩绾挎暟鎹浆鎹负鍛ㄧ嚎鏁版嵁
        
        Args:
            data: 鏃ョ嚎鏁版嵁
        
        Returns:
            鍛ㄧ嚎鏁版嵁
        """
        weekly = data.resample('W').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        return weekly
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        鐢熸垚浜ゆ槗淇″彿
        
        绛栫暐閫昏緫锛?        - 涓婅鏈燂細鍛↘鏀剁洏浠蜂笉璺岀牬甯冩灄甯︿笅杞?        - 涓嬭穼鏈燂細鍛↘鏀剁洏浠疯穼鐮村竷鏋楀甫涓嬭建
        
        涔板叆鏉′欢锛?        1. 甯傚満涔嬪墠澶勪簬涓嬭穼鏈?        2. 鍛↘鏀剁洏浠烽潬杩慴oll甯︿腑杞?%鍐呮椂涔板叆
        
        鍗栧嚭鏉′欢锛?        - 鍦ㄤ笂琛屾湡涓紝鍛↘3娆¤穼鐮翠腑绾垮悗锛屽啀娆′笂娑ㄧ涓€娆¤秴杩囦笂杞ㄦ椂鍗栧嚭
        
        浠撲綅绠＄悊锛?        - 涔板叆鏃朵竴娆℃€у叏閮ㄤ拱鍏ワ紝涔板叆鍚庝笉鍐嶄拱鍏?        - 鍗栧嚭鏃朵竴娆℃€у叏閮ㄥ崠鍑猴紝涓嶅仛绌猴紝鍙仛澶?        
        Args:
            data: 鍖呭惈OHLCV鏁版嵁鐨凞ataFrame锛堟棩绾挎暟鎹級
        
        Returns:
            娣诲姞浜嗕俊鍙峰垪鐨凞ataFrame锛堟棩绾挎暟鎹級
        """
        df = data.copy()
        
        weekly_df = self._resample_to_weekly(df)
        
        weekly_df['Middle'] = weekly_df['Close'].rolling(window=self.period).mean()
        weekly_df['Upper'] = weekly_df['Middle'] + weekly_df['Close'].rolling(window=self.period).std() * self.std_dev
        weekly_df['Lower'] = weekly_df['Middle'] - weekly_df['Close'].rolling(window=self.period).std() * self.std_dev
        
        weekly_df['signal'] = 0
        weekly_df['phase'] = ''
        weekly_df['below_middle_count'] = 0
        weekly_df['market_phase'] = ''
        weekly_df['ready_to_buy'] = False
        weekly_df['ready_to_sell'] = False
        weekly_df['recovered_from_down'] = False
        weekly_df['touched_middle_nearby'] = False
        
        for i in range(len(weekly_df)):
            if i < self.period:
                weekly_df.loc[weekly_df.index[i], 'signal'] = 0
                weekly_df.loc[weekly_df.index[i], 'phase'] = '鍒濆鍖?
                weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
                weekly_df.loc[weekly_df.index[i], 'market_phase'] = '鍒濆鍖?
                weekly_df.loc[weekly_df.index[i], 'ready_to_buy'] = False
                weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
                continue
            
            current_close = weekly_df['Close'].iloc[i]
            current_middle = weekly_df['Middle'].iloc[i]
            current_upper = weekly_df['Upper'].iloc[i]
            current_lower = weekly_df['Lower'].iloc[i]
            prev_signal = weekly_df['signal'].iloc[i-1]
            prev_phase = weekly_df['phase'].iloc[i-1]
            prev_below_count = weekly_df['below_middle_count'].iloc[i-1]
            prev_ready_to_buy = weekly_df['ready_to_buy'].iloc[i-1]
            prev_ready_to_sell = weekly_df['ready_to_sell'].iloc[i-1]
            prev_market_phase = weekly_df['market_phase'].iloc[i-1]
            prev_recovered = weekly_df['recovered_from_down'].iloc[i-1]
            prev_touched_middle = weekly_df['touched_middle_nearby'].iloc[i-1]
            
            if current_close >= current_lower:
                weekly_df.loc[weekly_df.index[i], 'market_phase'] = '涓婅鏈?
            else:
                weekly_df.loc[weekly_df.index[i], 'market_phase'] = '涓嬭穼鏈?
            
            if prev_market_phase == '涓嬭穼鏈? and current_close >= current_lower:
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = True
            elif prev_recovered:
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
            else:
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
            
            if prev_signal == 0:
                weekly_df.loc[weekly_df.index[i], 'signal'] = 0
                weekly_df.loc[weekly_df.index[i], 'phase'] = '绌轰粨'
                weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
                
                middle_distance = abs(current_close - current_middle) / current_middle
                
                if prev_recovered and middle_distance <= self.middle_threshold:
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = True
                    weekly_df.loc[weekly_df.index[i], 'signal'] = 1
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '涔板叆'
                    weekly_df.loc[weekly_df.index[i], 'ready_to_buy'] = False
                    weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                    weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                else:
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = prev_touched_middle
                    weekly_df.loc[weekly_df.index[i], 'ready_to_buy'] = False
                    weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
            
            elif prev_signal == 1:
                if current_close < current_middle:
                    new_below_count = prev_below_count + 1
                    weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = new_below_count
                    weekly_df.loc[weekly_df.index[i], 'signal'] = 1
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '鎸佹湁'
                    weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
                    
                    if new_below_count >= 3:
                        weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = True
                        weekly_df.loc[weekly_df.index[i], 'phase'] = '鍑嗗鍗栧嚭'
                    else:
                        weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                elif current_close > current_upper and prev_ready_to_sell:
                    weekly_df.loc[weekly_df.index[i], 'signal'] = -1
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '鍗栧嚭'
                    weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
                    weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                    weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
                else:
                    weekly_df.loc[weekly_df.index[i], 'signal'] = 1
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '鎸佹湁'
                    weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = prev_below_count
                    weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = prev_ready_to_sell
                    weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
            
            elif prev_signal == -1:
                weekly_df.loc[weekly_df.index[i], 'signal'] = 0
                weekly_df.loc[weekly_df.index[i], 'phase'] = '绌轰粨'
                weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
                weekly_df.loc[weekly_df.index[i], 'ready_to_buy'] = False
                weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
        
        df['Middle'] = df['Close'].rolling(window=self.period * 5).mean()
        df['Upper'] = df['Middle'] + df['Close'].rolling(window=self.period * 5).std() * self.std_dev
        df['Lower'] = df['Middle'] - df['Close'].rolling(window=self.period * 5).std() * self.std_dev
        
        for i in range(len(df)):
            if i < self.period * 5:
                df.loc[df.index[i], 'signal'] = 0
                df.loc[df.index[i], 'phase'] = '鍒濆鍖?
                df.loc[df.index[i], 'market_phase'] = '鍒濆鍖?
                df.loc[df.index[i], 'below_middle_count'] = 0
                df.loc[df.index[i], 'ready_to_buy'] = False
                df.loc[df.index[i], 'ready_to_sell'] = False
                df.loc[df.index[i], 'recovered_from_down'] = False
                df.loc[df.index[i], 'touched_middle_nearby'] = False
                continue
            
            current_date = df.index[i]
            week_start = current_date - pd.Timedelta(days=current_date.weekday())
            week_end = week_start + pd.Timedelta(days=6)
            
            matching_week = weekly_df[(weekly_df.index >= week_start) & (weekly_df.index <= week_end)]
            
            if len(matching_week) > 0:
                week_signal = matching_week['signal'].iloc[-1]
                week_phase = matching_week['phase'].iloc[-1]
                week_market_phase = matching_week['market_phase'].iloc[-1]
                week_below_count = matching_week['below_middle_count'].iloc[-1]
                week_ready_to_buy = matching_week['ready_to_buy'].iloc[-1]
                week_ready_to_sell = matching_week['ready_to_sell'].iloc[-1]
                week_recovered = matching_week['recovered_from_down'].iloc[-1]
                week_touched_middle = matching_week['touched_middle_nearby'].iloc[-1]
                
                # 鑾峰彇璇ュ懆鐨勬渶鍚庝竴涓氦鏄撴棩
                week_trading_days = df[(df.index >= week_start) & (df.index <= week_end)]
                if len(week_trading_days) > 0:
                    last_trading_day = week_trading_days.index[-1]
                    if current_date == last_trading_day:
                        # 鏄鍛ㄧ殑鏈€鍚庝竴涓氦鏄撴棩锛屼娇鐢ㄥ懆绾夸俊鍙峰拰闃舵
                        df.loc[df.index[i], 'signal'] = week_signal
                        df.loc[df.index[i], 'phase'] = week_phase
                    else:
                        # 涓嶆槸璇ュ懆鐨勬渶鍚庝竴涓氦鏄撴棩锛屼繚鎸佷箣鍓嶇殑淇″彿鍜岄樁娈?                        if i > 0:
                            prev_signal = df['signal'].iloc[i-1]
                            # 濡傛灉涔嬪墠鐨勪俊鍙锋槸鍗栧嚭淇″彿锛屽垯閲嶇疆涓虹┖浠?                            if prev_signal == -1:
                                df.loc[df.index[i], 'signal'] = 0
                                df.loc[df.index[i], 'phase'] = '绌轰粨'
                            else:
                                df.loc[df.index[i], 'signal'] = prev_signal
                                df.loc[df.index[i], 'phase'] = df['phase'].iloc[i-1]
                        else:
                            df.loc[df.index[i], 'signal'] = 0
                            df.loc[df.index[i], 'phase'] = '绌轰粨'
                else:
                    # 璇ュ懆娌℃湁浜ゆ槗鏃ワ紝淇濇寔涔嬪墠鐨勪俊鍙峰拰闃舵
                    if i > 0:
                        prev_signal = df['signal'].iloc[i-1]
                        # 濡傛灉涔嬪墠鐨勪俊鍙锋槸鍗栧嚭淇″彿锛屽垯閲嶇疆涓虹┖浠?                        if prev_signal == -1:
                            df.loc[df.index[i], 'signal'] = 0
                            df.loc[df.index[i], 'phase'] = '绌轰粨'
                        else:
                            df.loc[df.index[i], 'signal'] = prev_signal
                            df.loc[df.index[i], 'phase'] = df['phase'].iloc[i-1]
                    else:
                        df.loc[df.index[i], 'signal'] = 0
                        df.loc[df.index[i], 'phase'] = '绌轰粨'
                
                df.loc[df.index[i], 'market_phase'] = week_market_phase
                df.loc[df.index[i], 'below_middle_count'] = week_below_count
                df.loc[df.index[i], 'ready_to_buy'] = week_ready_to_buy
                df.loc[df.index[i], 'ready_to_sell'] = week_ready_to_sell
                df.loc[df.index[i], 'recovered_from_down'] = week_recovered
                df.loc[df.index[i], 'touched_middle_nearby'] = week_touched_middle
            else:
                df.loc[df.index[i], 'signal'] = 0
                df.loc[df.index[i], 'phase'] = '绌轰粨'
                df.loc[df.index[i], 'market_phase'] = '涓婅鏈?
                df.loc[df.index[i], 'below_middle_count'] = 0
                df.loc[df.index[i], 'ready_to_buy'] = False
                df.loc[df.index[i], 'ready_to_sell'] = False
                df.loc[df.index[i], 'recovered_from_down'] = False
                df.loc[df.index[i], 'touched_middle_nearby'] = False
        
        return df

