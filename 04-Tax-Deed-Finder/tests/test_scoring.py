"""Tests for the scoring engine."""
import pytest
from analyzer.scoring import (
    calculate_score, apply_auto_filters,
    ParcelData, ValuationData, DemographicsData, RiskData,
)


def _risk(**kwargs) -> RiskData:
    defaults = dict(
        flood_zone="X", wetlands_percent=0.0, is_landlocked=False,
        has_road_access=True, road_type="paved", has_additional_liens=False,
        liens_amount=0, drive_time_minutes=30, acres=1.0, assessed_value=5000,
    )
    defaults.update(kwargs)
    return RiskData(**defaults)


def _parcel(**kwargs) -> ParcelData:
    return ParcelData(**{"property_type": "land", "acres": 1.0, "minimum_bid": 100, **kwargs})


def _val(**kwargs) -> ValuationData:
    return ValuationData(**{"market_value_estimate": None, "assessed_value": None, **kwargs})


def _demo(**kwargs) -> DemographicsData:
    return DemographicsData(**{"growth_rate_3yr": 0, **kwargs})


class TestAutoFilters:
    def test_passes_clean_parcel(self):
        passes, reasons = apply_auto_filters(_risk())
        assert passes
        assert reasons == []

    def test_fails_high_flood_zone(self):
        for zone in ["A", "AE", "AO", "AH", "VE"]:
            passes, reasons = apply_auto_filters(_risk(flood_zone=zone))
            assert not passes, f"Expected fail for zone {zone}"
            assert any("flood_zone" in r for r in reasons)

    def test_passes_flood_zone_x(self):
        passes, _ = apply_auto_filters(_risk(flood_zone="X"))
        assert passes

    def test_fails_wetlands_over_50(self):
        passes, reasons = apply_auto_filters(_risk(wetlands_percent=51))
        assert not passes
        assert any("wetlands" in r for r in reasons)

    def test_passes_wetlands_exactly_50(self):
        passes, _ = apply_auto_filters(_risk(wetlands_percent=50))
        assert passes

    def test_fails_landlocked(self):
        passes, reasons = apply_auto_filters(_risk(is_landlocked=True))
        assert not passes
        assert "landlocked" in reasons

    def test_fails_no_road_access(self):
        passes, reasons = apply_auto_filters(_risk(has_road_access=False))
        assert not passes
        assert "no_road_access" in reasons

    def test_fails_tiny_lot(self):
        passes, reasons = apply_auto_filters(_risk(acres=0.05))
        assert not passes
        assert any("too_small" in r for r in reasons)

    def test_fails_high_liens(self):
        passes, reasons = apply_auto_filters(_risk(has_additional_liens=True, liens_amount=1000))
        assert not passes
        assert any("liens" in r for r in reasons)

    def test_passes_low_liens(self):
        passes, _ = apply_auto_filters(_risk(has_additional_liens=True, liens_amount=400))
        assert passes

    def test_fails_too_far(self):
        passes, reasons = apply_auto_filters(_risk(drive_time_minutes=130))
        assert not passes
        assert any("drive_time" in r for r in reasons)


class TestScoring:
    def test_failed_filter_gives_zero_score(self):
        result = calculate_score(
            _parcel(), _val(market_value_estimate=1000),
            _demo(growth_rate_3yr=10), _risk(flood_zone="AE")
        )
        assert result.score_total == 0
        assert not result.passes_filters

    def test_discount_80_gives_40_pts(self):
        result = calculate_score(
            _parcel(minimum_bid=200),
            _val(market_value_estimate=1000),
            _demo(), _risk(),
        )
        assert result.score_discount == 40
        assert result.discount_percent == pytest.approx(80.0)

    def test_discount_60_gives_30_pts(self):
        result = calculate_score(
            _parcel(minimum_bid=400),
            _val(market_value_estimate=1000),
            _demo(), _risk(),
        )
        assert result.score_discount == 30

    def test_no_market_value_gives_zero_discount(self):
        result = calculate_score(_parcel(), _val(), _demo(), _risk())
        assert result.score_discount == 0
        assert result.discount_percent is None

    def test_growth_over_7_gives_20_pts(self):
        result = calculate_score(_parcel(), _val(), _demo(growth_rate_3yr=8), _risk())
        assert result.score_population_growth == 20

    def test_growth_3_gives_10_pts(self):
        result = calculate_score(_parcel(), _val(), _demo(growth_rate_3yr=3), _risk())
        assert result.score_population_growth == 10

    def test_paved_road_gives_20_pts(self):
        result = calculate_score(_parcel(), _val(), _demo(), _risk(road_type="paved"))
        assert result.score_road_access == 20

    def test_unpaved_road_gives_10_pts(self):
        result = calculate_score(_parcel(), _val(), _demo(), _risk(road_type="unpaved"))
        assert result.score_road_access == 10

    def test_house_gives_10_size_pts(self):
        result = calculate_score(_parcel(property_type="house"), _val(), _demo(), _risk())
        assert result.score_size == 10

    def test_quarter_acre_gives_10_size_pts(self):
        result = calculate_score(_parcel(acres=0.5), _val(), _demo(), _risk(acres=0.5))
        assert result.score_size == 10

    def test_bid_under_100_gives_10_pts(self):
        result = calculate_score(_parcel(minimum_bid=50), _val(), _demo(), _risk())
        assert result.score_bid_price == 10

    def test_max_score_100(self):
        result = calculate_score(
            _parcel(property_type="house", minimum_bid=50),
            _val(market_value_estimate=1000),
            _demo(growth_rate_3yr=10),
            _risk(road_type="paved"),
        )
        assert result.score_total <= 100
        assert result.score_total == 40 + 20 + 20 + 10 + 10
