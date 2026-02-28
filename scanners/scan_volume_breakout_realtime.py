"""
A-share realtime scanner for minute volume-breakout strategy.

Features:
1. Scan every N minutes during CN trading sessions.
2. Use minute bars from AkShare + realtime spot price.
3. Detect buy points and sell points (for existing paper positions).
4. Persist signal history and paper positions.

Usage examples:
    python scanners/scan_volume_breakout_realtime.py --once --period 15
    python scanners/scan_volume_breakout_realtime.py --daemon --scan-interval-minutes 20
    python scanners/scan_volume_breakout_realtime.py --stock-pool-file scanners/stock_pool.csv
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, time as dtime
from typing import Dict, List, Optional, Tuple

import akshare as ak
import pandas as pd
from zoneinfo import ZoneInfo


CN_TZ = ZoneInfo("Asia/Shanghai")
TRADING_SESSIONS = (
    (dtime(9, 30), dtime(11, 30)),
    (dtime(13, 0), dtime(15, 0)),
)


def now_cn() -> datetime:
    return datetime.now(CN_TZ)


def is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5


def is_trading_time(dt: datetime) -> bool:
    if not is_weekday(dt):
        return False
    t = dt.timetz().replace(tzinfo=None)
    for start, end in TRADING_SESSIONS:
        if start <= t < end:
            return True
    return False


def normalize_symbol(symbol: str) -> Optional[str]:
    """Normalize to 000001.SZ / 600519.SS."""
    if not symbol:
        return None
    s = symbol.strip().upper()

    m = re.match(r"^(\d{6})\.(SZ|SS)(?:\.(?:SZ|SS))?$", s)
    if m:
        return f"{m.group(1)}.{m.group(2)}"

    m = re.match(r"^(SH|SZ)(\d{6})$", s)
    if m:
        code = m.group(2)
        ex = "SS" if m.group(1) == "SH" else "SZ"
        return f"{code}.{ex}"

    m = re.match(r"^(\d{6})$", s)
    if m:
        code = m.group(1)
        ex = "SS" if code.startswith(("5", "6", "9")) else "SZ"
        return f"{code}.{ex}"

    return None


def symbol_to_code(symbol: str) -> str:
    return symbol.split(".")[0]


def next_weekday_0930(dt: datetime) -> datetime:
    nxt = dt
    while True:
        nxt = (nxt + timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0)
        if is_weekday(nxt):
            return nxt


def next_market_open(dt: datetime) -> datetime:
    """Return next CN market open time."""
    base = dt.replace(second=0, microsecond=0)
    if not is_weekday(base):
        return next_weekday_0930(base)

    t = base.timetz().replace(tzinfo=None)
    morning_open = base.replace(hour=9, minute=30)
    noon_open = base.replace(hour=13, minute=0)
    if t < dtime(9, 30):
        return morning_open
    if dtime(11, 30) <= t < dtime(13, 0):
        return noon_open
    if t >= dtime(15, 0):
        return next_weekday_0930(base)
    # already in trading session
    return base


def sleep_until(target_dt: datetime) -> None:
    while True:
        now = now_cn()
        seconds = int((target_dt - now).total_seconds())
        if seconds <= 0:
            return
        time.sleep(min(seconds, 60))


def normalize_minute_df(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "时间": "datetime",
        "日期": "datetime",
        "day": "datetime",
        "开盘": "Open",
        "最高": "High",
        "最低": "Low",
        "收盘": "Close",
        "成交量": "Volume",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    out = df.copy()
    out.rename(columns=rename_map, inplace=True)
    req = ["datetime", "Open", "High", "Low", "Close", "Volume"]
    if not all(c in out.columns for c in req):
        missing = [c for c in req if c not in out.columns]
        raise ValueError(f"missing columns: {missing}")

    out = out[req].copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    out = out.dropna(subset=["datetime"])
    out = out.drop_duplicates(subset=["datetime"], keep="last")
    out = out.sort_values("datetime").set_index("datetime")
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    out = out[out["Close"] > 0]
    return out


def drop_incomplete_last_bar(df: pd.DataFrame, period_min: int, ref_dt: datetime) -> pd.DataFrame:
    if df.empty or len(df) < 2:
        return df
    last_ts = pd.Timestamp(df.index[-1]).to_pydatetime().replace(tzinfo=CN_TZ)
    lag = (ref_dt - last_ts).total_seconds() / 60.0
    if 0 <= lag < period_min:
        return df.iloc[:-1].copy()
    return df


def trading_days_between(start_date: datetime, end_date: datetime) -> int:
    if end_date.date() <= start_date.date():
        return 0
    days = 0
    d = start_date.date()
    while d < end_date.date():
        d = d + timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def get_daily_ma5_rt(minute_df: pd.DataFrame, realtime_price: float) -> Optional[float]:
    daily_close = minute_df["Close"].resample("D").last().dropna()
    if len(daily_close) < 4:
        return None
    last4_sum = float(daily_close.iloc[-4:].sum())
    return (last4_sum + float(realtime_price)) / 5.0


def discover_symbols_from_cache(period_min: int) -> List[str]:
    minute_dir = os.path.join("data_cache", "a_stock_minute")
    if not os.path.exists(minute_dir):
        return []
    suffix = f"_{period_min}min.csv"
    symbols = set()
    for fn in os.listdir(minute_dir):
        if not fn.endswith(suffix):
            continue
        raw = fn[: -len(suffix)]
        sym = normalize_symbol(raw)
        if sym:
            symbols.add(sym)
    return sorted(symbols)


def load_symbols_from_pool_file(pool_file: str) -> List[str]:
    """
    Load symbols from CSV stock pool file.

    Supported columns:
    - symbol (required): e.g. 000001.SZ
    - enabled (optional): 1/0, true/false, yes/no
    - name (optional): ignored by scanner logic, only for human edit
    """
    if not os.path.exists(pool_file):
        return []

    try:
        df = pd.read_csv(pool_file, dtype=str).fillna("")
    except Exception as exc:
        print(f"Failed to read stock pool file: {pool_file}, error: {exc}")
        return []

    if "symbol" not in df.columns:
        print(f"Stock pool file missing required column 'symbol': {pool_file}")
        return []

    enabled_col = "enabled" if "enabled" in df.columns else None
    disable_values = {"0", "false", "no", "n", "off"}

    symbols: List[str] = []
    invalid_rows = 0
    for _, row in df.iterrows():
        raw_symbol = str(row.get("symbol", "")).strip()
        if not raw_symbol:
            continue

        if enabled_col:
            enabled_raw = str(row.get(enabled_col, "1")).strip().lower()
            if enabled_raw in disable_values:
                continue

        sym = normalize_symbol(raw_symbol)
        if not sym:
            invalid_rows += 1
            continue
        symbols.append(sym)

    deduped = sorted(list(dict.fromkeys(symbols)))
    print(
        f"Loaded stock pool: {pool_file} | total_rows={len(df)} "
        f"| valid={len(deduped)} | invalid={invalid_rows}"
    )
    return deduped


def init_stock_pool_file(pool_file: str, period_min: int) -> None:
    if os.path.exists(pool_file):
        print(f"Stock pool file already exists: {pool_file}")
        return

    os.makedirs(os.path.dirname(pool_file) or ".", exist_ok=True)
    cached = discover_symbols_from_cache(period_min)
    if cached:
        seed = cached[:50]
    else:
        seed = [
            "000001.SZ",
            "000333.SZ",
            "000651.SZ",
            "000858.SZ",
            "002594.SZ",
            "300750.SZ",
            "600036.SS",
            "600519.SS",
            "601318.SS",
            "601899.SS",
        ]

    payload = pd.DataFrame(
        [{"symbol": s, "name": "", "enabled": 1} for s in seed],
        columns=["symbol", "name", "enabled"],
    )
    payload.to_csv(pool_file, index=False, encoding="utf-8-sig")
    print(f"Initialized stock pool file: {pool_file} (symbols={len(payload)})")


def fetch_minute_data(code6: str, period_min: int, adjust: str) -> Optional[pd.DataFrame]:
    try:
        raw = ak.stock_zh_a_hist_min_em(
            symbol=code6,
            start_date="",
            end_date="",
            period=str(period_min),
            adjust=adjust,
        )
        if raw is None or raw.empty:
            return None
        return normalize_minute_df(raw)
    except Exception:
        return None


def fetch_spot_map() -> Dict[str, Dict[str, float]]:
    """Return map: code6 -> {'price': float, 'name': str}."""
    out: Dict[str, Dict[str, float]] = {}
    try:
        spot = ak.stock_zh_a_spot_em()
        if spot is None or spot.empty:
            return out
        code_col = "代码" if "代码" in spot.columns else None
        price_col = "最新价" if "最新价" in spot.columns else None
        name_col = "名称" if "名称" in spot.columns else None
        if not code_col or not price_col:
            return out
        for _, row in spot.iterrows():
            code = str(row.get(code_col, "")).zfill(6)
            price = pd.to_numeric(row.get(price_col), errors="coerce")
            if code and pd.notna(price) and float(price) > 0:
                out[code] = {
                    "price": float(price),
                    "name": str(row.get(name_col, "")) if name_col else "",
                }
    except Exception:
        return out
    return out


@dataclass
class PositionState:
    symbol: str
    shares: int
    entry_price: float
    entry_time: str
    peak_price: float
    peak_profit_pct: float

    @property
    def entry_dt(self) -> datetime:
        dt = datetime.fromisoformat(self.entry_time)
        return dt if dt.tzinfo else dt.replace(tzinfo=CN_TZ)


class VolumeBreakoutRealtimeScanner:
    def __init__(
        self,
        symbols: List[str],
        period_min: int = 15,
        volume_ma_period: int = 20,
        volume_ratio: float = 2.0,
        stop_loss_pct: float = 0.05,
        take_profit_trigger_pct: float = 0.10,
        tp_trail_retrace: float = 0.07,
        max_holding_days_no_profit: int = 20,
        adjust: str = "qfq",
        positions_file: str = "results/volume_breakout_realtime/positions.json",
        output_dir: str = "results/volume_breakout_realtime",
        paper_trade: bool = True,
        fixed_shares: int = 100,
    ):
        self.symbols = symbols
        self.period_min = period_min
        self.volume_ma_period = volume_ma_period
        self.volume_ratio = volume_ratio
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_trigger_pct = take_profit_trigger_pct
        self.tp_trail_retrace = tp_trail_retrace
        self.max_holding_days_no_profit = max_holding_days_no_profit
        self.adjust = adjust
        self.positions_file = positions_file
        self.output_dir = output_dir
        self.paper_trade = paper_trade
        self.fixed_shares = fixed_shares

        os.makedirs(self.output_dir, exist_ok=True)
        self.positions: Dict[str, PositionState] = self._load_positions()

    def _load_positions(self) -> Dict[str, PositionState]:
        if not os.path.exists(self.positions_file):
            return {}
        try:
            with open(self.positions_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            out: Dict[str, PositionState] = {}
            if isinstance(raw, dict):
                for symbol, p in raw.items():
                    sym = normalize_symbol(symbol)
                    if not sym:
                        continue
                    out[sym] = PositionState(
                        symbol=sym,
                        shares=int(p.get("shares", 0)),
                        entry_price=float(p.get("entry_price", 0.0)),
                        entry_time=str(p.get("entry_time")),
                        peak_price=float(p.get("peak_price", p.get("entry_price", 0.0))),
                        peak_profit_pct=float(p.get("peak_profit_pct", 0.0)),
                    )
            return out
        except Exception:
            return {}

    def _save_positions(self) -> None:
        payload = {sym: asdict(pos) for sym, pos in self.positions.items()}
        os.makedirs(os.path.dirname(self.positions_file), exist_ok=True)
        with open(self.positions_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _append_history(self, records: List[Dict]) -> None:
        if not records:
            return
        hist_path = os.path.join(self.output_dir, "signals_history.csv")
        df = pd.DataFrame(records)
        exists = os.path.exists(hist_path)
        df.to_csv(hist_path, mode="a", header=not exists, index=False, encoding="utf-8-sig")

    def _save_latest_summary(self, summary: Dict) -> None:
        out_path = os.path.join(self.output_dir, "summary_latest.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    def _build_buy_signal(self, symbol: str, bar: pd.Series, realtime_price: float, name: str) -> Dict:
        stop_price = realtime_price * (1 - self.stop_loss_pct)
        return {
            "symbol": symbol,
            "name": name,
            "side": "BUY",
            "signal_time": str(bar.name),
            "scan_time": now_cn().strftime("%Y-%m-%d %H:%M:%S"),
            "signal_price": round(float(bar["Close"]), 3),
            "realtime_price": round(float(realtime_price), 3),
            "stop_loss_price": round(float(stop_price), 3),
            "volume": float(bar["Volume"]),
            "volume_ma": round(float(bar["volume_ma"]), 2),
            "volume_ratio_actual": round(float(bar["Volume"]) / float(bar["volume_ma"]), 3),
            "reason": "bullish_volume_breakout",
        }

    def _evaluate_sell(
        self,
        symbol: str,
        pos: PositionState,
        minute_df: pd.DataFrame,
        realtime_price: float,
        name: str,
    ) -> Optional[Dict]:
        current_profit_pct = realtime_price / pos.entry_price - 1.0
        pos.peak_price = max(pos.peak_price, realtime_price)
        pos.peak_profit_pct = max(pos.peak_profit_pct, pos.peak_price / pos.entry_price - 1.0)

        reason = None
        stop_price = pos.entry_price * (1 - self.stop_loss_pct)

        if realtime_price <= stop_price:
            reason = "stop_loss"
        else:
            if pos.peak_profit_pct >= self.take_profit_trigger_pct:
                retrace = pos.peak_profit_pct - current_profit_pct
                if retrace >= self.tp_trail_retrace:
                    reason = "take_profit_trail"
                else:
                    ma5_rt = get_daily_ma5_rt(minute_df, realtime_price)
                    if ma5_rt is not None and realtime_price < ma5_rt and pos.peak_price > ma5_rt:
                        reason = "take_profit_ma5_rt"

        if reason is None:
            hold_days = trading_days_between(pos.entry_dt, now_cn())
            if hold_days > self.max_holding_days_no_profit and current_profit_pct < 0:
                reason = "time_stop_loss"

        if reason is None:
            return None

        return {
            "symbol": symbol,
            "name": name,
            "side": "SELL",
            "signal_time": now_cn().strftime("%Y-%m-%d %H:%M:%S"),
            "scan_time": now_cn().strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price": round(float(pos.entry_price), 3),
            "realtime_price": round(float(realtime_price), 3),
            "peak_price": round(float(pos.peak_price), 3),
            "profit_pct": round(current_profit_pct * 100, 3),
            "peak_profit_pct": round(pos.peak_profit_pct * 100, 3),
            "reason": reason,
        }

    def run_scan_once(self) -> Dict:
        ts = now_cn().strftime("%Y-%m-%d %H:%M:%S")
        print("=" * 90)
        print(f"Volume Breakout Realtime Scan @ {ts} | symbols={len(self.symbols)} | period={self.period_min}min")
        print("=" * 90)

        spot_map = fetch_spot_map()
        buy_signals: List[Dict] = []
        sell_signals: List[Dict] = []
        errors = 0

        for i, symbol in enumerate(self.symbols, 1):
            code = symbol_to_code(symbol)
            name = spot_map.get(code, {}).get("name", "")
            minute_df = fetch_minute_data(code, self.period_min, self.adjust)
            if minute_df is None or len(minute_df) < self.volume_ma_period + 2:
                print(f"[{i}/{len(self.symbols)}] {symbol} skip: minute data unavailable")
                continue

            clean_df = drop_incomplete_last_bar(minute_df, self.period_min, now_cn())
            if len(clean_df) < self.volume_ma_period + 1:
                print(f"[{i}/{len(self.symbols)}] {symbol} skip: not enough completed bars")
                continue

            work = clean_df.copy()
            work["is_bullish"] = work["Close"] > work["Open"]
            work["volume_ma"] = work["Volume"].rolling(window=self.volume_ma_period).mean()
            work["volume_spike"] = work["Volume"] > work["volume_ma"] * self.volume_ratio
            bar = work.iloc[-1]
            buy_signal = bool(bar["is_bullish"] and bar["volume_spike"] and pd.notna(bar["volume_ma"]))

            realtime_price = spot_map.get(code, {}).get("price")
            if realtime_price is None or realtime_price <= 0:
                realtime_price = float(minute_df["Close"].iloc[-1])

            try:
                if symbol in self.positions:
                    sell = self._evaluate_sell(symbol, self.positions[symbol], clean_df, realtime_price, name)
                    if sell:
                        sell_signals.append(sell)
                        print(
                            f"[{i}/{len(self.symbols)}] {symbol} SELL {sell['reason']} "
                            f"entry={sell['entry_price']:.3f} now={sell['realtime_price']:.3f} "
                            f"pnl={sell['profit_pct']:+.2f}%"
                        )
                        if self.paper_trade:
                            self.positions.pop(symbol, None)
                    else:
                        print(f"[{i}/{len(self.symbols)}] {symbol} holding, no sell")
                else:
                    if buy_signal:
                        buy = self._build_buy_signal(symbol, bar, realtime_price, name)
                        buy_signals.append(buy)
                        print(
                            f"[{i}/{len(self.symbols)}] {symbol} BUY breakout "
                            f"sig={buy['signal_price']:.3f} now={buy['realtime_price']:.3f}"
                        )
                        if self.paper_trade:
                            self.positions[symbol] = PositionState(
                                symbol=symbol,
                                shares=self.fixed_shares,
                                entry_price=float(realtime_price),
                                entry_time=now_cn().isoformat(),
                                peak_price=float(realtime_price),
                                peak_profit_pct=0.0,
                            )
                    else:
                        print(f"[{i}/{len(self.symbols)}] {symbol} no buy")
            except Exception as exc:
                errors += 1
                print(f"[{i}/{len(self.symbols)}] {symbol} error: {exc}")

        all_records = buy_signals + sell_signals
        self._append_history(all_records)
        if self.paper_trade:
            self._save_positions()

        summary = {
            "scan_time": now_cn().isoformat(),
            "period_min": self.period_min,
            "symbol_count": len(self.symbols),
            "buy_count": len(buy_signals),
            "sell_count": len(sell_signals),
            "error_count": errors,
            "paper_positions_count": len(self.positions),
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
        }
        self._save_latest_summary(summary)

        print("-" * 90)
        print(
            f"Done: buy={len(buy_signals)} sell={len(sell_signals)} "
            f"errors={errors} positions={len(self.positions)}"
        )
        print(f"Output dir: {self.output_dir}")
        print("=" * 90)
        return summary


def parse_symbols(args: argparse.Namespace) -> List[str]:
    if args.symbol:
        sym = normalize_symbol(args.symbol)
        return [sym] if sym else []

    if args.symbols:
        symbols: List[str] = []
        for raw in args.symbols.split(","):
            sym = normalize_symbol(raw)
            if sym:
                symbols.append(sym)
        return sorted(list(dict.fromkeys(symbols)))

    symbols = load_symbols_from_pool_file(args.stock_pool_file)
    if symbols:
        return symbols

    symbols = discover_symbols_from_cache(args.period)
    if args.max_symbols and args.max_symbols > 0:
        symbols = symbols[: args.max_symbols]
    return symbols


def main() -> None:
    parser = argparse.ArgumentParser(description="A-share realtime volume-breakout scanner")
    parser.add_argument("--period", type=int, choices=[5, 15, 30, 60], default=15, help="minute period")
    parser.add_argument("--scan-interval-minutes", type=int, default=20, help="scan interval in daemon mode")
    parser.add_argument("--once", action="store_true", help="run once then exit")
    parser.add_argument("--daemon", action="store_true", help="run in loop during trading sessions")
    parser.add_argument("--symbol", default="", help="single symbol, e.g. 000001.SZ")
    parser.add_argument("--symbols", default="", help="comma separated symbols")
    parser.add_argument(
        "--stock-pool-file",
        default="scanners/stock_pool.csv",
        help="CSV file with columns: symbol,name,enabled",
    )
    parser.add_argument(
        "--init-stock-pool",
        action="store_true",
        help="initialize stock pool CSV template then exit",
    )
    parser.add_argument("--max-symbols", type=int, default=120, help="max symbols from cache when no symbol input")
    parser.add_argument("--volume-ma-period", type=int, default=20)
    parser.add_argument("--volume-ratio", type=float, default=2.0)
    parser.add_argument("--stop-loss", type=float, default=0.05)
    parser.add_argument("--take-profit-trigger", type=float, default=0.10)
    parser.add_argument("--tp-trail-retrace", type=float, default=0.07)
    parser.add_argument("--max-holding-days-no-profit", type=int, default=20)
    parser.add_argument("--adjust", choices=["", "qfq", "hfq"], default="qfq")
    parser.add_argument("--positions-file", default="results/volume_breakout_realtime/positions.json")
    parser.add_argument("--output-dir", default="results/volume_breakout_realtime")
    parser.add_argument("--paper-trade", action="store_true", help="enable paper position management")
    parser.add_argument("--fixed-shares", type=int, default=100, help="shares per paper entry")
    args = parser.parse_args()

    if args.init_stock_pool:
        init_stock_pool_file(args.stock_pool_file, args.period)
        return

    symbols = parse_symbols(args)
    if not symbols:
        print("No symbols available. Set --symbol/--symbols or prepare data_cache/a_stock_minute.")
        return

    scanner = VolumeBreakoutRealtimeScanner(
        symbols=symbols,
        period_min=args.period,
        volume_ma_period=args.volume_ma_period,
        volume_ratio=args.volume_ratio,
        stop_loss_pct=args.stop_loss,
        take_profit_trigger_pct=args.take_profit_trigger,
        tp_trail_retrace=args.tp_trail_retrace,
        max_holding_days_no_profit=args.max_holding_days_no_profit,
        adjust=args.adjust,
        positions_file=args.positions_file,
        output_dir=args.output_dir,
        paper_trade=args.paper_trade,
        fixed_shares=args.fixed_shares,
    )

    run_once_only = args.once or not args.daemon
    if run_once_only:
        scanner.run_scan_once()
        return

    print(
        f"Daemon started. Interval={args.scan_interval_minutes} min, "
        f"period={args.period} min, symbols={len(symbols)}"
    )
    print("CN trading sessions: 09:30-11:30, 13:00-15:00")

    while True:
        now = now_cn()
        if is_trading_time(now):
            scanner.run_scan_once()
            time.sleep(max(1, args.scan_interval_minutes * 60))
        else:
            nxt = next_market_open(now)
            wait_min = int((nxt - now).total_seconds() / 60)
            print(f"Out of trading session. Next open: {nxt:%Y-%m-%d %H:%M:%S} (in {wait_min} min)")
            sleep_until(nxt)


if __name__ == "__main__":
    main()
