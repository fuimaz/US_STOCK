import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
from chan_theory_v5 import ChanTheory
from data_fetcher import DataFetcher

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def load_backtest_results():
    """加载回测结果"""
    csv_path = 'results/chan_backtest_all/all_a_stocks_backtest.csv'
    df = pd.read_csv(csv_path)
    return df

def select_stocks(df, top_n=3, bottom_n=3):
    """选择表现最好和最差的股票"""
    
    # 排除交易次数为0的股票
    df_with_trades = df[df['交易次数'] > 0].copy()
    
    # 按累计收益率排序
    df_sorted = df_with_trades.sort_values('累计收益率', ascending=False)
    
    # 选择表现最好的股票（排除单次交易收益过高的异常值）
    top_stocks = df_sorted[df_sorted['交易次数'] >= 2].head(top_n)
    
    # 选择表现最差的股票
    bottom_stocks = df_sorted.tail(bottom_n)
    
    return top_stocks, bottom_stocks

def plot_stock_with_chan_theory(symbol, data, chan, save_path):
    """绘制股票K线图和缠论买卖点"""
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[3, 1])
    
    # 绘制K线图
    colors = ['#ff5252' if data['Close'].iloc[i] >= data['Open'].iloc[i] else '#4caf50' 
              for i in range(len(data))]
    
    ax1.bar(data.index, data['Close'] - data['Open'], bottom=data['Open'], 
            width=0.6, color=colors, alpha=0.8)
    ax1.bar(data.index, data['High'] - data['Close'], bottom=data['Close'], 
            width=0.1, color=colors, alpha=0.8)
    ax1.bar(data.index, data['Low'] - data['Open'], bottom=data['Open'], 
            width=0.1, color=colors, alpha=0.8)
    
    # 绘制买卖点
    buy_points = chan.buy_points
    sell_points = chan.sell_points
    
    if buy_points:
        buy_dates = [bp['index'] for bp in buy_points]
        buy_prices = [bp['price'] for bp in buy_points]
        ax1.scatter(buy_dates, buy_prices, color='red', s=200, marker='^', 
                   label='买点', zorder=5, alpha=0.8)
        for i, (date, price) in enumerate(zip(buy_dates, buy_prices)):
            ax1.annotate(f'买入\n{price:.2f}', xy=(date, price), 
                        xytext=(10, 20), textcoords='offset points',
                        fontsize=8, color='red', fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    if sell_points:
        sell_dates = [sp['index'] for sp in sell_points]
        sell_prices = [sp['price'] for sp in sell_points]
        ax1.scatter(sell_dates, sell_prices, color='green', s=200, marker='v', 
                   label='卖点', zorder=5, alpha=0.8)
        for i, (date, price) in enumerate(zip(sell_dates, sell_prices)):
            ax1.annotate(f'卖出\n{price:.2f}', xy=(date, price), 
                        xytext=(10, -30), textcoords='offset points',
                        fontsize=8, color='green', fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    ax1.set_title(f'{symbol} 缠论买卖点', fontsize=16, fontweight='bold')
    ax1.set_ylabel('价格', fontsize=12)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 格式化x轴
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 绘制成交量
    colors_vol = ['#ff5252' if data['Close'].iloc[i] >= data['Open'].iloc[i] else '#4caf50' 
                  for i in range(len(data))]
    ax2.bar(data.index, data['Volume'], width=0.6, color=colors_vol, alpha=0.6)
    ax2.set_title('成交量', fontsize=12)
    ax2.set_ylabel('成交量', fontsize=10)
    ax2.set_xlabel('日期', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ 图表已保存: {save_path}")

def analyze_and_plot_stocks():
    """分析并绘制股票图表"""
    
    print("=" * 100)
    print("缠论回测结果分析 - 买卖点图表生成")
    print("=" * 100)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/chan_analysis_charts'
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ 结果将保存到: {output_dir}/")
    print()
    
    # 加载回测结果
    df = load_backtest_results()
    print(f"✓ 加载回测结果: {len(df)} 只股票")
    print()
    
    # 选择股票
    top_stocks, bottom_stocks = select_stocks(df, top_n=3, bottom_n=3)
    
    print("表现最好的股票（按累计收益率，交易次数>=2）:")
    print("-" * 100)
    for idx, row in top_stocks.iterrows():
        print(f"  {row['股票代码']}: 累计收益={row['累计收益率']:.2f}%, 胜率={row['胜率']:.2f}%, 交易次数={int(row['交易次数'])}")
    print()
    
    print("表现最差的股票:")
    print("-" * 100)
    for idx, row in bottom_stocks.iterrows():
        print(f"  {row['股票代码']}: 累计收益={row['累计收益率']:.2f}%, 胜率={row['胜率']:.2f}%, 交易次数={int(row['交易次数'])}")
    print()
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # 绘制表现最好的股票
    print("正在生成表现最好股票的买卖点图表...")
    print("-" * 100)
    for idx, row in top_stocks.iterrows():
        symbol = row['股票代码']
        print(f"\n[{symbol}]")
        
        try:
            # 获取数据
            data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
            
            if data is None or len(data) == 0:
                print(f"  ✗ 未获取到数据")
                continue
            
            print(f"  ✓ 数据获取完成，共 {len(data)} 条记录")
            
            # 初始化缠论指标
            chan = ChanTheory(k_type='day')
            
            # 完整分析
            result = chan.analyze(data)
            
            # 绘制图表
            save_path = os.path.join(output_dir, f'{symbol}_top.png')
            plot_stock_with_chan_theory(symbol, data, chan, save_path)
            
            # 打印交易详情
            buy_points = chan.buy_points
            sell_points = chan.sell_points
            
            print(f"  买点数量: {len(buy_points)}")
            print(f"  卖点数量: {len(sell_points)}")
            
            # 计算收益
            trades = []
            for i, buy_point in enumerate(buy_points):
                buy_date = buy_point['index']
                buy_price = buy_point['price']
                
                # 找到下一个卖点
                sell_price = None
                sell_date = None
                
                for sell_point in sell_points:
                    if sell_point['index'] > buy_date:
                        sell_date = sell_point['index']
                        sell_price = sell_point['price']
                        break
                
                # 如果没有卖点，使用最后一个价格
                if sell_price is None:
                    sell_date = data.index[-1]
                    sell_price = data['Close'].iloc[-1]
                
                # 计算收益率
                return_pct = (sell_price - buy_price) / buy_price * 100
                
                trades.append({
                    'buy_date': buy_date,
                    'buy_price': buy_price,
                    'sell_date': sell_date,
                    'sell_price': sell_price,
                    'return_pct': return_pct
                })
            
            print(f"  交易详情:")
            for i, trade in enumerate(trades):
                print(f"    交易{i+1}: {trade['buy_date'].strftime('%Y-%m-%d')} 买入 {trade['buy_price']:.2f} -> "
                      f"{trade['sell_date'].strftime('%Y-%m-%d')} 卖出 {trade['sell_price']:.2f} "
                      f"(收益率: {trade['return_pct']:.2f}%)")
            
        except Exception as e:
            print(f"  ✗ 分析失败: {e}")
    
    # 绘制表现最差的股票
    print("\n\n正在生成表现最差股票的买卖点图表...")
    print("-" * 100)
    for idx, row in bottom_stocks.iterrows():
        symbol = row['股票代码']
        print(f"\n[{symbol}]")
        
        try:
            # 获取数据
            data = fetcher.fetch_stock_data(symbol, period='20y', adjust='forward')
            
            if data is None or len(data) == 0:
                print(f"  ✗ 未获取到数据")
                continue
            
            print(f"  ✓ 数据获取完成，共 {len(data)} 条记录")
            
            # 初始化缠论指标
            chan = ChanTheory(k_type='day')
            
            # 完整分析
            result = chan.analyze(data)
            
            # 绘制图表
            save_path = os.path.join(output_dir, f'{symbol}_bottom.png')
            plot_stock_with_chan_theory(symbol, data, chan, save_path)
            
            # 打印交易详情
            buy_points = chan.buy_points
            sell_points = chan.sell_points
            
            print(f"  买点数量: {len(buy_points)}")
            print(f"  卖点数量: {len(sell_points)}")
            
            # 计算收益
            trades = []
            for i, buy_point in enumerate(buy_points):
                buy_date = buy_point['index']
                buy_price = buy_point['price']
                
                # 找到下一个卖点
                sell_price = None
                sell_date = None
                
                for sell_point in sell_points:
                    if sell_point['index'] > buy_date:
                        sell_date = sell_point['index']
                        sell_price = sell_point['price']
                        break
                
                # 如果没有卖点，使用最后一个价格
                if sell_price is None:
                    sell_date = data.index[-1]
                    sell_price = data['Close'].iloc[-1]
                
                # 计算收益率
                return_pct = (sell_price - buy_price) / buy_price * 100
                
                trades.append({
                    'buy_date': buy_date,
                    'buy_price': buy_price,
                    'sell_date': sell_date,
                    'sell_price': sell_price,
                    'return_pct': return_pct
                })
            
            print(f"  交易详情:")
            for i, trade in enumerate(trades):
                print(f"    交易{i+1}: {trade['buy_date'].strftime('%Y-%m-%d')} 买入 {trade['buy_price']:.2f} -> "
                      f"{trade['sell_date'].strftime('%Y-%m-%d')} 卖出 {trade['sell_price']:.2f} "
                      f"(收益率: {trade['return_pct']:.2f}%)")
            
        except Exception as e:
            print(f"  ✗ 分析失败: {e}")
    
    print("\n" + "=" * 100)
    print("分析完成！")
    print("=" * 100)

if __name__ == '__main__':
    analyze_and_plot_stocks()
