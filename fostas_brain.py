import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class FOSTASWeb:
    """Web Sitesi Yapan Sistem"""

    def __init__(self):
        self.html = ""
        
        self.glm_key = os.getenv("NV_GLM_KEY")
        self.nv_url = "https://integrate.api.nvidia.com/v1"
        
        if self.glm_key:
            self.client = OpenAI(base_url=self.nv_url, api_key=self.glm_key)
            self.ok = True
        else:
            self.client = None
            self.ok = False

    def create(self, prompt: str) -> bool:
        """Web sitesi oluştur"""
        
        if not self.client:
            self.html = "<h1>ERROR: API Key yok</h1>"
            return False
        
        # Fotoğraf linkler
        images = [
            "https://picsum.photos/800/600?random=1",
            "https://picsum.photos/800/600?random=2",
            "https://picsum.photos/800/600?random=3",
            "https://picsum.photos/800/600?random=4",
        ]
        
        img_html = "\n".join([
            f'<img src="{img}" alt="foto" style="width:100%;margin:20px 0;border-radius:10px;">'
            for img in images
        ])
        
        # GLM'ye sor
        request = f"""Web sitesi HTML kodu yaz.

İstek: {prompt}

Resimler:
{img_html}

Gerekli:
- <!DOCTYPE html>
- Responsive
- Menü (Home, About, Contact)
- Modern CSS
- JavaScript toggle (onclick)

SADECE HTML KOD!"""
        
        try:
            response = self.client.chat.completions.create(
                model="z-ai/glm-5.2",
                messages=[{"role": "user", "content": request}],
                max_tokens=6000,
                temperature=0.7
            )
            
            code = response.choices[0].message.content
            
            # Temizle
            code = re.sub(r"^```(html)?\n?", "", code.strip())
            code = re.sub(r"\n?```$", "", code)
            
            if "<!DOCTYPE" in code or "<html" in code:
                self.html = code
                return True
            else:
                self.html = self._fallback(prompt, img_html)
                return True
                
        except Exception as e:
            self.html = f"<h1>Hata: {str(e)}</h1>"
            return False

    def _fallback(self, title: str, images: str) -> str:
        """Fallback HTML"""
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
        p {{ color:#666; line-height:1.6; }}
        footer {{ background:#333; color:white; text-align:center; padding:20px; margin-top:40px; }}
        img {{ max-width:100%; height:auto; }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
    </header>
    
    <nav>
        <a onclick="show('home')">Anasayfa</a>
        <a onclick="show('about')">Hakkında</a>
        <a onclick="show('contact')">İletişim</a>
    </nav>
    
    <div class="container">
        <div id="home" class="section active">
            <h2>Hoş Geldiniz</h2>
            <p>{title}</p>
            {images}
        </div>
        
        <div id="about" class="section">
            <h2>Hakkında Biz</h2>
            <p>Profesyonel web sitesi. FOSTAS tarafından oluşturuldu.</p>
            {images}
        </div>
        
        <div id="contact" class="section">
            <h2>İletişim</h2>
            <p>Email: info@example.com</p>
            <p>Telefon: +90 123 456 7890</p>
            {images}
        </div>
    </div>
    
    <footer>
        <p>&copy; 2024 - FOSTAS Web Studio</p>
    </footer>
    
    <script>
        function show(id) {{
            var sections = document.querySelectorAll('.section');
            for(var i=0; i<sections.length; i++) {{
                sections[i].classList.remove('active');
            }}
            document.getElementById(id).classList.add('active');
        }}
    </script>
</body>
</html>"""
