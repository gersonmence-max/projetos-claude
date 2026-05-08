# backend/tests/test_classifier.py
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from classifier import classify_property


def _c(**kw):
    return classify_property(kw)["classification"]


# ── FORTE ────────────────────────────────────────────────────────────────────

def test_forte_todos_criterios():
    r = _c(score=80, discount_pct=60, population=20_000, fema_zone="X")
    assert r == "FORTE"


def test_forte_exige_score_75():
    r = _c(score=74, discount_pct=60, population=20_000, fema_zone="X")
    assert r != "FORTE"


def test_forte_exige_fema_safe():
    r = _c(score=80, discount_pct=60, population=20_000, fema_zone="C")
    assert r != "FORTE"


def test_forte_exige_populacao_15k():
    r = _c(score=80, discount_pct=60, population=14_000, fema_zone="X")
    assert r != "FORTE"


def test_forte_exige_desconto_50():
    r = _c(score=80, discount_pct=49, population=20_000, fema_zone="X")
    assert r != "FORTE"


# ── MODERADO ─────────────────────────────────────────────────────────────────

def test_moderado_dois_de_tres_criterios():
    r = _c(score=60, discount_pct=30, population=20_000, fema_zone="X")
    assert r == "MODERADO"


def test_moderado_exige_score_55():
    r = _c(score=54, discount_pct=60, population=20_000, fema_zone="X")
    assert r != "MODERADO"


def test_moderado_fema_b_conta_como_safe():
    r = _c(score=60, discount_pct=30, population=20_000, fema_zone="B")
    assert r == "MODERADO"


# ── FRACO ────────────────────────────────────────────────────────────────────

def test_fraco_apenas_um_criterio():
    r = _c(score=56, discount_pct=60, population=5_000, fema_zone="C")
    assert r == "FRACO"


def test_fraco_score_baixo():
    r = _c(score=30, discount_pct=20, population=10_000, fema_zone="X")
    assert r == "FRACO"


def test_sem_dados_retorna_fraco():
    r = _c(score=0)
    assert r == "FRACO"


# ── EVITAR ───────────────────────────────────────────────────────────────────

def test_evitar_fema_ae_score_baixo():
    r = _c(score=60, discount_pct=70, population=30_000, fema_zone="AE")
    assert r == "EVITAR"


def test_evitar_fema_a_score_baixo():
    r = _c(score=50, discount_pct=80, population=50_000, fema_zone="A")
    assert r == "EVITAR"


def test_nao_evitar_fema_ae_score_alto():
    r = _c(score=65, discount_pct=80, population=50_000, fema_zone="AE")
    assert r != "EVITAR"


def test_evitar_populacao_pequena_score_baixo():
    r = _c(score=60, discount_pct=70, population=3_000, fema_zone="X")
    assert r == "EVITAR"


def test_nao_evitar_populacao_pequena_score_alto():
    r = _c(score=75, discount_pct=80, population=3_000, fema_zone="X")
    assert r != "EVITAR"
