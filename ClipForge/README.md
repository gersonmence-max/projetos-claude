# ClipForge

Detecta automaticamente os melhores momentos de vídeos longos e gera clips curtos prontos para YouTube Shorts, TikTok e Kwai.

## Requisitos

- Python 3.10+
- FFmpeg instalado no sistema
- Conexão com internet (para download dos vídeos)

## Instalação

### macOS / Linux
```bash
bash install.sh
```

### Windows
```
Clique duas vezes em install.bat
(ou execute como Administrador no Prompt de Comando)
```

### Manual (qualquer sistema)
```bash
pip install -r requirements.txt
playwright install chromium
```

## Como rodar

```bash
python app.py
```

Acesse **http://localhost:5000** no navegador.

## Estrutura de pastas

```
ClipForge/
├── app.py              ← servidor web
├── pipeline.py         ← orquestrador do pipeline
├── scoring.py          ← detecção de momentos virais
├── chunking.py         ← segmentação da transcrição
├── subtitles.py        ← geração de legendas .ASS
├── ffmpeg_export.py    ← exportação por plataforma
├── uploader.py         ← upload automático
├── requirements.txt
├── install.sh / .bat
├── static/
│   └── index.html      ← interface web
└── clips/              ← clips gerados (criada automaticamente)
    └── [nome-da-pasta]/
        ├── yt/         ← clips para YouTube Shorts
        ├── tt/         ← clips para TikTok
        └── kw/         ← clips para Kwai
```

## Configuração do YouTube (opcional)

1. Acesse https://console.cloud.google.com
2. Crie um projeto → ative **YouTube Data API v3**
3. Crie credenciais OAuth 2.0 → baixe como `client_secrets.json`
4. Coloque o arquivo na pasta do ClipForge
5. Na primeira vez, o navegador vai abrir para autorização

## Configuração do TikTok (opcional)

1. Instale a extensão **"Get cookies.txt LOCALLY"** no Chrome
2. Acesse tiktok.com e faça login
3. Clique na extensão → **Export As** → salve como `cookies.txt`
4. Coloque na pasta do ClipForge

## Configuração do Kwai (opcional)

Preencha usuário e senha diretamente na interface do app.
O upload usa automação de browser (Playwright) — sem API oficial.

## Ollama / LLM local (opcional, melhora a qualidade)

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh   # macOS/Linux
# Windows: https://ollama.com/download

# Baixar o modelo
ollama pull mistral:7b-instruct
```

O sistema funciona sem o Ollama — ele só melhora a precisão do scoring.

## Tecnologias usadas

| Componente | Ferramenta |
|---|---|
| Download | yt-dlp |
| Transcrição | faster-whisper medium int8 |
| Scoring | heurísticas + VADER + Ollama |
| Legendas | libass (formato .ASS) |
| Exportação | FFmpeg |
| Upload YT | YouTube Data API v3 |
| Upload TikTok | tiktok-uploader |
| Upload Kwai | Playwright |
| Servidor | Flask + SocketIO |
