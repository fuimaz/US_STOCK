"""
Equity Millipede 策略回测 - A股分钟数据

基于 Forex Factory - Building an equity millipede 策略改编

策略特点:
- 顺势交易: 顺着主要趋势方向开仓
- 入场时机: 放量阳线做多, 放量阴线做空
- 止损: 5%止损
- 止盈: 10%以上回抽止盈
"""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# 导入行业过滤功能 (从 volume_breakout_minute 复用)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 这里直接复制行业过滤相关代码，避免循环导入


# 股票行业分类映射
STOCK_INDUSTRY_MAPPING = {
    '000002.SZ': ('万科A', '房地产'),
    '000533.SZ': ('顺钠股份', '房地产'),
    '600048.SS': ('保利发展', '房地产'),
    '000568.SZ': ('泸州老窖', '白酒'),
    '000858.SZ': ('五粮液', '白酒'),
    '002304.SZ': ('洋河股份', '白酒'),
    '600519.SS': ('贵州茅台', '白酒'),
    '000001.SZ': ('平安银行', '银行'),
    '000333.SZ': ('美的集团', '家电'),
    '000651.SZ': ('格力电器', '家电'),
    '600690.SS': ('海尔智家', '家电'),
    '000625.SZ': ('长安汽车', '汽车'),
    '002594.SZ': ('比亚迪', '汽车'),
    '600104.SS': ('上汽集团', '汽车'),
    '000661.SZ': ('长春高新', '医药'),
    '600276.SS': ('恒瑞医药', '医药'),
    '300760.SZ': ('迈瑞医疗', '医药'),
    '000725.SZ': ('京东方A', '电子'),
    '002475.SZ': ('立讯精密', '电子'),
    '002129.SZ': ('TCL中环', '电子'),
    '002460.SZ': ('赣锋锂业', '锂电池'),
    '300274.SZ': ('阳光电源', '光伏'),
    '601012.SS': ('隆基绿能', '光伏'),
    '300750.SZ': ('宁德时代', '锂电池'),
    '002230.SZ': ('科大讯飞', '软件'),
    '300033.SZ': ('同花顺', '软件'),
    '300124.SZ': ('汇川技术', '自动化'),
    '000876.SZ': ('新希望', '饲料'),
    '002714.SZ': ('牧原股份', '养殖'),
    '002028.SZ': ('思源电气', '电力设备'),
    '002049.SZ': ('紫光国微', '半导体'),
    '688521.SS': ('芯原股份', '半导体'),
    '002415.SZ': ('海康威视', '安防'),
    '000525.SZ': ('红太阳', '化工'),
    '600346.SS': ('恒力石化', '化工'),
    '600050.SS': ('中国联通', '通信'),
    '600941.SS': ('中国移动', '通信'),
    '600036.SS': ('招商银行', '银行'),
    '601318.SS': ('中国平安', '保险'),
    '600030.SS': ('中信证券', '证券'),
    '600019.SS': ('宝钢股份', '钢铁'),
    '601186.SS': ('中国铁建', '基建'),
    '603288.SS': ('海天味业', '调味品'),
    '600887.SS': ('伊利股份', '乳制品'),
    '600009.SS': ('上海机场', '机场'),
    '600900.SS': ('长江电力', '电力'),
    '600886.SS': ('国投电力', '电力'),
    '601899.SS': ('紫金矿业', '有色'),
    '601600.SS': ('中国铝业', '有色'),
    '601898.SS': ('中煤能源', '煤炭'),
    '601088.SS': ('中国神华', '煤炭'),
    '600028.SS': ('中国石化', '石油'),
    '601857.SS': ('中国石油', '石油'),
    '600029.SS': ('南方航空', '航空'),
    '600115.SS': ('东方航空', '航空'),
    '601111.SS': ('中国国航', '航空'),
    '001217.SZ': ('沃尔核材', '新材料'),
    '002272.SZ': ('川金股份', '化工'),
    '002837.SZ': ('英维克', '温控设备'),
    '300364.SZ': ('中文在线', '传媒'),
}

# 需要排除的行业
EXCLUDED_INDUSTRIES = ['房地产', '白酒', '酒类', '酿酒']


