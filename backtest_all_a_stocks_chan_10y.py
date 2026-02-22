"""
对所有A股数据进行缠论回测（近10年）
"""
import pandas as pd
import numpy as np
import os
from chan_theory_v5 import ChanTheory
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def get_all_a_stock_files():
    """
    获取所有A股数据文件
    
    Returns:
        A股数据文件列表
    """
    cache_dir = 'data_cache'
    a_stock_files = []
    
    if not os.path.exists(cache_dir):
        return a_stock_files
    
    for filename in os.listdir(cache_dir):
        # 沪市：600xxx.SS, 601xxx.SS, 603xxx.SS
        # 深市：000xxx.SZ, 002xxx.SZ, 300xxx.SZ
        if (filename.endswith('.csv') and 
            ('.SS' in filename or '.SZ' in filename) and
            '_20y_1d_forward.csv' in filename):
            a_stock_files.append(os.path.join(cache_dir, filename))
    
    return sorted(a_stock_files)

def filter_last_10_years(data):
    """
    筛选近10年的数据
    
    Args:
        data: 股票数据
    
    Returns:
        筛选后的数据
    """
    # 计算近10年的起始日期
    end_date = data.index[-1]
    start_date = end_date - timedelta(days=10 * 365)
    
    # 筛选数据
    filtered_data = data[data.index >= start_date].copy()
    
    return filtered_data

def backtest_chan_theory_on_stock(data_full, data_10y, symbol):
    """
    对单只股票进行缠论回测
    
    Args:
        data_full: 完整股票数据（20年）
        data_10y: 近10年股票数据
        symbol: 股票代码
    
    Returns:
        回测结果字典
    """
    # 初始化缠论指标
    chan = ChanTheory(k_type='day')
    
    # 完整分析（使用完整数据）
    result = chan.analyze(data_full)
    
    # 统计买卖点
    buy_points = chan.buy_points
    sell_points = chan.sell_points
    
    # 筛选近10年内的买卖点
    buy_points_10y = [bp for bp in buy_points if bp['index'] in data_10y.index]
    sell_points_10y = [sp for sp in sell_points if sp['index'] in data_10y.index]
    
    # 计算收益
    trades = []
    total_return = 0
    win_count = 0
    loss_count = 0
    
    for buy_point in buy_points_10y:
        buy_date = buy_point['index']
        buy_price = buy_point['price']
        
        # 找到下一个卖点
        sell_price = None
        sell_date = None
        
        for sell_point in sell_points_10y:
            if sell_point['index'] > buy_date:
                sell_date = sell_point['index']
                sell_price = sell_point['price']
                break
        
        # 如果没有卖点，使用最后一个价格
        if sell_price is None:
            sell_date = data_10y.index[-1]
            sell_price = data_10y['Close'].iloc[-1]
        
        # 计算收益率
        return_pct = (sell_price - buy_price) / buy_price * 100
        
        # 计算持仓天数
        holding_days = (sell_date - buy_date).days
        
        # 记录交易
        trades.append({
            'buy_date': buy_date,
            'buy_price': buy_price,
            'sell_date': sell_date,
            'sell_price': sell_price,
            'return_pct': return_pct,
            'holding_days': holding_days
        })
        
        # 统计
        total_return += return_pct
        if return_pct > 0:
            win_count += 1
        else:
            loss_count += 1
    
    # 计算买入持有收益
    if len(data_10y) > 0:
        buy_hold_return = (data_10y['Close'].iloc[-1] - data_10y['Close'].iloc[0]) / data_10y['Close'].iloc[0] * 100
    else:
        buy_hold_return = 0
    
    # 计算超额收益
    excess_return = total_return - buy_hold_return
    
    # 计算最大回撤
    if len(trades) > 0:
        cumulative_returns = []
        cum_return = 0
        for trade in trades:
            cum_return += trade['return_pct']
            cumulative_returns.append(cum_return)
        
        if len(cumulative_returns) > 0:
            max_cum_return = max(cumulative_returns)
            min_cum_return = min(cumulative_returns)
            max_drawdown = max_cum_return - min_cum_return
        else:
            max_drawdown = 0
    else:
        max_drawdown = 0
    
    # 计算平均持仓天数
    if len(trades) > 0:
        avg_holding_days = np.mean([trade['holding_days'] for trade in trades])
    else:
        avg_holding_days = 0
    
    # 计算平均收益率
    if len(trades) > 0:
        avg_return = total_return / len(trades)
    else:
        avg_return = 0
    
    # 计算胜率
    if len(trades) > 0:
        win_rate = win_count / len(trades) * 100
    else:
        win_rate = 0
    
    return {
        'symbol': symbol,
        'trade_count': len(trades),
        'avg_return': avg_return,
        'cumulative_return': total_return,
        'win_rate': win_rate,
        'win_count': win_count,
        'loss_count': loss_count,
        'avg_holding_days': avg_holding_days,
        'buy_hold_return': buy_hold_return,
        'excess_return': excess_return,
        'max_drawdown': max_drawdown,
        'trades': trades
    }

