"""
成交量突破策略回测 V2 - 优化版本
- 添加日线趋势过滤（只在日线MA20向上时交易）
- 放宽止损至7-8%
- 优化止盈逻辑：盈利>15%后启动移动止损（回撤5%止盈）
"""
import argparse
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class PositionState:
    """持仓状态"""
    shares: float = 0.0
    avg_cost: float = 0.0
    entry_price: float = 0.0
    peak_price: float = 0.0  # 持仓期间的最高价
    peak_profit_pct: float = 0.0  # 持仓期间曾经达到的最高收益率
    trailing_stop_pct: float = 0.0  # 移动止损线
    entry_time: Optional[pd.Timestamp] = None
    is_long: bool = True


def load_minute_data(symbol: str, period: str) -> Optional[pd.DataFrame]:
    """加载分钟级数据"""
    filename = f"{symbol}_{period}.csv"
    filepath = os.path.join("data_cache", "a_stock_minute", filename)
    
    if not os.path.exists(filepath):
        cache_dir = os.path.join("data_cache", "a_stock_minute")
        for f in os.listdir(cache_dir):
            if f.endswith(f"_{period}.csv"):
                file_symbol = f[:-len(f"_{period}.csv")]
                if file_symbol == symbol:
                    filepath = os.path.join(cache_dir, f)
                    break
        else:
            return None
    
    try:
        df = pd.read_csv(filepath)
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
        elif 'day' in df.columns:
            df['day'] = pd.to_datetime(df['day'])
            df.set_index('day', inplace=True)
        
        rename_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
        for old, new in rename_map.items():
            if old in df.columns:
                df.rename(columns={old: new}, inplace=True)
        
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            return None
        
        return df[required_cols].copy()
    except Exception as e:
        print(f"加载数据失败 {filepath}: {e}")
        return None


def get_daily_indicators(df_minute: pd.DataFrame) -> pd.DataFrame:
    """
    从分钟数据计算日线指标
    - MA20: 用于判断日线趋势
    - MA5: 可能保留用于其他用途
    """
    # 统一列名
    data = df_minute.copy()
    rename_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
    for old, new in rename_map.items():
        if old in data.columns:
            data.rename(columns={old: new}, inplace=True)
    
    daily = data.resample('D').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    # 计算日线MA20（趋势判断）
    daily['MA20'] = daily['Close'].rolling(window=20).mean()
    # 日线MA5
    daily['MA5'] = daily['Close'].rolling(window=5).mean()
    
    # 判断日线趋势：收盘价 > MA20 为多头趋势
    daily['trend_up'] = daily['Close'] > daily['MA20']
    
    # 转换为日期索引以便分钟数据匹配
    daily.index = daily.index.date
    
    return daily[['Close', 'MA20', 'MA5', 'trend_up']]


