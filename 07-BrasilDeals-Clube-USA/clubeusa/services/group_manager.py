# ============================================================
#  services/group_manager.py — Clube USA
#
#  Gerenciamento automatico de grupos WhatsApp:
#  1. Detecta quando grupo esta cheio (1024 membros)
#  2. Cria novo grupo automaticamente via Z-API
#  3. Envia link de convite para todos os grupos existentes
#  4. Atribui novos membros ao grupo com espaco disponivel
#  5. Suporta PT e ES (grupos separados por idioma)
# ============================================================

import os
import re
import logging
import requests
from datetime import datetime
from typing import Optional

log = logging.getLogger("group_manager")

ZAPI_BASE    = "https://api.z-api.io/instances/{instance}/token/{token}"
GROUP_CAPACITY = 1024
NOTIFY_AT    = 1000  # avisa quando grupo esta a 24 vagas do limite


def _zapi_url(path: str) -> str:
    instance = os.environ["ZAPI_INSTANCE"]
    token    = os.environ["ZAPI_TOKEN"]
    return f"https://api.z-api.io/instances/{instance}/token/{token}{path}"


def _zapi_headers() -> dict:
    return {
        "Content-Type":   "application/json",
        "Client-Token":   os.environ["ZAPI_CLIENT_TOKEN"],
    }


def _zapi_post(path: str, payload: dict) -> dict:
    resp = requests.post(
        _zapi_url(path), json=payload,
        headers=_zapi_headers(), timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def _zapi_get(path: str) -> dict:
    resp = requests.get(
        _zapi_url(path),
        headers=_zapi_headers(), timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
#  SUPABASE — operacoes no banco
# ============================================================

def _supabase():
    from supabase import create_client
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]  # service key para operacoes admin
    )


def get_available_group(language: str = "pt") -> Optional[dict]:
    """
    Retorna o grupo ativo com espaco disponivel para o idioma.
    Prioriza o grupo mais cheio (concentra membros antes de abrir novo).
    """
    sb = _supabase()
    result = (
        sb.table("whatsapp_groups")
        .select("*")
        .eq("language", language)
        .eq("is_active", True)
        .eq("is_full", False)
        .order("member_count", desc=True)
        .limit(1)
        .execute()
    )
    groups = result.data
    return groups[0] if groups else None


def get_all_active_groups(language: str = None) -> list:
    """Retorna todos os grupos ativos, opcionalmente filtrado por idioma."""
    sb = _supabase()
    query = (
        sb.table("whatsapp_groups")
        .select("*")
        .eq("is_active", True)
    )
    if language:
        query = query.eq("language", language)
    return query.execute().data or []


# ============================================================
#  CRIACAO DE NOVO GRUPO
# ============================================================

def get_next_sequence(language: str) -> int:
    """Retorna o proximo numero de sequencia para o idioma."""
    sb = _supabase()
    result = (
        sb.table("whatsapp_groups")
        .select("sequence_number")
        .eq("language", language)
        .order("sequence_number", desc=True)
        .limit(1)
        .execute()
    )
    groups = result.data
    return (groups[0]["sequence_number"] + 1) if groups else 1


def build_group_name(language: str, sequence: int) -> str:
    """
    Gera nome do grupo baseado no idioma e sequencia.
    PT: Clube USA | ES: Club USA
    """
    names = {
        "pt": f"Clube USA",
        "es": f"Club USA",
    }
    base = names.get(language, "Clube USA")
    if sequence > 1:
        return f"{base} #{sequence}"
    return base


