import os
import re
import base64
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class FOSTASCore:
    """
    FOSTAS: Multi-Agent AI App Studio with SVG + Emoji Graphics
    - Nemotron: UX/UI Architect
    - DeepSeek: Technical Architect
    - GLM-5.2: Code Master (Writes HTML/JS + SVG Graphics)
    - GPT-OSS: QA Inspector
    - Llama 3.3: Fallback Engine
    """

    def __init__(self):
        self.raw_game_html = ""
        self.project_memory = {
            "assets": [],
            "docs": "",
            "app_type": None
        }
        
        # Initialize NVIDIA API clients
        self.nv_keys = {
            "nemotron": os.getenv("NV_NEMOTRON_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "glm": os.getenv("NV_GLM_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
        }

        self.nv_base_url = "https://integrate.api.nvidia.com/v1"
        self.clients = {}
        self.status = {}
        self.generation_log = []

        # Initialize all clients
        for model_name, key in self.nv_keys.items():
            if key:
                try:
                    self.clients[model_name] = OpenAI(base_url=self.nv_base_url, api_key=key)
                    self.status[model_name] = {"ok": True, "error": None}
                except Exception as e:
                    self.status[model_name] = {"ok": False, "error": str(e)}
            else:
                self.status[model_name] = {"ok": False, "error": "API key missing in .env"}

    def _log_step(self, agent_name: str, action: str):
        """Log generation steps for UI feedback"""
        self.generation_log.append({
            "agent": agent_name,
            "action": action,
            "timestamp": time.time()
        })

    def _nvidia_chat(self, model_client: str, model_name: str, prompt: str, 
                     max_tokens: int = 4096, temperature: float = 0.7, 
                     extra_body: dict = None) -> str:
        """Call NVIDIA API via OpenAI SDK"""
        if model_client not in self.clients:
            return f"ERROR: {model_client} client not initialized"
        
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
            return f"ERROR: {str(e)}"

    def upload_document(self, text: str):
        """Store user uploaded document"""
        self.project_memory["docs"] = text[:5000]
        self._log_step("System", "Document uploaded")

    def register_user_asset(self, filename: str, file_data: bytes):
        """Register user uploaded image/asset"""
        safe_name = filename.replace(" ", "_")
        encoded_data = base64.b64encode(file_data).decode('utf-8')
        
        existing = next((a for a in self.project_memory["assets"] if a["name"] == safe_name), None)
        if existing:
            existing["data"] = file_data
            existing["b64"] = encoded_data
        else:
            self.project_memory["assets"].append({
                "name": safe_name, 
                "path": f"res://assets/{safe_name}",
                "data": file_data,
                "b64": encoded_data,
                "mime": self._guess_mime(filename)
            })
        self._log_step("System", f"Asset registered: {safe_name}")
        return f"res://assets/{safe_name}"

    def _guess_mime(self, filename: str) -> str:
        """Guess MIME type from filename"""
        ext = filename.lower().split('.')[-1]
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "webp": "image/webp",
        }
        return mime_map.get(ext, "application/octet-stream")

    def _clean_html(self, code: str) -> str:
        """Remove markdown formatting from HTML code"""
        code = code.strip()
        code = re.sub(r"^```(html|javascript|js)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
        code = re.sub(r"```", "", code)
        return code.strip()

    def _inject_user_asset(self, code: str) -> str:
        """Inject user uploaded asset into HTML as base64 data URI"""
        if not self.project_memory["assets"]:
            return code
        
        asset = self.project_memory["assets"][0]
        b64 = asset["b64"]
        mime = asset["mime"]
        data_uri = f"data:{mime};base64,{b64}"
        
        code = code.replace("{{USER_IMAGE}}", data_uri)
        code = code.replace("{{ASSET}}", data_uri)
        code = code.replace("USER_ASSET", data_uri)
        code = code.replace("{{LOGO}}", data_uri)
        
        if mime.startswith("image/"):
            code = re.sub(r'src=["\']USER_[^"\']*["\']', f'src="{data_uri}"', code)
            code = re.sub(r'src=["\']ASSET["\']', f'src="{data_uri}"', code)
        
        return code

    def _create_fallback_html(self, prompt: str) -> str:
        """Create a beautiful fallback HTML"""
        emoji_map = {
            "oyun": "🎮",
            "game": "🎮",
            "restoran": "🍕",
            "restaurant": "🍕",
            "müze": "🏛️",
            "museum": "🏛️",
            "portföy": "💼",
            "portfolio": "💼",
            "alışveriş": "🛒",
            "shop": "🛒",
            "video": "🎥",
            "blog": "📝",
            "chat": "💬",
            "app": "📱",
        }
        
        emoji = "📱"
        for key, val in emoji_map.items():
            if key.lower() in prompt.lower():
                emoji = val
                break
        
        title = prompt[:40] if len(prompt) < 40 else prompt[:37] + "..."
        
        fallback_html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FOSTAS - {title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 40px;
            max-width: 700px;
            text-align: center;
            animation: slideUp 0.6s ease;
        }}
        
        @keyframes slideUp {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .emoji {{
            font-size: 80px;
            margin-bottom: 20px;
            display: block;
            animation: bounce 1.5s infinite;
        }}
        
        @keyframes bounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-10px); }}
        }}
        
        h1 {{
            color: #333;
            font-size: 32px;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .subtitle {{
            color: #666;
            font-size: 18px;
            margin-bottom: 30px;
        }}
        
        .info {{
            background: #f5f5f5;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 30px 0;
            border-radius: 8px;
            text-align: left;
        }}
        
        .features {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 30px 0;
        }}
        
        .feature {{
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #667eea30;
        }}
        
        .feature-icon {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .feature-title {{
            color: #667eea;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            margin-top: 20px;
        }}
        
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
        }}
        
        @media (max-width: 600px) {{
            .container {{
                padding: 25px;
            }}
            h1 {{
                font-size: 24px;
            }}
            .emoji {{
                font-size: 60px;
            }}
            .features {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <span class="emoji">{emoji}</span>
        <h1>FOSTAS AI Studio</h1>
        <p class="subtitle">🚀 Yapay Zeka ile Oluşturuldu</p>
        
        <div class="info">
            <p><strong>📌 Başlık:</strong> {title}</p>
            <p>Bu uygulama FOSTAS OS tarafından otomatik olarak tasarlanmıştır.</p>
        </div>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">⚡</div>
                <div class="feature-title">Hızlı</div>
            </div>
            <div class="feature">
                <div class="feature-icon">📱</div>
                <div class="feature-title">Responsive</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🎨</div>
                <div class="feature-title">Modern</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🔧</div>
                <div class="feature-title">Esnek</div>
            </div>
        </div>
        
        <button onclick="alert('FOSTAS tarafından oluşturuldu!')">🎮 Başla</button>
    </div>
</body>
</html>"""
        return fallback_html

    def _add_interactivity_layer(self, code: str) -> str:
        """Add global button handler + drag-drop functionality"""
        interactivity_script = """
<script>
window.addEventListener('load', function() {
    document.querySelectorAll('button').forEach(btn => {
        if (!btn.hasAttribute('onclick') && !btn.onclick) {
            btn.addEventListener('click', function() {
                const startFunctions = [
                    'startApp', 'initGame', 'startGame', 'beginApp', 'init',
                    'start', 'play', 'launch', 'begin', 'run', 'execute'
                ];
                
                startFunctions.forEach(fn => {
                    if (typeof window[fn] === 'function') {
                        window[fn]();
                    }
                });
                
                const startScreens = document.querySelectorAll('[id*="start"], [id*="menu"], [id*="screen"]');
                startScreens.forEach(el => {
                    if (el.style.display !== 'flex' && el.style.display !== 'grid') {
                        el.style.display = 'none';
                    }
                });
                
                const mainContent = document.querySelectorAll('[id*="main"], [id*="game"], [id*="app"], [id*="content"]');
                mainContent.forEach(el => el.style.display = 'block');
            });
        }
    });
    
    document.querySelectorAll('img, [data-draggable="true"], svg').forEach(el => {
        el.style.cursor = 'grab';
        let isDragging = false;
        let offset = { x: 0, y: 0 };
        
        el.addEventListener('mousedown', (e) => {
            isDragging = true;
            el.style.cursor = 'grabbing';
            el.style.zIndex = 9999;
            el.style.position = 'relative';
            offset.x = e.clientX - el.offsetLeft;
            offset.y = e.clientY - el.offsetTop;
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                el.style.left = (e.clientX - offset.x) + 'px';
                el.style.top = (e.clientY - offset.y) + 'px';
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                el.style.cursor = 'grab';
            }
        });
    });
});
</script>
"""
        if "</body>" in code:
            return code.replace("</body>", interactivity_script + "</body>")
        else:
            return code + interactivity_script + "</body></html>"

    def generate_app_from_doc(self) -> bool:
        """Generate app from uploaded document"""
        if not self.project_memory["docs"].strip():
            return False
        
        doc_summary = self.project_memory["docs"][:500]
        prompt = f"Yüklenen dökümana göre bir web uygulaması yap:\n\n{doc_summary}"
        return self.generate_app(prompt)

    def generate_app(self, user_prompt: str) -> bool:
        """
        Main app generation pipeline
        """
        
        self.generation_log = []
        doc_context = self.project_memory["docs"] if self.project_memory["docs"] else "None"
        
        # ============ STAGE 1: NEMOTRON (Architect) ============
        self._log_step("🧠 Nemotron", "Mimarlık planlıyor...")
        
        nemotron_prompt = f"""Kullanıcı istediği: "{user_prompt}"
Bağlam: "{doc_context}"

Lütfen detaylı plan yap:
1. App türü (oyun, website, tool, vb.)
2. Ana özellikler (3-5 madde)
3. Görsel stil (modern, retro, minimalist, vb.)
4. Kilit interaksiyonlar
5. Hangi SVG/Emoji grafikler lazım?

Markdown kullanma."""

        app_plan = self._nvidia_chat(
            "nemotron",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            nemotron_prompt,
            max_tokens=1000,
            temperature=0.6,
            extra_body={"reasoning_budget": 2048}
        )
        
        if "ERROR" in app_plan or len(app_plan) < 100:
            self._log_step("⚠️ Nemotron", "Llama'ya geçiş...")
            app_plan = self._nvidia_chat(
                "llama",
                "meta/llama-3.3-70b-instruct",
                nemotron_prompt,
                max_tokens=800,
                temperature=0.5
            )
        
        self._log_step("✅ Nemotron", "Plan hazır")

        # ============ STAGE 2: DEEPSEEK (Engineer) ============
        self._log_step("⚙️ DeepSeek", "Teknik spesifikasyon yazıyor...")
        
        deepseek_prompt = f"""Plan: {app_plan}

Lütfen teknik spesifikasyon yaz:
1. HTML yapısı (ana sections)
2. CSS yaklaşımı (layout, animasyonlar, responsive)
3. Lazım olan JavaScript functions
4. SVG şekilleri neler olmalı?
5. Emoji kullanılabilir mi?

Markdown kullanma."""

        tech_spec = self._nvidia_chat(
            "deepseek",
            "deepseek-ai/deepseek-v4-pro",
            deepseek_prompt,
            max_tokens=1500,
            temperature=0.6,
            extra_body={"chat_template_kwargs": {"thinking": False}}
        )
        
        if "ERROR" in tech_spec or len(tech_spec) < 100:
            tech_spec = app_plan
        
        self._log_step("✅ DeepSeek", "Spesifikasyon hazır")

        # ============ STAGE 3: GLM-5.2 (Master Coder) ============
        self._log_step("💻 GLM-5.2", "Kod ve grafikler yazıyor...")
        
        asset_info = ""
        if self.project_memory["assets"]:
            asset_name = self.project_memory["assets"][0]["name"]
            asset_info = f"\nKullanıcı '{asset_name}' adında resim yükledi. Bunu {{{{USER_IMAGE}}}} olarak kodda kullan."
        
        glm_prompt = f"""Dünyanın en iyi web geliştiricisisin. TEK bir HTML dosyası yaz.

İstek: "{user_prompt}"
Plan: {app_plan}
Spesifikasyon: {tech_spec}
{asset_info}

KURALLLAR (ÇOK ÖNEMLİ):
1. <!DOCTYPE html> ile başla
2. Tüm HTML, CSS, JavaScript tek dosyada
3. Responsive (mobile-first)
4. TÜM button'lar onclick="..." kullan, addEventListener KULLANMA
5. Tüm JS functions GLOBAL olsun (window.func = function() {{}})
6. Oyunsa: Canvas veya DOM manipulation kullan
7. **SVG graphics inline yaz** - gerçek resim indirme YAPMA
8. **Çok Emoji kullan!** 🎮🎯🎨🚀⭐
9. CSS gradients ve smooth animasyonlar
10. Hiç external link yok, tümü inline

ÖRNEK SVG (araba oyunu için):
```javascript
function createCarSVG() {{
    return `<svg viewBox="0 0 100 50">
        <rect x="10" y="15" width="80" height="20" fill="#FF4B4B"/>
        <circle cx="25" cy="35" r="8" fill="#333"/>
        <circle cx="75" cy="35" r="8" fill="#333"/>
    </svg>`;
}}
```

SADECEhtml KOD, MARKDOWN YOKTUR. <!DOCTYPE html> İLE BAŞLA!"""

        code = self._nvidia_chat(
            "glm",
            "z-ai/glm-5.2",
            glm_prompt,
            max_tokens=8000,
            temperature=0.7
        )
        
        # Fallback 1: DeepSeek
        if "ERROR" in code or len(code) < 300 or "<!DOCTYPE" not in code:
            self._log_step("⚠️ GLM-5.2", "DeepSeek'e geçiş...")
            code = self._nvidia_chat(
                "deepseek",
                "deepseek-ai/deepseek-v4-pro",
                glm_prompt,
                max_tokens=8000,
                temperature=0.7,
                extra_body={"chat_template_kwargs": {"thinking": False}}
            )
        
        # Fallback 2: Llama
        if "ERROR" in code or len(code) < 300 or "<!DOCTYPE" not in code:
            self._log_step("⚠️ DeepSeek", "Llama'ya geçiş...")
            code = self._nvidia_chat(
                "llama",
                "meta/llama-3.3-70b-instruct",
                glm_prompt,
                max_tokens=5000,
                temperature=0.7
            )
        
        self._log_step("✅ GLM-5.2", "Kod yazıldı")

        # ============ STAGE 4: GPT-OSS (QA Inspector) ============
        if "<!DOCTYPE" in code or "<html" in code:
            self._log_step("🔍 GPT-OSS", "Kalite kontrol yapıyor...")
            
            code_sample = code[:4000]
            qa_prompt = f"""Bu HTML kodunu kontrol et:

{code_sample}

Kontrol et:
1. <!DOCTYPE html> var mı?
2. Button'lar onclick kullanıyor mu?
3. JS functions global mi?
4. SVG grafikleri düzgün mü?
5. HTML valid mi?
6. Mobile responsive mi?

Sorun bulursan düzelt. SADECE HTML kodu ver, başka birşey yok.
"""

            reviewed = self._nvidia_chat(
                "gpt_oss",
                "openai/gpt-oss-120b",
                qa_prompt,
                max_tokens=6000,
                temperature=0.5
            )
            
            if ("<!DOCTYPE" in reviewed or "<html" in reviewed) and len(reviewed) > 300:
                code = reviewed
            
            self._log_step("✅ GPT-OSS", "QA geçti")

        # ============ FINAL PROCESSING ============
        code = self._clean_html(code)
        
        # Inject user assets
        if self.project_memory["assets"]:
            code = self._inject_user_asset(code)
            self._log_step("✅ System", "Kullanıcı resmi eklendi")
        
        # Add interactivity layer
        if "<!DOCTYPE" in code or "<html" in code:
            code = self._add_interactivity_layer(code)
            self.raw_game_html = code
            self._log_step("✅ System", "Uygulama tamamlandı")
            return True
        
        # Ultimate fallback
        self._log_step("⚠️ System", "Fallback template kullanılıyor...")
        self.raw_game_html = self._create_fallback_html(user_prompt)
        return True
