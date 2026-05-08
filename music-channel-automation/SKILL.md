---
name: music-channel-automation
description: >
  Automação completa para criar álbuns musicais diários para 4 canais do YouTube.
  Use esta skill sempre que o usuário mencionar: criar álbum, gerar músicas, produção diária,
  Som do Céu, Heaven's Sound, Veylo, Holy Thunder, Suno, compilado, renda passiva com música.
  Cobre todo o fluxo: escolha do canal → geração de letras → criação no Suno AI →
  seleção automática → download → capa no Ideogram → compilado MP4 → upload YouTube.
---

# Music Channel Automation — 4 Canais

## Os 4 Canais

| ID | Canal | Idioma | Estilo | YouTube |
|---|---|---|---|---|
| `gospel-pt` | Som do Céu | Português BR | Gospel coral anos 50, Black Music | ✅ Criado |
| `gospel-en` | Heaven's Sound | Inglês | Gospel coral anos 50, Black Music | 🔲 Criar |
| `rock` | Holy Thunder | Inglês | Rock gospel estilo AC/DC, vocal pesado | 🔲 Criar |
| `electronic` | Veylo | Inglês (mínimo) | Eletrônico instrumental, sem vocal ou vocal mínimo em inglês | ✅ Criado |

**Álbuns:** 18 músicas por canal  
**Frequência:** 1 canal por dia (ou mais conforme créditos disponíveis)  
**Letras:** Claude cria tudo — tema escolhido automaticamente, letras originais a cada álbum

---

## FLUXO COMPLETO

```
1. Identificar canal do dia
        ↓
2. Claude escolhe tema e cria 18 letras originais
        ↓
3. Suno AI → 18 músicas (2 versões cada)
        ↓
4. Selecionar melhor versão de cada música
        ↓
5. Baixar as 18 melhores versões
        ↓
6. Ideogram → Capa do álbum
        ↓
7. ffmpeg → Compilado MP4
        ↓
8. YouTube Studio → Upload
```

---

## ETAPA 1 — Identificar o Canal

O usuário inicia com um comando simples como:
- `"canal gospel português"` → `gospel-pt`
- `"canal inglês"` → `gospel-en`
- `"canal rock"` → `rock`
- `"canal eletrônico"` ou `"veylo"` → `electronic`
- `"próximo canal"` → Claude escolhe o canal que há mais dias sem álbum

Confirmar com o usuário antes de prosseguir:
> "Vou criar o álbum de hoje para o canal **[NOME]**. Tema: **[TEMA]**. Posso começar?"

---

## ETAPA 2 — Geração de Letras por Canal

### Regras gerais para TODAS as letras:
- Cada música deve ter **estrutura única** — nenhuma letra igual ou parecida com as anteriores do álbum
- Linguagem **poética, fluida, bonita de ouvir** — sem repetição excessiva de palavras
- Estrutura sugerida: `[Intro] [Verse 1] [Chorus] [Verse 2] [Chorus] [Bridge] [Outro]`
- **Nunca tradução literal** entre português e inglês — mesma mensagem, expressão diferente
- Comprimento ideal: 20-35 linhas por letra

---

### 🇧🇷 gospel-pt — Som do Céu

**Prompt base para gerar letras:**
```
Crie [N] letras de música gospel coral estilo anos 50 em PORTUGUÊS BRASILEIRO.
Tema geral do álbum: [TEMA]

Regras obrigatórias:
- Escrita 100% em português do Brasil — sem palavras em inglês, sem português de Portugal
- Linguagem poética, fluida, bonita de ouvir — nada repetitivo
- Cada música deve ter título único e mensagem distinta dentro do tema
- Estrutura: [Intro] [Verse 1] [Chorus] [Verse 2] [Chorus] [Bridge] [Outro]
- Tom: alegre, espiritual, esperançoso — estilo coral negro americano dos anos 50 adaptado ao Brasil
- Inspire-se em: hinos tradicionais brasileiros, ritmo de coral negro, swing suave
- Nenhuma letra deve se parecer com as outras do álbum
```

**Style para o Suno:**
```
1950s black gospel choir, vintage soul, call and response vocals, 
warm organ, upright bass, brushed drums, hand claps, joyful congregation,
analog warmth, mono recording feel, Brazilian Portuguese lyrics only,
100% Portuguese Brazil, NO English words
```

---

### 🇺🇸 gospel-en — Heaven's Sound

