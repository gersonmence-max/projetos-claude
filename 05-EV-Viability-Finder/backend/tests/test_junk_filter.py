# backend/tests/test_junk_filter.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from filters import is_junk_property


def test_right_of_way_e_junk():
    assert is_junk_property({"address": "Right of Way Lot 5, AR"}) is True


def test_easement_e_junk():
    assert is_junk_property({"address": "123 easement blvd"}) is True


def test_preco_muito_baixo_e_junk():
    assert is_junk_property({"price": 10.0, "address": "123 Main St"}) is True


def test_preco_25_nao_e_junk():
    assert is_junk_property({"price": 25.0, "address": "123 Main St"}) is False


def test_acres_minimo_e_junk():
    # 0.09 < 0.10 → junk
    assert is_junk_property({"acres": 0.09, "address": "123 Main St"}) is True


def test_acres_limite_nao_e_junk():
    # 0.10 >= 0.10 → not junk
    assert is_junk_property({"acres": 0.10, "address": "123 Main St"}) is False


def test_acres_zero_nao_filtrado():
    # Acreage=0 significa desconhecido (COSL urban) — não é junk por falta de dados
    assert is_junk_property({"acres": 0.0, "address": "123 Main St"}) is False


def test_fema_ve_e_junk():
    assert is_junk_property({"fema_zone": "VE", "address": "123 Main St"}) is True


def test_fema_ae_nao_e_junk():
    # AE é planície de inundação mas não é junk automático
    assert is_junk_property({"fema_zone": "AE", "address": "123 Main St"}) is False


def test_propriedade_normal_nao_e_junk():
    assert is_junk_property({
        "address": "456 Oak Ave, Little Rock, AR",
        "price": 500.0,
        "acres": 0.5,
        "fema_zone": "X",
    }) is False


def test_parcel_id_row_e_junk():
    assert is_junk_property({"parcel_id": "ROW-1234", "address": "Main St"}) is True
