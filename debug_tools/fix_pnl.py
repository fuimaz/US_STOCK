"""
修复PnL计算口径问题 - 开仓手续费也计入每笔交易的pnl
"""

with open('backtest_futures_minute.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改开仓记录，添加开仓手续费到交易记录
old_open_record = '''        self.trades.append({
            'time': time,
            'symbol': symbol,
            'direction': 'OPEN_LONG' if direction == 1 else 'OPEN_SHORT',
            'price': fill_price,
            'quantity': quantity,
            'commission': commission
        })'''

new_open_record = '''        self.trades.append({
            'time': time,
            'symbol': symbol,
            'direction': 'OPEN_LONG' if direction == 1 else 'OPEN_SHORT',
            'price': fill_price,
            'quantity': quantity,
            'commission': commission,
            'open_commission': commission  # 开仓手续费
        })'''

content = content.replace(old_open_record, new_open_record)

# 2. 修改平仓记录，将开仓手续费也计入pnl
old_close_record = '''        self.trades.append({
            'time': time,
            'symbol': symbol,
            'direction': 'CLOSE_LONG' if pos.direction == 1 else 'CLOSE_SHORT',
            'price': fill_price,
            'quantity': pos.quantity,
            'commission': commission,
            'pnl': pnl - commission
        })'''

new_close_record = '''        # 获取开仓时的手续费
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

content = content.replace(old_close_record, new_close_record)

# 3. 修改generate_report，添加gross_pnl和net_pnl的区分
old_report = '''        closed_trades = [t for t in self.trades if 'pnl' in t]
        if closed_trades:
            total_pnl = sum(t['pnl'] for t in closed_trades)
            winning_trades = [t for t in closed_trades if t['pnl'] > 0]
            losing_trades = [t for t in closed_trades if t['pnl'] <= 0]
            
            win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0'''

new_report = '''        closed_trades = [t for t in self.trades if 'pnl' in t]
        if closed_trades:
            total_pnl = sum(t['pnl'] for t in closed_trades)  # 净PnL（已扣除所有手续费）
            total_commission = sum(t.get('total_commission', 0) for t in closed_trades)  # 总手续费
            gross_pnl = total_pnl + total_commission  # 毛PnL（未扣除手续费）
            
            winning_trades = [t for t in closed_trades if t['pnl'] > 0]
            losing_trades = [t for t in closed_trades if t['pnl'] <= 0]
            
            win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0'''

content = content.replace(old_report, new_report)

# 4. 修改返回值，添加更多统计信息
old_return = '''        return {
            'symbol': symbol,
            'name': CONTRACT_SPECS.get(symbol, {}).get('name', symbol),
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades) if closed_trades else 0,
            'losing_trades': len(losing_trades) if closed_trades else 0,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'final_equity': self.account.total_equity,
            'open_positions': len(open_positions_info) if open_positions_info else 0,
            'unrealized_pnl': unrealized_pnl,
            'trades': closed_trades,
            'equity_curve': self.equity_curve,
            'signals': self.signals
        }'''

new_return = '''        return {
            'symbol': symbol,
            'name': CONTRACT_SPECS.get(symbol, {}).get('name', symbol),
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades) if closed_trades else 0,
            'losing_trades': len(losing_trades) if closed_trades else 0,
            'win_rate': win_rate,
            'total_pnl': total_pnl,  # 净PnL（扣除所有手续费）
            'gross_pnl': gross_pnl if closed_trades else 0,  # 毛PnL（未扣除手续费）
            'total_commission': total_commission if closed_trades else 0,  # 总手续费
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'final_equity': self.account.total_equity,
            'open_positions': len(open_positions_info) if open_positions_info else 0,
            'unrealized_pnl': unrealized_pnl,
            'trades': closed_trades,
            'equity_curve': self.equity_curve,
            'signals': self.signals
        }'''

content = content.replace(old_return, new_return)

# 5. 修改主函数输出，显示更多信息
old_print = '''            print(f"--- {symbol} 回测结果 ---")
            print(f"交易次数: {result.get('total_trades', 0)}")
            print(f"胜率: {result.get('win_rate', 0)*100:.2f}%")
            print(f"总盈亏: {result.get('total_pnl', 0):.2f}")
            print(f"收益率: {result.get('total_return', 0)*100:.2f}%")
            print(f"最大回撤: {result.get('max_drawdown', 0)*100:.2f}%")
            print(f"未平仓持仓: {result.get('open_positions', 0)} 个")
            print(f"未实现盈亏: {result.get('unrealized_pnl', 0):.2f}")'''

new_print = '''            print(f"--- {symbol} 回测结果 ---")
            print(f"交易次数: {result.get('total_trades', 0)}")
            print(f"胜率: {result.get('win_rate', 0)*100:.2f}%")
            print(f"毛盈亏: {result.get('gross_pnl', 0):.2f}")
            print(f"总手续费: {result.get('total_commission', 0):.2f}")
            print(f"净盈亏: {result.get('total_pnl', 0):.2f}")
            print(f"收益率: {result.get('total_return', 0)*100:.2f}%")
            print(f"最大回撤: {result.get('max_drawdown', 0)*100:.2f}%")
            print(f"未平仓持仓: {result.get('open_positions', 0)} 个")
            print(f"未实现盈亏: {result.get('unrealized_pnl', 0):.2f}")'''

content = content.replace(old_print, new_print)

# 6. 修改analyze_single_contract的输出
old_analyze_print = '''    print(f"\\n回测结果:")
    print(f"  交易次数: {result.get('total_trades', 0)}")
    print(f"  胜率: {result.get('win_rate', 0)*100:.2f}%")
    print(f"  总盈亏: {result.get('total_pnl', 0):.2f}")
    print(f"  收益率: {result.get('total_return', 0)*100:.2f}%")
    print(f"  最大回撤: {result.get('max_drawdown', 0)*100:.2f}%")
    print(f"  最终权益: {result.get('final_equity', 0):.2f}")
    print(f"  未平仓持仓: {result.get('open_positions', 0)} 个")
    print(f"  未实现盈亏: {result.get('unrealized_pnl', 0):.2f}")'''

new_analyze_print = '''    print(f"\\n回测结果:")
    print(f"  交易次数: {result.get('total_trades', 0)}")
    print(f"  胜率: {result.get('win_rate', 0)*100:.2f}%")
    print(f"  毛盈亏: {result.get('gross_pnl', 0):.2f}")
    print(f"  总手续费: {result.get('total_commission', 0):.2f}")
    print(f"  净盈亏: {result.get('total_pnl', 0):.2f}")
    print(f"  收益率: {result.get('total_return', 0)*100:.2f}%")
    print(f"  最大回撤: {result.get('max_drawdown', 0)*100:.2f}%")
    print(f"  最终权益: {result.get('final_equity', 0):.2f}")
    print(f"  未平仓持仓: {result.get('open_positions', 0)} 个")
    print(f"  未实现盈亏: {result.get('unrealized_pnl', 0):.2f}")'''

content = content.replace(old_analyze_print, new_analyze_print)

with open('backtest_futures_minute.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - 已修复PnL计算口径问题')
