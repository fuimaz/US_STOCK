"""
缠论指标实现 - 完整版
基于缠中说禅理论，实现分型、笔、线段、中枢、买卖点
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


class ChanTheory:
    """
    缠论指标类
    
    实现步骤：
    1. K线包含关系处理
    2. 分型识别（顶分型、底分型）
    3. 笔识别（连接顶底分型）
    4. 线段识别（由笔组成）
    5. 中枢识别（线段重叠部分）
    6. 买卖点识别（基于中枢和背驰）
    """
    
    def __init__(self, k_type='day'):
        """
        初始化缠论指标
        
        Args:
            k_type: K线类型，'day'表示日K，'week'表示周K
        """
        self.k_type = k_type
        self.min_k_count = 5 if k_type == 'day' else 3  # 笔的最小K线数
        
        # 存储识别结果
        self.fenxing_list = []      # 分型列表
        self.bi_list = []           # 笔列表
        self.xianduan_list = []     # 线段列表
        self.zhongshu_list = []     # 中枢列表
        self.buy_points = []        # 买点列表
        self.sell_points = []       # 卖点列表
    
    def process_inclusion(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        处理K线包含关系
        
        包含关系定义：
        - 当前K线高点 >= 前一根K线高点 且 当前K线低点 <= 前一根K线低点
        - 或 当前K线高点 <= 前一根K线高点 且 当前K线低点 >= 前一根K线低点
        
        处理规则：
        - 向上走势（当前高点 > 前一根高点）：取高高（最高高点，最高低点）
        - 向下走势（当前高点 < 前一根高点）：取低低（最低低点，最低高点）
        
        Args:
            data: 原始OHLCV数据
            
        Returns:
            处理完包含关系后的DataFrame
        """
        df = data.copy()
        n = len(df)
        if n < 2:
            return df
        
        # 创建新列存储处理后的高低点
        processed_high = df['High'].values.copy()
        processed_low = df['Low'].values.copy()
        
        i = 1
        direction = 0  # 0:未确定, 1:向上, -1:向下
        
        while i < len(processed_high):
            prev_high = processed_high[i - 1]
            prev_low = processed_low[i - 1]
            curr_high = processed_high[i]
            curr_low = processed_low[i]
            
            # 检查是否有包含关系
            if (curr_high >= prev_high and curr_low <= prev_low) or \
               (curr_high <= prev_high and curr_low >= prev_low):
                # 有包含关系，需要处理
                
                # 确定方向（如果还未确定）
                if direction == 0:
                    # 向前查找确定方向
                    for j in range(1, i):
                        if processed_high[j] > processed_high[j - 1]:
                            direction = 1
                            break
                        elif processed_high[j] < processed_high[j - 1]:
                            direction = -1
                            break
                    # 如果还是0，根据当前K线判断
                    if direction == 0:
                        direction = 1 if curr_high > prev_high else -1
                
                # 根据方向处理包含关系
                if direction == 1:  # 向上走势，取高高
                    new_high = max(prev_high, curr_high)
                    new_low = max(prev_low, curr_low)
                else:  # 向下走势，取低低
                    new_high = min(prev_high, curr_high)
                    new_low = min(prev_low, curr_low)
                
                # 合并到当前K线
                processed_high[i] = new_high
                processed_low[i] = new_low
                
                # 删除前一根K线（标记为NaN）
                processed_high[i - 1] = np.nan
                processed_low[i - 1] = np.nan
                
                # 重新计算方向
                if i >= 2 and not np.isnan(processed_high[i - 2]):
                    if processed_high[i] > processed_high[i - 2]:
                        direction = 1
                    elif processed_high[i] < processed_high[i - 2]:
                        direction = -1
            else:
                # 没有包含关系，更新方向
                if curr_high > prev_high:
                    direction = 1
                elif curr_high < prev_high:
                    direction = -1
                i += 1
        
        # 将处理后的结果保存
        df['processed_high'] = processed_high
        df['processed_low'] = processed_low
        df['processed'] = ~df['processed_high'].isna()
        
        # 只保留未标记为NaN的K线用于后续分析
        self.processed_df = df[df['processed']].copy()
        
        return df
    
    def identify_fenxing(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        识别分型（顶分型和底分型）
        
        分型定义（在处理完包含关系后）：
        - 顶分型：中间K线的高点 > 左右两边K线的高点，且低点也 > 左右两边K线的低点
        - 底分型：中间K线的低点 < 左右两边K线的低点，且高点也 < 左右两边K线的高点
        
        Args:
            data: 包含OHLCV数据的DataFrame
            
        Returns:
            添加了分型标记的DataFrame
        """
        df = data.copy()
        
        # 先处理包含关系
        df = self.process_inclusion(df)
        
        # 使用处理后的数据
        if len(self.processed_df) < 3:
            df['fenxing_type'] = 0
            return df
        
        proc_df = self.processed_df.reset_index()
        
        # 获取原始索引的列名（可能是 'index' 或原始索引的名称）
        idx_col = proc_df.columns[0]
        
        # 初始化分型标记
        df['fenxing_type'] = 0  # 0:无分型, 1:顶分型, -1:底分型
        
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
            
            # 识别顶分型
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
            
            # 识别底分型
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
        """
        识别笔
        
        笔的定义：
        1. 由相邻的顶分型和底分型连接而成
        2. 顶分型连接底分型为向下笔
        3. 底分型连接顶分型为向上笔
        4. 顶分型与底分型之间至少有1根独立K线（日K至少5根K线）
        5. 笔的开始和结束必须是顶底分型交替
        
        Args:
            data: 包含分型数据的DataFrame
            
        Returns:
            添加了笔标记的DataFrame
        """
        df = data.copy()
        
        # 如果没有分型数据，先识别分型
        if 'fenxing_type' not in df.columns:
            df = self.identify_fenxing(df)
        
        # 初始化笔标记
        df['bi_type'] = 0  # 0:无笔, 1:向上笔, -1:向下笔
        
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
            
            # 检查K线数量（顶底分型之间至少有1根独立K线）
            # 使用索引位置计算
            try:
                idx1 = df.index.get_loc(curr_fx['index'])
                idx2 = df.index.get_loc(next_fx['index'])
                k_count = idx2 - idx1 - 1  # 之间的K线数
            except KeyError:
                i += 1
                continue
            
            if k_count < 0:  # 放宽限制：允许0根独立K线（只要不在同一天）
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
                
                # 标记笔
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
                
                # 标记笔
                mask = (df.index >= curr_fx['index']) & (df.index <= next_fx['index'])
                df.loc[mask, 'bi_type'] = -1
            
            # 移动到下一个分型（笔的结束分型作为下笔的开始）
            i += 1
        
        return df
    
    def identify_xianduan(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        识别线段（简化版）
        
        简化线段定义：
        1. 至少由3笔组成
        2. 线段方向由第一笔决定
        3. 当出现反向笔突破前一线段的高点/低点时，前一线段结束
        4. 简化处理：连续同向笔合并，反向笔检查是否形成新的线段
        
        Args:
            data: 包含笔数据的DataFrame
            
        Returns:
            添加了线段标记的DataFrame
        """
        df = data.copy()
        
        # 如果没有笔数据，先识别笔
        if len(self.bi_list) == 0:
            df = self.identify_bi(df)
        
        # 初始化线段标记
        df['xianduan_type'] = 0
        
        self.xianduan_list = []
        
        if len(self.bi_list) < 3:
            return df
        
        # 按时间排序
        bi_sorted = sorted(self.bi_list, key=lambda x: x['start'])
        
        # 简化的线段识别：3笔构成一段
        i = 0
        while i < len(bi_sorted) - 2:
            bi1 = bi_sorted[i]
            bi2 = bi_sorted[i + 1]
            bi3 = bi_sorted[i + 2]
            
            # 检查方向是否交替
            is_alt = (bi1['type'] != bi2['type']) and (bi2['type'] != bi3['type'])
            
            if is_alt:
                xd_type = bi1['type']
                
                # 计算线段高低点
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
                
                i += 3  # 跳过已使用的3笔
            else:
                i += 1
        
        # 标记线段
        for xd in self.xianduan_list:
            mask = (df.index >= xd['start']) & (df.index <= xd['end'])
            df.loc[mask, 'xianduan_type'] = xd['type']
        
        return df
    
    def identify_zhongshu(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        识别中枢（简化版）
        
        中枢定义：
        1. 连续3段以上线段的价格重叠区间
        2. 中枢区间 = [max(各段低点), min(各段高点)]
        3. 必须有有效重叠（max(低点) < min(高点)）
        
        Args:
            data: 包含线段数据的DataFrame
            
        Returns:
            添加了中枢标记的DataFrame
        """
        df = data.copy()
        
        # 如果没有线段数据，先识别线段
        if len(self.xianduan_list) == 0:
            df = self.identify_xianduan(df)
        
        # 初始化中枢标记
        df['zhongshu_high'] = np.nan
        df['zhongshu_low'] = np.nan
        
        self.zhongshu_list = []
        
        if len(self.xianduan_list) < 3:
            return df
        
        # 按时间排序
        xd_sorted = sorted(self.xianduan_list, key=lambda x: x['start'])
        
        # 寻找3段以上重叠
        i = 0
        while i < len(xd_sorted) - 2:
            # 取连续的3段
            xd1 = xd_sorted[i]
            xd2 = xd_sorted[i + 1]
            xd3 = xd_sorted[i + 2]
            
            # 检查是否有重叠
            overlap_high = min(xd1['high'], xd2['high'], xd3['high'])
            overlap_low = max(xd1['low'], xd2['low'], xd3['low'])
            
            if overlap_low < overlap_high:
                # 形成中枢
                zs_start = xd1['start']
                zs_end = xd3['end']
                
                # 继续向后找是否还有更多段属于这个中枢
                j = i + 3
                while j < len(xd_sorted):
                    xdj = xd_sorted[j]
                    # 检查这一段是否与前3段有重叠
                    if xdj['low'] < overlap_high and xdj['high'] > overlap_low:
                        # 更新中枢区间
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
                
                i = j - 1  # 从下一个可能的中枢开始
            else:
                i += 1
        
        # 标记中枢
        for zs in self.zhongshu_list:
            mask = (df.index >= zs['start']) & (df.index <= zs['end'])
            df.loc[mask, 'zhongshu_high'] = zs['high']
            df.loc[mask, 'zhongshu_low'] = zs['low']
        
        return df
    
    def identify_buy_sell_points(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        识别买卖点
        
        缠论买卖点定义：
        
        第一类买点：
        - 下跌趋势背驰后的买点
        - 向下线段结束后，形成向上线段，且向上线段突破最后一个中枢
        
        第一类卖点：
        - 上涨趋势背驰后的卖点
        - 向上线段结束后，形成向下线段，且向下线段跌破最后一个中枢
        
        第二类买点：
        - 第一类买点后，回调形成的次低点（不破前低）
        
        第二类卖点：
        - 第一类卖点后，反弹形成的次高点（不过前高）
        
        第三类买点：
        - 突破中枢后，回调不回到中枢内
        
        第三类卖点：
        - 跌破中枢后，反弹不回到中枢内
        
        Args:
            data: 包含中枢和线段数据的DataFrame
            
        Returns:
            添加了买卖点标记的DataFrame
        """
        df = data.copy()
        
        # 如果没有中枢数据，先识别中枢
        if len(self.zhongshu_list) == 0:
            df = self.identify_zhongshu(df)
        
        # 初始化买卖点标记
        df['buy_point'] = 0   # 0:无买点, 1:一买, 2:二买, 3:三买
        df['sell_point'] = 0  # 0:无卖点, 1:一卖, 2:二卖, 3:三卖
        
        self.buy_points = []
        self.sell_points = []
        
        if len(self.xianduan_list) < 2 or len(self.zhongshu_list) == 0:
            return df
        
        # 按时间顺序处理线段
        xd_sorted = sorted(self.xianduan_list, key=lambda x: x['start'])
        zs_sorted = sorted(self.zhongshu_list, key=lambda x: x['start'])
        
        # 找到每个中枢后的线段
        last_zs = None
        last_zs_idx = -1
        last_buy_point = None  # 记录最后一买的位置
        last_sell_point = None  # 记录最后一卖的位置
        
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
                # 当前线段不在中枢内，可能是中枢后的线段
                # 找到最近的中枢
                for zs in reversed(zs_sorted):
                    if xd['start'] >= zs['end']:
                        current_zs = zs
                        break
            
            if current_zs is None:
                continue
            
            zs_high = current_zs['high']
            zs_low = current_zs['low']
            
            # 判断买卖点（需要至少前一个线段）
            if i > 0:
                prev_xd = xd_sorted[i - 1]
                
                # 第一类买卖点：趋势反转突破中枢
                # 一买：向下线段结束后，向上线段突破中枢 -> 买点在向下线段的终点（低点）
                # 一卖：向上线段结束后，向下线段跌破中枢 -> 卖点在向上线段的终点（高点）
                if prev_xd['type'] == -1 and xd_type == 1:
                    # 向下线段后向上线段
                    if xd_high > zs_high:
                        # 向上突破中枢，是一买
                        # 一买位置：前一个向下线段的结束点（低点）
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
                            'desc': '第一类买点'
                        }
                        self.buy_points.append(buy_point)
                        last_buy_point = buy_point
                        
                elif prev_xd['type'] == 1 and xd_type == -1:
                    # 向上线段后向下线段
                    if xd_low < zs_low:
                        # 向下跌破中枢，是一卖
                        # 一卖位置：前一个向上线段的结束点（高点）
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
                            'desc': '第一类卖点'
                        }
                        self.sell_points.append(sell_point)
                        last_sell_point = sell_point
                
                # 第二类买卖点：一买/一卖后的次级别回调
                # 二买：一买后，向上线段结束，回调（向下线段）不破前低
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
                                'desc': '第二类买点'
                            })
                
                # 二卖：一卖后，向下线段结束，反弹（向上线段）不过前高
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
                                'desc': '第二类卖点'
                            })
                
                # 第三类买卖点
                # 三卖：向上线段后向下线段，向下线段完全在中枢上方
                if prev_xd['type'] == 1 and xd_type == -1:
                    if xd_high > zs_high and xd_low > zs_high:
                        sell_date = prev_xd['end']
                        try:
                            sell_price = df.loc[sell_date, 'Close']
                        except KeyError:
                            sell_price = prev_xd['high']
                        
                        df.loc[sell_date, 'sell_point'] = 3
                        self.sell_points.append({
                            'index': sell_date,
                            'date': sell_date,
                            'type': 3,
                            'price': sell_price,
                            'desc': '第三类卖点'
                        })
                        
                # 三买：向下线段后向上线段，向上线段完全在中枢下方（这种情况较少见）
                elif prev_xd['type'] == -1 and xd_type == 1:
                    if xd_low > zs_low and xd_low > zs_high:
                        buy_date = prev_xd['end']
                        try:
                            buy_price = df.loc[buy_date, 'Close']
                        except KeyError:
                            buy_price = prev_xd['low']
                        
                        df.loc[buy_date, 'buy_point'] = 3
                        self.buy_points.append({
                            'index': buy_date,
                            'date': buy_date,
                            'type': 3,
                            'price': buy_price,
                            'desc': '第三类买点'
                        })
        
        return df
    
    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        完整分析流程
        
        Args:
            data: 包含OHLCV数据的DataFrame
            
        Returns:
            添加了所有缠论指标的DataFrame
        """
        df = data.copy()
        
        # 1. 处理包含关系 + 识别分型
        df = self.identify_fenxing(df)
        
        # 2. 识别笔
        df = self.identify_bi(df)
        
        # 3. 识别线段
        df = self.identify_xianduan(df)
        
        # 4. 识别中枢
        df = self.identify_zhongshu(df)
        
        # 5. 识别买卖点
        df = self.identify_buy_sell_points(df)
        
        return df
    
    def get_summary(self) -> dict:
        """
        获取分析结果汇总
        
        Returns:
            包含统计信息的字典
        """
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
