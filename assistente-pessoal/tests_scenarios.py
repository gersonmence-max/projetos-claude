"""
tests_scenarios.py — Ziontec Bot
108 testes: normalizacao, interceptadores, validador, pendencias, undo.
"""
import re, sys, datetime
sys.path.insert(0, '.')

from core import (
    normalizar_hora, calcular_horas_trabalhadas, hora_e_ambigua,
    normalizar_socio, extrair_numero, calcular_data_prazo,
    interceptar_correcao_horas, interceptar_periodo_incompleto,
    validar_acao, ValidationError,
    interceptar_despesa, interceptar_pagamento,
    resolver_pendencia, criar_pendencia, set_obras_ativas,
    registrar_undo, pop_undo,
)

VERDE = "\033[92m✅"
VERMELHO = "\033[91m❌"
RESET = "\033[0m"
passed = failed = 0

def check(desc, resultado, esperado):
    global passed, failed
    ok = resultado == esperado
    print(f"{''.join([VERDE if ok else VERMELHO])} {desc}{RESET}")
    if not ok:
        print(f"   Esperado : {repr(esperado)}")
        print(f"   Obtido   : {repr(resultado)}")
        failed += 1
    else:
        passed += 1

print("\n=== NORMALIZACAO DE HORARIO ===")
check("8          -> 08:00", normalizar_hora("8"),          "08:00")
check("8h         -> 08:00", normalizar_hora("8h"),         "08:00")
check("8:00       -> 08:00", normalizar_hora("8:00"),       "08:00")
check("8am        -> 08:00", normalizar_hora("8am"),        "08:00")
check("8 da manha -> 08:00", normalizar_hora("8 da manha"), "08:00")
check("8pm        -> 20:00", normalizar_hora("8pm"),        "20:00")
check("8 da noite -> 20:00", normalizar_hora("8 da noite"), "20:00")
check("20h        -> 20:00", normalizar_hora("20h"),        "20:00")
check("20         -> 20:00", normalizar_hora("20"),         "20:00")
check("meio dia   -> 12:00", normalizar_hora("meio dia"),   "12:00")
check("meia noite -> 00:00", normalizar_hora("meia noite"), "00:00")
check("16:30      -> 16:30", normalizar_hora("16:30"),      "16:30")

print("\n=== CALCULO DE HORAS ===")
h,i,f,a = calcular_horas_trabalhadas("8am","16h")
check("8am-16h = 8h",        h, 8.0)
check("8am-16h nao ambiguo", a, False)
h,i,f,a = calcular_horas_trabalhadas("7h","15h")
check("7h-15h = 8h",         h, 8.0)
h,i,f,a = calcular_horas_trabalhadas("8","8")
check("das 8 as 8 = 12h (regra obra)", h,   12.0)
check("das 8 as 8 ini = 08:00",        i, "08:00")
check("das 8 as 8 fim = 20:00",        f, "20:00")
check("das 8 as 8 nao ambiguo",        a, False)
h,i,f,a = calcular_horas_trabalhadas("8am","8pm")
check("8am-8pm = 12h explicito",       h, 12.0)
h,i,f,a = calcular_horas_trabalhadas("19","4")
check("19h-4h sem indicador = ambiguo",  a, True)
check("19h-4h sem indicador h=None",     h, None)

print("\n=== AMBIGUIDADE AM/PM ===")
check("8 sozinho          -> ambiguo",     hora_e_ambigua("8"),          True)
check("11 sozinho         -> ambiguo",     hora_e_ambigua("11"),         True)
check("8h                 -> nao ambiguo", hora_e_ambigua("8h"),         False)
check("8am                -> nao ambiguo", hora_e_ambigua("8am"),        False)
check("20h                -> nao ambiguo", hora_e_ambigua("20h"),        False)
check("8 da manha         -> nao ambiguo", hora_e_ambigua("8 da manha"), False)
check("13 (>=13)          -> nao ambiguo", hora_e_ambigua("13"),         False)
check("8 ctx=manha        -> nao ambiguo", hora_e_ambigua("8","trabalhei de manha"), False)

