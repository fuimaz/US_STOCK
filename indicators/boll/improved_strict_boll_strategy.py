"""
鏀硅繘鐨勪弗鏍煎竷鏋楀甫绛栫暐
浣跨敤鏇寸幇瀹炵殑涓婅鏈熷畾涔?"""
import pandas as pd
import numpy as np
from core.backtest_engine import BaseStrategy

class ImprovedStrictBollStrategy(BaseStrategy):
    """鏀硅繘鐨勪弗鏍煎竷鏋楀甫绛栫暐 - 浣跨敤鏇寸幇瀹炵殑涓婅鏈熷畾涔?""
    
    def __init__(self, period=20, std_dev=2, min_uptrend_days=20, min_interval_days=10, 
                 ma_period=60, uptrend_threshold=0.5):
        """
        鍒濆鍖栫瓥鐣?        
        Args:
            period: 甯冩灄甯﹀懆鏈?            std_dev: 鏍囧噯宸€嶆暟
            min_uptrend_days: 鏈€灏忎笂琛屾湡澶╂暟锛堜竴涓湀绾?0涓氦鏄撴棩锛?            min_interval_days: 鏈€灏忛棿闅斿ぉ鏁帮紙2鍛ㄧ害10涓氦鏄撴棩锛?            ma_period: 鐢ㄤ簬鍒ゆ柇瓒嬪娍鐨勭Щ鍔ㄥ钩鍧囩嚎鍛ㄦ湡
            uptrend_threshold: 涓婅鏈熷垽鏂槇鍊硷紙0-1涔嬮棿锛岃秺楂樿秺涓ユ牸锛?        """
        super().__init__("ImprovedStrictBollStrategy")
        self.period = period
        self.std_dev = std_dev
        self.min_uptrend_days = min_uptrend_days
        self.min_interval_days = min_interval_days
        self.ma_period = ma_period
        self.uptrend_threshold = uptrend_threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        鐢熸垚浜ゆ槗淇″彿
        
        Args:
            data: 鍖呭惈OHLCV鏁版嵁鐨凞ataFrame
        
        Returns:
            娣诲姞浜嗕俊鍙峰垪鐨凞ataFrame
        """
        df = data.copy()
        
        # 璁＄畻甯冩灄甯?        df['middle_band'] = df['Close'].rolling(window=self.period).mean()
        df['std'] = df['Close'].rolling(window=self.period).std()
        df['upper_band'] = df['middle_band'] + self.std_dev * df['std']
        df['lower_band'] = df['middle_band'] - self.std_dev * df['std']
        
        # 璁＄畻绉诲姩骞冲潎绾跨敤浜庡垽鏂秼鍔?        df['ma_long'] = df['Close'].rolling(window=self.ma_period).mean()
        df['ma_short'] = df['Close'].rolling(window=self.period).mean()
        
        # 鍒濆鍖栫姸鎬佸彉閲?        signals = pd.Series(0, index=df.index)
        
        # 鐘舵€佸彉閲?        in_uptrend = False
        uptrend_start_idx = 0
        
        # 鐮翠笅杞ㄧ浉鍏崇姸鎬?        lower_band_breaks = []  # 璁板綍鐮翠笅杞ㄧ殑鏃ユ湡
        last_lower_band_break_idx = -1
        
        # 鍙嶅脊鐩稿叧鐘舵€?        middle_band_crosses = []  # 璁板綍绌夸腑杞ㄧ殑鏃ユ湡
        last_middle_band_cross_idx = -1
        
        # 浜ゆ槗鐘舵€?        position = 0
        buy_idx = -1
        
        # 閬嶅巻姣忎釜浜ゆ槗鏃?        for i in range(len(df)):
            current_price = df['Close'].iloc[i]
            current_high = df['High'].iloc[i]
            current_low = df['Low'].iloc[i]
            middle_band = df['middle_band'].iloc[i]
            upper_band = df['upper_band'].iloc[i]
            lower_band = df['lower_band'].iloc[i]
            ma_long = df['ma_long'].iloc[i]
            ma_short = df['ma_short'].iloc[i]
            
            # 妫€鏌ユ槸鍚︽湁瓒冲鐨勬暟鎹?            if pd.isna(middle_band) or pd.isna(upper_band) or pd.isna(lower_band) or pd.isna(ma_long):
                continue
            
            # 1. 鍒ゆ柇鏄惁澶勪簬涓婅鏈燂紙鏀硅繘鐗堬級
            # 涓婅鏈熷畾涔夛細
            # - 浠锋牸鍦ㄩ暱鏈熺Щ鍔ㄥ钩鍧囩嚎涔嬩笂
            # - 鐭湡绉诲姩骞冲潎绾垮湪闀挎湡绉诲姩骞冲潎绾夸箣涓?            # - 杩囧幓涓€娈垫椂闂村唴锛屽垱鏂伴珮鐨勫ぉ鏁板崰姣旇秴杩囬槇鍊?            # - 浠锋牸杩戞湡鏈変笂鍗囪秼鍔?            
            if in_uptrend:
                # 妫€鏌ヤ笂琛屾湡鏄惁缁撴潫
                # 鏉′欢锛氫环鏍艰穼鐮撮暱鏈熷潎绾匡紝鎴栫煭鏈熷潎绾胯穼鐮撮暱鏈熷潎绾?                if current_price < ma_long or ma_short < ma_long:
                    in_uptrend = False
                    uptrend_start_idx = 0
                    lower_band_breaks = []
                    middle_band_crosses = []
            else:
                # 妫€鏌ユ槸鍚﹀紑濮嬫柊鐨勪笂琛屾湡
                # 鏉′欢锛?                # 1. 浠锋牸鍦ㄩ暱鏈熷潎绾夸箣涓?                # 2. 鐭湡鍧囩嚎鍦ㄩ暱鏈熷潎绾夸箣涓?                # 3. 杩囧幓min_uptrend_days澶╁唴锛屽垱鏂伴珮鐨勫ぉ鏁板崰姣旇秴杩囬槇鍊?                # 4. 浠锋牸杩戞湡鏈変笂鍗囪秼鍔?                
                if i >= self.min_uptrend_days:
                    # 鏉′欢1鍜?
                    if current_price > ma_long and ma_short > ma_long:
                        # 鏉′欢3锛氭鏌ュ垱鏂伴珮鐨勫ぉ鏁板崰姣?                        recent_highs = df['High'].iloc[i - self.min_uptrend_days:i + 1]
                        new_high_days = 0
                        for j in range(1, len(recent_highs)):
                            if recent_highs.iloc[j] > recent_highs.iloc[j - 1]:
                                new_high_days += 1
                        
                        new_high_ratio = new_high_days / len(recent_highs)
                        
                        # 鏉′欢4锛氭鏌ヤ环鏍间笂鍗囪秼鍔?                        price_change = (current_price - df['Close'].iloc[i - self.min_uptrend_days]) / df['Close'].iloc[i - self.min_uptrend_days]
                        
                        # 缁煎悎鍒ゆ柇
                        if new_high_ratio >= self.uptrend_threshold and price_change > 0:
                            in_uptrend = True
                            uptrend_start_idx = i - self.min_uptrend_days
                            lower_band_breaks = []
                            middle_band_crosses = []
            
            # 2. 妫€娴嬬牬涓嬭建
            if in_uptrend and current_low <= lower_band:
                # 妫€鏌ユ槸鍚﹁窛绂讳笂娆＄牬涓嬭建宸茬粡瓒呰繃鏈€灏忛棿闅?                if last_lower_band_break_idx == -1 or i - last_lower_band_break_idx >= self.min_interval_days:
                    lower_band_breaks.append(i)
                    last_lower_band_break_idx = i
            
            # 3. 妫€娴嬬┛涓建
            if in_uptrend and position == 0:
                # 妫€鏌ユ槸鍚︿粠涓嬫柟鍚戜笂绌胯繃涓建
                if i > 0:
                    prev_price = df['Close'].iloc[i - 1]
                    prev_middle_band = df['middle_band'].iloc[i - 1]
                    
                    # 鍓嶄竴澶╁湪涓建涔嬩笅锛屽綋澶╁湪涓建涔嬩笂
                    if prev_price <= prev_middle_band and current_price > middle_band:
                        # 妫€鏌ユ槸鍚﹁窛绂讳笂娆＄┛涓建宸茬粡瓒呰繃鏈€灏忛棿闅?                        if last_middle_band_cross_idx == -1 or i - last_middle_band_cross_idx >= self.min_interval_days:
                            middle_band_crosses.append(i)
                            last_middle_band_cross_idx = i
            
            # 4. 涔板叆淇″彿锛氬湪涓婅鏈燂紝鍑虹幇鑲′环璺岀牬boll涓嬭建锛屼笖闂撮殧2鍛ㄤ互涓婄殑涓ゆ鍙嶅脊閮芥病鏈変笂绌縝oll甯︿腑杞紝
            # 绗笁娆℃垨鑰呬箣鍚庣殑鍙嶅脊绌胯繃涓建鍚庯紝鍥炶惤鍒颁腑杞ㄤ箣涓嬩拱鍏?            if in_uptrend and position == 0:
                # 妫€鏌ユ槸鍚︽湁瓒冲鐨勭牬涓嬭建娆℃暟
                if len(lower_band_breaks) >= 2:
                    # 妫€鏌ユ槸鍚︽湁瓒冲鐨勭┛涓建娆℃暟
                    if len(middle_band_crosses) >= 3:
                        # 妫€鏌ユ槸鍚︿粠涓婃柟鍚戜笅绌胯繃涓建锛堝洖钀藉埌涓建涔嬩笅锛?                        if i > 0:
                            prev_price = df['Close'].iloc[i - 1]
                            prev_middle_band = df['middle_band'].iloc[i - 1]
                            
                            # 鍓嶄竴澶╁湪涓建涔嬩笂锛屽綋澶╁湪涓建涔嬩笅
                            if prev_price > prev_middle_band and current_price <= middle_band:
                                # 妫€鏌ユ槸鍚︽槸绗笁娆℃垨涔嬪悗鐨勭┛涓建鍚庣殑鍥炶惤
                                last_cross_idx = middle_band_crosses[-1]
                                if last_cross_idx < i and i - last_cross_idx <= self.min_interval_days:
                                    signals.iloc[i] = 1
                                    position = 1
                                    buy_idx = i
            
            # 5. 鍗栧嚭淇″彿锛氬湪涓婅鏈熷嚭鐜拌偂浠烽棿闅?鍛ㄤ互涓?娆¤穼鐮碽oll涓嬭建鍚庯紝缁х画涓婃定鍒癰oll甯︿笂杞ㄦ椂鍗栧嚭
            if in_uptrend and position == 1:
                # 妫€鏌ユ槸鍚︽湁瓒冲鐨勭牬涓嬭建娆℃暟锛堜拱鍏ュ悗锛?                post_buy_breaks = [b for b in lower_band_breaks if b > buy_idx]
                
                if len(post_buy_breaks) >= 2:
                    # 妫€鏌ユ槸鍚﹀埌杈句笂杞?                    if current_high >= upper_band:
                        signals.iloc[i] = -1
                        position = 0
                        buy_idx = -1
            
            # 6. 姝㈡崯锛氬鏋滆穼鐮翠笅杞ㄤ笖涓嶅湪涔板叆淇″彿闄勮繎锛屾鎹?            if position == 1 and i > buy_idx + 5:
                if current_low <= lower_band:
                    signals.iloc[i] = -1
                    position = 0
                    buy_idx = -1
        
        df['signal'] = signals
        
        return df
