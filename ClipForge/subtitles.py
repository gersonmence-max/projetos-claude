"""
subtitles.py — Geração de arquivos .ASS para legendas queimadas nos clips

Três estilos:
  yellow  → amarelo intenso com contorno preto (padrão viral TikTok/Shorts)
  white   → branco com sombra preta (podcast/entrevista)
  blackbg → fundo preto sólido com texto branco (máxima legibilidade)

O arquivo .ASS é depois passado para o FFmpeg via filtro ass= para queimar
a legenda diretamente no vídeo exportado.
"""

from pathlib import Path


# ── Configurações por estilo ───────────────────────────────────────────────────
SUBTITLE_STYLES = {
    "yellow": {
        "label":       "Viral amarela",
        "primary":     "&H0000FFFF",   # amarelo (BGR no ASS)
        "outline":     "&H00000000",   # preto
        "shadow":      "&H00000000",
        "outline_size": 3,
        "shadow_depth": 0,
        "bold":        1,
        "border_style": 1,             # outline + drop shadow
        "back_color":  "&H00000000",
    },
    "white": {
        "label":       "Branca limpa",
        "primary":     "&H00FFFFFF",   # branco
        "outline":     "&H00000000",
        "shadow":      "&H80000000",   # sombra semitransparente
        "outline_size": 1,
        "shadow_depth": 2,
        "bold":        1,
        "border_style": 1,
        "back_color":  "&H00000000",
    },
    "blackbg": {
        "label":       "Fundo preto",
        "primary":     "&H00FFFFFF",   # branco
        "outline":     "&H00000000",
        "shadow":      "&H00000000",
        "outline_size": 0,
        "shadow_depth": 0,
        "bold":        0,
        "border_style": 3,             # caixa opaca (fundo sólido)
        "back_color":  "&H00000000",   # preto opaco
    },
}

# Fontes recomendadas (fáceis de ler em vídeo vertical)
FONT_MAP = {
    "Arial Black":         "Arial Black",
    "Impact":              "Impact",
    "Montserrat ExtraBold":"Montserrat",
    "Oswald Bold":         "Oswald",
    "Bebas Neue":          "Bebas Neue",
}


def _ass_time(seconds: float) -> str:
    """Converte segundos para formato ASS: H:MM:SS.cs"""
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass(
    words:        list[dict],
    output_path:  str,
    style:        str = "yellow",
    font:         str = "Arial Black",
    font_size:    int = 52,
    words_per_line: int = 3,
    start_offset: float = 0.0,
    video_width:  int = 1080,
    video_height: int = 1920,
    margin_v:     int = 180,   # margem vertical da base (px)
) -> str:
    """
    Gera um arquivo .ASS com as legendas do clip.

    Args:
        words:          Lista de {"word": str, "start": float, "end": float}
                        com timestamps absolutos do vídeo original
        output_path:    Caminho do arquivo .ass a criar
        style:          "yellow" | "white" | "blackbg"
        font:           Nome da fonte
        font_size:      Tamanho da fonte em pixels
        words_per_line: Quantas palavras por linha de legenda
        start_offset:   Timestamp de início do clip (para relativizar os tempos)
        video_width/height: Dimensões do vídeo (para cálculo de margem)
        margin_v:       Margem da base em pixels

    Returns:
        Caminho do arquivo .ass criado
    """
    cfg   = SUBTITLE_STYLES.get(style, SUBTITLE_STYLES["yellow"])
    fname = FONT_MAP.get(font, font)

    # ── Cabeçalho ASS ──────────────────────────────────────────────────────────
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{fname},{font_size},{cfg['primary']},&H000000FF,{cfg['outline']},{cfg['back_color']},{cfg['bold']},0,0,0,100,100,0,0,{cfg['border_style']},{cfg['outline_size']},{cfg['shadow_depth']},2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # ── Agrupa palavras em linhas ──────────────────────────────────────────────
    events = []
    if not words:
        Path(output_path).write_text(header, encoding="utf-8")
        return output_path

    # Normaliza timestamps para relativos ao início do clip
    def rel(t):
        return max(0.0, t - start_offset)

    # Agrupa em blocos de words_per_line palavras
    i = 0
    while i < len(words):
        block = words[i : i + words_per_line]
        if not block:
            break

        t_start = rel(block[0]["start"])
        t_end   = rel(block[-1]["end"])

        # Garante duração mínima de 0.3s
        if t_end - t_start < 0.3:
            t_end = t_start + 0.3

        text = " ".join(w["word"].strip() for w in block)

        # Formata texto uppercase para estilo viral
        if style == "yellow":
            text = text.upper()

        events.append(
            f"Dialogue: 0,{_ass_time(t_start)},{_ass_time(t_end)},Default,,0,0,0,,{text}"
        )
        i += words_per_line

    # ── Escreve arquivo ────────────────────────────────────────────────────────
    content = header + "\n".join(events) + "\n"
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path


# ── Teste standalone ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Simula palavras com timestamps
    mock_words = []
    sentence = "vou te contar uma coisa que ninguém fala sobre isso".split()
    t = 0.0
    for w in sentence:
        dur = 0.3 + len(w) * 0.04
        mock_words.append({"word": w, "start": t, "end": t + dur})
        t += dur + 0.05

    for style in ["yellow", "white", "blackbg"]:
        out = f"/tmp/test_{style}.ass"
        generate_ass(mock_words, out, style=style, start_offset=0.0)
        print(f"✓ {style}: {out}")
        with open(out) as f:
            lines = f.readlines()
        print(f"  {len(lines)} linhas — primeiros eventos:")
        for l in lines[-4:]:
            print(f"  {l.rstrip()}")
        print()
