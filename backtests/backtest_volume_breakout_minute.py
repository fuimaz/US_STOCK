"""
成交量突破策略回测 - A股分钟数据
- 放量阳线开多
- 放量阴线开空
- 5%止损
- 10%以上回抽突破日线MA5止盈
"""
import argparse
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# 股票行业分类映射 (股票代码 -> (名称, 行业))
# 行业: 房地产、酒类、银行、家电、汽车、医药、电子、白酒、光伏、软件等
STOCK_INDUSTRY_MAPPING = {
    # 房地产 (需要排除)
    '000002.SZ': ('万科A', '房地产'),
    '000533.SZ': ('顺钠股份', '房地产'),
    '600048.SS': ('保利发展', '房地产'),
    
    # 酒类/白酒 (需要排除)
    '000568.SZ': ('泸州老窖', '白酒'),
    '000858.SZ': ('五粮液', '白酒'),
    '002304.SZ': ('洋河股份', '白酒'),
    '600519.SS': ('贵州茅台', '白酒'),
    
    # 银行
    '000001.SZ': ('平安银行', '银行'),
    
    # 家电
    '000333.SZ': ('美的集团', '家电'),
    '000651.SZ': ('格力电器', '家电'),
    '600690.SS': ('海尔智家', '家电'),
    
    # 汽车
    '000625.SZ': ('长安汽车', '汽车'),
    '002594.SZ': ('比亚迪', '汽车'),
    '600104.SS': ('上汽集团', '汽车'),
    
    # 医药
    '000661.SZ': ('长春高新', '医药'),
    '600276.SS': ('恒瑞医药', '医药'),
    '300760.SZ': ('迈瑞医疗', '医药'),
    
    # 电子
    '000725.SZ': ('京东方A', '电子'),
    '002475.SZ': ('立讯精密', '电子'),
    '002129.SZ': ('TCL中环', '电子'),
    
    # 光伏/新能源
    '002460.SZ': ('赣锋锂业', '锂电池'),
    '300274.SZ': ('阳光电源', '光伏'),
    '601012.SS': ('隆基绿能', '光伏'),
    '300750.SZ': ('宁德时代', '锂电池'),
    
    # 软件/科技
    '002230.SZ': ('科大讯飞', '软件'),
    '300033.SZ': ('同花顺', '软件'),
    '300124.SZ': ('汇川技术', '自动化'),
    
    # 农业/养殖
    '000876.SZ': ('新希望', '饲料'),
    '002714.SZ': ('牧原股份', '养殖'),
    
    # 电力设备
    '002028.SZ': ('思源电气', '电力设备'),
    
    # 半导体
    '002049.SZ': ('紫光国微', '半导体'),
    '688521.SS': ('芯原股份', '半导体'),
    
    # 安防
    '002415.SZ': ('海康威视', '安防'),
    
    # 化工
    '000525.SZ': ('红太阳', '化工'),
    '600346.SS': ('恒力石化', '化工'),
    
    # 通信
    '600050.SS': ('中国联通', '通信'),
    '600941.SS': ('中国移动', '通信'),
    
    # 金融
    '600036.SS': ('招商银行', '银行'),
    '601318.SS': ('中国平安', '保险'),
    '600030.SS': ('中信证券', '证券'),
    
    # 基建/工程
    '600019.SS': ('宝钢股份', '钢铁'),
    '601186.SS': ('中国铁建', '基建'),
    
    # 消费品
    '603288.SS': ('海天味业', '调味品'),
    '600887.SS': ('伊利股份', '乳制品'),
    
    # 公用事业
    '600009.SS': ('上海机场', '机场'),
    '600900.SS': ('长江电力', '电力'),
    '600886.SS': ('国投电力', '电力'),
    
    # 有色/资源
    '601899.SS': ('紫金矿业', '有色'),
    '601600.SS': ('中国铝业', '有色'),
    '601898.SS': ('中煤能源', '煤炭'),
    '601088.SS': ('中国神华', '煤炭'),
    
    # 石油化工
    '600028.SS': ('中国石化', '石油'),
    '601857.SS': ('中国石油', '石油'),
    
    # 航空
    '600029.SS': ('南方航空', '航空'),
    '600115.SS': ('东方航空', '航空'),
    '601111.SS': ('中国国航', '航空'),
    
    # 其他
    '001217.SZ': ('沃尔核材', '新材料'),
    '002272.SZ': ('川金股份', '化工'),
    '002837.SZ': ('英维克', '温控设备'),
    '300364.SZ': ('中文在线', '传媒'),
}