def create_new_group(language: str = "pt") -> Optional[dict]:
    """
    Cria novo grupo no WhatsApp via Z-API e registra no banco.
    Retorna o grupo criado ou None em caso de erro.
    """
    sequence = get_next_sequence(language)
    name     = build_group_name(language, sequence)

    log.info(f"Criando novo grupo: '{name}' (idioma: {language})")

    # 1. Criar grupo na Z-API
    try:
        resp = _zapi_post("/create-group", {
            "groupName": name,
            "phones":    [],  # grupo vazio — membros entram pelo link
        })
        group_id_zapi = resp.get("groupId") or resp.get("id")
        if not group_id_zapi:
            log.error(f"Z-API nao retornou groupId: {resp}")
            return None
    except Exception as e:
        log.error(f"Erro ao criar grupo na Z-API: {e}")
        return None

    # 2. Buscar link de convite
    try:
        link_resp = _zapi_get(f"/group-invite-link/{group_id_zapi}")
        invite_link = link_resp.get("link") or link_resp.get("inviteLink")
    except Exception as e:
        log.warning(f"Nao foi possivel obter link de convite: {e}")
        invite_link = None

    # 3. Configurar grupo como fechado (so admin envia)
    try:
        _zapi_post("/update-group-settings", {
            "groupId":   group_id_zapi,
            "settings":  {"sendMessages": "ADMINS"},  # so admin envia
        })
    except Exception as e:
        log.warning(f"Nao foi possivel configurar restricoes do grupo: {e}")

    # 4. Enviar mensagem de boas-vindas como mensagem fixada
    welcome = _build_welcome_message(name, language)
    try:
        _zapi_post("/send-text", {
            "phone":   group_id_zapi,
            "message": welcome,
        })
    except Exception as e:
        log.warning(f"Nao foi possivel enviar boas-vindas: {e}")

    # 5. Registrar no banco
    sb = _supabase()
    result = (
        sb.table("whatsapp_groups")
        .insert({
            "group_id_zapi":   group_id_zapi,
            "name":            name,
            "language":        language,
            "capacity":        GROUP_CAPACITY,
            "member_count":    0,
            "is_full":         False,
            "is_active":       True,
            "invite_link":     invite_link,
            "sequence_number": sequence,
        })
        .execute()
    )

    group = result.data[0] if result.data else None
    if group:
        log.info(f"Grupo criado com sucesso: {name} | ID: {group_id_zapi}")

        # 6. Registrar no audit log
        _audit("group.created", "whatsapp_group", group["id"], {
            "name": name, "language": language, "sequence": sequence
        })

    return group


# ============================================================
#  NOTIFICACAO DE NOVO GRUPO
#  Envia link do novo grupo para todos os grupos existentes
# ============================================================

def notify_all_groups_new_link(new_group: dict, language: str = "pt"):
    """
    Quando um novo grupo e criado, envia o link para todos
    os grupos existentes do mesmo idioma para indicacoes.
    """
    all_groups = get_all_active_groups(language)
    invite_link = new_group.get("invite_link", "clubeusa.com")
    name        = new_group.get("name", "Clube USA")

    messages = {
        "pt": (
            f"*Clube USA esta crescendo!*\n\n"
            f"Nosso grupo esta quase cheio. "
            f"Se voce conhece alguem que quer economizar nos EUA, "
            f"compartilhe o link do novo grupo:\n\n"
            f"{invite_link}\n\n"
            f"Cada indicacao sua vale *+200 pontos* no programa de recompensas.\n\n"
            f"Acesse seu link de indicacao em: clubeusa.com/indicar\n\n"
            f"_Clube USA — Economize com quem entende voce_"
        ),
        "es": (
            f"*Club USA esta creciendo!*\n\n"
            f"Nuestro grupo esta casi lleno. "
            f"Si conoces a alguien que quiere ahorrar en USA, "
            f"comparte el link del nuevo grupo:\n\n"
            f"{invite_link}\n\n"
            f"Cada referido vale *+200 puntos* en el programa de recompensas.\n\n"
            f"Accede a tu link de referido en: clubeusa.com/referir\n\n"
            f"_Club USA — Ahorra con quien te entiende_"
        ),
    }

    msg = messages.get(language, messages["pt"])
    sent = 0

    for group in all_groups:
        if group["id"] == new_group.get("id"):
            continue  # nao envia para o grupo recem criado
        try:
            _zapi_post("/send-text", {
                "phone":   group["group_id_zapi"],
                "message": msg,
            })
            sent += 1
            log.info(f"Link enviado para grupo: {group['name']}")
        except Exception as e:
            log.warning(f"Erro ao enviar para {group['name']}: {e}")

    log.info(f"Link do novo grupo enviado para {sent} grupos.")
    return sent


