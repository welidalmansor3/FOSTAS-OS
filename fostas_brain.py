import os
import re
import json
import time
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ImageSearchAgent:
    """Fotoğraf linki ara (indirme değil)"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_image_links(self, query: str, count: int = 5) -> list:
        """Gerçek fotoğraf linklerini ara (Picsum Photos - key yok!)"""
        images = []
        
        # Picsum Photos: Ücretsiz, key yok, hızlı, kaliteli
        # https://picsum.photos - Random real photos
        
        for i in range(count):
            width = 800 if i % 2 == 0 else 600
            height = 600 if i % 2 == 0 else 800
            
            # Picsum: Her çağrı farklı resim verir (seed ile aynı kalır)
            url = f"https://picsum.photos/{width}/{height}?random={i}&seed={query.replace(' ', '')}"
            
            images.append({
                "url": url,
                "title": f"{query} - {i+1}",
                "source": "Picsum Photos"
            })
        
        return images


class FOSTASCore:
    """FOSTAS - GLM-5.2 Only"""

    def __init__(self):
        self.raw_html = ""
        self.image_search_agent = ImageSearchAgent()
        self.generation_log = []
        
        self.glm_key = os.getenv("NV_GLM_KEY")
        self.nv_base_url = "https://integrate.api.nvidia.com/v1"
        self.client = None
        self.status = {}
        
        if self.glm_key:
            try:
                self.client = OpenAI(base_url=self.nv_base_url, api_key=self.glm_key)
                self.status["glm"] = {"ok": True, "error": None}
            except Exception as e:
                self.status["glm"] = {"ok": False, "error": str(e)}
        else:
            self.status["glm"] = {"ok": False, "error": "API key missing"}

    def _log_step(self, action: str):
        """Log işlemi"""
        self.generation_log.append({
            "action": action,
            "timestamp": time.time()
        })

    def _glm_chat(self, prompt: str, max_tokens: int = 8000, temperature: float = 0.7) -> str:
        """GLM-5.2 call"""
        if not self.client:
            return "ERROR: GLM client not initialized"
        
        try:
            completion = self.client.chat.completions.create(
                model="z-ai/glm-5.2",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            return completion.choices[0].message.content
        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            print(f"🔴 GLM ERROR: {error_msg}")
            print(f"📝 Prompt length: {len(prompt)}")
            return error_msg

    def _clean_html(self, code: str) -> str:
        """HTML temizle"""
        code = code.strip()
        code = re.sub(r"^```(html)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
        code = re.sub(r"```", "", code)
        return code.strip()

    def _create_fallback_html(self, prompt: str) -> str:
        """Fallback HTML"""
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FOSTAS</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 32px;
            margin-bottom: 20px;
        }}
        p {{ color: #666; line-height: 1.6; margin: 15px 0; }}
        button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            margin-top: 20px;
        }}
        button:hover {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgba(102,126,234,0.4); }}
    </style>
</head>
<body>
    <div class="container">
        <h1>FOSTAS</h1>
        <p>{prompt[:60]}</p>
        <button onclick="alert('FOSTAS tarafından oluşturuldu!')">Başla</button>
    </div>
</body>
</html>"""

    def generate_app(self, user_prompt: str) -> bool:
        """GLM-5.2 ile uygulama oluştur"""
        
        self.generation_log = []
        self._log_step("🚀 GLM-5.2 başlatıldı...")
        
        # Check GLM status
        if not self.client:
            self._log_step("❌ GLM client not initialized!")
            print("ERROR: GLM client is None!")
            return False
        
        # ===== STEP 1: Image Linki Ara =====
        self._log_step("🖼️ Fotoğraf linki arıyor...")
        
        # Simple image list - don't need GLM for this
        search_terms = ["profesyonel", "modern", "tasarım", "iş", "teknoloji"]
        
        # Fotoğraf linki ara
        all_images = []
        for term in search_terms:
            self._log_step(f"🔍 Arıyor: {term}")
            images = self.image_search_agent.search_image_links(term, count=2)
            all_images.extend(images[:2])
        
        # Unique linkler
        unique_images = {img['url']: img for img in all_images}.values()
        image_list = list(unique_images)[:8]
        
        self._log_step(f"✅ {len(image_list)} fotoğraf linki bulundu")
        
        # ===== STEP 2: HTML Kod Yaz =====
        self._log_step("💻 HTML kod yazılıyor...")
        
        images_json = json.dumps(
            [{"url": img['url'], "title": img['title']} for img in image_list],
            ensure_ascii=False
        )
        
        html_prompt = f"""ISTEK: {user_prompt}

FOTOĞRAFLAR: {images_json[:500]}

TEK HTML DOSYASI YAZ:
- <!DOCTYPE html>
- Responsive
- Modern CSS
- Fotoğraf linkler: <img src="...">
- onclick button'lar
- SPA (tek sayfa, JavaScript ile tab'lar)

SADECE HTML/CSS/JS!"""
        
        code = self._glm_chat(html_prompt, max_tokens=4096, temperature=0.7)
        
        self._log_step("✅ HTML yazıldı")
        
        # ===== STEP 3: Clean & Finalize =====
        self._log_step("🧹 HTML temizleniyor...")
        
        code = self._clean_html(code)
        
        if "<!DOCTYPE" in code or "<html" in code:
            self.raw_html = code
            self._log_step("✅ Uygulama tamamlandı!")
            return True
        else:
            self.raw_html = self._create_fallback_html(user_prompt)
            self._log_step("⚠️ Fallback HTML kullanıldı")
            return True

    def get_logs(self) -> list:
        """Logları al"""
        return self.generation_log
