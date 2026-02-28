"""
Equity Millipede策略回测（近10年日线）
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indicators.millipede_strategy import calculate_indicators, generate_signals
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 行业过滤 - 排除房地产和酒类
EXCLUDED_INDUSTRIES = ['房地产', '白酒', '酒类', '啤酒', '红酒']
EXCLUDED_STOCKS = {
    '000002.SZ': '万科A',   # 房地产
    '000533.SZ': '顺钠股份', # 房地产
    '000568.SZ': '泸州老窖', # 白酒
    '000858.SZ': '五粮液',   # 白酒
    '002304.SZ': '洋河股份', # 白酒
    '600048.SS': '保利发展', # 房地产
    '600519.SS': '贵州茅台', # 白酒
}

def get_all_a_stock_files():
    """获取所有A股数据文件（20年日线）"""
    cache_dir = 'data_cache'
    a_stock_files = []
    
    if not os.path.exists(cache_dir):
        return a_stock_files
    
    for filename in os.listdir(cache_dir):
        if (filename.endswith('.csv') and 
            ('.SS' in filename or '.SZ' in filename) and
            '_20y_1d_forward.csv' in filename):
            a_stock_files.append(os.path.join(cache_dir, filename))
    
    return sorted(a_stock_files)

def filter_last_10_years(data):
    """筛选近10年的数据"""
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10 * 365)
    filtered_data = data[data.index >= start_date].copy()
    return filtered_data

def backtest_millipede_on_stock(data_full, data_10y, symbol):
    """
    对单只股票进行Millipede策略回测
    
    Args:
        data_full: 完整股票数据（20年）
        data_10y: 近10年股票数据
        symbol: 股票代码
    
    Returns:
        回测结果字典
    """
    initial_capital = 100000
    
    # 重命名列以匹配策略要求（保持原样，策略使用Open/High/Low/Close/Volume）
    data = data_10y.copy()
    
    # 去掉不需要的列
    cols_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
    data = data[[c for c in cols_to_keep if c in data.columns]]
    
    # 计算指标
    df_indicators = calculate_indicators(data)
    
    # 生成信号
    df_with_signals = generate_signals(df_indicators)
    
    if df_with_signals is None or df_with_signals.empty:
        return {
            'symbol': symbol,
            'final_capital': np.nan,
            'total_return_pct': np.nan,
            'annualized_return_pct': np.nan,
            'sharpe_ratio': np.nan,
            'max_drawdown_pct': np.nan,
            'win_rate_pct': np.nan,
            'total_trades': 0
        }
    
    # 简单的回测逻辑
    position = 0  # 持仓股数
    cash = initial_capital
    entry_price = 0
    entry_date = None
    trades = []
    equity_curve = []
    
    for i in range(len(df_with_signals)):
        row = df_with_signals.iloc[i]
        date = df_with_signals.index[i]
        close_price = row['Close']
        
        current_equity = cash + position * close_price if position > 0 else cash
        equity_curve.append(current_equity)
        
        # 买入信号
        if row.get('signal') == 1 and position == 0 and cash > 0:
            # 计算买入数量（使用可用资金的一半）
            shares_to_buy = int(cash * 0.5 / close_price)
            if shares_to_buy > 0:
                position = shares_to_buy
                entry_price = close_price
                entry_date = date
                cash = cash - shares_to_buy * close_price
        
        # 卖出信号
        elif row.get('signal') == -1 and position > 0:
            sell_price = close_price
            profit = (sell_price - entry_price) / entry_price * 100
            
            trades.append({
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_date': date,
                'exit_price': sell_price,
                'return_pct': profit
            })
            
            cash = cash + position * sell_price
            position = 0
            entry_price = 0
            entry_date = None
    
    # 最终持仓
    if position > 0:
        final_price = df_with_signals['Close'].iloc[-1]
        profit = (final_price - entry_price) / entry_price * 100
        trades.append({
            'entry_date': entry_date,
            'entry_price': entry_price,
            'exit_date': df_with_signals.index[-1],
            'exit_price': final_price,
            'return_pct': profit
        })
        cash = cash + position * final_price
        position = 0
    
    # 计算指标
    final_capital = cash
    total_return = (final_capital - initial_capital) / initial_capital * 100
    
    # 计算年化收益
    days = (df_with_signals.index[-1] - df_with_signals.index[0]).days
    if days > 0:
        years = days / 365
        annualized_return = ((final_capital / initial_capital) ** (1/years) - 1) * 100
    else:
        annualized_return = 0
    
    # 计算夏普比率
    if len(equity_curve) > 1:
        returns = np.diff(equity_curve) / equity_curve[:-1]
        returns = returns[~np.isnan(returns) & ~np.isinf(returns)]
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0
    else:
        sharpe_ratio = 0
    
    # 计算最大回撤
    if len(equity_curve) > 0:
        equity_series = pd.Series(equity_curve)
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax * 100
        max_drawdown = abs(drawdown.min())
    else:
        max_drawdown = 0
    
    # 计算胜率
    if len(trades) > 0:
        win_count = sum(1 for t in trades if t['return_pct'] > 0)
        win_rate = win_count / len(trades) * 100
    else:
        win_rate = 0
    
    return {
        'symbol': symbol,
        'final_capital': final_capital,
        'total_return_pct': total_return,
        'annualized_return_pct': annualized_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown_pct': max_drawdown,
        'win_rate_pct': win_rate,
        'total_trades': len(trades)
    }

def summarize_results(all_results, output_dir):
    """汇总回测结果"""
    # 过滤有效结果
    valid_results = [r for r in all_results if not np.isnan(r.get('total_return_pct', np.nan))]
    
    if len(valid_results) == 0:
        print("没有有效的回测结果")
        return
    
    # 创建DataFrame
    df = pd.DataFrame(valid_results)
    
    # 保存到CSV
    csv_path = os.path.join(output_dir, 'millipede_backtest_10y.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✓ 详细结果已保存到: {csv_path}")
    
    # 统计信息
    print("\n" + "=" * 80)
    print("回测统计汇总 (Equity Millipede 策略 - 10年日线)")
    print("=" * 80)
    
    profitable_stocks = df[df['total_return_pct'] > 0]
    print(f"\n总股票数: {len(df)}")
    print(f"盈利股票数: {len(profitable_stocks)} ({len(profitable_stocks)/len(df)*100:.1f}%)")
    print(f"亏损股票数: {len(df) - len(profitable_stocks)}")
    
    # 有交易的股票
    df_with_trades = df[df['total_trades'] > 0]
    print(f"\n有交易的股票数: {len(df_with_trades)}")
    
    if len(df_with_trades) > 0:
        print(f"\n平均总收益: {df_with_trades['total_return_pct'].mean():.2f}%")
        print(f"平均年化收益: {df_with_trades['annualized_return_pct'].mean():.2f}%")
        print(f"平均胜率: {df_with_trades['win_rate_pct'].mean():.2f}%")
        print(f"平均最大回撤: {df_with_trades['max_drawdown_pct'].mean():.2f}%")
        
        # Top 10 盈利股票
        print("\n" + "-" * 80)
        print("Top 10 盈利股票:")
        print("-" * 80)
        top_stocks = df_with_trades.nlargest(10, 'total_return_pct')
        for idx, row in top_stocks.iterrows():
            print(f"  {row['symbol']}: 收益={row['total_return_pct']:.2f}%, 年化={row['annualized_return_pct']:.2f}%, 胜率={row['win_rate_pct']:.2f}%, 交易={int(row['total_trades'])}")
        
        # Top 10 亏损股票
        print("\n" + "-" * 80)
        print("Top 10 亏损股票:")
        print("-" * 80)
        bottom_stocks = df_with_trades.nsmallest(10, 'total_return_pct')
        for idx, row in bottom_stocks.iterrows():
            print(f"  {row['symbol']}: 收益={row['total_return_pct']:.2f}%, 年化={row['annualized_return_pct']:.2f}%, 胜率={row['win_rate_pct']:.2f}%, 交易={int(row['total_trades'])}")

def backtest_all_a_stocks():
    """对所有A股进行Millipede策略回测（近10年日线）"""
    print("=" * 80)
    print("Equity Millipede 策略回测（近10年日线）")
    print("=" * 80)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/millipede_backtest_10y'
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ 结果将保存到: {output_dir}/")
    print()
    
    # 获取所有A股数据文件
    a_stock_files = get_all_a_stock_files()
    print(f"✓ 找到 {len(a_stock_files)} 个A股数据文件")
    print()
    
    # 过滤排除的股票
    filtered_files = []
    for filepath in a_stock_files:
        filename = os.path.basename(filepath)
        symbol = filename.split('_')[0]
        if symbol in EXCLUDED_STOCKS:
            stock_name = EXCLUDED_STOCKS[symbol]
            print(f"[行业过滤] 排除 {symbol} {stock_name}")
        else:
            filtered_files.append(filepath)
    
    print(f"\n找到 {len(filtered_files)} 只股票（已过滤房地产和酒类行业）")
    print()
    
    # 回测所有股票
    all_results = []
    success_count = 0
    fail_count = 0
    
    for i, filepath in enumerate(filtered_files):
        filename = os.path.basename(filepath)
        symbol = filename.split('_')[0]
        
        if (i + 1) % 10 == 0:
            print(f"[{i+1}/{len(filtered_files)}] 进度...")
        
        try:
            # 读取数据
            data = pd.read_csv(filepath, index_col='datetime', parse_dates=True)
            
            if len(data) < 100:
                fail_count += 1
                continue
            
            # 筛选近10年数据
            data_10y = filter_last_10_years(data)
            
            if len(data_10y) < 50:
                fail_count += 1
                continue
            
            # 回测
            result = backtest_millipede_on_stock(data, data_10y, symbol)
            all_results.append(result)
            success_count += 1
            
        except Exception as e:
            fail_count += 1
    
    print()
    print("=" * 80)
    print(f"回测完成！成功: {success_count}, 失败: {fail_count}")
    print("=" * 80)
    print()
    
    # 汇总结果
    summarize_results(all_results, output_dir)

if __name__ == '__main__':
    backtest_all_a_stocks()
