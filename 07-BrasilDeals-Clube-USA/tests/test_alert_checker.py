import pytest
from unittest.mock import MagicMock, patch

# conftest já adiciona clubeusa ao sys.path
# adicionar dealscanner2 também
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dealscanner2'))


def test_should_trigger_price_type_below_target():
    from alert_checker import should_trigger
    alert = {"target_type": "price", "target_value": 30.00, "price_current": 50.00}
    assert should_trigger(alert, current_price=29.99) is True

def test_should_not_trigger_price_type_above_target():
    from alert_checker import should_trigger
    alert = {"target_type": "price", "target_value": 30.00, "price_current": 50.00}
    assert should_trigger(alert, current_price=31.00) is False

def test_should_trigger_percent_type_sufficient_drop():
    from alert_checker import should_trigger
    alert = {"target_type": "percent", "target_value": 15.0, "price_current": 100.00}
    assert should_trigger(alert, current_price=84.00) is True  # queda de 16%

def test_should_not_trigger_percent_type_insufficient_drop():
    from alert_checker import should_trigger
    alert = {"target_type": "percent", "target_value": 15.0, "price_current": 100.00}
    assert should_trigger(alert, current_price=90.00) is False  # queda de 10%

def test_should_not_trigger_percent_without_price_current():
    from alert_checker import should_trigger
    alert = {"target_type": "percent", "target_value": 15.0, "price_current": None}
    assert should_trigger(alert, current_price=80.00) is False
