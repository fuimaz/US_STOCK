"""
缠论指标实现 - 延迟确认版本（修复未来函数）

关键修改：
1. 分型确认需要后续K线，因此将买卖点标记向后延迟
2. 顶分型确认：需要后续1根K线确认高点
3. 底分型确认：需要后续1根K线确认低点
4. 买卖点日期 = 实际触发日期 + 延迟天数
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


class ChanTheoryDelayed:
    """
    缠论指标类 - 延迟确认版本
    """
    
    def __init__(self, k_type='day', delay_days=1):
        """
        初始化缠论指标
        
        Args:
            k_type: K线类型，'day'表示日K，'week'表示周K
            delay_days: 确认延迟天数（默认1天，用于修复未来函数）
        """
        self.k_type = k_type
        self.delay_days = delay_days
        self.min_k_count = 5 if k_type == 'day' else 3
        
        # 存储识别结果
        self.fenxing_list = []
        self.bi_list = []
        self.xianduan_list = []
        self.zhongshu_list = []
        self.buy_points = []
        self.sell_points = []
    
    def process_inclusion(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理K线包含关系（与原版相同）"""
        df = data.copy()
        n = len(df)
        if n < 2:
            return df
        
        processed_high = df['High'].values.copy()
        processed_low = df['Low'].values.copy()
        
        i = 1
        direction = 0
        
        while i < len(processed_high):
            prev_high = processed_high[i - 1]
            prev_low = processed_low[i - 1]
            curr_high = processed_high[i]
            curr_low = processed_low[i]
            
            if (curr_high >= prev_high and curr_low <= prev_low) or \
               (curr_high <= prev_high and curr_low >= prev_low):
                if direction == 0:
                    for j in range(1, i):
                        if processed_high[j] > processed_high[j - 1]:
                            direction = 1
                            break
                        elif processed_high[j] < processed_high[j - 1]:
                            direction = -1
                            break
                    if direction == 0:
                        direction = 1 if curr_high > prev_high else -1
                
                if direction == 1:
                    new_high = max(prev_high, curr_high)
                    new_low = max(prev_low, curr_low)
                else:
                    new_high = min(prev_high, curr_high)
                    new_low = min(prev_low, curr_low)
                
                processed_high[i] = new_high
                processed_low[i] = new_low
                processed_high[i - 1] = np.nan
                processed_low[i - 1] = np.nan
                
                if i >= 2 and not np.isnan(processed_high[i - 2]):
                    if processed_high[i] > processed_high[i - 2]:
                        direction = 1
                    elif processed_high[i] < processed_high[i - 2]:
                        direction = -1
            else:
                if curr_high > prev_high:
                    direction = 1
                elif curr_high < prev_high:
                    direction = -1
                i += 1
        
        df['processed_high'] = processed_high
        df['processed_low'] = processed_low
        df['processed'] = ~df['processed_high'].isna()
        
        self.processed_df = df[df['processed']].copy()
        
        return df
    
    def identify_fenxing(self, data: pd.DataFrame) -> pd.DataFrame:
        """识别分型 - 延迟确认"""
        df = data.copy()
        df = self.process_inclusion(df)
        
        if len(self.processed_df) < 3:
            df['fenxing_type'] = 0
            return df
        
        proc_df = self.processed_df.reset_index()
        idx_col = proc_df.columns[0]
        
        df['fenxing_type'] = 0
        self.fenxing_list = []
        
        # 遍历处理后的K线识别分型
        for i in range(1, len(proc_df) - 1):
            prev_high = proc_df['processed_high'].iloc[i - 1]
            prev_low = proc_df['processed_low'].iloc[i - 1]
            curr_high = proc_df['processed_high'].iloc[i]
            curr_low = proc_df['processed_low'].iloc[i]
            next_high = proc_df['processed_high'].iloc[i + 1]
            next_low = proc_df['processed_low'].iloc[i + 1]
            curr_idx = proc_df[idx_col].iloc[i]
            
            # 顶分型
            if curr_high > prev_high and curr_high > next_high and \
               curr_low > prev_low and curr_low > next_low:
                df.loc[curr_idx, 'fenxing_type'] = 1
                self.fenxing_list.append({
                    'index': curr_idx,
                    'date': curr_idx,
                    'type': 1,
                    'high': curr_high,
                    'low': curr_low
                })
            
            # 底分型
            elif curr_low < prev_low and curr_low < next_low and \
                 curr_high < prev_high and curr_high < next_high:
                df.loc[curr_idx, 'fenxing_type'] = -1
                self.fenxing_list.append({
                    'index': curr_idx,
                    'date': curr_idx,
                    'type': -1,
                    'high': curr_high,
                    'low': curr_low
                })
        
        return df
    
    def identify_bi(self, data: pd.DataFrame) -> pd.DataFrame:
        """识别笔（与原版相同）"""
        df = data.copy()
        
        if 'fenxing_type' not in df.columns:
            df = self.identify_fenxing(df)
        
        df['bi_type'] = 0
        self.bi_list = []
        
        if len(self.fenxing_list) < 2:
            return df
        
        fenxing_sorted = sorted(self.fenxing_list, key=lambda x: x['index'])
        
        i = 0
        while i < len(fenxing_sorted) - 1:
            curr_fx = fenxing_sorted[i]
            next_fx = fenxing_sorted[i + 1]
            
            if curr_fx['type'] == next_fx['type']:
                i += 1
                continue
            
            try:
                idx1 = df.index.get_loc(curr_fx['index'])
                idx2 = df.index.get_loc(next_fx['index'])
                k_count = idx2 - idx1 - 1
            except KeyError:
                i += 1
                continue
            
            if k_count < 0:
                i += 1
                continue
            
            if curr_fx['type'] == -1 and next_fx['type'] == 1:
                bi = {
                    'start': curr_fx['index'],
                    'end': next_fx['index'],
                    'type': 1,
                    'start_price': curr_fx['low'],
                    'end_price': next_fx['high'],
                    'k_count': k_count + 2
                }
                self.bi_list.append(bi)
                mask = (df.index >= curr_fx['index']) & (df.index <= next_fx['index'])
                df.loc[mask, 'bi_type'] = 1
                
            elif curr_fx['type'] == 1 and next_fx['type'] == -1:
                bi = {
                    'start': curr_fx['index'],
                    'end': next_fx['index'],
                    'type': -1,
                    'start_price': curr_fx['high'],
                    'end_price': next_fx['low'],
                    'k_count': k_count + 2
                }
                self.bi_list.append(bi)
                mask = (df.index >= curr_fx['index']) & (df.index <= next_fx['index'])
                df.loc[mask, 'bi_type'] = -1
            
            i += 1
        
        return df
    
    def identify_xianduan(self, data: pd.DataFrame) -> pd.DataFrame:
        """识别线段（与原版相同）"""
        df = data.copy()
        
        if len(self.bi_list) == 0:
            df = self.identify_bi(df)
        
        df['xianduan_type'] = 0
        self.xianduan_list = []
        
        if len(self.bi_list) < 3:
            return df
        
        bi_sorted = sorted(self.bi_list, key=lambda x: x['start'])
        
        i = 0
        while i < len(bi_sorted) - 2:
            bi1 = bi_sorted[i]
            bi2 = bi_sorted[i + 1]
            bi3 = bi_sorted[i + 2]
            
            is_alt = (bi1['type'] != bi2['type']) and (bi2['type'] != bi3['type'])
            
            if is_alt:
                xd_type = bi1['type']
                
                prices = [bi1['start_price'], bi1['end_price'], 
                         bi2['start_price'], bi2['end_price'],
                         bi3['start_price'], bi3['end_price']]
                
                xd = {
                    'type': xd_type,
                    'start': bi1['start'],
                    'end': bi3['end'],
                    'bi_list': [bi1, bi2, bi3],
                    'high': max(prices),
                    'low': min(prices)
                }
                self.xianduan_list.append(xd)
                
                i += 3
            else:
                i += 1
        
        for xd in self.xianduan_list:
            mask = (df.index >= xd['start']) & (df.index <= xd['end'])
            df.loc[mask, 'xianduan_type'] = xd['type']
        
        return df
    
    def identify_zhongshu(self, data: pd.DataFrame) -> pd.DataFrame:
        """识别中枢（与原版相同）"""
        df = data.copy()
        
        if len(self.xianduan_list) == 0:
            df = self.identify_xianduan(df)
        
        df['zhongshu_high'] = np.nan
        df['zhongshu_low'] = np.nan
        
        self.zhongshu_list = []
        
        if len(self.xianduan_list) < 3:
            return df
        
        xd_sorted = sorted(self.xianduan_list, key=lambda x: x['start'])
        
        i = 0
        while i < len(xd_sorted) - 2:
            xd1 = xd_sorted[i]
            xd2 = xd_sorted[i + 1]
            xd3 = xd_sorted[i + 2]
            
            overlap_high = min(xd1['high'], xd2['high'], xd3['high'])
            overlap_low = max(xd1['low'], xd2['low'], xd3['low'])
            
            if overlap_low < overlap_high:
                zs_start = xd1['start']
                zs_end = xd3['end']
                
                j = i + 3
                while j < len(xd_sorted):
                    xdj = xd_sorted[j]
                    if xdj['low'] < overlap_high and xdj['high'] > overlap_low:
                        overlap_high = min(overlap_high, xdj['high'])
                        overlap_low = max(overlap_low, xdj['low'])
                        zs_end = xdj['end']
                        j += 1
                    else:
                        break
                
                zs = {
                    'start': zs_start,
                    'end': zs_end,
                    'high': overlap_high,
                    'low': overlap_low,
                    'xd_list': xd_sorted[i:j]
                }
                self.zhongshu_list.append(zs)
                
                i = j - 1
            else:
                i += 1
        
        for zs in self.zhongshu_list:
            mask = (df.index >= zs['start']) & (df.index <= zs['end'])
            df.loc[mask, 'zhongshu_high'] = zs['high']
            df.loc[mask, 'zhongshu_low'] = zs['low']
        
        return df
    
    def identify_buy_sell_points(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        识别买卖点 - 延迟确认版本
        
        关键修改：买卖点日期向后延迟delay_days天，避免未来函数
        """
        df = data.copy()
        
        if len(self.zhongshu_list) == 0:
            df = self.identify_zhongshu(df)
        
        df['buy_point'] = 0
        df['sell_point'] = 0
        
        self.buy_points = []
        self.sell_points = []
        
        if len(self.xianduan_list) < 2 or len(self.zhongshu_list) == 0:
            return df
        
        xd_sorted = sorted(self.xianduan_list, key=lambda x: x['start'])
        zs_sorted = sorted(self.zhongshu_list, key=lambda x: x['start'])
        
        last_zs = None
        last_buy_point = None
        last_sell_point = None
        
        for i, xd in enumerate(xd_sorted):
            xd_type = xd['type']
            xd_end = xd['end']
            xd_high = xd['high']
            xd_low = xd['low']
            
            # 找到当前线段对应的中枢
            current_zs = None
            for zs in zs_sorted:
                if xd['start'] >= zs['start'] and xd['end'] <= zs['end']:
                    current_zs = zs
                    break
            
            if current_zs is None:
                for zs in reversed(zs_sorted):
                    if xd['start'] >= zs['end']:
                        current_zs = zs
                        break
            
            if current_zs is None:
                continue
            
            zs_high = current_zs['high']
            zs_low = current_zs['low']
            
            if i > 0:
                prev_xd = xd_sorted[i - 1]
                
                # 第一类买卖点
                if prev_xd['type'] == -1 and xd_type == 1:
                    if xd_high > zs_high:
                        # 一买：在前一个向下线段终点（延迟确认）
                        buy_date = prev_xd['end']
                        # 延迟确认
                        delayed_date = self._get_delayed_date(df, buy_date)
                        if delayed_date is not None:
                            try:
                                buy_price = df.loc[delayed_date, 'Close']
                            except KeyError:
                                buy_price = prev_xd['low']
                            
                            df.loc[delayed_date, 'buy_point'] = 1
                            buy_point = {
                                'index': delayed_date,
                                'date': delayed_date,
                                'type': 1,
                                'price': buy_price,
                                'desc': '第一类买点'
                            }
                            self.buy_points.append(buy_point)
                            last_buy_point = buy_point
                        
                elif prev_xd['type'] == 1 and xd_type == -1:
                    if xd_low < zs_low:
                        # 一卖：在前一个向上线段终点（延迟确认）
                        sell_date = prev_xd['end']
                        # 延迟确认
                        delayed_date = self._get_delayed_date(df, sell_date)
                        if delayed_date is not None:
                            try:
                                sell_price = df.loc[delayed_date, 'Close']
                            except KeyError:
                                sell_price = prev_xd['high']
                            
                            df.loc[delayed_date, 'sell_point'] = 1
                            sell_point = {
                                'index': delayed_date,
                                'date': delayed_date,
                                'type': 1,
                                'price': sell_price,
                                'desc': '第一类卖点'
                            }
                            self.sell_points.append(sell_point)
                            last_sell_point = sell_point
                
                # 第二类买卖点
                if last_buy_point is not None:
                    if prev_xd['type'] == 1 and xd_type == -1:
                        if xd_low >= last_buy_point['price']:
                            buy_date = prev_xd['end']
                            delayed_date = self._get_delayed_date(df, buy_date)
                            if delayed_date is not None:
                                try:
                                    buy_price = df.loc[delayed_date, 'Close']
                                except KeyError:
                                    buy_price = prev_xd['low']
                                
                                df.loc[delayed_date, 'buy_point'] = 2
                                self.buy_points.append({
                                    'index': delayed_date,
                                    'date': delayed_date,
                                    'type': 2,
                                    'price': buy_price,
                                    'desc': '第二类买点'
                                })
                
                if last_sell_point is not None:
                    if prev_xd['type'] == -1 and xd_type == 1:
                        if xd_high <= last_sell_point['price']:
                            sell_date = prev_xd['end']
                            delayed_date = self._get_delayed_date(df, sell_date)
                            if delayed_date is not None:
                                try:
                                    sell_price = df.loc[delayed_date, 'Close']
                                except KeyError:
                                    sell_price = prev_xd['high']
                                
                                df.loc[delayed_date, 'sell_point'] = 2
                                self.sell_points.append({
                                    'index': delayed_date,
                                    'date': delayed_date,
                                    'type': 2,
                                    'price': sell_price,
                                    'desc': '第二类卖点'
                                })
        
        return df
    
    def _get_delayed_date(self, df, original_date):
        """
        获取延迟后的日期
        
        Args:
            df: DataFrame
            original_date: 原始日期
            
        Returns:
            延迟后的日期，如果超出范围返回None
        """
        try:
            idx = df.index.get_loc(original_date)
            delayed_idx = idx + self.delay_days
            if delayed_idx < len(df):
                return df.index[delayed_idx]
            else:
                return None
        except KeyError:
            return None
    
    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """完整分析流程"""
        df = data.copy()
        
        df = self.identify_fenxing(df)
        df = self.identify_bi(df)
        df = self.identify_xianduan(df)
        df = self.identify_zhongshu(df)
        df = self.identify_buy_sell_points(df)
        
        return df
    
    def get_summary(self) -> dict:
        """获取分析结果汇总"""
        return {
            'fenxing_count': len(self.fenxing_list),
            'bi_count': len(self.bi_list),
            'xianduan_count': len(self.xianduan_list),
            'zhongshu_count': len(self.zhongshu_list),
            'buy_points': len(self.buy_points),
            'sell_points': len(self.sell_points),
            'buy_point_details': self.buy_points,
            'sell_point_details': self.sell_points
        }
