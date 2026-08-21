import os
import re
import requests
import logging
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional, Dict, List, Tuple

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIProvider:
    """AI Provider abstraction"""
    
    def __init__(self, name: str, model: str, api_key: str):
        self.name = name
        self.model = model
        self.api_key = api_key
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.client = None
        self.is_available = False
        
        if api_key:
            try:
                self.client = OpenAI(base_url=self.base_url, api_key=api_key)
                self.is_available = True
                logger.info(f"✅ {self.name} initialized")
            except Exception as e:
                logger.error(f"❌ {self.name} init failed: {e}")
    
    def call(self, prompt: str, max_tokens: int = 2048, timeout: int = 30) -> Tuple[bool, str]:
        """Call AI model"""
        if not self.is_available:
            return False, "Provider not available"
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
                timeout=timeout
            )
            result = completion.choices[0].message.content
            return True, result
        except Exception as e:
            logger.error(f"❌ {self.name} call failed: {e}")
            return False, str(e)


class ImageDownloader:
    """Download and embed images as base64"""
    
    @staticmethod
    def download_as_base64(url: str, timeout: int = 10) -> Optional[str]:
        """Download image and return as data URI"""
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                import base64
                b64 = base64.b64encode(response.content).decode('utf-8')
                return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            logger.warning(f"Image download failed: {url} - {e}")
        return None
    
    @staticmethod
    def get_images(count: int = 6) -> List[str]:
        """Get base64 encoded images"""
        images = []
        urls = [f"https://picsum.photos/800/600?random={i}" for i in range(1, count + 1)]
        
        for url in urls:
            b64_uri = ImageDownloader.download_as_base64(url)
            if b64_uri:
                images.append(b64_uri)
            else:
                images.append(f"https://via.placeholder.com/800x600?text=Image")
        
        return images


class WebsiteValidator:
    """Validate generated HTML"""
    
    @staticmethod
    def validate(html: str) -> Tuple[bool, List[str]]:
        """Validate HTML structure"""
        issues = []
        
        if "<!DOCTYPE" not in html and "<html" not in html:
            issues.append("Missing DOCTYPE or html tag")
        
        if "<head>" not in html:
            issues.append("Missing head tag")
        
        if "<body>" not in html:
            issues.append("Missing body tag")
        
        if html.count("<") != html.count(">"):
            issues.append("Unmatched HTML tags")
        
        is_valid = len(issues) == 0
        return is_valid, issues


class FOSTASMedo:
    """Multi-AI Website Generator"""
    
    def __init__(self):
        self.html = ""
        self.logs = []
        self.images = []
        
        self.providers = {
            "nemotron": AIProvider(
                "🧠 Nemotron",
                "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                os.getenv("NV_NEMOTRON_KEY")
            ),
            "deepseek": AIProvider(
                "📚 DeepSeek",
                "deepseek-ai/deepseek-v4-pro",
                os.getenv("NV_DEEPSEEK_KEY")
            ),
            "glm": AIProvider(
                "💻 GLM-5.2",
                "z-ai/glm-5.2",
                os.getenv("NV_GLM_KEY")
            ),
            "gpt_oss": AIProvider(
                "🔍 GPT-OSS",
                "openai/gpt-oss-120b",
                os.getenv("NV_GPT_OSS_KEY")
            ),
            "llama": AIProvider(
                "🦙 Llama",
                "meta/llama-3.3-70b-instruct",
                os.getenv("NV_LLAMA_KEY")
            ),
        }
    
    def log(self, msg: str):
        self.logs.append(msg)
        logger.info(msg)
    
    def create(self, prompt: str) -> bool:
        self.logs = []
        
        self.log("📸 Downloading images...")
        self.images = ImageDownloader.get_images(6)
        self.log(f"✅ {len(self.images)} images ready")
        
        self.log("🧠 Creating plan...")
        plan_prompt = f"""User: "{prompt}"
Brief plan: type, sections, style, responsive?
No markdown."""
        
        success, plan = self.providers["nemotron"].call(plan_prompt, 400)
        if not success:
            success, plan = self.providers["llama"].call(plan_prompt, 400)
        
        self.log("✅ Plan ready")
        
        self.log("📚 Tech spec...")
        spec_prompt = f"""Plan: {plan}
Spec: HTML/CSS/JS strategy?
No markdown."""
        
        success, spec = self.providers["deepseek"].call(spec_prompt, 400)
        if not success or len(spec) < 50:
            spec = "Responsive HTML5 website"
        
        self.log("💻 Generating HTML...")
        
        images_html = "\n".join([
            f'<img src="{img}" alt="img" style="width:100%;height:auto;margin:20px 0;border-radius:10px;">'
            for img in self.images[:4]
        ])
        
        code_prompt = f"""CREATE WEBSITE!
Request: {prompt}
Plan: {plan}
Spec: {spec}
Images: {len(self.images)} ready
RULES: <!DOCTYPE html>, ONE FILE, SPA, responsive, onclick, images embedded
ONLY HTML CODE!"""
        
        success, code = self.providers["glm"].call(code_prompt, 6000)
        
        if not success or len(code) < 500:
            self.log("⚠️ GLM failed, trying DeepSeek...")
            success, code = self.providers["deepseek"].call(code_prompt, 5000)
        
        if not success or len(code) < 500:
            self.log("⚠️ DeepSeek failed, trying Llama...")
            success, code = self.providers["llama"].call(code_prompt, 4000)
        
        if not success:
            self.log("⚠️ Using fallback")
            self.html = self._fallback_html(prompt, images_html)
            return True
        
        self.log("✅ Code generated")
        
        self.log("🔍 Validating...")
        code = self._clean_html(code)
        is_valid, issues = WebsiteValidator.validate(code)
        
        if is_valid:
            self.log("✅ Valid!")
            self.html = code
            return True
        else:
            self.log(f"⚠️ Issues: {issues}")
            self.html = code if "<!DOCTYPE" in code else self._fallback_html(prompt, images_html)
            return True
    
    def _clean_html(self, code: str) -> str:
        code = code.strip()
        code = re.sub(r"^```(html)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
        return code.strip()
    
    def _fallback_html(self, title: str, images: str) -> str:
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title[:50]}</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Arial;background:#f5f5f5}}header{{background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:30px}}nav{{background:#333;padding:15px;text-align:center}}nav a{{color:white;margin:0 15px;cursor:pointer;text-decoration:none}}nav a:hover{{color:#667eea}}.container{{max-width:1200px;margin:0 auto;padding:30px}}.page{{display:none}}.page.active{{display:block}}footer{{background:#333;color:white;text-align:center;padding:20px;margin-top:40px}}
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
        <div id="home" class="page active"><h2>Welcome</h2>{images}</div>
        <div id="about" class="page"><h2>About</h2>{images}</div>
        <div id="contact" class="page"><h2>Contact</h2><p>Email: info@example.com</p></div>
    </div>
    <footer><p>&copy; 2024 FOSTAS</p></footer>
    <script>function show(id){{document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));document.getElementById(id).classList.add('active')}}</script>
</body>
</html>"""
