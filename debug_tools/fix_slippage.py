"""
修复滑点计算问题 - 使用加减而非乘除
"""

with open('backtest_futures_minute.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修改滑点计算方式：使用绝对值而非比例乘法
# 开仓滑点
old_open = '''        # 滑点按价格百分比计算
        slippage_price = price * self.slippage
        if direction == 1:
            fill_price = price + slippage_price
        else:
            fill_price = price - slippage_price'''

new_open = '''        # 滑点计算：避免价格*百分比导致的精度问题
        # 滑点用价格的小数部分表示（如滑点1元）
        slippage = 1.0  # 固定滑点1元
        if direction == 1:
            fill_price = price + slippage
        else:
            fill_price = price - slippage'''

content = content.replace(old_open, new_open)

# 平仓滑点
old_close = '''        # 滑点按价格百分比计算
        slippage_price = price * self.slippage
        if pos.direction == 1:
            fill_price = price - slippage_price
        else:
            fill_price = price + slippage_price'''

new_close = '''        # 滑点计算：避免价格*百分比导致的精度问题
        # 滑点用价格的小数部分表示（如滑点1元）
        slippage = 1.0  # 固定滑点1元
        if pos.direction == 1:
            fill_price = price - slippage
        else:
            fill_price = price + slippage'''

content = content.replace(old_close, new_close)

with open('backtest_futures_minute.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - 已修复滑点计算问题')