# ============================================================
#  ATRIBUICAO DE MEMBRO AO GRUPO
# ============================================================

def assign_member_to_group(member_id: str, language: str = "pt") -> Optional[dict]:
    """
    Atribui membro ao grupo disponivel.
    Se nao houver grupo disponivel, cria um novo automaticamente.
    """
    group = get_available_group(language)

    if not group:
        log.info(f"Nenhum grupo disponivel para idioma '{language}'. Criando novo...")
        group = create_new_group(language)
        if not group:
            log.error("Falha ao criar novo grupo.")
            return None

        # Notifica grupos existentes sobre o novo grupo
        notify_all_groups_new_link(group, language)

    # Verifica se o grupo esta chegando no limite
    if group["member_count"] >= NOTIFY_AT and not group["is_full"]:
        log.warning(
            f"Grupo '{group['name']}' esta a "
            f"{GROUP_CAPACITY - group['member_count']} vagas do limite. "
            f"Considere criar o proximo grupo em breve."
        )

    # Atualiza o member_id no banco — o trigger sync_group_capacity cuida do contador
    sb = _supabase()
    sb.table("members").update({"group_id": group["id"]}).eq("id", member_id).execute()

    log.info(f"Membro {member_id} atribuido ao grupo '{group['name']}'")
    return group


# ============================================================
#  MENSAGENS PADRAO
# ============================================================

def _build_welcome_message(group_name: str, language: str) -> str:
    messages = {
        "pt": (
            f"Bem-vindo ao *{group_name}*!\n\n"
            f"Aqui voce recebe os melhores deals do dia diretamente no seu WhatsApp.\n\n"
            f"*Horarios dos deals:*\n"
            f"Manha: 09:00\nAlmoco: 13:00\nNoite: 20:00\n\n"
            f"*Regras:*\n"
            f"So o admin envia mensagens neste grupo.\n"
            f"Os links sao verificados e seguros.\n\n"
            f"*Sorteio semanal:* todo domingo\n"
            f"Clique em pelo menos 1 deal por semana para participar.\n\n"
            f"Acesse seu painel em: *clubeusa.com*\n\n"
            f"_Clube USA — Economize com quem entende voce_"
        ),
        "es": (
            f"Bienvenido a *{group_name}*!\n\n"
            f"Aqui recibes los mejores deals del dia directamente en tu WhatsApp.\n\n"
            f"*Horarios de deals:*\n"
            f"Manana: 09:00\nAlmuerzo: 13:00\nNoche: 20:00\n\n"
            f"*Reglas:*\n"
            f"Solo el admin envia mensajes en este grupo.\n"
            f"Los links son verificados y seguros.\n\n"
            f"*Sorteo semanal:* cada domingo\n"
            f"Haz click en al menos 1 deal por semana para participar.\n\n"
            f"Accede a tu panel en: *clubeusa.com*\n\n"
            f"_Club USA — Ahorra con quien te entiende_"
        ),
    }
    return messages.get(language, messages["pt"])


def _audit(action: str, target_type: str, target_id: str, metadata: dict = None):
    """Registra acao no audit log."""
    try:
        sb = _supabase()
        sb.table("audit_logs").insert({
            "actor_type":  "system",
            "action":      action,
            "target_type": target_type,
            "target_id":   target_id,
            "metadata":    metadata or {},
        }).execute()
    except Exception as e:
        log.warning(f"Falha ao registrar audit log: {e}")
