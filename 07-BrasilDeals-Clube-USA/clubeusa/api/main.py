# ============================================================
#  api/main.py — Clube USA API
#  FastAPI com seguranca completa
#
#  Endpoints:
#  POST /auth/register        — cadastro de membro
#  POST /auth/otp/request     — solicitar OTP por WhatsApp
#  POST /auth/otp/verify      — verificar OTP e receber JWT
#  GET  /member/profile       — perfil do membro autenticado
#  GET  /member/deals         — deals da semana por categoria
#  GET  /member/referral      — link e stats de indicacao
#  POST /member/click         — registrar clique em deal
#  GET  /member/leaderboard   — ranking de pontos
#  POST /billing/subscribe    — assinar VIP via Stripe
#  POST /billing/portal       — portal de gestao da assinatura
#  POST /billing/webhook      — webhook Stripe (pagamento confirmado)
#  GET  /health               — health check
#  POST /alerts              — criar alerta de preco (plano pago)
#  GET  /alerts              — listar alertas ativos (plano pago)
#  DELETE /alerts/{id}       — cancelar alerta (plano pago)
#  POST /alerts/from-link    — criar alerta via URL Amazon (plano pago)
#  GET  /admin                   — painel admin HTML
#  GET  /admin/metrics           — snapshot do sistema (admin)
#  GET  /admin/members           — lista membros (admin)
#  GET  /admin/members/{id}      — perfil completo (admin)
#  POST /admin/members/{id}/status — alterar status (admin)
#  GET  /admin/deals             — lista deals (admin)
#  POST /admin/deals/{id}/approve — aprovar deal (admin)
#  POST /admin/deals/{id}/reject  — rejeitar deal (admin)
#  POST /admin/deals/scan        — disparar varredura (admin)
#  POST /admin/deals/send        — enviar aprovados (admin)
#  GET  /admin/alerts            — listar alertas (admin)
# ============================================================

import hmac
import os
import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, field_validator
import stripe

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("api")

# Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_VIP_PRICE_ID   = os.environ.get("STRIPE_VIP_PRICE_ID", "")   # $4.99/mes
APP_URL = os.environ.get("APP_URL", "https://clubeusa.com")


# ============================================================
#  APP
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Clube USA API iniciando...")
    yield
    log.info("Clube USA API encerrando...")

app = FastAPI(
    title="Clube USA API",
    version="1.0.0",
    docs_url=None,      # desabilita /docs em producao
    redoc_url=None,     # desabilita /redoc em producao
    lifespan=lifespan,
)

# CORS — apenas dominios autorizados
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://clubeusa.com",
        "https://www.clubeusa.com",
        "http://localhost:3000",   # dev
        "http://localhost:8080",   # dev
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ============================================================
#  MIDDLEWARES DE SEGURANCA
# ============================================================

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]          = "DENY"
    response.headers["X-XSS-Protection"]         = "1; mode=block"
    response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]        = "geolocation=(), microphone=()"
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    from utils.security import check_rate_limit, hash_ip
    ip = request.client.host if request.client else "unknown"
    ip_hash = hash_ip(ip)

    # Rate limit por IP: 60 req/min geral, 5 req/min para auth
    path = request.url.path
    if path.startswith("/auth"):
        allowed = check_rate_limit(f"auth:{ip_hash}", max_req=5, window_sec=60)
    else:
        allowed = check_rate_limit(f"api:{ip_hash}", max_req=60, window_sec=60)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Muitas requisicoes. Tente novamente em alguns instantes."}
        )
    return await call_next(request)


# ============================================================
#  AUTENTICACAO
# ============================================================

def get_current_member(authorization: str = Header(None)) -> dict:
    """Dependency — valida JWT e retorna payload do membro."""
    from utils.security import verify_token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token nao fornecido.")
    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    return payload


def require_vip(member: dict = Depends(get_current_member)) -> dict:
    """Dependency — exige plano VIP."""
    if member.get("plan") != "vip":
        raise HTTPException(status_code=403, detail="Recurso exclusivo para membros VIP.")
    return member


def require_paid_plan(member: dict = Depends(get_current_member)) -> dict:
    """Dependency — exige plano pago, sem revelar o nome do plano."""
    if member.get("plan") not in ("vip",):
        raise HTTPException(
            status_code=403,
            detail="Faça upgrade do seu plano para acessar esta funcionalidade."
        )
    return member


