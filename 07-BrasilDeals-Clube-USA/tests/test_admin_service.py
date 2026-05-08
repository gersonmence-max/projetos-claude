import pytest
from unittest.mock import MagicMock


def _mock_sb():
    return MagicMock()


# ---- get_metrics ----

def test_get_metrics_returns_expected_keys(mocker):
    from services.admin_service import get_metrics
    mock_sb = _mock_sb()
    # members total
    mock_sb.table().select().execute.return_value.data = [
        {"plan": "free", "status": "active"},
        {"plan": "vip",  "status": "active"},
        {"plan": "free", "status": "inactive"},
    ]
    # clicks this week
    mock_sb.table().select().gte().execute.return_value.data = [{}] * 5
    # deals by status
    mock_sb.table().select().eq().execute.return_value.data = [{}] * 3
    # alerts active
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)

    result = get_metrics()
    assert "members" in result
    assert "deals" in result
    assert "engagement" in result
    assert "alerts" in result


# ---- list_members ----

def test_list_members_returns_list(mocker):
    from services.admin_service import list_members
    mock_sb = _mock_sb()
    mock_sb.table().select().order().range().execute.return_value.data = [
        {"id": "m1", "phone_enc": "enc", "name_enc": "enc2", "plan": "free", "status": "active", "points": 100}
    ]
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)
    mocker.patch("services.admin_service._decrypt", return_value="decrypted")

    result = list_members()
    assert isinstance(result, list)
    assert len(result) == 1


# ---- set_member_status ----

def test_set_member_status_returns_true(mocker):
    from services.admin_service import set_member_status
    mock_sb = _mock_sb()
    mock_sb.table().update().eq().execute.return_value.data = [{"id": "m1"}]
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)

    result = set_member_status("m1", "banned")
    assert result is True


def test_set_member_status_invalid_raises(mocker):
    from services.admin_service import set_member_status
    mocker.patch("services.admin_service._supabase", return_value=_mock_sb())

    with pytest.raises(ValueError, match="Status inválido"):
        set_member_status("m1", "suspended")


# ---- approve_deal / reject_deal ----

def test_approve_deal_returns_true(mocker):
    from services.admin_service import approve_deal
    mock_sb = _mock_sb()
    mock_sb.table().update().eq().execute.return_value.data = [{"id": "d1"}]
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)

    assert approve_deal("d1") is True


def test_reject_deal_returns_true(mocker):
    from services.admin_service import reject_deal
    mock_sb = _mock_sb()
    mock_sb.table().update().eq().execute.return_value.data = [{"id": "d1"}]
    mocker.patch("services.admin_service._supabase", return_value=mock_sb)

    assert reject_deal("d1") is True
