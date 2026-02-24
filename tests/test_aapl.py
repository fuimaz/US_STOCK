import pandas as pd
from chan_theory import ChanTheory

# Load cached data
data = pd.read_csv('data_cache/AAPL_1y_1d_forward.csv')
data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
data = data.set_index('datetime')
data = data[['Open', 'High', 'Low', 'Close', 'Volume']]

chan = ChanTheory(k_type='day')
result = chan.analyze(data)

print('=== Chan Theory Results ===')
print(f"Fenxing: {len(chan.fenxing_list)}")
print(f"Bi: {len(chan.bi_list)}")
print(f"Xianduan: {len(chan.xianduan_list)}")
print(f"Zhongshu: {len(chan.zhongshu_list)}")
print(f"Buy: {len(chan.buy_points)}")
print(f"Sell: {len(chan.sell_points)}")

print('\nXianduan details:')
for xd in chan.xianduan_list:
    t = 'Up' if xd['type']==1 else 'Dn'
    print(f"  {xd['start'].strftime('%m-%d')} -> {xd['end'].strftime('%m-%d')} ({t}) Bi: {len(xd['bi_list'])}")

print('\nZhongshu details:')
for zs in chan.zhongshu_list:
    print(f"  {zs['start'].strftime('%m-%d')} -> {zs['end'].strftime('%m-%d')} Range: [{zs['low']:.1f}, {zs['high']:.1f}]")

print('\nBuy points:')
for bp in chan.buy_points:
    print(f"  {bp['date'].strftime('%m-%d')} {bp['desc']} ${bp['price']:.2f}")

print('\nSell points:')
for sp in chan.sell_points:
    print(f"  {sp['date'].strftime('%m-%d')} {sp['desc']} ${sp['price']:.2f}")
