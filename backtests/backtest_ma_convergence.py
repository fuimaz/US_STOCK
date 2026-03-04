"""
均线收敛策略回测

策略规则:
1. 日线交易
2. 买入条件:
   - 5日均线 < 20日均线
   - 10日均线 < 20日均线
   - |5日均线 - 10日均线| / 20日均线 <= 1% (5日与10日相差1%内)
   - 5日均线 >= 20日均线 * (1 - 1.5%) (5日均线低于20日均线1.5%以内)
   - 10日均线 >= 20日均线 * (1 - 1.5%) (10日均线低于20日均线1.5%以内)
3. 止损: 4%
4. 止盈: 峰值收益>=10%后回抽MA5止盈
"""

import pandas as pd
import numpy as np
import os
import re
import concurrent.futures as cf
from datetime import datetime, timedelta
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.ma_convergence_strategy import calculate_indicators, generate_signals
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


_A_SHARE_SYMBOL_RE = re.compile(r"^\d{6}\.(SZ|SS|BJ)$", re.IGNORECASE)


def _is_a_share_symbol(symbol: str) -> bool:
    return bool(_A_SHARE_SYMBOL_RE.match(symbol))


def get_all_stock_files(
    data_dir='data_cache',
    years=20,
    a_share_only: bool = False,
    exclude_symbols=None,
    include_symbols=None,
):
    """获取所有股票数据文件"""
    stock_files = []
    exclude = {str(s).upper() for s in (exclude_symbols or [])}
    include = {str(s).upper() for s in (include_symbols or [])} if include_symbols else None
    
    if not os.path.exists(data_dir):
        return stock_files
    
    for filename in os.listdir(data_dir):
        if filename.endswith('.csv'):
            # 只获取20年日线数据
            if f'{years}y_1d_forward.csv' in filename:
                # 排除A股分钟数据目录
                if '_1y_1d' not in filename and 'minute' not in filename.lower():
                    symbol = filename.split('_')[0]
                    if a_share_only and (not _is_a_share_symbol(symbol)):
                        continue
                    if include is not None and symbol.upper() not in include:
                        continue
                    if symbol.upper() in exclude:
                        continue
                    stock_files.append(os.path.join(data_dir, filename))
    
    return sorted(stock_files)


def filter_by_date_range(data, start_date=None, end_date=None):
    """按日期范围筛选数据"""
    if start_date:
        data = data[data.index >= start_date]
    if end_date:
        data = data[data.index <= end_date]
    return data


def _backtest_worker(args):
    filepath, start_date, end_date, signal_params = args
    filename = os.path.basename(filepath)
    symbol = filename.split('_')[0]

    data = pd.read_csv(filepath, index_col='datetime', parse_dates=True)
    if len(data) < 50:
        return None

    if start_date or end_date:
        data = filter_by_date_range(data, start_date, end_date)
    if len(data) < 50:
        return None

    return backtest_on_stock(data, symbol, signal_params=signal_params)


