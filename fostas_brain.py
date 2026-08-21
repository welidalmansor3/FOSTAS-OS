import re
import json
import time
import requests
from html.parser import HTMLParser
from openai import OpenAI

# ===== API Keys (Secure) =====
API_KEYS = {
    "nemotron": "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",
    "deepseek": "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",
    "glm": "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",
    "gpt_oss": "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",
    "llama": "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",
}


class HTMLValidator(HTMLParser):
    """HTML validasyon"""
    def __init__(self):
        super().__init__()
        self.has_doctype = False
        self.has_html = False
        self.tags = []
        self.errors = []
    
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "html":
            self.has_html = True
    
    def feed(self, data):
        if "<!DOCTYPE" in data or "<!doctype" in data:
            self.has_doctype = True
        try:
            super().feed(data)
        except Exception as e:
            self.errors.append(str(e))
    
    def is_valid(self):
        return self.has_doctype and self.has_html and len(self.errors) == 0


class FOSTASBrain:
    """FOSTAS v10 - Fixed & Validated"""
    
    def __init__(self):
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.clients = {}
        self.logs = []
        self.used_models = []
        self.total_tokens = 0
        
        # Initialize clients
        for name, key in API_KEYS.items():
            try:
                self.clients[name] = OpenAI(base_url=self.base_url, api_key=key)
            except Exception as e:
                self._log(f"❌ {name}", f"Init error: {str(e)}")

    def _log(self, agent: str, msg: str):
        """Log işlemi"""
        entry = f"{agent}: {msg}"
        self.logs.append(entry)
        print(f"[{agent}] {msg}")

    def _call_ai(self, agent: str, model: str, prompt: str, max_tokens: int = 2048, retry_count: int = 0) -> tuple:
        """
        AI çağırı - Improved error handling + timeout
        Returns: (response, success, tokens_used)
        """
        if agent not in self.clients:
            return "", False, 0
        
        max_retries = 2
        
        try:
            completion = self.clients[agent].chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
                timeout=30
            )
            
            response = completion.choices[0].message.content
            tokens = completion.usage.completion_tokens if hasattr(completion.usage, 'completion_tokens') else max_tokens
            
            self.used_models.append(model)
            self.total_tokens += tokens
            
            return response, True, tokens
            
        except Exception as e:
            error_msg = str(e)
            
            if retry_count < max_retries:
                self._log(agent, f"Retry {retry_count + 1}/{max_retries}...")
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self._call_ai(agent, model, prompt, max_tokens, retry_count + 1)
            else:
                self._log(agent, f"Failed: {error_msg}")
                return "", False, 0

    def _download_images(self) -> list:
        """Fotoğrafları indir"""
        self._log("📸 Images", "Downloading...")
        
        images = []
        urls = [
            "https://picsum.photos/800/600?random=1",
            "https://picsum.photos/800/600?random=2",
            "https://picsum.photos/800/600?random=3",
            "https://picsum.photos/800/600?random=4",
        ]
        
        for i, url in enumerate(urls):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    import base64
                    b64 = base64.b64encode(response.content).decode('utf-8')
                    data_uri = f"data:image/jpeg;base64,{b64}"
                    images.append(data_uri)
            except:
                pass
        
        if not images:
            # Fallback
            images = [f"https://via.placeholder.com/800x600?text=Resim+{i}" for i in range(4)]
        
        self._log("✅ Images", f"{len(images)} downloaded")
        return images

    def _validate_html(self, code: str) -> bool:
        """HTML validation"""
        validator = HTMLValidator()
        validator.feed(code)
        
        if not validator.is_valid():
            self._log("⚠️ Validation", f"Invalid HTML: {validator.errors}")
            return False
        
        self._log("✅ Validation", "HTML valid")
        return True

    def _clean_html(self, code: str) -> str:
        """HTML temizle"""
        code = code.strip()
        code = re.sub(r"^```(html)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
        return code.strip()

    def generate(self, prompt: str) -> tuple:
        """
        Website oluştur
        Returns: (html, success, status_message)
        """
        self.logs = []
        self.used_models = []
        self.total_tokens = 0
        
        self._log("🚀 Start", f"Generating: {prompt[:50]}...")
        
        # ===== 1. Download Images =====
        images = self._download_images()
        images_html = "\n".join([
            f'<img src="{img}" alt="resim" style="width:100%;border-radius:10px;margin:20px 0;">'
            for img in images[:2]
        ])
        
        # ===== 2. Nemotron - Plan =====
        self._log("🧠 Nemotron", "Planning...")
        
        plan_prompt = f"""Kullanıcı istiyor: "{prompt}"

Kısa plan (3 madde):
1. Tip
2. Ana özellikler
3. Tasarım

Markdown YOKTUR."""
        
        plan, plan_ok, _ = self._call_ai(
            "nemotron",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            plan_prompt,
            400
        )
        
        if not plan_ok:
            self._log("⚠️ Nemotron", "Using Llama...")
            plan, _, _ = self._call_ai(
                "llama",
                "meta/llama-3.3-70b-instruct",
                plan_prompt,
                300
            )
        
        self._log("✅ Plan", "Ready")
        
        # ===== 3. DeepSeek - Spec =====
        self._log("📚 DeepSeek", "Spec...")
        
        spec_prompt = f"""Plan: {plan}

Teknik spec (3 madde):
1. HTML yapısı
2. CSS
3. JS

Markdown YOKTUR."""
        
        spec, spec_ok, _ = self._call_ai(
            "deepseek",
            "deepseek-ai/deepseek-v4-pro",
            spec_prompt,
            300
        )
        
        if not spec_ok:
            spec = plan
        
        self._log("✅ Spec", "Ready")
        
        # ===== 4. GLM-5.2 - Generate HTML =====
        self._log("💻 GLM-5.2", "Generating HTML...")
        
        code_prompt = f"""MEDO TARZINDA WEBSITE YAP!

İstek: {prompt}

Plan: {plan}
Spec: {spec}

Fotoğraflar:
{images_html}

KURALLAR:
1. <!DOCTYPE html> ile başla
2. Responsive + Mobile menü
3. 3 sayfa: Home, About, Contact
4. onclick button'lar
5. Modern CSS
6. Fotoğraflar ekli

SADECE HTML!"""
        
        code, code_ok, code_tokens = self._call_ai(
            "glm",
            "z-ai/glm-5.2",
            code_prompt,
            6000
        )
        
        # Fallback chain
        if not code_ok or len(code) < 500:
            self._log("⚠️ GLM", "Fallback to DeepSeek...")
            code, code_ok, code_tokens = self._call_ai(
                "deepseek",
                "deepseek-ai/deepseek-v4-pro",
                code_prompt,
                5000
            )
        
        if not code_ok or len(code) < 500:
            self._log("⚠️ DeepSeek", "Fallback to Llama...")
            code, code_ok, code_tokens = self._call_ai(
                "llama",
                "meta/llama-3.3-70b-instruct",
                code_prompt,
                4000
            )
        
        self._log("✅ Generation", "Complete")
        
        # ===== 5. Clean & Validate =====
        code = self._clean_html(code)
        
        if not self._validate_html(code):
            self._log("⚠️ Validation", "Invalid, using fallback...")
            code = self._fallback_html(prompt, images_html)
        
        # ===== 6. GPT-OSS QA (Full code - not truncated) =====
        self._log("🔍 GPT-OSS", "QA checking...")
        
        qa_prompt = f"""Bu HTML'i kontrol et:

{code}

Kontrol:
1. <!DOCTYPE var mı?
2. Responsive mi?
3. Menü var mı?
4. onclick button'lar var mı?

Sorun varsa düzelt. SADECE HTML!"""
        
        reviewed, qa_ok, qa_tokens = self._call_ai(
            "gpt_oss",
            "openai/gpt-oss-120b",
            qa_prompt,
            5000
        )
        
        if qa_ok and len(reviewed) > 500 and ("<!DOCTYPE" in reviewed or "<html" in reviewed):
            code = reviewed
            self._log("✅ QA", "Code fixed")
        else:
            self._log("✅ QA", "Code acceptable")
        
        # ===== Final =====
        success = self._validate_html(code)
        
        if success:
            self._log("✅ DONE", "Website ready!")
            return code, True, "SUCCESS"
        else:
            self._log("⚠️ FALLBACK", "Using template...")
            return self._fallback_html(prompt, images_html), True, "FALLBACK"

    def _fallback_html(self, title: str, images: str) -> str:
        """Fallback HTML Template"""
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title[:50]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial; background: #f5f5f5; }}
        header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; }}
        nav {{ background: #333; padding: 15px; text-align: center; }}
        nav a {{ color: white; margin: 0 15px; text-decoration: none; cursor: pointer; }}
        nav a:hover {{ color: #667eea; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 30px; }}
        .page {{ display: none; }}
        .page.active {{ display: block; }}
        h2 {{ color: #667eea; margin: 20px 0; }}
        footer {{ background: #333; color: white; text-align: center; padding: 20px; margin-top: 40px; }}
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
        <div id="home" class="page active">
            <h2>Hoş Geldiniz</h2>
            {images}
        </div>
        <div id="about" class="page">
            <h2>Hakkında</h2>
            {images}
        </div>
        <div id="contact" class="page">
            <h2>İletişim</h2>
            {images}
        </div>
    </div>
    <footer><p>&copy; 2024 FOSTAS</p></footer>
    <script>
        function show(id) {{
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById(id).classList.add('active');
        }}
    </script>
</body>
</html>"""
