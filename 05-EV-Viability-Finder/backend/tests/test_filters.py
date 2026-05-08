# backend/tests/test_filters.py
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from filters import apply_filters, FilterConfig


def test_preco_maximo_exclui_caro():
    config = FilterConfig(max_price=300_000)
    prop = {"price": 500_000, "acres": 5, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_preco_maximo_permite_dentro_do_limite():
    config = FilterConfig(max_price=300_000)
    prop = {"price": 200_000, "acres": 5, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is True


def test_tamanho_minimo_exclui_pequeno():
    config = FilterConfig(min_acres=2.0)
    prop = {"price": 100_000, "acres": 0.5, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_tamanho_minimo_permite_grande():
    config = FilterConfig(min_acres=2.0)
    prop = {"price": 100_000, "acres": 10, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is True


def test_zona_fema_exclui_risco_inundacao():
    config = FilterConfig()
    for zone in ("A", "AE", "AO", "AH", "VE", "V"):
        prop = {"price": 100_000, "acres": 5, "fema_zone": zone}
        assert apply_filters(prop, config, regrid_available=False) is False, f"{zone} should be rejected"


def test_zona_fema_x_passa():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X"}
    assert apply_filters(prop, config, regrid_available=False) is True


def test_desconto_minimo_exclui_com_regrid():
    config = FilterConfig(min_discount_pct=10.0)
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "discount_pct": 5.0}
    assert apply_filters(prop, config, regrid_available=True) is False


def test_desconto_minimo_passa_com_regrid():
    config = FilterConfig(min_discount_pct=10.0)
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "discount_pct": 15.0}
    assert apply_filters(prop, config, regrid_available=True) is True


def test_filtros_regrid_ignorados_sem_chave():
    """Desconto e PPA são agora sempre aplicados, não gated em regrid_available."""
    config = FilterConfig(min_discount_pct=10.0, max_price_per_acre=5_000)
    prop = {
        "price": 100_000, "acres": 5, "fema_zone": "X",
        "discount_pct": 2.0, "price_per_acre": 20_000
    }
    # Com dados de desconto/ppa abaixo dos limites, propriedade é excluída
    # independentemente de regrid_available
    assert apply_filters(prop, config, regrid_available=False) is False


def test_preco_por_acre_exclui_caro_com_regrid():
    config = FilterConfig(max_price_per_acre=5_000)
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "price_per_acre": 8_000}
    assert apply_filters(prop, config, regrid_available=True) is False


def test_fema_ao_eliminado():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "AO"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_fema_ah_eliminado():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "AH"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_populacao_abaixo_2500_eliminado():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "population": 2_000}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_populacao_2500_passa():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "population": 2_500}
    assert apply_filters(prop, config, regrid_available=False) is True


def test_populacao_none_nao_eliminado():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "population": None}
    assert apply_filters(prop, config, regrid_available=False) is True
