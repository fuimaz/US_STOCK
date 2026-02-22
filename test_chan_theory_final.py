"""
最终测试缠论指标 - 使用真实数据
"""
import pandas as pd
import numpy as np
from chan_theory import ChanTheory
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# Load AAPL data
data = pd.read_csv('data_cache/AAPL_1y_1d_forward.csv')
data['datetime'] = pd.to_datetime(data['datetime'], utc=True).dt.tz_localize(None)
data = data.set_index('datetime')
data = data[['Open', 'High', 'Low', 'Close', 'Volume']]

print("=" * 80)
print("Chan Theory Final Test")
print("=" * 80)
print(f"\nData: AAPL")
print(f"Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
print(f"Data points: {len(data)}")

# Analyze
chan = ChanTheory(k_type='day')
result = chan.analyze(data)

summary = chan.get_summary()

print("\n" + "=" * 80)
print("Results Summary")
print("=" * 80)
print(f"Fenxing (分型): {summary['fenxing_count']}")
print(f"Bi (笔): {summary['bi_count']}")
print(f"Xianduan (线段): {summary['xianduan_count']}")
print(f"Zhongshu (中枢): {summary['zhongshu_count']}")
print(f"Buy Points (买点): {summary['buy_points']}")
print(f"Sell Points (卖点): {summary['sell_points']}")

# Visualize
print("\nGenerating visualization...")

output_dir = 'results/chan_theory'
os.makedirs(output_dir, exist_ok=True)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

fig, axes = plt.subplots(5, 1, figsize=(16, 24), sharex=True)
fig.suptitle('AAPL - Chan Theory Analysis', fontsize=16, fontweight='bold')

# 1. Price
ax1 = axes[0]
ax1.plot(data.index, data['Close'], label='Close', linewidth=1.5, color='black')
ax1.set_ylabel('Price')
ax1.set_title('Price Chart')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Fenxing
ax2 = axes[1]
ax2.plot(data.index, data['Close'], linewidth=1, color='gray', alpha=0.5)
for fx in chan.fenxing_list:
    color = 'red' if fx['type'] == 1 else 'green'
    marker = 'v' if fx['type'] == 1 else '^'
    price = fx['high'] if fx['type'] == 1 else fx['low']
    ax2.scatter(fx['date'], price, color=color, marker=marker, s=80, zorder=5)
ax2.set_ylabel('Price')
ax2.set_title(f'Fenxing ({len(chan.fenxing_list)} found)')
ax2.grid(True, alpha=0.3)

# 3. Bi
ax3 = axes[2]
ax3.plot(data.index, data['Close'], linewidth=1, color='gray', alpha=0.5)
for bi in chan.bi_list:
    color = 'red' if bi['type'] == 1 else 'green'
    ax3.plot([bi['start'], bi['end']], [bi['start_price'], bi['end_price']], 
            color=color, linewidth=2, alpha=0.7)
ax3.set_ylabel('Price')
ax3.set_title(f'Bi ({len(chan.bi_list)} found)')
ax3.grid(True, alpha=0.3)

# 4. Xianduan
ax4 = axes[3]
ax4.plot(data.index, data['Close'], linewidth=1, color='gray', alpha=0.5)
for xd in chan.xianduan_list:
    color = 'red' if xd['type'] == 1 else 'green'
    ax4.plot([xd['start'], xd['end']], [xd['low'], xd['high']], 
            color=color, linewidth=3, alpha=0.7)
ax4.set_ylabel('Price')
ax4.set_title(f'Xianduan ({len(chan.xianduan_list)} found)')
ax4.grid(True, alpha=0.3)

# 5. Zhongshu and Buy/Sell Points
ax5 = axes[4]
ax5.plot(data.index, data['Close'], linewidth=1.5, color='black', alpha=0.7)

# Zhongshu
for zs in chan.zhongshu_list:
    ax5.fill_between([zs['start'], zs['end']], zs['low'], zs['high'],
                    alpha=0.2, color='blue')

# Buy points
for bp in chan.buy_points:
    colors = {1: 'red', 2: 'orange', 3: 'purple'}
    ax5.scatter(bp['date'], bp['price'], color=colors.get(bp['type'], 'red'), 
               marker='^', s=200, zorder=10, edgecolors='black', linewidths=1.5)

# Sell points
for sp in chan.sell_points:
    colors = {1: 'green', 2: 'cyan', 3: 'blue'}
    ax5.scatter(sp['date'], sp['price'], color=colors.get(sp['type'], 'green'),
               marker='v', s=200, zorder=10, edgecolors='black', linewidths=1.5)

ax5.set_ylabel('Price')
ax5.set_xlabel('Date')
ax5.set_title(f'Zhongshu ({len(chan.zhongshu_list)}) & Buy/Sell Points ({len(chan.buy_points)}/{len(chan.sell_points)})')
ax5.grid(True, alpha=0.3)

# Format x-axis
for ax in axes:
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

plt.xticks(rotation=45)
plt.tight_layout()

chart_file = os.path.join(output_dir, 'AAPL_chan_theory_final.png')
plt.savefig(chart_file, dpi=150, bbox_inches='tight')
plt.close()

print(f"Chart saved to: {chart_file}")

# Save results
data_file = os.path.join(output_dir, 'AAPL_chan_theory_result.csv')
result.to_csv(data_file)
print(f"Data saved to: {data_file}")

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)
