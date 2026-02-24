"""
缠论指标实现 - 实时近似版本（方案3）

核心思想：
1. 不等待后续K线确认分型
2. 当天收盘时，如果当前K线满足部分分型条件，标记为"疑似分型"
3. 基于疑似分型实时生成买卖点
4. 接受一定误判率，但无未来函数

疑似分型判断规则：
- 疑似顶分型：当前高点 > 前一根高点 且 当前低点 > 前一根低点
- 疑似底分型：当前低点 < 前一根低点 且 当前高点 < 前一根高点

注意：这与标准缠论分型定义不同（标准需要后一根K线确认）
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


class ChanTheoryRealtime:
    """
    缠论指标类 - 实时近似版本
    """
    
    def __init__(self, k_type='day'):
        """
        初始化缠论指标
        
        Args:
            k_type: K线类型，'day'表示日K，'week'表示周K
        """
        self.k_type = k_type
        self.min_k_count = 5 if k_type == 'day' else 3
        
        # 存储识别结果
        self.fenxing_list = []      # 疑似分型列表
        self.bi_list = []
        self.xianduan_list = []
        self.zhongshu_list = []
        self.buy_points = []
        self.sell_points = []
    
    def identify_fenxing_realtime(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        实时识别疑似分型
        
        规则（与标准缠论不同）：
        - 疑似顶分型：当前高点 > 前一根高点 AND 当前低点 > 前一根低点
        - 疑似底分型：当前低点 < 前一根低点 AND 当前高点 < 前一根高点
        
        不等待后一根K线确认，当天收盘即可判断
        """
        df = data.copy()
        
        # 初始化分型标记
        df['fenxing_type'] = 0  # 0:无分型, 1:疑似顶分型, -1:疑似底分型
        df['fenxing_high'] = df['High']
        df['fenxing_low'] = df['Low']
        
        self.fenxing_list = []
        
        # 遍历K线识别疑似分型（从第1根开始，需要前一根）
        for i in range(1, len(df)):
            prev_high = df['High'].iloc[i - 1]
            prev_low = df['Low'].iloc[i - 1]
            curr_high = df['High'].iloc[i]
            curr_low = df['Low'].iloc[i]
            curr_idx = df.index[i]
            
            # 疑似顶分型：当前高于前一根（上涨趋势中的高点）
            if curr_high > prev_high and curr_low > prev_low:
                df.loc[curr_idx, 'fenxing_type'] = 1
                df.loc[curr_idx, 'fenxing_high'] = curr_high
                df.loc[curr_idx, 'fenxing_low'] = curr_low
                self.fenxing_list.append({
                    'index': curr_idx,
                    'date': curr_idx,
                    'type': 1,
                    'high': curr_high,
                    'low': curr_low,
                    'confirmed': False  # 标记为未确认
                })
            
            # 疑似底分型：当前低于前一根（下跌趋势中的低点）
            elif curr_low < prev_low and curr_high < prev_high:
                df.loc[curr_idx, 'fenxing_type'] = -1
                df.loc[curr_idx, 'fenxing_high'] = curr_high
                df.loc[curr_idx, 'fenxing_low'] = curr_low
                self.fenxing_list.append({
                    'index': curr_idx,
                    'date': curr_idx,
                    'type': -1,
                    'high': curr_high,
                    'low': curr_low,
                    'confirmed': False
                })
        
        return df
    
    def identify_bi(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        识别笔（基于疑似分型）
        """
        df = data.copy()
        
        if 'fenxing_type' not in df.columns:
            df = self.identify_fenxing_realtime(df)
        
        df['bi_type'] = 0
        self.bi_list = []
        
        if len(self.fenxing_list) < 2:
            return df
        
        # 按时间顺序处理分型
        fenxing_sorted = sorted(self.fenxing_list, key=lambda x: x['index'])
        
        i = 0
        while i < len(fenxing_sorted) - 1:
            curr_fx = fenxing_sorted[i]
            next_fx = fenxing_sorted[i + 1]
            
            # 必须是相反类型（顶底交替）
            if curr_fx['type'] == next_fx['type']:
                i += 1
                continue
            
            # 检查K线数量
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
            
            # 确定笔的方向
            if curr_fx['type'] == -1 and next_fx['type'] == 1:
                # 底分型到顶分型：向上笔
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
                # 顶分型到底分型：向下笔
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
        识别买卖点 - 实时版本
        
        基于疑似分型和线段，实时生成买卖点
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
                        # 一买：在前一个向下线段终点（实时判断）
                        buy_date = prev_xd['end']
                        try:
                            buy_price = df.loc[buy_date, 'Close']
                        except KeyError:
                            buy_price = prev_xd['low']
                        
                        df.loc[buy_date, 'buy_point'] = 1
                        buy_point = {
                            'index': buy_date,
                            'date': buy_date,
                            'type': 1,
                            'price': buy_price,
                            'desc': '第一类买点(实时)'
                        }
                        self.buy_points.append(buy_point)
                        last_buy_point = buy_point
                        
                elif prev_xd['type'] == 1 and xd_type == -1:
                    if xd_low < zs_low:
                        # 一卖：在前一个向上线段终点（实时判断）
                        sell_date = prev_xd['end']
                        try:
                            sell_price = df.loc[sell_date, 'Close']
                        except KeyError:
                            sell_price = prev_xd['high']
                        
                        df.loc[sell_date, 'sell_point'] = 1
                        sell_point = {
                            'index': sell_date,
                            'date': sell_date,
                            'type': 1,
                            'price': sell_price,
                            'desc': '第一类卖点(实时)'
                        }
                        self.sell_points.append(sell_point)
                        last_sell_point = sell_point
                
                # 第二类买卖点
                if last_buy_point is not None:
                    if prev_xd['type'] == 1 and xd_type == -1:
                        if xd_low >= last_buy_point['price']:
                            buy_date = prev_xd['end']
                            try:
                                buy_price = df.loc[buy_date, 'Close']
                            except KeyError:
                                buy_price = prev_xd['low']
                            
                            df.loc[buy_date, 'buy_point'] = 2
                            self.buy_points.append({
                                'index': buy_date,
                                'date': buy_date,
                                'type': 2,
                                'price': buy_price,
                                'desc': '第二类买点(实时)'
                            })
                
                if last_sell_point is not None:
                    if prev_xd['type'] == -1 and xd_type == 1:
                        if xd_high <= last_sell_point['price']:
                            sell_date = prev_xd['end']
                            try:
                                sell_price = df.loc[sell_date, 'Close']
                            except KeyError:
                                sell_price = prev_xd['high']
                            
                            df.loc[sell_date, 'sell_point'] = 2
                            self.sell_points.append({
                                'index': sell_date,
                                'date': sell_date,
                                'type': 2,
                                'price': sell_price,
                                'desc': '第二类卖点(实时)'
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
