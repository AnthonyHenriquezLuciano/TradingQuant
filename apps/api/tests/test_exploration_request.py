"""Regression: API accepts every family implemented by the research engine.

The client-side catalog must never offer runnable families rejected by Pydantic.
"""
import pytest
from pydantic import ValidationError

from engine import FAMILIES
from main import ExplorationRequest


def test_exploration_request_accepts_every_implemented_family():
    for family in set(FAMILIES.values()):
        request = ExplorationRequest(
            name="Validación de señales", dataset_id="00000000-0000-0000-0000-000000000001",
            symbol="XAUUSD", families=[family],
        )
        assert request.families == [family]


def test_exploration_request_rejects_unimplemented_family_with_explanation():
    with pytest.raises(ValidationError, match="Indicadores no implementados para simulación"):
        ExplorationRequest(
            name="Prueba", dataset_id="00000000-0000-0000-0000-000000000001",
            symbol="XAUUSD", families=["tech_indicator_without_engine"],
        )
