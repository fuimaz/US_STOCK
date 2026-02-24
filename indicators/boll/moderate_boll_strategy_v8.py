"""
淇鍚庣殑閫備腑甯冩灄甯︾瓥鐣?V8锛堝懆K鐗堟湰锛屼娇鐢ㄧЩ鍔ㄦ鎹燂級
鍩轰簬浠ヤ笅瑙勫垯锛?1. 涓婅鏈熸槸涓嶆柇鍒涙柊楂橈紝鑳芥寔缁竴涓湀浠ヤ笂鐨勫垱鏂伴珮
2. 涔板叆鏃舵満鏄湪涓嬭鏈燂紝鍑虹幇鑲′环璺岀牬boll涓嬭建锛屼笖闂撮殧2鍛ㄤ互涓婄殑2娆″弽寮归兘娌℃湁涓婄┛boll甯︿笂杞紝
   绗笁娆℃垨鑰呬箣鍚庣殑鍙嶅脊绌胯繃涓建鍚庯紝鍥炶惤鍒颁腑杞ㄤ箣涓嬩拱鍏?3. 鍗栧嚭鏄湪涓婅鏈燂紝浣跨敤绉诲姩姝㈡崯锛氫环鏍间粠楂樼偣鍥炶惤涓€瀹氭瘮渚嬶紙榛樿10%锛夋椂鍗栧嚭
"""
import pandas as pd
import numpy as np
from core.backtest_engine import BaseStrategy

