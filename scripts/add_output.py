"""
添加交易记录保存和K线图绘制功能到 backtest_futures_minute.py
"""

with open('backtest_futures_minute.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在文件开头添加导入
import_addition = '''
import os
import sys

# 导入绘图模块
try:
    from kline_plotter import KLinePlotter
except ImportError:
    KLinePlotter = None
'''

# 在最后一个导入后添加
content = content.replace(
    'from typing import Dict, List, Tuple, Optional',
    'from typing import Dict, List, Tuple, Optional' + import_addition
)

# 2. 修改 run 函数，在 return 之前添加K线图绘制
old_run_end = '''        return self.generate_report(symbol, open_positions_info)
    
    def generate_report'''

new_run_end = '''        # 绘制K线图
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
    
    def generate_report'''

content = content.replace(old_run_end, new_run_end)

# 3. 修改 generate_report 函数，添加保存交易记录到CSV
old_generate = '''    def generate_report(self, symbol: str, open_positions_info: List[dict] = None) -> dict:
        if not self.trades:
            return {'symbol': symbol, 'total_trades': 0, 'message': '无交易'}'''

new_generate = '''    def generate_report(self, symbol: str, open_positions_info: List[dict] = None) -> dict:
        # 保存交易记录到CSV
        self.save_trades_csv(symbol)
        
        if not self.trades:
            return {'symbol': symbol, 'total_trades': 0, 'message': '无交易'}'''

content = content.replace(old_generate, new_generate)

# 4. 在 generate_report 函数末尾添加 save_trades_csv 方法
# 找到 generate_report 函数的 return 语句
old_return = '''            'signals': self.signals
        }


# ==================== 主函数'''

new_return = '''            'signals': self.signals
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


# ==================== 主函数'''

content = content.replace(old_return, new_return)

with open('backtest_futures_minute.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - 已添加交易记录保存和K线图绘制功能')
