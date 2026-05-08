#!/usr/bin/env python3
# ============================================================
#  painel.py  |  http://localhost:8080
# ============================================================

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime

import config
from scanner import load_db, save_db, run_scan, run_scan_mock, can_scan
from sender import send_deal_by_id, auto_send_approved

log = logging.getLogger("painel")


def score_color(s):
    if s >= 80: return "#22c55e"
    if s >= 65: return "#84cc16"
    if s >= 50: return "#f59e0b"
    return "#f97316"

def status_cfg(st):
    return {
        "pending":  ("#f59e0b", "Pendente"),
        "approved": ("#22c55e", "Aprovado"),
        "rejected": ("#ef4444", "Rejeitado"),
        "sent":     ("#818cf8", "Enviado"),
    }.get(st, ("#888", st))


def render_card(deal):
    sc       = deal.get("score", 0)
    col      = score_color(sc)
    stc, stl = status_cfg(deal["status"])
    pct      = deal.get("discount_pct", 0)
    rev      = f"{deal['reviews']:,}" if deal.get("reviews") else "—"
    rat      = f"{'★'*int(deal.get('rating',0))} {deal.get('rating','')}" if deal.get("rating") else "—"
    ctx      = deal.get("price_context")
    auto     = deal.get("auto_approved", False)

    # Badge de contexto de preco
    ctx_html = ""
    if ctx:
        ctx_html = f'<div class="ctx-badge">{ctx}</div>'

    # Badge auto-aprovado
    auto_html = ""
    if auto and deal["status"] == "approved":
        auto_html = '<span class="auto-badge">auto</span>'

    actions = ""
    if deal["status"] == "pending":
        actions = f"""
        <button onclick="act('{deal['id']}','approve')" class="btn-approve">Aprovar</button>
        <button onclick="act('{deal['id']}','reject')"  class="btn-reject">Rejeitar</button>"""
    elif deal["status"] == "approved":
        actions = f"""
        <button onclick="act('{deal['id']}','send')"   class="btn-send">Enviar agora</button>
        <button onclick="act('{deal['id']}','reject')" class="btn-reject">Rejeitar</button>"""

    arc = int(sc)
    return f"""
<div class="card" id="c-{deal['id']}">
  <div class="card-top">
    <div class="score-ring" style="--c:{col}">
      <svg viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--surface2)" stroke-width="3"/>
        <circle cx="18" cy="18" r="15.9" fill="none" stroke="{col}" stroke-width="3"
          stroke-dasharray="{arc} {100-arc}" stroke-dashoffset="25" stroke-linecap="round"/>
      </svg>
      <span>{sc}</span>
    </div>
    <div class="card-badges">
      <span class="badge-pct">-{pct}%</span>
      <span class="badge-status" style="color:{stc};border-color:{stc}40;background:{stc}12">{stl} {auto_html}</span>
      <span class="badge-quality" style="color:{col}">{deal.get('score_label','')}</span>
    </div>
  </div>
  {ctx_html}
  <div class="card-title">{deal['title'][:85]}</div>
  <div class="card-price">
    <span class="price-now">${deal['price_now']:.2f}</span>
    <span class="price-was">${deal.get('price_was',0):.2f}</span>
  </div>
  <div class="card-meta">
    <span>{rat}</span>
    <span>{rev} rev</span>
    <span>{deal.get('query','')[:28]}</span>
  </div>
  <div class="card-actions">
    {actions}
    <a href="{deal['affiliate_url']}" target="_blank" class="btn-link">Ver na Amazon</a>
  </div>
</div>"""


