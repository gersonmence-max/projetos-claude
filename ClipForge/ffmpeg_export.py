"""
ffmpeg_export.py — Exportação de clips com perfis por plataforma
Gera versões otimizadas do mesmo clip para YouTube Shorts, TikTok e Kwai

Instalação:
    # macOS:   brew install ffmpeg
    # Ubuntu:  sudo apt install ffmpeg
    # Windows: https://ffmpeg.org/download.html

Uso:
    from ffmpeg_export import export_clip, PLATFORMS

    export_clip(
        input_path = "video_original.mp4",
        start      = 124.5,
        end        = 151.2,
        output_dir = "./clips/pele/",
        clip_name  = "clip_01",
        platforms  = ["youtube", "tiktok", "kwai"],
    )
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# PERFIS POR PLATAFORMA
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PlatformProfile:
    name: str
    slug: str
    width: int
    height: int
    aspect_ratio: str
    fps: int
    video_bitrate: str
    audio_bitrate: str
    audio_sample_rate: int
    max_duration: int        # segundos máximos aceitos pela plataforma
    max_file_mb: int         # tamanho máximo recomendado em MB
    codec_video: str
    codec_audio: str
    container: str
    safe_zone_top_pct: float
    safe_zone_bottom_pct: float
    notes: str


PLATFORMS: dict[str, PlatformProfile] = {

    # ── YouTube Shorts ────────────────────────────────────────────────────────
    "youtube": PlatformProfile(
        name                 = "YouTube Shorts",
        slug                 = "yt",
        width                = 1080,
        height               = 1920,
        aspect_ratio         = "9:16",
        fps                  = 30,
        video_bitrate        = "8M",
        audio_bitrate        = "192k",
        audio_sample_rate    = 48000,          # ← 48kHz (diferente do TikTok)
        max_duration         = 180,
        max_file_mb          = 256,
        codec_video          = "libx264",
        codec_audio          = "aac",
        container            = "mp4",
        safe_zone_top_pct    = 0.14,
        safe_zone_bottom_pct = 0.20,
        notes                = (
            "Vertical 9:16 obrigatório para o feed de Shorts. "
            "Adicione #Shorts no título. "
            "Audio: AAC 48kHz (diferente do TikTok que usa 44.1kHz)."
        ),
    ),

    # ── TikTok ────────────────────────────────────────────────────────────────
    "tiktok": PlatformProfile(
        name                 = "TikTok",
        slug                 = "tt",
        width                = 1080,
        height               = 1920,
        aspect_ratio         = "9:16",
        fps                  = 30,
        video_bitrate        = "7M",
        audio_bitrate        = "256k",
        audio_sample_rate    = 44100,          # ← 44.1kHz (diferente do YouTube)
        max_duration         = 600,
        max_file_mb          = 287,
        codec_video          = "libx264",
        codec_audio          = "aac",
        container            = "mp4",
        safe_zone_top_pct    = 0.12,
        safe_zone_bottom_pct = 0.25,
        notes                = (
            "Videos 21-34s têm melhor engajamento. "
            "Audio: AAC-LC 44.1kHz — diferente do YouTube (48kHz). "
            "TikTok recomprime tudo — 1080p é essencial como fonte."
        ),
    ),

    # ── Kwai ──────────────────────────────────────────────────────────────────
    "kwai": PlatformProfile(
        name                 = "Kwai",
        slug                 = "kw",
        width                = 1080,
        height               = 1920,
        aspect_ratio         = "9:16",
        fps                  = 30,
        video_bitrate        = "5M",           # conservador — sem doc oficial
        audio_bitrate        = "192k",
        audio_sample_rate    = 44100,
        max_duration         = 300,
        max_file_mb          = 200,
        codec_video          = "libx264",
        codec_audio          = "aac",
        container            = "mp4",
        safe_zone_top_pct    = 0.10,
        safe_zone_bottom_pct = 0.22,
        notes                = (
            "Sem API oficial — upload via Playwright. "
            "Specs por engenharia reversa — podem mudar sem aviso."
        ),
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DETECÇÃO DE PROPORÇÃO DO VÍDEO ORIGINAL
# ═══════════════════════════════════════════════════════════════════════════════

def get_video_dimensions(input_path: str) -> tuple[int, int]:
    """
    Retorna (width, height) do vídeo via ffprobe.
    Retorna (0, 0) se falhar.
    """
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            input_path,
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 0, 0


def build_vf_chain(
    src_w: int,
    src_h: int,
    profile: PlatformProfile,
    ass_path: Optional[str] = None,
) -> str:
    """
    Monta o filtro de vídeo adaptado à proporção original do vídeo.

    Estratégia por proporção de origem:
      - 16:9 (horizontal, ex: YouTube)  → escala pela largura, crop vertical centrado
      - 9:16 (vertical, ex: TikTok)     → escala pela altura, sem crop necessário
      - 4:3 / outro                     → escala + pad para completar sem distorção
      - proporção desconhecida          → comportamento safe com centralização

    Melhoria do GPT aplicada:
      crop=w:h:(iw-ow)/2:(ih-oh)/2  → centraliza horizontal E verticalmente
      Evita cortar cabeça ou pés independente da proporção original.
    """
    tw, th = profile.width, profile.height   # target: ex 1080x1920
    target_ratio = tw / th                   # 0.5625 para 9:16

    if src_w > 0 and src_h > 0:
        src_ratio = src_w / src_h
    else:
        src_ratio = 16 / 9  # assume horizontal se não souber

    # Vídeo horizontal (16:9, 21:9, etc.) → mais comum vindo do YouTube
    if src_ratio > 1.0:
        # Escala pela largura alvo, altura fica proporcional e maior que th
        # Ex: 1920x1080 → scale=1080:-2 → 1080x607 → precisa pad vertical
        # Ou: scale by height → (th/src_h)*src_w × th
        scale_by_h_w = int((th / src_h) * src_w)

        if scale_by_h_w >= tw:
            # Escala pela altura → largura >= tw → pode fazer crop horizontal
            vf = (
                f"scale=-2:{th},"
                f"crop={tw}:{th}:(iw-{tw})/2:0,"
                f"setsar=1,"
                f"fps={profile.fps}"
            )
        else:
            # Escala pela largura → adiciona pad preto vertical centrado
            vf = (
                f"scale={tw}:-2,"
                f"pad={tw}:{th}:0:(oh-ih)/2:black,"
                f"setsar=1,"
                f"fps={profile.fps}"
            )

    # Vídeo vertical (9:16, 4:5, etc.)
    elif src_ratio < 1.0:
        if abs(src_ratio - target_ratio) < 0.05:
            # Mesma proporção — só redimensiona
            vf = (
                f"scale={tw}:{th},"
                f"setsar=1,"
                f"fps={profile.fps}"
            )
        elif src_ratio > target_ratio:
            # Mais largo que 9:16 → crop horizontal centrado
            vf = (
                f"scale=-2:{th},"
                f"crop={tw}:{th}:(iw-{tw})/2:0,"
                f"setsar=1,"
                f"fps={profile.fps}"
            )
        else:
            # Mais estreito que 9:16 → pad horizontal centrado
            vf = (
                f"scale={tw}:-2,"
                f"pad={tw}:{th}:(ow-iw)/2:0:black,"
                f"setsar=1,"
                f"fps={profile.fps}"
            )

    # Vídeo quadrado (1:1)
    else:
        vf = (
            f"scale={tw}:-2,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:black,"
            f"setsar=1,"
            f"fps={profile.fps}"
        )

    # Adiciona legenda queimada se fornecida
    if ass_path:
        safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")
        vf += f",ass='{safe_ass}'"

    return vf


# ═══════════════════════════════════════════════════════════════════════════════
# GERAÇÃO DO COMANDO FFMPEG
# ═══════════════════════════════════════════════════════════════════════════════

def build_ffmpeg_command(
    input_path:  str,
    output_path: str,
    start:       float,
    end:         float,
    profile:     PlatformProfile,
    ass_path:    Optional[str] = None,
    src_w:       int = 0,
    src_h:       int = 0,
) -> list[str]:
    """
    Monta o comando FFmpeg completo com:
      - Filtro de vídeo adaptativo (corrige 16:9, 4:3, 21:9 → 9:16)
      - Legenda queimada (opcional, via arquivo .ass)
      - Specs corretas por plataforma (bitrate, sample rate, etc.)
    """
    duration = end - start
    vf_chain  = build_vf_chain(src_w, src_h, profile, ass_path)

    cmd = [
        "ffmpeg",
        "-y",                          # sobrescreve sem perguntar
        "-ss", str(start),             # seek antes do input (mais rápido)
        "-i", input_path,
        "-t", str(duration),
        "-vf", vf_chain,
        "-c:v", profile.codec_video,
        "-profile:v", "high",
        "-level", "4.2",
        "-b:v", profile.video_bitrate,
        "-maxrate", profile.video_bitrate,
        "-bufsize", str(int(profile.video_bitrate.replace("M", "")) * 2) + "M",
        "-c:a", profile.codec_audio,
        "-b:a", profile.audio_bitrate,
        "-ar", str(profile.audio_sample_rate),
        "-ac", "2",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    return cmd


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTAÇÃO DE UM CLIP
# ═══════════════════════════════════════════════════════════════════════════════

def export_clip(
    input_path:  str,
    start:       float,
    end:         float,
    output_dir:  str,
    clip_name:   str,
    platforms:   list[str],
    ass_path:    Optional[str] = None,
    verbose:     bool = True,
    log_dir:     Optional[str] = None,   # pasta para salvar logs do ffmpeg
) -> dict[str, str]:
    """
    Exporta um clip para múltiplas plataformas.

    Args:
        input_path:  Vídeo original
        start:       Timestamp início (segundos)
        end:         Timestamp fim (segundos)
        output_dir:  Pasta raiz de saída
        clip_name:   Nome base (ex: "clip_01")
        platforms:   ["youtube", "tiktok", "kwai"]
        ass_path:    Arquivo .ass de legenda (opcional)
        verbose:     Imprime progresso
        log_dir:     Se informado, salva stderr do FFmpeg em .log por clip

    Returns:
        {plataforma: caminho_do_arquivo}
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    outputs  = {}
    duration = end - start

    # Detecta dimensões do vídeo fonte UMA vez para todos os targets
    src_w, src_h = get_video_dimensions(input_path)
    src_info = f"{src_w}×{src_h}" if src_w else "dimensões desconhecidas"

    if verbose:
        print(f"\n[export] {clip_name}  [{start:.1f}s → {end:.1f}s]  ({duration:.1f}s)  fonte: {src_info}")

    for plat_key in platforms:
        if plat_key not in PLATFORMS:
            print(f"[export] ⚠ Plataforma '{plat_key}' não reconhecida — pulando")
            continue

        profile = PLATFORMS[plat_key]

        # ── Melhoria GPT #5: corta automaticamente ao limite em vez de abortar ──
        effective_end = end
        if duration > profile.max_duration:
            effective_end = start + profile.max_duration
            if verbose:
                print(f"  ⚠ {profile.name}: clip cortado em {profile.max_duration}s "
                      f"(original: {duration:.0f}s)")

        # Pasta por plataforma dentro da pasta da categoria
        plat_dir    = Path(output_dir) / plat_key
        plat_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(plat_dir / f"{clip_name}_{profile.slug}.{profile.container}")

        cmd = build_ffmpeg_command(
            input_path  = input_path,
            output_path = output_path,
            start       = start,
            end         = effective_end,
            profile     = profile,
            ass_path    = ass_path,
            src_w       = src_w,
            src_h       = src_h,
        )

        if verbose:
            src_ratio_str = f"{src_w/src_h:.2f}" if src_w else "?"
            print(f"  → {profile.name}: {profile.width}×{profile.height} "
                  f"| src ratio {src_ratio_str} "
                  f"| {profile.video_bitrate} | {profile.audio_sample_rate}Hz")

        try:
            result = subprocess.run(
                cmd,
                capture_output = True,
                text           = True,
                timeout        = 300,
            )

            # ── Melhoria GPT #3: salva log completo do FFmpeg ──────────────────
            if log_dir:
                log_path = Path(log_dir) / f"{clip_name}_{profile.slug}.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(result.stderr, encoding="utf-8")

            if result.returncode != 0:
                print(f"  ✗ Erro FFmpeg ({profile.name}): {result.stderr[-400:]}")
                if log_dir:
                    print(f"    Log completo: {log_path}")
                continue

            # ── Melhoria GPT #2: valida tamanho do arquivo gerado ──────────────
            if not Path(output_path).exists():
                print(f"  ✗ Arquivo não gerado: {output_path}")
                continue

            size_mb = Path(output_path).stat().st_size / (1024 * 1024)

            if size_mb > profile.max_file_mb:
                print(f"  ⚠ {profile.name}: {size_mb:.1f}MB excede limite "
                      f"recomendado de {profile.max_file_mb}MB — "
                      f"considere reduzir o bitrate")
            elif verbose:
                print(f"    ✓ {size_mb:.1f}MB  {output_path}")

            outputs[plat_key] = output_path

        except subprocess.TimeoutExpired:
            print(f"  ✗ Timeout ({profile.name}) — FFmpeg demorou mais de 300s")
        except FileNotFoundError:
            print("  ✗ FFmpeg não encontrado.")
            print("    macOS:   brew install ffmpeg")
            print("    Ubuntu:  sudo apt install ffmpeg")
            print("    Windows: https://ffmpeg.org/download.html")
            break  # inutl continuar sem ffmpeg

    return outputs


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTAÇÃO EM BATCH (lista de clips)
# ═══════════════════════════════════════════════════════════════════════════════

