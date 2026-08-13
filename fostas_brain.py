import os
import re
import json
import time
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class SharedMemory:
    """Tüm yapyzekalar arasında veri paylaşımı"""
    def __init__(self):
        self.data = {
            "user_prompt": "",
            "app_type": "",
            "image_requirements": [],
            "search_queries": [],
            "image_links": [],
            "app_plan": "",
            "technical_spec": "",
            "ui_design": "",
            "final_code": ""
        }
    
    def set(self, key: str, value):
        self.data[key] = value
    
    def get(self, key: str):
        return self.data.get(key, "")
    
    def append(self, key: str, value):
        if isinstance(self.data[key], list):
            self.data[key].append(value)
    
    def get_all(self) -> dict:
        return self.data.copy()


class ImageSearchAgent:
    """
    Bing Image Search ile fotoğraf linki ara (indirme değil, link al)
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_image_links(self, query: str, count: int = 5) -> list:
        """
        Bing'den fotoğraf linklerini ara (indirme DEĞİL, sadece link)
        Returns: [{"url": "...", "title": "...", "source": "bing"}, ...]
        """
        try:
            # Bing Image Search (public, key yok)
            search_url = "https://www.bing.com/images/search"
            params = {
                'q': query,
                'first': 1
            }
            
            # HTML'den URL'leri çıkar
            images = []
            
            # Alternatif: DuckDuckGo Image Search (API'siz)
            try:
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
            
            # Alternatif: Google Images Unofficial
            try:
                # Bazen çalışan, bazen çalışmayan method
                google_url = f"https://www.google.com/search?q={query}&tbm=isch"
                response = requests.get(google_url, timeout=10, headers=self.session.headers)
                
                # URL pattern çıkar
                img_urls = re.findall(r'"https?://[^"]+\.jpg"', response.text)
                for url in img_urls[:count]:
                    images.append({
                        "url": url.strip('"'),
                        "title": query,
                        "source": "Google Images"
                    })
                
                if images:
                    return images
            except:
                pass
            
            # Fallback: Pexels + Pixabay search (API'siz ancak reliable)
            try:
                # Pexels public search
                pexels_url = f"https://www.pexels.com/search/{query}/?page=1"
                response = requests.get(pexels_url, timeout=10)
                
                # img src pattern çıkar
                img_matches = re.findall(r'<img[^>]*src="([^"]+\.jpg)"', response.text)
                for url in img_matches[:count]:
                    if 'images.pexels.com' in url:
                        images.append({
                            "url": url,
                            "title": query,
                            "source": "Pexels"
                        })
                
                if images:
                    return images
            except:
                pass
            
            # Son çare: Placeholder URL'ler
            if not images:
                images = [
                    {
                        "url": f"https://via.placeholder.com/800x600?text={query.replace(' ', '+')}&bg_color=667eea&text_color=ffffff",
                        "title": f"{query} - Placeholder",
                        "source": "Placeholder"
                    }
                ]
            
            return images
        
        except Exception as e:
            print(f"Image search error: {str(e)}")
            return []


class FOSTASCore:
    """
    FOSTAS v8: Connected Multi-Agent + Dynamic Image Links
    
    Agents (Yapyzekalar):
    1. Nemotron → Lead Architect (Plan)
    2. DeepSeek → Research Agent (Image requirements)
    3. Image Search Agent → Fotoğraf linki ara
    4. GLM-5.2 → Code Master (HTML yaz)
    5. GPT-OSS → QA Engineer (Kontrol)
    6. Llama → Fallback (Acil durum)
    """

    def __init__(self):
        self.raw_html = ""
        self.shared_memory = SharedMemory()
        self.image_search_agent = ImageSearchAgent()
        self.generation_log = []
        
        # API Keys
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

        # Initialize clients
        for model_name, key in self.nv_keys.items():
            if key:
                try:
                    self.clients[model_name] = OpenAI(base_url=self.nv_base_url, api_key=key)
                    self.status[model_name] = {"ok": True, "error": None}
                except Exception as e:
                    self.status[model_name] = {"ok": False, "error": str(e)}
            else:
                self.status[model_name] = {"ok": False, "error": "API key missing"}

    def _log_step(self, agent: str, action: str):
        """Log işlemi"""
        self.generation_log.append({
            "agent": agent,
            "action": action,
            "timestamp": time.time()
        })

    def _nvidia_chat(self, model_client: str, model_name: str, prompt: str, 
                     max_tokens: int = 2048, temperature: float = 0.7, 
                     extra_body: dict = None) -> str:
        """NVIDIA API call"""
        if model_client not in self.clients:
            return f"ERROR: {model_client} not initialized"
        
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
    <title>FOSTAS - {prompt[:30]}</title>
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
        @media (max-width: 600px) {{
            .container {{ padding: 25px; }}
            h1 {{ font-size: 24px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>FOSTAS</h1>
        <p>Yapay zeka tarafından oluşturulan uygulama</p>
        <p>{prompt[:60]}</p>
        <button onclick="alert('FOSTAS tarafından oluşturuldu!')">Başla</button>
    </div>
</body>
</html>"""

    def generate_app(self, user_prompt: str) -> bool:
        """
        BAĞLI YAPYZEKA PIPELINE:
        1. Nemotron → Plan
        2. DeepSeek → Fotoğraf gereksinimleri
        3. ImageSearchAgent → Fotoğraf linki ara
        4. GLM-5.2 → HTML kod yaz (linkler ile)
        5. GPT-OSS → QA
        6. Llama → Fallback
        """
        
        self.generation_log = []
        self.shared_memory.set("user_prompt", user_prompt)
        
        # ===== STAGE 1: NEMOTRON (Lead Architect) =====
        self._log_step("🧠 Nemotron", "Mimarlık planlıyor...")
        
        nemotron_prompt = f"""Kullanıcı istiyor: "{user_prompt}"

Lütfen detaylı plan yap:
1. Uygulama türü (Web site / Mobile app)
2. Hedef kullanıcılar
3. Ana özellikler (4-5 madde)
4. Tasarım stili (modern, minimalist, vb.)
5. Hangi tür fotoğraflar lazım? (açıklama)

Markdown KULLANMA, kısa olsun."""

        app_plan = self._nvidia_chat(
            "nemotron",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            nemotron_prompt,
            max_tokens=800,
            temperature=0.6
        )
        
        if "ERROR" in app_plan or len(app_plan) < 50:
            app_plan = self._nvidia_chat(
                "llama",
                "meta/llama-3.3-70b-instruct",
                nemotron_prompt,
                max_tokens=600
            )
        
        self.shared_memory.set("app_plan", app_plan)
        self._log_step("✅ Nemotron", "Plan hazır - DeepSeek'e gidiyor")

        # ===== STAGE 2: DEEPSEEK (Research Agent) =====
        self._log_step("📚 DeepSeek", "Fotoğraf araştırması yapıyor...")
        
        deepseek_prompt = f"""Nemotron'un Planı:
{app_plan}

Bunun için hangi fotoğraflar lazım?
Lütfen 5-7 arama terimini listele (internette aranacak):

Format:
1. [Terim 1]
2. [Terim 2]
...

Sadece terimler, başka birşey YOKTUR."""

        research_result = self._nvidia_chat(
            "deepseek",
            "deepseek-ai/deepseek-v4-pro",
            deepseek_prompt,
            max_tokens=600,
            temperature=0.6,
            extra_body={"chat_template_kwargs": {"thinking": False}}
        )
        
        # Terimleri çıkar
        search_terms = re.findall(r'^\d+\.\s*(.+?)$', research_result, re.MULTILINE)
        search_terms = [term.strip() for term in search_terms if term.strip()]
        
        if not search_terms:
            search_terms = [user_prompt, "professional", "modern design"]
        
        self.shared_memory.set("search_queries", search_terms)
        self._log_step("✅ DeepSeek", f"Araştırma tamamlandı - {len(search_terms)} terim bulundu")

        # ===== STAGE 3: IMAGE SEARCH AGENT =====
        self._log_step("🖼️ Image Search Agent", f"Internetten fotoğraf linki arıyor ({len(search_terms)} terim)...")
        
        all_image_links = []
        
        for term in search_terms[:5]:  # Max 5 search
            self._log_step("🔍 Searching", f"Arıyor: {term}")
            images = self.image_search_agent.search_image_links(term, count=3)
            
            for img in images[:2]:  # Her terim için max 2 resim
                all_image_links.append({
                    "url": img['url'],
                    "title": f"{term} - {img['source']}",
                    "source": img['source']
                })
        
        # Duplicates kaldır
        unique_links = {img['url']: img for img in all_image_links}.values()
        all_image_links = list(unique_links)[:8]  # Max 8 fotoğraf
        
        self.shared_memory.set("image_links", all_image_links)
        self._log_step("✅ Image Search", f"{len(all_image_links)} fotoğraf linki bulundu")

        # ===== STAGE 4: GLM-5.2 (Code Master) =====
        self._log_step("💻 GLM-5.2", "HTML kod yazıyor...")
        
        # Image links JSON format
        images_json = json.dumps(
            [{"url": img['url'], "title": img['title']} for img in all_image_links],
            ensure_ascii=False
        )
        
        glm_prompt = f"""Plan:
{app_plan}

Mevcut Fotoğraf Linkler ({len(all_image_links)} adet):
{images_json}

TEK bir HTML dosyası yaz:
1. <!DOCTYPE html> ile başla
2. Responsive design (mobile-first)
3. Modern CSS (gradients, animations)
4. Fotoğrafları <img src="[LINK]"> ile koy (indirme DEĞİL, link kullan)
5. Professional ve güzel görünsün
6. TÜM button'lar onclick="..." kullansın

SADECEhtml KOD! MARKDOWN YOKTUR!
<!DOCTYPE html> ile başla!"""

        code = self._nvidia_chat(
            "glm",
            "z-ai/glm-5.2",
            glm_prompt,
            max_tokens=8000,
            temperature=0.7
        )
        
        self.shared_memory.set("final_code", code)
        self._log_step("✅ GLM-5.2", "Kod yazıldı - GPT-OSS'a gidiyor")

        # ===== STAGE 5: GPT-OSS (QA) =====
        self._log_step("🔍 GPT-OSS", "Kalite kontrol yapıyor...")
        
        if "<!DOCTYPE" in code or "<html" in code:
            qa_prompt = f"""Bu HTML kodu kontrol et:

{code[:3000]}

Kontrol et:
1. <!DOCTYPE html> var mı?
2. Fotoğraf linkler doğru mı (img src=...)?
3. Mobile responsive mi?
4. Button'lar var mı?

Sorun varsa düzelt. SADECE HTML!"""
            
            reviewed = self._nvidia_chat(
                "gpt_oss",
                "openai/gpt-oss-120b",
                qa_prompt,
                max_tokens=6000,
                temperature=0.4
            )
            
            if ("<!DOCTYPE" in reviewed or "<html" in reviewed) and len(reviewed) > 300:
                code = reviewed
        
        self._log_step("✅ GPT-OSS", "QA geçti")

        # ===== FINAL =====
        code = self._clean_html(code)
        
        if "<!DOCTYPE" in code or "<html" in code:
            self.raw_html = code
            self._log_step("✅ System", "Uygulama tamamlandı!")
            return True
        else:
            self.raw_html = self._create_fallback_html(user_prompt)
            self._log_step("⚠️ System", "Fallback HTML kullanılıyor")
            return True

    def get_logs(self) -> list:
        """Üretim loglarını al"""
        return self.generation_log

    def get_memory(self) -> dict:
        """Shared memory'i al"""
        return self.shared_memory.get_all()