def render_page(flt="all", sort="score"):
    db     = load_db()
    counts = {s: sum(1 for d in db if d["status"] == s)
              for s in ("pending","approved","sent","rejected")}
    counts["all"] = len(db)

    # Cache info
    ok, cache_msg = can_scan()
    cache_info = "" if ok else f'<div class="cache-info">{cache_msg}</div>'

    # Auto-aprovados stats
    auto_count = sum(1 for d in db if d.get("auto_approved") and d["status"] in ("approved","sent"))

    shown = db if flt == "all" else [d for d in db if d["status"] == flt]
    key_map = {"score": lambda d: -d.get("score",0),
               "discount": lambda d: -d.get("discount_pct",0),
               "reviews": lambda d: -d.get("reviews",0),
               "price": lambda d: d.get("price_now",999)}
    shown.sort(key=key_map.get(sort, key_map["score"]))

    cards = "".join(render_card(d) for d in shown) or \
            '<div class="empty">Nenhum deal. Clique em "Scan Mock" para testar.</div>'

    def tab(s, label):
        a = "active" if flt == s else ""
        return f'<button class="tab {a}" onclick="setFilter(\'{s}\')">{label} <b>{counts.get(s,0)}</b></button>'

    def srt(s, label):
        a = "active" if sort == s else ""
        return f'<button class="sort-btn {a}" onclick="setSort(\'{s}\')">{label}</button>'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BrasilDeals — Painel</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:#0b1410;--surface:#162018;--surface2:#1e2e22;--surface3:#263329;--border:rgba(255,255,255,0.07);--text:#edf0ec;--muted:rgba(237,240,236,0.45);--green:#22c55e;--green-d:#16a34a;--radius:12px}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}
