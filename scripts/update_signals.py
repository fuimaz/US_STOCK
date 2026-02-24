with open('backtest_futures_minute.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修改信号检测逻辑，交易所有买卖点（第一类和第二类）
old = '''    """预计算所有信号 - 只交易第二类买卖点"""
    print("  预计算信号...")
    
    strategy = ChanFuturesStrategy(k_type='minute')
    result = strategy.analyze(data)
    
    result['buy_signal'] = 0
    result['sell_signal'] = 0
    
    for i in range(1, len(result)):
        current = result.iloc[i]
        previous = result.iloc[i-1]
        
        # 只交易第二类买卖点 (buy_point == 2)
        if current['buy_point'] == 2 and previous['buy_point'] == 0:
            result.iloc[i, result.columns.get_loc('buy_signal')] = 1
        
        # 只交易第二类买卖点 (sell_point == 2)
        if current['sell_point'] == 2 and previous['sell_point'] == 0:
            result.iloc[i, result.columns.get_loc('sell_signal')] = 1'''

new = '''    """预计算所有信号 - 交易第一类和第二类买卖点"""
    print("  预计算信号...")
    
    strategy = ChanFuturesStrategy(k_type='minute')
    result = strategy.analyze(data)
    
    result['buy_signal'] = 0
    result['sell_signal'] = 0
    
    for i in range(1, len(result)):
        current = result.iloc[i]
        previous = result.iloc[i-1]
        
        # 交易第一类和第二类买卖点 (buy_point == 1 或 2)
        if current['buy_point'] in [1, 2] and previous['buy_point'] == 0:
            result.iloc[i, result.columns.get_loc('buy_signal')] = 1
        
        # 交易第一类和第二类卖点 (sell_point == 1 或 2)
        if current['sell_point'] in [1, 2] and previous['sell_point'] == 0:
            result.iloc[i, result.columns.get_loc('sell_signal')] = 1'''

content = content.replace(old, new)

# 修改打印信息
content = content.replace('期货缠论分钟级回测 - 只交易第二类买卖点', '期货缠论分钟级回测 - 交易第一类和第二类买卖点')

with open('backtest_futures_minute.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
