"""Research-grade session and previous-day reference levels (UTC/source timezone explicit).

Session levels are only made available AFTER the complete local-time session ends.
A sweep is an intrabar break followed by a closing-price rejection of the reference.
"""
from __future__ import annotations
from zoneinfo import ZoneInfo
import numpy as np
import polars as pl
from numba import njit

SITUATIONS = {
    3: ("london_high_sweep", "Europe/London", 8, 16, -1),
    4: ("london_low_sweep", "Europe/London", 8, 16, 1),
    5: ("asia_high_sweep", "Asia/Tokyo", 9, 17, -1),
    6: ("asia_low_sweep", "Asia/Tokyo", 9, 17, 1),
    7: ("previous_day_high_sweep", None, 0, 0, -1),
    8: ("previous_day_low_sweep", None, 0, 0, 1),
}
SOURCE_ZONES = frozenset((
    "UTC", "Europe/London", "Europe/Athens", "America/New_York",
    "America/Santo_Domingo", "Asia/Tokyo",
))
TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60,
              "4h": 240, "1d": 1440}


def sweep_reference(
    df: pl.DataFrame, kind: int, source_timezone: str, timeframe: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return available reference level, session-day ordinal and valid-location mask.

    For sessions, 'session day' is local London/Tokyo day. For PDH/L, it's
    the local source timezone calendar day. No future candles are accessible
    when a level becomes available.
    """
    if kind not in SITUATIONS:
        raise ValueError("Situación no reconocida.")
    if source_timezone not in SOURCE_ZONES:
        raise ValueError("Zona horaria de origen no admitida.")
    if timeframe not in TF_MINUTES or TF_MINUTES[timeframe] > 60:
        raise ValueError("Las barridas requieren intervalos de M1 a H1.")
    _, target_zone, start, end, side = SITUATIONS[kind]
    target_zone = target_zone or source_timezone
    # Input OHLC timestamps are naive. Interpret them in a user-specified
    # IANA timezone; convert to actual market timezone with DST.
    try:
        ts = (
            df.select(
                pl.col("timestamp")
                .dt.replace_time_zone(source_timezone, ambiguous="earliest")
                .dt.convert_time_zone(target_zone)
                .alias("local")
            )["local"].to_list()
        )
    except Exception as exc:
        raise ValueError("No se pudieron convertir las fechas a la zona horaria seleccionada.") from exc
    n = len(ts)
    levels = np.full(n, np.nan)
    ids = np.empty(n, dtype=np.int32)
    valid = np.zeros(n, dtype=np.bool_)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    ordinal = np.array([t.date().toordinal() for t in ts], dtype=np.int32)
    ids[:] = ordinal

    if kind in (7, 8):
        # Rolling previous trading day's completed range. This naturally
        # uses Friday as the previous day on Monday, never Monday's future.
        previous_high = np.nan
        previous_low = np.nan
        current_day = ordinal[0]
        day_high = -np.inf
        day_low = np.inf
        count = 0
        for i in range(n):
            if ordinal[i] != current_day:
                if count >= 4:
                    previous_high, previous_low = day_high, day_low
                current_day = ordinal[i]
                day_high, day_low, count = -np.inf, np.inf, 0
            if np.isfinite(previous_high):
                levels[i] = previous_high if side == -1 else previous_low
                valid[i] = True
            day_high = max(day_high, high[i])
            day_low = min(day_low, low[i])
            count += 1
        return levels, ids, valid

    # Build only session candles [start,end) and publish the range from end
    # until the end of the SAME local calendar day.
    values: dict[int, tuple[float, float, int]] = {}
    for i, t in enumerate(ts):
        in_session = start <= (t.hour + t.minute/60.) < end
        if not in_session:
            continue
        d = ordinal[i]
        h, l, cnt = values.get(d, (-np.inf, np.inf, 0))
        values[d] = (max(h, high[i]), min(l, low[i]), cnt + 1)
    required = int((end-start) * 60 / TF_MINUTES[timeframe] * .70)
    for i, t in enumerate(ts):
        hour = t.hour + t.minute/60.
        if hour < end:
            continue
        range_data = values.get(ordinal[i])
        if range_data is None or range_data[2] < required:
            continue
        levels[i] = range_data[0] if side == -1 else range_data[1]
        valid[i] = True
    return levels, ids, valid


@njit(cache=True)
def sweep_signals(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                  level: np.ndarray, days: np.ndarray, valid: np.ndarray,
                  side: int, buffer_bps: int) -> np.ndarray:
    """One close-confirmed wick rejection per reference day, next-bar entry."""
    n = len(close)
    out = np.zeros(n, dtype=np.int8)
    last_signal_day = -1
    for i in range(1, n):
        if not valid[i] or not np.isfinite(level[i]):
            continue
        if days[i] == last_signal_day:
            continue
        price = level[i]
        threshold = price * (buffer_bps / 10000.0)
        if side == -1:
            swept = high[i] > price + threshold and close[i] < price
        else:
            swept = low[i] < price - threshold and close[i] > price
        if swept:
            out[i] = side
            last_signal_day = days[i]
    return out