def get_symbols_for_period(period: str) -> List[str]:
    """获取指定周期的所有股票代码"""
    cache_dir = os.path.join("data_cache", "a_stock_minute")
    if not os.path.exists(cache_dir):
        return []
    
    suffix = f"_{period}.csv"
    symbols = set()
    
    for filename in os.listdir(cache_dir):
        if filename.endswith(suffix):
            symbol = filename[:-len(suffix)]
            symbols.add(symbol)
    
    return sorted(list(symbols))


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 100000.0,
    commission: float = 0.001,
    slippage: float = 0.0005,
    volume_ma_period: int = 20,
    volume_ratio: float = 1.5,
    stop_loss_pct: float = 0.08,  # 放宽至8%
    take_profit_trigger_pct: float = 0.15,  # 15%后启动移动止损
    trailing_stop_pct: float = 0.05,  # 回撤5%止盈
) -> Dict:
    """运行回测"""
    data = df.copy()
    
    # 计算分钟级基础指标
    data['change'] = data['Close'].pct_change()
    data['is_bullish'] = data['Close'] > data['Open']
    data['is_bearish'] = data['Close'] < data['Open']
    
    # 成交量均线
    data['volume_ma'] = data['Volume'].rolling(window=volume_ma_period).mean()
    data['volume_spike'] = data['Volume'] > data['volume_ma'] * volume_ratio
    
    # 获取日线指标
    daily_indicators = get_daily_indicators(df)
    
    # 生成交易信号
    data['buy_signal'] = False
    data['sell_signal'] = False
    
    # 放量阳线 -> 做多
    data.loc[
        (data['is_bullish']) & 
        (data['volume_spike']) & 
        (data['volume_ma'].notna()),
        'buy_signal'
    ] = True
    
    # 放量阴线 -> 做空（暂不做空，只做多）
    data.loc[
        (data['is_bearish']) & 
        (data['volume_spike']) & 
        (data['volume_ma'].notna()),
        'sell_signal'
    ] = True
    
    # 开始回测
    cash = initial_capital
    pos = PositionState()
    trades = []
    equity_curve = []
    
    for i in range(len(data)):
        row = data.iloc[i]
        date = data.index[i]
        close_price = float(row['Close'])
        high_price = float(row['High'])
        low_price = float(row['Low'])
        
        # 获取当日日线趋势
        date_date = date.date() if hasattr(date, 'date') else date
        daily_trend_up = False
        if date_date in daily_indicators.index:
            daily_trend_up = daily_indicators.loc[date_date, 'trend_up']
        
        # ========== 处理卖出 ==========
        if pos.shares > 0:
            current_profit_pct = (close_price / pos.avg_cost - 1.0)
            
            # 更新峰值
            pos.peak_price = max(pos.peak_price, close_price)
            pos.peak_profit_pct = max(pos.peak_profit_pct, current_profit_pct)
            
            # 更新移动止损线（当盈利超过take_profit_trigger_pct后）
            if pos.peak_profit_pct >= take_profit_trigger_pct:
                # 移动止损线 = 峰值 * (1 - trailing_stop_pct)
                pos.trailing_stop_pct = trailing_stop_pct
            
            sell_reason = None
            should_sell = False
            
            # 1. 止损检查（放宽至8%）
            stop_price = pos.avg_cost * (1 - stop_loss_pct)
            if close_price <= stop_price or low_price <= stop_price:
                should_sell = True
                sell_reason = "stop_loss"
            
            # 2. 移动止损止盈（盈利>15%后，回撤5%止盈）
            if not should_sell and pos.trailing_stop_pct > 0:
                # 移动止损价 = 峰值 * (1 - trailing_stop_pct)
                trailing_stop_price = pos.peak_price * (1 - trailing_stop_pct)
                if close_price <= trailing_stop_price or low_price <= trailing_stop_price:
                    should_sell = True
                    sell_reason = "trailing_stop"
            
            profit_pct = current_profit_pct
            
            if should_sell:
                proceeds = pos.shares * close_price * (1 - slippage) * (1 - commission)
                cash = cash + proceeds
                
                trade = {
                    "date": date,
                    "type": "sell",
                    "price": close_price,
                    "shares": pos.shares,
                    "value": proceeds,
                    "reason": sell_reason,
                    "profit_pct": profit_pct * 100,
                }
                trades.append(trade)
                
                pos = PositionState()
        
        # ========== 处理买入 ==========
        buy_signal = bool(row.get('buy_signal', False))
        
        # 只在日线趋势向上时买入
        if pos.shares == 0 and buy_signal and daily_trend_up:
            max_shares = int(cash / (close_price * (1 + slippage) * (1 + commission)))
            if max_shares > 0:
                cost = max_shares * close_price * (1 + slippage) * (1 + commission)
                pos.shares = max_shares
                pos.avg_cost = close_price * (1 + slippage)
                pos.entry_price = close_price
                pos.peak_price = close_price
                pos.peak_profit_pct = 0.0
                pos.trailing_stop_pct = 0.0  # 初始化移动止损
                pos.entry_time = date
                pos.is_long = True
                cash -= cost
                
                trade = {
                    "date": date,
                    "type": "buy",
                    "price": close_price,
                    "shares": max_shares,
                    "value": cost,
                    "reason": "long_entry",
                }
                trades.append(trade)
        
        # 记录权益
        current_equity = cash + pos.shares * close_price if pos.shares != 0 else cash
        equity_curve.append({
            "date": date,
            "equity": current_equity,
            "close": close_price,
            "cash": cash,
            "position": pos.shares,
        })
    
    # 最终平仓
    if pos.shares != 0:
        final_price = float(data['Close'].iloc[-1])
        final_profit_pct = (final_price / pos.avg_cost - 1.0) if pos.is_long else (pos.avg_cost / final_price - 1.0)
        
        proceeds = pos.shares * final_price * (1 - slippage) * (1 - commission)
        
        trade = {
            "date": data.index[-1],
            "type": "close",
            "price": final_price,
            "shares": pos.shares,
            "value": proceeds,
            "reason": "final_close",
            "profit_pct": final_profit_pct * 100,
        }
        trades.append(trade)
        
        cash = cash + proceeds
        equity_curve[-1]["equity"] = cash
        equity_curve[-1]["cash"] = cash
    
    # 计算统计指标
    eq_df = pd.DataFrame(equity_curve).set_index("date")
    if len(eq_df) > 1:
        returns = eq_df["equity"].pct_change().dropna()
        total_return = (cash - initial_capital) / initial_capital
        years = len(eq_df) / (252 * 4 * 60)
        years = max(years, 1/252)
        annualized = (cash / initial_capital) ** (1 / years) - 1 if years > 0 else 0
        sharpe = (returns.mean() / returns.std() * np.sqrt(252 * 4 * 60)) if returns.std() > 0 else 0
        running_peak = eq_df["equity"].cummax()
        drawdown = ((running_peak - eq_df["equity"]) / running_peak).max() if len(running_peak) > 0 else 0
    else:
        total_return = 0
        annualized = 0
        sharpe = 0
        drawdown = 0
    
    # 计算胜率
    trade_df = pd.DataFrame(trades)
    win_count = 0
    total_round_trips = 0
    
    if not trade_df.empty:
        close_trades = trade_df[trade_df["type"].isin(["sell", "close"])]
        for _, row in close_trades.iterrows():
            profit_pct = row.get("profit_pct", 0)
            if profit_pct > 0:
                win_count += 1
            total_round_trips += 1
    
    win_rate = (win_count / total_round_trips * 100) if total_round_trips > 0 else 0
    
    return {
        "final_capital": cash,
        "total_return": total_return,
        "total_return_pct": total_return * 100,
        "annualized_return_pct": annualized * 100,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": drawdown * 100,
        "win_rate_pct": win_rate,
        "total_trades": len(trade_df),
        "equity_curve": eq_df,
        "trades": trade_df,
        "signals": data,
    }


