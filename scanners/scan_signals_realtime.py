"""
缠论实时信号扫描器。

- 扫描股票池中的近期买卖点信号。
- 优先读取本地缓存，缓存过期时在线拉取数据。
- 结果追加写入固定历史 CSV 文件。
"""

import json
import os
import sys
import warnings
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

warnings.filterwarnings('ignore')

# 将项目根目录加入导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_fetcher import DataFetcher
from indicators.chan.chan_theory_realtime import ChanTheoryRealtime


# 扫描使用的股票池
STOCK_UNIVERSE = {# A股主要指数成分股
    '000001.SZ': '平安银行',
    '000002.SZ': '万科A',
    '000333.SZ': '美的集团',
    '000568.SZ': '泸州老窖',
    '000625.SZ': '长安汽车',
    '000651.SZ': '格力电器',
    '000661.SZ': '长春高新',
    '000725.SZ': '京东方A',
    '000858.SZ': '五粮液',
    '000876.SZ': '新希望',
    '002049.SZ': '紫光国微',
    '002230.SZ': '科大讯飞',
    '002304.SZ': '洋河股份',
    '002415.SZ': '海康威视',
    '002460.SZ': '赣锋锂业',
    '002475.SZ': '立讯精密',
    '002594.SZ': '比亚迪',
    '002714.SZ': '牧原股份',
    '300033.SZ': '同花顺',
    '300124.SZ': '汇川技术',
    '300274.SZ': '阳光电源',
    '300750.SZ': '宁德时代',
    '300760.SZ': '迈瑞医疗',
    '600009.SS': '上海机场',
    '600018.SS': '上港集团',
    '600019.SS': '宝钢股份',
    '600028.SS': '中国石化',
    '600029.SS': '南方航空',
    '600030.SS': '中信证券',
    '600031.SS': '三一重工',
    '600036.SS': '招商银行',
    '600048.SS': '保利发展',
    '600050.SS': '中国联通',
    '600104.SS': '上汽集团',
    '600115.SS': '东方航空',
    '600276.SS': '恒瑞医药',
    '600309.SS': '万华化学',
    '600346.SS': '恒力石化',
    '600519.SS': '贵州茅台',
    '600584.SS': '长电科技',
    '600585.SS': '海螺水泥',
    '600690.SS': '海尔智家',
    '600694.SS': '大商股份',
    '600886.SS': '国投电力',
    '600887.SS': '伊利股份',
    '600900.SS': '长江电力',
    '600941.SS': '中国移动',
    '601012.SS': '隆基绿能',
    '601088.SS': '中国神华',
    '601111.SS': '中国国航',
    '601166.SS': '兴业银行',
    '601186.SS': '中国铁建',
    '601238.SS': '广汽集团',
    '601318.SS': '中国平安',
    '601390.SS': '中国中铁',
    '601398.SS': '工商银行',
    '601600.SS': '中国铝业',
    '601601.SS': '中国太保',
    '601628.SS': '中国人寿',
    '601688.SS': '华泰证券',
    '601857.SS': '中国石油',
    '601888.SS': '中国中免',
    '601898.SS': '中煤能源',
    '601899.SS': '紫金矿业',
    '601939.SS': '建设银行',
    '601985.SS': '中国核电',
    '603288.SS': '海天味业',
}