def is_stock_in_excluded_industry(symbol: str) -> bool:
    """检查股票是否属于需要排除的行业"""
    info = STOCK_INDUSTRY_MAPPING.get(symbol)
    if info is None:
        return False
    name, industry = info
    return industry in EXCLUDED_INDUSTRIES


def filter_stocks_by_industry(symbols: List[str]) -> List[str]:
    """根据行业过滤股票列表"""
    filtered = []
    excluded = []
    
    for symbol in symbols:
        if is_stock_in_excluded_industry(symbol):
            excluded.append(symbol)
        else:
            filtered.append(symbol)
    
    if excluded:
        print(f"\n[行业过滤] 排除 {len(excluded)} 只股票:")
        for sym in excluded:
            info = STOCK_INDUSTRY_MAPPING.get(sym)
            if info:
                name, industry = info
                print(f"  - {sym} {name}: {industry}")
    
    return filtered


@dataclass
class PositionState:
    """持仓状态"""
    shares: float = 0.0
    avg_cost: float = 0.0
    entry_price: float = 0.0
    peak_price: float = 0.0
    peak_profit_pct: float = 0.0
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
        
        rename_map = {
            'open': 'Open', 'high': 'High', 'low': 'Low', 
            'close': 'Close', 'volume': 'Volume'
        }
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


def get_daily_ma5(df_minute: pd.DataFrame) -> pd.Series:
    """从分钟数据计算日线MA5"""
    daily = df_minute.resample('D').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    daily['MA5'] = daily['Close'].rolling(window=5).mean()
    return daily['MA5']


def build_market_gap_down_flags(market_df: pd.DataFrame, gap_down_threshold: float = 0.02) -> pd.Series:
    """Build per-day market gap-down flags: open vs previous close."""
    if market_df is None or market_df.empty:
        return pd.Series(dtype=bool)

    daily = market_df.resample('D').agg({
        'Open': 'first',
        'Close': 'last',
    }).dropna()

    if len(daily) < 2:
        return pd.Series(dtype=bool)

    threshold = abs(float(gap_down_threshold))
    gap_pct = daily['Open'] / daily['Close'].shift(1) - 1.0
    flags = (gap_pct <= -threshold).fillna(False).astype(bool)
    flags.index = pd.to_datetime(flags.index).normalize()
    flags.name = "market_gap_down_block"
    return flags


