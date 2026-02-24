with open('backtest_futures_minute.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复语法错误
old = '''        print(f"\\n信号统计: 买入信号 {len(buy_signal_indices)} 个, 卖出信号 {len(sell_signal_indices)} 个")
        
平仓持仓信息
        open_positions_info = []
               # 计算未 if self.account.positions:
            for pos_symbol, pos in self.account.positions.items():'''

new = '''        print(f"\\n信号统计: 买入信号 {len(buy_signal_indices)} 个, 卖出信号 {len(sell_signal_indices)} 个")
        
        # 计算未平仓持仓信息
        open_positions_info = []
        if self.account.positions:
            for pos_symbol, pos in self.account.positions.items():'''

content = content.replace(old, new)

with open('backtest_futures_minute.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
