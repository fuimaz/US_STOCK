import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.lines import Line2D
import mplfinance as mpf
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter
import argparse


class InteractiveKLineViewer:
    def __init__(self, data: pd.DataFrame, title: str = "K线图", signals: pd.DataFrame = None):
        """
        交互式K线图查看器
        
        Args:
            data: 包含OHLCV数据的DataFrame
            title: 图表标题
            signals: 包含买卖信号的DataFrame（可选）
        """
        self.data = data
        self.title = title
        self.signals = signals
        self.window_size = len(data)  # 默认显示全部K线（全览图）
        self.current_pos = 0  # 从开始位置显示
        self.is_dragging = False
        self.last_x = None
        self.view_data = None  # 当前视图数据
        self.slider = None  # 滑动条控件
        self.last_update_pos = -1  # 上次更新的位置（用于节流）
        self.drag_threshold = 5  # 拖动阈值（像素），只有移动超过这个距离才更新
        self.last_xaxis_range = None  # 上次x轴范围，避免重复更新标签
        
        # 图表对象引用（用于更新而不是重绘）
        self.candle_collection = None  # 使用PatchCollection批量绘制K线实体
        self.wick_collection = None  # 使用LineCollection批量绘制影线
        self.bb_upper_line = None
        self.bb_middle_line = None
        self.bb_lower_line = None
        self.volume_collection = None  # 使用PatchCollection批量绘制成交量
        self.rsi_line = None
        self.signal_scatters = {'buy': None, 'sell': None}
        
        # 预计算所有技术指标
        self._precompute_indicators()
        
        self._setup_chinese_font()
        self._create_plot()
        self._setup_events()
        
    def _precompute_indicators(self):
        """预计算所有技术指标，避免重复计算"""
        # 计算布林带
        self.data['BB_Middle'] = self.data['Close'].rolling(window=20).mean()
        self.data['BB_Std'] = self.data['Close'].rolling(window=20).std()
        self.data['BB_Upper'] = self.data['BB_Middle'] + self.data['BB_Std'] * 2
        self.data['BB_Lower'] = self.data['BB_Middle'] - self.data['BB_Std'] * 2
        
        # 计算RSI
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        
        # 预计算K线颜色
        self.data['Color'] = np.where(self.data['Close'] >= self.data['Open'], 'r', 'g')
        
    def _setup_chinese_font(self):
        """设置中文字体"""
        try:
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
        except:
            pass
    
    def _create_plot(self):
        """创建图表"""
        self.fig, self.axes = plt.subplots(3, 1, figsize=(16, 12), 
                                          gridspec_kw={'height_ratios': [3, 1, 1]})
        self.fig.suptitle(self.title, fontsize=14, fontweight='bold')
        
        # 调整布局为滑动条留出空间
        plt.subplots_adjust(left=0.08, right=0.92, top=0.93, bottom=0.15, hspace=0.4)
        
        # 创建滑动条
        self._create_slider()
        
        self._update_plot()
    
    def _update_plot(self):
        """更新图表内容"""
        start_idx = max(0, self.current_pos)
        end_idx = min(len(self.data), self.current_pos + self.window_size)
        self.view_data = self.data.iloc[start_idx:end_idx]
        
        # 使用高效方式更新图表
        self._update_candles(self.axes[0], self.view_data, start_idx)
        self._update_volume(self.axes[1], self.view_data)
        self._update_rsi(self.axes[2], self.view_data)
        
        # 只在x轴范围变化时更新标签
        current_xaxis_range = (start_idx, end_idx)
        if self.last_xaxis_range != current_xaxis_range:
            dates = pd.to_datetime(self.view_data.index)
            self._set_date_ticks(self.axes[0], dates)
            self._set_date_ticks(self.axes[1], dates)
            self._set_date_ticks(self.axes[2], dates)
            self.last_xaxis_range = current_xaxis_range
        
        # 更新信息提示
        info_text = f"显示范围: {len(self.view_data)} 根K线\n"
        info_text += f"总数据: {len(self.data)} 根\n"
        info_text += f"当前位置: {start_idx} - {end_idx-1}"
        
        # 移除旧的信息文本
        for text in self.axes[0].texts:
            if hasattr(text, '_info_text'):
                text.remove()
        
        # 添加新的信息文本
        text_obj = self.axes[0].text(0.02, 0.98, info_text, transform=self.axes[0].transAxes,
                                     fontsize=9, verticalalignment='top',
                                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        text_obj._info_text = True
        
        self.fig.canvas.draw_idle()
    
    def _update_candles(self, ax, data, start_idx):
        """高效更新K线图 - 使用LineCollection和PatchCollection批量绘制"""
        # 清除旧的K线对象
        if self.candle_collection is not None:
            self.candle_collection.remove()
        if self.wick_collection is not None:
            self.wick_collection.remove()
        
        if len(data) == 0:
            return
        
        # 使用向量化操作批量创建K线
        n = len(data)
        opens = data['Open'].values
        highs = data['High'].values
        lows = data['Low'].values
        closes = data['Close'].values
        colors = data['Color'].values
        
        # 批量创建影线 - 使用LineCollection
        segments = []
        wick_colors = []
        for i in range(n):
            segments.append([(i, lows[i]), (i, highs[i])])
            wick_colors.append(colors[i])
        
        self.wick_collection = LineCollection(segments, colors=wick_colors, linewidths=1)
        ax.add_collection(self.wick_collection)
        
        # 批量创建实体 - 使用PatchCollection
        heights = np.abs(closes - opens)
        bottoms = np.minimum(opens, closes)
        
        patches = []
        for i in range(n):
            rect = Rectangle((i - 0.3, bottoms[i]), 0.6, heights[i])
            patches.append(rect)
        
        self.candle_collection = PatchCollection(patches, facecolors=colors, edgecolors=colors, alpha=0.8)
        ax.add_collection(self.candle_collection)
        
        ax.set_xlim(-0.5, n - 0.5)
        ax.set_ylabel('价格')
        ax.grid(True, alpha=0.3)
        
        # 更新布林带
        bb_upper = data['BB_Upper'].values
        bb_middle = data['BB_Middle'].values
        bb_lower = data['BB_Lower'].values
        x = np.arange(n)
        
        if self.bb_upper_line is None:
            self.bb_upper_line, = ax.plot(x, bb_upper, 'orange', alpha=0.5, linewidth=1)
            self.bb_middle_line, = ax.plot(x, bb_middle, 'blue', alpha=0.5, linewidth=1)
            self.bb_lower_line, = ax.plot(x, bb_lower, 'orange', alpha=0.5, linewidth=1)
        else:
            self.bb_upper_line.set_data(x, bb_upper)
            self.bb_middle_line.set_data(x, bb_middle)
            self.bb_lower_line.set_data(x, bb_lower)
        
        # 更新买卖点标记
        self._update_signals(ax, data)
    
    def _update_volume(self, ax, data):
        """高效更新成交量图 - 使用PatchCollection批量绘制"""
        if self.volume_collection is not None:
            self.volume_collection.remove()
        
        if len(data) == 0:
            return
        
        colors = data['Color'].values
        x = np.arange(len(data))
        volumes = data['Volume'].values
        bar_width = 0.6
        
        # 批量创建成交量柱状图
        patches = []
        for i in range(len(data)):
            rect = Rectangle((i - bar_width/2, 0), bar_width, volumes[i])
            patches.append(rect)
        
        self.volume_collection = PatchCollection(patches, facecolors=colors, alpha=0.6)
        ax.add_collection(self.volume_collection)
        
        ax.set_xlim(-0.5, len(data) - 0.5)
        ax.set_ylabel('成交量')
        ax.grid(True, alpha=0.3)
    
    def _update_rsi(self, ax, data):
        """高效更新RSI图"""
        if len(data) == 0:
            return
        
        x = np.arange(len(data))
        rsi_values = data['RSI'].values
        
        if self.rsi_line is None:
            self.rsi_line, = ax.plot(x, rsi_values, 'purple', linewidth=1.5)
        else:
            self.rsi_line.set_data(x, rsi_values)
        
        ax.set_xlim(-0.5, len(data) - 0.5)
        ax.set_ylabel('RSI')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        # 添加参考线（只添加一次）
        if not hasattr(ax, '_ref_lines_added'):
            ax.axhline(y=70, color='r', linestyle='--', alpha=0.5)
            ax.axhline(y=30, color='g', linestyle='--', alpha=0.5)
            ax._ref_lines_added = True
    
    def _update_signals(self, ax, data):
        """高效更新买卖点标记"""
        if self.signals is None:
            return
        
        # 清除旧的标记
        if self.signal_scatters['buy'] is not None:
            self.signal_scatters['buy'].remove()
        if self.signal_scatters['sell'] is not None:
            self.signal_scatters['sell'].remove()
        
        # 获取视图数据中的信号
        view_signals = self.signals.loc[data.index]
        
        buy_x = []
        buy_y = []
        sell_x = []
        sell_y = []
        
        # 只在信号变化的那一天标记
        for i in range(1, len(data)):
            current_date = data.index[i]
            prev_date = data.index[i-1]
            
            if current_date not in view_signals.index or prev_date not in view_signals.index:
                continue
            
            current_signal = view_signals.loc[current_date, 'signal']
            prev_signal = view_signals.loc[prev_date, 'signal']
            
            if current_signal == 1 and prev_signal == 0:
                buy_x.append(i)
                buy_y.append(data['Low'].iloc[i] * 0.98)
            elif current_signal == -1 and prev_signal == 1:
                sell_x.append(i)
                sell_y.append(data['High'].iloc[i] * 1.02)
        
        # 批量绘制标记
        if buy_x:
            self.signal_scatters['buy'] = ax.scatter(buy_x, buy_y, marker='^', s=200, 
                                                   color='red', zorder=5)
        if sell_x:
            self.signal_scatters['sell'] = ax.scatter(sell_x, sell_y, marker='v', s=200, 
                                                    color='green', zorder=5)
    
    def _set_date_ticks(self, ax, dates):
        """设置x轴时间标签"""
        if len(dates) == 0:
            return
        
        # 根据数据量决定标签间隔
        n_ticks = min(10, max(5, len(dates) // 10))
        tick_indices = np.linspace(0, len(dates) - 1, n_ticks, dtype=int)
        
        # 设置刻度位置和标签
        ax.set_xticks(tick_indices)
        tick_labels = [dates[i].strftime('%Y-%m-%d') for i in tick_indices]
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
        
        # 设置x轴标签
        ax.set_xlabel('日期', fontsize=10)
    
    def _create_slider(self):
        """创建滑动条"""
        # 滑动条位置和大小
        slider_ax = plt.axes([0.15, 0.05, 0.7, 0.03], facecolor='lightgoldenrodyellow')
        
        # 计算滑动条范围（避免low和high相同）
        slider_min = 0
        slider_max = max(1, len(self.data) - self.window_size)
        
        # 创建滑动条
        self.slider = Slider(
            slider_ax,
            '日期范围',
            slider_min,
            slider_max,
            valinit=self.current_pos,
            valstep=1
        )
        
        # 设置滑动条回调
        self.slider.on_changed(self._on_slider_change)
        
        # 设置滑动条标签格式
        self.slider.valtext.set_fontsize(9)
    
    def _on_slider_change(self, val):
        """滑动条变化回调"""
        self.current_pos = int(val)
        self._update_plot()
    
    def _setup_events(self):
        """设置鼠标事件"""
        self.fig.canvas.mpl_connect('button_press_event', self._on_press)
        self.fig.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.current_tooltip_idx = None
    
    def _on_press(self, event):
        """鼠标按下事件"""
        if event.inaxes == self.axes[0]:
            self.is_dragging = True
            self.last_x = event.xdata
            
            # 点击K线显示信息
            view_idx = int(round(event.xdata))
            if 0 <= view_idx < len(self.view_data):
                self._show_tooltip(event, view_idx)
    
    def _on_release(self, event):
        """鼠标释放事件"""
        self.is_dragging = False
    
    def _on_motion(self, event):
        """鼠标移动事件"""
        if self.is_dragging and event.inaxes == self.axes[0] and self.last_x is not None:
            dx = event.xdata - self.last_x
            
            # 只有移动超过阈值才更新
            if abs(dx) < self.drag_threshold:
                return
            
            self.current_pos -= int(dx)
            self.current_pos = max(0, min(len(self.data) - self.window_size, self.current_pos))
            self.last_x = event.xdata
            
            # 节流：如果位置没有变化，不更新
            if self.current_pos == self.last_update_pos:
                return
            self.last_update_pos = self.current_pos
            
            # 更新滑动条位置
            if self.slider:
                self.slider.eventson = False
                self.slider.set_val(self.current_pos)
                self.slider.eventson = True
            self._update_plot()
            # 拖动时不显示tooltip
            return
        
        # 鼠标悬停显示信息（拖动时不显示）
        if event.inaxes == self.axes[0] and not self.is_dragging:
            view_idx = int(round(event.xdata))
            if 0 <= view_idx < len(self.view_data):
                self._show_tooltip(event, view_idx)
    
    def _on_scroll(self, event):
        """鼠标滚轮事件"""
        if event.inaxes == self.axes[0]:
            if event.button == 'up':
                self.window_size = max(20, self.window_size - 5)
            else:
                self.window_size = min(len(self.data), self.window_size + 5)
            self.current_pos = max(0, min(len(self.data) - self.window_size, self.current_pos))
            # 更新滑动条位置
            if self.slider:
                self.slider.eventson = False
                self.slider.set_val(self.current_pos)
                self.slider.eventson = True
            self._update_plot()
    
    def _show_tooltip(self, event, view_idx):
        """显示提示信息"""
        # 如果索引没有变化，不重复更新
        if self.current_tooltip_idx == view_idx:
            return
        self.current_tooltip_idx = view_idx
        
        # 从视图数据中获取对应的数据
        row = self.view_data.iloc[view_idx]
        date_str = self.view_data.index[view_idx].strftime('%Y-%m-%d')
        
        # 计算涨跌
        change = row['Close'] - row['Open']
        change_pct = (change / row['Open']) * 100
        change_str = f"+{change:.2f} (+{change_pct:.2f}%)" if change >= 0 else f"{change:.2f} ({change_pct:.2f}%)"
        
        # 计算BOLL（使用视图数据）
        data_subset = self.view_data.iloc[:view_idx+1]
        bb_middle = data_subset['Close'].rolling(window=20).mean().iloc[-1]
        bb_std = data_subset['Close'].rolling(window=20).std().iloc[-1]
        bb_upper = bb_middle + bb_std * 2
        bb_lower = bb_middle - bb_std * 2
        
        # 计算RSI（使用视图数据）
        delta = data_subset['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs)) if not pd.isna(rs) else 50
        
        tooltip_text = (
            f"日期: {date_str}\n"
            f"开盘: {row['Open']:.2f}\n"
            f"最高: {row['High']:.2f}\n"
            f"最低: {row['Low']:.2f}\n"
            f"收盘: {row['Close']:.2f}\n"
            f"涨跌: {change_str}\n"
            f"成交量: {row['Volume']:,.0f}\n"
            f"---\n"
            f"BOLL上轨: {bb_upper:.2f}\n"
            f"BOLL中轨: {bb_middle:.2f}\n"
            f"BOLL下轨: {bb_lower:.2f}\n"
            f"---\n"
            f"RSI: {rsi:.2f}"
        )
        
        # 清除之前的标注
        for artist in self.axes[0].texts:
            if hasattr(artist, 'is_tooltip'):
                artist.remove()
        
        # 获取当前显示范围
        x_min, x_max = self.axes[0].get_xlim()
        y_min, y_max = self.axes[0].get_ylim()
        
        # 根据收盘价位置调整提示框位置
        x_pos = view_idx
        y_pos = row['Close']
        
        # 计算提示框应该显示的位置
        # 估算提示框大小（基于文本行数）
        text_lines = tooltip_text.split('\n')
        tooltip_height = len(text_lines) * 12  # 每行约12像素
        tooltip_width = 150  # 估算宽度
        
        # 转换为数据坐标
        x_range = x_max - x_min
        y_range = y_max - y_min
        
        # 计算相对位置（0-1之间）
        x_ratio = (x_pos - x_min) / x_range if x_range > 0 else 0.5
        y_ratio = (y_pos - y_min) / y_range if y_range > 0 else 0.5
        
        # 智能调整偏移量
        x_offset = 10
        y_offset = 10
        
        # 如果在右侧，提示框显示在左侧
        if x_ratio > 0.7:
            x_offset = -160
        
        # 如果在上方，提示框显示在下方
        if y_ratio > 0.7:
            y_offset = -tooltip_height - 10
        
        # 如果在下方，提示框显示在上方
        elif y_ratio < 0.3:
            y_offset = 20
        
        annot = self.axes[0].annotate(
            tooltip_text,
            xy=(x_pos, y_pos),
            xytext=(x_offset, y_offset),
            textcoords='offset points',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.95, edgecolor='brown', linewidth=1.5),
            fontsize=8.5,
            family='Microsoft YaHei',
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='brown', lw=1)
        )
        annot.is_tooltip = True
        self.fig.canvas.draw_idle()
    
    def show(self):
        """显示图表"""
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='交互式K线图查看器 - 支持鼠标拖拽和缩放')
    parser.add_argument(
        '-s', '--symbol',
        type=str,
        default='AAPL',
        help='股票代码（默认：AAPL）'
    )
    parser.add_argument(
        '-p', '--period',
        type=str,
        default='1y',
        help='数据周期：1y=1年，2y=2年，5y=5年（默认：1y）'
    )
    parser.add_argument(
        '-t', '--timeframe',
        type=str,
        default='1d',
        choices=['1d', '1w', '1m'],
        help='时间周期：1d=日线，1w=周线，1m=月线（默认：1d）'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='不使用缓存，强制从网络获取'
    )
    parser.add_argument(
        '--signals',
        type=str,
        help='信号文件路径（CSV格式，包含signal列）'
    )
    
    args = parser.parse_args()
    
    timeframe_names = {
        '1d': '日线',
        '1w': '周线',
        '1m': '月线'
    }
    
    print("=" * 60)
    print("交互式K线图查看器")
    print("=" * 60)
    print(f"\n股票代码: {args.symbol}")
    print(f"时间周期: {timeframe_names[args.timeframe]} ({args.timeframe})")
    print(f"数据周期: {args.period}")
    print(f"使用缓存: {'否' if args.no_cache else '是'}")
    
    # 初始化
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=1,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 获取数据
    print(f"\n正在获取 {args.symbol} 的数据...")
    use_cache = not args.no_cache
    daily_data = fetcher.fetch_stock_data(
        args.symbol,
        period=args.period,
        use_cache=use_cache
    )
    
    # 转换为指定周期
    if args.timeframe == '1d':
        data = daily_data
        print(f"✓ 使用日线数据: {len(data)} 条")
    elif args.timeframe == '1w':
        print(f"\n正在转换为周线数据...")
        data = fetcher.resample_data(daily_data, timeframe='1w')
        print(f"✓ 周线数据: {len(data)} 条")
    elif args.timeframe == '1m':
        print(f"\n正在转换为月线数据...")
        data = fetcher.resample_data(daily_data, timeframe='1m')
        print(f"✓ 月线数据: {len(data)} 条")
    
    print(f"✓ 时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
    print(f"✓ 最新收盘价: ${data['Close'].iloc[-1]:.2f}")
    print(f"✓ 最高价: ${data['High'].max():.2f}")
    print(f"✓ 最低价: ${data['Low'].min():.2f}")
    
    # 加载信号文件
    signals = None
    if args.signals:
        print(f"\n正在加载信号文件: {args.signals}")
        try:
            signals = pd.read_csv(args.signals, index_col=0, parse_dates=True)
            signals.index = pd.to_datetime(signals.index).tz_localize(None)
            print(f"✓ 信号文件加载成功: {len(signals)} 条")
            
            # 确保信号数据与数据对齐
            common_index = data.index.intersection(signals.index)
            if len(common_index) > 0:
                signals = signals.loc[common_index]
                print(f"✓ 信号数据对齐: {len(signals)} 条")
            else:
                print("⚠️  信号数据与价格数据没有交集")
                signals = None
        except Exception as e:
            print(f"✗ 信号文件加载失败: {e}")
            signals = None
    
    # 创建交互式查看器
    print(f"\n正在创建交互式图表...")
    print(f"\n操作说明：")
    print(f"  - 鼠标拖拽：左右移动K线")
    print(f"  - 鼠标滚轮：缩放K线数量")
    print(f"  - 鼠标悬停：查看详细信息")
    
    viewer = InteractiveKLineViewer(data, title=f'{args.symbol} {timeframe_names[args.timeframe]}交互式K线图', signals=signals)
    viewer.show()


if __name__ == '__main__':
    main()
