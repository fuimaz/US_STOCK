import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str = "Strategy"):
        self.name = name
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 包含OHLCV数据的DataFrame
        
        Returns:
            添加了信号列的DataFrame
        """
        pass


class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.0001
    ):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
            commission: 手续费率（默认0.1%）
            slippage: 滑点率（默认0.01%）
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy: BaseStrategy
    ) -> Dict:
        """
        运行回测
        
        Args:
            data: 历史数据
            strategy: 交易策略
        
        Returns:
            回测结果字典
        """
        df = strategy.generate_signals(data.copy())
        
        capital = self.initial_capital
        position = 0
        trades = []
        equity_curve = []
        
        for i in range(len(df)):
            current_price = df['Close'].iloc[i]
            signal = df.get('signal', pd.Series([0] * len(df))).iloc[i]
            
            if signal == 1 and position == 0:
                shares = capital / (current_price * (1 + self.slippage))
                cost = shares * current_price * (1 + self.slippage) * (1 + self.commission)
                capital -= cost
                position = shares
                
                trades.append({
                    'date': df.index[i],
                    'type': 'buy',
                    'price': current_price,
                    'shares': shares,
                    'cost': cost
                })
            
            elif signal == -1 and position > 0:
                proceeds = position * current_price * (1 - self.slippage) * (1 - self.commission)
                capital += proceeds
                
                trades.append({
                    'date': df.index[i],
                    'type': 'sell',
                    'price': current_price,
                    'shares': position,
                    'proceeds': proceeds
                })
                
                position = 0
            
            current_value = capital + position * current_price
            equity_curve.append({
                'date': df.index[i],
                'equity': current_value,
                'price': current_price
            })
        
        if position > 0:
            final_price = df['Close'].iloc[-1]
            proceeds = position * final_price * (1 - self.slippage) * (1 - self.commission)
            capital += proceeds
            position = 0
        
        equity_df = pd.DataFrame(equity_curve).set_index('date')
        
        results = {
            'equity_curve': equity_df,
            'trades': pd.DataFrame(trades),
            'final_capital': capital,
            'total_return': (capital - self.initial_capital) / self.initial_capital,
            'total_trades': len(trades)
        }
        
        results.update(self._calculate_metrics(equity_df, trades))
        
        return results
    
    def _calculate_metrics(
        self,
        equity_df: pd.DataFrame,
        trades: List[Dict]
    ) -> Dict:
        """计算绩效指标"""
        equity = equity_df['equity']
        returns = equity.pct_change().dropna()
        
        total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
        
        annualized_return = (equity.iloc[-1] / equity.iloc[0]) ** (252 / len(equity)) - 1
        
        sharpe_ratio = 0
        if returns.std() > 0:
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
        
        max_drawdown = 0
        peak = equity.iloc[0]
        for value in equity:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        win_rate = 0
        if len(trades) >= 2:
            buy_trades = [t for t in trades if t['type'] == 'buy']
            sell_trades = [t for t in trades if t['type'] == 'sell']
            
            profits = []
            for i, buy in enumerate(buy_trades):
                if i < len(sell_trades):
                    sell = sell_trades[i]
                    profit = (sell['proceeds'] - buy['cost']) / buy['cost']
                    profits.append(profit)
            
            if profits:
                win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100
        
        return {
            'total_return_pct': total_return,
            'annualized_return_pct': annualized_return * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown * 100,
            'win_rate_pct': win_rate,
            'volatility_pct': returns.std() * np.sqrt(252) * 100
        }
    
    def print_results(self, results: Dict):
        """打印回测结果"""
        print("\n" + "="*50)
        print(f"回测结果 - {results.get('strategy_name', '策略')}")
        print("="*50)
        print(f"初始资金: ${self.initial_capital:,.2f}")
        print(f"最终资金: ${results['final_capital']:,.2f}")
        print(f"总收益率: {results['total_return_pct']:.2f}%")
        print(f"年化收益率: {results['annualized_return_pct']:.2f}%")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"最大回撤: {results['max_drawdown_pct']:.2f}%")
        print(f"胜率: {results['win_rate_pct']:.2f}%")
        print(f"波动率: {results['volatility_pct']:.2f}%")
        print(f"总交易次数: {results['total_trades']}")
        print("="*50 + "\n")
