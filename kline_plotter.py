import mplfinance as mpf
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib as mpl


class KLinePlotter:
    def __init__(self, style: str = 'charles'):
        """
        K线图绘制器
        
        Args:
            style: 图表样式，可选 'charles', 'default', 'yahoo', 'nightclouds', 'sas', 'starsandstripes'
        """
        self.style = style
        self._setup_chinese_font()
    
    def _setup_chinese_font(self):
        """设置中文字体"""
        try:
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
        except:
            pass
    
    def plot_with_indicators(
        self,
        data: pd.DataFrame,
        title: str = "K线图",
        show_boll: bool = True,
        show_rsi: bool = True,
        show_volume: bool = True,
        boll_period: int = 20,
        boll_std: float = 2,
        rsi_period: int = 14,
        save_path: Optional[str] = None,
        figsize: tuple = (14, 10)
    ):
        """
        绘制带有BOLL、RSI指标的K线图
        
        Args:
            data: 包含OHLCV数据的DataFrame
            title: 图表标题
            show_boll: 是否显示布林带
            show_rsi: 是否显示RSI
            show_volume: 是否显示成交量
            boll_period: 布林带周期
            boll_std: 布林带标准差倍数
            rsi_period: RSI周期
            save_path: 图片保存路径
            figsize: 图表大小
        """
        df = data.copy()
        
        addplot = []
        
        if show_boll:
            df['BB_Middle'] = df['Close'].rolling(window=boll_period).mean()
            df['BB_Std'] = df['Close'].rolling(window=boll_period).std()
            df['BB_Upper'] = df['BB_Middle'] + df['BB_Std'] * boll_std
            df['BB_Lower'] = df['BB_Middle'] - df['BB_Std'] * boll_std
            
            addplot.append(
                mpf.make_addplot(
                    df['BB_Upper'],
                    type='line',
                    color='orange',
                    alpha=0.5,
                    panel=0,
                    secondary_y=False
                )
            )
            addplot.append(
                mpf.make_addplot(
                    df['BB_Middle'],
                    type='line',
                    color='blue',
                    alpha=0.5,
                    panel=0,
                    secondary_y=False
                )
            )
            addplot.append(
                mpf.make_addplot(
                    df['BB_Lower'],
                    type='line',
                    color='orange',
                    alpha=0.5,
                    panel=0,
                    secondary_y=False
                )
            )
        
        if show_rsi:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            addplot.append(
                mpf.make_addplot(
                    df['RSI'],
                    type='line',
                    color='purple',
                    panel=2 if show_volume else 1,
                    ylabel='RSI',
                    secondary_y=False
                )
            )
        
        kwargs = {
            'type': 'candle',
            'style': self.style,
            'title': title,
            'ylabel': '价格',
            'volume': show_volume,
            'figsize': figsize,
            'addplot': addplot,
            'warn_too_much_data': len(df) + 1000
        }
        
        if show_volume:
            kwargs['ylabel_lower'] = '成交量'
        
        if save_path:
            kwargs['savefig'] = save_path
        
        mpf.plot(df, **kwargs)

    def plot_candlestick(
        self,
        data: pd.DataFrame,
        title: str = "K线图",
        mav: Optional[List[int]] = None,
        volume: bool = True,
        save_path: Optional[str] = None,
        figsize: tuple = (12, 8)
    ):
        """
        绘制K线图
        
        Args:
            data: 包含OHLCV数据的DataFrame
            title: 图表标题
            mav: 移动平均线周期列表，如 [5, 10, 20]
            volume: 是否显示成交量
            save_path: 图片保存路径，如 'chart.png'
            figsize: 图表大小
        """
        if mav is None:
            mav = [5, 10, 20]
        
        kwargs = {
            'type': 'candle',
            'style': self.style,
            'title': title,
            'ylabel': '价格',
            'ylabel_lower': '成交量',
            'volume': volume,
            'mav': mav,
            'figsize': figsize
        }
        
        if save_path:
            kwargs['savefig'] = save_path
        
        mpf.plot(data, **kwargs)

    def plot_with_signals(
        self,
        data: pd.DataFrame,
        buy_signals: pd.Series,
        sell_signals: pd.Series,
        title: str = "K线图与交易信号",
        mav: Optional[List[int]] = None,
        volume: bool = True,
        save_path: Optional[str] = None,
        figsize: tuple = (14, 10)
    ):
        """
        绘制带有买卖信号的K线图
        
        Args:
            data: 包含OHLCV数据的DataFrame
            buy_signals: 买入信号Series，True表示买入点
            sell_signals: 卖出信号Series，True表示卖出点
            title: 图表标题
            mav: 移动平均线周期列表
            volume: 是否显示成交量
            save_path: 图片保存路径
            figsize: 图表大小
        """
        if mav is None:
            mav = [5, 10, 20]
        
        addplot = []
        
        if buy_signals.any():
            buy_markers = buy_signals.astype(float)
            buy_markers[buy_markers == 0] = None
            addplot.append(
                mpf.make_addplot(
                    buy_markers,
                    type='scatter',
                    markersize=100,
                    marker='^',
                    color='g',
                    panel=0,
                    secondary_y=False
                )
            )
        
        if sell_signals.any():
            sell_markers = sell_signals.astype(float)
            sell_markers[sell_markers == 0] = None
            addplot.append(
                mpf.make_addplot(
                    sell_markers,
                    type='scatter',
                    markersize=100,
                    marker='v',
                    color='r',
                    panel=0,
                    secondary_y=False
                )
            )
        
        kwargs = {
            'type': 'candle',
            'style': self.style,
            'title': title,
            'ylabel': '价格',
            'ylabel_lower': '成交量',
            'volume': volume,
            'mav': mav,
            'figsize': figsize,
            'addplot': addplot
        }
        
        if save_path:
            kwargs['savefig'] = save_path
        
        mpf.plot(data, **kwargs)

    def plot_with_signals_and_indicators(
        self,
        data: pd.DataFrame,
        buy_signals: pd.Series,
        sell_signals: pd.Series,
        title: str = "K线图与交易信号",
        show_boll: bool = True,
        show_rsi: bool = True,
        show_volume: bool = True,
        boll_period: int = 20,
        boll_std: float = 2,
        rsi_period: int = 14,
        save_path: Optional[str] = None,
        figsize: tuple = (16, 12)
    ):
        """
        绘制带有买卖信号和BOLL、RSI指标的K线图
        
        Args:
            data: 包含OHLCV数据的DataFrame
            buy_signals: 买入信号Series，True表示买入点
            sell_signals: 卖出信号Series，True表示卖出点
            title: 图表标题
            show_boll: 是否显示布林带
            show_rsi: 是否显示RSI
            show_volume: 是否显示成交量
            boll_period: 布林带周期
            boll_std: 布林带标准差倍数
            rsi_period: RSI周期
            save_path: 图片保存路径
            figsize: 图表大小
        """
        df = data.copy()
        
        addplot = []
        
        if show_boll:
            df['BB_Middle'] = df['Close'].rolling(window=boll_period).mean()
            df['BB_Std'] = df['Close'].rolling(window=boll_period).std()
            df['BB_Upper'] = df['BB_Middle'] + df['BB_Std'] * boll_std
            df['BB_Lower'] = df['BB_Middle'] - df['BB_Std'] * boll_std
            
            addplot.append(
                mpf.make_addplot(
                    df['BB_Upper'],
                    type='line',
                    color='orange',
                    alpha=0.5,
                    panel=0,
                    secondary_y=False
                )
            )
            addplot.append(
                mpf.make_addplot(
                    df['BB_Middle'],
                    type='line',
                    color='blue',
                    alpha=0.5,
                    panel=0,
                    secondary_y=False
                )
            )
            addplot.append(
                mpf.make_addplot(
                    df['BB_Lower'],
                    type='line',
                    color='orange',
                    alpha=0.5,
                    panel=0,
                    secondary_y=False
                )
            )
        
        if show_rsi:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            addplot.append(
                mpf.make_addplot(
                    df['RSI'],
                    type='line',
                    color='purple',
                    panel=2 if show_volume else 1,
                    ylabel='RSI',
                    secondary_y=False
                )
            )
        
        if buy_signals.any():
            buy_markers = buy_signals.astype(float)
            buy_markers[buy_markers == 0] = None
            addplot.append(
                mpf.make_addplot(
                    buy_markers,
                    type='scatter',
                    markersize=100,
                    marker='^',
                    color='g',
                    panel=0,
                    secondary_y=False
                )
            )
        
        if sell_signals.any():
            sell_markers = sell_signals.astype(float)
            sell_markers[sell_markers == 0] = None
            addplot.append(
                mpf.make_addplot(
                    sell_markers,
                    type='scatter',
                    markersize=100,
                    marker='v',
                    color='r',
                    panel=0,
                    secondary_y=False
                )
            )
        
        kwargs = {
            'type': 'candle',
            'style': self.style,
            'title': title,
            'ylabel': '价格',
            'volume': show_volume,
            'figsize': figsize,
            'addplot': addplot
        }
        
        if show_volume:
            kwargs['ylabel_lower'] = '成交量'
        
        if save_path:
            kwargs['savefig'] = save_path
        
        mpf.plot(df, **kwargs)

    def plot_comparison(
        self,
        data_dict: Dict[str, pd.DataFrame],
        title: str = "股票对比",
        normalize: bool = True,
        figsize: tuple = (14, 8),
        save_path: Optional[str] = None
    ):
        """
        绘制多只股票的对比图
        
        Args:
            data_dict: 字典，key为股票代码，value为对应的DataFrame
            title: 图表标题
            normalize: 是否归一化（以第一日价格为基准）
            figsize: 图表大小
            save_path: 图片保存路径
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        for symbol, data in data_dict.items():
            close_prices = data['Close']
            
            if normalize:
                close_prices = close_prices / close_prices.iloc[0] * 100
            
            ax.plot(close_prices.index, close_prices, label=symbol)
        
        ax.set_title(title)
        ax.set_xlabel('日期')
        ax.set_ylabel('价格' + (' (归一化)' if normalize else ''))
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
