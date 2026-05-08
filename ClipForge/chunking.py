"""
chunking.py — Segmentação inteligente de transcrições Whisper em Chunks
Compatível diretamente com scoring.py

Instalação:
    pip install faster-whisper  # opcional, para transcrever direto daqui

Uso básico:
    from chunking import transcription_to_chunks, ChunkConfig, ContentType
    from scoring  import rank_chunks

    chunks = transcription_to_chunks("whisper_output.json", config=ChunkConfig())
    top    = rank_chunks(chunks, top_n=10)
"""

import json
import re
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# Importa Chunk do scoring.py (devem estar no mesmo diretório)
try:
    from scoring import Chunk, ContentType
except ImportError:
    # Definição local de fallback caso scoring.py não esteja presente
    from dataclasses import dataclass as _dc
    from typing import Optional as _Opt

    @_dc
    class Chunk:
        text: str
        start: float
        end: float
        audio_path: Optional[str] = None
        word_timestamps: list = field(default_factory=list)

    class ContentType(Enum):
        PODCAST_EDUCACIONAL = "podcast_educacional"
        VLOG                = "vlog"
        ENTREVISTA          = "entrevista"
        AULA                = "aula"
        GENERICO            = "generico"


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChunkConfig:
    """
    Parâmetros de segmentação — todos ajustáveis por tipo de conteúdo.
    """
    # Tamanho alvo em palavras
    chunk_words: int        = 75
    overlap_pct: float      = 0.20       # 20% de overlap entre chunks

    # Duração em segundos
    min_duration: float     = 20.0       # chunk menor que isso é descartado
    max_duration: float     = 90.0       # chunk maior é dividido forçadamente

    # Qualidade mínima
    min_useful_words: int   = 20         # palavras após remover stopwords/fillers
    max_filler_ratio: float = 0.25       # até 25% de filler words é tolerado

    # Detecção de pausa (silêncio entre palavras)
    pause_threshold: float  = 0.6        # segundos — pausa natural de fala
    long_pause: float       = 1.5        # pausa longa = possível ponto de corte

    # Diagnóstico
    include_diagnostics: bool = True


# Perfis pré-definidos por tipo de conteúdo
CONTENT_CONFIGS: dict = {
    ContentType.PODCAST_EDUCACIONAL: ChunkConfig(
        chunk_words=85, overlap_pct=0.20, min_duration=25.0, max_duration=80.0
    ),
    ContentType.VLOG: ChunkConfig(
        chunk_words=60, overlap_pct=0.25, min_duration=15.0, max_duration=60.0
    ),
    ContentType.ENTREVISTA: ChunkConfig(
        chunk_words=90, overlap_pct=0.15, min_duration=20.0, max_duration=90.0
    ),
    ContentType.AULA: ChunkConfig(
        chunk_words=100, overlap_pct=0.20, min_duration=30.0, max_duration=90.0
    ),
    ContentType.GENERICO: ChunkConfig(),
}


# ═══════════════════════════════════════════════════════════════════════════════
# STOPWORDS E FILLERS
# ═══════════════════════════════════════════════════════════════════════════════

STOPWORDS_PT = {
    "a", "o", "e", "de", "do", "da", "em", "um", "uma", "para", "com",
    "que", "não", "se", "na", "no", "por", "mais", "como", "mas", "ao",
    "ele", "ela", "eles", "elas", "isso", "este", "esta", "esse", "essa",
    "ter", "ser", "foi", "era", "são", "tem", "então", "assim", "até",
    "pra", "lá", "já", "só", "bem", "muito", "também", "quando", "onde",
}

FILLER_WORDS = {
    "né", "tipo", "assim", "sabe", "entende", "quer", "dizer", "ou",
    "seja", "basicamente", "literalmente", "obviamente", "enfim", "enfim",
    "tá", "tô", "tava", "aí", "daí", "ah", "eh", "hm", "hmm", "ahn",
}


def _is_useful_word(word: str) -> bool:
    w = re.sub(r"[^a-záàâãéêíóôõúüç]", "", word.lower())
    return len(w) >= 3 and w not in STOPWORDS_PT and w not in FILLER_WORDS


def _filler_ratio(words: list[str]) -> float:
    if not words:
        return 0.0
    fillers = sum(1 for w in words if re.sub(r"\W", "", w.lower()) in FILLER_WORDS)
    return fillers / len(words)


