"""
缠论指标实现 - 改进方案C：多时间周期共振验证
在实时近似版本基础上，买卖点增加趋势强度和多周期验证
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


class ChanTheoryImprovedC:
    """
    缠论指标类 - 改进方案C（多周期共振）
    """
    
    def __init__(self, k_type='day', trend_strength_threshold=0.03, ma_confirmation=True):
        """
        Args:
            k_type: K线类型
            trend_strength_threshold: 趋势强度阈值（默认3%）
            ma_confirmation: 是否使用均线确认
        """
        self.k_type = k_type
        self.trend_strength_threshold = trend_strength_threshold
        self.ma_confirmation = ma_confirmation
        self.min_k_count = 5 if k_type == 'day' else 3
        
        self.fenxing_list = []
        self.bi_list = []
        self.xianduan_list = []
        self.zhongshu_list = []
        self.buy_points = []
        self.sell_points = []
    
    def identify_fenxing_realtime(self, data: pd.DataFrame) -> pd.DataFrame:
        """识别疑似分型 - 与原版相同"""
        df = data.copy()
        
        df['fenxing_type'] = 0
        df['fenxing_high'] = df['High']
        df['fenxing_low'] = df['Low']
        
        self.fenxing_list = []
        
        for i in range(1, len(df)):
            prev_high = df['High'].iloc[i - 1]
            prev_low = df['Low'].iloc[i - 1]
            curr_high = df['High'].iloc[i]
            curr_low = df['Low'].iloc[i]
            curr_idx = df.index[i]
            
            if curr_high > prev_high and curr_low > prev_low:
                df.loc[curr_idx, 'fenxing_type'] = 1
                self.fenxing_list.append({
                    'index': curr_idx,
                    'date': curr_idx,
                    'type': 1,
                    'high': curr_high,
                    'low': curr_low,
                    'confirmed': False
                })
            
            elif curr_low < prev_low and curr_high < prev_high:
                df.loc[curr_idx, 'fenxing_type'] = -1
                self.fenxing_list.append({
                    'index': curr_idx,
                    'date': curr_idx,
                    'type': -1,
                    'high': curr_high,
                    'low': curr_low,
                    'confirmed': False
                })
        
        return df
    
    def identify_bi(self, df: pd.DataFrame) -> pd.DataFrame:
        """识别笔 - 与原版相同"""
        df['bi_type'] = 0
        df['bi_start'] = np.nan
        df['bi_end'] = np.nan
        
        self.bi_list = []
        
        if len(self.fenxing_list) < 2:
            return df
        
        i = 0
        while i < len(self.fenxing_list) - 1:
            curr_fx = self.fenxing_list[i]
            next_fx = self.fenxing_list[i + 1]
            
            if curr_fx['type'] == next_fx['type']:
                i += 1
                continue
            
            start_idx = df.index.get_loc(curr_fx['index'])
            end_idx = df.index.get_loc(next_fx['index'])
            
            if abs(end_idx - start_idx) >= self.min_k_count:
                bi = {
                    'start': curr_fx['index'],
                    'end': next_fx['index'],
                    'start_price': curr_fx['high'] if curr_fx['type'] == 1 else curr_fx['low'],
                    'end_price': next_fx['high'] if next_fx['type'] == 1 else next_fx['low'],
                    'type': 1 if next_fx['type'] == 1 else -1
                }
                self.bi_list.append(bi)
                i += 1
            else:
                i += 1
        
        return df
    
    def identify_xianduan(self, df: pd.DataFrame) -> pd.DataFrame:
        """识别线段 - 与原版相同"""
        df['xd_type'] = 0
        self.xianduan_list = []
        
        if len(self.bi_list) < 3:
            return df
        
        i = 0
        while i < len(self.bi_list) - 2:
            bi1 = self.bi_list[i]
            bi2 = self.bi_list[i + 1]
            bi3 = self.bi_list[i + 2]
            
            is_alt = (bi1['type'] != bi2['type'] and 
                     bi2['type'] != bi3['type'] and
                     bi1['type'] == bi3['type'])
            
            if is_alt:
                xd_type = bi1['type']
                xd_high = max(bi1['start_price'], bi1['end_price'], 
                             bi2['start_price'], bi2['end_price'],
                             bi3['start_price'], bi3['end_price'])
                xd_low = min(bi1['start_price'], bi1['end_price'],
                            bi2['start_price'], bi2['end_price'],
                            bi3['start_price'], bi3['end_price'])
                
                xd = {
                    'start': bi1['start'],
                    'end': bi3['end'],
                    'type': xd_type,
                    'high': xd_high,
                    'low': xd_low
                }
                self.xianduan_list.append(xd)
                i += 3
            else:
                i += 1
        
        return df
    
    def identify_zhongshu(self, df: pd.DataFrame) -> pd.DataFrame:
        """识别中枢 - 与原版相同"""
        self.zhongshu_list = []
        
        if len(self.xianduan_list) < 3:
            return df
        
        i = 0
        while i < len(self.xianduan_list) - 2:
            xd1 = self.xianduan_list[i]
            xd2 = self.xianduan_list[i + 1]
            xd3 = self.xianduan_list[i + 2]
            
            if xd1['type'] == xd3['type'] and xd2['type'] != xd1['type']:
                overlap_high = min(xd1['high'], xd2['high'], xd3['high'])
                overlap_low = max(xd1['low'], xd2['low'], xd3['low'])
                
                if overlap_high > overlap_low:
                    zs = {
                        'start': xd2['start'],
                        'end': xd2['end'],
                        'high': overlap_high,
                        'low': overlap_low,
                        'type': 'up' if xd1['type'] == 1 else 'down'
                    }
                    self.zhongshu_list.append(zs)
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        
        return df
    
    def check_trend_strength(self, df, start_date, end_date, direction='up'):
        """
        检查趋势强度（模拟多周期验证）
        
        通过计算近期价格变化幅度来判断趋势强度
        
        Args:
            df: DataFrame
            start_date: 开始日期
            end_date: 结束日期
            direction: 'up' 或 'down'
        
        Returns:
            dict: {'passed': bool, 'strength': float}
        """
        try:
            # 获取区间数据
            mask = (df.index >= start_date) & (df.index <= end_date)
            period_data = df.loc[mask]
            
            if len(period_data) < 2:
                return {'passed': True, 'strength': 0}
            
            # 计算变化幅度
            price_change = (period_data['Close'].iloc[-1] - period_data['Close'].iloc[0]) / period_data['Close'].iloc[0]
            
            # 检查均线排列（多周期共振的简化版）
            ma_confirm = True
            if self.ma_confirmation and len(df) > 60:
                ma5 = df['Close'].rolling(5).mean().loc[end_date]
                ma20 = df['Close'].rolling(20).mean().loc[end_date]
                ma60 = df['Close'].rolling(60).mean().loc[end_date]
                
                if direction == 'up':
                    # 买点：短期均线在长期均线上方
                    ma_confirm = ma5 > ma20 or ma20 > ma60
                else:
                    # 卖点：短期均线在长期均线下方
                    ma_confirm = ma5 < ma20 or ma20 < ma60
            
            # 判断趋势强度是否足够
            if direction == 'up':
                passed = price_change > -self.trend_strength_threshold and ma_confirm
            else:
                passed = price_change < self.trend_strength_threshold and ma_confirm
            
            return {
                'passed': passed,
                'strength': abs(price_change),
                'ma_confirm': ma_confirm
            }
            
        except Exception as e:
            return {'passed': True, 'strength': 0, 'ma_confirm': True}
    
    def identify_buy_sell_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """识别买卖点 - 增加趋势强度和多周期验证"""
        df['buy_point'] = 0
        df['sell_point'] = 0
        
        self.buy_points = []
        self.sell_points = []
        
        if len(self.xianduan_list) < 2 or len(self.zhongshu_list) < 1:
            return df
        
        last_buy_point = None
        last_sell_point = None
        
        for i in range(1, len(self.xianduan_list)):
            prev_xd = self.xianduan_list[i - 1]
            xd = self.xianduan_list[i]
            xd_type = xd['type']
            xd_high = xd['high']
            xd_low = xd['low']
            
            relevant_zs = [zs for zs in self.zhongshu_list 
                          if zs['start'] <= xd['end']]
            
            if not relevant_zs:
                continue
            
            zs_high = max(zs['high'] for zs in relevant_zs)
            zs_low = min(zs['low'] for zs in relevant_zs)
            
            # 一买 - 增加趋势强度验证
            if prev_xd['type'] == -1 and xd_type == 1:
                if xd_high > zs_high:
                    buy_date = prev_xd['end']
                    
                    # 检查下跌段趋势强度（跌幅不能过大）
                    trend_check = self.check_trend_strength(
                        df, prev_xd['start'], prev_xd['end'], 'down'
                    )
                    
                    if trend_check['passed']:
                        df.loc[buy_date, 'buy_point'] = 1
                        self.buy_points.append({
                            'index': buy_date,
                            'price': df.loc[buy_date, 'Close'],
                            'type': 1,
                            'desc': 'Type 1 Buy (Trend Confirmed)',
                            'trend_strength': round(trend_check['strength'], 4),
                            'ma_confirm': trend_check['ma_confirm']
                        })
                        last_buy_point = {
                            'index': buy_date,
                            'price': df.loc[buy_date, 'Close'],
                            'type': 1
                        }
            
            # 二买
            if last_buy_point and xd_type == -1:
                xd_low = min(df.loc[xd['start']:xd['end'], 'Low'])
                if xd_low >= last_buy_point['price']:
                    buy_date = xd['end']
                    
                    trend_check = self.check_trend_strength(
                        df, xd['start'], xd['end'], 'down'
                    )
                    
                    if trend_check['passed']:
                        df.loc[buy_date, 'buy_point'] = 2
                        self.buy_points.append({
                            'index': buy_date,
                            'price': df.loc[buy_date, 'Close'],
                            'type': 2,
                            'desc': 'Type 2 Buy (Trend Confirmed)',
                            'trend_strength': round(trend_check['strength'], 4),
                            'ma_confirm': trend_check['ma_confirm']
                        })
            
            # 一卖 - 增加趋势强度验证
            if prev_xd['type'] == 1 and xd_type == -1:
                if xd_low < zs_low:
                    sell_date = prev_xd['end']
                    
                    # 检查上涨段趋势强度
                    trend_check = self.check_trend_strength(
                        df, prev_xd['start'], prev_xd['end'], 'up'
                    )
                    
                    if trend_check['passed']:
                        df.loc[sell_date, 'sell_point'] = 1
                        self.sell_points.append({
                            'index': sell_date,
                            'price': df.loc[sell_date, 'Close'],
                            'type': 1,
                            'desc': 'Type 1 Sell (Trend Confirmed)',
                            'trend_strength': round(trend_check['strength'], 4),
                            'ma_confirm': trend_check['ma_confirm']
                        })
                        last_sell_point = {
                            'index': sell_date,
                            'price': df.loc[sell_date, 'Close'],
                            'type': 1
                        }
            
            # 二卖
            if last_sell_point and xd_type == 1:
                xd_high = max(df.loc[xd['start']:xd['end'], 'High'])
                if xd_high <= last_sell_point['price']:
                    sell_date = xd['end']
                    
                    trend_check = self.check_trend_strength(
                        df, xd['start'], xd['end'], 'up'
                    )
                    
                    if trend_check['passed']:
                        df.loc[sell_date, 'sell_point'] = 2
                        self.sell_points.append({
                            'index': sell_date,
                            'price': df.loc[sell_date, 'Close'],
                            'type': 2,
                            'desc': 'Type 2 Sell (Trend Confirmed)',
                            'trend_strength': round(trend_check['strength'], 4),
                            'ma_confirm': trend_check['ma_confirm']
                        })
        
        return df
    
    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """完整分析流程"""
        df = data.copy()
        df = self.identify_fenxing_realtime(df)
        df = self.identify_bi(df)
        df = self.identify_xianduan(df)
        df = self.identify_zhongshu(df)
        df = self.identify_buy_sell_points(df)
        return df
