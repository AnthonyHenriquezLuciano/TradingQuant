"""Ensure newly exposed indicator families run in the real discovery pipeline."""
from test_advanced import synthetic_bars,config
from engine_advanced import run_advanced


def test_extended_indicators_generate_real_candidates_without_fallback():
    dataset=synthetic_bars(1800)
    for name in ("tech_macd","tech_rsi","tech_bandas_bollinger","tech_ema","sit_fair_value_gap_fvg"):
        params=config(families=[name],candidates=5,mc_iterations=100,
            indicator_ranges={"tech_period_min":10,"tech_period_max":14,"tech_period_step":2})
        result=run_advanced(dataset,params)
        assert 1<=result["tested"]<=5, (name,result["tested"])
        for candidate in result["candidates"]:
            assert candidate["family"]==name
            assert "in_sample" in candidate
            assert "out_of_sample" in candidate
            assert "monte_carlo" in candidate
