from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq
from config import config

load_dotenv()


class AIExecutor:
    def __init__(self, model: str = None):
        self.gemini_client = genai.Client(api_key=config.google_api_key)
        self.gemini_model  = model or config.primary_model
        self.groq          = Groq(api_key=config.groq_api_key)
        self.stats         = {"gemini_calls": 0, "groq_calls": 0, "errors": 0}

    def execute(self, prompt: str, urgent: bool = False) -> dict:
        start = datetime.now()
        if urgent:
            result = self._groq(prompt)
        else:
            result = self._gemini(prompt)
        duration = (datetime.now() - start).total_seconds()
        return {
            "success": result["success"],
            "output":  result["output"],
            "model":   result.get("model", self.gemini_model),
            "duration": duration,
        }

    def _gemini(self, prompt: str) -> dict:
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=config.max_output_tokens,
                ),
            )
            self.stats["gemini_calls"] += 1
            return {"success": True, "output": response.text, "model": self.gemini_model}
        except Exception as e:
            print(f"  Gemini falhou: {e} — usando Groq...")
            self.stats["errors"] += 1
            result = self._groq(prompt)
            result["model"] = config.fallback_model
            return result

    def _groq(self, prompt: str) -> dict:
        try:
            response = self.groq.chat.completions.create(
                model=config.fallback_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.max_output_tokens,
            )
            self.stats["groq_calls"] += 1
            return {"success": True, "output": response.choices[0].message.content, "model": config.fallback_model}
        except Exception as e:
            self.stats["errors"] += 1
            return {"success": False, "output": f"ERRO: {e}", "model": config.fallback_model}

    def get_stats(self) -> dict:
        total = self.stats["gemini_calls"] + self.stats["groq_calls"]
        return {**self.stats, "total_calls": total}
