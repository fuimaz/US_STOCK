"""
期货分钟级数据回测
基于 chan_theory_realtime.py 的缠论策略，对国内期货5分钟/15分钟数据进行回测
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import os
import sys

# 导入绘图模块
try:
    from kline_plotter import KLinePlotter
except ImportError:
    KLinePlotter = None

import warnings
warnings.filterwarnings('ignore')

# 导入缠论分析模块
from chan_theory_realtime import ChanTheoryRealtime


# ==================== 配置参数 ====================

# 期货合约配置（合约乘数、保证金比例）
CONTRACT_SPECS = {
    # 黑色系
    'I0': {'name': '铁矿石', 'multiplier': 100, 'margin_rate': 0.12},  # 100吨/手
    'RB0': {'name': '螺纹钢', 'multiplier': 10, 'margin_rate': 0.10},   # 10吨/手
    'JM0': {'name': '焦煤', 'multiplier': 60, 'margin_rate': 0.12},     # 60吨/手
    'J0': {'name': '焦炭', 'multiplier': 100, 'margin_rate': 0.12},     # 100吨/手
    'HC0': {'name': '热卷', 'multiplier': 10, 'margin_rate': 0.10},     # 10吨/手
    # 能源化工
    'SC0': {'name': '原油', 'multiplier': 1000, 'margin_rate': 0.10},   # 1000桶/手
    'RU0': {'name': '橡胶', 'multiplier': 10, 'margin_rate': 0.10},     # 10吨/手
    'TA0': {'name': 'PTA', 'multiplier': 5, 'margin_rate': 0.08},       # 5吨/手
    'MA0': {'name': '甲醇', 'multiplier': 10, 'margin_rate': 0.08},      # 10吨/手
    'FG0': {'name': '玻璃', 'multiplier': 50, 'margin_rate': 0.08},      # 50吨/手
    # 有色金属
    'CU0': {'name': '沪铜', 'multiplier': 5, 'margin_rate': 0.10},       # 5吨/手
    'AL0': {'name': '沪铝', 'multiplier': 5, 'margin_rate': 0.10},       # 5吨/手
    'ZN0': {'name': '沪锌', 'multiplier': 5, 'margin_rate': 0.10},      # 5吨/手
    'PB0': {'name': '沪铅', 'multiplier': 5, 'margin_rate': 0.10},      # 5吨/手
    'NI0': {'name': '沪镍', 'multiplier': 1, 'margin_rate': 0.10},       # 1吨/手
    # 农产品
    'M0': {'name': '豆粕', 'multiplier': 10, 'margin_rate': 0.10},       # 10吨/手
    'Y0': {'name': '豆油', 'multiplier': 10, 'margin_rate': 0.10},      # 10吨/手
    'C0': {'name': '玉米', 'multiplier': 100, 'margin_rate': 0.10},      # 100吨/手
    'CS0': {'name': '玉米淀粉', 'multiplier': 10, 'margin_rate': 0.10}, # 10吨/手
    'SR0': {'name': '白糖', 'multiplier': 10, 'margin_rate': 0.10},       # 10吨/手
    'CF0': {'name': '棉花', 'multiplier': 5, 'margin_rate': 0.10},        # 5吨/手
    # 贵金属
    'AU0': {'name': '黄金', 'multiplier': 1000, 'margin_rate': 0.12},     # 1000克/手
    'AG0': {'name': '白银', 'multiplier': 15, 'margin_rate': 0.12},       # 15千克/手
}

# 回测参数
BACKTEST_CONFIG = {
    'initial_capital': 1_000_000,    # 初始资金 100万
    'commission_rate': 0.0001,       # 手续费万分之1
    'slippage': 0.0001,             # 滑点万分之1 (0.01%)，适合限价单
    'stop_loss_pct': 0.02,           # 止损2%
    'stop_profit_pct': 0.04,         # 止盈4%
    'max_position_pct': 0.8,         # 最大仓位80%
    'margin_rate': 0.10,             # 默认保证金比例10%
}


# ==================== 数据处理 ====================

def load_futures_data(symbol: str, data_dir: str = 'data_cache/china_futures') -> pd.DataFrame:
    """加载期货分钟数据"""
    file_path_5m = os.path.join(data_dir, f'{symbol}_5min.csv')
    
    if os.path.exists(file_path_5m):
        df = pd.read_csv(file_path_5m)
    else:
        raise FileNotFoundError(f"数据文件不存在: {file_path_5m}")
    
    if 'datetime' in df.columns:
        df['DateTime'] = pd.to_datetime(df['datetime'])
    elif 'DateTime' not in df.columns:
        df['DateTime'] = df.index
    
    column_mapping = {
        'open': 'Open', 'high': 'High', 'low': 'Low', 
        'close': 'Close', 'volume': 'Volume'
    }
    df = df.rename(columns=column_mapping)
    
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"缺少必要列: {col}")
    
    df.set_index('DateTime', inplace=True)
    df.sort_index(inplace=True)
    
    return df


def resample_to_15min(df: pd.DataFrame) -> pd.DataFrame:
    """将5分钟数据重采样为15分钟数据"""
    resampled = df.resample('15min').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    resampled = resampled.dropna()
    resampled.index.name = 'DateTime'
    return resampled


# ==================== 账户与持仓管理 ====================

class Position:
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
        self.open_commission = open_commission  # 开仓手续费
    
    @property
    def market_value(self) -> float:
        return self.entry_price * self.quantity * self.multiplier
    
    @property
    def margin(self) -> float:
        return self.market_value * self.margin_rate
    
    def get_pnl(self, current_price: float) -> float:
        price_diff = (current_price - self.entry_price) * self.direction
        return price_diff * self.quantity * self.multiplier


class FuturesAccount:
    """期货账户"""
    def __init__(self, initial_capital: float, commission_rate: float, slippage: float, default_margin_rate: float = 0.10):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.default_margin_rate = default_margin_rate
        
        self.available_cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[dict] = []
        self.equity_curve: List[dict] = []
    
    @property
    def total_equity(self) -> float:
        total_pnl = sum(pos.get_pnl(self._get_current_price(pos.symbol)) 
                       for pos in self.positions.values())
        return self.available_cash + self.total_margin + total_pnl
    
    @property
    def total_margin(self) -> float:
        return sum(pos.margin for pos in self.positions.values())
    
    def _get_current_price(self, symbol: str) -> float:
        return getattr(self, '_current_prices', {}).get(symbol, 0)
    
    def set_current_prices(self, prices: Dict[str, float]):
        self._current_prices = prices
    
    def open_position(self, symbol: str, direction: int, quantity: int, 
                     price: float, time, multiplier: int, margin_rate: float = None) -> bool:
        """开仓 - 滑点按价格百分比计算"""
        if margin_rate is None:
            margin_rate = self.default_margin_rate
        
        # 滑点计算：避免价格*百分比导致的精度问题
        # 滑点用价格的小数部分表示（如滑点1元）
        slippage = 1.0  # 固定滑点1元
        if direction == 1:
            fill_price = price + slippage
        else:
            fill_price = price - slippage
        
        commission = fill_price * quantity * multiplier * self.commission_rate
        required_margin = fill_price * quantity * multiplier * margin_rate
        
        if self.available_cash < (commission + required_margin):
            return False
        
        self.available_cash -= commission
        
        if symbol in self.positions:
            existing = self.positions[symbol]
            if existing.direction == -direction:
                self.close_position(symbol, fill_price, time)
        
        pos = Position(symbol, direction, quantity, fill_price, time, multiplier, margin_rate, commission)
        margin = fill_price * quantity * multiplier * margin_rate
        self.available_cash -= margin
        
        self.positions[symbol] = pos
        
        self.trades.append({
            'time': time,
            'symbol': symbol,
            'direction': 'OPEN_LONG' if direction == 1 else 'OPEN_SHORT',
            'price': fill_price,
            'quantity': quantity,
            'commission': commission
        })
        
        return True
    
    def close_position(self, symbol: str, price: float, time) -> bool:
        """平仓 - 滑点按价格百分比计算"""
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        
        # 滑点计算：避免价格*百分比导致的精度问题
        # 滑点用价格的小数部分表示（如滑点1元）
        slippage = 1.0  # 固定滑点1元
        if pos.direction == 1:
            fill_price = price - slippage
        else:
            fill_price = price + slippage
        
        commission = fill_price * pos.quantity * pos.multiplier * self.commission_rate
        pnl = pos.get_pnl(fill_price)
        
        self.available_cash += pos.margin
        self.available_cash += pnl - commission
        
        # 获取开仓时的手续费
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
        })
        
        del self.positions[symbol]
        return True
    
    def record_equity(self, time, prices: Dict[str, float]):
        self.set_current_prices(prices)
        self.equity_curve.append({
            'time': time,
            'equity': self.total_equity,
            'available_cash': self.available_cash,
            'margin': self.total_margin,
            'positions': len(self.positions)
        })


# ==================== 缠论期货策略 ====================

class ChanFuturesStrategy:
    def __init__(self, k_type: str = 'minute'):
        self.chan = ChanTheoryRealtime(k_type=k_type)
        self.last_signal = None
    
    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        return self.chan.analyze(data)
    
    def get_signal(self, result_df: pd.DataFrame) -> dict:
        if len(result_df) < 2:
            return {'signal': 0, 'type': 0, 'desc': ''}
        
        current = result_df.iloc[-1]
        previous = result_df.iloc[-2]
        
        if current['sell_point'] > 0 and previous['sell_point'] == 0:
            return {
                'signal': -1,
                'type': int(current['sell_point']),
                'desc': '卖点'
            }
        
        if current['buy_point'] > 0 and previous['buy_point'] == 0:
            return {
                'signal': 1,
                'type': int(current['buy_point']),
                'desc': '买点'
            }
        
        return {'signal': 0, 'type': 0, 'desc': ''}


def precompute_signals(data: pd.DataFrame, window_size: int = 500) -> pd.DataFrame:
    """预计算所有信号 - 交易第一类和第二类买卖点"""
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
            result.iloc[i, result.columns.get_loc('sell_signal')] = 1
    
    print(f"  预计算完成: 买入信号 {result['buy_signal'].sum()} 个, 卖出信号 {result['sell_signal'].sum()} 个")
    
    return result


# ==================== 回测引擎 ====================

class FuturesBacktestEngine:
    def __init__(
        self,
        strategy: ChanFuturesStrategy,
        initial_capital: float = 1_000_000,
        commission_rate: float = 0.0001,
        slippage: float = 0.0001,
        window_size: int = 100,
    ):
        self.strategy = strategy
        self.account = FuturesAccount(initial_capital, commission_rate, slippage, BACKTEST_CONFIG['margin_rate'])
        self.window_size = window_size
        
        self.trades = []
        self.equity_curve = []
        self.signals = []
    
    def run(self, data: pd.DataFrame, symbol: str) -> dict:
        print(f"\n开始回测 {symbol}...")
        print(f"数据范围: {data.index[0]} ~ {data.index[-1]}")
        print(f"数据条数: {len(data)}")
        
        contract_info = CONTRACT_SPECS.get(symbol, {'multiplier': 10, 'margin_rate': 0.10})
        multiplier = contract_info['multiplier']
        margin_rate = contract_info['margin_rate']
        
        result_df = precompute_signals(data, self.window_size)
        
        buy_signal_indices = []
        sell_signal_indices = []
        
        for i in range(self.window_size, len(data)):
            current_bar = data.iloc[i]
            current_time = data.index[i]
            current_price = current_bar['Close']
            
            self.account.set_current_prices({symbol: current_price})
            
            signal_row = result_df.iloc[i]
            buy_signal = signal_row['buy_signal']
            sell_signal = signal_row['sell_signal']
            
            if sell_signal == 1:
                signal = {'signal': -1, 'type': int(signal_row['sell_point']), 'desc': '二卖'}
            elif buy_signal == 1:
                signal = {'signal': 1, 'type': int(signal_row['buy_point']), 'desc': '二买'}
            else:
                signal = {'signal': 0, 'type': 0, 'desc': ''}
            
            self.signals.append({
                'time': current_time,
                'price': current_price,
                'signal': signal['signal'],
                'type': signal['type'],
                'desc': signal['desc']
            })
            
            if signal['signal'] == 1:
                buy_signal_indices.append(i)
            elif signal['signal'] == -1:
                sell_signal_indices.append(i)
            
            if symbol in self.account.positions:
                pos = self.account.positions[symbol]
                
                if pos.direction == 1:
                    pnl_pct = (current_price - pos.entry_price) / pos.entry_price
                else:
                    pnl_pct = (pos.entry_price - current_price) / pos.entry_price
                
                if pnl_pct <= -BACKTEST_CONFIG['stop_loss_pct']:
                    self.account.close_position(symbol, current_price, current_time)
                    print(f"  {current_time} 止损平仓, 价格: {current_price}, 盈亏: {pnl_pct*100:.2f}%")
                    continue
                
                if pnl_pct >= BACKTEST_CONFIG['stop_profit_pct']:
                    self.account.close_position(symbol, current_price, current_time)
                    print(f"  {current_time} 止盈平仓, 价格: {current_price}, 盈亏: {pnl_pct*100:.2f}%")
                    continue
            
            if signal['signal'] == 1 and symbol not in self.account.positions:
                max_quantity = int(self.account.available_cash * BACKTEST_CONFIG['max_position_pct'] 
                                 / (current_price * multiplier * margin_rate))
                quantity = max(1, max_quantity)
                
                if self.account.open_position(symbol, 1, quantity, current_price, current_time, multiplier, margin_rate):
                    print(f"  {current_time} 开多仓, 价格: {current_price}, 手数: {quantity}")
            
            elif signal['signal'] == -1 and symbol in self.account.positions:
                if self.account.close_position(symbol, current_price, current_time):
                    print(f"  {current_time} 平仓, 价格: {current_price}")
            
            self.account.record_equity(current_time, {symbol: current_price})
        
        # 修复：在回测结束后，用最后价格记录最终权益（包含未平仓持仓的盈亏）
        last_time = data.index[-1]
        last_price = data.iloc[-1]['Close']
        self.account.record_equity(last_time, {symbol: last_price})
        
        print(f"\n信号统计: 买入信号 {len(buy_signal_indices)} 个, 卖出信号 {len(sell_signal_indices)} 个")
        
        # 计算未平仓持仓信息
        open_positions_info = []
        if self.account.positions:
            for pos_symbol, pos in self.account.positions.items():
                unrealized_pnl = pos.get_pnl(last_price)
                open_positions_info.append({
                    'symbol': pos_symbol,
                    'direction': 'LONG',
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'current_price': last_price,
                    'unrealized_pnl': unrealized_pnl
                })
            print(f"未平仓持仓: {len(self.account.positions)} 个, 未实现盈亏: {sum(p['unrealized_pnl'] for p in open_positions_info):.2f}")
        else:
            print(f"未平仓持仓: 0 个")
        
        self.trades = self.account.trades
        self.equity_curve = self.account.equity_curve
        
        # 绘制K线图
        try:
            self.plot_kline(data, symbol, result_df)
        except Exception as e:
            print(f"  绘制K线图失败: {e}")
        
        return self.generate_report(symbol, open_positions_info)
    
    def plot_kline(self, data: pd.DataFrame, symbol: str, result_df: pd.DataFrame):
        """绘制带BOLL指标的K线图"""
        if KLinePlotter is None:
            print("  KLinePlotter未安装，跳过绘图")
            return
        
        # 生成买卖信号
        buy_signals = pd.Series(0.0, index=data.index, dtype=float)
        sell_signals = pd.Series(0.0, index=data.index, dtype=float)
        
        for i in range(1, len(result_df)):
            current = result_df.iloc[i]
            previous = result_df.iloc[i-1]
            
            if i < len(data):
                idx = data.index[i]
                
                # 交易第一类和第二类买卖点
                if current['buy_point'] in [1, 2] and previous['buy_point'] == 0:
                    buy_signals.loc[idx] = float(data.loc[idx, 'Close'])
                
                if current['sell_point'] in [1, 2] and previous['sell_point'] == 0:
                    sell_signals.loc[idx] = float(data.loc[idx, 'Close'])
        
        # 绘制K线图
        plotter = KLinePlotter(style='charles')
        
        output_dir = 'results/futures_signals'
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, f'{symbol}_kline.png')
        
        print(f"  正在绘制K线图...")
        
        contract_info = CONTRACT_SPECS.get(symbol, {'name': symbol})
        contract_name = contract_info.get('name', symbol)
        
        plotter.plot_with_signals_and_indicators(
            data=data,
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            title=f"{contract_name}({symbol}) 5分钟K线 - 缠论买卖点+布林带",
            show_boll=True,
            show_rsi=False,
            show_volume=True,
            boll_period=20,
            boll_std=2,
            save_path=save_path
        )
        
        print(f"  K线图已保存: {save_path}")
    
    def generate_report(self, symbol: str, open_positions_info: List[dict] = None) -> dict:
        # 保存交易记录到CSV
        self.save_trades_csv(symbol)
        
        if not self.trades:
            return {'symbol': symbol, 'total_trades': 0, 'message': '无交易'}
        
        closed_trades = [t for t in self.trades if 'pnl' in t]
        if closed_trades:
            total_pnl = sum(t['pnl'] for t in closed_trades)  # 净PnL（已扣除所有手续费）
            total_commission = sum(t.get('total_commission', 0) for t in closed_trades)  # 总手续费
            gross_pnl = total_pnl + total_commission  # 毛PnL（未扣除手续费）
            
            winning_trades = [t for t in closed_trades if t['pnl'] > 0]
            losing_trades = [t for t in closed_trades if t['pnl'] <= 0]
            
            win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        else:
            total_pnl = 0
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        if self.equity_curve:
            equity_values = [e['equity'] for e in self.equity_curve]
            initial_equity = equity_values[0]
            final_equity = equity_values[-1]
            total_return = (final_equity - initial_equity) / initial_equity
            
            peak = equity_values[0]
            max_drawdown = 0
            for eq in equity_values:
                if eq > peak:
                    peak = eq
                drawdown = (peak - eq) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        else:
            total_return = 0
            max_drawdown = 0
        
        # 未平仓持仓的未实现盈亏
        unrealized_pnl = 0
        if open_positions_info:
            unrealized_pnl = sum(p['unrealized_pnl'] for p in open_positions_info)
        
        return {
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
        }

    def save_trades_csv(self, symbol: str):
        """保存交易记录到CSV文件"""
        if not self.trades:
            return
        
        # 保存成交记录
        output_dir = 'results/futures_trades'
        os.makedirs(output_dir, exist_ok=True)
        
        trades_df = pd.DataFrame(self.trades)
        if not trades_df.empty:
            trades_path = os.path.join(output_dir, f'{symbol}_trades.csv')
            trades_df.to_csv(trades_path, index=False, encoding='utf-8-sig')
            print(f"  交易记录已保存: {trades_path}")
        
        # 保存权益曲线
        if self.equity_curve:
            equity_df = pd.DataFrame(self.equity_curve)
            equity_path = os.path.join(output_dir, f'{symbol}_equity.csv')
            equity_df.to_csv(equity_path, index=False, encoding='utf-8-sig')
            print(f"  权益曲线已保存: {equity_path}")


# ==================== 主函数 ====================

def run_backtest(symbols: List[str] = None, timeframe: str = '5min'):
    print("=" * 60)
    print("期货缠论分钟级回测 - 交易第一类和第二类买卖点")
    print("=" * 60)
    
    if symbols is None:
        symbols = list(CONTRACT_SPECS.keys())
    
    results = []
    
    for symbol in symbols:
        try:
            df = load_futures_data(symbol)
            print(f"\n{'='*50}")
            print(f"合约: {symbol} ({CONTRACT_SPECS.get(symbol, {}).get('name', symbol)})")
            print(f"时间周期: {timeframe}")
            
            if timeframe == '15min':
                df = resample_to_15min(df)
            
            strategy = ChanFuturesStrategy(k_type='minute')
            engine = FuturesBacktestEngine(
                strategy=strategy,
                initial_capital=BACKTEST_CONFIG['initial_capital'],
                commission_rate=BACKTEST_CONFIG['commission_rate'],
                slippage=BACKTEST_CONFIG['slippage'],
                window_size=100 if timeframe == '5min' else 50
            )
            
            result = engine.run(df, symbol)
            results.append(result)
            
            print(f"\n--- {symbol} 回测结果 ---")
            print(f"交易次数: {result.get('total_trades', 0)}")
            print(f"胜率: {result.get('win_rate', 0)*100:.2f}%")
            print(f"总盈亏: {result.get('total_pnl', 0):.2f}")
            print(f"收益率: {result.get('total_return', 0)*100:.2f}%")
            print(f"最大回撤: {result.get('max_drawdown', 0)*100:.2f}%")
            print(f"未平仓持仓: {result.get('open_positions', 0)} 个")
            print(f"未实现盈亏: {result.get('unrealized_pnl', 0):.2f}")
            
        except Exception as e:
            print(f"  回测失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("回测汇总")
    print("=" * 60)
    
    total_pnl = sum(r.get('total_pnl', 0) for r in results)
    total_trades = sum(r.get('total_trades', 0) for r in results)
    avg_return = np.mean([r.get('total_return', 0) for r in results if r.get('total_trades', 0) > 0])
    
    print(f"测试合约数: {len(results)}")
    print(f"总交易次数: {total_trades}")
    print(f"总盈亏: {total_pnl:.2f}")
    print(f"平均收益率: {avg_return*100:.2f}%")
    
    return results


def analyze_single_contract(symbol: str, timeframe: str = '5min'):
    print("=" * 60)
    print(f"合约分析: {symbol}")
    print("=" * 60)
    
    df = load_futures_data(symbol)
    
    if timeframe == '15min':
        df = resample_to_15min(df)
    
    print(f"\n数据信息:")
    print(f"  时间范围: {df.index[0]} ~ {df.index[-1]}")
    print(f"  数据条数: {len(df)}")
    
    strategy = ChanFuturesStrategy(k_type='minute')
    result = strategy.analyze(df)
    
    summary = strategy.chan.get_summary()
    
    print(f"\n缠论分析结果:")
    print(f"  分型数量: {summary['fenxing_count']}")
    print(f"  笔数量: {summary['bi_count']}")
    print(f"  线段数量: {summary['xianduan_count']}")
    print(f"  中枢数量: {summary['zhongshu_count']}")
    print(f"  买点数量: {summary['buy_points']}")
    print(f"  卖点数量: {summary['sell_points']}")
    
    buy_points = summary.get('buy_point_details', [])
    if buy_points and isinstance(buy_points, list):
        print(f"\n买点信号:")
        for bp in buy_points[:5]:
            print(f"  {bp.get('date', '')}: {bp.get('desc', '')}, 价格: {bp.get('price', 0):.2f}")
    
    sell_points = summary.get('sell_point_details', [])
    if sell_points and isinstance(sell_points, list):
        print(f"\n卖点信号:")
        for sp in sell_points[:5]:
            print(f"  {sp.get('date', '')}: {sp.get('desc', '')}, 价格: {sp.get('price', 0):.2f}")
    
    print(f"\n运行回测...")
    engine = FuturesBacktestEngine(
        strategy=strategy,
        initial_capital=BACKTEST_CONFIG['initial_capital'],
        commission_rate=BACKTEST_CONFIG['commission_rate'],
        slippage=BACKTEST_CONFIG['slippage'],
        window_size=100 if timeframe == '5min' else 50
    )
    
    result = engine.run(df, symbol)
    
    print(f"\n回测结果:")
    print(f"  交易次数: {result.get('total_trades', 0)}")
    print(f"  胜率: {result.get('win_rate', 0)*100:.2f}%")
    print(f"  毛盈亏: {result.get('gross_pnl', 0):.2f}")
    print(f"  总手续费: {result.get('total_commission', 0):.2f}")
    print(f"  净盈亏: {result.get('total_pnl', 0):.2f}")
    print(f"  收益率: {result.get('total_return', 0)*100:.2f}%")
    print(f"  最大回撤: {result.get('max_drawdown', 0)*100:.2f}%")
    print(f"  最终权益: {result.get('final_equity', 0):.2f}")
    print(f"  未平仓持仓: {result.get('open_positions', 0)} 个")
    print(f"  未实现盈亏: {result.get('unrealized_pnl', 0):.2f}")
    
    return result


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    else:
        symbol = 'I0'
    
    timeframe = '5min'
    if len(sys.argv) > 2:
        timeframe = sys.argv[2]
    
    result = analyze_single_contract(symbol, timeframe)
