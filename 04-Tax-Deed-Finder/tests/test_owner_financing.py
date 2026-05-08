"""Tests for the owner financing calculator."""
import pytest
from analyzer.owner_financing import calculate_owner_financing


class TestOwnerFinancing:
    def test_basic_calculation(self):
        result = calculate_owner_financing(minimum_bid=500, market_value=5000)
        assert result is not None
        assert result.resale_price == pytest.approx(3250.0)      # 5000 * 0.65
        assert result.down_payment == pytest.approx(325.0)        # 3250 * 0.10
        assert result.balance == pytest.approx(2925.0)
        assert result.term_months == 24
        assert result.monthly_payment == pytest.approx(121.875, rel=0.01)
        assert result.total_return == pytest.approx(3250.0, rel=0.01)

    def test_roi_calculation(self):
        result = calculate_owner_financing(minimum_bid=100, market_value=1000)
        assert result is not None
        # resale = 650, down = 65, balance = 585, monthly = 585/24 = 24.375
        # total = 65 + 24.375*24 = 65 + 585 = 650
        # roi = (650/100 - 1) * 100 = 550%
        assert result.roi_percent == pytest.approx(550.0, rel=0.01)

    def test_returns_none_for_zero_bid(self):
        result = calculate_owner_financing(minimum_bid=0, market_value=1000)
        assert result is None

    def test_returns_none_for_zero_market_value(self):
        result = calculate_owner_financing(minimum_bid=500, market_value=0)
        assert result is None

    def test_custom_parameters(self):
        result = calculate_owner_financing(
            minimum_bid=200,
            market_value=1000,
            resale_ratio=0.70,
            down_payment_ratio=0.15,
            term_months=36,
        )
        assert result is not None
        assert result.resale_price == pytest.approx(700.0)
        assert result.down_payment == pytest.approx(105.0)
        assert result.term_months == 36

    def test_months_to_recover(self):
        result = calculate_owner_financing(minimum_bid=1000, market_value=5000)
        assert result is not None
        # monthly = (5000*0.65 - 5000*0.65*0.10) / 24 = 2925/24 ≈ 121.875
        # recover = 1000 / 121.875 ≈ 8.2
        assert result.months_to_recover == pytest.approx(8.2, rel=0.05)
