"""
修正后的适中布林带策略 V6（周K版本）
基于以下规则：
1. 上行期是不断创新高，能持续一个月以上的创新高
2. 买入时机是在下行期，出现股价跌破boll下轨，且间隔2周以上的2次反弹都没有上穿boll带上轨，
   第三次或者之后的反弹穿过中轨后，回落到中轨之下买入
3. 卖出是在上行期，股价超过布林带中线的50%时卖出（价格 > 中线 * 1.5）
"""
import pandas as pd
import numpy as np
from backtest_engine import BaseStrategy

class ModerateBollStrategyV6(BaseStrategy):
    """修正后的适中布林带策略 V6（周K版本）"""
    
    def __init__(self, period=20, std_dev=2, min_uptrend_days=20, min_interval_days=10, 
                 ma_period=60, uptrend_threshold=0.5, max_hold_days=120, sell_threshold=1.5):
        """
        初始化策略
        
        Args:
            period: 布林带周期
            std_dev: 标准差倍数
            min_uptrend_days: 最小上行期天数（一个月约20个交易日）
            min_interval_days: 最小间隔天数（2周约10个交易日）
            ma_period: 用于判断趋势的移动平均线周期
            uptrend_threshold: 上行期判断阈值（0-1之间，越高越严格）
            max_hold_days: 最大持仓天数（如果超过这个天数仍未卖出，强制卖出）
            sell_threshold: 卖出阈值（价格超过中线的倍数，默认1.5即50%）
        """
        super().__init__("ModerateBollStrategyV6")
        self.period = period
        self.std_dev = std_dev
        self.min_uptrend_days = min_uptrend_days
        self.min_interval_days = min_interval_days
        self.ma_period = ma_period
        self.uptrend_threshold = uptrend_threshold
        self.max_hold_days = max_hold_days
        self.sell_threshold = sell_threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 包含OHLCV数据的DataFrame
        
        Returns:
            添加了信号列的DataFrame
        """
        df = data.copy()
        
        # 计算布林带
        df['middle_band'] = df['Close'].rolling(window=self.period).mean()
        df['std'] = df['Close'].rolling(window=self.period).std()
        df['upper_band'] = df['middle_band'] + self.std_dev * df['std']
        df['lower_band'] = df['middle_band'] - self.std_dev * df['std']
        
        # 计算移动平均线用于判断趋势
        df['ma_long'] = df['Close'].rolling(window=self.ma_period).mean()
        df['ma_short'] = df['Close'].rolling(window=self.period).mean()
        
        # 初始化状态变量
        signals = pd.Series(0, index=df.index)
        
        # 状态变量
        in_uptrend = False
        uptrend_start_idx = 0
        
        # 破下轨相关状态
        lower_band_breaks = []  # 记录破下轨的日期
        last_lower_band_break_idx = -1
        
        # 反弹相关状态
        upper_band_crosses = []  # 记录穿上轨的日期（反弹强度）
        middle_band_crosses = []  # 记录穿中轨的日期（买入信号）
        last_upper_band_cross_idx = -1
        last_middle_band_cross_idx = -1
        
        # 交易状态
        position = 0
        buy_idx = -1
        buy_price = 0
        buy_in_uptrend = False  # 记录买入时是否在上行期
        
        # 遍历每个交易日
        for i in range(len(df)):
            current_price = df['Close'].iloc[i]
            current_high = df['High'].iloc[i]
            current_low = df['Low'].iloc[i]
            middle_band = df['middle_band'].iloc[i]
            upper_band = df['upper_band'].iloc[i]
            lower_band = df['lower_band'].iloc[i]
            ma_long = df['ma_long'].iloc[i]
            ma_short = df['ma_short'].iloc[i]
            
            # 检查是否有足够的数据
            if pd.isna(middle_band) or pd.isna(upper_band) or pd.isna(lower_band) or pd.isna(ma_long):
                continue
            
            # 1. 判断是否处于上行期
            if in_uptrend:
                # 检查上行期是否结束
                if current_price < ma_long or ma_short < ma_long:
                    in_uptrend = False
                    uptrend_start_idx = 0
                    # 如果在持仓中，记录上行期结束
                    if position == 1:
                        pass  # 上行期结束，但继续持有
            else:
                # 检查是否开始新的上行期
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
                            # 如果在持仓中，重置破下轨计数（因为进入新的上行期）
                    # 如果在持仓中，重置破下轨计数（因为进入新的上行期）
                    if position == 1:
                        lower_band_breaks = []
            
            # 2. 检测破下轨
            if current_low <= lower_band:
                if last_lower_band_break_idx == -1 or i - last_lower_band_break_idx >= self.min_interval_days:
                    lower_band_breaks.append(i)
                    last_lower_band_break_idx = i
            
            # 3. 检测穿上轨（反弹强度）
            if position == 0:
                if i > 0:
                    prev_price = df['Close'].iloc[i - 1]
                    prev_upper_band = df['upper_band'].iloc[i - 1]
                    
                    # 前一天在上轨之下，当天在上轨之上
                    if prev_price <= prev_upper_band and current_price > upper_band:
                        if last_upper_band_cross_idx == -1 or i - last_upper_band_cross_idx >= self.min_interval_days:
                            upper_band_crosses.append(i)
                            last_upper_band_cross_idx = i
            
            # 4. 检测穿中轨（买入信号）
            if position == 0:
                if i > 0:
                    prev_price = df['Close'].iloc[i - 1]
                    prev_middle_band = df['middle_band'].iloc[i - 1]
                    
                    # 前一天在中轨之下，当天在中轨之上
                    if prev_price <= prev_middle_band and current_price > middle_band:
                        if last_middle_band_cross_idx == -1 or i - last_middle_band_cross_idx >= self.min_interval_days:
                            middle_band_crosses.append(i)
                            last_middle_band_cross_idx = i
            
            # 5. 买入信号：在下行期，出现股价跌破boll下轨，且间隔2周以上的2次反弹都没有上穿boll带上轨，
            # 第三次或者之后的反弹穿过中轨后，回落到中轨之下买入
            if not in_uptrend and position == 0:
                # 检查是否有足够的破下轨次数（至少1次即可）
                if len(lower_band_breaks) >= 1:
                    # 检查是否有足够的穿中轨次数（第3次或之后）
                    if len(middle_band_crosses) >= 3:
                        # 检查前2次反弹是否都没有穿上轨
                        # 穿中轨次数应该比穿上轨次数多至少2次
                        if len(middle_band_crosses) >= len(upper_band_crosses) + 2:
                            # 检查是否从上方向下穿过中轨（回落到中轨之下）
                            if i > 0:
                                prev_price = df['Close'].iloc[i - 1]
                                prev_middle_band = df['middle_band'].iloc[i - 1]
                                
                                # 前一天在中轨之上，当天在中轨之下
                                if prev_price > prev_middle_band and current_price <= middle_band:
                                    # 检查是否是第三次或之后的穿中轨后的回落
                                    last_cross_idx = middle_band_crosses[-1]
                                    if last_cross_idx < i and i - last_cross_idx <= self.min_interval_days:
                                        signals.iloc[i] = 1
                                        position = 1
                                        buy_idx = i
                                        buy_price = current_price
                                        buy_in_uptrend = in_uptrend
                                        # 买入后重置计数
                                        lower_band_breaks = []
                                        upper_band_crosses = []
                                        middle_band_crosses = []
            
            # 6. 卖出信号：在上行期，股价超过布林带中线的50%时卖出（价格 > 中线 * 1.5）
            if position == 1:
                # 检查是否在上行期
                if in_uptrend:
                    # 检查是否超过布林带中线的50%
                    sell_price_threshold = middle_band * self.sell_threshold
                    
                    if current_high >= sell_price_threshold:
                        signals.iloc[i] = -1
                        position = 0
                        buy_idx = -1
                        buy_price = 0
                        buy_in_uptrend = False
                        lower_band_breaks = []
                else:
                    # 如果不在上行期，检查是否需要止损
                    # 止损条件：持仓超过10天，且跌破下轨
                    if i - buy_idx > 10:
                        if current_low <= lower_band:
                            signals.iloc[i] = -1
                            position = 0
                            buy_idx = -1
                            buy_price = 0
                            buy_in_uptrend = False
                            lower_band_breaks = []
            
            # 7. 强制平仓：如果持仓时间过长
            if position == 1 and i - buy_idx >= self.max_hold_days:
                signals.iloc[i] = -1
                position = 0
                buy_idx = -1
                buy_price = 0
                buy_in_uptrend = False
                lower_band_breaks = []
        
        df['signal'] = signals
        
        return df