print("\n=== NORMALIZACAO DE SOCIO ===")
check("carlos no texto     -> Carlos", normalizar_socio("adicione 10h pro carlos"), "Carlos")
check("Carlos maiusculo    -> Carlos", normalizar_socio("Carlos trabalhou"),         "Carlos")
check("gerson no texto     -> Gerson", normalizar_socio("gerson foi"),              "Gerson")
check("sem nome fallback G -> Gerson", normalizar_socio("10 horas","Gerson"),       "Gerson")
check("sem nome fallback C -> Carlos", normalizar_socio("na randolph","Carlos"),    "Carlos")

print("\n=== INTERCEPTADOR: CORRECAO DE HORAS ===")
r = interceptar_correcao_horas("remova 10 horas do carlos na randolph","Gerson")
check("remova X horas detectado",      r is not None, True)
check("remova: socio = Carlos",        r.get("socio") if r else "", "Carlos")
check("remova: acao = corrigir_horas", r.get("acao")  if r else "", "corrigir_horas")
r = interceptar_correcao_horas("carlos fez 30 horas esse mes","Gerson")
check("fez 30h detectado",             r is not None,              True)
check("fez 30h: total = 30",           r.get("total") if r else 0, 30.0)
check("fez 30h: socio = Carlos",       r.get("socio") if r else "", "Carlos")
r = interceptar_correcao_horas("carlos fez 30 horas esse mes","Gerson")
check("sem obra no texto -> obra = ''", r.get("obra") if r else "X", "")
r = interceptar_correcao_horas("trabalhei 8h na randolph","Gerson")
check("registrar normal nao intercepta", r, None)
r = interceptar_correcao_horas("adicione 10 horas pro carlos","Gerson")
check("adicionar nao intercepta",        r, None)

print("\n=== GAP: OBRAS COM NOMES SIMILARES ===")
def buscar_obra_mock(nome, lista):
    nl = nome.lower().strip()
    for o in lista:
        if o.lower().strip() == nl: return [o]
    return [o for o in lista if nl in o.lower() or o.lower() in nl]

obras_mock = ["Randolph","Randolph Service","Milton","Holliston"]
r = buscar_obra_mock("Randolph", obras_mock)
check("Randolph exato -> 1 resultado",         len(r)==1, True)
check("Randolph exato -> resultado correto",   r[0] if r else "", "Randolph")
r = buscar_obra_mock("Randolph Service", obras_mock)
check("Randolph Service exato -> 1 resultado", len(r)==1, True)
r = buscar_obra_mock("randolph", obras_mock)
check("randolph lower -> encontra Randolph",   "Randolph" in r, True)

print("\n=== GAP: PERIODO INCOMPLETO ===")
r = interceptar_periodo_incompleto("trabalhei ate as 18h")
check("ate as 18h detectado",              r is not None, True)
check("ate as 18h: tipo correto",          r.get("tipo") if r else "", "periodo_incompleto")
r = interceptar_periodo_incompleto("sai as 17h")
check("sai as 17h detectado",              r is not None, True)
r = interceptar_periodo_incompleto("cheguei as 8h")
check("cheguei as 8h detectado",           r is not None, True)
r = interceptar_periodo_incompleto("trabalhei 8h na randolph")
check("8h direto nao intercepta",          r, None)
r = interceptar_periodo_incompleto("trabalhei das 8 as 16")
check("intervalo completo nao intercepta", r, None)

print("\n=== DATAS E PRAZOS ===")
hoje = datetime.datetime.now()
from datetime import timedelta
r = calcular_data_prazo("2 semanas")
check("2 semanas = data correta", r, (hoje+timedelta(weeks=2)).strftime("%d/%m/%Y"))
r = calcular_data_prazo("14 dias")
check("14 dias = data correta",   r, (hoje+timedelta(days=14)).strftime("%d/%m/%Y"))
check("nao definido = Indefinido", calcular_data_prazo("nao definido"), "Indefinido")
check("nd = Indefinido",           calcular_data_prazo("nd"),           "Indefinido")

print("\n=== EXTRACAO DE VALORES ===")
check("$1500 -> 1500", extrair_numero("$1500"),  1500.0)
check("1.500 -> 1.5",  extrair_numero("1.500"),  1.5)
check("1500 -> 1500",  extrair_numero("1500"),   1500.0)
check("nao sei -> 0",  extrair_numero("nao sei"), 0)
check("zero -> 0",     extrair_numero("zero"),    0)
check("vazio -> 0",    extrair_numero(""),        0)