def export_all_clips(
    clips:      list[dict],
    input_path: str,
    output_dir: str,
    platforms:  list[str],
    ass_files:  Optional[list[str]] = None,
    verbose:    bool = True,
    log_dir:    Optional[str] = None,
) -> list[dict]:
    """
    Exporta uma lista de clips para todas as plataformas.

    Args:
        clips:      [{start, end, id, score, ...}]
        input_path: Vídeo original
        output_dir: Pasta raiz de saída
        platforms:  Plataformas ativas
        ass_files:  Lista de .ass paralela a clips (opcional)
        verbose:    Progresso
        log_dir:    Pasta para logs FFmpeg

    Returns:
        Lista de clips com campo 'exports' adicionado
    """
    results  = []
    iterator = clips

    # ── Melhoria GPT #4: progress bar com tqdm quando disponível ──────────────
    if TQDM_AVAILABLE and not verbose:
        iterator = tqdm(clips, desc="Exportando clips", unit="clip")
    elif TQDM_AVAILABLE and verbose:
        iterator = tqdm(clips, desc="Exportando", unit="clip",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]")

    for i, clip in enumerate(iterator):
        clip_name = f"clip_{str(i+1).zfill(2)}"
        ass       = ass_files[i] if ass_files and i < len(ass_files) else None

        exports = export_clip(
            input_path  = input_path,
            start       = clip["start"],
            end         = clip["end"],
            output_dir  = output_dir,
            clip_name   = clip_name,
            platforms   = platforms,
            ass_path    = ass,
            verbose     = verbose,
            log_dir     = log_dir,
        )
        results.append({**clip, "exports": exports, "clip_name": clip_name})

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════════════════════