def require_admin(authorization: str = Header(None)) -> None:
    """Dependency — valida token de admin via ADMIN_SECRET."""
    secret = os.environ.get("ADMIN_SECRET", "")
    expected = f"Bearer {secret}"
    if not secret or not hmac.compare_digest(
        (authorization or "").encode(), expected.encode()
    ):
        raise HTTPException(status_code=401, detail="Acesso negado.")


# ============================================================
#  SCHEMAS (Pydantic — validacao de entrada)
# ============================================================

class RegisterRequest(BaseModel):
    phone:         str
    name:          Optional[str] = None
    email:         Optional[str] = None
    language:      str = "pt"
    state:         Optional[str] = None
    categories:    list[str] = ["all"]
    referral_code: Optional[str] = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        if v not in ("pt", "es"):
            raise ValueError("Idioma invalido. Use 'pt' ou 'es'.")
        return v

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v):
        valid = {"all","electronics","kitchen","baby","fitness",
                 "beauty","tools","pets","fashion","automotive","books"}
        cleaned = [c for c in v if c in valid]
        return cleaned or ["all"]


class OTPRequest(BaseModel):
    phone: str

class OTPVerify(BaseModel):
    phone: str
    otp:   str

class ClickRequest(BaseModel):
    deal_id: str


class AlertCreate(BaseModel):
    asin:         str
    target_type:  str
    target_value: float

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v):
        if v not in ("price", "percent"):
            raise ValueError("target_type deve ser 'price' ou 'percent'.")
        return v

    @field_validator("target_value")
    @classmethod
    def validate_target_value(cls, v):
        if v <= 0:
            raise ValueError("target_value deve ser maior que zero.")
        return v

    @field_validator("asin")
    @classmethod
    def validate_asin(cls, v):
        import re
        if not re.match(r'^[A-Z0-9]{10}$', v.strip().upper()):
            raise ValueError("ASIN inválido. Deve ter 10 caracteres alfanuméricos.")
        return v.strip().upper()


class AlertFromLink(BaseModel):
    url:          str
    target_type:  str
    target_value: float

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, v):
        if v not in ("price", "percent"):
            raise ValueError("target_type deve ser 'price' ou 'percent'.")
        return v

    @field_validator("target_value")
    @classmethod
    def validate_target_value(cls, v):
        if v <= 0:
            raise ValueError("target_value deve ser maior que zero.")
        return v


class StatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in ("active", "inactive", "banned"):
            raise ValueError("Status inválido. Use: active, inactive, banned.")
        return v


# ============================================================
#  OTP STORE (em producao usar Redis)
# ============================================================
_otp_store: dict = {}


# ============================================================
#  ROTAS — AUTH
# ============================================================