class SignalScanner:
    """实时买卖点信号扫描器。"""

    def __init__(self, stock_universe: Dict[str, str] = None, only_latest_trading_day: bool = False):
        """
        初始化扫描器
        
        Args:
            stock_universe: 股票池，格式 {symbol: name}
            only_latest_trading_day: 是否仅保留最新交易日触发的信号
        """
        self.stock_universe = stock_universe or STOCK_UNIVERSE
        self.only_latest_trading_day = only_latest_trading_day
        self.fetcher = DataFetcher(
            cache_dir='data_cache',
            cache_days=30,
            proxy='http://127.0.0.1:7897',
            retry_count=3,
            retry_delay=2.0,
        )
        self.prefetched_data: Dict[str, pd.DataFrame] = {}

    @staticmethod
    def _normalize_price_frame(data: pd.DataFrame) -> pd.DataFrame:
        """统一清洗成 OHLCV + datetime 索引格式。"""
        if data is None or len(data) == 0:
            return pd.DataFrame()
        df = data.copy()
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], utc=True).dt.tz_localize(None)
            df = df.set_index('datetime')
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']].copy().dropna()

    def prefetch_all_symbols(self):
        """一次性批量拉取股票池日线数据并更新缓存。"""
        symbols = list(self.stock_universe.keys())
        print(f"Batch fetching daily data for {len(symbols)} symbols...")
        try:
            batch_data = self.fetcher.fetch_stock_data_batch(
                symbols=symbols,
                period='1y',
                interval='1d',
                use_cache=True,
                adjust='forward',
            )
            self.prefetched_data = {
                symbol: self._normalize_price_frame(data)
                for symbol, data in batch_data.items()
                if data is not None and len(data) > 0
            }
            print(f"Batch fetch complete: {len(self.prefetched_data)}/{len(symbols)} symbols updated")
        except Exception as exc:
            print(f"Batch fetch failed: {exc}")
            self.prefetched_data = {}

    def fetch_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """优先读取当日缓存，否则在线拉取。"""
        try:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cache_file = f'data_cache/{symbol}_1y_1d_forward.csv'

            if os.path.exists(cache_file):
                cache_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
                if cache_mtime >= today:
                    data = self._normalize_price_frame(pd.read_csv(cache_file))
                    if len(data) > 0 and data.index[-1].date() == today.date():
                        print(f"  [{symbol}] Using cached data (latest: {data.index[-1].date()})")
                        return data

            prefetched = self.prefetched_data.get(symbol)
            if prefetched is not None and len(prefetched) > 0:
                print(f"  [{symbol}] Using batch-fetched data (latest: {prefetched.index[-1].date()})")
                return prefetched

            print(f"  [{symbol}] Cache outdated, fetching online...")
            try:
                data = self.fetcher.fetch_stock_data(
                    symbol=symbol,
                    period='1y',
                    interval='1d',
                    use_cache=True,
                    adjust='forward',
                )
                if data is not None and len(data) > 0:
                    data = self._normalize_price_frame(data)
                    print(f"  [{symbol}] Fetched online data (latest: {data.index[-1].date()})")
                    return data
            except Exception as exc:
                print(f"  [{symbol}] Online fetch failed: {exc}")

            cache_file_20y = f'data_cache/{symbol}_20y_1d_forward.csv'
            if os.path.exists(cache_file_20y):
                print(f"  [{symbol}] Using 20y cached data (fallback)")
                return self._normalize_price_frame(pd.read_csv(cache_file_20y))

            print(f"  [{symbol}] No data available, skipping")
            return None
        except Exception as exc:
            print(f"  [{symbol}] Error: {exc}")
            return None

    def analyze_signals(self, symbol: str, name: str) -> Dict:
        """分析单只股票并返回近期买卖点信号。"""
        data = self.fetch_stock_data(symbol)
        if data is None or len(data) < 60:
            return {'symbol': symbol, 'name': name, 'buy_signals': [], 'sell_signals': []}

        chan = ChanTheoryRealtime(k_type='day')
        chan.analyze(data)

        current_price = data['Close'].iloc[-1]
        current_date = data.index[-1]
        recent_data = data.tail(20)
        trend = 'UP' if recent_data['Close'].iloc[-1] > recent_data['Close'].iloc[0] else 'DOWN'
        latest_trading_day = data.index[-1].date()

        buy_signals = []
        for bp in chan.buy_points:
            bp_day = bp['index'].date()
            is_recent = bp['index'] >= data.index[-5]
            is_latest_day = bp_day == latest_trading_day
            if (self.only_latest_trading_day and is_latest_day) or (not self.only_latest_trading_day and is_recent):
                price_diff = (current_price - bp['price']) / bp['price'] * 100
                buy_signals.append({
                    'symbol': symbol,
                    'name': name,
                    'signal_date': bp['index'].strftime('%Y-%m-%d'),
                    'signal_type': f"Type {bp['type']} Buy",
                    'signal_desc': bp.get('desc', ''),
                    'signal_price': round(bp['price'], 2),
                    'current_price': round(current_price, 2),
                    'price_diff': round(price_diff, 2),
                    'current_date': current_date.strftime('%Y-%m-%d'),
                    'trend': trend,
                })

        sell_signals = []
        for sp in chan.sell_points:
            sp_day = sp['index'].date()
            is_recent = sp['index'] >= data.index[-5]
            is_latest_day = sp_day == latest_trading_day
            if (self.only_latest_trading_day and is_latest_day) or (not self.only_latest_trading_day and is_recent):
                price_diff = (current_price - sp['price']) / sp['price'] * 100
                sell_signals.append({
                    'symbol': symbol,
                    'name': name,
                    'signal_date': sp['index'].strftime('%Y-%m-%d'),
                    'signal_type': f"Type {sp['type']} Sell",
                    'signal_desc': sp.get('desc', ''),
                    'signal_price': round(sp['price'], 2),
                    'current_price': round(current_price, 2),
                    'price_diff': round(price_diff, 2),
                    'current_date': current_date.strftime('%Y-%m-%d'),
                    'trend': trend,
                })

        return {
            'symbol': symbol,
            'name': name,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'total_buy_points': len(chan.buy_points),
            'total_sell_points': len(chan.sell_points),
        }

    def scan_all_stocks(self) -> Dict:
        """扫描所有配置股票。"""
        print('=' * 100)
        print(f"Chan Theory Real-time Signal Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('=' * 100)
        print(f"Stock universe: {len(self.stock_universe)} stocks")
        print()
        self.prefetch_all_symbols()
        print()

        all_buy_signals = []
        all_sell_signals = []
        error_count = 0

        for i, (symbol, name) in enumerate(self.stock_universe.items(), 1):
            print(f"[{i}/{len(self.stock_universe)}] Scanning: {name} ({symbol})")
            try:
                result = self.analyze_signals(symbol, name)

                if result['buy_signals']:
                    for signal in result['buy_signals']:
                        all_buy_signals.append(signal)
                        print(f"  >>> BUY SIGNAL: {signal['signal_type']} @ {signal['signal_price']} ({signal['price_diff']:+.2f}%)")

                if result['sell_signals']:
                    for signal in result['sell_signals']:
                        all_sell_signals.append(signal)
                        print(f"  >>> SELL SIGNAL: {signal['signal_type']} @ {signal['signal_price']} ({signal['price_diff']:+.2f}%)")

                if not result['buy_signals'] and not result['sell_signals']:
                    print('  No recent signals')
            except Exception as exc:
                print(f"  Error: {exc}")
                error_count += 1
            print()

        print('=' * 100)
        print('Scan complete')
        print(f"  Buy signals: {len(all_buy_signals)}")
        print(f"  Sell signals: {len(all_sell_signals)}")
        print(f"  Errors: {error_count}")
        print('=' * 100)

        return {'buy_signals': all_buy_signals, 'sell_signals': all_sell_signals}

    def save_results(self, signals: Dict):
        """将本次结果追加到固定历史 CSV，并更新最新摘要。"""
        output_dir = 'results/realtime_scan'
        os.makedirs(output_dir, exist_ok=True)

        scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        history_csv = f'{output_dir}/signals_history.csv'

        all_signals = []
        for signal in signals['buy_signals']:
            row = dict(signal)
            row['side'] = 'BUY'
            row['scan_time'] = scan_time
            all_signals.append(row)

        for signal in signals['sell_signals']:
            row = dict(signal)
            row['side'] = 'SELL'
            row['scan_time'] = scan_time
            all_signals.append(row)

        if all_signals:
            history_df = pd.DataFrame(all_signals)
            file_exists = os.path.exists(history_csv)
            history_df.to_csv(
                history_csv,
                mode='a',
                header=not file_exists,
                index=False,
                encoding='utf-8-sig',
            )

        summary = {
            'scan_time': datetime.now().isoformat(),
            'total_stocks': len(self.stock_universe),
            'buy_count': len(signals['buy_signals']),
            'sell_count': len(signals['sell_signals']),
            'buy_signals': signals['buy_signals'],
            'sell_signals': signals['sell_signals'],
        }
        with open(f'{output_dir}/summary_latest.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\nResults saved to: {output_dir}/")
        print(f"  History CSV: {history_csv}")
        print(f"  Appended rows: {len(all_signals)}")

    def print_summary(self, signals: Dict):
        """在控制台打印简要汇总。"""
        print('\n' + '=' * 100)
        print('SIGNAL SUMMARY')
        print('=' * 100)

        if signals['buy_signals']:
            buy_sorted = sorted(signals['buy_signals'], key=lambda x: x['signal_date'], reverse=True)
            print(f"\n[ BUY SIGNALS ] - Total: {len(buy_sorted)}")
            print(f"{'Symbol':<12} {'Name':<10} {'Date':<12} {'Type':<14} {'SigPrice':<10} {'CurPrice':<10} {'Change':<8}")
            print('-' * 90)
            for s in buy_sorted:
                print(
                    f"{s['symbol']:<12} {s['name']:<10} {s['signal_date']:<12} {s['signal_type']:<14} "
                    f"{s['signal_price']:>8.2f} {s['current_price']:>8.2f} {s['price_diff']:>+6.2f}%"
                )
        else:
            print('\n[ BUY SIGNALS ] - None')

        if signals['sell_signals']:
            sell_sorted = sorted(signals['sell_signals'], key=lambda x: x['signal_date'], reverse=True)
            print(f"\n[ SELL SIGNALS ] - Total: {len(sell_sorted)}")
            print(f"{'Symbol':<12} {'Name':<10} {'Date':<12} {'Type':<14} {'SigPrice':<10} {'CurPrice':<10} {'Change':<8}")
            print('-' * 90)
            for s in sell_sorted:
                print(
                    f"{s['symbol']:<12} {s['name']:<10} {s['signal_date']:<12} {s['signal_type']:<14} "
                    f"{s['signal_price']:>8.2f} {s['current_price']:>8.2f} {s['price_diff']:>+6.2f}%"
                )
        else:
            print('\n[ SELL SIGNALS ] - None')

        print('\n' + '=' * 100)


def main():
    """程序入口。"""
    now = datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    scanner = SignalScanner()
    signals = scanner.scan_all_stocks()
    scanner.print_summary(signals)
    scanner.save_results(signals)
    return signals


if __name__ == '__main__':
    main()
