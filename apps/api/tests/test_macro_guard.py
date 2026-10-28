"""Macro rules are saved as drafts and never silently ignored by the backtester."""
import pytest
from pydantic import ValidationError
from main import ExplorationRequest

CONFIG = dict(
    name="macro guard",
    dataset_id="not-used",
    symbol="XAUUSD",
    timeframes=["5m"],
    families=["ema_cross"],
    indicator_ranges={},
)

def test_macro_selected_rejected_without_point_in_time_feed():
    with pytest.raises(ValidationError, match="point-in-time"):
        ExplorationRequest(**CONFIG, macro_indicators=["macro_inflation_cpi"], macro_rules={
            "macro_inflation_cpi": {
                "condition": "rising",
                "threshold": 0,
                "min_release_lag_days": 1,
            },
        })

def test_technical_only_still_allowed():
    request=ExplorationRequest(**CONFIG, macro_indicators=[])
    assert request.macro_indicators==[]
    assert request.mode == "random"
