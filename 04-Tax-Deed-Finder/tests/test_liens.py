"""Tests for the liens enricher — type detection and survival rules."""
import pytest
from enrichers.liens import (
    detect_lien_type,
    is_release_document,
    classify_lien,
    _build_lien_record,
)


class TestDetectLienType:
    def test_irs_federal_explicit(self):
        assert detect_lien_type("NOTICE OF FEDERAL TAX LIEN Internal Revenue Service") == "irs_federal"

    def test_irs_abbreviation(self):
        assert detect_lien_type("IRS lien filed against John Smith") == "irs_federal"

    def test_state_tax_department_of_revenue(self):
        assert detect_lien_type("Texas Department of Revenue state tax lien") == "state_tax"

    def test_hoa(self):
        assert detect_lien_type("Homeowners Association assessment lien filed") == "hoa"

    def test_hoa_abbreviation(self):
        assert detect_lien_type("Sunridge HOA lien") == "hoa"

    def test_hospital(self):
        assert detect_lien_type("St. Mary Medical Center medical lien") == "hospital"

    def test_code_enforcement(self):
        assert detect_lien_type("City of Dallas code enforcement lien violation") == "code_enforcement"

    def test_mechanics(self):
        assert detect_lien_type("Mechanic's Lien filed by ABC Contractors") == "mechanics"

    def test_judgment(self):
        assert detect_lien_type("Final Judgment Lien entered in Kaufman County Court") == "judgment"

    def test_other_fallback(self):
        assert detect_lien_type("Some random document with no lien keywords") == "other"

    def test_irs_takes_priority_over_state(self):
        # Both keywords present — IRS pattern should match first
        text = "Internal Revenue Service state tax lien notice"
        result = detect_lien_type(text)
        assert result == "irs_federal"


class TestIsReleaseDocument:
    def test_release_of_lien(self):
        assert is_release_document("Release of Lien — John Smith") is True

    def test_satisfaction_of_lien(self):
        assert is_release_document("Satisfaction of Lien filed 2024") is True

    def test_lien_release(self):
        assert is_release_document("Lien Release recorded") is True

    def test_regular_lien_is_not_release(self):
        assert is_release_document("Federal Tax Lien Notice") is False

    def test_discharge_of_lien(self):
        assert is_release_document("Discharge of Lien executed") is True


class TestClassifyLien:
    # IRS always survives everywhere
    def test_irs_survives_all_states(self):
        for state in ["TX", "GA", "TN", "AR", "FL", "NC"]:
            survives, reason = classify_lien("irs_federal", state)
            assert survives, f"IRS should survive in {state}"
            assert reason is not None

    def test_state_tax_survives_in_monitored_states(self):
        for state in ["TX", "GA", "TN", "AR", "FL", "NC"]:
            survives, _ = classify_lien("state_tax", state)
            assert survives, f"State tax lien should survive in {state}"

    def test_hoa_survives_in_florida(self):
        survives, reason = classify_lien("hoa", "FL")
        assert survives
        assert "720" in reason or "HOA" in reason

    def test_hoa_survives_in_texas(self):
        survives, _ = classify_lien("hoa", "TX")
        assert survives

    def test_hoa_does_not_survive_in_georgia(self):
        survives, _ = classify_lien("hoa", "GA")
        assert not survives

    def test_hoa_does_not_survive_in_tennessee(self):
        survives, _ = classify_lien("hoa", "TN")
        assert not survives

    def test_judgment_never_survives(self):
        for state in ["TX", "GA", "TN", "AR", "FL", "NC"]:
            survives, _ = classify_lien("judgment", state)
            assert not survives, f"Judgment lien should NOT survive in {state}"

    def test_mechanics_never_survives(self):
        for state in ["TX", "GA", "FL", "NC"]:
            survives, _ = classify_lien("mechanics", state)
            assert not survives

    def test_hospital_never_survives(self):
        for state in ["TX", "GA", "FL"]:
            survives, _ = classify_lien("hospital", state)
            assert not survives

    def test_code_enforcement_never_survives(self):
        for state in ["TX", "GA", "FL", "NC"]:
            survives, _ = classify_lien("code_enforcement", state)
            assert not survives


class TestBuildLienRecord:
    def _row(self, **kwargs):
        base = {
            "doc_number": "2024-001",
            "doc_type": "LIEN",
            "grantor": "John Doe",
            "grantee": "Internal Revenue Service",
            "recorded_date": "01/15/2024",
            "amount": "$15,000.00",
            "full_text": "Internal Revenue Service federal tax lien notice John Doe",
        }
        base.update(kwargs)
        return base

    def test_builds_irs_record(self):
        rec = _build_lien_record(self._row(), "TX")
        assert rec.lien_type == "irs_federal"
        assert rec.survives_tax_deed is True
        assert rec.survive_reason is not None
        assert rec.lien_amount == 15000.0
        assert rec.grantee == "Internal Revenue Service"

    def test_release_document_marked_released(self):
        row = self._row(full_text="Release of Lien Internal Revenue Service John Doe")
        rec = _build_lien_record(row, "TX")
        assert rec.is_released is True

    def test_judgment_does_not_survive_tx(self):
        row = self._row(full_text="Final Judgment Lien entered against John Doe")
        rec = _build_lien_record(row, "TX")
        assert rec.lien_type == "judgment"
        assert rec.survives_tax_deed is False

    def test_date_parsed(self):
        rec = _build_lien_record(self._row(recorded_date="03/22/2023"), "GA")
        assert rec.recorded_date is not None
        assert rec.recorded_date.year == 2023
        assert rec.recorded_date.month == 3
