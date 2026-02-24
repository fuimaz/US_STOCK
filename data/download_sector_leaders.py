import pandas as pd
from data_fetcher import DataFetcher
import time
from datetime import datetime

def download_sector_leaders():
    """
    下载美股各行业龙头股票近20年数据到缓存
    """
    
    # 各行业龙头股票列表
    sector_leaders = {
        '科技': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],
        '金融': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
        '医疗': ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRK'],
        '消费': ['PG', 'KO', 'MCD', 'NKE', 'WMT'],
        '能源': ['XOM', 'CVX', 'COP', 'SLB', 'HAL'],
        '工业': ['CAT', 'HON', 'GE', 'MMM', 'RTX'],
        '材料': ['LIN', 'DOW', 'DD', 'APD', 'FCX'],
        '公用事业': ['NEE', 'DUK', 'SO', 'EXC', 'D'],
        '房地产': ['AMT', 'PLD', 'O', 'CCI', 'EQIX'],
        '电信': ['VZ', 'T', 'CMCSA', 'TMUS', 'CHTR']
    }
    
    print("=" * 80)
    print("美股各行业龙头股票数据下载")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 初始化数据获取器（使用代理）
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=0,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 统计信息
    total_stocks = 0
    success_count = 0
    failed_stocks = []
    results = []
    
    # 遍历各个行业
    for sector, symbols in sector_leaders.items():
        print(f"\n{'=' * 80}")
        print(f"行业: {sector}")
        print(f"{'=' * 80}")
        
        sector_success = 0
        sector_failed = []
        
        # 遍历该行业的股票
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] 正在下载 {symbol}...")
            
            try:
                # 下载20年前复权数据
                data = fetcher.fetch_stock_data(
                    symbol,
                    period='20y',
                    adjust='forward'
                )
                
                if data is not None and len(data) > 0:
                    print(f"  ✓ {symbol} 下载成功: {len(data)} 条数据")
                    print(f"    时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
                    print(f"    最新收盘价: ${data['Close'].iloc[-1]:.2f}")
                    
                    results.append({
                        '行业': sector,
                        '股票代码': symbol,
                        '数据条数': len(data),
                        '开始日期': data.index[0].strftime('%Y-%m-%d'),
                        '结束日期': data.index[-1].strftime('%Y-%m-%d'),
                        '最新收盘价': data['Close'].iloc[-1],
                        '状态': '成功'
                    })
                    
                    sector_success += 1
                    success_count += 1
                else:
                    print(f"  ✗ {symbol} 下载失败: 数据为空")
                    sector_failed.append(symbol)
                    failed_stocks.append(symbol)
                
                total_stocks += 1
                
                # 避免请求过快
                time.sleep(1)
                
            except Exception as e:
                print(f"  ✗ {symbol} 下载失败: {e}")
                sector_failed.append(symbol)
                failed_stocks.append(symbol)
                total_stocks += 1
                
                # 失败后等待更长时间
                time.sleep(2)
        
        # 行业统计
        print(f"\n{sector} 行业统计:")
        print(f"  成功: {sector_success}/{len(symbols)}")
        print(f"  失败: {len(sector_failed)}/{len(symbols)}")
        if sector_failed:
            print(f"  失败股票: {', '.join(sector_failed)}")
    
    # 总体统计
    print(f"\n{'=' * 80}")
    print("总体统计")
    print(f"{'=' * 80}")
    print(f"总股票数: {total_stocks}")
    print(f"成功: {success_count}")
    print(f"失败: {len(failed_stocks)}")
    print(f"成功率: {success_count/total_stocks*100:.2f}%")
    
    if failed_stocks:
        print(f"\n失败股票列表:")
        for symbol in failed_stocks:
            print(f"  - {symbol}")
    
    # 保存结果到CSV
    if results:
        results_df = pd.DataFrame(results)
        results_file = 'download_results.csv'
        results_df.to_csv(results_file, index=False, encoding='utf-8-sig')
        print(f"\n✓ 下载结果已保存到: {results_file}")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == '__main__':
    download_sector_leaders()