@app.post("/auth/register", status_code=201)
async def register(body: RegisterRequest, request: Request):
    """Cadastro de novo membro."""
    from services.member_service import register_member
    try:
        result = register_member(
            phone         = body.phone,
            name          = body.name,
            email         = body.email,
            language      = body.language,
            state         = body.state,
            categories    = body.categories,
            referral_code = body.referral_code,
            ip            = request.client.host if request.client else None,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    except Exception as e:
        log.error(f"Erro no cadastro: {e}")
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@app.post("/auth/otp/request")
async def request_otp(body: OTPRequest, request: Request):
    """
    Envia OTP de 6 digitos via WhatsApp para login.
    O membro nao precisa de senha — autentica pelo numero.
    """
    from utils.security import validate_phone, generate_otp, hash_pii
    import time

    try:
        phone = validate_phone(body.phone)
    except ValueError:
        raise HTTPException(status_code=422, detail="Telefone invalido.")

    otp = generate_otp()
    phone_hash = hash_pii(phone)

    # Guarda OTP com expiração de 10 minutos
    _otp_store[phone_hash] = {
        "otp":     otp,
        "expires": time.time() + 600,
        "attempts": 0,
    }

    # Envia via WhatsApp (ou loga em dev)
    if os.environ.get("ENVIRONMENT") == "production":
        _send_otp_whatsapp(phone, otp)
    else:
        log.info(f"[DEV] OTP para {phone}: {otp}")

    return {"message": "Codigo enviado para seu WhatsApp.", "expires_in": 600}


@app.post("/auth/otp/verify")
async def verify_otp(body: OTPVerify):
    """Verifica OTP e retorna JWT se valido."""
    from utils.security import validate_phone, hash_pii, create_token
    import time

    try:
        phone = validate_phone(body.phone)
    except ValueError:
        raise HTTPException(status_code=422, detail="Telefone invalido.")

    phone_hash = hash_pii(phone)
    record = _otp_store.get(phone_hash)

    # Validacoes de seguranca
    if not record:
        raise HTTPException(status_code=400, detail="Codigo invalido ou expirado.")
    if time.time() > record["expires"]:
        del _otp_store[phone_hash]
        raise HTTPException(status_code=400, detail="Codigo expirado. Solicite um novo.")
    if record["attempts"] >= 3:
        del _otp_store[phone_hash]
        raise HTTPException(status_code=429, detail="Muitas tentativas. Solicite novo codigo.")

    if body.otp != record["otp"]:
        _otp_store[phone_hash]["attempts"] += 1
        raise HTTPException(status_code=400, detail="Codigo incorreto.")

    # OTP valido — busca membro
    del _otp_store[phone_hash]

    from utils.security import hash_pii
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("members").select("id,plan,status").eq("phone_hash", phone_hash).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Membro nao encontrado. Cadastre-se primeiro.")

    member = result.data[0]
    if member["status"] == "banned":
        raise HTTPException(status_code=403, detail="Acesso negado.")

    token = create_token(member["id"], member["plan"])
    return {"token": token, "member_id": member["id"], "plan": member["plan"]}


# ============================================================
#  ROTAS — MEMBRO
# ============================================================

@app.get("/member/profile")
async def get_profile(member: dict = Depends(get_current_member)):
    """Perfil do membro autenticado."""
    from services.member_service import get_member_profile
    profile = get_member_profile(member["sub"])
    if not profile:
        raise HTTPException(status_code=404, detail="Membro nao encontrado.")
    return profile


@app.get("/member/deals")
async def get_deals(
    category: Optional[str] = None,
    limit: int = 20,
    member: dict = Depends(get_current_member)
):
    """
    Deals da semana filtrados por categoria.
    VIP recebe mais deals e com antecedencia.
    """
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    # VIP ve todos, free ve apenas os enviados
    if member.get("plan") == "vip":
        status_filter = ["approved", "sent"]
        limit = min(limit, 50)
    else:
        status_filter = ["sent"]
        limit = min(limit, 20)

    query = (
        sb.table("deals")
        .select("id,title,price_now,price_was,discount_pct,rating,reviews,score,score_label,price_context,affiliate_url,category,sent_at")
        .in_("status", status_filter)
        .order("score", desc=True)
        .limit(limit)
    )
    if category and category != "all":
        query = query.eq("category", category)

    result = query.execute()
    return {"deals": result.data or [], "plan": member.get("plan", "free")}


@app.get("/member/referral")
async def get_referral(member: dict = Depends(get_current_member)):
    """Link de indicacao e estatisticas."""
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    result = sb.table("members").select(
        "referral_code,referral_count,points,level"
    ).eq("id", member["sub"]).execute()

    if not result.data:
        raise HTTPException(status_code=404)

    m = result.data[0]
    referral_link = f"{APP_URL}?ref={m['referral_code']}"

    # Historico de indicacoes
    refs = sb.table("referrals").select(
        "status,points_awarded,created_at"
    ).eq("referrer_id", member["sub"]).order("created_at", desc=True).limit(10).execute()

    return {
        "referral_code":  m["referral_code"],
        "referral_link":  referral_link,
        "referral_count": m["referral_count"],
        "points_earned":  m["referral_count"] * 200,
        "total_points":   m["points"],
        "level":          m["level"],
        "history":        refs.data or [],
    }


@app.post("/member/click")
async def register_click(
    body: ClickRequest,
    request: Request,
    member: dict = Depends(get_current_member)
):
    """Registra clique em deal e retorna URL com UTM rastreavel."""
    from services.member_service import track_click
    from supabase import create_client

    # Verifica se deal existe
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    deal = sb.table("deals").select("id,affiliate_url").eq("id", body.deal_id).execute()
    if not deal.data:
        raise HTTPException(status_code=404, detail="Deal nao encontrado.")

    utm = track_click(
        member_id = member["sub"],
        deal_id   = body.deal_id,
        ip        = request.client.host if request.client else None,
    )

    # Adiciona UTM ao link afiliado para rastrear conversao
    base_url = deal.data[0]["affiliate_url"]
    tracked_url = f"{base_url}&utm_source=clubeusa&utm_medium=whatsapp&utm_campaign={utm}"
    return {"url": tracked_url, "utm": utm}


@app.get("/member/leaderboard")
async def get_leaderboard(member: dict = Depends(get_current_member)):
    """Top 10 membros por pontos (sem expor dados pessoais)."""
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    result = sb.rpc("get_leaderboard", {"p_limit": 10}).execute()
    my_rank = sb.rpc("get_leaderboard", {"p_limit": 1000}).execute()

    my_position = None
    for i, row in enumerate(my_rank.data or []):
        if row["member_id"] == member["sub"]:
            my_position = i + 1
            break

    return {
        "leaderboard": result.data or [],
        "my_rank":     my_position,
    }


# ============================================================
#  ROTAS — BILLING (Stripe)
# ============================================================

@app.post("/billing/subscribe")
async def subscribe_vip(member: dict = Depends(get_current_member)):
    """
    Cria sessao de checkout Stripe para assinar o VIP.
    Retorna URL para redirecionar o usuario.
    """
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Pagamento nao configurado.")

    if member.get("plan") == "vip":
        raise HTTPException(status_code=400, detail="Voce ja e membro VIP.")

    try:
        session = stripe.checkout.Session.create(
            mode               = "subscription",
            payment_method_types = ["card"],
            line_items         = [{"price": STRIPE_VIP_PRICE_ID, "quantity": 1}],
            success_url        = f"{APP_URL}/vip/sucesso?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url         = f"{APP_URL}/vip/cancelado",
            metadata           = {"member_id": member["sub"]},
            subscription_data  = {
                "metadata": {"member_id": member["sub"]},
                "trial_period_days": 30 if not _has_used_trial(member["sub"]) else 0,
            },
            locale = "pt-BR",
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        log.error(f"Stripe erro: {e}")
        raise HTTPException(status_code=502, detail="Erro ao criar sessao de pagamento.")


@app.post("/billing/portal")
async def billing_portal(member: dict = Depends(get_current_member)):
    """Portal Stripe para gerenciar assinatura (cancelar, trocar cartao)."""
    if not stripe.api_key:
        raise HTTPException(status_code=503)

    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("members").select("stripe_customer_id").eq("id", member["sub"]).execute()

    if not result.data or not result.data[0].get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="Nenhuma assinatura ativa encontrada.")

    customer_id = result.data[0]["stripe_customer_id"]
    try:
        session = stripe.billing_portal.Session.create(
            customer   = customer_id,
            return_url = f"{APP_URL}/painel",
        )
        return {"portal_url": session.url}
    except stripe.error.StripeError as e:
        log.error(f"Stripe portal erro: {e}")
        raise HTTPException(status_code=502)


@app.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook Stripe — processa eventos de pagamento.
    Ativa/desativa VIP automaticamente.
    DEVE ser chamado pelo Stripe, nao pelo frontend.
    """
    payload   = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        log.warning("Webhook Stripe com assinatura invalida.")
        raise HTTPException(status_code=400, detail="Assinatura invalida.")

    log.info(f"Stripe webhook: {event['type']}")

    if event["type"] == "checkout.session.completed":
        _handle_checkout_completed(event["data"]["object"])
    elif event["type"] == "customer.subscription.deleted":
        _handle_subscription_cancelled(event["data"]["object"])
    elif event["type"] == "invoice.payment_failed":
        _handle_payment_failed(event["data"]["object"])

    return {"received": True}


# ============================================================
#  HELPERS STRIPE
# ============================================================

def _handle_checkout_completed(session: dict):
    """Ativa VIP apos pagamento confirmado."""
    member_id   = session.get("metadata", {}).get("member_id")
    customer_id = session.get("customer")
    if not member_id:
        return

    from supabase import create_client
    from datetime import datetime, timedelta
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    sb.table("members").update({
        "plan":               "vip",
        "vip_started_at":     datetime.utcnow().isoformat(),
        "vip_expires_at":     (datetime.utcnow() + timedelta(days=32)).isoformat(),
        "vip_trial_used":     True,
        "stripe_customer_id": customer_id,
    }).eq("id", member_id).execute()

    # Adiciona pontos de boas-vindas VIP
    from supabase import create_client
    sb.rpc("increment_points", {"p_member_id": member_id, "p_points": 500}).execute()

    # Audit log
    sb.table("audit_logs").insert({
        "actor_type":  "system",
        "action":      "member.vip_activated",
        "target_type": "member",
        "target_id":   member_id,
        "metadata":    {"stripe_customer_id": customer_id},
    }).execute()

    log.info(f"VIP ativado para membro {member_id}")

    # Envia mensagem de boas-vindas VIP via WhatsApp
    _send_vip_welcome(member_id)


def _handle_subscription_cancelled(subscription: dict):
    """Cancela VIP quando assinatura e cancelada."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    result = sb.table("members").select("id").eq("stripe_customer_id", customer_id).execute()
    if not result.data:
        return

    member_id = result.data[0]["id"]
    sb.table("members").update({"plan": "free"}).eq("id", member_id).execute()

    sb.table("audit_logs").insert({
        "actor_type":  "system",
        "action":      "member.vip_cancelled",
        "target_type": "member",
        "target_id":   member_id,
        "metadata":    {"stripe_customer_id": customer_id},
    }).execute()

    log.info(f"VIP cancelado para membro {member_id}")


def _handle_payment_failed(invoice: dict):
    """Loga falha de pagamento — nao cancela imediatamente (Stripe retentar)."""
    customer_id = invoice.get("customer")
    log.warning(f"Pagamento falhou para customer {customer_id}")


def _has_used_trial(member_id: str) -> bool:
    """Verifica se membro ja usou o trial gratuito."""
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("members").select("vip_trial_used").eq("id", member_id).execute()
    return result.data[0].get("vip_trial_used", False) if result.data else False


def _send_vip_welcome(member_id: str):
    """Envia mensagem de boas-vindas VIP via WhatsApp."""
    try:
        from supabase import create_client
        from utils.security import decrypt
        sb  = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        res = sb.table("members").select("phone_enc,language").eq("id", member_id).execute()
        if not res.data:
            return
        phone    = decrypt(res.data[0]["phone_enc"])
        language = res.data[0]["language"]
        messages = {
            "pt": (
                "*Bem-vindo ao Clube USA VIP!*\n\n"
                "Seu acesso VIP esta ativo.\n\n"
                "Voce agora recebe:\n"
                "- Deals exclusivos antes de todo mundo\n"
                "- Acesso ao painel completo em clubeusa.com\n"
                "- Sorteio VIP de $150 todo mes\n"
                "- 500 pontos de boas-vindas creditados\n\n"
                "Acesse seu painel: clubeusa.com/painel\n\n"
                "_Clube USA — Obrigado pela sua confianca_"
            ),
            "es": (
                "*Bienvenido a Club USA VIP!*\n\n"
                "Tu acceso VIP esta activo.\n\n"
                "Ahora recibes:\n"
                "- Deals exclusivos antes que nadie\n"
                "- Acceso al panel completo en clubeusa.com\n"
                "- Sorteo VIP de $150 cada mes\n"
                "- 500 puntos de bienvenida acreditados\n\n"
                "Accede a tu panel: clubeusa.com/panel\n\n"
                "_Club USA — Gracias por tu confianza_"
            ),
        }
        msg = messages.get(language, messages["pt"])
        import requests as req
        req.post(
            f"https://api.z-api.io/instances/{os.environ['ZAPI_INSTANCE']}/token/{os.environ['ZAPI_TOKEN']}/send-text",
            json={"phone": phone, "message": msg},
            headers={"Client-Token": os.environ["ZAPI_CLIENT_TOKEN"]},
            timeout=10,
        )
    except Exception as e:
        log.warning(f"Falha ao enviar boas-vindas VIP: {e}")


# ============================================================
#  HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():
    return {
        "status":  "ok",
        "service": "clube-usa-api",
        "version": "1.0.0",
    }


# ============================================================
#  ROTAS — ALERTAS DE PRECO
# ============================================================

@app.post("/alerts", status_code=201)
async def create_alert(body: AlertCreate, member: dict = Depends(require_paid_plan)):
    """Cria alerta de preco para um ASIN."""
    from services.alert_service import create_alert as svc_create
    try:
        result = svc_create(
            member_id    = member["sub"],
            asin         = body.asin,
            target_type  = body.target_type,
            target_value = body.target_value,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/alerts")
async def list_alerts(member: dict = Depends(require_paid_plan)):
    """Lista alertas ativos do membro autenticado."""
    from services.alert_service import list_alerts as svc_list
    return svc_list(member["sub"])


@app.delete("/alerts/{alert_id}", status_code=204)
async def cancel_alert(alert_id: str, member: dict = Depends(require_paid_plan)):
    """Cancela um alerta."""
    from services.alert_service import cancel_alert as svc_cancel
    found = svc_cancel(alert_id, member["sub"])
    if not found:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")


@app.post("/alerts/from-link", status_code=201)
async def create_alert_from_link(body: AlertFromLink, member: dict = Depends(require_paid_plan)):
    """Recebe URL da Amazon, extrai ASIN e cria alerta."""
    from services.alert_service import extract_asin_from_url, create_alert as svc_create
    try:
        asin   = extract_asin_from_url(body.url)
        result = svc_create(
            member_id    = member["sub"],
            asin         = asin,
            target_type  = body.target_type,
            target_value = body.target_value,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _send_otp_whatsapp(phone: str, otp: str):
    """Envia OTP via WhatsApp."""
    import requests as req
    msg = f"*Clube USA*\n\nSeu codigo de acesso: *{otp}*\n\nValido por 10 minutos.\nNunca compartilhe este codigo."
    try:
        req.post(
            f"https://api.z-api.io/instances/{os.environ['ZAPI_INSTANCE']}/token/{os.environ['ZAPI_TOKEN']}/send-text",
            json={"phone": phone, "message": msg},
            headers={"Client-Token": os.environ["ZAPI_CLIENT_TOKEN"]},
            timeout=10,
        )
    except Exception as e:
        log.error(f"Falha ao enviar OTP: {e}")


# ============================================================
#  ROTAS — ADMIN
# ============================================================

@app.get("/admin", include_in_schema=False)
async def admin_panel():
    """Serve o painel admin HTML."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "admin.html")
    return FileResponse(os.path.abspath(html_path))


@app.get("/admin/metrics")
async def admin_metrics(_=Depends(require_admin)):
    from services.admin_service import get_metrics
    return get_metrics()


@app.get("/admin/members")
async def admin_list_members(
    plan: str = None, status: str = None, q: str = None,
    limit: int = 50, offset: int = 0,
    _=Depends(require_admin),
):
    from services.admin_service import list_members
    return list_members(plan=plan, status=status, q=q, limit=limit, offset=offset)


@app.get("/admin/members/{member_id}")
async def admin_get_member(member_id: str, _=Depends(require_admin)):
    from services.admin_service import get_member
    m = get_member(member_id)
    if not m:
        raise HTTPException(status_code=404, detail="Membro não encontrado.")
    return m


@app.post("/admin/members/{member_id}/status")
async def admin_set_member_status(
    member_id: str, body: StatusUpdate, _=Depends(require_admin)
):
    from services.admin_service import set_member_status
    try:
        found = set_member_status(member_id, body.status)
        if not found:
            raise HTTPException(status_code=404, detail="Membro não encontrado.")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/deals")
async def admin_list_deals(status: str = None, _=Depends(require_admin)):
    from services.admin_service import list_deals
    return list_deals(status=status)


@app.post("/admin/deals/{deal_id}/approve")
async def admin_approve_deal(deal_id: str, _=Depends(require_admin)):
    from services.admin_service import approve_deal
    if not approve_deal(deal_id):
        raise HTTPException(status_code=404, detail="Deal não encontrado.")
    return {"ok": True}


@app.post("/admin/deals/{deal_id}/reject")
async def admin_reject_deal(deal_id: str, _=Depends(require_admin)):
    from services.admin_service import reject_deal
    if not reject_deal(deal_id):
        raise HTTPException(status_code=404, detail="Deal não encontrado.")
    return {"ok": True}


@app.post("/admin/deals/scan")
async def admin_scan_deals(_=Depends(require_admin)):
    """Dispara varredura Amazon em background."""
    subprocess.Popen(
        [sys.executable, "scanner.py"],
        cwd=os.path.join(os.path.dirname(__file__), "..", "..", "dealscanner2"),
        start_new_session=True,
    )
    return {"ok": True, "message": "Varredura iniciada em background."}


@app.post("/admin/deals/send")
async def admin_send_deals(_=Depends(require_admin)):
    """Envia todos os deals aprovados em background."""
    subprocess.Popen(
        [sys.executable, "-c",
         "from sender import auto_send_approved; auto_send_approved()"],
        cwd=os.path.join(os.path.dirname(__file__), "..", "..", "dealscanner2"),
        start_new_session=True,
    )
    return {"ok": True, "message": "Envio iniciado em background."}


@app.get("/admin/alerts")
async def admin_list_alerts(_=Depends(require_admin)):
    from services.admin_service import list_admin_alerts
    return list_admin_alerts()
