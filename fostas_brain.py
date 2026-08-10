import os
import re
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.raw_game_html = ""
        self.project_memory = {
            "assets": [], 
            "docs": ""
        }
        
        self.nv_keys = {
            "glm": os.getenv("NV_GLM_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY"),
            "nemotron": os.getenv("NV_NEMOTRON_KEY")
        }

        self.nv_base_url = "https://integrate.api.nvidia.com/v1"
        self.clients = {}
        self.status = {}

        for model_name, key in self.nv_keys.items():
            if key:
                try:
                    self.clients[model_name] = OpenAI(base_url=self.nv_base_url, api_key=key)
                    self.status[model_name] = {"ok": True, "error": None}
                except Exception as e:
                    self.status[model_name] = {"ok": False, "error": str(e)}
            else:
                self.status[model_name] = {"ok": False, "error": "Key .env dosyasında yok."}

    def _nvidia_chat(self, client_key: str, model_name: str, prompt: str, max_tokens: int = 4096, temperature: float = 0.7, extra_body: dict = None) -> str:
        if client_key not in self.clients:
            return ""
        
        client = self.clients[client_key]
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
            return completion.choices[0].message.content or ""
        except Exception:
            return ""

    def upload_document(self, text: str):
        self.project_memory["docs"] += "\n\n--- USER UPLOAD ---\n" + text[:3000]

    def register_user_asset(self, filename: str, file_data: bytes):
        safe_name = filename.replace(" ", "_")
        encoded_data = base64.b64encode(file_data).decode('utf-8')
        
        existing = next((a for a in self.project_memory["assets"] if a["name"] == safe_name), None)
        if existing:
            existing["data"] = file_data
            existing["b64"] = encoded_data
        else:
            self.project_memory["assets"].append({
                "name": safe_name, 
                "path": "res://assets/" + safe_name, 
                "data": file_data,
                "b64": encoded_data
            })
        return "res://assets/" + safe_name

    def _clean_html_code(self, code: str) -> str:
        code = code.strip()
        if code.startswith("```"):
            code = re.sub(r"^```[a-zA-Z]*\n?", "", code)
            code = re.sub(r"\n?```$", "", code)
        code = code.replace("```html", "").replace("```", "")
        return code.strip()

    def generate_app_from_doc(self):
        if not self.project_memory["docs"].strip():
            return False
        return self.generate_app("Yüklenen dökümana göre bir uygulama/oyun yap.")

    def generate_app(self, user_prompt: str):
        """Generator function to yield status updates to the UI"""
        doc_context = self.project_memory["docs"] if self.project_memory["docs"] else "Yok."
        
        model_info = "Kullanıcı medya yüklemiyor. Sadece CSS ve Emoji kullan."
        model_b64 = None
        
        if self.project_memory["assets"]:
            model = self.project_memory["assets"][0]
            model_b64 = model["b64"]
            model_info = "Kullanıcı '" + model["name"] + "' adında bir dosya yükledi. Bu dosyayı (MODEL_BASE64_PLACEHOLDER) arayüzde kullan."
        
        # AŞAMA 1: NEMOTRON
        yield "🧠 Aşama 1: Nemotron (Mimar) tasarımı planlıyor..."
        p1 = "You are Lead Architect. Request: \"" + user_prompt + "\". Context: \"" + doc_context + "\". Define layout, mechanics, UI in 3 bullets."
        plan = self._nvidia_chat("nemotron", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", p1, max_tokens=4000, extra_body={"reasoning_budget": 2048})
        if not plan or len(plan) < 20:
            yield "⚠️ Nemotron yanıt vermedi, Llama devreye giriyor..."
            plan = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", p1, max_tokens=1000)

        # AŞAMA 2: DEEPSEEK
        yield "⚙️ Aşama 2: DeepSeek (Mühendis) teknik şartname yazıyor..."
        p2 = "You are Frontend Engineer. Plan: \"" + plan + "\". Write technical spec for HTML/JS. List functions."
        spec = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", p2, max_tokens=2000, extra_body={"chat_template_kwargs":{"thinking":False}})

        # AŞAMA 3: GLM-5.2
        yield "💻 Aşama 3: GLM-5.2 (Kodlayıcı) kodu yazıyor..."
        p3 = (
            "Write a fully functional responsive App/Game in a SINGLE HTML file. Request: \"" + user_prompt + "\". Plan: \"" + plan + "\". Spec: \"" + spec + "\".\n"
            "STRICT RULES:\n"
            "1. ONLY raw HTML code. No markdown.\n"
            "2. Mobile-first responsive, modern design.\n"
            "3. CRITICAL BUTTON RULE: Use INLINE ONCLICK. NO addEventListener.\n"
            "4. CRITICAL IMAGE RULE: Use real images from Wikimedia/Unsplash. If not possible, use CSS Gradients/Emojis. NO broken images.\n"
            "5. All JS functions MUST be global: function name() { }."
        )
        code = self._nvidia_chat("glm", "z-ai/glm-5.2", p3, max_tokens=8000, temperature=0.8)
        
        if not code or "<!DOCTYPE html>" not in code:
            yield "⚠️ GLM başarısız oldu, DeepSeek kodu yazıyor..."
            code = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", p3, max_tokens=8000, extra_body={"chat_template_kwargs":{"thinking":False}})
        
        if not code or "<!DOCTYPE html>" not in code:
            yield "⚠️ DeepSeek de başarısız, Llama son çare devreye giriyor..."
            code = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", p3, max_tokens=4000, temperature=0.7)

        # AŞAMA 4: GPT-OSS
        if code and "<!DOCTYPE html>" in code:
            yield "🔍 Aşama 4: GPT-OSS (Kalite Kontrol) denetliyor ve düzeltiyor..."
            p4 = "You are QA. Review HTML. Ensure: 1. Inline onclick. 2. Global JS. 3. Valid images or CSS fallback. Fix bugs. Output ONLY raw HTML.\nCODE:\n" + code
            reviewed = self._nvidia_chat("gpt_oss", "openai/gpt-oss-120b", p4, max_tokens=8000)
            if reviewed and "<!DOCTYPE html>" in reviewed:
                code = reviewed

        # Temizlik
        if code:
            code = self._clean_html_code(code)

        if model_b64 and code:
            code = code.replace("MODEL_BASE64_PLACEHOLDER", "data:application/octet-stream;base64," + model_b64)

        if code and "<!DOCTYPE html>" in code:
            # Enforcer Script
            enforcer = """
<script>
window.addEventListener('load', function() {
    document.querySelectorAll('img, .icon, .draggable').forEach(el => {
        el.style.cursor = 'grab';
        let isDragging = false, startX, startY, iLeft, iTop;
        const cs = window.getComputedStyle(el);
        if (cs.position === 'static') { el.style.position = 'relative'; }
        el.addEventListener('mousedown', (e) => {
            isDragging = true; el.style.cursor = 'grabbing'; el.style.zIndex = 9999;
            startX = e.clientX; startY = e.clientY;
            iLeft = parseInt(cs.left) || 0; iTop = parseInt(cs.top) || 0;
            e.preventDefault();
        });
        document.addEventListener('mousemove', (e) => {
            if (isDragging) { el.style.left = (iLeft + e.clientX - startX) + 'px'; el.style.top = (iTop + e.clientY - startY) + 'px'; }
        });
        document.addEventListener('mouseup', () => { if (isDragging) { isDragging = false; el.style.cursor = 'grab'; } });
    });

    document.querySelectorAll('button').forEach(btn => {
        if (!btn.hasAttribute('onclick')) {
            btn.addEventListener('click', function() {
                if(typeof startApp === 'function') startApp();
                else if(typeof initGame === 'function') initGame();
                else if(typeof startGame === 'function') startGame();
                let ss = document.getElementById('startScreen'); if(ss) ss.style.display = 'none';
                let ma = document.getElementById('mainApp'); if(ma) ma.style.display = 'block';
            });
        }
    });
});
</script>
</body>
"""
            if "</body>" in code:
                code = code.replace("</body>", enforcer)
            else:
                code += enforcer

            self.raw_game_html = code
            yield "✅ Üretim tamamlandı! 'Dene ve İndir' sekmesine geçebilirsin."
            return True
        
        self.raw_game_html = "<!DOCTYPE html><html><body style='background:#111;color:#fff;text-align:center;padding:50px;'><h1>Üretim başarısız oldu.</h1></body></html>"
        yield "❌ Tüm modeller başarısız oldu. Lütfen farklı bir prompt dene."
        return False
