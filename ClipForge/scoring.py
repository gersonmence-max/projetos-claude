"""
scoring.py — Módulo de scoring para detecção de momentos virais
Integra: heurísticas textuais, análise de áudio, sentimento, flags LLM
Suporta pesos dinâmicos por tipo de conteúdo

Instalação das dependências:
    pip install vaderSentiment librosa numpy requests
"""

import re
import json
import numpy as np
import requests
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


# ── Dependências opcionais ───────────────────────────────────────────────────
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("[scoring] vaderSentiment não encontrado — sentimento desativado")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[scoring] librosa não encontrado — análise de áudio desativada")


# ═══════════════════════════════════════════════════════════════════════════════
# TIPOS E CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

class ContentType(Enum):
    PODCAST_EDUCACIONAL = "podcast_educacional"
    VLOG                = "vlog"
    ENTREVISTA          = "entrevista"
    AULA                = "aula"
    GENERICO            = "generico"


# Pesos dinâmicos por tipo de conteúdo
CONTENT_WEIGHTS: dict = {
    ContentType.PODCAST_EDUCACIONAL: {
        "emocao": 0.20, "densidade": 0.30, "narrativa": 0.20,
        "autonomia": 0.15, "audio": 0.10, "hook": 0.05,
    },
    ContentType.VLOG: {
        "emocao": 0.35, "densidade": 0.10, "narrativa": 0.20,
        "autonomia": 0.15, "audio": 0.15, "hook": 0.05,
    },
    ContentType.ENTREVISTA: {
        "emocao": 0.20, "densidade": 0.15, "narrativa": 0.30,
        "autonomia": 0.20, "audio": 0.10, "hook": 0.05,
    },
    ContentType.AULA: {
        "emocao": 0.15, "densidade": 0.35, "narrativa": 0.15,
        "autonomia": 0.20, "audio": 0.10, "hook": 0.05,
    },
    ContentType.GENERICO: {
        "emocao": 0.25, "densidade": 0.20, "narrativa": 0.20,
        "autonomia": 0.20, "audio": 0.10, "hook": 0.05,
    },
}


@dataclass
class Chunk:
    text: str
    start: float                          # segundos
    end: float                            # segundos
    audio_path: Optional[str] = None      # áudio completo para librosa
    word_timestamps: list = field(default_factory=list)  # [{word, start, end}]


@dataclass
class ChunkScore:
    chunk_start: float
    chunk_end: float
    text_preview: str

    # Dimensões (0.0 – 1.0)
    emocao: float = 0.0
    densidade: float = 0.0
    narrativa: float = 0.0
    autonomia: float = 0.0
    audio: float = 0.0
    hook: float = 0.0

    # Penalizações
    penalty_cansativo: float = 0.0

    # Score final
    score_final: float = 0.0

    # Diagnóstico
    flags: dict = field(default_factory=dict)
    llm_flags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HEURÍSTICAS TEXTUAIS
# ═══════════════════════════════════════════════════════════════════════════════

VIRAL_TRIGGERS = [
    r"\bninguém (te conta|fala|sabe)\b",
    r"\bo segredo (é|está)\b",
    r"\bvou te (contar|mostrar|revelar)\b",
    r"\bisso mudou (minha|a minha)\b",
    r"\bnunca (vi|imaginei|pensei)\b",
    r"\bprecisa (saber|conhecer|ver)\b",
    r"\bna prática\b",
    r"\bna (real|realidade)\b",
    r"\bmas (na verdade|calma)\b",
    r"\bao contrário\b",
    r"\berrei (muito|feio|bastante)\b",
]

SECOND_PERSON = re.compile(r"\b(você|seu|sua|te|teu|tua)\b", re.IGNORECASE)

IMPERATIVE_START = re.compile(
    r"^(faça|use|aprenda|descubra|veja|olha|imagina|pensa|considera|tenta|lembra)\b",
    re.IGNORECASE,
)