def print_summary(symbol: str, result: Dict):
    """打印回测结果摘要"""
    print("=" * 70)
    print(f"股票: {symbol}")
    print(f"最终资金: {result['final_capital']:.2f}")
    print(f"总收益: {result['total_return_pct']:.2f}%")
    print(f"年化收益: {result['annualized_return_pct']:.2f}%")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"最大回撤: {result['max_drawdown_pct']:.2f}%")
    print(f"胜率: {result['win_rate_pct']:.2f}%")
    print(f"交易次数: {result['total_trades']}")
    print("=" * 70)


def save_results(symbol: str, output_dir: str, result: Dict):
    """保存回测结果"""
    os.makedirs(output_dir, exist_ok=True)
    
    signal_file = os.path.join(output_dir, f"{symbol}_signals.csv")
    result['signals'].to_csv(signal_file, encoding='utf-8-sig')
    
    trades_file = os.path.join(output_dir, f"{symbol}_trades.csv")
    result['trades'].to_csv(trades_file, index=False, encoding='utf-8-sig')
    
    equity_file = os.path.join(output_dir, f"{symbol}_equity.csv")
    result['equity_curve'].to_csv(equity_file, encoding='utf-8-sig')
    
    summary_data = [{
        "symbol": symbol,
        "final_capital": result['final_capital'],
        "total_return_pct": result['total_return_pct'],
        "annualized_return_pct": result['annualized_return_pct'],
        "sharpe_ratio": result['sharpe_ratio'],
        "max_drawdown_pct": result['max_drawdown_pct'],
        "win_rate_pct": result['win_rate_pct'],
        "total_trades": result['total_trades'],
    }]
    summary_file = os.path.join(output_dir, f"{symbol}_summary.csv")
    pd.DataFrame(summary_data).to_csv(summary_file, index=False, encoding='utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description="成交量突破策略回测 V2 - 优化版")
    parser.add_argument("--symbol", default="", help="单只股票代码")
    parser.add_argument("--period", choices=["15min", "30min", "60min"], default="60min", help="时间周期")
    parser.add_argument("--output-dir", default="results/volume_breakout_v2", help="输出目录")
    parser.add_argument("--initial-capital", type=float, default=100000.0, help="初始资金")
    parser.add_argument("--commission", type=float, default=0.001, help="手续费率")
    parser.add_argument("--slippage", type=float, default=0.0005, help="滑点")
    parser.add_argument("--volume-ma-period", type=int, default=20, help="成交量均线周期")
    parser.add_argument("--volume-ratio", type=float, default=1.5, help="成交量放大倍数")
    parser.add_argument("--stop-loss", type=float, default=0.08, help="止损百分比(默认8)")
    parser.add_argument("--take-profit-trigger", type=float, default=0.15, help="移动止损触发涨幅(默认15)")
    parser.add_argument("--trailing-stop", type=float, default=0.05, help="移动止损回撤百分比(默认5)")
    parser.add_argument("--universe", choices=["single", "all"], default="single", help="回测范围")
    args = parser.parse_args()
    
    if args.universe == "all":
        symbols = get_symbols_for_period(args.period)
        print(f"找到 {len(symbols)} 只股票")
    else:
        if not args.symbol:
            print("请指定股票代码 --symbol")
            return
        symbols = [args.symbol]
    
    all_results = []
    
    for symbol in symbols:
        print(f"\n处理 {symbol}...")
        
        data = load_minute_data(symbol, args.period)
        if data is None or len(data) < 100:
            print(f"  跳过: 数据不足")
            continue
        
        print(f"  数据量: {len(data)} 条")
        
        result = run_backtest(
            df=data,
            initial_capital=args.initial_capital,
            commission=args.commission,
            slippage=args.slippage,
            volume_ma_period=args.volume_ma_period,
            volume_ratio=args.volume_ratio,
            stop_loss_pct=args.stop_loss,
            take_profit_trigger_pct=args.take_profit_trigger,
            trailing_stop_pct=args.trailing_stop,
        )
        
        print_summary(symbol, result)
        save_results(symbol, args.output_dir, result)
        
        all_results.append({
            "symbol": symbol,
            "period": args.period,
            "final_capital": result['final_capital'],
            "total_return_pct": result['total_return_pct'],
            "annualized_return_pct": result['annualized_return_pct'],
            "sharpe_ratio": result['sharpe_ratio'],
            "max_drawdown_pct": result['max_drawdown_pct'],
            "win_rate_pct": result['win_rate_pct'],
            "total_trades": result['total_trades'],
        })
    
    if all_results:
        summary_file = os.path.join(args.output_dir, f"summary_{args.period}.csv")
        pd.DataFrame(all_results).to_csv(summary_file, index=False, encoding='utf-8-sig')
        print(f"\n已保存汇总: {summary_file}")
        
        df_summary = pd.DataFrame(all_results)
        print(f"\n===== {args.period} 周期汇总 (V2优化版) =====")
        print(f"平均总收益: {df_summary['total_return_pct'].mean():.2f}%")
        print(f"平均年化收益: {df_summary['annualized_return_pct'].mean():.2f}%")
        print(f"平均胜率: {df_summary['win_rate_pct'].mean():.2f}%")
        print(f"平均最大回撤: {df_summary['max_drawdown_pct'].mean():.2f}%")
        print(f"盈利股票数: {(df_summary['total_return_pct'] > 0).sum()} / {len(df_summary)}")


if __name__ == "__main__":
    main()
