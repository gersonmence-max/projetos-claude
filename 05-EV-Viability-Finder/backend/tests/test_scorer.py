# backend/tests/test_scorer.py
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scorer import calculate_score


def test_score_desconto_alto_pontua_bem():
    prop = {"discount_pct": 95, "price": 500}
    assert calculate_score(prop) >= 50.0


def test_score_desconto_alto_com_populacao_alta():
    prop = {"discount_pct": 95, "price": 500, "population": 80_000, "median_hh_income": 70_000}
    assert calculate_score(prop) >= 70.0


def test_score_sem_desconto_sem_dados_retorna_neutro():
    # Sem desconto e sem dados FEMA retorna 5.0 (FEMA neutro)
    assert calculate_score({}) == 5.0


def test_score_sem_desconto_sem_penalidade():
    # Nova scorer não tem penalidades. Sem desconto + sem FEMA = 5.0 (FEMA neutro)
    prop = {"price": 5_000, "discount_pct": 0}
    score = calculate_score(prop)
    assert score == 5.0


def test_score_sempre_entre_0_e_100():
    prop = {"discount_pct": 999, "price": 1, "fema_zone": "X",
            "population": 999_999, "median_hh_income": 999_999}
    assert 0.0 <= calculate_score(prop) <= 100.0


def test_score_maior_desconto_maior_score():
    alto = {"discount_pct": 90, "price": 500}
    baixo = {"discount_pct": 30, "price": 500}
    assert calculate_score(alto) > calculate_score(baixo)


def test_score_fema_x_adiciona_pontos():
    base = {"discount_pct": 50, "price": 1000}
    com_fema = {**base, "fema_zone": "X"}
    assert calculate_score(com_fema) > calculate_score(base)


def test_score_fema_ae_penalidade():
    base = {"discount_pct": 50, "price": 1000}
    ae   = {**base, "fema_zone": "AE"}
    assert calculate_score(ae) < calculate_score(base)


def test_score_populacao_grande_adiciona_pontos():
    base    = {"discount_pct": 50, "price": 1000}
    grande  = {**base, "population": 100_000, "median_hh_income": 50_000}
    assert calculate_score(grande) > calculate_score(base)


def test_score_populacao_pequena_penalidade():
    base     = {"discount_pct": 50, "price": 1000, "population": 50_000}
    pequena  = {"discount_pct": 50, "price": 1000, "population": 1_000}
    assert calculate_score(base) > calculate_score(pequena)


def test_score_fema_zone_x500_pontos():
    # Nova scorer não usa has_road_access/utilities_available. Testamos X500 FEMA.
    base = {"discount_pct": 50, "price": 1000}
    com  = {**base, "fema_zone": "X500"}
    assert calculate_score(com) > calculate_score(base)
