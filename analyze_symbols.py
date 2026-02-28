import pandas as pd
import numpy as np
import sys
import os
sys.path.insert(0, '.')
from indicators.boll.boll_volume_strategy import BollVolumeStrategy
from backtests.backtest_boll_volume_strategy import run_backtest

symbols = ['002460.SZ', '002129.SZ', '000533.SZ', '600346.SS', '601318.SS', '300033.SZ', '002028.SZ']

for sym in symbols:
    try:
        f = f'data_cache/{sym}_20y_1d_forward.csv'
        d = pd.read_csv(f)
        d['datetime'] = pd.to_datetime(d['datetime'], utc=True).dt.tz_localize(None)
        d = d.set_index('datetime').sort_index()
        w = d[['Open','High','Low','Close','Volume']].resample('W-FRI').agg({
            'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'
        }).dropna()
        
        strat = BollVolumeStrategy()
        result = run_backtest(w, strat)
        
        out_dir = f'results/boll_volume_strategy_weekly_cached/analysis_{sym}'
        os.makedirs(out_dir, exist_ok=True)
        result['signals'].to_csv(f'{out_dir}/signals.csv', encoding='utf-8-sig')
        result['trades'].to_csv(f'{out_dir}/trades.csv', index=False, encoding='utf-8-sig')
        result['equity_curve'].to_csv(f'{out_dir}/equity.csv', encoding='utf-8-sig')
        
        print(f'\n=== {sym} ===')
        print(f"总收益: {result['total_return_pct']:.2f}%")
        print(f"年化: {result['annualized_return_pct']:.2f}%")
        print(f"胜率: {result['win_rate_pct']:.1f}%")
        print(f"交易次数: {result['total_trades']}")
        print(f"最大回撤: {result['max_drawdown_pct']:.2f}%")
        print(f"夏普: {result['sharpe_ratio']:.2f}")
        
        trades = result['trades']
        if len(trades) > 0:
            buys = trades[trades['type']=='buy']
            sells = trades[trades['type']=='sell']
            print(f"买入: {len(buys)}, 卖出: {len(sells)}")
            if len(sells) > 0 and 'reason' in sells.columns:
                reasons = sells['reason'].value_counts()
                print(f"卖出原因: {dict(reasons)}")
                
        # 分析信号触发情况
        sig = result['signals']
        buy_probe = sig['buy_probe'].sum() if 'buy_probe' in sig.columns else 0
        buy_break = sig['buy_breakout'].sum() if 'buy_breakout' in sig.columns else 0
        buy_add = sig['buy_add'].sum() if 'buy_add' in sig.columns else 0
        sell_reduce = sig['sell_reduce'].sum() if 'sell_reduce' in sig.columns else 0
        sell_exit = sig['sell_exit'].sum() if 'sell_exit' in sig.columns else 0
        print(f"信号统计: probe={buy_probe}, breakout={buy_break}, add={buy_add}, reduce={sell_reduce}, exit={sell_exit}")
        
    except Exception as e:
        print(f'{sym} error: {e}')
        import traceback
        traceback.print_exc()