def get_platform_summary() -> str:
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║              PERFIS DE EXPORTAÇÃO POR PLATAFORMA             ║")
    lines.append("╠══════════════════════════════════════════════════════════════╣")
    for key, p in PLATFORMS.items():
        lines.append(f"║  {p.name:<22} ({key})")
        lines.append(f"║    Resolução:   {p.width}×{p.height}  {p.aspect_ratio}  {p.fps}fps")
        lines.append(f"║    Bitrate:     vídeo={p.video_bitrate}  áudio={p.audio_bitrate}  {p.audio_sample_rate}Hz")
        lines.append(f"║    Duração máx: {p.max_duration}s  Tamanho máx: {p.max_file_mb}MB")
        lines.append(f"║    Safe zones:  topo={p.safe_zone_top_pct:.0%}  base={p.safe_zone_bottom_pct:.0%}")
        lines.append("║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    return "\n".join(lines)


def check_ffmpeg() -> bool:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(get_platform_summary())

    if not check_ffmpeg():
        print("\n⚠ FFmpeg não encontrado.")
        print("  macOS:   brew install ffmpeg")
        print("  Ubuntu:  sudo apt install ffmpeg")
        print("  Windows: https://ffmpeg.org/download.html")
    else:
        print("\n✓ FFmpeg detectado")

    # Demonstra filtros gerados para diferentes proporções de origem
    print("\n── Filtros adaptados por proporção de origem ──────────────────")
    profile = PLATFORMS["youtube"]
    for src_w, src_h, label in [
        (1920, 1080, "16:9 horizontal (YouTube)"),
        (1080, 1920, "9:16 vertical (TikTok/Shorts)"),
        (1440, 1080, "4:3 (webcam antiga)"),
        (2560, 1080, "21:9 ultrawide"),
        (1080, 1080, "1:1 quadrado (Instagram)"),
    ]:
        vf = build_vf_chain(src_w, src_h, profile)
        print(f"\n  {label} ({src_w}×{src_h}):")
        print(f"    {vf}")
