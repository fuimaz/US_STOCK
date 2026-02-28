"""
A鑲℃渶杩?骞寸儹闂ㄨ偂绁ㄧ紶璁哄疄鏃舵柟妗堝洖娴?
鑾峰彇杩?骞存定骞呭墠鍒楃殑鐑棬鑲＄エ杩涜鍥炴祴
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from chan_theory_realtime import ChanTheoryRealtime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# 鏈€杩?骞碅鑲＄儹闂ㄨ偂绁紙鎸夎繎1骞存定骞呭拰琛屼笟鐑害閫夊彇锛?
HOT_STOCKS_1Y = [
    # AI/浜哄伐鏅鸿兘姒傚康 (2024-2025骞存渶鐑棬)
    ('002230.SZ', '绉戝ぇ璁', 'AI'),
    ('000977.SZ', '娴疆淇℃伅', 'AI鏈嶅姟鍣?),
    ('002475.SZ', '绔嬭绮惧瘑', 'AI纭欢'),
    
    # 浜哄舰鏈哄櫒浜?(2024涓嬪崐骞?2025鏈€鐑棬)
    ('002050.SZ', '涓夎姳鏅烘帶', '鏈哄櫒浜?),
    ('300124.SZ', '姹囧窛鎶€鏈?, '鏈哄櫒浜?),
    
    # 绠楀姏/鏁版嵁涓績
    ('600941.SS', '涓浗绉诲姩', '绠楀姏'),
    
    # 鏂拌兘婧愯溅
    ('300750.SZ', '瀹佸痉鏃朵唬', '鏂拌兘婧?),
    ('002594.SZ', '姣斾簹杩?, '鏂拌兘婧?),
    ('601012.SS', '闅嗗熀缁胯兘', '鍏変紡'),
    
    # 閾惰锛?024琛ㄧ幇杈冨ソ锛?
    ('600036.SS', '鎷涘晢閾惰', '閾惰'),
    ('000001.SZ', '骞冲畨閾惰', '閾惰'),
    ('601398.SS', '宸ュ晢閾惰', '閾惰'),
    
    # 娑堣垂/鐧介厭
    ('600519.SS', '璐靛窞鑼呭彴', '鐧介厭'),
    ('000858.SZ', '浜旂伯娑?, '鐧介厭'),
    ('000333.SZ', '缇庣殑闆嗗洟', '瀹剁數'),
    
    # 鍖昏嵂
    ('600276.SS', '鎭掔憺鍖昏嵂', '鍖昏嵂'),
    ('300760.SZ', '杩堢憺鍖荤枟', '鍖昏嵂'),
    
    # 楂樿偂鎭?绾㈠埄 (2024骞磋〃鐜板ソ)
    ('601088.SS', '涓浗绁炲崕', '鐓ょ偔'),
    ('600900.SS', '闀挎睙鐢靛姏', '鐢靛姏'),
    ('601899.SS', '绱噾鐭夸笟', '鏈夎壊'),
]


def load_cached_data(symbol, period='20y'):
    """浠庣紦瀛樺姞杞借偂绁ㄦ暟鎹?""
    cache_file = f'data_cache/{symbol}_{period}_1d_forward.csv'
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        data = pd.read_csv(cache_file)
        if 'datetime' in data.columns:
            data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
            data = data.set_index('datetime')
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        data = data.dropna()
        return data
    except Exception as e:
        print(f"  Error loading cache: {e}")
        return None