# 需要排除的行业
EXCLUDED_INDUSTRIES = ['房地产', '白酒', '酒类', '酿酒']


def get_stock_industry(symbol: str) -> Optional[Tuple[str, str]]:
    """获取股票的行业信息
    
    Args:
        symbol: 股票代码
        
    Returns:
        (名称, 行业) 元组，如果未知则返回None
    """
    return STOCK_INDUSTRY_MAPPING.get(symbol)


def is_stock_in_excluded_industry(symbol: str) -> bool:
    """检查股票是否属于需要排除的行业
    
    Args:
        symbol: 股票代码
        
    Returns:
        True表示需要排除，False表示保留
    """
    info = get_stock_industry(symbol)
    if info is None:
        # 如果未知行业，默认不排除（保守处理）
        return False
    name, industry = info
    return industry in EXCLUDED_INDUSTRIES


def filter_stocks_by_industry(symbols: List[str]) -> List[str]:
    """根据行业过滤股票列表，排除指定行业
    
    Args:
        symbols: 原始股票代码列表
        
    Returns:
        过滤后的股票代码列表
    """
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
            info = get_stock_industry(sym)
            if info:
                name, industry = info
                print(f"  - {sym} {name}: {industry}")
            else:
                print(f"  - {sym}: 未知行业")
    
    return filtered


@dataclass
class PositionState:
    """持仓状态"""
    shares: float = 0.0  # 正数为多头，负数为空头
    avg_cost: float = 0.0
    entry_price: float = 0.0
    peak_price: float = 0.0  # 持仓期间的最高/最低价
    peak_profit_pct: float = 0.0  # 持仓期间曾经达到的最高收益率
    entry_time: Optional[pd.Timestamp] = None
    is_long: bool = True  # True=多头, False=空头


def load_minute_data(symbol: str, period: str) -> Optional[pd.DataFrame]:
    """
    加载分钟级数据
    
    Args:
        symbol: 股票代码，如 000001.SZ.SZ
        period: 周期，如 15min, 30min, 60min
        
    Returns:
        DataFrame或None
    """
    # 处理文件名格式 - 文件名可能是 000001.SZ.SZ_15min.csv
    # 首先尝试直接拼接
    filename = f"{symbol}_{period}.csv"
    filepath = os.path.join("data_cache", "a_stock_minute", filename)
    
    if not os.path.exists(filepath):
        # 尝试处理双后缀问题 (如 000001.SZ.SZ -> 000001.SZ.SZ_15min.csv)
        # 直接查找匹配的文件
        cache_dir = os.path.join("data_cache", "a_stock_minute")
        for f in os.listdir(cache_dir):
            if f.endswith(f"_{period}.csv"):
                # 提取股票代码部分
                file_symbol = f[:-len(f"_{period}.csv")]
                if file_symbol == symbol:
                    filepath = os.path.join(cache_dir, f)
                    break
        else:
            return None
    
    try:
        df = pd.read_csv(filepath)
        # 处理datetime列
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
        elif 'day' in df.columns:
            df['day'] = pd.to_datetime(df['day'])
            df.set_index('day', inplace=True)
        
        # 统一列名
        rename_map = {
            'open': 'Open', 'high': 'High', 'low': 'Low', 
            'close': 'Close', 'volume': 'Volume'
        }
        for old, new in rename_map.items():
            if old in df.columns:
                df.rename(columns={old: new}, inplace=True)
        
        # 确保有必要的列
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            return None
        
        out = df[required_cols].copy()
        for col in required_cols:
            out[col] = pd.to_numeric(out[col], errors='coerce')
        out = out.dropna(subset=['Open', 'High', 'Low', 'Close'])
        out = out[out['Close'] > 0]
        out = out[~out.index.duplicated(keep='last')].sort_index()
        return out
    except Exception as e:
        print(f"加载数据失败 {filepath}: {e}")
        return None


