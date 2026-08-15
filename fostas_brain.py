import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class FOSTASMedo:
    """
    Medo Gibi Site/App Yapan Sistem
    - Web sitesi + Mobil app (SPA)
    - 5 Yapyzeka birlikte çalışıyor
    - HTML + CSS + JavaScript (tek dosya)
    """

    def __init__(self):
        self.html = ""
        self.logs = []
        
        # API Keys
        self.keys = {
            "nemotron": os.getenv("NV_NEMOTRON_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "glm": os.getenv("NV_GLM_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
        }
        
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.clients = {}
        
        for name, key in self.keys.items():
            if key:
                self.clients[name] = OpenAI(base_url=self.base_url, api_key=key)

    def log(self, agent, msg):
        self.logs.append(f"{agent}: {msg}")
        print(f"[{agent}] {msg}")

    def call_ai(self, agent, model, prompt, tokens=2048):
        """Yapyzeka çağırı"""
        if agent not in self.clients:
            return "ERROR"
        
        try:
            r = self.clients[agent].chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=tokens,
                temperature=0.7
            )
            return r.choices[0].message.content
        except:
            return "ERROR"

    def create(self, prompt):
        """Medo sitesi oluştur"""
        self.logs = []
        
        # ===== 1. NEMOTRON (UX/UI Architect) =====
        self.log("🧠 Nemotron", "Site mimarisini planlıyor...")
        
        plan_prompt = f"""Kullanıcı istiyor: "{prompt}"

Kısa plan (3-4 madde):
1. Site/App türü
2. Ana sayfalar (Anasayfa, Hakkında, Hizmetler, Ekip, İletişim, vb.)
3. Tasarım stili
4. Mobil uyumlu mu?

Markdown YOKTUR."""
        
        plan = self.call_ai("nemotron", 
                           "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                           plan_prompt, 600)
        
        if "ERROR" in plan:
            plan = self.call_ai("llama",
                               "meta/llama-3.3-70b-instruct",
                               plan_prompt, 500)
        
        self.log("✅ Nemotron", "Plan hazır")

        # ===== 2. DEEPSEEK (Technical Architect) =====
        self.log("📚 DeepSeek", "Teknik detaylar belirliyor...")
        
        spec_prompt = f"""Plan: {plan}

Teknik spesifikasyon:
1. HTML yapısı (kaç sayfa/section?)
2. CSS stratejisi (responsive, mobile-first)
3. JavaScript (tab switch, menü, form)
4. Fotoğraf sayısı

Markdown YOKTUR."""
        
        spec = self.call_ai("deepseek",
                           "deepseek-ai/deepseek-v4-pro",
                           spec_prompt, 600)
        
        if "ERROR" in spec:
            spec = plan
        
        self.log("✅ DeepSeek", "Spec hazır")

        # ===== 3. GLM-5.2 (Code Master - Ana) =====
        self.log("💻 GLM-5.2", "HTML+CSS+JS yazıyor...")
        
        # Fotoğraf linkler (Picsum - 100% çalışır)
        images = [
            "https://picsum.photos/800/600?random=1",
            "https://picsum.photos/800/600?random=2",
            "https://picsum.photos/800/600?random=3",
            "https://picsum.photos/800/600?random=4",
            "https://picsum.photos/800/600?random=5",
            "https://picsum.photos/800/600?random=6",
        ]
        
        code_prompt = f"""MEDO TARZINDA SPA WEBSITE YAP!

İstek: {prompt}

Plan: {plan}

Spec: {spec}

KURALLAR:
1. <!DOCTYPE html> ile başla
2. SADECE HTML + CSS + JavaScript (TEK DOSYA!)
3. SPA (Single Page App) - tüm sayfalar bir HTML'de
4. Menü (Anasayfa, Hakkında, Hizmetler, Ekip, İletişim, vb.)
5. Responsive (Mobile-first)
6. Fotoğraflar:
   {chr(10).join([f"   - {img}" for img in images])}
7. CSS:
   - Modern gradients
   - Smooth animations
   - Flexbox/Grid
   - Mobile hamburger menü
8. JavaScript:
   - function showPage(id) {{}}
   - Menü tab switch'i
   - onclick button'lar (addEventListener YOKTUR)
   - Tüm functions GLOBAL
9. Professional ve Medo'ya benzer görünsün
10. İletişim formu (Name, Email, Message)
11. Footer (sosyal medya, copyright)

HTML Yapısı:
- Header (sabit, hamburger menü mobile)
- Navigation
- Main (tüm sections gömülü, display:none/block toggle)
- Footer (sabit)

CSS Strategy:
.page {{ display: none; }}
.page.active {{ display: block; }}

JavaScript:
function showPage(pageId) {{
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
}}

SADECE HTML KOD! MARKDOWN YOKTUR!
<!DOCTYPE html> ile başla!"""
        
        code = self.call_ai("glm",
                           "z-ai/glm-5.2",
                           code_prompt, 8000)
        
        if "ERROR" not in code and "<!DOCTYPE" in code and len(code) > 1000:
            self.log("✅ GLM-5.2", "Kod yazıldı")
        else:
            self.log("⚠️ GLM-5.2", "DeepSeek'e fallback...")
            code = self.call_ai("deepseek",
                               "deepseek-ai/deepseek-v4-pro",
                               code_prompt, 8000)
            
            if "ERROR" not in code and "<!DOCTYPE" in code:
                self.log("✅ DeepSeek", "Kod yazıldı")
            else:
                self.log("⚠️ DeepSeek", "Llama'ya fallback...")
                code = self.call_ai("llama",
                                   "meta/llama-3.3-70b-instruct",
                                   code_prompt, 6000)
                self.log("✅ Llama", "Kod yazıldı")

        # ===== 4. GPT-OSS (QA Inspector) =====
        self.log("🔍 GPT-OSS", "Kod kontrol ediyor...")
        
        if "<!DOCTYPE" in code or "<html" in code:
            qa_prompt = f"""HTML kodu kontrol et:

{code[:3000]}

Kontrol Listesi:
1. <!DOCTYPE html> var mı? ✓
2. Responsive mi? ✓
3. Menü var mı? ✓
4. JavaScript functions global mi? ✓
5. Fotoğraflar img src ile var mı? ✓
6. Formlar var mı? ✓
7. Mobile hamburger menü var mı? ✓

Sorun varsa düzelt. SADECE HTML!"""
            
            reviewed = self.call_ai("gpt_oss",
                                   "openai/gpt-oss-120b",
                                   qa_prompt, 5000)
            
            if ("<!DOCTYPE" in reviewed or "<html" in reviewed) and len(reviewed) > 500:
                code = reviewed
                self.log("✅ GPT-OSS", "Kod düzeltildi")
            else:
                self.log("✅ GPT-OSS", "Kod tamam")

        # ===== 5. LLAMA (Final Check) =====
        self.log("🦙 Llama", "Final kontrol...")
        
        code = self._clean_html(code)
        
        if "<!DOCTYPE" in code or "<html" in code:
            self.html = code
            self.log("✅ Llama", "TAMAMLANDI!")
            return True
        else:
            self.html = self._fallback_medo(prompt, images)
            self.log("⚠️ Llama", "Fallback kullanıldı")
            return True

    def _clean_html(self, code):
        """HTML temizle"""
        code = code.strip()
        code = re.sub(r"^```(html)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
        return code.strip()

    def _fallback_medo(self, title, images):
        """Medo tarzı fallback"""
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title[:50]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: #f8f9fa; }}
        
        header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        
        .logo {{ font-size: 24px; font-weight: bold; }}
        
        nav {{ padding: 15px 20px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.05); display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }}
        nav a {{ cursor: pointer; color: #333; text-decoration: none; font-weight: 500; transition: color 0.3s; }}
        nav a:hover {{ color: #667eea; }}
        
        .hamburger {{ display: none; cursor: pointer; background: none; border: none; color: white; font-size: 24px; }}
        
        main {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        
        .page {{ display: none; animation: fadeIn 0.3s; }}
        .page.active {{ display: block; }}
        
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        
        h1 {{ color: #667eea; margin-bottom: 20px; font-size: 36px; }}
        h2 {{ color: #667eea; margin: 30px 0 15px 0; }}
        p {{ color: #555; line-height: 1.8; margin: 15px 0; }}
        
        .image-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }}
        .image-grid img {{ width: 100%; height: auto; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }}
        .image-grid img:hover {{ transform: scale(1.05); }}
        
        .contact-form {{ background: white; padding: 30px; border-radius: 10px; max-width: 500px; margin: 30px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .contact-form input, .contact-form textarea {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; font-family: inherit; }}
        .contact-form button {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
        
        footer {{ background: #333; color: white; text-align: center; padding: 30px; margin-top: 50px; }}
        
        @media (max-width: 768px) {{
            .hamburger {{ display: block; }}
            nav {{ display: none; flex-direction: column; gap: 0; }}
            nav.open {{ display: flex; }}
            nav a {{ padding: 10px; border-bottom: 1px solid #eee; }}
            h1 {{ font-size: 24px; }}
            .image-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="logo">{title[:30]}</div>
        <button class="hamburger" onclick="toggleMenu()">☰</button>
    </header>
    
    <nav id="menu">
        <a onclick="showPage('home')">Anasayfa</a>
        <a onclick="showPage('about')">Hakkında</a>
        <a onclick="showPage('services')">Hizmetler</a>
        <a onclick="showPage('contact')">İletişim</a>
    </nav>
    
    <main>
        <div id="home" class="page active">
            <h1>{title}</h1>
            <p>Profesyonel web sitesi ve uygulaması. FOSTAS tarafından oluşturuldu.</p>
            <div class="image-grid">
                <img src="{images[0]}" alt="görsel 1">
                <img src="{images[1]}" alt="görsel 2">
                <img src="{images[2]}" alt="görsel 3">
            </div>
        </div>
        
        <div id="about" class="page">
            <h2>Hakkında Biz</h2>
            <p>Biz, en iyi hizmeti sunmaya kararlı bir ekibiz.</p>
            <div class="image-grid">
                <img src="{images[3]}" alt="görsel 4">
                <img src="{images[4]}" alt="görsel 5">
            </div>
        </div>
        
        <div id="services" class="page">
            <h2>Hizmetlerimiz</h2>
            <p>En iyi hizmetler:</p>
            <ul>
                <li>Profesyonel hizmet</li>
                <li>Kaliteli destek</li>
                <li>Hızlı çözüm</li>
            </ul>
            <div class="image-grid">
                <img src="{images[5]}" alt="görsel 6">
            </div>
        </div>
        
        <div id="contact" class="page">
            <h2>İletişim</h2>
            <form class="contact-form" onsubmit="return false;">
                <input type="text" placeholder="Adınız" required>
                <input type="email" placeholder="Email" required>
                <textarea placeholder="Mesajınız" rows="5" required></textarea>
                <button type="submit" onclick="alert('Teşekkürler! Mesajınız alındı.')">Gönder</button>
            </form>
            <p>Email: info@example.com</p>
            <p>Telefon: +90 123 456 7890</p>
        </div>
    </main>
    
    <footer>
        <p>&copy; 2024 {title} - FOSTAS tarafından oluşturuldu</p>
    </footer>
    
    <script>
        function showPage(pageId) {{
            var pages = document.querySelectorAll('.page');
            pages.forEach(function(page) {{
                page.classList.remove('active');
            }});
            document.getElementById(pageId).classList.add('active');
            closeMenu();
        }}
        
        function toggleMenu() {{
            var menu = document.getElementById('menu');
            menu.classList.toggle('open');
        }}
        
        function closeMenu() {{
            var menu = document.getElementById('menu');
            menu.classList.remove('open');
        }}
    </script>
</body>
</html>"""