def backtest_chan_realtime(data, symbol, initial_capital=100000):
    """
    缂犺瀹炴椂鏂规鍥炴祴锛堟棤寤惰繜锛屾棤鏈潵鍑芥暟锛?
    """
    if data is None or len(data) < 60:
        return None
    
    # 鍙娇鐢ㄨ繎1骞存暟鎹?
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=365)
    data_backtest = data[data.index >= start_date].copy()
    
    if len(data_backtest) < 30:
        return None
    
    # 浣跨敤缂犺鍒嗘瀽 - 瀹炴椂杩戜技鏂规
    chan = ChanTheoryRealtime(k_type='day')
    result = chan.analyze(data)
    
    # 鑾峰彇鍥炴祴鍖洪棿鍐呯殑涔板崠鐐?
    buy_points = [bp for bp in chan.buy_points if bp['index'] in data_backtest.index and bp['type'] in [1, 2]]
    sell_points = [sp for sp in chan.sell_points if sp['index'] in data_backtest.index and sp['type'] in [1, 2]]
    
    # 鍥炴祴浜ゆ槗
    capital = initial_capital
    position = 0
    trades = []
    
    # 鍚堝苟淇″彿
    all_signals = []
    for bp in buy_points:
        all_signals.append({'date': bp['index'], 'type': 'buy', 'price': bp['price'], 'bp_type': bp['type']})
    for sp in sell_points:
        all_signals.append({'date': sp['index'], 'type': 'sell', 'price': sp['price'], 'sp_type': sp['type']})
    
    all_signals.sort(key=lambda x: x['date'])
    
    # 浜ゆ槗璐圭敤
    commission = 0.001  # 0.1% 浣ｉ噾
    slippage = 0.0005   # 0.05% 婊戠偣
    
    for signal in all_signals:
        current_price = signal['price']
        
        if signal['type'] == 'buy' and position == 0:
            # 涔板叆
            shares = capital / (current_price * (1 + slippage))
            cost = shares * current_price * (1 + slippage) * (1 + commission)
            capital -= cost
            position = shares
            trades.append({
                'type': 'buy', 
                'date': signal['date'], 
                'price': current_price, 
                'value': cost,
                'bp_type': signal.get('bp_type', 1)
            })
            
        elif signal['type'] == 'sell' and position > 0:
            # 鍗栧嚭
            proceeds = position * current_price * (1 - slippage) * (1 - commission)
            capital += proceeds
            trades.append({
                'type': 'sell', 
                'date': signal['date'], 
                'price': current_price, 
                'value': proceeds,
                'sp_type': signal.get('sp_type', 1)
            })
            position = 0
    
    # 璁＄畻鏈€缁堜环鍊?
    final_price = data_backtest['Close'].iloc[-1]
    if position > 0:
        final_value = capital + position * final_price * (1 - slippage) * (1 - commission)
    else:
        final_value = capital
    
    # 璁＄畻鏀剁泭
    total_return = (final_value - initial_capital) / initial_capital * 100
    years = len(data_backtest) / 252
    annualized = ((final_value / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # 璁＄畻涔板叆鎸佹湁鏀剁泭
    first_price = data_backtest['Close'].iloc[0]
    buyhold_return = (final_price - first_price) / first_price * 100
    buyhold_annualized = ((final_price / first_price) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # 璁＄畻鑳滅巼
    profits = []
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    
    for i, buy in enumerate(buy_trades):
        if i < len(sell_trades):
            profit = (sell_trades[i]['value'] - buy['value']) / buy['value']
            profits.append(profit)
    
    win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100 if profits else 0
    avg_profit = np.mean(profits) * 100 if profits else 0
    max_profit = max(profits) * 100 if profits else 0
    max_loss = min(profits) * 100 if profits else 0
    
    # 璁＄畻鏈€澶у洖鎾?
    equity_curve = [initial_capital]
    for trade in trades:
        if trade['type'] == 'sell':
            equity_curve.append(trade['value'])
    
    max_drawdown = 0
    peak = initial_capital
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return {
        'symbol': symbol,
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized,
        'buyhold_return': buyhold_return,
        'buyhold_annualized': buyhold_annualized,
        'excess_return': total_return - buyhold_return,
        'win_rate': win_rate,
        'trade_count': len(profits),
        'buy_count': len(buy_points),
        'sell_count': len(sell_points),
        'avg_profit': avg_profit,
        'max_profit': max_profit,
        'max_loss': max_loss,
        'max_drawdown': max_drawdown,
        'trades': trades,
        'data': data_backtest,
        'buy_points': buy_points,
        'sell_points': sell_points
    }


def generate_charts(result, symbol, name, sector, output_dir='results/hot_stocks_1y'):
    """鐢熸垚K绾垮浘琛?""
    os.makedirs(output_dir, exist_ok=True)
    
    data = result['data']
    buy_points = result['buy_points']
    sell_points = result['sell_points']
    
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    # 涓诲浘锛欿绾?
    ax1 = axes[0]
    
    # 缁樺埗K绾?
    from mplfinance.original_flavor import candlestick_ohlc
    import matplotlib.dates as mdates
    
    # 鍑嗗鏁版嵁
    df_plot = data.reset_index()
    date_col = 'datetime' if 'datetime' in df_plot.columns else df_plot.columns[0]
    df_plot['Date'] = pd.to_datetime(df_plot[date_col])
    df_plot['Date'] = df_plot['Date'].map(mdates.date2num)
    
    ohlc = df_plot[['Date', 'Open', 'High', 'Low', 'Close']].values
    candlestick_ohlc(ax1, ohlc, width=0.6, colorup='red', colordown='green', alpha=0.8)
    
    # 鏍囪涔板崠鐐?
    first_buy = True
    first_sell = True
    for bp in buy_points:
        marker_size = 150 if bp['type'] == 1 else 120
        marker_color = 'blue' if bp['type'] == 1 else 'orange'
        label = f"B{type(bp['type'])}" if bp['type'] == 1 else f"B{type(bp['type'])}"
        ax1.scatter(mdates.date2num(bp['index']), bp['price'], marker='^', s=marker_size, 
                   color=marker_color, edgecolors='black', linewidth=1.5, zorder=5)
        ax1.annotate(label, (mdates.date2num(bp['index']), bp['price']), 
                    xytext=(5, 10), textcoords='offset points', fontsize=8, color=marker_color)
    
    for sp in sell_points:
        marker_size = 150 if sp['type'] == 1 else 120
        marker_color = 'purple' if sp['type'] == 1 else 'cyan'
        label = f"S{type(sp['type'])}" if sp['type'] == 1 else f"S{type(sp['type'])}"
        ax1.scatter(mdates.date2num(sp['index']), sp['price'], marker='v', s=marker_size,
                   color=marker_color, edgecolors='black', linewidth=1.5, zorder=5)
        ax1.annotate(label, (mdates.date2num(sp['index']), sp['price']), 
                    xytext=(5, -15), textcoords='offset points', fontsize=8, color=marker_color)
    
    ax1.set_title(f'{symbol} {name} ({sector}) - Chan Theory Signals (Last 1 Year)\n'
                  f'Strategy: {result["total_return"]:.1f}% | Buy&Hold: {result["buyhold_return"]:.1f}% | Excess: {result["excess_return"]:+.1f}%',
                  fontsize=14)
    ax1.set_ylabel('Price', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # 鎴愪氦閲?
    ax2 = axes[1]
    colors = ['red' if close >= open else 'green' for open, close in zip(data['Open'], data['Close'])]
    ax2.bar(df_plot['Date'], data['Volume'], color=colors, alpha=0.6, width=0.6)
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{symbol}_signals.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    return f'{output_dir}/{symbol}_signals.png'


def main():
    print("=" * 100)
    print("A鑲＄儹闂ㄨ偂绁ㄧ紶璁哄疄鏃舵柟妗堝洖娴?(杩?骞?")
    print("=" * 100)
    print()
    
    results = []
    success_count = 0
    fail_count = 0
    
    for symbol, name, sector in HOT_STOCKS_1Y:
        print(f"Processing: {name} ({symbol}) - {sector}")
        print("-" * 100)
        
        # 鍔犺浇鏁版嵁
        data = load_cached_data(symbol, period='20y')
        if data is None:
            print(f"  [FAIL] No cached data available\n")
            fail_count += 1
            continue
        
        print(f"  Data points: {len(data)}")
        print(f"  Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
        
        # 鍥炴祴
        result = backtest_chan_realtime(data, symbol)
        if result is None:
            print(f"  [FAIL] Backtest failed\n")
            fail_count += 1
            continue
        
        print(f"  Last 1Y data: {len(result['data'])} bars")
        print(f"  Buy signals: {result['buy_count']}")
        print(f"  Sell signals: {result['sell_count']}")
        print(f"  Trades: {result['trade_count']}")
        print(f"  Win rate: {result['win_rate']:.1f}%")
        print(f"  Strategy return: {result['total_return']:.2f}% (annual {result['annualized_return']:.2f}%)")
        print(f"  Buy&Hold return: {result['buyhold_return']:.2f}% (annual {result['buyhold_annualized']:.2f}%)")
        print(f"  Excess return: {result['excess_return']:+.2f}%")
        print(f"  Max drawdown: {result['max_drawdown']:.2f}%")
        print(f"  Avg profit: {result['avg_profit']:+.2f}%")
        
        # 鐢熸垚鍥捐〃
        chart_path = generate_charts(result, symbol, name, sector)
        print(f"  Chart: {chart_path}")
        
        results.append({
            'symbol': symbol,
            'name': name,
            'sector': sector,
            'total_return': result['total_return'],
            'annualized_return': result['annualized_return'],
            'buyhold_return': result['buyhold_return'],
            'excess_return': result['excess_return'],
            'win_rate': result['win_rate'],
            'trade_count': result['trade_count'],
            'max_drawdown': result['max_drawdown'],
            'avg_profit': result['avg_profit'],
            'chart': chart_path
        })
        
        success_count += 1
        print(f"  [OK] Done\n")
    
    # 姹囨€荤粺璁?
    print("=" * 100)
    print("Backtest Summary")
    print("=" * 100)
    print()
    
    if results:
        df_results = pd.DataFrame(results)
        
        # 鎸夋敹鐩婃帓搴?
        df_results = df_results.sort_values('total_return', ascending=False)
        
        print(f"{'Rank':<4} {'Symbol':<12} {'Name':<10} {'Sector':<10} {'Strategy':<10} {'Buy&Hold':<10} {'Excess':<10} {'WinRate':<8} {'Trades':<8}")
        print("-" * 100)
        
        rank = 1
        for _, row in df_results.iterrows():
            print(f"{rank:<4} {row['symbol']:<12} {row['name']:<10} {row['sector']:<10} "
                  f"{row['total_return']:>8.1f}% {row['buyhold_return']:>8.1f}% "
                  f"{row['excess_return']:>+8.1f}% {row['win_rate']:>6.1f}% {int(row['trade_count']):>6}")
            rank += 1
        
        print("-" * 100)
        print()
        
        # 缁熻鎸囨爣
        print("Overall Statistics:")
        print(f"  Stocks tested: {len(results)}")
        print(f"  Avg strategy return: {df_results['total_return'].mean():.2f}%")
        print(f"  Avg buy&hold return: {df_results['buyhold_return'].mean():.2f}%")
        print(f"  Avg excess return: {df_results['excess_return'].mean():+.2f}%")
        print(f"  Win rate >50%: {sum(df_results['win_rate'] > 50)}/{len(results)}")
        print(f"  Positive excess: {sum(df_results['excess_return'] > 0)}/{len(results)}")
        print(f"  Avg trades: {df_results['trade_count'].mean():.1f}")
        print(f"  Avg max drawdown: {df_results['max_drawdown'].mean():.2f}%")
        print()
        
        # 鎸夎涓氱粺璁?
        print("By Sector:")
        sector_stats = df_results.groupby('sector').agg({
            'total_return': 'mean',
            'buyhold_return': 'mean',
            'excess_return': 'mean',
            'win_rate': 'mean',
            'trade_count': 'mean'
        }).round(2)
        print(sector_stats)
        print()
        
        # 淇濆瓨缁撴灉
        output_file = 'results/hot_stocks_1y_backtest.csv'
        os.makedirs('results', exist_ok=True)
        df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Results saved: {output_file}")
        print()
    
    print(f"[OK]: {success_count} | [FAIL]: {fail_count}")
    print("=" * 100)


if __name__ == '__main__':
    main()