def get_symbols_for_period(period: str, filter_industry: bool = True) -> List[str]:
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
    
    all_symbols = sorted(list(symbols))
    
    if filter_industry:
        return filter_stocks_by_industry(all_symbols)
    
    return all_symbols


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 100000.0,
    commission: float = 0.001,
    slippage: float = 0.0005,
    volume_ma_period: int = 20,
    volume_ratio: float = 1.5,
    trend_ma_period: int = 20,
    stop_loss_pct: float = 0.05,
    take_profit_trigger_pct: float = 0.10,
    long_only: bool = True,
    market_gap_down_flags: Optional[pd.Series] = None,
) -> Dict:
    """
    运行回测 - Equity Millipede 策略
    
    策略逻辑:
    - 买入: 上涨趋势 + 放量阳线
    - 卖出: 止损 / 止盈 / 趋势反转
    """
    data = df.copy()
    
    # 基础指标
    data['change'] = data['Close'].pct_change()
    data['is_bullish'] = data['Close'] > data['Open']
    data['is_bearish'] = data['Close'] < data['Open']
    
    # 趋势指标 - EMA
    data['ema_fast'] = data['Close'].ewm(span=5, adjust=False).mean()
    data['ema_slow'] = data['Close'].ewm(span=trend_ma_period, adjust=False).mean()
    
    # 趋势方向
    data['trend'] = 0
    data.loc[data['ema_fast'] > data['ema_slow'], 'trend'] = 1
    data.loc[data['ema_fast'] < data['ema_slow'], 'trend'] = -1
    
    # 成交量指标
    data['volume_ma'] = data['Volume'].rolling(window=volume_ma_period).mean()
    data['volume_spike'] = data['Volume'] > data['volume_ma'] * volume_ratio
    
    # 日线MA5
    daily_ma5 = get_daily_ma5(df)
    
    # 生成交易信号
    # 买入: 上涨趋势 + 放量阳线
    data['buy_signal'] = (
        (data['trend'] == 1) & 
        (data['volume_spike']) & 
        (data['is_bullish']) &
        (data['volume_ma'].notna())
    )
    
    # 卖出: 下跌趋势 + 放量阴线
    data['sell_signal'] = (
        (data['trend'] == -1) & 
        (data['volume_spike']) & 
        (data['is_bearish']) &
        (data['volume_ma'].notna())
    )

    # 大盘跳空低开过滤（按交易日应用到当日全部分钟K）
    if market_gap_down_flags is not None and len(market_gap_down_flags) > 0:
        flag_series = market_gap_down_flags.copy()
        flag_series.index = pd.to_datetime(flag_series.index).normalize()
        data['market_gap_down_block'] = (
            data.index.to_series().dt.normalize().map(flag_series).fillna(False).astype(bool).values
        )
    else:
        data['market_gap_down_block'] = False
    
    # 回测
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
        
        # 处理卖出
        if pos.shares > 0:
            current_profit_pct = (close_price / pos.avg_cost - 1.0)
            pos.peak_price = max(pos.peak_price, close_price)
            pos.peak_profit_pct = max(pos.peak_profit_pct, current_profit_pct)
            
            should_sell = False
            sell_reason = None
            
            # 1. 止损
            stop_price = pos.avg_cost * (1 - stop_loss_pct)
            if close_price <= stop_price or low_price <= stop_price:
                should_sell = True
                sell_reason = "stop_loss"
            
            # 2. 止盈 - 涨幅>10%后回抽MA5
            if not should_sell and pos.peak_profit_pct >= take_profit_trigger_pct:
                date_ts = pd.Timestamp(date.date()) if hasattr(date, 'date') else pd.Timestamp(date)
                if date_ts in daily_ma5.index:
                    daily_ma5_val = daily_ma5.loc[date_ts]
                    if pd.notna(daily_ma5_val):
                        if close_price < daily_ma5_val and pos.peak_price > daily_ma5_val:
                            should_sell = True
                            sell_reason = "take_profit_ma5"
            
            # 3. 趋势反转 (多头转空头)
            if not long_only and not should_sell:
                if row['trend'] == -1 and row['is_bearish']:
                    should_sell = True
                    sell_reason = "trend_reversal"
            
            if should_sell:
                proceeds = pos.shares * close_price * (1 - slippage) * (1 - commission)
                cash = cash + proceeds
                
                trades.append({
                    "date": date,
                    "type": "sell",
                    "price": close_price,
                    "shares": pos.shares,
                    "value": proceeds,
                    "reason": sell_reason,
                    "profit_pct": current_profit_pct * 100,
                })
                
                pos = PositionState()
        
        # 处理买入 - 只做多
        if long_only:
            buy_signal = bool(row.get('buy_signal', False))
        else:
            buy_signal = bool(row.get('buy_signal', False))
            sell_signal = bool(row.get('sell_signal', False))
        
        market_gap_down_block = bool(row.get('market_gap_down_block', False))

        if pos.shares == 0 and buy_signal and not market_gap_down_block:
            max_shares = int(cash / (close_price * (1 + slippage) * (1 + commission)))
            if max_shares > 0:
                cost = max_shares * close_price * (1 + slippage) * (1 + commission)
                pos.shares = max_shares
                pos.avg_cost = close_price * (1 + slippage)
                pos.entry_price = close_price
                pos.peak_price = close_price
                pos.peak_profit_pct = 0.0
                pos.entry_time = date
                pos.is_long = True
                cash -= cost
                
                trades.append({
                    "date": date,
                    "type": "buy",
                    "price": close_price,
                    "shares": max_shares,
                    "value": cost,
                    "reason": "long_entry",
                })
        
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
        final_profit_pct = (final_price / pos.avg_cost - 1.0)
        
        proceeds = pos.shares * final_price * (1 - slippage) * (1 - commission)
        
        trades.append({
            "date": data.index[-1],
            "type": "close",
            "price": final_price,
            "shares": abs(pos.shares),
            "value": proceeds,
            "reason": "final_close",
            "profit_pct": final_profit_pct * 100,
        })
        
        cash = cash + proceeds
        equity_curve[-1]["equity"] = cash
        equity_curve[-1]["cash"] = cash
    
    # 统计
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
    
    # 胜率
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
    parser = argparse.ArgumentParser(description="Equity Millipede 策略回测 - A股分钟数据")
    parser.add_argument("--symbol", default="", help="单只股票代码，如 000001.SZ.SZ")
    parser.add_argument("--period", choices=["15min", "30min", "60min"], default="15min", help="时间周期")
    parser.add_argument("--output-dir", default="results/millipede_minute", help="输出目录")
    parser.add_argument("--initial-capital", type=float, default=100000.0, help="初始资金")
    parser.add_argument("--commission", type=float, default=0.001, help="手续费率")
    parser.add_argument("--slippage", type=float, default=0.0005, help="滑点")
    parser.add_argument("--volume-ma-period", type=int, default=20, help="成交量均线周期")
    parser.add_argument("--volume-ratio", type=float, default=1.5, help="成交量放大倍数")
    parser.add_argument("--trend-ma-period", type=int, default=20, help="趋势均线周期")
    parser.add_argument("--stop-loss", type=float, default=0.05, help="止损百分比")
    parser.add_argument("--take-profit-trigger", type=float, default=0.10, help="止盈触发涨幅")
    parser.add_argument("--universe", choices=["single", "all"], default="single", help="回测范围")
    parser.add_argument("--no-industry-filter", action="store_true", help="禁用行业过滤")
    parser.add_argument("--market-symbol", default="000001.SS", help="大盘代理代码（用于跳空过滤）")
    parser.add_argument("--market-gap-down-threshold", type=float, default=0.02, help="大盘跳空低开阈值，如0.02=2%%")
    parser.add_argument("--no-market-gap-filter", action="store_true", help="禁用大盘跳空低开过滤")
    args = parser.parse_args()
    
    # 获取股票列表
    if args.universe == "all":
        filter_industry = not args.no_industry_filter
        symbols = get_symbols_for_period(args.period, filter_industry=filter_industry)
        
        if filter_industry:
            print(f"找到 {len(symbols)} 只股票（已过滤房地产和酒类行业）")
        else:
            print(f"找到 {len(symbols)} 只股票（未过滤行业）")
    else:
        if not args.symbol:
            print("请指定股票代码 --symbol")
            return
        symbols = [args.symbol]
    
    all_results = []

    market_gap_down_flags = None
    if args.no_market_gap_filter:
        print("[大盘过滤] 已禁用")
    else:
        market_df = load_minute_data(args.market_symbol, args.period)
        if market_df is None or len(market_df) < 2:
            print(f"[大盘过滤] 未找到 {args.market_symbol} 的 {args.period} 数据，跳过该过滤器")
        else:
            market_gap_down_flags = build_market_gap_down_flags(
                market_df=market_df,
                gap_down_threshold=args.market_gap_down_threshold,
            )
            blocked_days = int(market_gap_down_flags.sum()) if len(market_gap_down_flags) > 0 else 0
            print(
                f"[大盘过滤] 使用 {args.market_symbol}，阈值 {args.market_gap_down_threshold * 100:.2f}% ，"
                f"触发 {blocked_days} 个交易日暂停开仓"
            )
    
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
            trend_ma_period=args.trend_ma_period,
            stop_loss_pct=args.stop_loss,
            take_profit_trigger_pct=args.take_profit_trigger,
            long_only=True,
            market_gap_down_flags=market_gap_down_flags,
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
    
    # 保存汇总
    if all_results:
        summary_file = os.path.join(args.output_dir, f"summary_{args.period}.csv")
        pd.DataFrame(all_results).to_csv(summary_file, index=False, encoding='utf-8-sig')
        print(f"\n已保存汇总: {summary_file}")
        
        df_summary = pd.DataFrame(all_results)
        print(f"\n===== {args.period} 周期汇总 (Equity Millipede 策略) =====")
        print(f"平均总收益: {df_summary['total_return_pct'].mean():.2f}%")
        print(f"平均年化收益: {df_summary['annualized_return_pct'].mean():.2f}%")
        print(f"平均胜率: {df_summary['win_rate_pct'].mean():.2f}%")
        print(f"平均最大回撤: {df_summary['max_drawdown_pct'].mean():.2f}%")
        print(f"盈利股票数: {(df_summary['total_return_pct'] > 0).sum()} / {len(df_summary)}")


if __name__ == "__main__":
    main()