# ═══════════════════════════════════════════════════════════════════════════════
# PARSING DO JSON DO WHISPER
# ═══════════════════════════════════════════════════════════════════════════════

def load_whisper_json(path: str) -> list[dict]:
    """
    Carrega saída do Whisper e normaliza para lista de palavras com timestamps.

    Suporta dois formatos comuns:
      - faster-whisper / whisper.cpp com word_timestamps=True
        {"segments": [{"words": [{"word": "...", "start": 0.0, "end": 0.5}]}]}
      - Whisper Python padrão (word-level via flag --word_timestamps True)
        {"segments": [{"words": [{"word": "...", "start": 0.0, "end": 0.5}]}]}

    Retorna lista plana: [{"word": str, "start": float, "end": float}, ...]
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    words: list[dict] = []

    # Formato com segments → words
    if "segments" in data:
        for seg in data["segments"]:
            seg_words = seg.get("words", [])
            for w in seg_words:
                word_text = w.get("word", w.get("text", "")).strip()
                if not word_text:
                    continue
                words.append({
                    "word":  word_text,
                    "start": float(w.get("start", 0)),
                    "end":   float(w.get("end",   0)),
                })
        if words:
            return words

    # Formato plano: lista de words diretamente
    if isinstance(data, list) and data and "word" in data[0]:
        return [
            {"word": w["word"].strip(), "start": float(w["start"]), "end": float(w["end"])}
            for w in data if w.get("word", "").strip()
        ]

    raise ValueError(
        "Formato de JSON não reconhecido. "
        "Certifique-se de gerar com --word_timestamps True no Whisper."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DETECÇÃO DE PAUSAS NATURAIS
# ═══════════════════════════════════════════════════════════════════════════════

def _find_pause_boundaries(words: list[dict], threshold: float) -> list[int]:
    """
    Retorna índices onde a pausa entre palavra[i].end e palavra[i+1].start
    é maior que threshold segundos.
    Esses são pontos naturais de corte.
    """
    boundaries = []
    for i in range(len(words) - 1):
        gap = words[i + 1]["start"] - words[i]["end"]
        if gap >= threshold:
            boundaries.append(i)
    return boundaries


def _snap_to_pause(
    target_idx: int,
    pause_boundaries: list[int],
    window: int = 8,
) -> int:
    """
    Ajusta o índice de corte para a pausa natural mais próxima dentro de ±window palavras.
    Se não encontrar pausa, retorna o índice original.
    """
    candidates = [b for b in pause_boundaries if abs(b - target_idx) <= window]
    if not candidates:
        return target_idx
    return min(candidates, key=lambda b: abs(b - target_idx))


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO DE ABERTURA AUTOSSUFICIENTE
# ═══════════════════════════════════════════════════════════════════════════════

DANGLING_START = re.compile(
    r"^(ele|ela|eles|elas|isso|esse|essa|este|esta|aquilo|aquele|aquela|"
    r"e aí|então|mas aí|aí então|como (eu |a gente )?(falei|disse|mencionei))\b",
    re.IGNORECASE,
)


def _fix_dangling_start(
    start_idx: int,
    words: list[dict],
    pause_boundaries: list[int],
    max_lookback: int = 15,
) -> int:
    """
    Se o chunk começa com pronome solto, recua até a pausa anterior.
    Evita clips que começam no meio de uma ideia.
    """
    first_words = " ".join(w["word"] for w in words[start_idx: start_idx + 5])
    if not DANGLING_START.match(first_words.strip()):
        return start_idx

    # Procura pausa anterior dentro de max_lookback palavras
    earlier = [b for b in pause_boundaries if b < start_idx and b >= start_idx - max_lookback]
    if earlier:
        return earlier[-1] + 1  # começa após a pausa
    return start_idx


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTRUÇÃO DOS CHUNKS COM OVERLAP
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChunkDiagnostic:
    total_words: int
    useful_words: int
    filler_ratio: float
    duration: float
    has_long_pause: bool
    start_is_clean: bool
    rejection_reason: Optional[str] = None


def _build_chunk(
    words: list[dict],
    start_idx: int,
    end_idx: int,
    audio_path: Optional[str],
    config: ChunkConfig,
) -> tuple[Optional[Chunk], ChunkDiagnostic]:
    """
    Constrói um Chunk a partir de uma fatia de words[start_idx:end_idx].
    Retorna (Chunk, diagnostico) ou (None, diagnostico) se o chunk for rejeitado.
    """
    slice_words = words[start_idx:end_idx]
    if not slice_words:
        diag = ChunkDiagnostic(0, 0, 0.0, 0.0, False, False, "vazio")
        return None, diag

    text = " ".join(w["word"] for w in slice_words)
    word_list = [w["word"] for w in slice_words]
    start_sec = slice_words[0]["start"]
    end_sec   = slice_words[-1]["end"]
    duration  = end_sec - start_sec

    useful = sum(1 for w in word_list if _is_useful_word(w))
    filler = _filler_ratio(word_list)
    has_long_pause = any(
        slice_words[i + 1]["start"] - slice_words[i]["end"] >= config.long_pause
        for i in range(len(slice_words) - 1)
    )
    clean_start = not DANGLING_START.match(text.strip()[:60])

    diag = ChunkDiagnostic(
        total_words    = len(word_list),
        useful_words   = useful,
        filler_ratio   = round(filler, 3),
        duration       = round(duration, 2),
        has_long_pause = has_long_pause,
        start_is_clean = clean_start,
    )

    # Filtros de qualidade
    if duration < config.min_duration:
        diag.rejection_reason = f"muito_curto ({duration:.1f}s < {config.min_duration}s)"
        return None, diag

    if duration > config.max_duration:
        diag.rejection_reason = f"muito_longo ({duration:.1f}s > {config.max_duration}s)"
        # Não rejeita — será subdividido pelo chamador
        return None, diag

    if useful < config.min_useful_words:
        diag.rejection_reason = f"poucas_palavras_uteis ({useful} < {config.min_useful_words})"
        return None, diag

    if filler > config.max_filler_ratio:
        diag.rejection_reason = f"filler_excessivo ({filler:.0%} > {config.max_filler_ratio:.0%})"
        return None, diag

    chunk = Chunk(
        text             = text,
        start            = start_sec,
        end              = end_sec,
        audio_path       = audio_path,
        word_timestamps  = slice_words,
    )
    return chunk, diag


# ═══════════════════════════════════════════════════════════════════════════════
# SUBDIVISÃO DE CHUNKS LONGOS
# ═══════════════════════════════════════════════════════════════════════════════

def _split_long_chunk(
    words: list[dict],
    start_idx: int,
    end_idx: int,
    pause_boundaries: list[int],
    config: ChunkConfig,
    audio_path: Optional[str],
) -> list[tuple]:
    """
    Divide um chunk longo em sub-chunks usando pausas como pontos de corte.
    Retorna lista de (Chunk | None, ChunkDiagnostic).
    """
    results = []
    mid_target = start_idx + (end_idx - start_idx) // 2
    split_point = _snap_to_pause(mid_target, pause_boundaries, window=15)

    if split_point <= start_idx or split_point >= end_idx:
        # Não achou pausa boa — força no meio
        split_point = mid_target

    for s, e in [(start_idx, split_point + 1), (split_point + 1, end_idx)]:
        result = _build_chunk(words, s, e, audio_path, config)
        results.append(result)

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def words_to_chunks(
    words: list[dict],
    config: Optional[ChunkConfig] = None,
    audio_path: Optional[str] = None,
    verbose: bool = False,
) -> tuple[list[Chunk], list[ChunkDiagnostic]]:
    """
    Converte lista de palavras com timestamps em Chunks com overlap.

    Args:
        words:      Lista de {"word", "start", "end"} — saída normalizada do Whisper
        config:     ChunkConfig com parâmetros de segmentação
        audio_path: Caminho do arquivo de áudio (para score_audio no scoring.py)
        verbose:    Imprime diagnóstico de cada chunk

    Returns:
        (lista de Chunks aceitos, lista de ChunkDiagnostics de todos)
    """
    if config is None:
        config = ChunkConfig()

    overlap_words = max(1, int(config.chunk_words * config.overlap_pct))
    step          = config.chunk_words - overlap_words

    pause_boundaries = _find_pause_boundaries(words, config.pause_threshold)

    chunks: list[Chunk]            = []
    diagnostics: list[ChunkDiagnostic] = []

    i = 0
    chunk_idx = 0

    while i < len(words):
        end_i = min(i + config.chunk_words, len(words))

        # Snap do fim para pausa natural
        end_i = _snap_to_pause(end_i, pause_boundaries, window=8) + 1
        end_i = min(end_i, len(words))

        # Snap do início — corrige pronome solto
        start_i = _fix_dangling_start(i, words, pause_boundaries)

        chunk, diag = _build_chunk(words, start_i, end_i, audio_path, config)

        # Chunk muito longo → subdivide
        if diag.rejection_reason and "muito_longo" in diag.rejection_reason:
            sub_results = _split_long_chunk(
                words, start_i, end_i, pause_boundaries, config, audio_path
            )
            for sub_chunk, sub_diag in sub_results:
                chunk_idx += 1
                diagnostics.append(sub_diag)
                if sub_chunk:
                    chunks.append(sub_chunk)
                    if verbose:
                        _print_diag(chunk_idx, sub_chunk, sub_diag)
        else:
            chunk_idx += 1
            diagnostics.append(diag)
            if chunk:
                chunks.append(chunk)
                if verbose:
                    _print_diag(chunk_idx, chunk, diag)
            elif verbose and diag.rejection_reason:
                print(f"  [chunk {chunk_idx:03d}] REJEITADO — {diag.rejection_reason}")

        i += step
        if end_i >= len(words):
            break

    return chunks, diagnostics


def transcription_to_chunks(
    json_path: str,
    config: Optional[ChunkConfig] = None,
    content_type: Optional[ContentType] = None,
    audio_path: Optional[str] = None,
    verbose: bool = True,
) -> list[Chunk]:
    """
    Pipeline completo: JSON do Whisper → lista de Chunks prontos para o scoring.

    Args:
        json_path:    Caminho para o JSON gerado pelo Whisper
        config:       ChunkConfig manual (se None, usa perfil do content_type)
        content_type: Tipo de conteúdo para selecionar perfil automático
        audio_path:   Caminho do áudio (opcional, para análise de áudio no scoring)
        verbose:      Imprime resumo do processo

    Returns:
        Lista de Chunks prontos para rank_chunks() do scoring.py
    """
    if config is None:
        ct = content_type or ContentType.GENERICO
        config = CONTENT_CONFIGS.get(ct, ChunkConfig())

    if verbose:
        print(f"[chunking] Carregando: {json_path}")

    words = load_whisper_json(json_path)

    if verbose:
        duracao_total = words[-1]["end"] if words else 0
        print(f"[chunking] {len(words)} palavras  |  duração: {duracao_total/60:.1f} min")
        print(f"[chunking] Config: chunk={config.chunk_words}w  "
              f"overlap={config.overlap_pct:.0%}  "
              f"min={config.min_duration}s  max={config.max_duration}s")
        print("-" * 60)

    chunks, diagnostics = words_to_chunks(
        words,
        config     = config,
        audio_path = audio_path,
        verbose    = verbose,
    )

    rejeitados = sum(1 for d in diagnostics if d.rejection_reason)

    if verbose:
        print("-" * 60)
        print(f"[chunking] Total gerado:   {len(diagnostics)}")
        print(f"[chunking] Aceitos:        {len(chunks)}")
        print(f"[chunking] Rejeitados:     {rejeitados}")
        if chunks:
            duracoes = [c.end - c.start for c in chunks]
            print(f"[chunking] Duração média:  {sum(duracoes)/len(duracoes):.1f}s")
            print(f"[chunking] Duração min:    {min(duracoes):.1f}s")
            print(f"[chunking] Duração max:    {max(duracoes):.1f}s")

    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════════════════════

def _print_diag(idx: int, chunk: Chunk, diag: ChunkDiagnostic) -> None:
    dur = chunk.end - chunk.start
    print(
        f"  [chunk {idx:03d}]  {chunk.start:.1f}s–{chunk.end:.1f}s  "
        f"({dur:.1f}s)  "
        f"úteis={diag.useful_words}  "
        f"filler={diag.filler_ratio:.0%}  "
        f"{'✓pausa' if diag.has_long_pause else ''}  "
        f"{'✓abertura' if diag.start_is_clean else '⚠pronome'}"
    )


def chunks_to_json(chunks: list[Chunk], output_path: str) -> None:
    """Serializa chunks para JSON (útil para cache entre etapas do pipeline)."""
    data = [
        {
            "text":  c.text,
            "start": c.start,
            "end":   c.end,
            "word_timestamps": c.word_timestamps,
        }
        for c in chunks
    ]
    Path(output_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[chunking] {len(chunks)} chunks salvos em {output_path}")


def chunks_from_json(json_path: str, audio_path: Optional[str] = None) -> list[Chunk]:
    """Carrega chunks de um JSON salvo anteriormente (cache)."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return [
        Chunk(
            text            = c["text"],
            start           = c["start"],
            end             = c["end"],
            audio_path      = audio_path,
            word_timestamps = c.get("word_timestamps", []),
        )
        for c in data
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO DE USO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile, os

    # ── Simula saída do Whisper com word-level timestamps ────────────────────
    mock_words = []
    sentences = [
        # Chunk 1: narrativa forte — deve ser aceito
        "Vou te contar uma coisa que ninguém fala sobre produtividade".split(),
        "Quando eu tinha 22 anos eu trabalhava 14 horas por dia e não produzia nada".split(),
        "Aí eu descobri um método que triplicou minha produtividade em 30 dias".split(),

        # Pausa longa simulada aqui (será refletida nos timestamps)

        # Chunk 2: filler excessivo — deve ser rejeitado
        "Né tipo assim sabe eu acho que basicamente literalmente".split(),
        "Aí né tipo foi isso mesmo sabe literalmente enfim".split(),

        # Pausa longa

        # Chunk 3: início com pronome solto — sistema deve recuar
        "Ela então decidiu que isso era o melhor caminho".split(),
        "E aí né o resultado foi incrível surpreendente".split(),

        # Chunk 4: conteúdo educacional denso — deve pontuar bem
        "Existem três estratégias comprovadas para escalar um negócio digital".split(),
        "A primeira é automação inteligente com ferramentas de baixo custo".split(),
        "A segunda é criação de conteúdo consistente com análise de dados".split(),
        "A terceira e mais importante é construir um sistema de recorrência".split(),
    ]

    t = 0.0
    for sentence in sentences:
        for word in sentence:
            duration = 0.25 + len(word) * 0.03
            mock_words.append({"word": word, "start": round(t, 2), "end": round(t + duration, 2)})
            t += duration + 0.05
        t += 0.8  # pausa entre frases

    # Pausa longa entre chunk 1 e chunk 2
    mock_words[len(sentences[0]) + len(sentences[1]) + len(sentences[2]) - 1]["end"] -= 0.3
    if len(mock_words) > 30:
        mock_words[30]["start"] = mock_words[29]["end"] + 2.0  # pausa de 2s

    # Salva mock como JSON no formato Whisper
    whisper_mock = {"segments": [{"words": mock_words}]}
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(whisper_mock, tmp, ensure_ascii=False)
    tmp.close()

    print("=" * 60)
    print("CHUNKING — EXEMPLO COM MOCK WHISPER")
    print("=" * 60)

    chunks = transcription_to_chunks(
        json_path    = tmp.name,
        content_type = ContentType.PODCAST_EDUCACIONAL,
        verbose      = True,
    )

    print(f"\n── {len(chunks)} CHUNKS PRONTOS PARA O SCORING ──────────────")
    for i, c in enumerate(chunks, 1):
        dur = c.end - c.start
        print(f"\n#{i}  [{c.start:.1f}s – {c.end:.1f}s]  ({dur:.1f}s)")
        print(f"    {c.text[:100]}{'...' if len(c.text) > 100 else ''}")

    # Salva e recarrega (teste de cache)
    cache_path = "/tmp/chunks_cache.json"
    chunks_to_json(chunks, cache_path)
    reloaded = chunks_from_json(cache_path)
    print(f"\n[cache] Recarregados: {len(reloaded)} chunks de {cache_path}")

    os.unlink(tmp.name)

    # ── Integração completa com scoring ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("INTEGRAÇÃO chunking → scoring")
    print("=" * 60)

    try:
        from scoring import rank_chunks, ContentType as ScoringContentType
        top = rank_chunks(
            chunks,
            content_type = ScoringContentType.PODCAST_EDUCACIONAL,
            top_n        = 5,
            min_score    = 0.20,
            use_llm      = False,
            use_audio    = False,
        )
        print(f"\n── TOP {len(top)} CLIPS ──────────────────────────────────")
        for i, s in enumerate(top, 1):
            print(f"#{i}  score={s.score_final:.3f}  "
                  f"[{s.chunk_start:.1f}s–{s.chunk_end:.1f}s]  "
                  f"hook={s.hook:.2f}  narrativa={s.narrativa:.2f}")
            print(f"    {s.text_preview[:90]}")
    except ImportError:
        print("[scoring] não encontrado — rode com scoring.py no mesmo diretório")
