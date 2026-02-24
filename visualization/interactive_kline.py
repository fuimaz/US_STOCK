import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.lines import Line2D
import mplfinance as mpf
from data.data_fetcher import DataFetcher
from visualization.kline_plotter import KLinePlotter
import argparse


class InteractiveKLineViewer:
    def __init__(self, data: pd.DataFrame, title: str = "K绾垮浘", signals: pd.DataFrame = None):
        """
        浜や簰寮廗绾垮浘鏌ョ湅鍣?        
        Args:
            data: 鍖呭惈OHLCV鏁版嵁鐨凞ataFrame
            title: 鍥捐〃鏍囬
            signals: 鍖呭惈涔板崠淇″彿鐨凞ataFrame锛堝彲閫夛級
        """
        self.data = data
        self.title = title
        self.signals = signals
        self.window_size = len(data)  # 榛樿鏄剧ず鍏ㄩ儴K绾匡紙鍏ㄨ鍥撅級
        self.current_pos = 0  # 浠庡紑濮嬩綅缃樉绀?        self.is_dragging = False
        self.last_x = None
        self.view_data = None  # 褰撳墠瑙嗗浘鏁版嵁
        self.slider = None  # 婊戝姩鏉℃帶浠?        self.last_update_pos = -1  # 涓婃鏇存柊鐨勪綅缃紙鐢ㄤ簬鑺傛祦锛?        self.drag_threshold = 5  # 鎷栧姩闃堝€硷紙鍍忕礌锛夛紝鍙湁绉诲姩瓒呰繃杩欎釜璺濈鎵嶆洿鏂?        self.last_xaxis_range = None  # 涓婃x杞磋寖鍥达紝閬垮厤閲嶅鏇存柊鏍囩
        
        # 鍥捐〃瀵硅薄寮曠敤锛堢敤浜庢洿鏂拌€屼笉鏄噸缁橈級
        self.candle_collection = None  # 浣跨敤PatchCollection鎵归噺缁樺埗K绾垮疄浣?        self.wick_collection = None  # 浣跨敤LineCollection鎵归噺缁樺埗褰辩嚎
        self.bb_upper_line = None
        self.bb_middle_line = None
        self.bb_lower_line = None
        self.volume_collection = None  # 浣跨敤PatchCollection鎵归噺缁樺埗鎴愪氦閲?        self.rsi_line = None
        self.signal_scatters = {'buy': None, 'sell': None}
        
        # 棰勮绠楁墍鏈夋妧鏈寚鏍?        self._precompute_indicators()
        
        self._setup_chinese_font()
        self._create_plot()
        self._setup_events()
        
    def _precompute_indicators(self):
        """棰勮绠楁墍鏈夋妧鏈寚鏍囷紝閬垮厤閲嶅璁＄畻"""
        # 璁＄畻甯冩灄甯?        self.data['BB_Middle'] = self.data['Close'].rolling(window=20).mean()
        self.data['BB_Std'] = self.data['Close'].rolling(window=20).std()
        self.data['BB_Upper'] = self.data['BB_Middle'] + self.data['BB_Std'] * 2
        self.data['BB_Lower'] = self.data['BB_Middle'] - self.data['BB_Std'] * 2
        
        # 璁＄畻RSI
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        
        # 棰勮绠桲绾块鑹?        self.data['Color'] = np.where(self.data['Close'] >= self.data['Open'], 'r', 'g')
        
    def _setup_chinese_font(self):
        """璁剧疆涓枃瀛椾綋"""
        try:
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
        except:
            pass
    
    def _create_plot(self):
        """鍒涘缓鍥捐〃"""
        self.fig, self.axes = plt.subplots(3, 1, figsize=(16, 12), 
                                          gridspec_kw={'height_ratios': [3, 1, 1]})
        self.fig.suptitle(self.title, fontsize=14, fontweight='bold')
        
        # 璋冩暣甯冨眬涓烘粦鍔ㄦ潯鐣欏嚭绌洪棿
        plt.subplots_adjust(left=0.08, right=0.92, top=0.93, bottom=0.15, hspace=0.4)
        
        # 鍒涘缓婊戝姩鏉?        self._create_slider()
        
        self._update_plot()
    
    def _update_plot(self):
        """鏇存柊鍥捐〃鍐呭"""
        start_idx = max(0, self.current_pos)
        end_idx = min(len(self.data), self.current_pos + self.window_size)
        self.view_data = self.data.iloc[start_idx:end_idx]
        
        # 浣跨敤楂樻晥鏂瑰紡鏇存柊鍥捐〃
        self._update_candles(self.axes[0], self.view_data, start_idx)
        self._update_volume(self.axes[1], self.view_data)
        self._update_rsi(self.axes[2], self.view_data)
        
        # 鍙湪x杞磋寖鍥村彉鍖栨椂鏇存柊鏍囩
        current_xaxis_range = (start_idx, end_idx)
        if self.last_xaxis_range != current_xaxis_range:
            dates = pd.to_datetime(self.view_data.index)
            self._set_date_ticks(self.axes[0], dates)
            self._set_date_ticks(self.axes[1], dates)
            self._set_date_ticks(self.axes[2], dates)
            self.last_xaxis_range = current_xaxis_range
        
        # 鏇存柊淇℃伅鎻愮ず
        info_text = f"鏄剧ず鑼冨洿: {len(self.view_data)} 鏍筀绾縗n"
        info_text += f"鎬绘暟鎹? {len(self.data)} 鏍筡n"
        info_text += f"褰撳墠浣嶇疆: {start_idx} - {end_idx-1}"
        
        # 绉婚櫎鏃х殑淇℃伅鏂囨湰
        for text in self.axes[0].texts:
            if hasattr(text, '_info_text'):
                text.remove()
        
        # 娣诲姞鏂扮殑淇℃伅鏂囨湰
        text_obj = self.axes[0].text(0.02, 0.98, info_text, transform=self.axes[0].transAxes,
                                     fontsize=9, verticalalignment='top',
                                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        text_obj._info_text = True
        
        self.fig.canvas.draw_idle()
    
    def _update_candles(self, ax, data, start_idx):
        """楂樻晥鏇存柊K绾垮浘 - 浣跨敤LineCollection鍜孭atchCollection鎵归噺缁樺埗"""
        # 娓呴櫎鏃х殑K绾垮璞?        if self.candle_collection is not None:
            self.candle_collection.remove()
        if self.wick_collection is not None:
            self.wick_collection.remove()
        
        if len(data) == 0:
            return
        
        # 浣跨敤鍚戦噺鍖栨搷浣滄壒閲忓垱寤篕绾?        n = len(data)
        opens = data['Open'].values
        highs = data['High'].values
        lows = data['Low'].values
        closes = data['Close'].values
        colors = data['Color'].values
        
        # 鎵归噺鍒涘缓褰辩嚎 - 浣跨敤LineCollection
        segments = []
        wick_colors = []
        for i in range(n):
            segments.append([(i, lows[i]), (i, highs[i])])
            wick_colors.append(colors[i])
        
        self.wick_collection = LineCollection(segments, colors=wick_colors, linewidths=1)
        ax.add_collection(self.wick_collection)
        
        # 鎵归噺鍒涘缓瀹炰綋 - 浣跨敤PatchCollection
        heights = np.abs(closes - opens)
        bottoms = np.minimum(opens, closes)
        
        patches = []
        for i in range(n):
            rect = Rectangle((i - 0.3, bottoms[i]), 0.6, heights[i])
            patches.append(rect)
        
        self.candle_collection = PatchCollection(patches, facecolors=colors, edgecolors=colors, alpha=0.8)
        ax.add_collection(self.candle_collection)
        
        ax.set_xlim(-0.5, n - 0.5)
        ax.set_ylabel('浠锋牸')
        ax.grid(True, alpha=0.3)
        
        # 鏇存柊甯冩灄甯?        bb_upper = data['BB_Upper'].values
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
        
        # 鏇存柊涔板崠鐐规爣璁?        self._update_signals(ax, data)
    
    def _update_volume(self, ax, data):
        """楂樻晥鏇存柊鎴愪氦閲忓浘 - 浣跨敤PatchCollection鎵归噺缁樺埗"""
        if self.volume_collection is not None:
            self.volume_collection.remove()
        
        if len(data) == 0:
            return
        
        colors = data['Color'].values
        x = np.arange(len(data))
        volumes = data['Volume'].values
        bar_width = 0.6
        
        # 鎵归噺鍒涘缓鎴愪氦閲忔煴鐘跺浘
        patches = []
        for i in range(len(data)):
            rect = Rectangle((i - bar_width/2, 0), bar_width, volumes[i])
            patches.append(rect)
        
        self.volume_collection = PatchCollection(patches, facecolors=colors, alpha=0.6)
        ax.add_collection(self.volume_collection)
        
        ax.set_xlim(-0.5, len(data) - 0.5)
        ax.set_ylabel('鎴愪氦閲?)
        ax.grid(True, alpha=0.3)
    
    def _update_rsi(self, ax, data):
        """楂樻晥鏇存柊RSI鍥?""
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
        
        # 娣诲姞鍙傝€冪嚎锛堝彧娣诲姞涓€娆★級
        if not hasattr(ax, '_ref_lines_added'):
            ax.axhline(y=70, color='r', linestyle='--', alpha=0.5)
            ax.axhline(y=30, color='g', linestyle='--', alpha=0.5)
            ax._ref_lines_added = True
    
    def _update_signals(self, ax, data):
        """楂樻晥鏇存柊涔板崠鐐规爣璁?""
        if self.signals is None:
            return
        
        # 娓呴櫎鏃х殑鏍囪
        if self.signal_scatters['buy'] is not None:
            self.signal_scatters['buy'].remove()
        if self.signal_scatters['sell'] is not None:
            self.signal_scatters['sell'].remove()
        
        # 鑾峰彇瑙嗗浘鏁版嵁涓殑淇″彿
        view_signals = self.signals.loc[data.index]
        
        buy_x = []
        buy_y = []
        sell_x = []
        sell_y = []
        
        # 鍙湪淇″彿鍙樺寲鐨勯偅涓€澶╂爣璁?        for i in range(1, len(data)):
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
        
        # 鎵归噺缁樺埗鏍囪
        if buy_x:
            self.signal_scatters['buy'] = ax.scatter(buy_x, buy_y, marker='^', s=200, 
                                                   color='red', zorder=5)
        if sell_x:
            self.signal_scatters['sell'] = ax.scatter(sell_x, sell_y, marker='v', s=200, 
                                                    color='green', zorder=5)
    
    def _set_date_ticks(self, ax, dates):
        """璁剧疆x杞存椂闂存爣绛?""
        if len(dates) == 0:
            return
        
        # 鏍规嵁鏁版嵁閲忓喅瀹氭爣绛鹃棿闅?        n_ticks = min(10, max(5, len(dates) // 10))
        tick_indices = np.linspace(0, len(dates) - 1, n_ticks, dtype=int)
        
        # 璁剧疆鍒诲害浣嶇疆鍜屾爣绛?        ax.set_xticks(tick_indices)
        tick_labels = [dates[i].strftime('%Y-%m-%d') for i in tick_indices]
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
        
        # 璁剧疆x杞存爣绛?        ax.set_xlabel('鏃ユ湡', fontsize=10)
    
    def _create_slider(self):
        """鍒涘缓婊戝姩鏉?""
        # 婊戝姩鏉′綅缃拰澶у皬
        slider_ax = plt.axes([0.15, 0.05, 0.7, 0.03], facecolor='lightgoldenrodyellow')
        
        # 璁＄畻婊戝姩鏉¤寖鍥达紙閬垮厤low鍜宧igh鐩稿悓锛?        slider_min = 0
        slider_max = max(1, len(self.data) - self.window_size)
        
        # 鍒涘缓婊戝姩鏉?        self.slider = Slider(
            slider_ax,
            '鏃ユ湡鑼冨洿',
            slider_min,
            slider_max,
            valinit=self.current_pos,
            valstep=1
        )
        
        # 璁剧疆婊戝姩鏉″洖璋?        self.slider.on_changed(self._on_slider_change)
        
        # 璁剧疆婊戝姩鏉℃爣绛炬牸寮?        self.slider.valtext.set_fontsize(9)
    
    def _on_slider_change(self, val):
        """婊戝姩鏉″彉鍖栧洖璋?""
        self.current_pos = int(val)
        self._update_plot()
    
    def _setup_events(self):
        """璁剧疆榧犳爣浜嬩欢"""
        self.fig.canvas.mpl_connect('button_press_event', self._on_press)
        self.fig.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.current_tooltip_idx = None
    
    def _on_press(self, event):
        """榧犳爣鎸変笅浜嬩欢"""
        if event.inaxes == self.axes[0]:
            self.is_dragging = True
            self.last_x = event.xdata
            
            # 鐐瑰嚮K绾挎樉绀轰俊鎭?            view_idx = int(round(event.xdata))
            if 0 <= view_idx < len(self.view_data):
                self._show_tooltip(event, view_idx)
    
    def _on_release(self, event):
        """榧犳爣閲婃斁浜嬩欢"""
        self.is_dragging = False
    
    def _on_motion(self, event):
        """榧犳爣绉诲姩浜嬩欢"""
        if self.is_dragging and event.inaxes == self.axes[0] and self.last_x is not None:
            dx = event.xdata - self.last_x
            
            # 鍙湁绉诲姩瓒呰繃闃堝€兼墠鏇存柊
            if abs(dx) < self.drag_threshold:
                return
            
            self.current_pos -= int(dx)
            self.current_pos = max(0, min(len(self.data) - self.window_size, self.current_pos))
            self.last_x = event.xdata
            
            # 鑺傛祦锛氬鏋滀綅缃病鏈夊彉鍖栵紝涓嶆洿鏂?            if self.current_pos == self.last_update_pos:
                return
            self.last_update_pos = self.current_pos
            
            # 鏇存柊婊戝姩鏉′綅缃?            if self.slider:
                self.slider.eventson = False
                self.slider.set_val(self.current_pos)
                self.slider.eventson = True
            self._update_plot()
            # 鎷栧姩鏃朵笉鏄剧ずtooltip
            return
        
        # 榧犳爣鎮仠鏄剧ず淇℃伅锛堟嫋鍔ㄦ椂涓嶆樉绀猴級
        if event.inaxes == self.axes[0] and not self.is_dragging:
            view_idx = int(round(event.xdata))
            if 0 <= view_idx < len(self.view_data):
                self._show_tooltip(event, view_idx)
    
    def _on_scroll(self, event):
        """榧犳爣婊氳疆浜嬩欢"""
        if event.inaxes == self.axes[0]:
            if event.button == 'up':
                self.window_size = max(20, self.window_size - 5)
            else:
                self.window_size = min(len(self.data), self.window_size + 5)
            self.current_pos = max(0, min(len(self.data) - self.window_size, self.current_pos))
            # 鏇存柊婊戝姩鏉′綅缃?            if self.slider:
                self.slider.eventson = False
                self.slider.set_val(self.current_pos)
                self.slider.eventson = True
            self._update_plot()
    
    def _show_tooltip(self, event, view_idx):
        """鏄剧ず鎻愮ず淇℃伅"""
        # 濡傛灉绱㈠紩娌℃湁鍙樺寲锛屼笉閲嶅鏇存柊
        if self.current_tooltip_idx == view_idx:
            return
        self.current_tooltip_idx = view_idx
        
        # 浠庤鍥炬暟鎹腑鑾峰彇瀵瑰簲鐨勬暟鎹?        row = self.view_data.iloc[view_idx]
        date_str = self.view_data.index[view_idx].strftime('%Y-%m-%d')
        
        # 璁＄畻娑ㄨ穼
        change = row['Close'] - row['Open']
        change_pct = (change / row['Open']) * 100
        change_str = f"+{change:.2f} (+{change_pct:.2f}%)" if change >= 0 else f"{change:.2f} ({change_pct:.2f}%)"
        
        # 璁＄畻BOLL锛堜娇鐢ㄨ鍥炬暟鎹級
        data_subset = self.view_data.iloc[:view_idx+1]
        bb_middle = data_subset['Close'].rolling(window=20).mean().iloc[-1]
        bb_std = data_subset['Close'].rolling(window=20).std().iloc[-1]
        bb_upper = bb_middle + bb_std * 2
        bb_lower = bb_middle - bb_std * 2
        
        # 璁＄畻RSI锛堜娇鐢ㄨ鍥炬暟鎹級
        delta = data_subset['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean().iloc[-1]
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs)) if not pd.isna(rs) else 50
        
        tooltip_text = (
            f"鏃ユ湡: {date_str}\n"
            f"寮€鐩? {row['Open']:.2f}\n"
            f"鏈€楂? {row['High']:.2f}\n"
            f"鏈€浣? {row['Low']:.2f}\n"
            f"鏀剁洏: {row['Close']:.2f}\n"
            f"娑ㄨ穼: {change_str}\n"
            f"鎴愪氦閲? {row['Volume']:,.0f}\n"
            f"---\n"
            f"BOLL涓婅建: {bb_upper:.2f}\n"
            f"BOLL涓建: {bb_middle:.2f}\n"
            f"BOLL涓嬭建: {bb_lower:.2f}\n"
            f"---\n"
            f"RSI: {rsi:.2f}"
        )
        
        # 娓呴櫎涔嬪墠鐨勬爣娉?        for artist in self.axes[0].texts:
            if hasattr(artist, 'is_tooltip'):
                artist.remove()
        
        # 鑾峰彇褰撳墠鏄剧ず鑼冨洿
        x_min, x_max = self.axes[0].get_xlim()
        y_min, y_max = self.axes[0].get_ylim()
        
        # 鏍规嵁鏀剁洏浠蜂綅缃皟鏁存彁绀烘浣嶇疆
        x_pos = view_idx
        y_pos = row['Close']
        
        # 璁＄畻鎻愮ず妗嗗簲璇ユ樉绀虹殑浣嶇疆
        # 浼扮畻鎻愮ず妗嗗ぇ灏忥紙鍩轰簬鏂囨湰琛屾暟锛?        text_lines = tooltip_text.split('\n')
        tooltip_height = len(text_lines) * 12  # 姣忚绾?2鍍忕礌
        tooltip_width = 150  # 浼扮畻瀹藉害
        
        # 杞崲涓烘暟鎹潗鏍?        x_range = x_max - x_min
        y_range = y_max - y_min
        
        # 璁＄畻鐩稿浣嶇疆锛?-1涔嬮棿锛?        x_ratio = (x_pos - x_min) / x_range if x_range > 0 else 0.5
        y_ratio = (y_pos - y_min) / y_range if y_range > 0 else 0.5
        
        # 鏅鸿兘璋冩暣鍋忕Щ閲?        x_offset = 10
        y_offset = 10
        
        # 濡傛灉鍦ㄥ彸渚э紝鎻愮ず妗嗘樉绀哄湪宸︿晶
        if x_ratio > 0.7:
            x_offset = -160
        
        # 濡傛灉鍦ㄤ笂鏂癸紝鎻愮ず妗嗘樉绀哄湪涓嬫柟
        if y_ratio > 0.7:
            y_offset = -tooltip_height - 10
        
        # 濡傛灉鍦ㄤ笅鏂癸紝鎻愮ず妗嗘樉绀哄湪涓婃柟
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
        """鏄剧ず鍥捐〃"""
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='浜や簰寮廗绾垮浘鏌ョ湅鍣?- 鏀寔榧犳爣鎷栨嫿鍜岀缉鏀?)
    parser.add_argument(
        '-s', '--symbol',
        type=str,
        default='AAPL',
        help='鑲＄エ浠ｇ爜锛堥粯璁わ細AAPL锛?
    )
    parser.add_argument(
        '-p', '--period',
        type=str,
        default='1y',
        help='鏁版嵁鍛ㄦ湡锛?y=1骞达紝2y=2骞达紝5y=5骞达紙榛樿锛?y锛?
    )
    parser.add_argument(
        '-t', '--timeframe',
        type=str,
        default='1d',
        choices=['1d', '1w', '1m'],
        help='鏃堕棿鍛ㄦ湡锛?d=鏃ョ嚎锛?w=鍛ㄧ嚎锛?m=鏈堢嚎锛堥粯璁わ細1d锛?
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='涓嶄娇鐢ㄧ紦瀛橈紝寮哄埗浠庣綉缁滆幏鍙?
    )
    parser.add_argument(
        '--signals',
        type=str,
        help='淇″彿鏂囦欢璺緞锛圕SV鏍煎紡锛屽寘鍚玸ignal鍒楋級'
    )
    
    args = parser.parse_args()
    
    timeframe_names = {
        '1d': '鏃ョ嚎',
        '1w': '鍛ㄧ嚎',
        '1m': '鏈堢嚎'
    }
    
    print("=" * 60)
    print("浜や簰寮廗绾垮浘鏌ョ湅鍣?)
    print("=" * 60)
    print(f"\n鑲＄エ浠ｇ爜: {args.symbol}")
    print(f"鏃堕棿鍛ㄦ湡: {timeframe_names[args.timeframe]} ({args.timeframe})")
    print(f"鏁版嵁鍛ㄦ湡: {args.period}")
    print(f"浣跨敤缂撳瓨: {'鍚? if args.no_cache else '鏄?}")
    
    # 鍒濆鍖?    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=1,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 鑾峰彇鏁版嵁
    print(f"\n姝ｅ湪鑾峰彇 {args.symbol} 鐨勬暟鎹?..")
    use_cache = not args.no_cache
    daily_data = fetcher.fetch_stock_data(
        args.symbol,
        period=args.period,
        use_cache=use_cache
    )
    
    # 杞崲涓烘寚瀹氬懆鏈?    if args.timeframe == '1d':
        data = daily_data
        print(f"鉁?浣跨敤鏃ョ嚎鏁版嵁: {len(data)} 鏉?)
    elif args.timeframe == '1w':
        print(f"\n姝ｅ湪杞崲涓哄懆绾挎暟鎹?..")
        data = fetcher.resample_data(daily_data, timeframe='1w')
        print(f"鉁?鍛ㄧ嚎鏁版嵁: {len(data)} 鏉?)
    elif args.timeframe == '1m':
        print(f"\n姝ｅ湪杞崲涓烘湀绾挎暟鎹?..")
        data = fetcher.resample_data(daily_data, timeframe='1m')
        print(f"鉁?鏈堢嚎鏁版嵁: {len(data)} 鏉?)
    
    print(f"鉁?鏃堕棿鑼冨洿: {data.index[0].date()} 鍒?{data.index[-1].date()}")
    print(f"鉁?鏈€鏂版敹鐩樹环: ${data['Close'].iloc[-1]:.2f}")
    print(f"鉁?鏈€楂樹环: ${data['High'].max():.2f}")
    print(f"鉁?鏈€浣庝环: ${data['Low'].min():.2f}")
    
    # 鍔犺浇淇″彿鏂囦欢
    signals = None
    if args.signals:
        print(f"\n姝ｅ湪鍔犺浇淇″彿鏂囦欢: {args.signals}")
        try:
            signals = pd.read_csv(args.signals, index_col=0, parse_dates=True)
            signals.index = pd.to_datetime(signals.index).tz_localize(None)
            print(f"鉁?淇″彿鏂囦欢鍔犺浇鎴愬姛: {len(signals)} 鏉?)
            
            # 纭繚淇″彿鏁版嵁涓庢暟鎹榻?            common_index = data.index.intersection(signals.index)
            if len(common_index) > 0:
                signals = signals.loc[common_index]
                print(f"鉁?淇″彿鏁版嵁瀵归綈: {len(signals)} 鏉?)
            else:
                print("鈿狅笍  淇″彿鏁版嵁涓庝环鏍兼暟鎹病鏈変氦闆?)
                signals = None
        except Exception as e:
            print(f"鉁?淇″彿鏂囦欢鍔犺浇澶辫触: {e}")
            signals = None
    
    # 鍒涘缓浜や簰寮忔煡鐪嬪櫒
    print(f"\n姝ｅ湪鍒涘缓浜や簰寮忓浘琛?..")
    print(f"\n鎿嶄綔璇存槑锛?)
    print(f"  - 榧犳爣鎷栨嫿锛氬乏鍙崇Щ鍔↘绾?)
    print(f"  - 榧犳爣婊氳疆锛氱缉鏀綤绾挎暟閲?)
    print(f"  - 榧犳爣鎮仠锛氭煡鐪嬭缁嗕俊鎭?)
    
    viewer = InteractiveKLineViewer(data, title=f'{args.symbol} {timeframe_names[args.timeframe]}浜や簰寮廗绾垮浘', signals=signals)
    viewer.show()


if __name__ == '__main__':
    main()


