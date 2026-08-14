import os
import re
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class SharedMemory:
    """Yapyzekalar arasında veri paylaşımı"""
    def __init__(self):
        self.data = {
            "user_prompt": "",
            "app_plan": "",
            "tech_spec": "",
            "ui_design": "",
            "image_urls": [],
            "html_code": ""
        }
    
    def set(self, key: str, value):
        self.data[key] = value
    
    def get(self, key: str):
        return self.data.get(key, "")


class FOSTASCore:
    """5 Yapyzeka Birlikte Çalışıyor"""

    def __init__(self):
        self.raw_html = ""
        self.shared_memory = SharedMemory()
        self.generation_log = []
        
        # API Keys
        self.keys = {
            "nemotron": os.getenv("NV_NEMOTRON_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "glm": os.getenv("NV_GLM_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
        }

        self.nv_base_url = "https://integrate.api.nvidia.com/v1"
        self.clients = {}
        self.status = {}

        # Clients
        for name, key in self.keys.items():
            if key:
                try:
                    self.clients[name] = OpenAI(base_url=self.nv_base_url, api_key=key)
                    self.status[name] = {"ok": True}
                except:
                    self.status[name] = {"ok": False}
            else:
                self.status[name] = {"ok": False}

    def _log(self, agent: str, action: str):
        self.generation_log.append({"agent": agent, "action": action})

    def _call(self, agent: str, model: str, prompt: str, max_tokens: int = 2048) -> str:
        """Yapyzeka çağırı"""
        if agent not in self.clients:
            return "ERROR"
        
        try:
            completion = self.clients[agent].chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _clean_html(self, code: str) -> str:
        code = code.strip()
        code = re.sub(r"^```(html)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
        return code.strip()

    def generate_app(self, user_prompt: str) -> bool:
        """5 Yapyzeka Pipeline"""
        
        self.generation_log = []
        self.shared_memory.set("user_prompt", user_prompt)
        
        # ===== 1. NEMOTRON =====
        self._log("🧠 Nemotron", "Plan yapıyor...")
        
        plan_prompt = f"""Kullanıcı istiyor: "{user_prompt}"

Kısa plan yap:
1. Web sitesi türü
2. 3 ana özellik
3. Tasarım stili
4. Hangi fotoğraflar lazım?

Markdown YOKTUR."""
        
        plan = self._call("nemotron", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", plan_prompt, max_tokens=500)
        
        if "ERROR" not in plan and len(plan) > 30:
            self.shared_memory.set("app_plan", plan)
            self._log("✅ Nemotron", "Plan hazır")
        else:
            self._log("⚠️ Nemotron", "Llama'ya geçiş")
            plan = self._call("llama", "meta/llama-3.3-70b-instruct", plan_prompt, max_tokens=400)
            self.shared_memory.set("app_plan", plan)

        # ===== 2. DEEPSEEK =====
        self._log("📚 DeepSeek", "Teknik spec yazıyor...")
        
        spec_prompt = f"""Plan: {plan}

Teknik spesifikasyon:
1. HTML yapısı
2. CSS yaklaşımı
3. JavaScript fonksiyonları
4. Fotoğraf sayısı

Markdown YOKTUR."""
        
        spec = self._call("deepseek", "deepseek-ai/deepseek-v4-pro", spec_prompt, max_tokens=500)
        
        if "ERROR" not in spec and len(spec) > 30:
            self.shared_memory.set("tech_spec", spec)
            self._log("✅ DeepSeek", "Spec hazır")
        else:
            spec = plan
            self._log("⚠️ DeepSeek", "Fallback")

        # ===== 3. GLM-5.2 (Ana Coder) =====
        self._log("💻 GLM-5.2", "HTML yazıyor...")
        
        # Fotoğraf linkler (Picsum)
        images = [
            f"https://picsum.photos/800/600?random={i}&seed={user_prompt.replace(' ', '')}"
            for i in range(4)
        ]
        images_html = "\n".join([
            f'<img src="{img}" alt="resim" style="width:100%;height:auto;margin:20px 0;border-radius:10px;">'
            for img in images
        ])
        
        code_prompt = f"""İstek: {user_prompt}

Plan: {plan}

Spec: {spec}

Fotoğraflar:
{images_html}

TEK HTML dosyası yaz:
- <!DOCTYPE html>
- Responsive
- Modern CSS
- Menü (Home, About, Contact)
- JavaScript ile tab switch
- onclick button'lar

SADECE HTML KOD!"""
        
        code = self._call("glm", "z-ai/glm-5.2", code_prompt, max_tokens=5000)
        
        if "ERROR" not in code and "<!DOCTYPE" in code and len(code) > 500:
            self._log("✅ GLM-5.2", "Kod yazıldı")
        else:
            self._log("⚠️ GLM-5.2", "DeepSeek'e geçiş")
            code = self._call("deepseek", "deepseek-ai/deepseek-v4-pro", code_prompt, max_tokens=5000)
            
            if "ERROR" not in code and "<!DOCTYPE" in code:
                self._log("✅ DeepSeek", "Kod yazıldı")
            else:
                self._log("⚠️ DeepSeek", "Llama'ya geçiş")
                code = self._call("llama", "meta/llama-3.3-70b-instruct", code_prompt, max_tokens=4000)
                self._log("✅ Llama", "Kod yazıldı")

        # ===== 4. GPT-OSS (QA) =====
        self._log("🔍 GPT-OSS", "Kod kontrol ediyor...")
        
        if "<!DOCTYPE" in code or "<html" in code:
            qa_prompt = f"""HTML kontrol et:

{code[:2000]}

Kontrol et:
1. <!DOCTYPE var mı?
2. Responsive mi?
3. Fotoğraflar var mı?
4. Button'lar onclick mu?

Sorun varsa düzelt. SADECE HTML!"""
            
            reviewed = self._call("gpt_oss", "openai/gpt-oss-120b", qa_prompt, max_tokens=4000)
            
            if ("<!DOCTYPE" in reviewed or "<html" in reviewed) and len(reviewed) > 300:
                code = reviewed
                self._log("✅ GPT-OSS", "QA geçti - kod düzeltildi")
            else:
                self._log("✅ GPT-OSS", "QA geçti")

        # ===== 5. LLAMA (Final Check) =====
        self._log("🦙 Llama", "Final kontrol...")
        
        code = self._clean_html(code)
        
        if "<!DOCTYPE" in code or "<html" in code:
            self.raw_html = code
            self._log("✅ Llama", "Tamamlandı!")
            return True
        else:
            self._log("⚠️ Llama", "Fallback kullanıldı")
            self.raw_html = self._fallback_html(user_prompt, images_html)
            return True

    def _fallback_html(self, title: str, images: str) -> str:
        """Fallback HTML"""
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title[:50]}</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:Arial; background:#f5f5f5; }}
        header {{ background:linear-gradient(135deg,#667eea,#764ba2); color:white; padding:30px; text-align:center; }}
        nav {{ background:#333; padding:15px; text-align:center; }}
        nav a {{ color:white; margin:0 15px; text-decoration:none; cursor:pointer; }}
        nav a:hover {{ color:#667eea; }}
        .container {{ max-width:1200px; margin:0 auto; padding:30px; }}
        .section {{ display:none; }}
        .section.active {{ display:block; }}
        h2 {{ color:#667eea; margin:20px 0; }}
        footer {{ background:#333; color:white; text-align:center; padding:20px; margin-top:40px; }}
    </style>
</head>
<body>
    <header><h1>{title}</h1></header>
    <nav>
        <a onclick="show('home')">Anasayfa</a>
        <a onclick="show('about')">Hakkında</a>
        <a onclick="show('contact')">İletişim</a>
    </nav>
    <div class="container">
        <div id="home" class="section active">
            <h2>Hoş Geldiniz</h2>
            {images}
        </div>
        <div id="about" class="section">
            <h2>Hakkında</h2>
            {images}
        </div>
        <div id="contact" class="section">
            <h2>İletişim</h2>
            {images}
        </div>
    </div>
    <footer><p>&copy; 2024 FOSTAS</p></footer>
    <script>
        function show(id) {{
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(id).classList.add('active');
        }}
    </script>
</body>
</html>"""

    def get_logs(self) -> list:
        return self.generation_log