def backtest_on_stock(data, symbol, initial_capital=100000, signal_params=None):
    """
    对单只股票进行均线收敛策略回测
    
    Args:
        data: 股票数据
        symbol: 股票代码
        initial_capital: 初始资金
    
    Returns:
        回测结果字典
    """
    # 复制数据
    df = data.copy()
    
    # 去掉不需要的列，只保留必要的
    cols_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
    df = df[[c for c in cols_to_keep if c in df.columns]]
    
    if len(df) < 50:
        return None
    
    # 计算指标
    if signal_params and isinstance(signal_params, dict):
        volume_ma_period = int(signal_params.get('volume_ma_period', 20))
    else:
        volume_ma_period = 20
    df_indicators = calculate_indicators(df, volume_ma_period=volume_ma_period)
    
    # 生成信号
    signal_params = signal_params if isinstance(signal_params, dict) else {}
    df_with_signals = generate_signals(df_indicators, **signal_params)
    
    if df_with_signals is None or df_with_signals.empty:
        return None
    
    # 回测逻辑
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
        
        # 计算当前权益
        if position > 0:
            current_equity = cash + position * close_price
        else:
            current_equity = cash
        equity_curve.append({'date': date, 'equity': current_equity})
        
        # 买入信号
        if row.get('signal') == 1 and position == 0 and cash > 0:
            # 使用全部可用资金买入（单只股票一笔资金）
            buy_price = row.get('entry_price', np.nan)
            if pd.isna(buy_price):
                buy_price = close_price
            shares_to_buy = int(cash / buy_price)
            if shares_to_buy > 0:
                position = shares_to_buy
                entry_price = buy_price
                entry_date = date
                cash = cash - shares_to_buy * buy_price
        
        # 卖出信号
        elif row.get('signal') == -1 and position > 0:
            sell_price = row.get('exit_price', np.nan)
            if pd.isna(sell_price):
                sell_price = close_price
            exit_reason = row.get('exit_reason', '')
            profit_pct = (sell_price - entry_price) / entry_price * 100
            
            trades.append({
                'symbol': symbol,
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_date': date,
                'exit_price': sell_price,
                'exit_reason': exit_reason,
                'return_pct': profit_pct,
                'holding_days': (date - entry_date).days if isinstance(date, pd.Timestamp) else 0
            })
            
            cash = cash + position * sell_price
            position = 0
            entry_price = 0
            entry_date = None
    
    # 最终持仓（如果还有持仓，按最后收盘价平仓）
    if position > 0:
        final_price = df_with_signals['Close'].iloc[-1]
        profit_pct = (final_price - entry_price) / entry_price * 100
        trades.append({
            'symbol': symbol,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'exit_date': df_with_signals.index[-1],
            'exit_price': final_price,
            'exit_reason': 'final_bar',
            'return_pct': profit_pct,
            'holding_days': (df_with_signals.index[-1] - entry_date).days if isinstance(entry_date, pd.Timestamp) else 0
        })
        cash = cash + position * final_price
        position = 0
    
    # 计算回测指标
    final_capital = cash
    total_return = (final_capital - initial_capital) / initial_capital * 100
    
    # 计算年化收益
    if len(df_with_signals) > 1:
        start_date = df_with_signals.index[0]
        end_date = df_with_signals.index[-1]
        days = (end_date - start_date).days
        if days > 0:
            years = days / 365
            annualized_return = ((final_capital / initial_capital) ** (1/years) - 1) * 100
        else:
            annualized_return = 0
    else:
        annualized_return = 0
    
    # 计算夏普比率
    if len(equity_curve) > 1:
        equity_values = [e['equity'] for e in equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        returns = returns[~np.isnan(returns) & ~np.isinf(returns) & (np.abs(returns) < 1)]
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0
    else:
        sharpe_ratio = 0
    
    # 计算最大回撤
    if len(equity_curve) > 0:
        equity_values = [e['equity'] for e in equity_curve]
        equity_series = pd.Series(equity_values)
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax * 100
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
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
        'total_trades': len(trades),
        'trades': trades
    }


def summarize_results(all_results, output_dir):
    """汇总回测结果"""
    # 过滤有效结果
    valid_results = []
    all_trades = []
    
    for r in all_results:
        if r is not None and not np.isnan(r.get('total_return_pct', np.nan)):
            valid_results.append(r)
            if 'trades' in r:
                all_trades.extend(r['trades'])
    
    if len(valid_results) == 0:
        print("没有有效的回测结果")
        return
    
    # 创建结果DataFrame
    df = pd.DataFrame(valid_results)
    
    # 保存详细结果
    csv_path = os.path.join(output_dir, 'ma_convergence_backtest.csv')
    df[['symbol', 'final_capital', 'total_return_pct', 'annualized_return_pct', 
        'sharpe_ratio', 'max_drawdown_pct', 'win_rate_pct', 'total_trades']].to_csv(
        csv_path, index=False, encoding='utf-8-sig')
    print(f"[OK] 详细结果已保存到: {csv_path}")
    
    # 保存交易记录
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_path = os.path.join(output_dir, 'ma_convergence_trades.csv')
        trades_df.to_csv(trades_path, index=False, encoding='utf-8-sig')
        print(f"[OK] 交易记录已保存到: {trades_path}")
    
    # 统计信息
    print("\n" + "=" * 80)
    print("回测统计汇总 (均线收敛策略)")
    print("=" * 80)
    
    print(f"\n总股票数: {len(df)}")
    
    profitable_stocks = df[df['total_return_pct'] > 0]
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
        print(f"平均交易次数: {df_with_trades['total_trades'].mean():.1f}")
        
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
    
    # 交易统计
    if all_trades:
        print("\n" + "-" * 80)
        print("交易统计:")
        print("-" * 80)
        trades_df = pd.DataFrame(all_trades)
        print(f"总交易次数: {len(trades_df)}")
        print(f"盈利交易: {len(trades_df[trades_df['return_pct'] > 0])}")
        print(f"亏损交易: {len(trades_df[trades_df['return_pct'] <= 0])}")
        print(f"平均持仓天数: {trades_df['holding_days'].mean():.1f}")
        print(f"平均收益: {trades_df['return_pct'].mean():.2f}%")
        print(f"最大单笔盈利: {trades_df['return_pct'].max():.2f}%")
        print(f"最大单笔亏损: {trades_df['return_pct'].min():.2f}%")