**Prompt base para gerar letras:**
```
Create [N] gospel choir song lyrics in English.
Album theme: [TEMA — mesma mensagem do gospel-pt, expressão diferente]

Rules:
- Beautiful, poetic English — not a literal translation of the Portuguese version
- Same spiritual message, completely different expression and imagery
- Structure: [Intro] [Verse 1] [Chorus] [Verse 2] [Chorus] [Bridge] [Outro]
- Style: 1950s Black American gospel choir — joyful, soulful, spirited
- Each song must have a unique title and distinct angle on the theme
- No two songs should sound alike in phrasing or structure
```

**Style para o Suno:**
```
1950s Black gospel choir, vintage soul, call and response, 
Hammond organ, upright bass, brushed snare, hand claps, 
joyful congregation, warm analog tone, spiritual and uplifting,
American English gospel tradition
```

---

### 🎸 rock — Holy Thunder

**Prompt base para gerar letras:**
```
Create [N] hard rock gospel song lyrics in English, AC/DC style.
Album theme: [TEMA]

Rules:
- Powerful, anthemic English — made to be sung loud
- Gospel message delivered with rock attitude — bold, defiant, triumphant
- Structure: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Verse 2] [Chorus] [Solo] [Chorus] [Outro]
- Style: AC/DC energy — short punchy lines, strong rhymes, driving rhythm in the words
- Each song distinct — different imagery, different energy level
- Titles should sound like rock songs: bold, punchy, powerful
```

**Style para o Suno:**
```
hard rock, AC/DC style, electric guitar riffs, power chords, 
driving drums, bass groove, raspy male vocals, anthemic chorus,
stadium rock feel, 1980s production, distortion, gospel message,
high energy, loud and proud
```

---

### 🎛️ electronic — Veylo

**Prompt base para gerar letras (quando usar vocal):**
```
Create [N] electronic music tracks. Most should be INSTRUMENTAL.
For tracks with vocals (maximum 3 out of 18): minimal English phrases only.
Album theme: [TEMA]

Rules for instrumental tracks:
- Descriptive title that evokes the mood/atmosphere
- No lyrics needed — just title and vibe description for Suno

Rules for vocal tracks (if any):
- Minimal English — 4 to 8 lines maximum
- Atmospheric, ethereal phrasing — not traditional song structure
- Words that blend into the music, not dominate it
```

**Style para o Suno — Instrumental:**
```
electronic instrumental, no vocals, atmospheric synths, 
deep bass, rhythmic percussion, evolving textures, 
hypnotic groove, professional mix, club-ready,
modern electronic production, 128 BPM
```

**Style para o Suno — Com vocal mínimo:**
```
electronic music, minimal ethereal vocals in English,
atmospheric synths, deep bass, hypnotic, 
vocals as texture not melody, modern production
```

---

## ETAPA 3 — Gerar no Suno AI

**URL:** https://suno.com

### Processo por música:
1. Clicar em **Create** → ativar modo **Custom**
2. Colar a **letra** (ou deixar vazio para instrumentais do Veylo)
3. Colar o **style** do canal correspondente
4. Usar o **título** gerado
5. Clicar em **Create** e aguardar as **2 versões** aparecerem completamente
6. **NÃO avançar** antes da geração terminar (~60-90 segundos)
7. Informar progresso: `"Gerando música 3/18: [título]..."`

### ⚠️ Regras de timing críticas:
- Uma música por vez — nunca iniciar nova geração antes da anterior terminar
- Se aparecer fila ou erro, aguardar 30 segundos e tentar novamente
- Se créditos acabarem, parar imediatamente e avisar o usuário

---

## ETAPA 4 — Selecionar Melhor Versão

Para cada par de versões gerado:

1. **Duração:** preferir a versão mais longa (mais completa)
2. **Título gerado pelo Suno:** versões com títulos mais elaborados tendem a ser melhores
3. **Empate:** sempre escolher versão 1 (primeira gerada)
4. Anotar: `"Música [N]: versão [1 ou 2] selecionada"`

---

## ETAPA 5 — Baixar as Músicas

Para cada música selecionada:
1. Clicar nos **3 pontinhos (...)** → **Download** → **Audio (.mp3)**
2. Aguardar download completar antes de próxima
3. Salvar em: `~/Downloads/[id-canal]_[data]/`
   - Ex: `~/Downloads/gospel-pt_2026-03-11/`
