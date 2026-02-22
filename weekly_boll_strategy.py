import pandas as pd
import numpy as np
from backtest_engine import BaseStrategy


class WeeklyBollingerStrategy(BaseStrategy):
    """周布林带策略"""
    
    def __init__(self, period: int = 20, std_dev: float = 2, middle_threshold: float = 0.05):
        """
        初始化周布林带策略
        
        Args:
            period: 布林带周期（周数）
            std_dev: 标准差倍数
            middle_threshold: 中线附近的阈值（百分比）
        """
        super().__init__(name=f"WeeklyBoll{period}")
        self.period = period
        self.std_dev = std_dev
        self.middle_threshold = middle_threshold
    
    def _resample_to_weekly(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        将日线数据转换为周线数据
        
        Args:
            data: 日线数据
        
        Returns:
            周线数据
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
        生成交易信号
        
        策略逻辑：
        - 上行期：周K收盘价不跌破布林带下轨
        - 下跌期：周K收盘价跌破布林带下轨
        
        买入条件：
        1. 市场之前处于下跌期
        2. 周K收盘价靠近boll带中轨5%内时买入
        
        卖出条件：
        - 在上行期中，周K3次跌破中线后，再次上涨第一次超过上轨时卖出
        
        仓位管理：
        - 买入时一次性全部买入，买入后不再买入
        - 卖出时一次性全部卖出，不做空，只做多
        
        Args:
            data: 包含OHLCV数据的DataFrame（日线数据）
        
        Returns:
            添加了信号列的DataFrame（日线数据）
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
                weekly_df.loc[weekly_df.index[i], 'phase'] = '初始化'
                weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
                weekly_df.loc[weekly_df.index[i], 'market_phase'] = '初始化'
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
                weekly_df.loc[weekly_df.index[i], 'market_phase'] = '上行期'
            else:
                weekly_df.loc[weekly_df.index[i], 'market_phase'] = '下跌期'
            
            if prev_market_phase == '下跌期' and current_close >= current_lower:
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = True
            elif prev_recovered:
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
            else:
                weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
            
            if prev_signal == 0:
                weekly_df.loc[weekly_df.index[i], 'signal'] = 0
                weekly_df.loc[weekly_df.index[i], 'phase'] = '空仓'
                weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
                
                middle_distance = abs(current_close - current_middle) / current_middle
                
                if prev_recovered and middle_distance <= self.middle_threshold:
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = True
                    weekly_df.loc[weekly_df.index[i], 'signal'] = 1
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '买入'
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
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '持有'
                    weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
                    
                    if new_below_count >= 3:
                        weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = True
                        weekly_df.loc[weekly_df.index[i], 'phase'] = '准备卖出'
                    else:
                        weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                elif current_close > current_upper and prev_ready_to_sell:
                    weekly_df.loc[weekly_df.index[i], 'signal'] = -1
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '卖出'
                    weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = 0
                    weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = False
                    weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
                else:
                    weekly_df.loc[weekly_df.index[i], 'signal'] = 1
                    weekly_df.loc[weekly_df.index[i], 'phase'] = '持有'
                    weekly_df.loc[weekly_df.index[i], 'below_middle_count'] = prev_below_count
                    weekly_df.loc[weekly_df.index[i], 'ready_to_sell'] = prev_ready_to_sell
                    weekly_df.loc[weekly_df.index[i], 'recovered_from_down'] = False
                    weekly_df.loc[weekly_df.index[i], 'touched_middle_nearby'] = False
            
            elif prev_signal == -1:
                weekly_df.loc[weekly_df.index[i], 'signal'] = 0
                weekly_df.loc[weekly_df.index[i], 'phase'] = '空仓'
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
                df.loc[df.index[i], 'phase'] = '初始化'
                df.loc[df.index[i], 'market_phase'] = '初始化'
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
                
                # 获取该周的最后一个交易日
                week_trading_days = df[(df.index >= week_start) & (df.index <= week_end)]
                if len(week_trading_days) > 0:
                    last_trading_day = week_trading_days.index[-1]
                    if current_date == last_trading_day:
                        # 是该周的最后一个交易日，使用周线信号和阶段
                        df.loc[df.index[i], 'signal'] = week_signal
                        df.loc[df.index[i], 'phase'] = week_phase
                    else:
                        # 不是该周的最后一个交易日，保持之前的信号和阶段
                        if i > 0:
                            prev_signal = df['signal'].iloc[i-1]
                            # 如果之前的信号是卖出信号，则重置为空仓
                            if prev_signal == -1:
                                df.loc[df.index[i], 'signal'] = 0
                                df.loc[df.index[i], 'phase'] = '空仓'
                            else:
                                df.loc[df.index[i], 'signal'] = prev_signal
                                df.loc[df.index[i], 'phase'] = df['phase'].iloc[i-1]
                        else:
                            df.loc[df.index[i], 'signal'] = 0
                            df.loc[df.index[i], 'phase'] = '空仓'
                else:
                    # 该周没有交易日，保持之前的信号和阶段
                    if i > 0:
                        prev_signal = df['signal'].iloc[i-1]
                        # 如果之前的信号是卖出信号，则重置为空仓
                        if prev_signal == -1:
                            df.loc[df.index[i], 'signal'] = 0
                            df.loc[df.index[i], 'phase'] = '空仓'
                        else:
                            df.loc[df.index[i], 'signal'] = prev_signal
                            df.loc[df.index[i], 'phase'] = df['phase'].iloc[i-1]
                    else:
                        df.loc[df.index[i], 'signal'] = 0
                        df.loc[df.index[i], 'phase'] = '空仓'
                
                df.loc[df.index[i], 'market_phase'] = week_market_phase
                df.loc[df.index[i], 'below_middle_count'] = week_below_count
                df.loc[df.index[i], 'ready_to_buy'] = week_ready_to_buy
                df.loc[df.index[i], 'ready_to_sell'] = week_ready_to_sell
                df.loc[df.index[i], 'recovered_from_down'] = week_recovered
                df.loc[df.index[i], 'touched_middle_nearby'] = week_touched_middle
            else:
                df.loc[df.index[i], 'signal'] = 0
                df.loc[df.index[i], 'phase'] = '空仓'
                df.loc[df.index[i], 'market_phase'] = '上行期'
                df.loc[df.index[i], 'below_middle_count'] = 0
                df.loc[df.index[i], 'ready_to_buy'] = False
                df.loc[df.index[i], 'ready_to_sell'] = False
                df.loc[df.index[i], 'recovered_from_down'] = False
                df.loc[df.index[i], 'touched_middle_nearby'] = False
        
        return df
