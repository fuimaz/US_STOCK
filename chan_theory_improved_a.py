"""
缠论指标实现 - 改进方案A：波动率过滤
在实时近似版本基础上，增加波动率过滤条件
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


class ChanTheoryImprovedA:
    """
    缠论指标类 - 改进方案A（波动率过滤）
    """
    
    def __init__(self, k_type='day', volatility_threshold=1.5):
        """
        Args:
            k_type: K线类型
            volatility_threshold: 波动率阈值（默认1.5倍平均波动）
        """
        self.k_type = k_type
        self.volatility_threshold = volatility_threshold
        self.min_k_count = 5 if k_type == 'day' else 3
        
        self.fenxing_list = []
        self.bi_list = []
        self.xianduan_list = []
        self.zhongshu_list = []
        self.buy_points = []
        self.sell_points = []
    
    def identify_fenxing_realtime(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        改进的疑似分型识别 - 增加波动率过滤
        """
        df = data.copy()
        
        # 计算平均波动率（前20根K线）
        df['range'] = df['High'] - df['Low']
        df['avg_range'] = df['range'].rolling(window=20, min_periods=5).mean()
        
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
            curr_range = df['range'].iloc[i]
            avg_range = df['avg_range'].iloc[i]
            
            # 疑似顶分型：当前高于前一根 + 波动率足够
            if (curr_high > prev_high and 
                curr_low > prev_low and 
                curr_range >= avg_range * self.volatility_threshold):
                
                df.loc[curr_idx, 'fenxing_type'] = 1
                self.fenxing_list.append({
                    'index': curr_idx,
                    'date': curr_idx,
                    'type': 1,
                    'high': curr_high,
                    'low': curr_low,
                    'confirmed': False,
                    'volatility_ratio': curr_range / avg_range if avg_range > 0 else 0
                })
            
            # 疑似底分型：当前低于前一根 + 波动率足够
            elif (curr_low < prev_low and 
                  curr_high < prev_high and 
                  curr_range >= avg_range * self.volatility_threshold):
                
                df.loc[curr_idx, 'fenxing_type'] = -1
                self.fenxing_list.append({
                    'index': curr_idx,
                    'date': curr_idx,
                    'type': -1,
                    'high': curr_high,
                    'low': curr_low,
                    'confirmed': False,
                    'volatility_ratio': curr_range / avg_range if avg_range > 0 else 0
                })
        
        return df
    
    def identify_bi(self, df: pd.DataFrame) -> pd.DataFrame:
        """识别笔 - 连接相邻的顶底分型"""
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
            
            # 检查K线数量
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
        """识别线段"""
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
        """识别中枢"""
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
    
    def identify_buy_sell_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """识别买卖点"""
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
            
            # 一买
            if prev_xd['type'] == -1 and xd_type == 1:
                if xd_high > zs_high:
                    buy_date = prev_xd['end']
                    df.loc[buy_date, 'buy_point'] = 1
                    self.buy_points.append({
                        'index': buy_date,
                        'price': df.loc[buy_date, 'Close'],
                        'type': 1,
                        'desc': 'Type 1 Buy'
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
                    df.loc[buy_date, 'buy_point'] = 2
                    self.buy_points.append({
                        'index': buy_date,
                        'price': df.loc[buy_date, 'Close'],
                        'type': 2,
                        'desc': 'Type 2 Buy'
                    })
            
            # 一卖
            if prev_xd['type'] == 1 and xd_type == -1:
                if xd_low < zs_low:
                    sell_date = prev_xd['end']
                    df.loc[sell_date, 'sell_point'] = 1
                    self.sell_points.append({
                        'index': sell_date,
                        'price': df.loc[sell_date, 'Close'],
                        'type': 1,
                        'desc': 'Type 1 Sell'
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
                    df.loc[sell_date, 'sell_point'] = 2
                    self.sell_points.append({
                        'index': sell_date,
                        'price': df.loc[sell_date, 'Close'],
                        'type': 2,
                        'desc': 'Type 2 Sell'
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