NUMBER_WITH_UNIT = re.compile(
    r"\b\d+[\.,]?\d*\s*(%|x|vezes|mil|milhões|bilhões|anos|meses|dias|horas|reais|dólares|kg|km)\b",
    re.IGNORECASE,
)


def score_heuristicas(text: str) -> tuple:
    flags = {}
    pontos = 0.0
    max_pontos = 9.0

    # Gatilhos virais
    gatilhos = [p for p in VIRAL_TRIGGERS if re.search(p, text, re.IGNORECASE)]
    if gatilhos:
        pontos += min(len(gatilhos) * 1.5, 3.0)
        flags["gatilhos_virais"] = len(gatilhos)

    # Pergunta retórica
    if "?" in text:
        pontos += 1.0
        flags["tem_pergunta"] = True

    # Números com unidade
    numeros = NUMBER_WITH_UNIT.findall(text)
    if numeros:
        pontos += min(len(numeros) * 0.5, 1.5)
        flags["numeros"] = numeros

    # Segunda pessoa
    segunda = len(SECOND_PERSON.findall(text))
    if segunda:
        pontos += min(segunda * 0.3, 1.0)
        flags["segunda_pessoa"] = segunda

    # Imperativo no início de frase
    frases = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()][:3]
    for frase in frases:
        if IMPERATIVE_START.match(frase):
            pontos += 0.5
            flags["imperativo"] = True
            break

    # Exclamações
    exc = text.count("!")
    if exc:
        pontos += min(exc * 0.3, 0.9)
        flags["exclamacoes"] = exc

    # Reticências (tensão não resolvida)
    if "..." in text or "…" in text:
        pontos += 0.3
        flags["reticencias"] = True

    return round(min(pontos / max_pontos, 1.0), 3), flags


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DENSIDADE LEXICAL
# ═══════════════════════════════════════════════════════════════════════════════

STOPWORDS_PT = {
    "a", "o", "e", "de", "do", "da", "em", "um", "uma", "para", "com",
    "que", "não", "se", "na", "no", "por", "mais", "como", "mas", "ao",
    "ele", "ela", "eles", "elas", "isso", "este", "esta", "esse", "essa",
    "ter", "ser", "foi", "era", "são", "tem", "então", "assim", "né",
    "tá", "tô", "tava", "tipo", "aí", "daí", "até", "pra", "lá", "já",
    "só", "bem", "muito", "também", "quando", "onde", "aqui",
}


