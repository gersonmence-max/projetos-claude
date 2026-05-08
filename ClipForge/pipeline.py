"""
pipeline.py — Orquestrador principal do ClipForge

Fluxo completo:
  1. Download do áudio (yt-dlp)
  2. Transcrição (faster-whisper medium int8)
  3. Segmentação em chunks (chunking.py)
  4. Scoring dos momentos virais (scoring.py)
  5. Geração de legendas ASS (subtitles.py)
  6. Exportação por plataforma com legenda queimada (ffmpeg_export.py)
  7. Upload nas plataformas ativas (uploader.py)
"""

import os
import json
import time
import hashlib
import subprocess
import tempfile
from pathlib import Path

from chunking import transcription_to_chunks, ContentType, chunks_to_json
from scoring  import rank_chunks, ContentType as ScoringContentType
from ffmpeg_export import export_all_clips, PLATFORMS
from subtitles import generate_ass, SUBTITLE_STYLES
from uploader  import upload_to_platforms


# ── Helpers ───────────────────────────────────────────────────────────────────
def _slug(s):
    import re, unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    s = s.encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

def _cache_key(url):
    return hashlib.md5(url.encode()).hexdigest()[:12]


# ── Pipeline Runner ───────────────────────────────────────────────────────────
class PipelineRunner:
    """
    Executa o pipeline completo e emite eventos SocketIO em tempo real
    para o frontend acompanhar o progresso.
    """

    def __init__(self, sid, socketio, clips_dir, url, folders,
                 platforms, sub_style, sub_font, sub_size,
                 n_clips, min_score):
        self.sid        = sid
        self.io         = socketio
        self.clips_dir  = Path(clips_dir)
        self.url        = url
        self.folders    = folders        # lista de nomes de pasta
        self.platforms  = platforms      # ["yt", "tt", "kw"]
        self.sub_style  = sub_style      # "yellow" | "white" | "blackbg"
        self.sub_font   = sub_font
        self.sub_size   = sub_size
        self.n_clips    = n_clips
        self.min_score  = min_score
        self.cancelled  = False
        self.tmp_dir    = None

    # ── Emit helpers ──────────────────────────────────────────────────────────
    def emit(self, event, data=None):
        self.io.emit(event, data or {}, room=self.sid)

    def log(self, msg, type_="info"):
        self.emit("log", {"msg": msg, "type": type_})

    def step(self, key, state, detail="", badge=""):
        self.emit("step", {"key": key, "state": state, "detail": detail, "badge": badge})

    def progress(self, pct, label=""):
        self.emit("progress", {"pct": pct, "label": label})

    # ── Main flow ─────────────────────────────────────────────────────────────
    def run(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="clipforge_"))
        try:
            self._run_inner()
        except Exception as e:
            self.log(f"Erro crítico: {e}", "error")
            self.emit("pipeline_error", {"msg": str(e)})
        finally:
            self._cleanup()

    def _run_inner(self):
        cache_key    = _cache_key(self.url)
        audio_path   = self.tmp_dir / "audio_temp.mp3"
        whisper_json = self.tmp_dir / "whisper.json"
        cache_dir    = Path(".clipforge_cache")
        cache_dir.mkdir(exist_ok=True)
        cached_json  = cache_dir / f"{cache_key}.json"

        # ── STEP 1: Download ─────────────────────────────────────────────────
        self.step("dl", "active", "conectando ao YouTube...", "rodando")
        self.progress(4, "Baixando áudio...")
        self.log(f"URL: {self.url[:60]}...")
        self.log("yt-dlp --extract-audio --audio-format mp3 --audio-quality 5", "data")

        result = subprocess.run([
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "--no-playlist",
            "-o", str(audio_path),
            self.url
        ], capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp falhou: {result.stderr[-300:]}")

        sz_mb = round(audio_path.stat().st_size / (1024*1024), 1)
        self.log(f"audio_temp.mp3 ({sz_mb}MB)", "ok")
        self.step("dl", "done", f"{sz_mb}MB", f"{sz_mb}mb")
        self.progress(18, "Download concluído")

        if self.cancelled: return

        # ── STEP 2: Transcrição ──────────────────────────────────────────────
        self.step("tr", "active", "faster-whisper medium int8...", "rodando")
        self.progress(22, "Transcrevendo...")
        self.log("faster-whisper medium int8 · word_timestamps=True", "data")

        if cached_json.exists():
            self.log(f"Cache encontrado: {cache_key} — pulando transcrição", "ok")
            whisper_json = cached_json
        else:
            self._run_whisper(audio_path, whisper_json)
            import shutil
            shutil.copy(whisper_json, cached_json)

        # Conta palavras para estatística
        with open(whisper_json) as f:
            wdata = json.load(f)
        n_words = sum(len(seg.get("words", [])) for seg in wdata.get("segments", []))
        dur_min = round(wdata.get("segments", [{}])[-1].get("end", 0) / 60, 1) if wdata.get("segments") else "?"

        self.log(f"{n_words:,} palavras · {dur_min} min", "ok")
        self.step("tr", "done", f"{n_words:,}w", f"{dur_min}min")
        self.progress(50, "Transcrição concluída")

        if self.cancelled: return

        # ── STEP 3: Segmentação + Scoring ────────────────────────────────────
        self.step("ch", "active", "chunking + scoring...", "rodando")
        self.progress(54, "Analisando momentos virais...")
        self.log("chunking.py → scoring.py → Ollama", "data")

        chunks = transcription_to_chunks(
            json_path    = str(whisper_json),
            content_type = ContentType.GENERICO,
            verbose      = False,
        )
        self.log(f"{len(chunks)} chunks segmentados", "data")

        top_chunks = rank_chunks(
            chunks,
            content_type = ScoringContentType.GENERICO,
            top_n        = self.n_clips,
            min_score    = self.min_score,
            use_llm      = True,
            use_audio    = False,
        )

        if not top_chunks:
            raise RuntimeError("Nenhum chunk passou no score mínimo. Tente reduzir o score mínimo.")

        self.log(f"top {len(top_chunks)} clips selecionados", "hl")
        self.step("ch", "done", f"{len(top_chunks)} clips", f"top{len(top_chunks)}")
        self.progress(68, "Scoring concluído")

        if self.cancelled: return

        # ── STEP 4: Legendas ─────────────────────────────────────────────────
        self.step("sub", "active", "gerando legendas .ass...", "rodando")
        self.progress(72, "Gerando legendas...")
        self.log(f"Estilo: {self.sub_style} · fonte: {self.sub_font} · {self.sub_size}px", "sub")

        ass_files = []
        for i, chunk in enumerate(top_chunks):
            ass_path = self.tmp_dir / f"clip_{str(i+1).zfill(2)}.ass"
            generate_ass(
                words      = chunk.word_timestamps,
                output_path= str(ass_path),
                style      = self.sub_style,
                font       = self.sub_font,
                font_size  = self.sub_size,
                start_offset = chunk.chunk_start,
            )
            ass_files.append(str(ass_path))

        self.log(f"{len(ass_files)} arquivos .ass gerados", "ok")
        self.step("sub", "done", f"{len(ass_files)} .ass", self.sub_style)
        self.progress(78, "Legendas OK")

        if self.cancelled: return

        # ── STEP 5: Download do vídeo + Exportação ───────────────────────────
        self.step("ex", "active", "baixando trechos e exportando...", "rodando")
        self.progress(80, "Exportando clips...")

        # Prepara lista de clips com timestamps
        clips_data = [
            {
                "id":    i + 1,
                "start": chunk.chunk_start,
                "end":   chunk.chunk_end,
                "score": chunk.score_final,
                "text":  chunk.text_preview,
                "ass":   ass_files[i],
            }
            for i, chunk in enumerate(top_chunks)
        ]

        # Baixa os trechos do vídeo (só os momentos selecionados)
        video_clips = self._download_video_clips(clips_data)

        # Exporta para cada plataforma com legenda queimada
        exported = []
        active_plats = self.platforms if self.platforms else ["yt"]

        for folder_name in self.folders:
            folder_path = self.clips_dir / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)

            for plat in active_plats:
                if plat not in PLATFORMS:
                    continue
                profile    = PLATFORMS[plat]
                plat_dir   = folder_path / plat
                plat_dir.mkdir(exist_ok=True)

                for i, clip in enumerate(clips_data):
                    src_video = video_clips.get(i)
                    if not src_video or not Path(src_video).exists():
                        continue

                    out_name = f"clip_{str(i+1).zfill(2)}_{plat}.mp4"
                    out_path = plat_dir / out_name

                    self._ffmpeg_encode_with_subs(
                        input_path  = src_video,
                        ass_path    = clip["ass"],
                        output_path = str(out_path),
                        profile     = profile,
                    )

                    sz = round(out_path.stat().st_size / (1024*1024), 1) if out_path.exists() else 0
                    self.log(f"  {out_name} → {folder_name}/{plat}/ ({sz}MB)", "ok")
                    exported.append({
                        "path":     str(out_path),
                        "name":     out_name,
                        "folder":   folder_name,
                        "platform": plat,
                        "score":    clip["score"],
                        "text":     clip["text"],
                        "start":    clip["start"],
                        "end":      clip["end"],
                        "size_mb":  sz,
                    })

        self.step("ex", "done", f"{len(exported)} arq", f"{len(clips_data)}clips")
        self.progress(90, "Exportação concluída")

        if self.cancelled: return

        # ── STEP 6: Upload ────────────────────────────────────────────────────
        if self.platforms:
            self.step("pub", "active", "publicando...", "rodando")
            self.progress(92, "Publicando...")
            upload_results = upload_to_platforms(
                clips     = exported,
                platforms = self.platforms,
                log_fn    = lambda m, t="pub": self.log(m, t),
            )
            self.step("pub", "done",
                      f"{len(self.platforms)} plataforma(s)",
                      f"{len(exported)}posts")
        else:
            self.step("pub", "done", "sem plataformas ativas", "skip")
            upload_results = {}

        self.progress(100, "Concluído!")
        self.log("━━━ PIPELINE COMPLETO ━━━", "hl")

        # Envia resultados para o frontend
        self.emit("pipeline_done", {
            "clips":   exported,
            "n_clips": len(exported),
            "uploads": upload_results,
        })

    # ── Whisper ───────────────────────────────────────────────────────────────
    def _run_whisper(self, audio_path, output_json):
        """Transcreve com faster-whisper medium int8"""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError("faster-whisper não instalado. Execute: pip install faster-whisper")

        self.log("Carregando modelo faster-whisper medium int8...", "data")
        model = WhisperModel("medium", device="auto", compute_type="int8")

        segments, info = model.transcribe(
            str(audio_path),
            word_timestamps = True,
            language        = "pt",
            beam_size       = 5,
        )

        self.log(f"Idioma detectado: {info.language} ({info.language_probability:.0%})", "data")

        # Monta JSON compatível com chunking.py
        segs_list = []
        total_segs = 0
        for seg in segments:
            words = []
            for w in (seg.words or []):
                words.append({"word": w.word, "start": w.start, "end": w.end})
            segs_list.append({
                "start": seg.start,
                "end":   seg.end,
                "text":  seg.text,
                "words": words,
            })
            total_segs += 1
            if total_segs % 20 == 0:
                pct = min(22 + int((seg.end / max(info.duration, 1)) * 28), 49)
                self.progress(pct, f"Transcrevendo... {int(seg.end/60)}min/{int(info.duration/60)}min")

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump({"segments": segs_list}, f, ensure_ascii=False)

    # ── Download de trechos do vídeo ──────────────────────────────────────────
    def _download_video_clips(self, clips_data):
        """Baixa apenas os trechos necessários do vídeo usando yt-dlp --download-sections"""
        video_clips = {}
        for i, clip in enumerate(clips_data):
            out_path = self.tmp_dir / f"raw_{str(i+1).zfill(2)}.mp4"
            start    = max(0, clip["start"] - 1)  # 1s de margem
            end      = clip["end"] + 1

            self.log(f"  baixando trecho {i+1}: {_fmt_time(start)} – {_fmt_time(end)}", "data")

            result = subprocess.run([
                "yt-dlp",
                "--download-sections", f"*{start:.1f}-{end:.1f}",
                "--no-playlist",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "-o", str(out_path),
                self.url,
            ], capture_output=True, text=True, timeout=120)

            if result.returncode == 0 and out_path.exists():
                video_clips[i] = str(out_path)
            else:
                self.log(f"  aviso: falha ao baixar trecho {i+1}", "warn")

        return video_clips

    # ── FFmpeg encode com legenda ─────────────────────────────────────────────
    def _ffmpeg_encode_with_subs(self, input_path, ass_path, output_path, profile):
        """Codifica o clip com legenda queimada e specs da plataforma"""
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", (
                f"scale={profile.width}:-2,"
                f"crop={profile.width}:{profile.height},"
                f"setsar=1,"
                f"fps={profile.fps},"
                f"ass={ass_path}"
            ),
            "-c:v", profile.codec_video,
            "-profile:v", "high",
            "-level", "4.2",
            "-b:v", profile.video_bitrate,
            "-maxrate", profile.video_bitrate,
            "-bufsize", str(int(profile.video_bitrate.replace("M","")) * 2) + "M",
            "-c:a", profile.codec_audio,
            "-b:a", profile.audio_bitrate,
            "-ar", str(profile.audio_sample_rate),
            "-ac", "2",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            self.log(f"  ffmpeg erro: {result.stderr[-200:]}", "warn")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def _cleanup(self):
        """Remove arquivos temporários"""
        if self.tmp_dir and self.tmp_dir.exists():
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.log("Arquivos temporários removidos", "data")


def _fmt_time(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"
