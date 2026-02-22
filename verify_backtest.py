"""
验证回测是否存在未来函数
"""
import pandas as pd
import numpy as np
from datetime import timedelta
from chan_theory import ChanTheory


def load_stock_data(symbol, period='20y'):
    cache_file = f'data_cache/{symbol}_{period}_1d_forward.csv'
    data = pd.read_csv(cache_file)
    data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
    data = data.set_index('datetime')
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    return data


def check_lookahead_bias(symbol):
    """
    检查是否存在未来函数
    
    问题：使用完整数据（20年）生成买卖点，但只在近10年回测
    这会导致未来信息泄露吗？
    """
    print(f"\n{'='*70}")
    print(f"验证: {symbol}")
    print(f"{'='*70}")
    
    # 加载完整数据
    data_full = load_stock_data(symbol, '20y')
    
    # 定义回测区间（近10年）
    end_date = data_full.index[-1]
    start_date = end_date - timedelta(days=10*365)
    
    print(f"完整数据区间: {data_full.index[0].strftime('%Y-%m-%d')} ~ {data_full.index[-1].strftime('%Y-%m-%d')} ({len(data_full)}天)")
    print(f"回测区间: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} ({len(data_full[data_full.index >= start_date])}天)")
    
    # 方法1：使用完整数据（当前做法）
    print("\n方法1：使用完整数据（20年）生成买卖点")
    chan_full = ChanTheory(k_type='day')
    chan_full.analyze(data_full)
    
    buy_points_full = [bp for bp in chan_full.buy_points if bp['index'] >= start_date]
    sell_points_full = [sp for sp in chan_full.sell_points if sp['index'] >= start_date]
    
    print(f"  买点数量: {len(buy_points_full)}")
    print(f"  卖点数量: {len(sell_points_full)}")
    if buy_points_full:
        print(f"  第一个买点: {buy_points_full[0]['date'].strftime('%Y-%m-%d')} @ {buy_points_full[0]['price']:.2f}")
    if sell_points_full:
        print(f"  第一个卖点: {sell_points_full[0]['date'].strftime('%Y-%m-%d')} @ {sell_points_full[0]['price']:.2f}")
    
    # 方法2：只使用回测区间数据（应该采用的做法）
    print("\n方法2：只使用回测区间数据（10年）生成买卖点")
    data_backtest = data_full[data_full.index >= start_date].copy()
    chan_backtest = ChanTheory(k_type='day')
    chan_backtest.analyze(data_backtest)
    
    buy_points_backtest = chan_backtest.buy_points
    sell_points_backtest = chan_backtest.sell_points
    
    print(f"  买点数量: {len(buy_points_backtest)}")
    print(f"  卖点数量: {len(sell_points_backtest)}")
    if buy_points_backtest:
        print(f"  第一个买点: {buy_points_backtest[0]['date'].strftime('%Y-%m-%d')} @ {buy_points_backtest[0]['price']:.2f}")
    if sell_points_backtest:
        print(f"  第一个卖点: {sell_points_backtest[0]['date'].strftime('%Y-%m-%d')} @ {sell_points_backtest[0]['price']:.2f}")
    
    # 对比
    print("\n对比:")
    print(f"  买点差异: {len(buy_points_full)} vs {len(buy_points_backtest)}")
    print(f"  卖点差异: {len(sell_points_full)} vs {len(sell_points_backtest)}")
    
    # 检查前10年的数据是否影响了后10年的买卖点
    print("\n未来函数检查:")
    if len(buy_points_full) != len(buy_points_backtest):
        print(f"  ⚠️  警告：使用完整数据 vs 回测数据生成的买卖点数量不同！")
        print(f"     这意味着前10年的数据影响了后10年的买卖点判断")
        print(f"     存在未来函数（lookahead bias）！")
        
        # 找出差异
        if len(buy_points_full) > 0 and len(buy_points_backtest) > 0:
            print(f"\n     完整数据的第一个买点: {buy_points_full[0]['date'].strftime('%Y-%m-%d')}")
            print(f"     回测数据的第一个买点: {buy_points_backtest[0]['date'].strftime('%Y-%m-%d')}")
    else:
        print(f"  ✅ 买卖点数量相同，可能没有明显的未来函数")
    
    return {
        'symbol': symbol,
        'buy_full': len(buy_points_full),
        'sell_full': len(sell_points_full),
        'buy_backtest': len(buy_points_backtest),
        'sell_backtest': len(sell_points_backtest)
    }


def main():
    print("="*70)
    print("回测未来函数验证")
    print("="*70)
    print("\n检查使用完整数据（20年）vs 回测数据（10年）生成的买卖点是否一致")
    print("如果不一致，说明存在未来函数！")
    
    symbols = ['000001.SZ', '000333.SZ', '600519.SS', '601888.SS']
    
    results = []
    for symbol in symbols:
        result = check_lookahead_bias(symbol)
        results.append(result)
    
    print("\n" + "="*70)
    print("汇总")
    print("="*70)
    for r in results:
        diff_buy = r['buy_full'] - r['buy_backtest']
        diff_sell = r['sell_full'] - r['sell_backtest']
        status = "❌ 有未来函数" if diff_buy != 0 or diff_sell != 0 else "✅ 正常"
        print(f"{r['symbol']}: 买点 {r['buy_full']} vs {r['buy_backtest']} (差异{diff_buy:+d}), 卖点 {r['sell_full']} vs {r['sell_backtest']} (差异{diff_sell:+d}) {status}")


if __name__ == '__main__':
    main()