def score_densidade(text: str) -> float:
    palavras = re.findall(r"\b[a-záàâãéêíóôõúüç]{3,}\b", text.lower())
    if not palavras:
        return 0.0
    conteudo = [p for p in palavras if p not in STOPWORDS_PT]
    raw = len(conteudo) / len(palavras)
    # 0.35 = ruim, 0.65 = ótimo
    score = (raw - 0.35) / (0.65 - 0.35)
    return round(max(0.0, min(score, 1.0)), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ESTRUTURA NARRATIVA
# ═══════════════════════════════════════════════════════════════════════════════

STORY_MARKERS = re.compile(
    r"\b(quando eu|lembro que|um dia|foi aí que|até que|de repente|"
    r"na época|faz (um|dois|três) anos|eu tinha|minha história)\b",
    re.IGNORECASE,
)
CONTRAST_MARKERS = re.compile(
    r"\b(mas|porém|contudo|no entanto|apesar|embora|ao contrário|"
    r"só que|na verdade|entretanto)\b",
    re.IGNORECASE,
)
RESOLUTION_MARKERS = re.compile(
    r"\b(resultado|descobri|aprendi|entendi|percebi|mudou|transformou|"
    r"valeu a pena|deu certo|deu errado|conclusão|no fim)\b",
    re.IGNORECASE,
)


def score_narrativa(text: str) -> tuple:
    flags = {}
    pontos = 0.0

    historia  = len(STORY_MARKERS.findall(text))
    contraste = len(CONTRAST_MARKERS.findall(text))
    resolucao = len(RESOLUTION_MARKERS.findall(text))

    if historia:
        pontos += min(historia * 0.4, 1.0)
        flags["historia_pessoal"] = historia
    if contraste:
        pontos += min(contraste * 0.3, 0.6)
        flags["contraste"] = contraste
    if resolucao:
        pontos += min(resolucao * 0.4, 0.8)
        flags["resolucao"] = resolucao
    if historia and contraste and resolucao:
        pontos += 0.5
        flags["narrativa_completa"] = True

    return round(min(pontos / 2.9, 1.0), 3), flags


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AUTONOMIA SEMÂNTICA
# ═══════════════════════════════════════════════════════════════════════════════

DANGLING_PRONOUNS = re.compile(
    r"^(ele|ela|eles|elas|isso|esse|essa|este|esta|aquilo|aquele|aquela|"
    r"como (eu|a gente) (falei|disse|mencionei)|como (vimos|discutimos))\b",
    re.IGNORECASE,
)
SELF_CONTAINED_OPENERS = re.compile(
    r"^(hoje|nesse vídeo|nessa aula|vou (falar|mostrar|explicar)|"
    r"a questão (é|aqui é)|o problema (é|real é)|existe (um|uma)|"
    r"imagina|pensa (comigo|bem)|sabe quando)\b",
    re.IGNORECASE,
)


def score_autonomia(text: str) -> tuple:
    flags = {}
    score = 0.5

    primeira_frase = re.split(r"[.!?\n]", text)[0].strip()

    if DANGLING_PRONOUNS.match(primeira_frase):
        score -= 0.3
        flags["pronome_solto"] = True
    if SELF_CONTAINED_OPENERS.match(primeira_frase):
        score += 0.3
        flags["abertura_autonoma"] = True

    ultima_frase = re.split(r"[.!?\n]", text.strip())[-1].strip()
    if re.search(r"\b(então|aí|mas|e)\s*$", ultima_frase, re.IGNORECASE):
        score -= 0.1
        flags["final_inconclusivo"] = True

    palavras = len(text.split())
    if palavras < 30:
        score -= 0.2
        flags["muito_curto"] = True
    elif palavras > 150:
        score -= 0.1
        flags["muito_longo"] = True

    return round(max(0.0, min(score, 1.0)), 3), flags


# ═══════════════════════════════════════════════════════════════════════════════
# 5. HOOK (primeira frase)
# ═══════════════════════════════════════════════════════════════════════════════

HOOK_STRONG = re.compile(
    r"\b(\d+[\.,]?\d*\s*(%|x|vezes|mil|dólares|reais)|"
    r"você (sabia|sabe|já|nunca)|"
    r"(nunca|sempre|todo mundo|ninguém)|"
    r"o maior|o pior|o melhor)\b",
    re.IGNORECASE,
)
HOOK_VERBS = re.compile(
    r"^(descubra|aprenda|veja|entenda|saiba|imagina|pensa|para de|começa|comece)\b",
    re.IGNORECASE,
)


def score_hook(text: str) -> float:
    frases = [s.strip() for s in re.split(r"[.!?\n]", text) if s.strip()]
    if not frases:
        return 0.0

    primeira = frases[0]
    pontos = 0.0

    if HOOK_STRONG.search(primeira):  pontos += 0.5
    if HOOK_VERBS.match(primeira):    pontos += 0.4
    if "?" in primeira:               pontos += 0.3
    if SECOND_PERSON.search(primeira): pontos += 0.2

    return round(min(pontos, 1.0), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ANÁLISE DE ÁUDIO (librosa)
# ═══════════════════════════════════════════════════════════════════════════════

def score_audio(audio_path: str, start: float, end: float) -> tuple:
    if not LIBROSA_AVAILABLE or not audio_path:
        return 0.5, {"audio": "indisponivel"}

    try:
        y, sr = librosa.load(audio_path, offset=start, duration=(end - start), sr=None)

        rms = librosa.feature.rms(y=y)[0]
        energia_media = float(np.mean(rms))
        energia_std   = float(np.std(rms))

        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
        )
        f0_validos = f0[voiced_flag] if voiced_flag is not None and f0 is not None else np.array([])
        pitch_std  = float(np.std(f0_validos)) if len(f0_validos) > 1 else 0.0

        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)[0]))

        s_energia   = min(energia_media / 0.05, 1.0)
        s_variacao  = min(energia_std   / 0.02, 1.0)
        s_pitch     = min(pitch_std     / 40.0, 1.0)
        s_zcr       = min(zcr           / 0.08, 1.0)

        audio_score = (s_energia * 0.35 + s_variacao * 0.25 +
                       s_pitch   * 0.25 + s_zcr      * 0.15)

        return round(min(audio_score, 1.0), 3), {
            "energia_media":   round(energia_media, 5),
            "energia_std":     round(energia_std,   5),
            "pitch_std_hz":    round(pitch_std,     2),
            "zcr":             round(zcr,           5),
        }

    except Exception as e:
        return 0.5, {"audio_erro": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PENALIZAÇÃO: CLIP CANSATIVO
# ═══════════════════════════════════════════════════════════════════════════════

def penalty_clip_cansativo(text: str) -> tuple:
    flags = {}
    penalidade = 0.0

    palavras = re.findall(r"\b[a-záàâãéêíóôõúüç]{4,}\b", text.lower())
    if not palavras:
        return 0.0, {}

    total  = len(palavras)
    unicos = len(set(palavras))
    repeticao = 1.0 - (unicos / total)

    if repeticao > 0.60:
        penalidade += 0.40
        flags["alta_repeticao"] = round(repeticao, 3)
    elif repeticao > 0.45:
        penalidade += 0.20
        flags["media_repeticao"] = round(repeticao, 3)

    fillers = re.findall(
        r"\b(né|tipo|assim|sabe|entende|quer dizer|ou seja|"
        r"basicamente|literalmente|obviamente)\b",
        text, re.IGNORECASE,
    )
    if len(fillers) / max(total, 1) > 0.08:
        penalidade += 0.25
        flags["filler_words"] = len(fillers)

    return round(min(penalidade, 0.6), 3), flags


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SENTIMENTO (VADER)
# ═══════════════════════════════════════════════════════════════════════════════

_vader = SentimentIntensityAnalyzer() if VADER_AVAILABLE else None


def score_sentimento(text: str) -> float:
    if not _vader:
        return 0.5
    compound = abs(_vader.polarity_scores(text)["compound"])
    return round(min(compound / 0.6, 1.0), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. FLAGS VIA LLM LOCAL (Ollama)
# ═══════════════════════════════════════════════════════════════════════════════

LLM_PROMPT = """Analise o trecho abaixo e responda SOMENTE com JSON válido, sem texto adicional.

Trecho:
"{text}"

Responda exatamente neste formato:
{{
  "tem_historia_pessoal": true,
  "tem_numero_ou_estatistica": false,
  "tem_virada_de_argumento": false,
  "tem_frase_memoravel": true,
  "tem_humor": false,
  "nivel_especificidade": 3,
  "autonomia_do_trecho": 4
}}

nivel_especificidade e autonomia_do_trecho: 1 (fraco) a 5 (ótimo)."""


def score_llm_flags(
    text: str,
    ollama_url: str = "http://localhost:11434/api/generate",
    model: str = "mistral:7b-instruct",
) -> tuple:
    prompt = LLM_PROMPT.format(text=text[:800])

    try:
        resp = requests.post(
            ollama_url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return 0.5, {"llm": "json_nao_encontrado"}

        flags = json.loads(match.group())

        pontos  = 0.25 if flags.get("tem_historia_pessoal")      else 0.0
        pontos += 0.15 if flags.get("tem_numero_ou_estatistica")  else 0.0
        pontos += 0.20 if flags.get("tem_virada_de_argumento")    else 0.0
        pontos += 0.20 if flags.get("tem_frase_memoravel")        else 0.0
        pontos += 0.10 if flags.get("tem_humor")                  else 0.0
        pontos += ((flags.get("nivel_especificidade", 1) - 1) / 4.0) * 0.05
        pontos += ((flags.get("autonomia_do_trecho",  1) - 1) / 4.0) * 0.05

        return round(min(pontos, 1.0), 3), flags

    except requests.exceptions.ConnectionError:
        return 0.5, {"llm": "ollama_offline"}
    except Exception as e:
        return 0.5, {"llm_erro": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ORQUESTRADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def score_chunk(
    chunk: Chunk,
    content_type: ContentType = ContentType.GENERICO,
    use_llm: bool = True,
    use_audio: bool = True,
    ollama_url: str = "http://localhost:11434/api/generate",
    ollama_model: str = "mistral:7b-instruct",
) -> ChunkScore:
    """
    Calcula o score completo de um chunk.
    Aplica pesos dinâmicos baseados no tipo de conteúdo.
    """
    w = CONTENT_WEIGHTS[content_type]
    text = chunk.text
    all_flags = {}

    # ── Camada 1: triagem rápida (sem LLM) ──────────────────────────────────
    s_heuristica, f_h = score_heuristicas(text)
    s_densidade        = score_densidade(text)
    s_narrativa,  f_n  = score_narrativa(text)
    s_autonomia,  f_a  = score_autonomia(text)
    s_hook             = score_hook(text)
    s_sentimento       = score_sentimento(text)
    pen_cansativo, f_c = penalty_clip_cansativo(text)

    all_flags.update(f_h)
    all_flags.update(f_n)
    all_flags.update(f_a)
    all_flags.update(f_c)

    # Emoção = combinação de VADER + heurísticas emocionais
    s_emocao = (s_sentimento * 0.6 + s_heuristica * 0.4)

    # ── Camada 2: áudio (opcional) ───────────────────────────────────────────
    s_audio = 0.5
    if use_audio and chunk.audio_path:
        s_audio, f_audio = score_audio(chunk.audio_path, chunk.start, chunk.end)
        all_flags["audio"] = f_audio

    # ── Camada 3: LLM local (opcional, só se passou na triagem) ─────────────
    llm_flags = {}
    s_llm = 0.5
    score_pre_llm = (
        s_emocao   * w["emocao"]   +
        s_densidade * w["densidade"] +
        s_narrativa * w["narrativa"] +
        s_autonomia * w["autonomia"] +
        s_audio    * w["audio"]    +
        s_hook     * w["hook"]
    )

    if use_llm and score_pre_llm > 0.35:  # só analisa candidatos promissores
        s_llm, llm_flags = score_llm_flags(text, ollama_url, ollama_model)
        # LLM refina autonomia e narrativa com peso pequeno
        s_narrativa = s_narrativa * 0.7 + s_llm * 0.3
        s_autonomia = s_autonomia * 0.7 + s_llm * 0.3

    # ── Score composto com pesos dinâmicos ───────────────────────────────────
    score_bruto = (
        s_emocao    * w["emocao"]    +
        s_densidade * w["densidade"] +
        s_narrativa * w["narrativa"] +
        s_autonomia * w["autonomia"] +
        s_audio     * w["audio"]     +
        s_hook      * w["hook"]
    )

    score_final = max(0.0, round(score_bruto - pen_cansativo, 3))

    return ChunkScore(
        chunk_start      = chunk.start,
        chunk_end        = chunk.end,
        text_preview     = text[:120] + "..." if len(text) > 120 else text,
        emocao           = round(s_emocao,    3),
        densidade        = round(s_densidade, 3),
        narrativa        = round(s_narrativa, 3),
        autonomia        = round(s_autonomia, 3),
        audio            = round(s_audio,     3),
        hook             = round(s_hook,      3),
        penalty_cansativo = pen_cansativo,
        score_final      = score_final,
        flags            = all_flags,
        llm_flags        = llm_flags,
    )


def rank_chunks(
    chunks: list[Chunk],
    content_type: ContentType = ContentType.GENERICO,
    top_n: int = 10,
    min_score: float = 0.40,
    use_llm: bool = True,
    use_audio: bool = True,
    ollama_url: str = "http://localhost:11434/api/generate",
    ollama_model: str = "mistral:7b-instruct",
) -> list[ChunkScore]:
    """
    Processa todos os chunks e retorna os top_n por score_final.

    Pipeline de 3 passagens:
      1. Heurísticas rápidas — filtra 70% dos chunks
      2. LLM só nos candidatos promissores
      3. Retorna top_n com score acima de min_score
    """
    resultados = []

    for i, chunk in enumerate(chunks):
        score = score_chunk(
            chunk,
            content_type = content_type,
            use_llm      = use_llm,
            use_audio    = use_audio,
            ollama_url   = ollama_url,
            ollama_model = ollama_model,
        )
        resultados.append(score)
        print(f"  [{i+1:03d}/{len(chunks)}] {chunk.start:.1f}s – {chunk.end:.1f}s  "
              f"score={score.score_final:.3f}  "
              f"hook={score.hook:.2f}  narrativa={score.narrativa:.2f}")

    # Filtra e ordena
    filtrados = [r for r in resultados if r.score_final >= min_score]
    filtrados.sort(key=lambda r: r.score_final, reverse=True)

    return filtrados[:top_n]


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO DE USO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Chunks de exemplo (normalmente gerados pelo módulo de transcrição)
    exemplos = [
        Chunk(
            text=(
                "Vou te contar uma coisa que ninguém fala sobre investimentos. "
                "Quando eu tinha 25 anos, perdi tudo que tinha economizado em 6 meses. "
                "Mas na verdade, esse foi o melhor erro da minha vida. "
                "Aprendi que 80% dos investidores iniciantes cometem esse mesmo erro."
            ),
            start=124.5,
            end=151.2,
        ),
        Chunk(
            text=(
                "Ele disse que ia fazer. Aí então eu falei pra ele que sim. "
                "E aí né, tipo, foi o que aconteceu basicamente. "
                "Mas enfim, aí a gente foi lá e tal."
            ),
            start=300.0,
            end=318.0,
        ),
        Chunk(
            text=(
                "Descubra como triplicar sua produtividade em 30 dias. "
                "Você sabia que 92% das pessoas usam o método errado de gestão de tempo? "
                "Resultado: trabalham mais e produzem menos."
            ),
            start=450.0,
            end=468.0,
        ),
    ]

    print("=" * 60)
    print("SCORING DE CHUNKS — EXEMPLO")
    print("=" * 60)

    top = rank_chunks(
        exemplos,
        content_type = ContentType.PODCAST_EDUCACIONAL,
        top_n        = 5,
        min_score    = 0.30,
        use_llm      = False,   # mude para True com Ollama rodando
        use_audio    = False,   # mude para True com áudio disponível
    )

    print("\n── TOP CLIPS ─────────────────────────────────────────────")
    for i, s in enumerate(top, 1):
        print(f"\n#{i}  score={s.score_final:.3f}  [{s.chunk_start:.1f}s – {s.chunk_end:.1f}s]")
        print(f"    Emoção={s.emocao:.2f}  Densidade={s.densidade:.2f}  "
              f"Narrativa={s.narrativa:.2f}  Autonomia={s.autonomia:.2f}  Hook={s.hook:.2f}")
        print(f"    Penalidade={s.penalty_cansativo:.2f}")
        print(f"    Flags: {s.flags}")
        print(f"    Preview: {s.text_preview}")
