import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import time
import os
import pickle


class DataFetcher:
    def __init__(self, cache_dir: str = 'data_cache', cache_days: int = 1, proxy: Optional[str] = None, retry_count: int = 3, retry_delay: float = 2.0):
        """
        初始化数据获取器
        
        Args:
            cache_dir: 缓存目录
            cache_days: 缓存有效期（天）
            proxy: 代理地址，如 'http://127.0.0.1:7890'
            retry_count: 重试次数
            retry_delay: 重试延迟（秒）
        """
        self.cache_dir = cache_dir
        self.cache_days = cache_days
        self.proxy = proxy
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _get_cache_path(self, symbol: str, period: str, interval: str, adjust: str = "auto") -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f'{symbol}_{period}_{interval}_{adjust}.csv')
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """检查缓存是否有效"""
        if not os.path.exists(cache_path):
            return False
        
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        age = datetime.now() - cache_time
        
        return age.days < self.cache_days
    
    def _load_cache(self, cache_path: str) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        try:
            data = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            print(f"  ✓ 从缓存加载数据")
            return data
        except Exception as e:
            print(f"  ✗ 加载缓存失败: {e}")
            return None
    
    def _save_cache(self, data: pd.DataFrame, cache_path: str):
        """保存数据到缓存"""
        try:
            data.to_csv(cache_path)
            print(f"  ✓ 数据已缓存到本地")
        except Exception as e:
            print(f"  ✗ 保存缓存失败: {e}")
    
    def _fetch_from_alpha_vantage(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """从 Alpha Vantage 获取股票数据"""
        try:
            from alpha_vantage.timeseries import TimeSeries
            import os
            
            api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', 'demo')
            
            ts = TimeSeries(key=api_key, output_format='pandas')
            
            if period == '1y':
                data, meta_data = ts.get_daily(symbol=symbol, outputsize='full')
            else:
                data, meta_data = ts.get_daily(symbol=symbol, outputsize='compact')
            
            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            data.index = pd.to_datetime(data.index)
            data.index.name = 'datetime'
            
            data = data.sort_index()
            
            if period == '1y':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                data = data[data.index >= start_date]
            
            return data
        except ImportError:
            print("  ✗ 需要安装 alpha_vantage: python -m pip install alpha_vantage")
            raise
        except Exception as e:
            print(f"  ✗ Alpha Vantage 获取失败: {e}")
            raise
    
    def _fetch_from_polygon(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """从 Polygon.io 获取股票数据"""
        try:
            import os
            import requests
            
            api_key = os.environ.get('POLYGON_API_KEY', '')
            
            if not api_key:
                raise ValueError("需要设置 POLYGON_API_KEY 环境变量")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}?apiKey={api_key}"
            
            response = requests.get(url)
            response.raise_for_status()
            
            result = response.json()
            
            if 'results' not in result or not result['results']:
                raise ValueError(f"无法获取股票 {symbol} 的数据")
            
            data_list = []
            for item in result['results']:
                timestamp = item['t'] // 1000000000
                date = datetime.fromtimestamp(timestamp)
                data_list.append({
                    'Open': item['o'],
                    'High': item['h'],
                    'Low': item['l'],
                    'Close': item['c'],
                    'Volume': item['v']
                })
            
            data = pd.DataFrame(data_list)
            data.index = pd.to_datetime([item['t'] // 1000000000 for item in result['results']], unit='s')
            data.index.name = 'datetime'
            
            data = data.sort_index()
            
            return data
        except ImportError:
            print("  ✗ 需要安装 requests: python -m pip install requests")
            raise
        except Exception as e:
            print(f"  ✗ Polygon.io 获取失败: {e}")
            raise
    
    def _fetch_from_stooq(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """从 Stooq 获取股票数据"""
        try:
            import requests
            
            # Stooq 使用 .US 后缀表示美股
            stooq_symbol = f"{symbol}.US"
            
            # 获取日线数据
            url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
            
            response = requests.get(url)
            response.raise_for_status()
            
            # Stooq 返回 CSV 格式数据
            from io import StringIO
            data = pd.read_csv(StringIO(response.text))
            
            # 重命名列名
            data.columns = ['datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
            
            # 转换日期格式
            data['datetime'] = pd.to_datetime(data['datetime'])
            data = data.set_index('datetime')
            
            # 排序
            data = data.sort_index()
            
            # 根据period筛选数据
            if period == '1y':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                data = data[data.index >= start_date]
            elif period == '1mo':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                data = data[data.index >= start_date]
            
            return data
        except Exception as e:
            print(f"  ✗ Stooq 获取失败: {e}")
            raise
    
    def _fetch_from_twelve_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """从 Twelve Data 获取股票数据"""
        try:
            import os
            import requests
            
            api_key = os.environ.get('TWELVE_DATA_API_KEY', '')
            
            if not api_key:
                raise ValueError("需要设置 TWELVE_DATA_API_KEY 环境变量")
            
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=500&apikey={api_key}"
            
            response = requests.get(url)
            response.raise_for_status()
            
            result = response.json()
            
            if 'status' in result and result['status'] == 'error':
                error_msg = result.get('message', '未知错误')
                raise ValueError(f"API错误: {error_msg}")
            
            if 'values' not in result or not result['values']:
                raise ValueError(f"无法获取股票 {symbol} 的数据")
            
            data_list = []
            for item in result['values']:
                data_list.append({
                    'Open': float(item['open']),
                    'High': float(item['high']),
                    'Low': float(item['low']),
                    'Close': float(item['close']),
                    'Volume': int(item['volume'])
                })
            
            data = pd.DataFrame(data_list)
            data.index = pd.to_datetime([item['datetime'] for item in result['values']])
            data.index.name = 'datetime'
            
            data = data.sort_index()
            
            if period == '1y':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                data = data[data.index >= start_date]
            
            return data
        except Exception as e:
            print(f"  ✗ Twelve Data 获取失败: {e}")
            raise
    
    def _apply_adjustment(self, data: pd.DataFrame, adjust: str = "none") -> pd.DataFrame:
        """
        应用复权调整
        
        Args:
            data: 原始数据
            adjust: 复权方式，'forward'(前复权) 或 'backward'(后复权)
        
        Returns:
            复权后的数据
        """
        if adjust == 'none':
            return data
        
        data = data.copy()
        
        # 计算累计收益率（简单复权方法）
        # 注意：这是一个简化的复权方法，真实的复权需要拆股、分红等历史数据
        if adjust == 'forward':
            # 前复权：以最新价格为基准，调整历史价格
            latest_close = data['Close'].iloc[-1]
            cumulative_returns = (1 + data['Close'].pct_change()).cumprod()
            adjustment_factor = cumulative_returns.iloc[-1] / cumulative_returns
            
            # 填充NaN值（第一行）
            adjustment_factor = adjustment_factor.fillna(1.0)
            
            for col in ['Open', 'High', 'Low', 'Close']:
                data[col] = data[col] * adjustment_factor
            
            # 保留两位小数
            for col in ['Open', 'High', 'Low', 'Close']:
                data[col] = data[col].round(2)
            
        elif adjust == 'backward':
            # 后复权：以历史价格为基准，调整未来价格
            first_close = data['Close'].iloc[0]
            cumulative_returns = (1 + data['Close'].pct_change()).cumprod()
            adjustment_factor = cumulative_returns / cumulative_returns.iloc[0]
            
            # 填充NaN值（第一行）
            adjustment_factor = adjustment_factor.fillna(1.0)
            
            for col in ['Open', 'High', 'Low', 'Close']:
                data[col] = data[col] / adjustment_factor
            
            # 保留两位小数
            for col in ['Open', 'High', 'Low', 'Close']:
                data[col] = data[col].round(2)
        
        print(f"  ✓ 已应用{adjust}复权")
        return data
    
    def fetch_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y",
        interval: str = "1d",
        max_retries: int = 3,
        retry_delay: int = 2,
        use_cache: bool = True,
        adjust: str = "forward"
    ) -> pd.DataFrame:
        """
        获取美股K线数据（支持缓存）
        
        Args:
            symbol: 股票代码，如 'AAPL', 'MSFT'
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'
            period: 时间周期，可选 '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
            interval: 数据间隔，可选 '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            use_cache: 是否使用缓存
            adjust: 复权方式，可选 'auto'(自动), 'forward'(前复权), 'backward'(后复权), 'none'(不复权)
        
        Returns:
            包含OHLCV数据的DataFrame
        """
        cache_path = self._get_cache_path(symbol, period, interval, adjust)
        
        if use_cache and self._is_cache_valid(cache_path):
            cached_data = self._load_cache(cache_path)
            if cached_data is not None:
                return cached_data
        
        # 首先尝试 yfinance（支持复权数据）
        try:
            # 设置代理环境变量
            if self.proxy:
                import os
                os.environ['HTTP_PROXY'] = self.proxy
                os.environ['HTTPS_PROXY'] = self.proxy
                print(f"  ✓ 使用代理: {self.proxy}")
            
            ticker = yf.Ticker(symbol)
            
            for attempt in range(self.retry_count):
                try:
                    if start_date and end_date:
                        data = ticker.history(
                            start=start_date, 
                            end=end_date, 
                            interval=interval,
                            auto_adjust=(adjust == 'auto')
                        )
                    else:
                        data = ticker.history(
                            period=period, 
                            interval=interval,
                            auto_adjust=(adjust == 'auto')
                        )
                    
                    if data.empty:
                        raise ValueError(f"无法获取股票 {symbol} 的数据")
                    
                    data.index = pd.to_datetime(data.index)
                    data.index.name = 'datetime'
                    
                    if use_cache:
                        self._save_cache(data, cache_path)
                    
                    return data
                except Exception as e:
                    if attempt < self.retry_count - 1:
                        current_delay = self.retry_delay * (2 ** attempt)
                        print(f"yfinance 获取 {symbol} 数据失败，{current_delay}秒后重试... (尝试 {attempt + 1}/{self.retry_count})")
                        time.sleep(current_delay)
                    else:
                        raise e
        except Exception as e:
            print(f"  ✗ yfinance 获取失败: {e}")
            print(f"  正在尝试 Stooq...")
        
        # 如果 yfinance 失败，尝试 Stooq
        try:
            data = self._fetch_from_stooq(symbol, period)
            if adjust != 'none':
                data = self._apply_adjustment(data, adjust)
            if use_cache:
                self._save_cache(data, cache_path)
            return data
        except Exception as e:
            print(f"  ✗ Stooq 获取失败: {e}")
            print(f"  正在尝试 Twelve Data...")
        
        # 如果 Stooq 失败，尝试 Twelve Data
        try:
            data = self._fetch_from_twelve_data(symbol, period)
            if adjust != 'none':
                data = self._apply_adjustment(data, adjust)
            if use_cache:
                self._save_cache(data, cache_path)
            return data
        except Exception as e:
            print(f"  ✗ Twelve Data 获取失败: {e}")
            print(f"  正在尝试 Alpha Vantage...")
        
        # 如果 Twelve Data 失败，尝试 Alpha Vantage
        try:
            data = self._fetch_from_alpha_vantage(symbol, period)
            if adjust != 'none':
                data = self._apply_adjustment(data, adjust)
            if use_cache:
                self._save_cache(data, cache_path)
            return data
        except Exception as e:
            print(f"  ✗ Alpha Vantage 获取失败: {e}")
            print(f"  正在尝试 Polygon.io...")
        
        # 如果 Alpha Vantage 失败，尝试 Polygon.io
        try:
            data = self._fetch_from_polygon(symbol, period)
            if adjust != 'none':
                data = self._apply_adjustment(data, adjust)
            if use_cache:
                self._save_cache(data, cache_path)
            return data
        except Exception as e:
            raise ValueError(f"无法获取股票 {symbol} 的真实数据。所有数据源均失败。")

    def resample_data(
        self,
        data: pd.DataFrame,
        timeframe: str = '1d'
    ) -> pd.DataFrame:
        """
        将数据转换为指定周期（日线、周线、月线）
        
        Args:
            data: 原始数据DataFrame
            timeframe: 时间周期，可选 '1d'(日线), '1w'(周线), '1m'(月线)
        
        Returns:
            转换周期后的DataFrame
        """
        if timeframe == '1d':
            return data
        
        df = data.copy()
        
        if timeframe == '1w':
            resample_rule = 'W'
            label = 'left'
        elif timeframe == '1m':
            resample_rule = 'ME'
            label = 'left'
        else:
            raise ValueError(f"不支持的时间周期: {timeframe}")
        
        resampled = df.resample(resample_rule, label=label).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        })
        
        resampled = resampled.dropna()
        resampled.index.name = 'datetime'
        
        return resampled

    def fetch_multiple_stocks(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y",
        interval: str = "1d"
    ) -> dict:
        """
        获取多只股票的数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 时间周期
            interval: 数据间隔
        
        Returns:
            字典，key为股票代码，value为对应的DataFrame
        """
        result = {}
        for symbol in symbols:
            try:
                data = self.fetch_stock_data(symbol, start_date, end_date, period, interval)
                result[symbol] = data
            except Exception as e:
                print(f"获取 {symbol} 数据失败: {e}")
        
        return result

    def fetch_stock_data_batch(
        self,
        symbols: List[str],
        period: str = "1y",
        interval: str = "1d",
        use_cache: bool = True,
        adjust: str = "forward"
    ) -> Dict[str, pd.DataFrame]:
        """
        使用 yfinance 一次性批量拉取多只股票，并按单股票缓存文件写入。

        Returns:
            key 为 symbol，value 为该股票 DataFrame（OHLCV）
        """
        if not symbols:
            return {}

        unique_symbols = list(dict.fromkeys(symbols))

        try:
            if self.proxy:
                os.environ['HTTP_PROXY'] = self.proxy
                os.environ['HTTPS_PROXY'] = self.proxy
                print(f"  ✓ 使用代理: {self.proxy}")

            raw = yf.download(
                tickers=' '.join(unique_symbols),
                period=period,
                interval=interval,
                group_by='ticker',
                auto_adjust=(adjust == 'auto'),
                progress=False,
                threads=False,
            )
        except Exception as e:
            raise ValueError(f"批量获取失败: {e}") from e

        if raw is None or raw.empty:
            raise ValueError("批量获取失败: yfinance 返回空数据")

        result: Dict[str, pd.DataFrame] = {}
        has_multi_columns = isinstance(raw.columns, pd.MultiIndex)

        for symbol in unique_symbols:
            try:
                if has_multi_columns:
                    if symbol not in raw.columns.get_level_values(0):
                        continue
                    item = raw[symbol].copy()
                else:
                    item = raw.copy()

                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                if not set(required_cols).issubset(item.columns):
                    continue

                item = item[required_cols].dropna()
                if item.empty:
                    continue

                item.index = pd.to_datetime(item.index)
                item.index.name = 'datetime'

                result[symbol] = item

                if use_cache:
                    cache_path = self._get_cache_path(symbol, period, interval, adjust)
                    self._save_cache(item, cache_path)
            except Exception:
                continue

        return result

    def get_stock_info(self, symbol: str) -> dict:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
        
        Returns:
            股票信息字典
        """
        # 设置代理环境变量
        if self.proxy:
            import os
            os.environ['HTTP_PROXY'] = self.proxy
            os.environ['HTTPS_PROXY'] = self.proxy
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            'name': info.get('longName', ''),
            'sector': info.get('sector', ''),
            'industry': info.get('industry', ''),
            'market_cap': info.get('marketCap', 0),
            'current_price': info.get('currentPrice', 0),
            'previous_close': info.get('previousClose', 0)
        }
