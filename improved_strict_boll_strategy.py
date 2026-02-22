"""
改进的严格布林带策略
使用更现实的上行期定义
"""
import pandas as pd
import numpy as np
from backtest_engine import BaseStrategy

class ImprovedStrictBollStrategy(BaseStrategy):
    """改进的严格布林带策略 - 使用更现实的上行期定义"""
    
    def __init__(self, period=20, std_dev=2, min_uptrend_days=20, min_interval_days=10, 
                 ma_period=60, uptrend_threshold=0.5):
        """
        初始化策略
        
        Args:
            period: 布林带周期
            std_dev: 标准差倍数
            min_uptrend_days: 最小上行期天数（一个月约20个交易日）
            min_interval_days: 最小间隔天数（2周约10个交易日）
            ma_period: 用于判断趋势的移动平均线周期
            uptrend_threshold: 上行期判断阈值（0-1之间，越高越严格）
        """
        super().__init__("ImprovedStrictBollStrategy")
        self.period = period
        self.std_dev = std_dev
        self.min_uptrend_days = min_uptrend_days
        self.min_interval_days = min_interval_days
        self.ma_period = ma_period
        self.uptrend_threshold = uptrend_threshold
    
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
        middle_band_crosses = []  # 记录穿中轨的日期
        last_middle_band_cross_idx = -1
        
        # 交易状态
        position = 0
        buy_idx = -1
        
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
            
            # 1. 判断是否处于上行期（改进版）
            # 上行期定义：
            # - 价格在长期移动平均线之上
            # - 短期移动平均线在长期移动平均线之上
            # - 过去一段时间内，创新高的天数占比超过阈值
            # - 价格近期有上升趋势
            
            if in_uptrend:
                # 检查上行期是否结束
                # 条件：价格跌破长期均线，或短期均线跌破长期均线
                if current_price < ma_long or ma_short < ma_long:
                    in_uptrend = False
                    uptrend_start_idx = 0
                    lower_band_breaks = []
                    middle_band_crosses = []
            else:
                # 检查是否开始新的上行期
                # 条件：
                # 1. 价格在长期均线之上
                # 2. 短期均线在长期均线之上
                # 3. 过去min_uptrend_days天内，创新高的天数占比超过阈值
                # 4. 价格近期有上升趋势
                
                if i >= self.min_uptrend_days:
                    # 条件1和2
                    if current_price > ma_long and ma_short > ma_long:
                        # 条件3：检查创新高的天数占比
                        recent_highs = df['High'].iloc[i - self.min_uptrend_days:i + 1]
                        new_high_days = 0
                        for j in range(1, len(recent_highs)):
                            if recent_highs.iloc[j] > recent_highs.iloc[j - 1]:
                                new_high_days += 1
                        
                        new_high_ratio = new_high_days / len(recent_highs)
                        
                        # 条件4：检查价格上升趋势
                        price_change = (current_price - df['Close'].iloc[i - self.min_uptrend_days]) / df['Close'].iloc[i - self.min_uptrend_days]
                        
                        # 综合判断
                        if new_high_ratio >= self.uptrend_threshold and price_change > 0:
                            in_uptrend = True
                            uptrend_start_idx = i - self.min_uptrend_days
                            lower_band_breaks = []
                            middle_band_crosses = []
            
            # 2. 检测破下轨
            if in_uptrend and current_low <= lower_band:
                # 检查是否距离上次破下轨已经超过最小间隔
                if last_lower_band_break_idx == -1 or i - last_lower_band_break_idx >= self.min_interval_days:
                    lower_band_breaks.append(i)
                    last_lower_band_break_idx = i
            
            # 3. 检测穿中轨
            if in_uptrend and position == 0:
                # 检查是否从下方向上穿过中轨
                if i > 0:
                    prev_price = df['Close'].iloc[i - 1]
                    prev_middle_band = df['middle_band'].iloc[i - 1]
                    
                    # 前一天在中轨之下，当天在中轨之上
                    if prev_price <= prev_middle_band and current_price > middle_band:
                        # 检查是否距离上次穿中轨已经超过最小间隔
                        if last_middle_band_cross_idx == -1 or i - last_middle_band_cross_idx >= self.min_interval_days:
                            middle_band_crosses.append(i)
                            last_middle_band_cross_idx = i
            
            # 4. 买入信号：在上行期，出现股价跌破boll下轨，且间隔2周以上的两次反弹都没有上穿boll带中轨，
            # 第三次或者之后的反弹穿过中轨后，回落到中轨之下买入
            if in_uptrend and position == 0:
                # 检查是否有足够的破下轨次数
                if len(lower_band_breaks) >= 2:
                    # 检查是否有足够的穿中轨次数
                    if len(middle_band_crosses) >= 3:
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
            
            # 5. 卖出信号：在上行期出现股价间隔2周以上2次跌破boll下轨后，继续上涨到boll带上轨时卖出
            if in_uptrend and position == 1:
                # 检查是否有足够的破下轨次数（买入后）
                post_buy_breaks = [b for b in lower_band_breaks if b > buy_idx]
                
                if len(post_buy_breaks) >= 2:
                    # 检查是否到达上轨
                    if current_high >= upper_band:
                        signals.iloc[i] = -1
                        position = 0
                        buy_idx = -1
            
            # 6. 止损：如果跌破下轨且不在买入信号附近，止损
            if position == 1 and i > buy_idx + 5:
                if current_low <= lower_band:
                    signals.iloc[i] = -1
                    position = 0
                    buy_idx = -1
        
        df['signal'] = signals
        
        return df