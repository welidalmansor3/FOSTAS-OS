import os
import re
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.raw_game_html = ""
        self.project_memory = {
            "assets": [], 
            "docs": ""
        }
        
        self.nv_keys = {
            "glm": os.getenv("NV_GLM_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY"),
            "nemotron": os.getenv("NV_NEMOTRON_KEY")
        }

        self.nv_base_url = "https://integrate.api.nvidia.com/v1"
        self.clients = {}
        self.status = {}

        for model_name, key in self.nv_keys.items():
            if key:
                try:
                    self.clients[model_name] = OpenAI(base_url=self.nv_base_url, api_key=key)
                    self.status[model_name] = {"ok": True, "error": None}
                except Exception as e:
                    self.status[model_name] = {"ok": False, "error": str(e)}
            else:
                self.status[model_name] = {"ok": False, "error": "Key .env dosyasında yok."}

    def _nvidia_chat(self, client_key: str, model_name: str, prompt: str, max_tokens: int = 4096, temperature: float = 0.7, extra_body: dict = None) -> str:
        if client_key not in self.clients:
            return ""
        
        client = self.clients[client_key]
        try:
            kwargs = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            if extra_body:
                kwargs["extra_body"] = extra_body

            completion = client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content or ""
        except Exception:
            return ""

    def upload_document(self, text: str):
        self.project_memory["docs"] += "\n\n--- USER UPLOAD ---\n" + text[:3000]

    def register_user_asset(self, filename: str