header{{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:20;gap:12px;flex-wrap:wrap}}
.logo{{font-weight:700;font-size:16px;color:var(--green);letter-spacing:.5px}}
.hbtns{{display:flex;gap:8px;flex-wrap:wrap}}
.hbtn{{padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:all .18s;white-space:nowrap}}
.hbtn-scan{{background:var(--green);color:#000}}.hbtn-scan:hover{{background:var(--green-d)}}
.hbtn-mock{{background:var(--surface2);color:var(--muted);border:1px solid var(--border)}}.hbtn-mock:hover{{color:var(--text)}}
.hbtn-send{{background:#6366f1;color:#fff}}.hbtn-send:hover{{background:#4f46e5}}
.cache-info{{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.25);border-radius:8px;padding:8px 16px;font-size:12px;color:#fbbf24;margin:0 28px 0}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;padding:20px 28px}}
.stat{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 18px}}
.stat-n{{font-size:28px;font-weight:700;line-height:1;margin-bottom:3px}}
.stat-l{{font-size:11px;color:var(--muted)}}
.sp .stat-n{{color:#f59e0b}}.sa .stat-n{{color:#22c55e}}.ss .stat-n{{color:#818cf8}}.sr .stat-n{{color:#ef4444}}.saa .stat-n{{color:#06b6d4}}
.toolbar{{padding:0 28px 16px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.tab{{background:transparent;border:1px solid var(--border);border-radius:8px;padding:6px 12px;color:var(--muted);cursor:pointer;font-size:12px;display:flex;align-items:center;gap:5px;transition:all .15s}}
.tab b{{background:var(--surface2);border-radius:4px;padding:1px 5px;font-size:10px}}
.tab.active,.tab:hover{{background:var(--surface);color:var(--text);border-color:rgba(255,255,255,.15)}}
.divider{{width:1px;height:20px;background:var(--border);margin:0 4px}}
.sort-btn{{background:transparent;border:1px solid var(--border);border-radius:6px;padding:5px 10px;color:var(--muted);cursor:pointer;font-size:11px;transition:all .15s}}
.sort-btn.active,.sort-btn:hover{{background:var(--surface2);color:var(--text)}}
.sort-label{{font-size:11px;color:var(--muted);margin-left:4px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px;padding:0 28px 32px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px;display:flex;flex-direction:column;gap:10px;transition:border-color .2s}}
.card:hover{{border-color:rgba(255,255,255,.14)}}
.card-top{{display:flex;align-items:center;gap:12px}}
.score-ring{{position:relative;width:48px;height:48px;flex-shrink:0}}
.score-ring svg{{width:100%;height:100%;transform:rotate(-90deg)}}
.score-ring span{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:var(--c,#fff)}}
.card-badges{{display:flex;flex-wrap:wrap;gap:5px;align-items:center}}
.badge-pct{{background:rgba(34,197,94,.15);color:#4ade80;border:1px solid rgba(34,197,94,.25);border-radius:5px;padding:2px 8px;font-size:12px;font-weight:700}}
.badge-status{{border:1px solid;border-radius:5px;padding:2px 8px;font-size:11px;font-weight:500;display:flex;align-items:center;gap:4px}}
.badge-quality{{font-size:11px;font-weight:600}}
.auto-badge{{background:rgba(6,182,212,.15);color:#22d3ee;border:1px solid rgba(6,182,212,.25);border-radius:3px;padding:1px 5px;font-size:10px;font-weight:600}}
.ctx-badge{{background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.2);border-radius:6px;padding:5px 10px;font-size:11px;font-weight:600;color:#fbbf24;letter-spacing:.3px}}
.card-title{{font-size:13px;font-weight:500;line-height:1.45}}
.card-price{{display:flex;align-items:baseline;gap:10px}}
.price-now{{font-size:22px;font-weight:700;color:#4ade80}}
.price-was{{font-size:13px;color:var(--muted);text-decoration:line-through}}
.card-meta{{display:flex;flex-wrap:wrap;gap:6px}}
.card-meta span{{font-size:11px;color:var(--muted);background:var(--surface2);padding:3px 7px;border-radius:5px}}
.card-actions{{display:flex;gap:7px;flex-wrap:wrap;margin-top:2px}}
.btn-approve{{padding:6px 13px;background:#22c55e;color:#000;border:none;border-radius:7px;cursor:pointer;font-size:12px;font-weight:600;transition:opacity .15s}}
.btn-approve:hover{{opacity:.85}}
.btn-reject{{padding:6px 13px;background:rgba(239,68,68,.12);color:#fca5a5;border:1px solid rgba(239,68,68,.25);border-radius:7px;cursor:pointer;font-size:12px;font-weight:600}}
.btn-reject:hover{{background:rgba(239,68,68,.22)}}
.btn-send{{padding:6px 13px;background:#6366f1;color:#fff;border:none;border-radius:7px;cursor:pointer;font-size:12px;font-weight:600;transition:opacity .15s}}
.btn-send:hover{{opacity:.85}}
.btn-link{{padding:6px 12px;border-radius:7px;border:1px solid var(--border);color:var(--muted);font-size:12px;text-decoration:none}}
.btn-link:hover{{color:var(--text);border-color:rgba(255,255,255,.2)}}
.empty{{grid-column:1/-1;text-align:center;color:var(--muted);padding:60px;font-size:15px}}
.toast{{position:fixed;bottom:20px;right:20px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:13px 18px;font-size:13px;z-index:99;opacity:0;transition:opacity .3s;pointer-events:none;max-width:300px}}
.toast.show{{opacity:1}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.spin{{display:inline-block;width:13px;height:13px;border:2px solid rgba(0,0,0,.3);border-top-color:#000;border-radius:50%;animation:spin .6s linear infinite;margin-right:5px;vertical-align:middle}}
</style>
</head>
<body>
<header>
  <div class="logo">BrasilDeals — Painel</div>
  <div class="hbtns">
    <button class="hbtn hbtn-mock" onclick="scan('mock')">Scan Mock</button>
    <button class="hbtn hbtn-scan" id="btn-scan" onclick="scan('real')">Varrer Amazon</button>
    <button class="hbtn hbtn-send" onclick="sendAll()">Enviar Aprovados</button>
  </div>
</header>

{cache_info}

<div class="stats">
  <div class="stat sp"><div class="stat-n">{counts['pending']}</div><div class="stat-l">Pendentes</div></div>
  <div class="stat sa"><div class="stat-n">{counts['approved']}</div><div class="stat-l">Aprovados</div></div>
  <div class="stat ss"><div class="stat-n">{counts['sent']}</div><div class="stat-l">Enviados</div></div>
  <div class="stat sr"><div class="stat-n">{counts['rejected']}</div><div class="stat-l">Rejeitados</div></div>
  <div class="stat saa"><div class="stat-n">{auto_count}</div><div class="stat-l">Auto-aprovados</div></div>
</div>

<div class="toolbar">
  {tab('all','Todos')}
  {tab('pending','Pendentes')}
  {tab('approved','Aprovados')}
  {tab('sent','Enviados')}
  {tab('rejected','Rejeitados')}
  <div class="divider"></div>
  <span class="sort-label">Ordenar:</span>
  {srt('score','Score')}
  {srt('discount','Desconto')}
  {srt('reviews','Reviews')}
  {srt('price','Preco')}
</div>

<div class="grid">{cards}</div>
<div class="toast" id="toast"></div>

<script>
const qs = new URLSearchParams(location.search);
function setFilter(f){{qs.set('filter',f);qs.delete('sort');location.search=qs.toString()}}
function setSort(s){{qs.set('sort',s);location.search=qs.toString()}}

function toast(msg,ok=true){{
  const t=document.getElementById('toast');
  t.textContent=msg;
  t.style.borderColor=ok?'rgba(34,197,94,.3)':'rgba(239,68,68,.3)';
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2800);
}}

async function act(id,type){{
  const card=document.getElementById('c-'+id);
  const r=await fetch('/action',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id,type}})}});
  const d=await r.json();
  toast(d.msg,d.ok);
  if(d.ok){{if(card)card.style.opacity='.3';setTimeout(()=>location.reload(),700);}}
}}

async function scan(mode){{
  const btn=document.getElementById('btn-scan');
  btn.innerHTML='<span class="spin"></span>Varrendo...';
  btn.disabled=true;
  toast('Varredura iniciada...');
  const r=await fetch('/scan?mode='+mode);
  const d=await r.json();
  btn.innerHTML='Varrer Amazon';
  btn.disabled=false;
  toast(d.msg,d.ok);
  if(d.ok)setTimeout(()=>location.reload(),900);
}}

async function sendAll(){{
  toast('Enviando com delay anti-spam...');
  const r=await fetch('/send-all');
  const d=await r.json();
  toast(d.msg,d.ok);
  if(d.ok)setTimeout(()=>location.reload(),900);
}}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, data, code=200):
        b = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _html(self, html):
        b = html.encode()
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p  = urlparse(self.path)
        qs = parse_qs(p.query)

        if p.path == "/":
            self._html(render_page(
                qs.get("filter",["all"])[0],
                qs.get("sort",["score"])[0]
            ))

        elif p.path == "/scan":
            mode = qs.get("mode",["real"])[0]
            try:
                if mode == "mock":
                    deals = run_scan_mock()
                    self._json({"ok":True,"msg":f"{len(deals)} deals mock carregados."})
                else:
                    deals, err = run_scan()
                    if err:
                        self._json({"ok":False,"msg":err})
                    else:
                        auto = sum(1 for d in deals if d.get("auto_approved"))
                        self._json({"ok":True,"msg":f"{len(deals)} novos deals ({auto} auto-aprovados)."})
            except Exception as e:
                self._json({"ok":False,"msg":str(e)})

        elif p.path == "/send-all":
            try:
                n = auto_send_approved()
                self._json({"ok":True,"msg":f"{n} deals enviados (com delay anti-spam)."})
            except Exception as e:
                self._json({"ok":False,"msg":str(e)})

        else:
            self._json({"error":"not found"},404)

    def do_POST(self):
        if self.path != "/action":
            self._json({"error":"not found"},404); return

        body    = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))))
        deal_id = body.get("id")
        action  = body.get("type")

        if action == "send":
            ok, msg = send_deal_by_id(deal_id)
            self._json({"ok":ok,"msg":msg}); return

        db = load_db()
        for deal in db:
            if deal["id"] == deal_id:
                if action == "approve":
                    deal["status"] = "approved"
                    msg = "Aprovado."
                elif action == "reject":
                    deal["status"] = "rejected"
                    msg = "Rejeitado."
                else:
                    self._json({"ok":False,"msg":"Acao invalida."}); return
                save_db(db)
                self._json({"ok":True,"msg":msg}); return

        self._json({"ok":False,"msg":"Deal nao encontrado."})


if __name__ == "__main__":
    import sys
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"\n  Painel: http://localhost:{port}\n")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
