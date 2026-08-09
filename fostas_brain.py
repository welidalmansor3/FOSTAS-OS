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

    def _nvidia_chat(self, model_client: str, model_name: str, prompt: str, max_tokens: int = 4096, temperature: float = 0.7, extra_body: dict = None) -> str:
        if model_client not in self.clients:
            return "Hata: Client bağlı değil."
        
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
            return "API Hatası: " + str(e)

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

    def generate_app_from_doc(self):
        if not self.project_memory["docs"].strip():
            return False
        return self.generate_app("Yüklenen dökümana göre bir web uygulaması yap.")

    def generate_app(self, user_prompt: str) -> bool:
        doc_context = self.project_memory["docs"] if self.project_memory["docs"] else "Yok."
        
        model_info = "Kullanıcı medya yüklemiyor. Standart CSS görselleri kullan."
        model_b64 = None
        
        if self.project_memory["assets"]:
            model = self.project_memory["assets"][0]
            model_b64 = model["b64"]
            model_info = "Kullanıcı '" + model["name"] + "' adında bir dosya yükledi. Bu dosyayı arayüzde kullan."
        
        # AŞAMA 1: NEMOTRON
        nemotron_prompt = "You are the Lead UX/UI Architect. User wants a web app: \"" + user_prompt + "\". Context: \"" + doc_context + "\". Define app layout in 3 bullet points."
        app_plan = self._nvidia_chat("nemotron", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", nemotron_prompt, max_tokens=8000, temperature=0.6, extra_body={"reasoning_budget": 4096})
        if "API Hatası" in app_plan or len(app_plan) < 50:
            app_plan = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", nemotron_prompt, max_tokens=1000, temperature=0.5)

        # AŞAMA 2: DEEPSEEK
        deepseek_prompt = "You are the Frontend Engineer. Plan: \"" + app_plan + "\". Write technical specification for Web App. List HTML, CSS, JS functions."
        tech_spec = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", deepseek_prompt, max_tokens=2000, extra_body={"chat_template_kwargs":{"thinking":False}})

        # AŞAMA 3: GLM-5.2
        glm_prompt = "You are an Expert Web Developer. Write a fully functional responsive Web App in a SINGLE HTML file. Request: \"" + user_prompt + "\". Plan: \"" + app_plan + "\". Spec: \"" + tech_spec + "\".\nSTRICT RULES:\n1. ONLY raw HTML code. No markdown.\n2. Mobile-first responsive.\n3. CRITICAL BUTTON RULE: Use INLINE ONCLICK. NO addEventListener.\n4. CRITICAL IMAGE RULE: Use real images from internet (Wikimedia/Unsplash).\n5. All JS functions MUST be global (function name() { })."
        
        code = self._nvidia_chat("glm", "z-ai/glm-5.2", glm_prompt, max_tokens=8000, temperature=0.8)
        
        if "API Hatası" in code or len(code) < 100 or "<!DOCTYPE html>" not in code:
            code = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", glm_prompt, max_tokens=8000, extra_body={"chat_template_kwargs":{"thinking":False}})
        if "API Hatası" in code or len(code) < 100 or "<!DOCTYPE html>" not in code:
            code = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", glm_prompt, max_tokens=4000, temperature=0.7)

        # AŞAMA 4: GPT-OSS (QA)
        if "<!DOCTYPE html>" in code or "<html>" in code:
            gpt_oss_prompt = "You are QA Engineer. Review this HTML code. Ensure: 1. Inline onclick for all buttons. 2. Global JS functions. 3. Valid image URLs. Fix bugs. Output ONLY raw HTML.\nCODE:\n" + code
            reviewed_code = self._nvidia_chat("gpt_oss", "openai/gpt-oss-120b", gpt_oss_prompt, max_tokens=8000)
            if "<!DOCTYPE html>" in reviewed_code or "<html>" in reviewed_code:
                code = reviewed_code

        # Markdown temizliği
        code = re.sub(r"^```html\n?", "", code.strip())
        code = re.sub(r"\n?```$", "", code.strip())

        if model_b64:
            code = code.replace("MODEL_BASE64_PLACEHOLDER", "data:application/octet-stream;base64," + model_b64)

        if "<!DOCTYPE html>" in code or "<html>" in code:
            # NÜKLEER ÇÖZÜM: GLOBAL BUTON YAKALAYICI VE SÜRÜKLE-BIRAK
            enforcer_script = """
<script>
window.addEventListener('load', function() {
    document.querySelectorAll('img, .icon, .draggable').forEach(el => {
        el.style.cursor = 'grab';
        let isDragging = false;
        let startX, startY, initialLeft, initialTop;
        const computedStyle = window.getComputedStyle(el);
        if (computedStyle.position === 'static') { el.style.position = 'relative'; }
        el.addEventListener('mousedown', (e) => {
            isDragging = true; el.style.cursor = 'grabbing'; el.style.zIndex = 9999;
            startX = e.clientX; startY = e.clientY;
            initialLeft = parseInt(computedStyle.left) || 0; initialTop = parseInt(computedStyle.top) || 0;
            e.preventDefault();
        });
        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                el.style.left = (initialLeft + (e.clientX - startX)) + 'px';
                el.style.top = (initialTop + (e.clientY - startY)) + 'px';
            }
        });
        document.addEventListener('mouseup', () => { if (isDragging) { isDragging = false; el.style.cursor = 'grab'; } });
    });

    document.querySelectorAll('button').forEach(btn => {
        if (!btn.hasAttribute('onclick')) {
            btn.addEventListener('click', function() {
                if(typeof startApp === 'function') startApp();
                else if(typeof initGame === 'function') initGame();
                else if(typeof startGame === 'function') startGame();
                else if(typeof beginApp === 'function') beginApp();
                let ss = document.getElementById('startScreen');
                if(ss) ss.style.display = 'none';
                let ma = document.getElementById('mainApp');
                if(ma) ma.style.display = 'block';
            });
        }
    });
});
</script>
</body>
"""
            if "</body>" in code:
                code = code.replace("</body>", enforcer_script)
            else:
                code += enforcer_script

            self.raw_game_html = code
            return True
        
        self.raw_game_html = "<h1 style='color:red;text-align:center;'>Uygulama üretilemedi.</h1>"
        return False
