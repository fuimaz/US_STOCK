import numpy as np
import pandas as pd
from core.backtest_engine import BaseStrategy


class BollVolumeStrategy(BaseStrategy):
    """
    BOLL + 成交量策略信号生成器。
    该类只负责生成指标和信号，不直接处理仓位与资金。
    """

    def __init__(
        self,
        boll_period: int = 20,
        boll_std: float = 2.0,
        vol_ma_short: int = 5,
        vol_ma_long: int = 20,
        squeeze_window: int = 60,
        squeeze_quantile: float = 0.2,
        breakout_volume_mult: float = 1.5,
        top_volume_mult: float = 2.0,
    ):
        super().__init__(name="BollVolumeStrategy")
        self.boll_period = boll_period
        self.boll_std = boll_std
        self.vol_ma_short = vol_ma_short
        self.vol_ma_long = vol_ma_long
        self.squeeze_window = squeeze_window
        self.squeeze_quantile = squeeze_quantile
        self.breakout_volume_mult = breakout_volume_mult
        self.top_volume_mult = top_volume_mult

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        df["Middle"] = df["Close"].rolling(self.boll_period).mean()
        rolling_std = df["Close"].rolling(self.boll_period).std()
        df["Upper"] = df["Middle"] + self.boll_std * rolling_std
        df["Lower"] = df["Middle"] - self.boll_std * rolling_std

        df["VolMA5"] = df["Volume"].rolling(self.vol_ma_short).mean()
        df["VolMA20"] = df["Volume"].rolling(self.vol_ma_long).mean()
        df["MA5"] = df["Close"].rolling(5).mean()
        df["BandWidth"] = (df["Upper"] - df["Lower"]) / df["Middle"]

        # BOLL 收口定义：带宽处于近期低分位
        bw_q = df["BandWidth"].rolling(self.squeeze_window).quantile(self.squeeze_quantile)
        df["is_squeeze"] = df["BandWidth"] <= bw_q
        df["squeeze_release"] = (
            df["is_squeeze"].shift(1).fillna(False)
            & (df["BandWidth"] > df["BandWidth"].shift(1))
            & (df["Middle"] > df["Middle"].shift(1))
        )

        body = (df["Close"] - df["Open"]).abs()
        upper_shadow = df["High"] - df[["Open", "Close"]].max(axis=1)
        lower_shadow = df[["Open", "Close"]].min(axis=1) - df["Low"]
        full_range = (df["High"] - df["Low"]).replace(0, np.nan)
        df["long_upper_shadow"] = (
            (upper_shadow >= body * 1.2)
            & (upper_shadow >= full_range * 0.35)
        ).fillna(False)
        df["bullish_reversal"] = (df["Close"] > df["Open"]) & (lower_shadow > body * 0.5)

        vol_ratio_20 = df["Volume"] / df["VolMA20"]
        vol_ratio_5 = df["Volume"] / df["VolMA5"]

        # 1) 抄底买入：下轨 + 缩量/温和放量 + 止跌K
        touch_lower = (df["Low"] <= df["Lower"]) | (df["Close"] <= df["Lower"])
        vol_ok_bottom = (vol_ratio_20 <= 1.0) | ((vol_ratio_20 > 1.0) & (vol_ratio_20 <= 1.3))
        df["buy_probe"] = touch_lower & vol_ok_bottom & df["bullish_reversal"]

        # 2) 突破买入：收口后向上开口 + 放量突破中轨
        cross_middle_up = (df["Close"] > df["Middle"]) & (df["Close"].shift(1) <= df["Middle"].shift(1))
        vol_ok_break = vol_ratio_5 >= self.breakout_volume_mult
        df["buy_breakout"] = df["squeeze_release"] & cross_middle_up & vol_ok_break

        # 3) 回踩加仓：上涨趋势中回踩中轨 + 缩量 + 阳线
        trend_up = df["Middle"] > df["Middle"].shift(1)
        pullback_to_middle = (df["Low"] <= df["Middle"] * 1.005) & (df["Close"] >= df["Middle"])
        prev_peak_volume = df["Volume"].rolling(10).max().shift(1)
        shrink_volume = df["Volume"] <= prev_peak_volume * 0.5
        df["buy_add"] = trend_up & pullback_to_middle & shrink_volume & (df["Close"] > df["Open"])

        # 4) 触顶减仓：上轨 + 天量 + 长上影/滞涨
        touch_upper = (df["High"] >= df["Upper"]) | (df["Close"] >= df["Upper"])
        abnormal_volume = vol_ratio_20 >= self.top_volume_mult
        flat_close = (df["Close"] <= df["Close"].shift(1)) & (df["Close"] >= df["Open"])
        df["sell_reduce"] = touch_upper & abnormal_volume & (df["long_upper_shadow"] | flat_close)

        # 5) 破位清仓：跌破中轨无法收回 + 放量下跌 + 通道向下开口
        below_middle = df["Close"] < df["Middle"]
        failed_reclaim = below_middle & (df["Close"].shift(1) < df["Middle"].shift(1))
        vol_down = (vol_ratio_20 >= 1.2) & (df["Close"] < df["Open"])
        down_open = (df["Middle"] < df["Middle"].shift(1)) & (df["Upper"] < df["Upper"].shift(1))
        df["sell_exit"] = failed_reclaim & vol_down & down_open

        # 6) 跟踪止盈触发：跌破前日低点或5日线
        df["trailing_exit"] = (df["Close"] < df["Low"].shift(1)) | (df["Close"] < df["MA5"])

        # 兼容 BacktestEngine 的最简信号列（全进全出）
        df["signal"] = 0
        df.loc[df["buy_probe"] | df["buy_breakout"] | df["buy_add"], "signal"] = 1
        df.loc[df["sell_reduce"] | df["sell_exit"] | df["trailing_exit"], "signal"] = -1

        return df
