import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class WebBuilder:
    """5 Yapyzeka - Web Sitesi Yapan Sistem"""

    def __init__(self):
        self.html = ""
        self.keys = {
            "nemotron": os.getenv("NV_NEMOTRON_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "glm": os.getenv("NV_GLM_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
        }
        self.clients = {}
        for name, key in self.keys.items():
            if key:
                self.clients[name] = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key)

    def call(self, agent, model, prompt, max_tok=2000):
        """Yapyzeka çağrı"""
        if agent not in self.clients:
            return ""
        try:
            resp = self.clients[agent].chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tok, temperature=0.7
            )
            return resp.choices[0].message.content
        except:
            return ""

    def build(self, user_prompt):
        """Web sitesi yap"""
        
        # 1. NEMOTRON - Plan
        plan = self.call("nemotron", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            f"Kullanıcı istiyor: {user_prompt}\n\nKısa plan yap (3 madde). Markdown YOKTUR.", 500)
        if not plan:
            plan = self.call("llama", "meta/llama-3.3-70b-instruct",
                f"Kullanıcı istiyor: {user_prompt}\n\nKısa plan yap (3 madde). Markdown YOKTUR.", 400)

        # 2. DEEPSEEK - Teknik Spec
        spec = self.call("deepseek", "deepseek-ai/deepseek-v4-pro",
            f"Plan: {plan}\n\nTeknik: HTML yapısı, CSS, JS. Markdown YOKTUR.", 500)
        if not spec:
            spec = plan

        # 3. GLM-5.2 - HTML Kod
        images = "\n".join([
            f"<img src='https://picsum.photos/800/600?random={i}' style='width:100%;margin:20px 0;border-radius:10px;'>"
            for i in range(1, 5)
        ])

        code = self.call("glm", "z-ai/glm-5.2",
            f"İstek: {user_prompt}\nPlan: {plan}\nSpec: {spec}\n\nTEK HTML dosyası yaz. Responsive. Menü. Fotoğraf. onclick button'lar. Markdown YOKTUR. <!DOCTYPE html> ile başla!",
            6000)
        
        if "<!DOCTYPE" not in code:
            code = self.call("deepseek", "deepseek-ai/deepseek-v4-pro",
                f"İstek: {user_prompt}\n\nTEK HTML dosyası yaz. Responsive. Modern CSS. Menü. Fotoğraf. onclick button'lar. Markdown YOKTUR. <!DOCTYPE html> ile başla!",
                6000)
        
        if "<!DOCTYPE" not in code:
            code = self.call("llama", "meta/llama-3.3-70b-instruct",
                f"İstek: {user_prompt}\n\nTEK HTML dosyası yaz. Responsive. Modern CSS. Menü. Fotoğraf. onclick button'lar. Markdown YOKTUR. <!DOCTYPE html> ile başla!",
                5000)

        # 4. GPT-OSS - QA
        if "<!DOCTYPE" in code:
            qa = self.call("gpt_oss", "openai/gpt-oss-120b",
                f"HTML kontrol et. <!DOCTYPE var mı? Responsive mi? Button'lar onclick mi? Sorun varsa düzelt. SADECE HTML!\n\n{code[:2000]}",
                4000)
            if "<!DOCTYPE" in qa:
                code = qa

        # 5. LLAMA - Final
        code = re.sub(r"^```(html)?\n?", "", code.strip())
        code = re.sub(r"\n?```$", "", code)
        
        if "<!DOCTYPE" in code:
            self.html = code
        else:
            self.html = self.fallback(user_prompt, images)

    def fallback(self, title, images):
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title[:50]}</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:Arial; background:#f5f5f5; }}
        header {{ background:linear-gradient(135deg,#667eea,#764ba2); color:white; padding:40px; text-align:center; }}
        nav {{ background:#333; padding:20px; text-align:center; }}
        nav a {{ color:white; margin:0 20px; text-decoration:none; cursor:pointer; font-weight:bold; }}
        nav a:hover {{ color:#667eea; }}
        .container {{ max-width:1200px; margin:0 auto; padding:40px; }}
        .section {{ display:none; padding:30px; background:white; border-radius:10px; margin:20px 0; }}
        .section.active {{ display:block; }}
        h2 {{ color:#667eea; margin-bottom:20px; }}
        footer {{ background:#333; color:white; text-align:center; padding:20px; margin-top:40px; }}
        img {{ max-width:100%; height:auto; }}
    </style>
</head>
<body>
    <header><h1>{title}</h1></header>
    <nav>
        <a onclick="show('home')">Home</a>
        <a onclick="show('about')">About</a>
        <a onclick="show('contact')">Contact</a>
    </nav>
    <div class="container">
        <div id="home" class="section active">
            <h2>Welcome</h2>
            {images}
        </div>
        <div id="about" class="section">
            <h2>About</h2>
            {images}
        </div>
        <div id="contact" class="section">
            <h2>Contact</h2>
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