class ModerateBollStrategyV8(BaseStrategy):
    """淇鍚庣殑閫備腑甯冩灄甯︾瓥鐣?V8锛堝懆K鐗堟湰锛屼娇鐢ㄧЩ鍔ㄦ鎹燂級"""
    
    def __init__(self, period=20, std_dev=2, min_uptrend_days=20, min_interval_days=10, 
                 ma_period=60, uptrend_threshold=0.5, max_hold_days=120, trailing_stop_pct=0.10):
        """
        鍒濆鍖栫瓥鐣?        
        Args:
            period: 甯冩灄甯﹀懆鏈?            std_dev: 鏍囧噯宸€嶆暟
            min_uptrend_days: 鏈€灏忎笂琛屾湡澶╂暟锛堜竴涓湀绾?0涓氦鏄撴棩锛?            min_interval_days: 鏈€灏忛棿闅斿ぉ鏁帮紙2鍛ㄧ害10涓氦鏄撴棩锛?            ma_period: 鐢ㄤ簬鍒ゆ柇瓒嬪娍鐨勭Щ鍔ㄥ钩鍧囩嚎鍛ㄦ湡
            uptrend_threshold: 涓婅鏈熷垽鏂槇鍊硷紙0-1涔嬮棿锛岃秺楂樿秺涓ユ牸锛?            max_hold_days: 鏈€澶ф寔浠撳ぉ鏁帮紙濡傛灉瓒呰繃杩欎釜澶╂暟浠嶆湭鍗栧嚭锛屽己鍒跺崠鍑猴級
            trailing_stop_pct: 绉诲姩姝㈡崯姣斾緥锛堥粯璁?.10鍗?0%锛?        """
        super().__init__("ModerateBollStrategyV8")
        self.period = period
        self.std_dev = std_dev
        self.min_uptrend_days = min_uptrend_days
        self.min_interval_days = min_interval_days
        self.ma_period = ma_period
        self.uptrend_threshold = uptrend_threshold
        self.max_hold_days = max_hold_days
        self.trailing_stop_pct = trailing_stop_pct
    
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
        
        # 鍙嶅脊鐩稿叧鐘舵€?        upper_band_crosses = []  # 璁板綍绌夸笂杞ㄧ殑鏃ユ湡锛堝弽寮瑰己搴︼級
        middle_band_crosses = []  # 璁板綍绌夸腑杞ㄧ殑鏃ユ湡锛堜拱鍏ヤ俊鍙凤級
        last_upper_band_cross_idx = -1
        last_middle_band_cross_idx = -1
        
        # 浜ゆ槗鐘舵€?        position = 0
        buy_idx = -1
        buy_price = 0
        buy_in_uptrend = False  # 璁板綍涔板叆鏃舵槸鍚﹀湪涓婅鏈?        
        # 绉诲姩姝㈡崯鐘舵€?        highest_price = 0  # 鎸佷粨鏈熼棿鐨勬渶楂樹环鏍?        highest_price_idx = -1  # 鏈€楂樹环鏍肩殑鏃ユ湡绱㈠紩
        
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
            
            # 1. 鍒ゆ柇鏄惁澶勪簬涓婅鏈?            if in_uptrend:
                # 妫€鏌ヤ笂琛屾湡鏄惁缁撴潫
                if current_price < ma_long or ma_short < ma_long:
                    in_uptrend = False
                    uptrend_start_idx = 0
                    # 濡傛灉鍦ㄦ寔浠撲腑锛岃褰曚笂琛屾湡缁撴潫
                    if position == 1:
                        pass  # 涓婅鏈熺粨鏉燂紝浣嗙户缁寔鏈?            else:
                # 妫€鏌ユ槸鍚﹀紑濮嬫柊鐨勪笂琛屾湡
                if i >= self.min_uptrend_days:
                    if current_price > ma_long and ma_short > ma_long:
                        recent_highs = df['High'].iloc[i - self.min_uptrend_days:i + 1]
                        new_high_days = 0
                        for j in range(1, len(recent_highs)):
                            if recent_highs.iloc[j] > recent_highs.iloc[j - 1]:
                                new_high_days += 1
                        
                        new_high_ratio = new_high_days / len(recent_highs)
                        price_change = (current_price - df['Close'].iloc[i - self.min_uptrend_days]) / df['Close'].iloc[i - self.min_uptrend_days]
                        
                        if new_high_ratio >= self.uptrend_threshold and price_change > 0:
                            in_uptrend = True
                            uptrend_start_idx = i - self.min_uptrend_days
                            # 濡傛灉鍦ㄦ寔浠撲腑锛岄噸缃牬涓嬭建璁℃暟锛堝洜涓鸿繘鍏ユ柊鐨勪笂琛屾湡锛?                    # 濡傛灉鍦ㄦ寔浠撲腑锛岄噸缃牬涓嬭建璁℃暟锛堝洜涓鸿繘鍏ユ柊鐨勪笂琛屾湡锛?                    if position == 1:
                        lower_band_breaks = []
            
            # 2. 妫€娴嬬牬涓嬭建
            if current_low <= lower_band:
                if last_lower_band_break_idx == -1 or i - last_lower_band_break_idx >= self.min_interval_days:
                    lower_band_breaks.append(i)
                    last_lower_band_break_idx = i
            
            # 3. 妫€娴嬬┛涓婅建锛堝弽寮瑰己搴︼級
            if position == 0:
                if i > 0:
                    prev_price = df['Close'].iloc[i - 1]
                    prev_upper_band = df['upper_band'].iloc[i - 1]
                    
                    # 鍓嶄竴澶╁湪涓婅建涔嬩笅锛屽綋澶╁湪涓婅建涔嬩笂
                    if prev_price <= prev_upper_band and current_price > upper_band:
                        if last_upper_band_cross_idx == -1 or i - last_upper_band_cross_idx >= self.min_interval_days:
                            upper_band_crosses.append(i)
                            last_upper_band_cross_idx = i
            
            # 4. 妫€娴嬬┛涓建锛堜拱鍏ヤ俊鍙凤級
            if position == 0:
                if i > 0:
                    prev_price = df['Close'].iloc[i - 1]
                    prev_middle_band = df['middle_band'].iloc[i - 1]
                    
                    # 鍓嶄竴澶╁湪涓建涔嬩笅锛屽綋澶╁湪涓建涔嬩笂
                    if prev_price <= prev_middle_band and current_price > middle_band:
                        if last_middle_band_cross_idx == -1 or i - last_middle_band_cross_idx >= self.min_interval_days:
                            middle_band_crosses.append(i)
                            last_middle_band_cross_idx = i
            
            # 5. 涔板叆淇″彿锛氬湪涓嬭鏈燂紝鍑虹幇鑲′环璺岀牬boll涓嬭建锛屼笖闂撮殧2鍛ㄤ互涓婄殑2娆″弽寮归兘娌℃湁涓婄┛boll甯︿笂杞紝
            # 绗笁娆℃垨鑰呬箣鍚庣殑鍙嶅脊绌胯繃涓建鍚庯紝鍥炶惤鍒颁腑杞ㄤ箣涓嬩拱鍏?            if not in_uptrend and position == 0:
                # 妫€鏌ユ槸鍚︽湁瓒冲鐨勭牬涓嬭建娆℃暟锛堣嚦灏?娆″嵆鍙級
                if len(lower_band_breaks) >= 1:
                    # 妫€鏌ユ槸鍚︽湁瓒冲鐨勭┛涓建娆℃暟锛堢3娆℃垨涔嬪悗锛?                    if len(middle_band_crosses) >= 3:
                        # 妫€鏌ュ墠2娆″弽寮规槸鍚﹂兘娌℃湁绌夸笂杞?                        # 绌夸腑杞ㄦ鏁板簲璇ユ瘮绌夸笂杞ㄦ鏁板鑷冲皯2娆?                        if len(middle_band_crosses) >= len(upper_band_crosses) + 2:
                            # 妫€鏌ユ槸鍚︿粠涓婃柟鍚戜笅绌胯繃涓建锛堝洖钀藉埌涓建涔嬩笅锛?                            if i > 0:
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
                                        buy_price = current_price
                                        buy_in_uptrend = in_uptrend
                                        # 鍒濆鍖栫Щ鍔ㄦ鎹熺姸鎬?                                        highest_price = current_price
                                        highest_price_idx = i
                                        # 涔板叆鍚庨噸缃鏁?                                        lower_band_breaks = []
                                        upper_band_crosses = []
                                        middle_band_crosses = []
            
            # 6. 鏇存柊绉诲姩姝㈡崯鐘舵€?            if position == 1:
                # 鏇存柊鏈€楂樹环鏍?                if current_high > highest_price:
                    highest_price = current_high
                    highest_price_idx = i
            
            # 7. 鍗栧嚭淇″彿锛氬湪涓婅鏈燂紝浣跨敤绉诲姩姝㈡崯
            if position == 1:
                # 妫€鏌ユ槸鍚﹀湪涓婅鏈?                if in_uptrend:
                    # 绉诲姩姝㈡崯锛氫环鏍间粠楂樼偣鍥炶惤瓒呰繃trailing_stop_pct
                    stop_loss_price = highest_price * (1 - self.trailing_stop_pct)
                    
                    if current_low <= stop_loss_price:
                        signals.iloc[i] = -1
                        position = 0
                        buy_idx = -1
                        buy_price = 0
                        buy_in_uptrend = False
                        highest_price = 0
                        highest_price_idx = -1
                        lower_band_breaks = []
                else:
                    # 濡傛灉涓嶅湪涓婅鏈燂紝妫€鏌ユ槸鍚﹂渶瑕佹鎹?                    # 姝㈡崯鏉′欢锛氭寔浠撹秴杩?0澶╋紝涓旇穼鐮翠笅杞?                    if i - buy_idx > 10:
                        if current_low <= lower_band:
                            signals.iloc[i] = -1
                            position = 0
                            buy_idx = -1
                            buy_price = 0
                            buy_in_uptrend = False
                            highest_price = 0
                            highest_price_idx = -1
                            lower_band_breaks = []
            
            # 8. 寮哄埗骞充粨锛氬鏋滄寔浠撴椂闂磋繃闀?            if position == 1 and i - buy_idx >= self.max_hold_days:
                signals.iloc[i] = -1
                position = 0
                buy_idx = -1
                buy_price = 0
                buy_in_uptrend = False
                highest_price = 0
                highest_price_idx = -1
                lower_band_breaks = []
        
        df['signal'] = signals
        
        return df