def summarize_results(all_results, output_dir):
    """
    汇总回测结果
    
    Args:
        all_results: 所有股票的回测结果
        output_dir: 输出目录
    """
    if len(all_results) == 0:
        print("没有有效的回测结果")
        return
    
    # 创建DataFrame
    df = pd.DataFrame([{
        '股票代码': r['symbol'],
        '交易次数': r['trade_count'],
        '平均收益率': r['avg_return'],
        '累计收益率': r['cumulative_return'],
        '胜率': r['win_rate'],
        '盈利次数': r['win_count'],
        '亏损次数': r['loss_count'],
        '平均持仓天数': r['avg_holding_days'],
        '买入持有收益': r['buy_hold_return'],
        '超额收益': r['excess_return'],
        '最大回撤': r['max_drawdown']
    } for r in all_results])
    
    # 保存到CSV
    csv_path = os.path.join(output_dir, 'all_a_stocks_backtest_10y.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✓ 详细结果已保存到: {csv_path}")
    
    # 打印统计信息
    print("\n" + "=" * 100)
    print("回测统计汇总")
    print("=" * 100)
    
    # 筛选有交易的股票
    df_with_trades = df[df['交易次数'] > 0]
    
    print(f"\n总股票数: {len(df)}")
    print(f"有交易的股票数: {len(df_with_trades)}")
    print(f"无交易的股票数: {len(df) - len(df_with_trades)}")
    
    if len(df_with_trades) > 0:
        print(f"\n平均交易次数: {df_with_trades['交易次数'].mean():.2f}")
        print(f"平均累计收益率: {df_with_trades['累计收益率'].mean():.2f}%")
        print(f"平均胜率: {df_with_trades['胜率'].mean():.2f}%")
        print(f"平均超额收益: {df_with_trades['超额收益'].mean():.2f}%")
        print(f"平均最大回撤: {df_with_trades['最大回撤'].mean():.2f}%")
        
        # 表现最好的股票
        print("\n" + "-" * 100)
        print("表现最好的股票（按累计收益率）:")
        print("-" * 100)
        top_stocks = df_with_trades.nlargest(10, '累计收益率')
        for idx, row in top_stocks.iterrows():
            print(f"  {row['股票代码']}: 累计收益={row['累计收益率']:.2f}%, 胜率={row['胜率']:.2f}%, 交易次数={int(row['交易次数'])}")
        
        # 表现最差的股票
        print("\n" + "-" * 100)
        print("表现最差的股票（按累计收益率）:")
        print("-" * 100)
        bottom_stocks = df_with_trades.nsmallest(10, '累计收益率')
        for idx, row in bottom_stocks.iterrows():
            print(f"  {row['股票代码']}: 累计收益={row['累计收益率']:.2f}%, 胜率={row['胜率']:.2f}%, 交易次数={int(row['交易次数'])}")
        
        # 胜率最高的股票
        print("\n" + "-" * 100)
        print("胜率最高的股票（交易次数>=5）:")
        print("-" * 100)
        df_with_enough_trades = df_with_trades[df_with_trades['交易次数'] >= 5]
        if len(df_with_enough_trades) > 0:
            high_win_rate_stocks = df_with_enough_trades.nlargest(10, '胜率')
            for idx, row in high_win_rate_stocks.iterrows():
                print(f"  {row['股票代码']}: 胜率={row['胜率']:.2f}%, 累计收益={row['累计收益率']:.2f}%, 交易次数={int(row['交易次数'])}")
    
    # 绘制统计图表
    plot_summary_charts(df, output_dir)

def plot_summary_charts(df, output_dir):
    """
    绘制汇总图表
    
    Args:
        df: 回测结果DataFrame
        output_dir: 输出目录
    """
    # 筛选有交易的股票
    df_with_trades = df[df['交易次数'] > 0]
    
    if len(df_with_trades) == 0:
        return
    
    # 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. 累计收益率分布
    ax1 = axes[0, 0]
    ax1.hist(df_with_trades['累计收益率'], bins=30, color='steelblue', edgecolor='black', alpha=0.7)
    ax1.set_xlabel('累计收益率 (%)', fontsize=12)
    ax1.set_ylabel('股票数量', fontsize=12)
    ax1.set_title('累计收益率分布', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.axvline(x=0, color='red', linestyle='--', linewidth=2, label='盈亏平衡线')
    ax1.legend()
    
    # 2. 胜率分布
    ax2 = axes[0, 1]
    ax2.hist(df_with_trades['胜率'], bins=20, color='lightcoral', edgecolor='black', alpha=0.7)
    ax2.set_xlabel('胜率 (%)', fontsize=12)
    ax2.set_ylabel('股票数量', fontsize=12)
    ax2.set_title('胜率分布', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.axvline(x=50, color='red', linestyle='--', linewidth=2, label='50%胜率线')
    ax2.legend()
    
    # 3. 交易次数分布
    ax3 = axes[1, 0]
    ax3.hist(df_with_trades['交易次数'], bins=20, color='lightgreen', edgecolor='black', alpha=0.7)
    ax3.set_xlabel('交易次数', fontsize=12)
    ax3.set_ylabel('股票数量', fontsize=12)
    ax3.set_title('交易次数分布', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # 4. 累计收益率 vs 胜率散点图
    ax4 = axes[1, 1]
    scatter = ax4.scatter(df_with_trades['胜率'], df_with_trades['累计收益率'], 
                         c=df_with_trades['交易次数'], cmap='viridis', 
                         alpha=0.6, s=100, edgecolors='black')
    ax4.set_xlabel('胜率 (%)', fontsize=12)
    ax4.set_ylabel('累计收益率 (%)', fontsize=12)
    ax4.set_title('累计收益率 vs 胜率', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='red', linestyle='--', linewidth=2)
    ax4.axvline(x=50, color='red', linestyle='--', linewidth=2)
    plt.colorbar(scatter, ax=ax4, label='交易次数')
    
    plt.tight_layout()
    chart_path = os.path.join(output_dir, 'backtest_summary_10y.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 汇总图表已保存到: {chart_path}")

def backtest_all_a_stocks():
    """
    对所有A股进行缠论回测（近10年）
    """
    print("=" * 100)
    print("对所有A股进行缠论回测（近10年）")
    print("=" * 100)
    print()
    
    # 创建输出文件夹
    output_dir = 'results/chan_backtest_10y'
    os.makedirs(output_dir, exist_ok=True)
    print(f"✓ 结果将保存到: {output_dir}/")
    print()
    
    # 获取所有A股数据文件
    a_stock_files = get_all_a_stock_files()
    print(f"✓ 找到 {len(a_stock_files)} 个A股数据文件")
    print()
    
    # 回测所有股票
    all_results = []
    success_count = 0
    fail_count = 0
    
    for i, filepath in enumerate(a_stock_files):
        # 提取股票代码
        filename = os.path.basename(filepath)
        symbol = filename.split('_')[0]
        
        print(f"[{i+1}/{len(a_stock_files)}] 正在回测 {symbol}...")
        
        try:
            # 读取数据
            data = pd.read_csv(filepath, index_col='datetime', parse_dates=True)
            
            if len(data) < 100:
                print(f"  ✗ 数据量不足（{len(data)}条），跳过")
                fail_count += 1
                continue
            
            # 筛选近10年数据
            data_10y = filter_last_10_years(data)
            
            if len(data_10y) < 50:
                print(f"  ✗ 近10年数据量不足（{len(data_10y)}条），跳过")
                fail_count += 1
                continue
            
            print(f"  ✓ 近10年数据: {len(data_10y)} 条")
            
            # 回测
            result = backtest_chan_theory_on_stock(data, data_10y, symbol)
            all_results.append(result)
            success_count += 1
            
            print(f"  ✓ 交易次数: {result['trade_count']}, 累计收益: {result['cumulative_return']:.2f}%, 胜率: {result['win_rate']:.2f}%")
            
        except Exception as e:
            print(f"  ✗ 回测失败: {e}")
            fail_count += 1
    
    print()
    print("=" * 100)
    print(f"回测完成！成功: {success_count}, 失败: {fail_count}")
    print("=" * 100)
    print()
    
    # 汇总结果
    summarize_results(all_results, output_dir)

if __name__ == '__main__':
    backtest_all_a_stocks()