print("\n=== VALIDADOR CENTRAL ===")
try:
    validar_acao({"acao":"registrar_horas","socio":"Carlos","horas":8,"obra":"Randolph"},"carlos trabalhou 8h na randolph")
    check("socio correto nao bloqueia", True, True)
except: check("socio correto nao bloqueia", False, True)

try:
    validar_acao({"acao":"registrar_horas","socio":"Gerson","horas":8,"obra":"Randolph"},"carlos trabalhou 8h na randolph")
    check("socio errado levanta ValueError", False, True)
except ValueError: check("socio errado levanta ValueError", True, True)
except: check("socio errado levanta ValueError", False, True)

try:
    validar_acao({"acao":"registrar_horas","socio":"Carlos","horas":8,"obra":""},"carlos trabalhou 8h")
    check("obra vazia levanta ValidationError", False, True)
except ValidationError as ve:
    check("obra vazia levanta ValidationError", True, True)
    check("obra vazia: pergunta correta", "obra" in ve.pergunta.lower(), True)

try:
    validar_acao({"acao":"registrar_despesa","socio":"Gerson","valor":0,"obra":"Randolph","categoria":"Material","descricao":"home depot"},"gastei 120 no home depot")
    check("valor 0 com numero levanta ValidationError", False, True)
except ValidationError: check("valor 0 com numero levanta ValidationError", True, True)

try:
    validar_acao({"acao":"registrar_horas","socio":"Carlos","horas":-5,"obra":"Randolph"},"")
    check("horas negativas levanta ValueError", False, True)
except ValueError: check("horas negativas levanta ValueError", True, True)

try:
    validar_acao({"acao":"registrar_despesa","socio":"Gerson","valor":120,"obra":"Randolph","categoria":"Material","descricao":"home depot"},"gastei 120 no home depot na randolph")
    check("payload correto passa validacao", True, True)
except: check("payload correto passa validacao", False, True)

print("\n=== INTERCEPTADOR: DESPESA ===")
r = interceptar_despesa("gastei 120 no home depot na randolph","Gerson")
check("gastei 120 home depot detectado",      r is not None, True)
check("gastei 120: valor = 120",              r.get("valor") if r else 0, 120.0)
check("gastei 120: categoria = Material",     r.get("categoria") if r else "", "Material")
check("gastei 120: acao = registrar_despesa", r.get("acao") if r else "", "registrar_despesa")
r = interceptar_despesa("home depot 90 na randolph","Gerson")
check("home depot 90 detectado",              r is not None, True)
check("home depot 90: valor = 90",            r.get("valor") if r else 0, 90.0)
r = interceptar_despesa("almoco 25","Gerson")
check("almoco 25 detectado",                  r is not None, True)
check("almoco 25: categoria = Alimentacao",   r.get("categoria") if r else "", "Alimentacao")
r = interceptar_despesa("gasolina 50","Carlos")
check("gasolina 50 detectado",                r is not None, True)
check("gasolina 50: categoria = Combustivel", r.get("categoria") if r else "", "Combustivel")
check("gasolina: desconto = Carlos",          r.get("desconto") if r else "", "Carlos")
r = interceptar_despesa("registra despesa de 100 de material","Gerson")
check("registra despesa nao intercepta",      r, None)

print("\n=== INTERCEPTADOR: PAGAMENTO ===")
r = interceptar_pagamento("recebi 500 da randolph", None)
check("recebi 500 detectado",                  r is not None, True)
check("recebi 500: valor = 500",               r.get("valor") if r else 0, 500.0)
check("recebi 500: acao = registrar_pagamento",r.get("acao") if r else "", "registrar_pagamento")
r = interceptar_pagamento("cliente pagou 1000", None)
check("cliente pagou 1000 detectado",          r is not None, True)
r = interceptar_pagamento("mandei material pra obra", None)
check("mensagem normal nao intercepta",        r, None)
obras_mock2 = {"randolph":{"contrato":10000,"pago":0,"cliente":"John"}}
r = interceptar_pagamento("cliente pagou metade da randolph", obras_mock2)
check("metade detectado",                      r is not None, True)
check("metade: valor = 5000",                  r.get("valor") if r else 0, 5000.0)

