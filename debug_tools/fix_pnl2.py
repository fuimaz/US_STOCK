"""
修复PnL计算问题 - 简化方案：在开仓时将手续费存储在Position对象中
"""

with open('backtest_futures_minute.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改Position类，添加open_commission属性
old_position = '''class Position:
    """持仓"""
    def __init__(self, symbol: str, direction: int, quantity: int, 
                 entry_price: float, entry_time, multiplier: int, margin_rate: float = 0.10):
        self.symbol = symbol
        self.direction = direction
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.multiplier = multiplier
        self.margin_rate = margin_rate'''

new_position = '''class Position:
    """持仓"""
    def __init__(self, symbol: str, direction: int, quantity: int, 
                 entry_price: float, entry_time, multiplier: int, margin_rate: float = 0.10,
                 open_commission: float = 0.0):
        self.symbol = symbol
        self.direction = direction
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.multiplier = multiplier
        self.margin_rate = margin_rate
        self.open_commission = open_commission  # 开仓手续费'''

content = content.replace(old_position, new_position)

# 2. 修改开仓方法，传递open_commission到Position
old_create_position = '''        pos = Position(symbol, direction, quantity, fill_price, time, multiplier, margin_rate)'''

new_create_position = '''        pos = Position(symbol, direction, quantity, fill_price, time, multiplier, margin_rate, commission)'''

content = content.replace(old_create_position, new_create_position)

# 3. 修改平仓方法，使用Position中的open_commission
old_close = '''        # 获取开仓时的手续费
        open_commission = 0
        for t in self.trades:
            if t.get('symbol') == symbol and t.get('direction', '').startswith('OPEN'):
                if 'open_commission' in t:
                    open_commission = t.get('open_commission', 0)
                    break
        
        # 总手续费 = 开仓手续费 + 平仓手续费
        total_commission = open_commission + commission
        # PnL = 收益 - 总手续费
        net_pnl = pnl - total_commission
        
        self.trades.append({
            'time': time,
            'symbol': symbol,
            'direction': 'CLOSE_LONG' if pos.direction == 1 else 'CLOSE_SHORT',
            'price': fill_price,
            'quantity': pos.quantity,
            'commission': commission,
            'open_commission': open_commission,
            'total_commission': total_commission,
            'pnl': net_pnl  # 净PnL（扣除所有手续费）
        })'''

new_close = '''        # 获取开仓时的手续费
        open_commission = pos.open_commission
        
        # 总手续费 = 开仓手续费 + 平仓手续费
        total_commission = open_commission + commission
        # PnL = 收益 - 总手续费
        net_pnl = pnl - total_commission
        
        self.trades.append({
            'time': time,
            'symbol': symbol,
            'direction': 'CLOSE_LONG' if pos.direction == 1 else 'CLOSE_SHORT',
            'price': fill_price,
            'quantity': pos.quantity,
            'commission': commission,
            'open_commission': open_commission,
            'total_commission': total_commission,
            'pnl': net_pnl  # 净PnL（扣除所有手续费）
        })'''

content = content.replace(old_close, new_close)

# 4. 修改开仓记录，移除不需要的open_commission字段
old_open_record = '''        self.trades.append({
            'time': time,
            'symbol': symbol,
            'direction': 'OPEN_LONG' if direction == 1 else 'OPEN_SHORT',
            'price': fill_price,
            'quantity': quantity,
            'commission': commission,
            'open_commission': commission  # 开仓手续费
        })'''

new_open_record = '''        self.trades.append({
            'time': time,
            'symbol': symbol,
            'direction': 'OPEN_LONG' if direction == 1 else 'OPEN_SHORT',
            'price': fill_price,
            'quantity': quantity,
            'commission': commission
        })'''

content = content.replace(old_open_record, new_open_record)

with open('backtest_futures_minute.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - 已修复PnL计算问题（简化方案）')