def infer_bars_per_year(index: pd.Index) -> float:
    """根据时间索引估算每年 bar 数（用于夏普年化）。"""
    if len(index) < 2:
        return 252 * 4

    dt_index = pd.DatetimeIndex(index).sort_values()
    deltas = pd.Series(dt_index[1:] - dt_index[:-1]).dt.total_seconds().dropna()
    deltas = deltas[deltas > 0]
    if deltas.empty:
        return 252 * 4

    median_minutes = deltas.median() / 60.0
    if median_minutes <= 0:
        return 252 * 4

    bars_per_day = max(1.0, 240.0 / median_minutes)
    return 252.0 * bars_per_day


def get_daily_ma5(df_minute: pd.DataFrame) -> pd.Series:
    """
    从分钟数据计算日线MA5
    
    Args:
        df_minute: 分钟级数据
        
    Returns:
        日线MA5序列
    """
    # 将分钟数据聚合为日线
    daily = df_minute.resample('D').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    # 计算日线MA5
    daily['MA5'] = daily['Close'].rolling(window=5).mean()
    
    return daily['MA5']


def get_symbols_for_period(period: str, filter_industry: bool = True) -> List[str]:
    """
    获取指定周期的所有股票代码
    
    Args:
        period: 周期，如 15min, 30min, 60min
        filter_industry: 是否按行业过滤股票
        
    Returns:
        股票代码列表
    """
    cache_dir = os.path.join("data_cache", "a_stock_minute")
    if not os.path.exists(cache_dir):
        return []
    
    suffix = f"_{period}.csv"
    symbols = set()
    
    for filename in os.listdir(cache_dir):
        if filename.endswith(suffix):
            # 提取股票代码 (去掉 _15min.csv 等后缀)
            symbol = filename[:-len(suffix)]
            symbols.add(symbol)
    
    all_symbols = sorted(list(symbols))
    
    # 如果启用行业过滤
    if filter_industry:
        return filter_stocks_by_industry(all_symbols)
    
    return all_symbols


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 100000.0,
    commission: float = 0.001,
    slippage: float = 0.0005,
    volume_ma_period: int = 20,
    volume_ratio: float = 2.0,
    stop_loss_pct: float = 0.05,
    take_profit_trigger_pct: float = 0.10,
    tp_trail_retrace: float = 0.07,
) -> Dict:
    """
    运行回测
    
    Args:
        df: 分钟级OHLCV数据
        initial_capital: 初始资金
        commission: 手续费率
        slippage: 滑点
        volume_ma_period: 成交量均线周期
        volume_ratio: 成交量放大倍数
        stop_loss_pct: 止损百分比
        take_profit_trigger_pct: 止盈触发涨幅
        
    Returns:
        回测结果字典
    """
    data = df.copy()
    
    # 计算基础指标
    data['change'] = data['Close'].pct_change()  # 涨跌幅
    data['is_bullish'] = data['Close'] > data['Open']  # 是否阳线
    data['is_bearish'] = data['Close'] < data['Open']  # 是否阴线
    
    # 成交量均线
    data['volume_ma'] = data['Volume'].rolling(window=volume_ma_period).mean()
    
    # 日内MA5 (用于分钟级别的参考)
    data['ma5_minute'] = data['Close'].rolling(window=5).mean()
    
    # 判断放量: 成交量 > 均线 * 倍数
    data['volume_spike'] = data['Volume'] > data['volume_ma'] * volume_ratio
    
    # 获取日线MA5用于止盈判断
    daily_ma5 = get_daily_ma5(df)
    
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
    
    # 放量阴线 -> 做空
    data.loc[
        (data['is_bearish']) & 
        (data['volume_spike']) & 
        (data['volume_ma'].notna()),
        'sell_signal'
    ] = True
    
    # 开始回测 - 只做多
    cash = initial_capital
    pos = PositionState()
    trades = []
    equity_curve = []

    def execute_sell(sell_shares: int, sell_price: float, sell_reason: str, trade_date) -> None:
        """执行卖出。"""
        nonlocal cash, pos, trades
        if pos.shares <= 0:
            return

        shares_to_sell = min(int(pos.shares), int(sell_shares))
        if shares_to_sell <= 0:
            return

        proceeds = shares_to_sell * sell_price * (1 - slippage) * (1 - commission)
        cash += proceeds
        profit_pct = (sell_price / pos.avg_cost - 1.0)

        trades.append({
            "date": trade_date,
            "type": "sell",
            "price": sell_price,
            "shares": shares_to_sell,
            "value": proceeds,
            "reason": sell_reason,
            "profit_pct": profit_pct * 100,
        })

        pos.shares -= shares_to_sell
        if pos.shares <= 0:
            pos = PositionState()
    
    for i in range(len(data)):
        row = data.iloc[i]
        date = data.index[i]
        open_price = float(row['Open'])
        close_price = float(row['Close'])
        high_price = float(row['High'])
        low_price = float(row['Low'])
        
        equity = cash + pos.shares * close_price if pos.shares != 0 else cash
        
        # ========== 处理卖出 ==========
        if pos.shares > 0:
            current_profit_pct = (close_price / pos.avg_cost - 1.0)
            
            # 更新峰值 (价格和收益率)
            pos.peak_price = max(pos.peak_price, high_price)
            pos.peak_profit_pct = max(pos.peak_profit_pct, high_price / pos.avg_cost - 1.0)
            
            sell_reason = None
            should_sell = False
            
            # 1. 止损检查（按当根最低价触发）
            stop_price = pos.avg_cost * (1 - stop_loss_pct)
            
            # 跳空低开保护：如果开盘价直接低于止损价，以开盘价卖出
            if open_price <= stop_price:
                should_sell = True
                sell_reason = "stop_loss_gap"
            elif low_price <= stop_price:
                should_sell = True
                sell_reason = "stop_loss"
            
            # 2. 止盈检查（单次全平）
            if not should_sell and pos.shares > 0 and pos.peak_profit_pct >= take_profit_trigger_pct:
                take_profit_by_ma5 = False
                date_ts = pd.Timestamp(date.date()) if hasattr(date, 'date') else pd.Timestamp(date)
                if date_ts in daily_ma5.index:
                    daily_ma5_val = daily_ma5.loc[date_ts]
                    if pd.notna(daily_ma5_val):
                        take_profit_by_ma5 = close_price < daily_ma5_val and pos.peak_price > daily_ma5_val

                retrace_pct = pos.peak_profit_pct - current_profit_pct
                if retrace_pct >= tp_trail_retrace:
                    should_sell = True
                    sell_reason = "take_profit_trail"
                elif take_profit_by_ma5:
                    should_sell = True
                    sell_reason = "take_profit_ma5"
            
            # 确定卖出价格
            if sell_reason == "stop_loss_gap":
                sell_price = open_price  # 跳空低开，以开盘价卖出
            elif sell_reason == "stop_loss":
                sell_price = stop_price  # 最低价触发止损，按止损价执行
            else:
                sell_price = close_price  # 非止损卖出，仍按收盘价
            
            # 执行卖出
            if should_sell:
                execute_sell(int(pos.shares), sell_price, sell_reason, date)
        
        # ========== 处理买入 - 只做多 ==========
        buy_signal = bool(row.get('buy_signal', False))
        
        if pos.shares == 0 and buy_signal:
            # 做多
            max_shares = int(cash / (close_price * (1 + slippage) * (1 + commission)))
            if max_shares > 0:
                cost = max_shares * close_price * (1 + slippage) * (1 + commission)
                pos.shares = max_shares
                pos.avg_cost = close_price * (1 + slippage)
                pos.entry_price = close_price
                pos.peak_price = close_price
                pos.peak_profit_pct = 0.0  # 初始化曾经达到的最高收益率
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
        
        if pos.is_long:
            proceeds = pos.shares * final_price * (1 - slippage) * (1 - commission)
        else:
            proceeds = abs(pos.shares) * final_price * (1 - slippage) * (1 - commission)
        
        trade = {
            "date": data.index[-1],
            "type": "close",
            "price": final_price,
            "shares": abs(pos.shares),
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
        span_days = (eq_df.index[-1] - eq_df.index[0]).total_seconds() / (24 * 3600)
        years = max(span_days / 365.25, 1/252)  # 至少按一天计算
        annualized = (cash / initial_capital) ** (1 / years) - 1 if years > 0 else 0
        bars_per_year = infer_bars_per_year(eq_df.index)
        sharpe = (returns.mean() / returns.std() * np.sqrt(bars_per_year)) if returns.std() > 0 else 0
        running_peak = eq_df["equity"].cummax()
        drawdown = ((running_peak - eq_df["equity"]) / running_peak).max() if len(running_peak) > 0 else 0
    else:
        total_return = 0
        annualized = 0
        sharpe = 0
        drawdown = 0
    
    # 计算胜率 - 根据交易记录中的reason字段判断
    trade_df = pd.DataFrame(trades)
    win_count = 0
    total_round_trips = 0
    
    if not trade_df.empty:
        # 找出所有平仓交易(sell, close)
        close_trades = trade_df[trade_df["type"].isin(["sell", "close"])]
        
        # 每笔平仓交易的profit_pct都是盈利的
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
    
    # 保存信号
    signal_file = os.path.join(output_dir, f"{symbol}_signals.csv")
    result['signals'].to_csv(signal_file, encoding='utf-8-sig')
    
    # 保存交易记录
    trades_file = os.path.join(output_dir, f"{symbol}_trades.csv")
    result['trades'].to_csv(trades_file, index=False, encoding='utf-8-sig')
    
    # 保存权益曲线
    equity_file = os.path.join(output_dir, f"{symbol}_equity.csv")
    result['equity_curve'].to_csv(equity_file, encoding='utf-8-sig')
    
    # 保存摘要
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
    parser = argparse.ArgumentParser(description="成交量突破策略回测 - A股分钟数据")
    parser.add_argument("--symbol", default="", help="单只股票代码，如 000001.SZ.SZ")
    parser.add_argument("--period", choices=["15min", "30min", "60min"], default="15min", help="时间周期")
    parser.add_argument("--output-dir", default="results/volume_breakout_minute", help="输出目录")
    parser.add_argument("--initial-capital", type=float, default=100000.0, help="初始资金")
    parser.add_argument("--commission", type=float, default=0.001, help="手续费率")
    parser.add_argument("--slippage", type=float, default=0.0005, help="滑点")
    parser.add_argument("--volume-ma-period", type=int, default=20, help="成交量均线周期")
    parser.add_argument("--volume-ratio", type=float, default=2.0, help="成交量放大倍数")
    parser.add_argument("--stop-loss", type=float, default=0.05, help="止损百分比")
    parser.add_argument("--take-profit-trigger", type=float, default=0.10, help="止盈触发涨幅")
    parser.add_argument("--tp-trail-retrace", type=float, default=0.07, help="峰值回撤止盈阈值")
    parser.add_argument("--universe", choices=["single", "all"], default="single", help="回测范围")
    parser.add_argument("--no-industry-filter", action="store_true", help="禁用行业过滤（不过滤房地产和酒类股票）")
    args = parser.parse_args()
    
    # 获取股票列表
    if args.universe == "all":
        # 根据参数决定是否启用行业过滤
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
    
    for symbol in symbols:
        print(f"\n处理 {symbol}...")
        
        # 加载数据
        data = load_minute_data(symbol, args.period)
        if data is None or len(data) < 100:
            print(f"  跳过: 数据不足")
            continue
        
        print(f"  数据量: {len(data)} 条")
        
        # 运行回测
        result = run_backtest(
            df=data,
            initial_capital=args.initial_capital,
            commission=args.commission,
            slippage=args.slippage,
            volume_ma_period=args.volume_ma_period,
            volume_ratio=args.volume_ratio,
            stop_loss_pct=args.stop_loss,
            take_profit_trigger_pct=args.take_profit_trigger,
            tp_trail_retrace=args.tp_trail_retrace,
        )
        
        # 打印结果
        print_summary(symbol, result)
        
        # 保存结果
        save_results(symbol, args.output_dir, result)
        
        # 记录汇总
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
    
    # 保存汇总结果
    if all_results:
        summary_file = os.path.join(args.output_dir, f"summary_{args.period}.csv")
        pd.DataFrame(all_results).to_csv(summary_file, index=False, encoding='utf-8-sig')
        print(f"\n已保存汇总: {summary_file}")
        
        # 打印平均收益
        df_summary = pd.DataFrame(all_results)
        print(f"\n===== {args.period} 周期汇总 =====")
        print(f"平均总收益: {df_summary['total_return_pct'].mean():.2f}%")
        print(f"平均年化收益: {df_summary['annualized_return_pct'].mean():.2f}%")
        print(f"平均胜率: {df_summary['win_rate_pct'].mean():.2f}%")
        print(f"平均最大回撤: {df_summary['max_drawdown_pct'].mean():.2f}%")
        print(f"盈利股票数: {(df_summary['total_return_pct'] > 0).sum()} / {len(df_summary)}")


if __name__ == "__main__":
    main()