4. Confirmar: `"Baixado: [título] ✓ (X/18)"`

---

## ETAPA 6 — Criar Capa no Ideogram

**URL:** https://ideogram.ai

### Prompts de capa por canal:

**gospel-pt / gospel-en:**
```
A vintage 1950s Black gospel choir performing inside a beautiful church,
warm golden lighting, wooden pews, stained glass windows, white robes,
joyful expressions, oil painting style, rich warm colors,
cinematic album cover composition, [TÍTULO DO ÁLBUM] in elegant vintage serif typography
```

**rock — Holy Thunder:**
```
A dramatic gospel rock concert stage, powerful lightning bolt striking a cross,
electric guitars, dark stormy sky with rays of heavenly light breaking through,
crowd raising hands, high contrast dramatic lighting, heavy metal album art style,
[TÍTULO DO ÁLBUM] in bold distressed metal typography
```

**electronic — Veylo:**
```
Abstract electronic music artwork, geometric light patterns, 
deep space atmosphere, electric blue and purple neon gradients,
flowing energy waves, futuristic and spiritual, 
no people, pure abstract visuals, [TÍTULO DO ÁLBUM] in clean modern sans-serif
```

### Instruções:
1. Proporção **1:1** (quadrado)
2. Gerar → escolher imagem mais harmoniosa
3. Baixar como `capa.jpg` na mesma pasta das músicas

---

## ETAPA 7 — Montar Compilado MP4

```bash
# Variáveis
PASTA=~/Downloads/[id-canal]_[data]
CAPA=$PASTA/capa.jpg

# Converter capa
ffmpeg -i $CAPA -vf scale=1280:1280 /tmp/capa_hd.jpg

# Gerar MP4 por música
for f in $PASTA/*.mp3; do
  nome=$(basename "$f" .mp3)
  ffmpeg -loop 1 -i /tmp/capa_hd.jpg -i "$f" \
    -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
    -pix_fmt yuv420p -shortest "/tmp/${nome}.mp4"
done

# Concatenar
ls /tmp/*.mp4 | sort | awk '{print "file "$0}' > /tmp/lista.txt
ffmpeg -f concat -safe 0 -i /tmp/lista.txt -c copy $PASTA/compilado_final.mp4
```

---

## ETAPA 8 — Upload no YouTube

**URL:** https://studio.youtube.com

### Dados por canal:

| Canal | Conta YouTube | Tags base |
|---|---|---|
| Som do Céu | [conta gospel PT] | gospel, coral, anos 50, black music, adoração |
| Heaven's Sound | [conta gospel EN] | gospel, choir, 1950s, black music, worship |
| Holy Thunder | [conta rock] | gospel rock, christian rock, ACDC style, holy thunder |
| Veylo | [conta eletrônica] | electronic music, instrumental, veylo, ambient |

### Template de título:
- `[Nome do Álbum] | Som do Céu | Gospel Coral Anos 50`
- `[Album Name] | Heaven's Sound | 1950s Gospel Choir`
- `[Album Name] | Holy Thunder | Gospel Rock`
- `[Album Name] | Veylo | Electronic Music`

### Processo:
1. Acessar conta correta do YouTube Studio
2. Upload do `compilado_final.mp4`
3. Thumbnail: usar `capa.jpg`
4. Preencher título, descrição e tags do canal
5. **SEMPRE** mostrar resumo ao usuário e aguardar confirmação antes de publicar

---

## Comando de Início Rápido

O usuário pode iniciar com qualquer um desses formatos:

```
"álbum gospel português"
"álbum gospel inglês"  
"álbum rock"
"álbum eletrônico"
"próximo canal"
"todos os canais hoje"
```

Ao receber o comando, Claude responde imediatamente com:
```
Canal: [NOME]
Tema escolhido: [TEMA]
Músicas: 18
Tempo estimado: ~90 minutos

Posso começar?
```

---

## Tratamento de Erros

| Problema | Ação |
|---|---|
| Suno sem créditos | Parar, avisar usuário, aguardar |
| Suno delira no idioma | Reforçar no style: "100% [idioma], NO other language" |
| Ideogram gera texto ilegível | Gerar sem texto, adicionar título via ffmpeg |
| ffmpeg não instalado | `brew install ffmpeg` (Mac) / `sudo apt install ffmpeg` (Linux) |
| YouTube pede verificação | Pausar, usuário completa manualmente |
| Download trava | Botão direito → Salvar como |
