import os
import re
from dotenv import load_dotenv

load_dotenv()


class WebBuilder:
    """Web sitesi oluştur - Fallback güvenli"""

    def __init__(self):
        self.html = ""

    def build(self, title: str) -> str:
        """Web sitesi HTML'i oluştur"""
        
        # Fotoğraflar
        images = [
            "https://picsum.photos/800/600?random=1",
            "https://picsum.photos/800/600?random=2",
            "https://picsum.photos/800/600?random=3",
            "https://picsum.photos/800/600?random=4",
        ]
        
        img_html = "\n".join([
            f'<img src="{img}" alt="Foto" loading="lazy" style="width:100%;margin:20px 0;border-radius:10px;box-shadow:0 4px 8px rgba(0,0,0,0.1);">'
            for img in images
        ])
        
        # HTML yapısı
        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            color: #333;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 20px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        header h1 {{
            font-size: 48px;
            margin-bottom: 10px;
            animation: slideIn 0.5s ease;
        }}
        
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        nav {{
            background: white;
            padding: 15px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        nav a {{
            color: #667eea;
            text-decoration: none;
            margin: 0 20px;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-block;
        }}
        
        nav a:hover {{
            color: #764ba2;
            transform: translateY(-2px);
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        .section {{
            display: none;
            animation: fadeIn 0.5s ease;
        }}
        
        .section.active {{
            display: block;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .section-content {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 36px;
        }}
        
        p {{
            color: #666;
            line-height: 1.8;
            margin-bottom: 20px;
            font-size: 16px;
        }}
        
        footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 30px;
            margin-top: 60px;
            font-size: 14px;
        }}
        
        footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        footer a:hover {{
            text-decoration: underline;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            header h1 {{ font-size: 32px; }}
            nav a {{ margin: 0 10px; font-size: 14px; }}
            .section-content {{ padding: 20px; }}
            h2 {{ font-size: 24px; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>Profesyonel Web Sitesi - FOSTAS tarafından oluşturuldu</p>
    </header>
    
    <nav>
        <a onclick="showSection('home')">🏠 Anasayfa</a>
        <a onclick="showSection('about')">📌 Hakkında</a>
        <a onclick="showSection('services')">🎯 Hizmetler</a>
        <a onclick="showSection('portfolio')">📸 Portföy</a>
        <a onclick="showSection('contact')">📞 İletişim</a>
    </nav>
    
    <div class="container">
        <!-- Anasayfa -->
        <div id="home" class="section active">
            <div class="section-content">
                <h2>Hoş Geldiniz</h2>
                <p>{title} sitesine hoş geldiniz. Biz profesyonel ve güvenilir hizmetler sunmaktayız.</p>
                <p>Sayfamızda dolaşmaya devam edin ve hakkımızda daha fazla bilgi alın.</p>
                {img_html}
            </div>
        </div>
        
        <!-- Hakkında -->
        <div id="about" class="section">
            <div class="section-content">
                <h2>Hakkında Biz</h2>
                <p>Yılların deneyimi ile sizlere en iyi hizmeti sunmaktayız.</p>
                <p>Müşteri memnuniyeti bizim önceliğimizdir. Her zaman kaliteli ve profesyonel çalışma yapıyoruz.</p>
                <p>Bizimle çalışmak istiyorsanız, lütfen iletişim sayfasından bize ulaşın.</p>
                {img_html}
            </div>
        </div>
        
        <!-- Hizmetler -->
        <div id="services" class="section">
            <div class="section-content">
                <h2>Hizmetlerimiz</h2>
                <p><strong>1. Profesyonel Tasarım</strong> - Modern ve göz alıcı tasarımlar</p>
                <p><strong>2. Responsive Web</strong> - Tüm cihazlarda mükemmel görünüm</p>
                <p><strong>3. Hızlı Yükleme</strong> - Optimize edilmiş performans</p>
                <p><strong>4. SEO Optimized</strong> - Arama motorlarında üst sıralar</p>
                <p><strong>5. Güvenli Sistem</strong> - En yüksek güvenlik standartları</p>
                {img_html}
            </div>
        </div>
        
        <!-- Portföy -->
        <div id="portfolio" class="section">
            <div class="section-content">
                <h2>Portföy</h2>
                <p>Geçmiş projelerimizden bazıları:</p>
                <p>✓ E-ticaret Siteleri</p>
                <p>✓ Kurumsal Web Siteleri</p>
                <p>✓ Kişisel Blog Siteleri</p>
                <p>✓ Mobil Uygulamalar</p>
                <p>✓ İçerik Yönetim Sistemleri</p>
                {img_html}
            </div>
        </div>
        
        <!-- İletişim -->
        <div id="contact" class="section">
            <div class="section-content">
                <h2>İletişim</h2>
                <p><strong>Email:</strong> info@fostas.com</p>
                <p><strong>Telefon:</strong> +90 (212) 123 45 67</p>
                <p><strong>Adres:</strong> İstanbul, Türkiye</p>
                <p><strong>Çalışma Saatleri:</strong> Pazartesi - Cuma, 09:00 - 18:00</p>
                <br>
                <p>Bize ulaşmaktan çekinmeyin. Sizin sorunlarınıza çözüm bulmaktan mutluluk duyarız.</p>
                {img_html}
            </div>
        </div>
    </div>
    
    <footer>
        <p>&copy; 2024 {title} - Tüm Hakları Saklıdır</p>
        <p>FOSTAS Multi-Agent AI tarafından oluşturuldu</p>
    </footer>
    
    <script>
        function showSection(sectionId) {{
            // Tüm section'ları gizle
            const sections = document.querySelectorAll('.section');
            sections.forEach(section => {{
                section.classList.remove('active');
            }});
            
            // Seçilen section'u göster
            const selectedSection = document.getElementById(sectionId);
            if (selectedSection) {{
                selectedSection.classList.add('active');
            }}
            
            // Sayfanın üstüne git
            window.scrollTo({{top: 0, behavior: 'smooth'}});
        }}
    </script>
</body>
</html>"""
        
        self.html = html
        return html