def run_backtest(
    data_dir='data_cache',
    years=20,
    start_date=None,
    end_date=None,
    a_share_only: bool = False,
    exclude_symbols=None,
    include_symbols=None,
    output_dir: str = 'results/ma_convergence_backtest',
    signal_params=None,
):
    """运行回测"""
    print("=" * 80)
    print("均线收敛策略回测")
    print("=" * 80)
    print()
    
    # 创建输出文件夹
    os.makedirs(output_dir, exist_ok=True)
    print(f"[OK] 结果将保存到: {output_dir}/")
    print()
    
    # 获取所有股票数据文件
    stock_files = get_all_stock_files(
        data_dir,
        years,
        a_share_only=a_share_only,
        exclude_symbols=exclude_symbols,
        include_symbols=include_symbols,
    )
    print(f"[OK] 找到 {len(stock_files)} 个股票数据文件")
    print()
    
    # 回测所有股票
    all_results = []
    success_count = 0
    fail_count = 0
    
    for i, filepath in enumerate(stock_files):
        filename = os.path.basename(filepath)
        symbol = filename.split('_')[0]
        
        if (i + 1) % 10 == 0:
            print(f"[{i+1}/{len(stock_files)}] 进度...")
        
        try:
            # 读取数据
            data = pd.read_csv(filepath, index_col='datetime', parse_dates=True)
            
            if len(data) < 50:
                fail_count += 1
                continue
            
            # 按日期范围筛选
            if start_date or end_date:
                data = filter_by_date_range(data, start_date, end_date)
            
            if len(data) < 50:
                fail_count += 1
                continue
            
            # 回测
            result = backtest_on_stock(data, symbol, signal_params=signal_params)
            if result:
                all_results.append(result)
                success_count += 1
            else:
                fail_count += 1
                
        except Exception as e:
            fail_count += 1
    
    print()
    print("=" * 80)
    print(f"回测完成！成功: {success_count}, 失败: {fail_count}")
    print("=" * 80)
    print()
    
    # 汇总结果
    summarize_results(all_results, output_dir)
    
    return all_results


def run_backtest_parallel(
    data_dir='data_cache',
    years=20,
    start_date=None,
    end_date=None,
    a_share_only: bool = False,
    workers: int = 8,
    exclude_symbols=None,
    include_symbols=None,
    output_dir: str = 'results/ma_convergence_backtest',
    signal_params=None,
):
    """并行运行回测（按股票文件并行）"""
    print("=" * 80)
    print("均线收敛策略回测 (Parallel)")
    print("=" * 80)
    print()

    os.makedirs(output_dir, exist_ok=True)
    print(f"[OK] 结果将保存到: {output_dir}/")
    print()

    stock_files = get_all_stock_files(
        data_dir,
        years,
        a_share_only=a_share_only,
        exclude_symbols=exclude_symbols,
        include_symbols=include_symbols,
    )
    print(f"[OK] 找到 {len(stock_files)} 个股票数据文件")
    print()

    all_results = []
    fail_count = 0

    signal_params = signal_params if isinstance(signal_params, dict) else {}
    tasks = [(fp, start_date, end_date, signal_params) for fp in stock_files]
    with cf.ProcessPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futures = [ex.submit(_backtest_worker, t) for t in tasks]
        for idx, fut in enumerate(cf.as_completed(futures), 1):
            try:
                res = fut.result()
                if res:
                    all_results.append(res)
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1

            if idx % 10 == 0 or idx == len(futures):
                print(f"[{idx}/{len(futures)}] 进度...")

    success_count = len(all_results)

    print()
    print("=" * 80)
    print(f"回测完成！成功: {success_count}, 失败: {fail_count}")
    print("=" * 80)
    print()

    summarize_results(all_results, output_dir)
    return all_results


