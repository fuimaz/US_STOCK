"""
分析历史扫描结果
统计哪些股票频繁出现买卖点信号
"""
import pandas as pd
import numpy as np
import os
import glob
import json
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt


def load_scan_results(results_dir='results/realtime_scan'):
    """加载所有历史扫描结果"""
    all_results = []
    
    # 加载所有summary文件
    summary_files = glob.glob(f'{results_dir}/summary_*.json')
    
    for file in sorted(summary_files):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 提取日期
                basename = os.path.basename(file)
                date_str = basename.replace('summary_', '').replace('.json', '')
                data['file_date'] = date_str
                all_results.append(data)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    return all_results


def analyze_signal_frequency(results):
    """分析信号出现频率"""
    buy_signals = defaultdict(list)
    sell_signals = defaultdict(list)
    
    for result in results:
        scan_date = result.get('file_date', 'unknown')
        
        # 统计买点
        for signal in result.get('buy_signals', []):
            symbol = signal['symbol']
            buy_signals[symbol].append({
                'date': scan_date,
                'type': signal['signal_type'],
                'price': signal['signal_price']
            })
        
        # 统计卖点
        for signal in result.get('sell_signals', []):
            symbol = signal['symbol']
            sell_signals[symbol].append({
                'date': scan_date,
                'type': signal['signal_type'],
                'price': signal['signal_price']
            })
    
    return buy_signals, sell_signals


def generate_statistics(buy_signals, sell_signals):
    """生成统计报告"""
    print("=" * 100)
    print("SCAN HISTORY ANALYSIS")
    print("=" * 100)
    print()
    
    # 统计出现次数最多的股票
    print("[ BUY SIGNAL FREQUENCY ]")
    print("-" * 80)
    
    buy_freq = [(symbol, len(signals)) for symbol, signals in buy_signals.items()]
    buy_freq.sort(key=lambda x: x[1], reverse=True)
    
    print(f"{'Rank':<6} {'Symbol':<12} {'Count':<8} {'Avg Price':<12} {'Recent Signals'}")
    print("-" * 80)
    
    for rank, (symbol, count) in enumerate(buy_freq[:20], 1):
        prices = [s['price'] for s in buy_signals[symbol]]
        avg_price = np.mean(prices)
        recent = buy_signals[symbol][-3:]  # 最近3次
        recent_str = ", ".join([f"{s['date'][-6:]}@{s['price']}" for s in recent])
        print(f"{rank:<6} {symbol:<12} {count:<8} {avg_price:>10.2f}  {recent_str}")
    
    print()
    print("[ SELL SIGNAL FREQUENCY ]")
    print("-" * 80)
    
    sell_freq = [(symbol, len(signals)) for symbol, signals in sell_signals.items()]
    sell_freq.sort(key=lambda x: x[1], reverse=True)
    
    print(f"{'Rank':<6} {'Symbol':<12} {'Count':<8} {'Avg Price':<12} {'Recent Signals'}")
    print("-" * 80)
    
    for rank, (symbol, count) in enumerate(sell_freq[:20], 1):
        prices = [s['price'] for s in sell_signals[symbol]]
        avg_price = np.mean(prices)
        recent = sell_signals[symbol][-3:]
        recent_str = ", ".join([f"{s['date'][-6:]}@{s['price']}" for s in recent])
        print(f"{rank:<6} {symbol:<12} {count:<8} {avg_price:>10.2f}  {recent_str}")
    
    print()
    print("[ SUMMARY ]")
    print("-" * 80)
    print(f"Total buy signals: {sum(len(s) for s in buy_signals.values())}")
    print(f"Unique stocks with buy signals: {len(buy_signals)}")
    print(f"Total sell signals: {sum(len(s) for s in sell_signals.values())}")
    print(f"Unique stocks with sell signals: {len(sell_signals)}")
    print()
    
    # 统计买卖都出现的股票
    both_signals = set(buy_signals.keys()) & set(sell_signals.keys())
    print(f"Stocks with both buy and sell signals: {len(both_signals)}")
    if both_signals:
        print(f"Symbols: {', '.join(list(both_signals)[:10])}")
    print()
    print("=" * 100)


