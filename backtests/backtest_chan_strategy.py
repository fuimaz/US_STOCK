"""
缂犺绛栫暐鍥炴祴 - 10骞存暟鎹?
浣跨敤鏂扮殑chan_theory.py瀹炵幇
"""
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from chan_theory import ChanTheory
from backtest_engine import BacktestEngine, BaseStrategy

# 璁剧疆涓枃瀛椾綋
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class ChanTheoryStrategy(BaseStrategy):
    """
    缂犺浜ゆ槗绛栫暐
    
    绛栫暐閫昏緫锛?
    - 涔板叆淇″彿锛氬嚭鐜扮涓€绫讳拱鐐规垨绗簩绫讳拱鐐?
    - 鍗栧嚭淇″彿锛氬嚭鐜扮涓€绫诲崠鐐规垨绗簩绫诲崠鐐?
    """
    
    def __init__(self, k_type='day'):
        super().__init__(name="ChanTheory_Strategy")
        self.k_type = k_type
        self.chan = ChanTheory(k_type=k_type)
        self.buy_points = []
        self.sell_points = []
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        鐢熸垚浜ゆ槗淇″彿

        Args:
            data: OHLCV鏁版嵁

        Returns:
            娣诲姞浜嗕俊鍙峰垪鐨凞ataFrame
        """
        df = data.copy()

        # 鍒濆鍖栦俊鍙峰垪
        df['signal'] = 0  # 0:鏃犱俊鍙? 1:涔板叆, -1:鍗栧嚭
        df['buy_point'] = 0
        df['sell_point'] = 0

        # 淇濆瓨鈥滈娆″彲瑙佲€濈殑淇″彿锛岄伩鍏嶅叏閲忓洖濉墠瑙?
        self.buy_points = []
        self.sell_points = []
        seen_buy = set()
        seen_sell = set()

        for i in range(len(df)):
            hist = df.iloc[:i + 1]
            current_idx = hist.index[-1]

            chan_now = ChanTheory(k_type=self.k_type)
            chan_now.analyze(hist)

            new_buy_types = []
            for bp in chan_now.buy_points:
                bp_type = int(bp.get('type', 0))
                if bp_type not in (1, 2):
                    continue
                bp_idx = bp.get('index', bp.get('date'))
                key = (pd.Timestamp(bp_idx), bp_type)
                if key in seen_buy:
                    continue
                seen_buy.add(key)
                new_buy_types.append(bp_type)

            new_sell_types = []
            for sp in chan_now.sell_points:
                sp_type = int(sp.get('type', 0))
                if sp_type not in (1, 2):
                    continue
                sp_idx = sp.get('index', sp.get('date'))
                key = (pd.Timestamp(sp_idx), sp_type)
                if key in seen_sell:
                    continue
                seen_sell.add(key)
                new_sell_types.append(sp_type)

            # 鍚屾棩鍐茬獊鏃讹紝鍗栧嚭浼樺厛锛屾洿淇濆畧
            if new_sell_types:
                sig_type = max(new_sell_types)
                df.loc[current_idx, 'signal'] = -1
                df.loc[current_idx, 'sell_point'] = sig_type
                self.sell_points.append({
                    'index': current_idx,
                    'date': current_idx,
                    'type': sig_type,
                    'price': float(hist['Close'].iloc[-1]),
                })
            elif new_buy_types:
                sig_type = max(new_buy_types)
                df.loc[current_idx, 'signal'] = 1
                df.loc[current_idx, 'buy_point'] = sig_type
                self.buy_points.append({
                    'index': current_idx,
                    'date': current_idx,
                    'type': sig_type,
                    'price': float(hist['Close'].iloc[-1]),
                })

            self.chan = chan_now

        return df


def load_stock_data(symbol, period='10y'):
    """
    鍔犺浇鑲＄エ鏁版嵁
    
    Args:
        symbol: 鑲＄エ浠ｇ爜
        period: 鏁版嵁鍛ㄦ湡
        
    Returns:
        DataFrame鎴朜one
    """
    cache_file = f'data_cache/{symbol}_{period}_1d_forward.csv'
    
    if not os.path.exists(cache_file):
        # 灏濊瘯鍏朵粬鏂囦欢鍚嶆牸寮?
        cache_file = f'data_cache/{symbol}_{period}_1d_none.csv'
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        data = pd.read_csv(cache_file)
        
        # 澶勭悊鏃堕棿鍒?
        if 'datetime' in data.columns:
            data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
            data = data.set_index('datetime')
        elif 'Date' in data.columns:
            data['Date'] = pd.to_datetime(data['Date'])
            data = data.set_index('Date')
        
        # 鍙繚鐣橭HLCV鍒?
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [c for c in required_cols if c in data.columns]
        data = data[available_cols].copy()
        
        # 鍒犻櫎NaN鍊?
        data = data.dropna()
        
        return data
    except Exception as e:
        print(f"  Error loading {symbol}: {e}")
        return None


def backtest_stock(symbol, data, initial_capital=100000):
    """
    瀵瑰崟鍙偂绁ㄨ繘琛屽洖娴?
    
    Args:
        symbol: 鑲＄エ浠ｇ爜
        data: 鑲＄エ鏁版嵁
        initial_capital: 鍒濆璧勯噾
        
    Returns:
        鍥炴祴缁撴灉瀛楀吀
    """
    if data is None or len(data) < 100:
        return None
    
    # 鍒涘缓绛栫暐鍜屽洖娴嬪紩鎿?
    strategy = ChanTheoryStrategy(k_type='day')
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=0.001,  # 0.1%鎵嬬画璐?
        slippage=0.0001    # 0.01%婊戠偣
    )
    
    # 杩愯鍥炴祴
    results = engine.run_backtest(data, strategy)
    results['symbol'] = symbol
    results['strategy_name'] = strategy.name
    results['data_points'] = len(data)
    results['date_range'] = f"{data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}"
    
    # 淇濆瓨涔板崠鐐逛俊鎭?
    results['buy_points'] = strategy.buy_points
    results['sell_points'] = strategy.sell_points
    
    return results


def print_backtest_results(results):
    """
    鎵撳嵃鍥炴祴缁撴灉
    
    Args:
        results: 鍥炴祴缁撴灉瀛楀吀
    """
    if results is None:
        print("No results to display")
        return
    
    symbol = results.get('symbol', 'Unknown')
    
    print("\n" + "="*70)
    print(f"鍥炴祴缁撴灉 - {symbol}")
    print("="*70)
    print(f"鏁版嵁鍖洪棿: {results.get('date_range', 'N/A')}")
    print(f"鏁版嵁鐐规暟: {results.get('data_points', 0)}")
    print(f"鍒濆璧勯噾: ${results.get('initial_capital', 100000):,.2f}")
    print(f"鏈€缁堣祫閲? ${results['final_capital']:,.2f}")
    print(f"鎬绘敹鐩婄巼: {results['total_return_pct']:.2f}%")
    print(f"骞村寲鏀剁泭鐜? {results['annualized_return_pct']:.2f}%")
    print(f"澶忔櫘姣旂巼: {results['sharpe_ratio']:.2f}")
    print(f"鏈€澶у洖鎾? {results['max_drawdown_pct']:.2f}%")
    print(f"鑳滅巼: {results['win_rate_pct']:.2f}%")
    print(f"娉㈠姩鐜? {results['volatility_pct']:.2f}%")
    print(f"鎬讳氦鏄撴鏁? {results['total_trades']}")
    print(f"涔扮偣鏁伴噺: {len(results.get('buy_points', []))}")
    print(f"鍗栫偣鏁伴噺: {len(results.get('sell_points', []))}")
    print("="*70 + "\n")


def plot_backtest_results(symbol, data, results, output_dir='results/chan_backtest'):
    """
    缁樺埗鍥炴祴缁撴灉鍥捐〃
    
    Args:
        symbol: 鑲＄エ浠ｇ爜
        data: 鑲＄エ鏁版嵁
        results: 鍥炴祴缁撴灉
        output_dir: 杈撳嚭鐩綍
    """
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    fig.suptitle(f'{symbol} - Chan Theory Strategy Backtest', fontsize=16, fontweight='bold')
    
    # 1. 浠锋牸璧板娍鍜屼拱鍗栫偣
    ax1 = axes[0]
    ax1.plot(data.index, data['Close'], label='Close Price', linewidth=1.5, color='black', alpha=0.8)
    
    # 鏍囪涔扮偣
    for bp in results.get('buy_points', []):
        if bp['index'] in data.index:
            color = 'red' if bp['type'] == 1 else 'orange'
            ax1.scatter(bp['index'], bp['price'], color=color, marker='^', s=150, 
                       zorder=5, edgecolors='black', linewidths=1.5, label=f'Buy Type {bp["type"]}' if bp == results['buy_points'][0] else '')
    
    # 鏍囪鍗栫偣
    for sp in results.get('sell_points', []):
        if sp['index'] in data.index:
            color = 'green' if sp['type'] == 1 else 'cyan'
            ax1.scatter(sp['index'], sp['price'], color=color, marker='v', s=150,
                       zorder=5, edgecolors='black', linewidths=1.5, label=f'Sell Type {sp["type"]}' if sp == results['sell_points'][0] else '')
    
    ax1.set_ylabel('Price', fontsize=12)
    ax1.set_title('Price Chart with Buy/Sell Points', fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 2. 璧勯噾鏇茬嚎
    ax2 = axes[1]
    equity_curve = results['equity_curve']
    ax2.plot(equity_curve.index, equity_curve['equity'], label='Portfolio Value', 
            linewidth=2, color='blue', alpha=0.8)
    ax2.axhline(y=results.get('initial_capital', 100000), color='gray', 
               linestyle='--', alpha=0.5, label='Initial Capital')
    ax2.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax2.set_title(f'Equity Curve (Return: {results["total_return_pct"]:.2f}%)', fontsize=14)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # 3. 鍥炴挙
    ax3 = axes[2]
    equity = equity_curve['equity']
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100
    ax3.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3, label='Drawdown')
    ax3.set_ylabel('Drawdown (%)', fontsize=12)
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_title(f'Drawdown (Max: {results["max_drawdown_pct"]:.2f}%)', fontsize=14)
    ax3.legend(loc='lower left')
    ax3.grid(True, alpha=0.3)
    
    # 鏍煎紡鍖杧杞?
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 淇濆瓨鍥捐〃
    chart_file = os.path.join(output_dir, f'{symbol}_backtest.png')
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Chart saved to: {chart_file}")


def run_backtest_on_multiple_stocks(symbols, period='10y'):
    """
    瀵瑰鍙偂绁ㄨ繘琛屽洖娴?
    
    Args:
        symbols: 鑲＄エ浠ｇ爜鍒楄〃
        period: 鏁版嵁鍛ㄦ湡
    """
    print("="*70)
    print(f"Chan Theory Strategy Backtest - {period} Data")
    print("="*70)
    
    all_results = []
    
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        
        # 鍔犺浇鏁版嵁
        data = load_stock_data(symbol, period)
        
        if data is None:
            print(f"  Data not found for {symbol}")
            continue
        
        print(f"  Data loaded: {len(data)} rows")
        print(f"  Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
        
        # 杩愯鍥炴祴
        results = backtest_stock(symbol, data)
        
        if results:
            print_backtest_results(results)
            plot_backtest_results(symbol, data, results)
            all_results.append(results)
        else:
            print(f"  Backtest failed for {symbol}")
    
    # 姹囨€荤粨鏋?
    if all_results:
        print_summary(all_results)
    
    return all_results


def print_summary(all_results):
    """
    鎵撳嵃姹囨€荤粨鏋?
    
    Args:
        all_results: 鎵€鏈夊洖娴嬬粨鏋滃垪琛?
    """
    print("\n" + "="*70)
    print("Summary Statistics")
    print("="*70)
    
    returns = [r['total_return_pct'] for r in all_results]
    annual_returns = [r['annualized_return_pct'] for r in all_results]
    max_dd = [r['max_drawdown_pct'] for r in all_results]
    sharpe = [r['sharpe_ratio'] for r in all_results]
    win_rates = [r['win_rate_pct'] for r in all_results]
    
    print(f"Number of stocks tested: {len(all_results)}")
    print(f"Average total return: {np.mean(returns):.2f}%")
    print(f"Median total return: {np.median(returns):.2f}%")
    print(f"Best return: {np.max(returns):.2f}%")
    print(f"Worst return: {np.min(returns):.2f}%")
    print(f"Win rate (positive return): {sum(1 for r in returns if r > 0) / len(returns) * 100:.1f}%")
    print()
    print(f"Average annualized return: {np.mean(annual_returns):.2f}%")
    print(f"Average max drawdown: {np.mean(max_dd):.2f}%")
    print(f"Average Sharpe ratio: {np.mean(sharpe):.2f}")
    print(f"Average win rate: {np.mean(win_rates):.2f}%")
    print("="*70 + "\n")
    
    # 鎸夋敹鐩婄巼鎺掑簭
    sorted_results = sorted(all_results, key=lambda x: x['total_return_pct'], reverse=True)
    
    print("Top 5 Performers:")
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"  {i}. {r['symbol']}: {r['total_return_pct']:.2f}% (Annual: {r['annualized_return_pct']:.2f}%)")
    
    print("\nBottom 5 Performers:")
    for i, r in enumerate(sorted_results[-5:], 1):
        print(f"  {i}. {r['symbol']}: {r['total_return_pct']:.2f}% (Annual: {r['annualized_return_pct']:.2f}%)")
    
    print("="*70 + "\n")


def main():
    """Main function."""
    # 娴嬭瘯鑲＄エ鍒楄〃
    test_symbols = [
        'AAPL',      # 鑻规灉
        'MSFT',      # 寰蒋
        'GOOGL',     # 璋锋瓕
        'AMZN',      # 浜氶┈閫?
        'TSLA',      # 鐗规柉鎷?
        'NVDA',      # 鑻变紵杈?
        'META',      # Meta
        'BABA',      # 闃块噷宸村反
        '601186.SS', # 涓浗閾佸缓
        '600519.SS', # 璐靛窞鑼呭彴
    ]
    
    # 杩愯鍥炴祴
    results = run_backtest_on_multiple_stocks(test_symbols, period='10y')
    
    print("\nBacktest completed!")


if __name__ == '__main__':
    main()

