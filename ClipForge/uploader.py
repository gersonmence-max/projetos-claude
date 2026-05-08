"""
uploader.py — Upload automático dos clips para as plataformas

YouTube  → YouTube Data API v3 (OAuth 2.0 via client_secrets.json)
TikTok   → tiktok-uploader (via cookies do navegador)
Kwai     → Playwright browser automation (sem API oficial)
"""

import os
import json
import time
from pathlib import Path


# ── YouTube Shorts ─────────────────────────────────────────────────────────────
def upload_youtube(clip_path: str, title: str, description: str,
                   tags: list, privacy: str, category_id: str,
                   secrets_file: str, log_fn=None) -> dict:
    """
    Faz upload de um clip para o YouTube Shorts via Data API v3.

    Requires:
        pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
    """
    def log(m): log_fn and log_fn(m, "pub")

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import pickle
    except ImportError:
        log("Google API não instalada. Execute: pip install google-api-python-client google-auth-oauthlib")
        return {"success": False, "error": "google-api não instalada"}

    SCOPES       = ["https://www.googleapis.com/auth/youtube.upload"]
    TOKEN_FILE   = Path(secrets_file).parent / "yt_token.pickle"
    creds        = None

    # Carrega token salvo
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    # Renova se expirado
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    # Autenticação inicial (abre navegador uma vez)
    if not creds or not creds.valid:
        if not Path(secrets_file).exists():
            log(f"client_secrets.json não encontrado em: {secrets_file}")
            return {"success": False, "error": "client_secrets.json não encontrado"}
        flow  = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title":       title[:100],
            "description": description[:5000],
            "tags":        tags[:15],
            "categoryId":  category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(clip_path, mimetype="video/mp4", resumable=True)
    log(f"Enviando para YouTube: {Path(clip_path).name}")

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log(f"  progresso: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    log(f"  ✓ YouTube: https://youtube.com/shorts/{video_id}")
    return {"success": True, "video_id": video_id, "url": f"https://youtube.com/shorts/{video_id}"}


# ── TikTok ─────────────────────────────────────────────────────────────────────
def upload_tiktok(clip_path: str, description: str, cookies_file: str,
                  log_fn=None) -> dict:
    """
    Faz upload para o TikTok via tiktok-uploader (sem API oficial).

    Requires:
        pip install tiktok-uploader
        Cookies exportados do Chrome com extensão "Get cookies.txt"
    """
    def log(m): log_fn and log_fn(m, "pub")

    try:
        from tiktok_uploader.upload import upload_video
    except ImportError:
        log("tiktok-uploader não instalado. Execute: pip install tiktok-uploader")
        return {"success": False, "error": "tiktok-uploader não instalado"}

    if not Path(cookies_file).exists():
        log(f"cookies.txt não encontrado: {cookies_file}")
        return {"success": False, "error": "cookies.txt não encontrado"}

    log(f"Enviando para TikTok: {Path(clip_path).name}")
    try:
        result = upload_video(
            filename    = clip_path,
            description = description[:2200],
            cookies     = cookies_file,
        )
        log("  ✓ TikTok: upload concluído")
        return {"success": True}
    except Exception as e:
        log(f"  TikTok erro: {e}")
        return {"success": False, "error": str(e)}


# ── Kwai ───────────────────────────────────────────────────────────────────────
def upload_kwai(clip_path: str, description: str,
                username: str, password: str, log_fn=None) -> dict:
    """
    Faz upload para o Kwai via Playwright (browser automatizado).
    Sem API oficial — pode quebrar com atualizações do Kwai.

    Requires:
        pip install playwright
        playwright install chromium
    """
    def log(m): log_fn and log_fn(m, "pub")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("Playwright não instalado. Execute: pip install playwright && playwright install chromium")
        return {"success": False, "error": "playwright não instalado"}

    log(f"Iniciando browser para Kwai: {Path(clip_path).name}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()

            # Login
            page.goto("https://www.kwai.com/login", timeout=30000)
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_timeout(3000)

            # Upload
            page.goto("https://www.kwai.com/upload", timeout=30000)
            page.wait_for_timeout(2000)

            # Procura input de arquivo
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(clip_path)
                page.wait_for_timeout(3000)

                # Preenche descrição
                desc_input = page.query_selector('textarea')
                if desc_input:
                    desc_input.fill(description[:200])

                # Publica
                publish_btn = page.query_selector('button:has-text("Publicar"), button:has-text("Post")')
                if publish_btn:
                    publish_btn.click()
                    page.wait_for_timeout(3000)
                    log("  ✓ Kwai: upload concluído")
                    browser.close()
                    return {"success": True}

            browser.close()
            log("  Kwai: não encontrou elementos de upload — interface pode ter mudado")
            return {"success": False, "error": "elementos de upload não encontrados"}

    except Exception as e:
        log(f"  Kwai erro: {e}")
        return {"success": False, "error": str(e)}


# ── Orquestrador ───────────────────────────────────────────────────────────────
def upload_to_platforms(clips: list, platforms: list, log_fn=None) -> dict:
    """
    Faz upload de todos os clips para as plataformas ativas.

    Args:
        clips:     Lista de dicts com {path, platform, name, ...}
        platforms: Lista de plataformas ativas ["yt", "tt", "kw"]
        log_fn:    Função de log do pipeline

    Returns:
        Dict com resultados por plataforma
    """
    results = {}

    # Carrega config salva (yt_config.json, tt_config.json, kw_config.json)
    config = _load_config()

    for plat in platforms:
        results[plat] = []

        # Filtra clips desta plataforma
        plat_clips = [c for c in clips if c.get("platform") == plat]
        if not plat_clips:
            continue

        for clip in plat_clips:
            clip_path = clip.get("path", "")
            title     = clip.get("text", "Clip gerado pelo ClipForge")[:80]
            desc      = config.get(f"{plat}_description", "✂️ Clip gerado pelo ClipForge")

            if plat == "yt":
                r = upload_youtube(
                    clip_path   = clip_path,
                    title       = title,
                    description = desc,
                    tags        = config.get("yt_tags", ["shorts","viral","clips"]),
                    privacy     = config.get("yt_privacy", "public"),
                    category_id = config.get("yt_category", "22"),
                    secrets_file= config.get("yt_secrets", "./client_secrets.json"),
                    log_fn      = log_fn,
                )
            elif plat == "tt":
                r = upload_tiktok(
                    clip_path    = clip_path,
                    description  = desc,
                    cookies_file = config.get("tt_cookies", "./cookies.txt"),
                    log_fn       = log_fn,
                )
            elif plat == "kw":
                r = upload_kwai(
                    clip_path   = clip_path,
                    description = desc,
                    username    = config.get("kw_user", ""),
                    password    = config.get("kw_pass", ""),
                    log_fn      = log_fn,
                )
            else:
                continue

            results[plat].append(r)

            # Pausa entre uploads para evitar rate limit
            time.sleep(2)

    return results


def _load_config() -> dict:
    """Carrega configurações de plataforma salvas pelo frontend via /api/config"""
    config_file = Path("./clipforge_config.json")
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except Exception:
            pass
    return {}