print("\n=== MAQUINA DE PENDENCIAS ===")
set_obras_ativas(["Randolph","Milton","Holliston"])

ud = {}
payload = {"acao":"registrar_horas","socio":"Carlos","horas":8,"obra":""}
ud['pendencia_ativa'] = criar_pendencia('pendencia_obra', payload, "Em qual obra?")
res, fw = resolver_pendencia(ud, "Randolph")
check("pendencia obra: resolveu com 'Randolph'", res is not None, True)
check("pendencia obra: obra = Randolph",         res.get('obra') if res else "", "Randolph")
check("pendencia obra: sem followup",            fw, None)
check("pendencia obra: limpa user_data",         ud.get('pendencia_ativa'), None)

ud = {}
payload = {"acao":"registrar_horas","socio":"Gerson","horas":8,"obra":"Randolph","hora_inicio":""}
ud['pendencia_ativa'] = criar_pendencia('pendencia_horario', payload, "As 8 e da manha ou da noite?")
ud['pendencia_ativa']['subtipo'] = 'ambiguo'
ud['pendencia_ativa']['hora_raw'] = '8'
ud['pendencia_ativa']['campo'] = 'hora_inicio'
res, fw = resolver_pendencia(ud, "manha")
check("pendencia horario: manha resolveu",  res is not None, True)
check("pendencia horario: hora = 08:00",    res.get('hora_inicio') if res else "", "08:00")

ud = {}
ud['pendencia_ativa'] = criar_pendencia('pendencia_horario', {"acao":"registrar_horas","obra":"Randolph","hora_inicio":""}, "As 8 e da manha ou da noite?")
ud['pendencia_ativa']['subtipo'] = 'ambiguo'
ud['pendencia_ativa']['hora_raw'] = '8'
ud['pendencia_ativa']['campo'] = 'hora_inicio'
res, fw = resolver_pendencia(ud, "noite")
check("pendencia horario: noite = 20:00",   res.get('hora_inicio') if res else "", "20:00")

ud = {}
payload = {"acao":"registrar_despesa","socio":"Gerson","obra":"Randolph","valor":0}
ud['pendencia_ativa'] = criar_pendencia('pendencia_valor', payload, "Qual o valor?")
res, fw = resolver_pendencia(ud, "150")
check("pendencia valor: 150 resolveu",      res is not None, True)
check("pendencia valor: valor = 150",       res.get('valor') if res else 0, 150.0)

ud = {}
payload = {"acao":"registrar_horas","socio":"Carlos","horas":8,"obra":""}
ud['pendencia_ativa'] = criar_pendencia('pendencia_obra', payload, "Em qual obra?")
res, fw = resolver_pendencia(ud, "nao sei")
check("pendencia obra invalida: nao resolve",    res, None)
check("pendencia obra invalida: retorna followup", fw is not None, True)

print("\n=== UNDO STACK ===")
ud = {}
registrar_undo(ud,'Banco de Horas','append',row_index=5,valores=['22/02/2026','Carlos',8,200,'08:00','16:00','Randolph'])
entrada = pop_undo(ud)
check("undo: entrada registrada",      entrada is not None, True)
check("undo: aba correta",             entrada.get('aba') if entrada else "", "Banco de Horas")
check("undo: tipo append",             entrada.get('tipo') if entrada else "", "append")
check("undo: row_index = 5",           entrada.get('row_index') if entrada else 0, 5)
check("undo: stack vazio apos pop",    pop_undo(ud), None)

ud = {}
for i in range(6):
    registrar_undo(ud,'Despesas','append',row_index=i+2,valores=[f'item{i}'])
check("undo: stack maximo 5",          len(ud.get('undo_stack',[])), 5)
check("undo: descarta o mais antigo",  ud['undo_stack'][0]['row_index'], 3)

print(f"\n{'='*45}")
total = passed + failed
print(f"Resultado: {passed}/{total} passou | {failed} falharam")
if failed == 0:
    print("\033[92mTodos os testes passaram! Bot seguro para subir.\033[0m")
else:
    print(f"\033[91m{failed} testes falharam. Corrija antes de subir.\033[0m")
sys.exit(0 if failed == 0 else 1)