if __name__ == '__main__':
    import argparse

    def _load_symbols_file(path: str) -> list[str]:
        p = str(path or "").strip()
        if not p:
            return []
        if not os.path.exists(p):
            raise SystemExit(f"symbols file not found: {p}")
        ext = os.path.splitext(p)[1].lower()
        if ext in (".csv", ".tsv"):
            sep = "\t" if ext == ".tsv" else ","
            df = pd.read_csv(p, sep=sep)
            if "symbol" in df.columns:
                syms = df["symbol"]
            else:
                syms = df.iloc[:, 0]
            return [str(s).strip() for s in syms.tolist() if str(s).strip()]
        # txt: one symbol per line
        lines = []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                lines.append(s)
        return lines

    parser = argparse.ArgumentParser(description="MA Convergence backtest (daily).")
    parser.add_argument("--data-dir", default="data_cache")
    parser.add_argument("--years", type=int, default=20)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--a-share-only", action="store_true", help="Only run for A-share symbols (e.g. 000001.SZ).")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers (1 = serial).")
    parser.add_argument("--output-dir", default="results/ma_convergence_backtest")
    parser.add_argument(
        "--exclude-symbols",
        default="",
        help="Comma-separated symbols to exclude (e.g. 600018.SS,000001.SZ).",
    )
    parser.add_argument(
        "--symbols-file",
        default="",
        help="Optional CSV/TSV/TXT file listing symbols to include (CSV/TSV prefers a 'symbol' column).",
    )
    parser.add_argument("--no-stop-loss", action="store_true", help="Disable stop-loss exits (hold until take-profit or final bar).")
    parser.add_argument("--stop-loss-pct", type=float, default=0.04, help="Fixed stop-loss percent (0.04=4%%). Used only when stop-loss enabled.")
    parser.add_argument("--time-exit-days", type=int, default=0, help="Exit after N holding days if peak profit never reached take-profit trigger (0=disabled).")
    parser.add_argument(
        "--volume-filter-mode",
        default="none",
        choices=["none", "contraction", "expansion", "contraction_then_expansion"],
        help="Volume filter mode for entries.",
    )
    parser.add_argument("--vol-ma", type=int, default=20, help="Volume moving average period.")
    parser.add_argument("--vol-ratio-max", type=float, default=0.8, help="contraction: require vol_ratio <= this.")
    parser.add_argument("--vol-ratio-min", type=float, default=1.2, help="expansion: require vol_ratio >= this.")
    parser.add_argument("--vol-setup-days", type=int, default=5, help="contraction_then_expansion: setup lookback days.")
    parser.add_argument("--vol-setup-max", type=float, default=0.8, help="contraction_then_expansion: setup vol_ratio max.")
    args = parser.parse_args()

    if not (0 < float(args.stop_loss_pct) < 1):
        raise SystemExit("--stop-loss-pct must be between 0 and 1 (e.g. 0.15 for 15%)")

    exclude_symbols = [s.strip() for s in str(args.exclude_symbols).split(",") if s.strip()]
    include_symbols = _load_symbols_file(args.symbols_file) if str(args.symbols_file).strip() else None
    signal_params = {
        "stop_loss_enabled": (not args.no_stop_loss),
        "stop_loss_pct": float(args.stop_loss_pct),
        "time_exit_enabled": int(args.time_exit_days) > 0,
        "max_holding_days": int(args.time_exit_days),
        "volume_filter_enabled": args.volume_filter_mode != "none",
        "volume_filter_mode": args.volume_filter_mode,
        "volume_ma_period": args.vol_ma,
        "volume_ratio_max": args.vol_ratio_max,
        "volume_ratio_min": args.vol_ratio_min,
        "volume_setup_lookback": args.vol_setup_days,
        "volume_setup_ratio_max": args.vol_setup_max,
    }

    if args.workers and args.workers > 1:
        run_backtest_parallel(
            data_dir=args.data_dir,
            years=args.years,
            start_date=args.start_date,
            end_date=args.end_date,
            a_share_only=args.a_share_only,
            workers=args.workers,
            exclude_symbols=exclude_symbols,
            include_symbols=include_symbols,
            output_dir=args.output_dir,
            signal_params=signal_params,
        )
    else:
        run_backtest(
            data_dir=args.data_dir,
            years=args.years,
            start_date=args.start_date,
            end_date=args.end_date,
            a_share_only=args.a_share_only,
            exclude_symbols=exclude_symbols,
            include_symbols=include_symbols,
            output_dir=args.output_dir,
            signal_params=signal_params,
        )
