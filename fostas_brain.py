import os
import re
import base64
import requests
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# NOT: Bu model ID'leri build.nvidia.com uzerinden dogrulandi (Agustos 2026).
# Onceki versiyonda bazi model isimleri hataliydi (ornegin "nemotron-3-nano-omni-30b-a3b-reasoning"
# ve "deepseek-v4-pro" NVIDIA katalogunda YOK) - bu yuzden o adimlar hep sessizce basarisiz oluyordu.
MODELS = {
    "nemotron": "nvidia/nemotron-3-nano-30b-a3b",   # plan
    "deepseek": "deepseek-ai/deepseek-v3.2",         # teknik spec
    "glm":      "z-ai/glm-5.2",                      # ana kod uretimi
    "gpt_oss":  "openai/gpt-oss-120b",               # kalite kontrol (QA)
    "llama":    "meta/llama-3.3-70b-instruct",       # yedek (fallback)
}

ENV_KEYS = {
    "nemotron": "NV_NEMOTRON_KEY",
    "deepseek": "NV_DEEPSEEK_KEY",
    "glm":      "NV_GLM_KEY",
    "gpt_oss":  "NV_GPT_OSS_KEY",
    "llama":    "NV_LLAMA_KEY",
}


class FOSTASBrain:
    def __init__(self):
        self.logs = []
        self.total_tokens = 0
        self.used_models = []
        self.clients = {}
        self.key_status = {}

        for agent, env_name in ENV_KEYS.items():
            key = os.getenv(env_name)
            self.key_status[agent] = bool(key)
            if key:
                self.clients[agent] = OpenAI(
                    base_url=NVIDIA_BASE_URL,
                    api_key=key,
                    timeout=45.0,
                )

    def _log(self, agent: str, msg: str):
        self.logs.append(f"{agent}: {msg}")

    def _call(self, agent: str, prompt: str, max_tokens: int = 1500, temperature: float = 0.7):
        """Hicbir zaman exception firlatmaz. Gercek hatayi loglar. (text, ok) dondurur."""
        if agent not in self.clients:
            self._log(f"❌ {agent}", f"API key yok ({ENV_KEYS[agent]} tanimli degil)")
            return "", False

        model = MODELS[agent]
        try:
            completion = self.clients[agent].chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = completion.choices[0].message.content or ""
            try:
                self.total_tokens += completion.usage.total_tokens
            except Exception:
                pass
            self.used_models.append(model)
            return text, True
        except Exception as e:
            self._log(f"❌ {agent} ({model})", f"HATA: {e}")
            return "", False

    def test_connections(self):
        """Her modele kucuk bir test istegi atar - gercekten baglanabiliyor mu diye."""
        results = {}
        for agent in MODELS:
            if agent not in self.clients:
                results[agent] = (False, f"API key yok ({ENV_KEYS[agent]})")
                continue
            text, ok = self._call(agent, "Sadece 'ok' yaz, baska hicbir sey yazma.", max_tokens=10, temperature=0)
            if ok:
                results[agent] = (True, (text or "").strip()[:60])
            else:
                last_error = self.logs[-1] if self.logs else "bilinmeyen hata"
                results[agent] = (False, last_error)
        return results

    @staticmethod
    def _extract_html(text: str) -> str:
        """Modelin cevabinin icinden gercek HTML'i cikarir (aciklama/markdown olsa bile)."""
        if not text:
            return ""
        match = re.search(r"<!DOCTYPE\s+html.*?</html>", text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(0).strip()
        match = re.search(r"<html.*?</html>", text, re.IGNORECASE | re.DOTALL)
        if match:
            return "<!DOCTYPE html>\n" + match.group(0).strip()
        cleaned = text.strip()
        cleaned = re.sub(r"^```(html)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        return cleaned.strip()

    def _download_images(self, count: int = 4):
        self._log("📸 Fotograflar", "Indiriliyor...")
        images = []
        for i in range(count):
            url = f"https://picsum.photos/800/600?random={i}"
            try:
                r = requests.get(url, timeout=8)
                if r.status_code == 200:
                    b64 = base64.b64encode(r.content).decode("utf-8")
                    images.append(f"data:image/jpeg;base64,{b64}")
            except Exception as e:
                self._log("⚠️ Fotograf", f"{i + 1}. indirilemedi: {e}")

        if not images:
            images = [f"https://placehold.co/800x600?text=Resim+{i + 1}" for i in range(count)]

        self._log("✅ Fotograflar", f"{len(images)} adet hazir")
        return images

    def generate(self, prompt: str):
        """Returns (html, success: bool, status: str)"""
        self.logs = []
        self.used_models = []
        self.total_tokens = 0

        images = self._download_images()
        images_html = "\n".join(
            f'<img src="{img}" alt="gorsel" style="width:100%;border-radius:12px;margin:16px 0;">'
            for img in images
        )

        # 1) Plan - Nemotron
        self._log("🧠 Nemotron", "Plan hazirlaniyor...")
        plan, ok = self._call(
            "nemotron",
            f'Kullanici istegi: "{prompt}"\n\nKisa bir plan yaz (site tipi, ana sayfalar, tasarim stili). '
            f"Markdown kullanma, duz metin yaz, en fazla 5 satir.",
            max_tokens=400,
        )
        if not ok or not plan.strip():
            self._log("↪️ Nemotron", "Basarisiz, Llama ile devam ediliyor")
            plan, ok = self._call(
                "llama", f'Kullanici istegi: "{prompt}" icin kisa bir web sitesi plani yaz.', max_tokens=300
            )
        if not plan.strip():
            plan = prompt

        # 2) Teknik spec - DeepSeek
        self._log("📚 DeepSeek", "Teknik detaylar...")
        spec, ok = self._call(
            "deepseek",
            f"Plan:\n{plan}\n\nBu plan icin kisa teknik notlar yaz (HTML bolumleri, CSS yaklasimi, JS ihtiyaclari). "
            f"Markdown kullanma, en fazla 5 satir.",
            max_tokens=400,
        )
        if not ok or not spec.strip():
            spec = plan

        # 3) GLM-5.2 - asil kod uretimi
        self._log("💻 GLM-5.2", "HTML/CSS/JS uretiliyor...")
        code_prompt = f"""Asagidaki istek icin TEK BIR HTML dosyasi uret.

Istek: {prompt}
Plan: {plan}
Teknik notlar: {spec}

Kurallar:
- <!DOCTYPE html> ile basla, tek dosyada HTML+CSS+JS olsun.
- Responsive olsun (mobilde hamburger menu).
- En az 3 bolum olsun (Anasayfa, Hakkinda, Iletisim) ve JavaScript ile aralarinda gecis yapilsin
  (SPA mantigi, display:none/block ile).
- Tum butonlar onclick="..." kullansin (addEventListener KULLANMA).
- Asagidaki gorselleri uygun yerlere yerlestir:
{images_html}
- Sadece HTML kodu dondur, baska aciklama yazma.
"""
        raw, ok = self._call("glm", code_prompt, max_tokens=6000, temperature=0.6)
        code = self._extract_html(raw)

        if not code or "<html" not in code.lower():
            self._log("↪️ GLM-5.2", "Gecerli HTML donmedi, DeepSeek deneniyor...")
            raw, ok = self._call("deepseek", code_prompt, max_tokens=6000, temperature=0.6)
            code = self._extract_html(raw)

        if not code or "<html" not in code.lower():
            self._log("↪️ DeepSeek", "Gecerli HTML donmedi, Llama deneniyor...")
            raw, ok = self._call("llama", code_prompt, max_tokens=4000, temperature=0.6)
            code = self._extract_html(raw)

        # 4) GPT-OSS QA - TAM kodu goruyor (onceki versiyonda ilk 2000 karakterle sinirliydi, bu HATAYDI)
        if code and "<html" in code.lower():
            self._log("🔍 GPT-OSS", "Kalite kontrolu...")
            qa_prompt = f"""Bu HTML kodunu incele. <!DOCTYPE, responsive tasarim, onclick butonlar ve JS
fonksiyonlarinin calisir oldugundan emin ol. Sorun varsa duzelt, sorun yoksa aynen geri dondur.
Sadece HTML dondur, aciklama yazma.

{code}
"""
            reviewed_raw, ok = self._call("gpt_oss", qa_prompt, max_tokens=6500, temperature=0.3)
            reviewed = self._extract_html(reviewed_raw)
            if reviewed and "<html" in reviewed.lower() and len(reviewed) > 300:
                code = reviewed
                self._log("✅ GPT-OSS", "Kontrol tamam, kod guncellendi")
            else:
                self._log("⚠️ GPT-OSS", "QA cevabi gecersizdi, onceki kod korundu")

        # 5) Son kontrol
        if code and "<html" in code.lower():
            if "<!DOCTYPE" not in code[:20].upper():
                code = "<!DOCTYPE html>\n" + code
            self._log("✅ Tamamlandi", "Website hazir")
            return code, True, "SUCCESS"

        self._log("⚠️ Tum modeller basarisiz oldu", "Sablon (fallback) kullaniliyor - yukaridaki hatalara bak")
        return self._fallback_html(prompt, images_html), False, "FALLBACK"

    @staticmethod
    def _fallback_html(title: str, images_html: str) -> str:
        safe_title = title[:60]
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: Arial, sans-serif; background:#f5f5f5; }}
header {{ background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; padding:32px 20px; text-align:center; }}
nav {{ background:#222; padding:14px; text-align:center; }}
nav a {{ color:#fff; margin:0 14px; text-decoration:none; cursor:pointer; font-weight:600; }}
nav a:hover {{ color:#a5b4fc; }}
main {{ max-width:1000px; margin:0 auto; padding:30px 20px; }}
.page {{ display:none; }}
.page.active {{ display:block; }}
h2 {{ color:#4c51bf; margin-bottom:14px; }}
footer {{ text-align:center; padding:20px; color:#666; margin-top:30px; }}
</style>
</head>
<body>
<header><h1>{safe_title}</h1></header>
<nav>
<a onclick="show('home')">Anasayfa</a>
<a onclick="show('about')">Hakkinda</a>
<a onclick="show('contact')">Iletisim</a>
</nav>
<main>
<div id="home" class="page active"><h2>Hos Geldiniz</h2><p>{safe_title}</p>{images_html}</div>
<div id="about" class="page"><h2>Hakkinda</h2><p>Bu site FOSTAS tarafindan otomatik olarak olusturuldu.</p></div>
<div id="contact" class="page"><h2>Iletisim</h2><p>Email: info@example.com</p></div>
</main>
<footer>&copy; 2026 FOSTAS</footer>
<script>
function show(id){{
  document.querySelectorAll('.page').forEach(function(p){{p.classList.remove('active');}});
  document.getElementById(id).classList.add('active');
}}
</script>
</body>
</html>"""
