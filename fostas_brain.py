import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class MEDOSite:
    """MEDO Tıbbi Kliniği Web Sitesi"""

    def __init__(self):
        self.html = ""
        
        # API Keys
        self.keys = {
            "nemotron": os.getenv("NV_NEMOTRON_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "glm": os.getenv("NV_GLM_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
        }
        
        self.url = "https://integrate.api.nvidia.com/v1"
        self.clients = {}
        
        for name, key in self.keys.items():
            if key:
                try:
                    self.clients[name] = OpenAI(base_url=self.url, api_key=key)
                except:
                    pass

    def _call(self, agent: str, model: str, prompt: str) -> str:
        """Yapyzeka çağır"""
        if agent not in self.clients:
            return ""
        
        try:
            response = self.clients[agent].chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except:
            return ""

    def create(self) -> bool:
        """MEDO Sitesi Oluştur"""
        
        # 1. NEMOTRON - Plan
        plan = self._call(
            "nemotron",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            """MEDO tıbbi kliniği web sitesi için plan yap:
1. Hero section
2. Hizmetler (doktor, muayane, ameliyat, test)
3. Doktor ekibi
4. Fiyatlar
5. İletişim
6. Footer

Kısa olsun."""
        )
        
        if not plan:
            plan = "MEDO tıbbi kliniği profesyonel web sitesi"

        # 2. DEEPSEEK - Teknik Spec
        spec = self._call(
            "deepseek",
            "deepseek-ai/deepseek-v4-pro",
            f"""Plan: {plan}

Teknik spesifikasyon:
1. Header (logo, menu)
2. Hero (başlık, call-to-action)
3. Hizmetler (4 card)
4. Doktorlar (3 profil)
5. Fiyatlar (tablo)
6. İletişim (form)
7. Footer

HTML/CSS/JS"""
        )
        
        if not spec:
            spec = "Profesyonel medikal tasarım"

        # Fotoğraflar
        images = [
            "https://picsum.photos/800/600?random=1&seed=medical",
            "https://picsum.photos/800/600?random=2&seed=medical",
            "https://picsum.photos/800/600?random=3&seed=medical",
            "https://picsum.photos/800/600?random=4&seed=medical",
        ]
        
        img_html = "\n".join([
            f'<img src="{img}" alt="MEDO" class="clinic-img">'
            for img in images
        ])

        # 3. GLM-5.2 - HTML Kod
        code = self._call(
            "glm",
            "z-ai/glm-5.2",
            f"""MEDO Tıbbi Kliniği web sitesi HTML kodu yaz.

Plan: {plan}
Spec: {spec}

Fotoğraflar:
{img_html}

KURALLAR:
- <!DOCTYPE html>
- Responsive (mobile-first)
- Modern CSS (tıbbi temalar: mavi, beyaz)
- Menü: Anasayfa, Hizmetler, Doktorlar, Fiyatlar, İletişim
- Hero section (kliniğin adı, slogan)
- 4 Hizmet (İşitme, Muayane, Test, Cihaz)
- 3 Doktor profili
- Fiyat tablosu
- İletişim formu (ad, email, mesaj)
- Footer (adres, telefon, sosyal)
- JavaScript: Menu toggle, form submit

SADECE HTML/CSS/JS!"""
        )
        
        if not code or "<!DOCTYPE" not in code:
            code = self._call(
                "deepseek",
                "deepseek-ai/deepseek-v4-pro",
                f"""MEDO web sitesi HTML kodu yaz:

{img_html}

Yapı:
- Header (MEDO logosu, menu)
- Hero (Sağlığınız Bizim Önceliği)
- Hizmetler (4 adet)
- Doktorlar (3 adet)
- Fiyatlar (tablo)
- İletişim
- Footer

SADECE HTML!"""
            )
        
        if not code:
            self.html = self._fallback(img_html)
            return True

        # 4. GPT-OSS - QA
        reviewed = self._call(
            "gpt_oss",
            "openai/gpt-oss-120b",
            f"""HTML kontrol et:

{code[:2000]}

Kontrol: <!DOCTYPE, Responsive, Fotoğraflar, Form

Düzelt. SADECE HTML!"""
        )
        
        if reviewed and "<!DOCTYPE" in reviewed:
            code = reviewed

        # 5. LLAMA - Final
        code = code.strip()
        code = re.sub(r"^```(html)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
        
        if "<!DOCTYPE" in code or "<html" in code:
            self.html = code
            return True
        else:
            self.html = self._fallback(img_html)
            return True

    def _fallback(self, images: str) -> str:
        """Fallback MEDO HTML"""
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MEDO - Tıbbi Kliniği</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Segoe UI', Arial; background:#f9f9f9; color:#333; }}
        
        header {{
            background: linear-gradient(135deg, #0066cc 0%, #004999 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        header h1 {{ font-size: 28px; }}
        
        nav a {{ color:white; margin:0 15px; text-decoration:none; cursor:pointer; }}
        nav a:hover {{ color:#ffcc00; }}
        
        .hero {{
            background: linear-gradient(135deg, #0066cc 0%, #004999 100%);
            color: white;
            padding: 80px 20px;
            text-align: center;
        }}
        
        .hero h2 {{ font-size: 42px; margin-bottom: 20px; }}
        .hero p {{ font-size: 20px; margin-bottom: 30px; }}
        
        .hero-btn {{
            background: #ffcc00;
            color: #0066cc;
            border: none;
            padding: 15px 40px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }}
        
        .hero-btn:hover {{ background: #ffdd33; }}
        
        .container {{ max-width: 1200px; margin: 0 auto; padding: 60px 20px; }}
        
        .services {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            margin: 40px 0;
        }}
        
        .service-card {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .service-card h3 {{ color: #0066cc; margin-bottom: 15px; font-size: 22px; }}
        .service-card p {{ color: #666; line-height: 1.6; }}
        
        .doctors {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 30px;
            margin: 40px 0;
        }}
        
        .doctor-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .doctor-card img {{ width: 100%; border-radius: 10px; margin-bottom: 15px; }}
        .doctor-card h3 {{ color: #0066cc; margin-bottom: 10px; }}
        .doctor-card p {{ color: #666; font-size: 14px; }}
        
        .prices {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            margin: 40px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        table th {{
            background: #0066cc;
            color: white;
            padding: 15px;
            text-align: left;
        }}
        
        table td {{
            padding: 15px;
            border-bottom: 1px solid #eee;
        }}
        
        table tr:hover {{ background: #f5f5f5; }}
        
        .contact {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            margin: 40px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .contact h2 {{ color: #0066cc; margin-bottom: 30px; }}
        
        .contact form {{
            display: grid;
            gap: 20px;
        }}
        
        .contact input, .contact textarea {{
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            font-family: Arial;
        }}
        
        .contact button {{
            background: #0066cc;
            color: white;
            border: none;
            padding: 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }}
        
        .contact button:hover {{ background: #004999; }}
        
        footer {{
            background: #333;
            color: white;
            padding: 40px;
            text-align: center;
            margin-top: 60px;
        }}
        
        .clinic-img {{ width: 100%; height: auto; margin: 20px 0; border-radius: 10px; }}
        
        h2 {{ color: #0066cc; font-size: 32px; margin-bottom: 30px; text-align: center; }}
    </style>
</head>
<body>
    <header>
        <h1>🏥 MEDO Kliniği</h1>
        <nav>
            <a onclick="document.getElementById('home').scrollIntoView()">Anasayfa</a>
            <a onclick="document.getElementById('services').scrollIntoView()">Hizmetler</a>
            <a onclick="document.getElementById('doctors').scrollIntoView()">Doktorlar</a>
            <a onclick="document.getElementById('prices').scrollIntoView()">Fiyatlar</a>
            <a onclick="document.getElementById('contact').scrollIntoView()">İletişim</a>
        </nav>
    </header>
    
    <div class="hero" id="home">
        <h2>Sağlığınız Bizim Önceliği</h2>
        <p>MEDO Kliniği - Profesyonel Tıbbi Hizmetler</p>
        <button class="hero-btn" onclick="document.getElementById('contact').scrollIntoView()">Randevu Al</button>
    </div>
    
    <div class="container">
        <section id="services">
            <h2>Hizmetlerimiz</h2>
            <div class="services">
                <div class="service-card">
                    <h3>👂 İşitme Testi</h3>
                    <p>Profesyonel işitme testleri ve cihaz uygulaması</p>
                </div>
                <div class="service-card">
                    <h3>🔍 Muayane</h3>
                    <p>Kapsamlı medikal muayane ve teşhis</p>
                </div>
                <div class="service-card">
                    <h3>🧬 Laboratuvar</h3>
                    <p>Kan testi ve biyolojik analizler</p>
                </div>
                <div class="service-card">
                    <h3>💊 İlaç Tedavisi</h3>
                    <p>Uzman doktor denetiminde ilaç tedavisi</p>
                </div>
            </div>
        </section>
        
        <section id="doctors">
            <h2>Doktor Ekibimiz</h2>
            <div class="doctors">
                <div class="doctor-card">
                    {images}
                    <h3>Dr. Ahmet Yılmaz</h3>
                    <p>Genel Pratisyen</p>
                </div>
                <div class="doctor-card">
                    {images}
                    <h3>Dr. Fatma Kaya</h3>
                    <p>Kardiyolog</p>
                </div>
                <div class="doctor-card">
                    {images}
                    <h3>Dr. Mustafa Demir</h3>
                    <p>Nöroloji Uzmanı</p>
                </div>
            </div>
        </section>
        
        <section id="prices">
            <h2>Fiyat Listesi</h2>
            <div class="prices">
                <table>
                    <tr>
                        <th>Hizmet</th>
                        <th>Fiyat</th>
                    </tr>
                    <tr>
                        <td>Muayane</td>
                        <td>500 ₺</td>
                    </tr>
                    <tr>
                        <td>İşitme Testi</td>
                        <td>800 ₺</td>
                    </tr>
                    <tr>
                        <td>Kan Testi</td>
                        <td>300 ₺</td>
                    </tr>
                    <tr>
                        <td>Ultrasound</td>
                        <td>1000 ₺</td>
                    </tr>
                </table>
            </div>
        </section>
        
        <section id="contact">
            <h2>İletişim</h2>
            <div class="contact">
                <form onsubmit="alert('Mesajınız alındı!'); return false;">
                    <input type="text" placeholder="Adınız" required>
                    <input type="email" placeholder="Email" required>
                    <input type="tel" placeholder="Telefon" required>
                    <textarea placeholder="Mesajınız" rows="5" required></textarea>
                    <button type="submit">Gönder</button>
                </form>
                <p style="margin-top: 30px; color: #666;">
                    <strong>📍 Adres:</strong> İstanbul, Türkiye<br>
                    <strong>📞 Telefon:</strong> +90 212 XXX XX XX<br>
                    <strong>📧 Email:</strong> info@medo.com.tr
                </p>
            </div>
        </section>
    </div>
    
    <footer>
        <p>&copy; 2024 MEDO Kliniği - Tüm Hakları Saklıdır</p>
        <p>Sağlığınız Bizim Görevimiz</p>
    </footer>
</body>
</html>"""
