"""
实时扫描缠论买卖点信号
每天下午2点左右运行，检测当前命中买卖点的股票

使用方法:
    python scan_signals_realtime.py
    
输出:
    - 控制台显示当前命中买卖点的股票
    - 保存结果到 results/realtime_scan/ 目录
"""
import pandas as pd
import numpy as np
import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

# 导入缠论指标代码（复用回测模块）
from chan_theory_realtime import ChanTheoryRealtime
from data_fetcher import DataFetcher


# 股票池配置 - 可以根据需要调整
STOCK_UNIVERSE = {
    # A股主要指数成分股
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
    """实时买卖点信号扫描器"""
    
    def __init__(self, stock_universe: Dict[str, str] = None):
        """
        初始化扫描器
        
        Args:
            stock_universe: 股票池，格式 {symbol: name}
        """
        self.stock_universe = stock_universe or STOCK_UNIVERSE
        self.fetcher = DataFetcher(
            cache_dir='data_cache',
            cache_days=30,
            proxy='http://127.0.0.1:7897',
            retry_count=3,
            retry_delay=2.0
        )
        
    def fetch_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """获取股票数据"""
        try:
            # 尝试从缓存获取
            cache_file = f'data_cache/{symbol}_1y_1d_forward.csv'
            
            if os.path.exists(cache_file):
                cache_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                if cache_mtime >= today:
                    data = pd.read_csv(cache_file)
                    if 'datetime' in data.columns:
                        data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
                        data = data.set_index('datetime')
                    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    data = data.dropna()
                    
                    last_date = data.index[-1].date()
                    if last_date == today.date():
                        print(f"  [{symbol}] Using cached data (latest: {last_date})")
                        return data
            
            # 尝试使用20年缓存
            cache_file_20y = f'data_cache/{symbol}_20y_1d_forward.csv'
            if os.path.exists(cache_file_20y):
                print(f"  [{symbol}] Using 20y cached data")
                data = pd.read_csv(cache_file_20y)
                if 'datetime' in data.columns:
                    data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
                    data = data.set_index('datetime')
                data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                data = data.dropna()
                return data
            
            print(f"  [{symbol}] No cache available, skipping")
            return None
            
        except Exception as e:
            print(f"  [{symbol}] Error: {e}")
            return None
    
    def analyze_signals(self, symbol: str, name: str) -> Dict:
        """
        分析股票的买卖点信号
        
        Returns:
            包含买卖信号的字典
        """
        # 获取数据
        data = self.fetch_stock_data(symbol)
        if data is None or len(data) < 60:
            return {'symbol': symbol, 'name': name, 'buy_signals': [], 'sell_signals': []}
        
        # 使用缠论分析
        chan = ChanTheoryRealtime(k_type='day')
        result = chan.analyze(data)
        
        # 获取当前价格
        current_price = data['Close'].iloc[-1]
        current_date = data.index[-1]
        
        # 获取近期走势
        recent_data = data.tail(20)
        trend = "UP" if recent_data['Close'].iloc[-1] > recent_data['Close'].iloc[0] else "DOWN"
        
        # 找出近5个交易日的买点信号
        buy_signals = []
        for bp in chan.buy_points:
            if bp['index'] >= data.index[-5]:
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
        
        # 找出近5个交易日的卖点信号
        sell_signals = []
        for sp in chan.sell_points:
            if sp['index'] >= data.index[-5]:
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
        """
        扫描所有股票的买卖点信号
        
        Returns:
            {'buy_signals': [...], 'sell_signals': [...]}
        """
        print("=" * 100)
        print(f"Chan Theory Real-time Signal Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        print(f"Stock universe: {len(self.stock_universe)} stocks")
        print()
        
        all_buy_signals = []
        all_sell_signals = []
        error_count = 0
        
        for i, (symbol, name) in enumerate(self.stock_universe.items(), 1):
            print(f"[{i}/{len(self.stock_universe)}] Scanning: {name} ({symbol})")
            
            try:
                result = self.analyze_signals(symbol, name)
                
                # 收集买点信号
                if result['buy_signals']:
                    for signal in result['buy_signals']:
                        all_buy_signals.append(signal)
                        print(f"  >>> BUY SIGNAL: {signal['signal_type']} @ {signal['signal_price']} ({signal['price_diff']:+.2f}%)")
                
                # 收集卖点信号
                if result['sell_signals']:
                    for signal in result['sell_signals']:
                        all_sell_signals.append(signal)
                        print(f"  >>> SELL SIGNAL: {signal['signal_type']} @ {signal['signal_price']} ({signal['price_diff']:+.2f}%)")
                
                # 无信号
                if not result['buy_signals'] and not result['sell_signals']:
                    print(f"  No recent signals")
                    
            except Exception as e:
                print(f"  Error: {e}")
                error_count += 1
            
            print()
        
        print("=" * 100)
        print(f"Scan complete")
        print(f"  Buy signals: {len(all_buy_signals)}")
        print(f"  Sell signals: {len(all_sell_signals)}")
        print(f"  Errors: {error_count}")
        print("=" * 100)
        
        return {
            'buy_signals': all_buy_signals,
            'sell_signals': all_sell_signals
        }
    
    def save_results(self, signals: Dict):
        """保存扫描结果"""
        output_dir = 'results/realtime_scan'
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存买点
        if signals['buy_signals']:
            buy_df = pd.DataFrame(signals['buy_signals'])
            buy_df.to_csv(f'{output_dir}/buy_signals_{timestamp}.csv', index=False, encoding='utf-8-sig')
            with open(f'{output_dir}/buy_signals_{timestamp}.json', 'w', encoding='utf-8') as f:
                json.dump(signals['buy_signals'], f, ensure_ascii=False, indent=2)
        
        # 保存卖点
        if signals['sell_signals']:
            sell_df = pd.DataFrame(signals['sell_signals'])
            sell_df.to_csv(f'{output_dir}/sell_signals_{timestamp}.csv', index=False, encoding='utf-8-sig')
            with open(f'{output_dir}/sell_signals_{timestamp}.json', 'w', encoding='utf-8') as f:
                json.dump(signals['sell_signals'], f, ensure_ascii=False, indent=2)
        
        # 保存汇总
        summary = {
            'scan_time': datetime.now().isoformat(),
            'total_stocks': len(self.stock_universe),
            'buy_count': len(signals['buy_signals']),
            'sell_count': len(signals['sell_signals']),
            'buy_signals': signals['buy_signals'],
            'sell_signals': signals['sell_signals']
        }
        with open(f'{output_dir}/summary_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to: {output_dir}/")
        print(f"  Timestamp: {timestamp}")
    
    def print_summary(self, signals: Dict):
        """打印汇总结果"""
        print("\n" + "=" * 100)
        print("SIGNAL SUMMARY")
        print("=" * 100)
        
        # 买点汇总
        if signals['buy_signals']:
            buy_sorted = sorted(signals['buy_signals'], key=lambda x: x['signal_date'], reverse=True)
            
            print(f"\n[ BUY SIGNALS ] - Total: {len(buy_sorted)}")
            print(f"{'Symbol':<12} {'Name':<10} {'Date':<12} {'Type':<14} {'SigPrice':<10} {'CurPrice':<10} {'Change':<8}")
            print("-" * 90)
            
            for s in buy_sorted:
                print(f"{s['symbol']:<12} {s['name']:<10} {s['signal_date']:<12} {s['signal_type']:<14} "
                      f"{s['signal_price']:>8.2f} {s['current_price']:>8.2f} {s['price_diff']:>+6.2f}%")
        else:
            print("\n[ BUY SIGNALS ] - None")
        
        # 卖点汇总
        if signals['sell_signals']:
            sell_sorted = sorted(signals['sell_signals'], key=lambda x: x['signal_date'], reverse=True)
            
            print(f"\n[ SELL SIGNALS ] - Total: {len(sell_sorted)}")
            print(f"{'Symbol':<12} {'Name':<10} {'Date':<12} {'Type':<14} {'SigPrice':<10} {'CurPrice':<10} {'Change':<8}")
            print("-" * 90)
            
            for s in sell_sorted:
                print(f"{s['symbol']:<12} {s['name']:<10} {s['signal_date']:<12} {s['signal_type']:<14} "
                      f"{s['signal_price']:>8.2f} {s['current_price']:>8.2f} {s['price_diff']:>+6.2f}%")
        else:
            print("\n[ SELL SIGNALS ] - None")
        
        print("\n" + "=" * 100)


def main():
    """主函数"""
    now = datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建扫描器
    scanner = SignalScanner()
    
    # 执行扫描
    signals = scanner.scan_all_stocks()
    
    # 打印汇总
    scanner.print_summary(signals)
    
    # 保存结果
    scanner.save_results(signals)
    
    return signals


if __name__ == '__main__':
    signals = main()
