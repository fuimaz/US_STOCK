"""
实时扫描缠论买点信号
每天下午2点左右运行，检测当前命中买点的股票

使用方法:
    python scan_buy_signals_realtime.py
    
输出:
    - 控制台显示当前命中买点的股票
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


class BuySignalScanner:
    """实时买点信号扫描器"""
    
    def __init__(self, stock_universe: Dict[str, str] = None):
        """
        初始化扫描器
        
        Args:
            stock_universe: 股票池，格式 {symbol: name}
        """
        self.stock_universe = stock_universe or STOCK_UNIVERSE
        self.fetcher = DataFetcher(
            cache_dir='data_cache',
            cache_days=30,  # 缓存30天数据
            proxy='http://127.0.0.1:7897',
            retry_count=3,
            retry_delay=2.0
        )
        self.results = []
        
    def fetch_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        获取股票数据
        
        优先从缓存获取，如果缓存数据不是今天的，则重新获取
        """
        try:
            # 尝试从缓存获取
            cache_file = f'data_cache/{symbol}_1y_1d_forward.csv'
            
            # 检查缓存是否存在且是最新的
            if os.path.exists(cache_file):
                cache_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                # 如果缓存是今天的，直接读取
                if cache_mtime >= today:
                    data = pd.read_csv(cache_file)
                    if 'datetime' in data.columns:
                        data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
                        data = data.set_index('datetime')
                    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    data = data.dropna()
                    
                    # 检查是否有今天的数据
                    last_date = data.index[-1].date()
                    if last_date == today.date():
                        print(f"  [{symbol}] Using cached data (latest: {last_date})")
                        return data
            
            # 缓存不存在或不是最新的，尝试使用20年缓存
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
            
            if data is not None and len(data) > 0:
                return data
            
            return None
            
        except Exception as e:
            print(f"  [{symbol}] Error: {e}")
            return None
    
    def analyze_buy_signals(self, symbol: str, name: str) -> Optional[Dict]:
        """
        分析股票的买点信号
        
        Returns:
            如果有买点信号，返回信号详情；否则返回None
        """
        # 获取数据
        data = self.fetch_stock_data(symbol)
        if data is None or len(data) < 60:
            return None
        
        # 使用缠论分析（复用回测代码）
        chan = ChanTheoryRealtime(k_type='day')
        result = chan.analyze(data)
        
        # 获取最新的买点信号
        if not chan.buy_points:
            return None
        
        # 找出最近的买点
        latest_buy_point = None
        for bp in reversed(chan.buy_points):
            # 只考虑近5个交易日的买点
            if bp['index'] >= data.index[-5]:
                latest_buy_point = bp
                break
        
        if latest_buy_point is None:
            return None
        
        # 获取当前价格
        current_price = data['Close'].iloc[-1]
        current_date = data.index[-1]
        
        # 计算信号与当前价格的关系
        signal_price = latest_buy_point['price']
        price_diff = (current_price - signal_price) / signal_price * 100
        
        # 获取近期走势
        recent_data = data.tail(20)
        trend = "上涨" if recent_data['Close'].iloc[-1] > recent_data['Close'].iloc[0] else "下跌"
        
        return {
            'symbol': symbol,
            'name': name,
            'signal_date': latest_buy_point['index'].strftime('%Y-%m-%d'),
            'signal_type': f"第{latest_buy_point['type']}类买点",
            'signal_desc': latest_buy_point.get('desc', ''),
            'signal_price': round(signal_price, 2),
            'current_price': round(current_price, 2),
            'price_diff': round(price_diff, 2),
            'current_date': current_date.strftime('%Y-%m-%d'),
            'trend': trend,
            'total_buy_points': len(chan.buy_points),
            'total_sell_points': len(chan.sell_points),
            'latest_close': round(data['Close'].iloc[-1], 2),
            'latest_volume': int(data['Volume'].iloc[-1]),
            'ma20': round(data['Close'].rolling(20).mean().iloc[-1], 2),
            'ma60': round(data['Close'].rolling(60).mean().iloc[-1], 2),
        }
    
    def scan_all_stocks(self) -> List[Dict]:
        """
        扫描所有股票的买点信号
        
        Returns:
            命中买点的股票列表
        """
        print("=" * 100)
        print(f"Chan Theory Real-time Buy Signal Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        print(f"Stock universe: {len(self.stock_universe)} stocks")
        print()
        
        buy_signals = []
        error_count = 0
        
        for i, (symbol, name) in enumerate(self.stock_universe.items(), 1):
            print(f"[{i}/{len(self.stock_universe)}] Scanning: {name} ({symbol})")
            
            try:
                signal = self.analyze_buy_signals(symbol, name)
                if signal:
                    buy_signals.append(signal)
                    print(f"  >>> BUY SIGNAL DETECTED! <<<")
                    print(f"      Type: {signal['signal_type']}")
                    print(f"      Signal Date: {signal['signal_date']}")
                    print(f"      Signal Price: {signal['signal_price']}")
                    print(f"      Current Price: {signal['current_price']} ({signal['price_diff']:+.2f}%)")
            except Exception as e:
                print(f"  Error: {e}")
                error_count += 1
            
            print()
        
        print("=" * 100)
        print(f"Scan complete - Found {len(buy_signals)} stocks with buy signals")
        print(f"Errors: {error_count}")
        print("=" * 100)
        
        return buy_signals
    
    def save_results(self, signals: List[Dict]):
        """保存扫描结果"""
        if not signals:
            print("No buy signals, skipping save")
            return
        
        # 创建结果目录
        output_dir = 'results/realtime_scan'
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f'{output_dir}/buy_signals_{timestamp}.csv'
        json_file = f'{output_dir}/buy_signals_{timestamp}.json'
        
        # 保存为CSV
        df = pd.DataFrame(signals)
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        # 保存为JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved:")
        print(f"  CSV: {csv_file}")
        print(f"  JSON: {json_file}")
    
    def print_summary(self, signals: List[Dict]):
        """打印汇总结果"""
        if not signals:
            print("\n" + "=" * 100)
            print("未在股票池中发现买点信号")
            print("=" * 100)
            return
        
        print("\n" + "=" * 100)
        print("BUY SIGNAL SUMMARY")
        print("=" * 100)
        
        # 按信号日期排序
        signals_sorted = sorted(signals, key=lambda x: x['signal_date'], reverse=True)
        
        print(f"{'Symbol':<12} {'Name':<10} {'Date':<12} {'Type':<12} {'SigPrice':<10} {'CurPrice':<10} {'Change':<8} {'Trend':<6}")
        print("-" * 100)
        
        for s in signals_sorted:
            print(f"{s['symbol']:<12} {s['name']:<10} {s['signal_date']:<12} {s['signal_type']:<12} "
                  f"{s['signal_price']:>8.2f} {s['current_price']:>8.2f} "
                  f"{s['price_diff']:>+6.2f}% {s['trend']:<6}")
        
        print("-" * 100)
        print(f"Total: {len(signals)} stocks")
        
        # 统计
        type1_count = sum(1 for s in signals if '1' in s['signal_type'])
        type2_count = sum(1 for s in signals if '2' in s['signal_type'])
        print(f"  Type 1 Buy: {type1_count}")
        print(f"  Type 2 Buy: {type2_count}")
        print("=" * 100)


def main():
    """主函数"""
    # 检查当前时间（可选）
    now = datetime.now()
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建扫描器
    scanner = BuySignalScanner()
    
    # 执行扫描
    signals = scanner.scan_all_stocks()
    
    # 打印汇总
    scanner.print_summary(signals)
    
    # 保存结果
    scanner.save_results(signals)
    
    return signals


if __name__ == '__main__':
    signals = main()
