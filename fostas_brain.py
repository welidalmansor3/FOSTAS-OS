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
        """DuckDuckGo'dan fotoğraf linki ara"""
        try:
            images = []
            
            # DuckDuckGo Image Search
            ddg_url = f"https://duckduckgo.com/i.js?q={query}&count={count}"
            response = requests.get(ddg_url, timeout=10, headers=self.session.headers)
            
            if response.status_code == 200:
                data = response.json()
                for result in data.get('results', [])[:count]:
                    images.append({
                        "url": result['image'],
                        "title": result.get('title', query),
                        "source": "DuckDuckGo"
                    })
                return images
        except:
            pass
        
        # Fallback
        return [
            {
                "url": f"https://via.placeholder.com/800x600?text={query.replace(' ', '+')}&bg_color=667eea&text_color=ffffff",
                "title": f"{query} - Placeholder",
                "source": "Placeholder"
            }
        ]


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
            return f"ERROR: {str(e)}"

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
        
        # ===== STEP 1: Image Linki Ara =====
        self._log_step("🖼️ Fotoğraf linki arıyor...")
        
        # Search terms çıkar
        search_prompt = f"""Şu istek için hangi fotoğraflar lazım?
"{user_prompt}"

Lütfen 3-5 arama terimi yaz (virgüllerle ayrılmış):
Örn: müze, antik eserler, iç mimar"""
        
        search_result = self._glm_chat(search_prompt, max_tokens=256, temperature=0.5)
        
        # Terimleri parse et
        search_terms = [term.strip() for term in search_result.split(",")][:5]
        
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
        
        html_prompt = f"""İstek: "{user_prompt}"

Mevcut fotoğraf linkler ({len(image_list)} adet):
{images_json}

TEK bir HTML dosyası yaz:
1. <!DOCTYPE html> ile başla
2. Responsive design (mobile-first)
3. Modern CSS (gradients, smooth animations)
4. Fotoğrafları <img src="[LINK]"> ile koy
5. Professional ve güzel görünsün
6. TÜM button'lar onclick="..." kullansın
7. Hiç external link yok, her şey inline

SADECE HTML KOD! MARKDOWN YOKTUR!
<!DOCTYPE html> ile başla!"""
        
        code = self._glm_chat(html_prompt, max_tokens=8000, temperature=0.8)
        
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