def generate_charts(buy_signals, sell_signals, output_dir='results/realtime_scan'):
    """生成统计图表"""
    if not buy_signals and not sell_signals:
        print("No data to chart")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. 买点频率Top15
    ax = axes[0, 0]
    if buy_signals:
        buy_freq = [(s, len(v)) for s, v in buy_signals.items()]
        buy_freq.sort(key=lambda x: x[1], reverse=True)
        top15 = buy_freq[:15]
        
        symbols = [x[0] for x in top15]
        counts = [x[1] for x in top15]
        
        ax.barh(range(len(symbols)), counts, color='green', alpha=0.7)
        ax.set_yticks(range(len(symbols)))
        ax.set_yticklabels(symbols)
        ax.set_xlabel('Signal Count')
        ax.set_title('Top 15 Stocks by Buy Signal Frequency')
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3, axis='x')
    
    # 2. 卖点频率Top15
    ax = axes[0, 1]
    if sell_signals:
        sell_freq = [(s, len(v)) for s, v in sell_signals.items()]
        sell_freq.sort(key=lambda x: x[1], reverse=True)
        top15 = sell_freq[:15]
        
        symbols = [x[0] for x in top15]
        counts = [x[1] for x in top15]
        
        ax.barh(range(len(symbols)), counts, color='red', alpha=0.7)
        ax.set_yticks(range(len(symbols)))
        ax.set_yticklabels(symbols)
        ax.set_xlabel('Signal Count')
        ax.set_title('Top 15 Stocks by Sell Signal Frequency')
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3, axis='x')
    
    # 3. 信号类型分布
    ax = axes[1, 0]
    
    buy_type1 = sum(1 for signals in buy_signals.values() for s in signals if '1' in s['type'])
    buy_type2 = sum(1 for signals in buy_signals.values() for s in signals if '2' in s['type'])
    sell_type1 = sum(1 for signals in sell_signals.values() for s in signals if '1' in s['type'])
    sell_type2 = sum(1 for signals in sell_signals.values() for s in signals if '2' in s['type'])
    
    categories = ['Type 1\nBuy', 'Type 2\nBuy', 'Type 1\nSell', 'Type 2\nSell']
    values = [buy_type1, buy_type2, sell_type1, sell_type2]
    colors = ['darkgreen', 'lightgreen', 'darkred', 'lightcoral']
    
    ax.bar(categories, values, color=colors, alpha=0.8, edgecolor='black')
    ax.set_ylabel('Count')
    ax.set_title('Signal Type Distribution')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4. 每日信号数量趋势
    ax = axes[1, 1]
    
    daily_counts = defaultdict(lambda: {'buy': 0, 'sell': 0})
    for symbol, signals in buy_signals.items():
        for s in signals:
            date = s['date'][:8]  # YYYYMMDD
            daily_counts[date]['buy'] += 1
    
    for symbol, signals in sell_signals.items():
        for s in signals:
            date = s['date'][:8]
            daily_counts[date]['sell'] += 1
    
    if daily_counts:
        dates = sorted(daily_counts.keys())
        buy_counts = [daily_counts[d]['buy'] for d in dates]
        sell_counts = [daily_counts[d]['sell'] for d in dates]
        
        x = range(len(dates))
        ax.plot(x, buy_counts, 'g-o', label='Buy', linewidth=2, markersize=6)
        ax.plot(x, sell_counts, 'r-s', label='Sell', linewidth=2, markersize=6)
        ax.set_xticks(x)
        ax.set_xticklabels([d[-4:] for d in dates], rotation=45)
        ax.set_xlabel('Date')
        ax.set_ylabel('Signal Count')
        ax.set_title('Daily Signal Count Trend')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    chart_file = f'{output_dir}/history_analysis_{datetime.now().strftime("%Y%m%d")}.png'
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Chart saved: {chart_file}")


def export_to_csv(buy_signals, sell_signals, output_dir='results/realtime_scan'):
    """导出详细记录到CSV"""
    
    # 买点记录
    if buy_signals:
        buy_records = []
        for symbol, signals in buy_signals.items():
            for s in signals:
                buy_records.append({
                    'symbol': symbol,
                    'date': s['date'],
                    'type': s['type'],
                    'price': s['price']
                })
        buy_df = pd.DataFrame(buy_records)
        buy_file = f'{output_dir}/buy_history_all.csv'
        buy_df.to_csv(buy_file, index=False, encoding='utf-8-sig')
        print(f"Buy history saved: {buy_file}")
    
    # 卖点记录
    if sell_signals:
        sell_records = []
        for symbol, signals in sell_signals.items():
            for s in signals:
                sell_records.append({
                    'symbol': symbol,
                    'date': s['date'],
                    'type': s['type'],
                    'price': s['price']
                })
        sell_df = pd.DataFrame(sell_records)
        sell_file = f'{output_dir}/sell_history_all.csv'
        sell_df.to_csv(sell_file, index=False, encoding='utf-8-sig')
        print(f"Sell history saved: {sell_file}")


def main():
    """主函数"""
    print("Loading scan history...")
    results = load_scan_results()
    
    if not results:
        print("No scan history found. Please run scan_signals_realtime.py first.")
        return
    
    print(f"Loaded {len(results)} scan records")
    print()
    
    # 分析频率
    buy_signals, sell_signals = analyze_signal_frequency(results)
    
    # 生成统计
    generate_statistics(buy_signals, sell_signals)
    
    # 生成图表
    print("Generating charts...")
    generate_charts(buy_signals, sell_signals)
    
    # 导出CSV
    print("Exporting to CSV...")
    export_to_csv(buy_signals, sell_signals)
    
    print()
    print("Analysis complete!")


if __name__ == '__main__':
    main()
