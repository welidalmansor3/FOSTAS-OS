import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.game_html = "" # Üretilen oyunun HTML kodu burada duracak
        
        self.nv_keys = {
            "glm": os.getenv("NV_GLM_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY")
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

    def _nvidia_chat(self, model_client: str, model_name: str, prompt: str, max_tokens: int = 4096, temperature: float = 0.7, extra_body: dict = None) -> str:
        if model_client not in self.clients:
            return f"Hata: {model_client} client bağlı değil."
        
        client = self.clients[model_client]
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
            return completion.choices[0].message.content
        except Exception as e:
            return f"API Hatası ({model_name}): {str(e)}"

    def generate_game(self, user_prompt: str):
        """Kullanıcının isteğine göre tek dosyalık oynanabilir HTML5 oyunu üretir."""
        
        system_prompt = f"""
        You are an expert HTML5 Game Developer. Your task is to create a fully playable, complete game in a SINGLE HTML file using HTML5 Canvas and JavaScript.
        
        User's Game Request: "{user_prompt}"
        
        STRICT RULES:
        1. Output ONLY raw HTML code. Do not use markdown fences like ```html. Start directly with <!DOCTYPE html>.
        2. The game must be visually appealing. Use CSS to center the canvas and give it a nice dark background.
        3. The game must have a start screen, a game loop, and a game over/restart mechanic.
        4. Implement basic physics, collision, and controls (Keyboard/Mouse).
        5. Do not use any external images or libraries. Draw everything using Canvas API (shapes, colors, text).
        6. Make sure the game fits within an 800x600 canvas size.
        """

        # 1. Önce en güçlü kodlayıcı olan GLM-5.2 ile dene
        code = self._nvidia_chat("glm", "z-ai/glm-5.2", system_prompt, max_tokens=8000, temperature=0.8)
        
        # 2. Hata verirse veya reddederse DeepSeek ile dene
        if "API Hatası" in code or len(code) < 100:
            code = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", system_prompt, max_tokens=8000, extra_body={"chat_template_kwargs":{"thinking":False}})
        
        # 3. O da yapamazsa Llama 3.3 ile dene
        if "API Hatası" in code or len(code) < 100:
            code = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", system_prompt, max_tokens=4000, temperature=0.7)

        # Markdown temizliği
        code = re.sub(r"^```html\n?", "", code.strip())
        code = re.sub(r"\n?```$", "", code.strip())

        if "<!DOCTYPE html>" in code or "<html>" in code:
            self.game_html = code
            return True
        
        self.game_html = "<h1 style='color:red;text-align:center;'>Oyun üretilemedi. Lütfen daha basit bir prompt deneyin.</h1>"
        return False
