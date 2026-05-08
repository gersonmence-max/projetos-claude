import os
from dotenv import load_dotenv

load_dotenv()

class _Config:
    primary_model: str     = os.getenv("PRIMARY_MODEL", "gemini-2.5-flash")
    fallback_model: str    = os.getenv("FALLBACK_MODEL", "llama-3.3-70b-versatile")
    max_fix_attempts: int  = int(os.getenv("MAX_FIX_ATTEMPTS", "3"))
    max_files: int         = int(os.getenv("MAX_FILES", "50"))
    max_output_tokens: int = int(os.getenv("MAX_OUTPUT_TOKENS", "16384"))
    google_api_key: str    = os.getenv("GOOGLE_API_KEY", "")
    groq_api_key: str      = os.getenv("GROQ_API_KEY", "")

config = _Config()
