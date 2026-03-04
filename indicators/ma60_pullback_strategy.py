"""
MA60 pullback strategy.

Rules:
1. Trend filter: MA5, MA10, MA20 are all above MA60.
2. Buy: under the trend filter, MA60 is in uptrend, and price breaks below MA60.
3. Stop loss: MA10 breaks below MA60.
4. Take profit: MA10 is more than 20% above MA60 on the day.
"""

from typing import Dict

import numpy as np
import pandas as pd


def calculate_indicators(
    df: pd.DataFrame,
    ma5_period: int = 5,
    ma10_period: int = 10,
    ma20_period: int = 20,
    ma60_period: int = 60,
    ma60_uptrend_lookback: int = 5,
) -> pd.DataFrame:
    """Calculate moving averages and helper columns."""
    data = df.copy()

    required_cols = ["Close"]
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"Missing required column: {col}")

    data["ma5"] = data["Close"].rolling(window=ma5_period).mean()
    data["ma10"] = data["Close"].rolling(window=ma10_period).mean()
    data["ma20"] = data["Close"].rolling(window=ma20_period).mean()
    data["ma60"] = data["Close"].rolling(window=ma60_period).mean()

    data["trend_ready"] = (
        data["ma5"].gt(data["ma60"])
        & data["ma10"].gt(data["ma60"])
        & data["ma20"].gt(data["ma60"])
        & data["ma5"].notna()
        & data["ma10"].notna()
        & data["ma20"].notna()
        & data["ma60"].notna()
    )

    data["price_cross_below_ma60"] = (
        data["Close"].lt(data["ma60"])
        & data["Close"].shift(1).ge(data["ma60"].shift(1))
    )

    data["ma10_cross_below_ma60"] = (
        data["ma10"].lt(data["ma60"])
        & data["ma10"].shift(1).ge(data["ma60"].shift(1))
    )

    data["ma10_vs_ma60_pct"] = (data["ma10"] - data["ma60"]) / data["ma60"] * 100.0
    lookback = max(1, int(ma60_uptrend_lookback))
    data["ma60_uptrend"] = data["ma60"].gt(data["ma60"].shift(lookback))
    return data


def generate_signals(
    df: pd.DataFrame,
    take_profit_threshold_pct: float = 20.0,
    stop_loss_enabled: bool = True,
    require_price_cross: bool = True,
    stop_loss_use_cross: bool = True,
    require_ma60_uptrend: bool = True,
    ma60_uptrend_lookback: int = 5,
) -> pd.DataFrame:
    """Generate position and trade signals."""
    data = df.copy()

    required_cols = ["Close", "ma10", "ma60", "trend_ready"]
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"Missing required column: {col}")

    if "price_cross_below_ma60" not in data.columns:
        data["price_cross_below_ma60"] = (
            data["Close"].lt(data["ma60"])
            & data["Close"].shift(1).ge(data["ma60"].shift(1))
        )
    if "ma10_cross_below_ma60" not in data.columns:
        data["ma10_cross_below_ma60"] = (
            data["ma10"].lt(data["ma60"])
            & data["ma10"].shift(1).ge(data["ma60"].shift(1))
        )
    if "ma10_vs_ma60_pct" not in data.columns:
        data["ma10_vs_ma60_pct"] = (data["ma10"] - data["ma60"]) / data["ma60"] * 100.0
    if "ma60_uptrend" not in data.columns:
        lookback = max(1, int(ma60_uptrend_lookback))
        data["ma60_uptrend"] = data["ma60"].gt(data["ma60"].shift(lookback))

    data["signal"] = 0
    data["position"] = 0
    data["entry_price"] = np.nan
    data["stop_loss_price"] = np.nan
    data["take_profit_price"] = np.nan
    data["exit_price"] = np.nan
    data["exit_reason"] = ""

    buy_trigger = (
        data["price_cross_below_ma60"] if require_price_cross else data["Close"].lt(data["ma60"])
    )
    ma60_uptrend_condition = data["ma60_uptrend"] if require_ma60_uptrend else True
    data["buy_condition"] = data["trend_ready"] & ma60_uptrend_condition & buy_trigger

    position = 0
    entry_price = np.nan

    for i in range(len(data)):
        row = data.iloc[i]
        current_price = float(row["Close"])

        if position == 0:
            if bool(row["buy_condition"]):
                position = 1
                entry_price = current_price

                data.iloc[i, data.columns.get_loc("signal")] = 1
                data.iloc[i, data.columns.get_loc("position")] = 1
                data.iloc[i, data.columns.get_loc("entry_price")] = entry_price
                data.iloc[i, data.columns.get_loc("stop_loss_price")] = row["ma60"]
                data.iloc[i, data.columns.get_loc("take_profit_price")] = row["ma60"] * (
                    1.0 + take_profit_threshold_pct / 100.0
                )
        else:
            data.iloc[i, data.columns.get_loc("position")] = 1
            data.iloc[i, data.columns.get_loc("entry_price")] = entry_price
            data.iloc[i, data.columns.get_loc("stop_loss_price")] = row["ma60"]
            data.iloc[i, data.columns.get_loc("take_profit_price")] = row["ma60"] * (
                1.0 + take_profit_threshold_pct / 100.0
            )

            if stop_loss_enabled:
                stop_loss_hit = (
                    bool(row["ma10_cross_below_ma60"])
                    if stop_loss_use_cross
                    else bool(row["ma10"] < row["ma60"])
                )
            else:
                stop_loss_hit = False
            take_profit_hit = bool(row["ma10_vs_ma60_pct"] > take_profit_threshold_pct)

            if stop_loss_hit or take_profit_hit:
                position = 0
                data.iloc[i, data.columns.get_loc("signal")] = -1
                data.iloc[i, data.columns.get_loc("position")] = 0
                data.iloc[i, data.columns.get_loc("exit_price")] = current_price
                data.iloc[i, data.columns.get_loc("exit_reason")] = (
                    "stop_loss_ma10_below_ma60" if stop_loss_hit else "take_profit_ma10_over_ma60"
                )
                entry_price = np.nan

    return data


def get_strategy_params() -> Dict:
    """Default strategy parameters."""
    return {
        "ma5_period": 5,
        "ma10_period": 10,
        "ma20_period": 20,
        "ma60_period": 60,
        "ma60_uptrend_lookback": 5,
        "take_profit_threshold_pct": 20.0,
        "stop_loss_enabled": True,
        "require_price_cross": True,
        "stop_loss_use_cross": True,
        "require_ma60_uptrend": True,
    }


def get_strategy_name() -> str:
    return "MA60 Pullback Strategy"


def get_strategy_description() -> str:
    return (
        "Buy when MA5/MA10/MA20 are above MA60, MA60 is in uptrend, and price breaks below MA60. "
        "Stop loss when MA10 breaks below MA60, take profit when MA10 is over MA60 by 20%."
    )
