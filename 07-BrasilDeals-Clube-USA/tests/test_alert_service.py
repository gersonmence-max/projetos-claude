import pytest
from unittest.mock import MagicMock, patch

# ---- extract_asin_from_url ----

def test_extract_asin_dp_format():
    from services.alert_service import extract_asin_from_url
    asin = extract_asin_from_url("https://www.amazon.com/dp/B08N5WRWNW")
    assert asin == "B08N5WRWNW"

def test_extract_asin_gp_product_format():
    from services.alert_service import extract_asin_from_url
    asin = extract_asin_from_url("https://www.amazon.com/gp/product/B08N5WRWNW?ref=something")
    assert asin == "B08N5WRWNW"

def test_extract_asin_with_title_slug():
    from services.alert_service import extract_asin_from_url
    asin = extract_asin_from_url("https://www.amazon.com/Some-Product-Title/dp/B0ABCDE12X/ref=sr")
    assert asin == "B0ABCDE12X"

def test_extract_asin_invalid_url_raises():
    from services.alert_service import extract_asin_from_url
    with pytest.raises(ValueError, match="ASIN não encontrado"):
        extract_asin_from_url("https://www.google.com/search?q=produto")

# ---- create_alert ----

def test_create_alert_succeeds(mocker):
    from services.alert_service import create_alert
    mock_sb = MagicMock()
    mock_sb.table().select().eq().eq().execute.return_value.data = []  # 0 alertas existentes
    mock_sb.table().insert().execute.return_value.data = [{
        "id": "uuid-1", "member_id": "m-1", "asin": "B08N5WRWNW",
        "target_type": "price", "target_value": 29.99, "status": "active"
    }]
    mocker.patch("services.alert_service._supabase", return_value=mock_sb)

    result = create_alert(
        member_id="m-1", asin="B08N5WRWNW",
        target_type="price", target_value=29.99
    )
    assert result["asin"] == "B08N5WRWNW"
    assert result["status"] == "active"

def test_create_alert_raises_on_limit(mocker):
    from services.alert_service import create_alert
    mock_sb = MagicMock()
    mock_sb.table().select().eq().eq().execute.return_value.data = [{}] * 10  # já tem 10
    mocker.patch("services.alert_service._supabase", return_value=mock_sb)

    with pytest.raises(ValueError, match="Limite"):
        create_alert("m-1", "B08N5WRWNW", "price", 29.99)

# ---- cancel_alert ----

def test_cancel_alert_returns_true(mocker):
    from services.alert_service import cancel_alert
    mock_sb = MagicMock()
    mock_sb.table().update().eq().eq().execute.return_value.data = [{"id": "uuid-1"}]
    mocker.patch("services.alert_service._supabase", return_value=mock_sb)

    result = cancel_alert("uuid-1", "m-1")
    assert result is True

def test_cancel_alert_not_found_returns_false(mocker):
    from services.alert_service import cancel_alert
    mock_sb = MagicMock()
    mock_sb.table().update().eq().eq().execute.return_value.data = []
    mocker.patch("services.alert_service._supabase", return_value=mock_sb)

    result = cancel_alert("uuid-inexistente", "m-1")
    assert result is False
