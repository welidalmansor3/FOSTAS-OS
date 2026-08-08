import os
import re
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.raw_game_html = "" # Üretilen uygulamanın HTML'i burada duracak
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
            model_info = "Kullanıcı '" + model["name"] + "' adında bir dosya yükledi. Bu dosyayı arayüzde bir log, resim veya ikon olarak kullan."
        
        # =====================================================================
        # AŞAMA 1: NEMOTRON İLE UYGULAMA MANTIĞINI PLANLAMA (BAŞ MİMAR)
        # =====================================================================
        nemotron_prompt = (
            "You are the Lead UX/UI Architect. User wants a web app/website: \"" + user_prompt + "\".\n"
            "Context: \"" + doc_context + "\"\n"
            "Media Info: \"" + model_info + "\"\n"
            "Define the app layout, navigation flow, sections, and interactive logic in 3 detailed bullet points. Focus on mobile-first responsive design."
        )
        
        app_plan = self._nvidia_chat(
            "nemotron", 
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", 
            nemotron_prompt, 
            max_tokens=8000, 
            temperature=0.6, 
            extra_body={"reasoning_budget": 4096}
        )
        
        if "API Hatası" in app_plan or len(app_plan) < 50:
            app_plan = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", nemotron_prompt, max_tokens=1000, temperature=0.5)

        # =====================================================================
        # AŞAMA 2: DEEPSEEK V4 İLE TEKNİK ŞARTNAME HAZIRLAMA (MÜHENDİS)
        # =====================================================================
        deepseek_prompt = (
            "You are the Frontend Engineer. Based on this app plan: \"" + app_plan + "\", write a detailed technical specification for a Web App.\n"
            "List the required HTML structure, CSS classes (flexbox/grid), and JavaScript functions.\n"
            "Specify how buttons will trigger functions.\n"
            "Do NOT write the full HTML yet. Just the technical blueprint."
        )
        tech_spec = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", deepseek_prompt, max_tokens=2000, extra_body={"chat_template_kwargs":{"thinking":False}})

        # =====================================================================
        # AŞAMA 3: GLM-5.2 İLE KODU YAZMA (KODLAYICI)
        # =====================================================================
        glm_prompt = (
            "You are an Expert Web Developer. Write a fully functional, responsive Web App in a SINGLE HTML file using HTML, CSS, and vanilla JavaScript.\n\n"
            "App Request: \"" + user_prompt + "\"\n"
            "Media Info: \"" + model_info + "\"\n"
            "App Plan: \"" + app_plan + "\"\n"
            "Technical Spec: \"" + tech_spec + "\"\n\n"
            "STRICT RULES:\n"
            "1. Output ONLY raw HTML code. Start with <!DOCTYPE html>. No markdown.\n"
            "2. Design must be modern, mobile-first (responsive), and visually stunning. Use CSS variables for theming.\n"
            "3. CRITICAL BUTTON RULE: Do NOT use addEventListener for buttons. Use INLINE ONCLICK. Example: <button onclick=\"startApp()\">Start</button>. This is mandatory.\n"
            "4. If a start screen exists, the button must hide the start screen and show the main app. Example: document.getElementById('startScreen').style.display='none'; document.getElementById('mainApp').style.display='block';\n"
            "5. All interactive logic must be inside <script> tags at the end of the body."
        )
        
        code = self._nvidia_chat("glm", "z-ai/glm-5.2", glm_prompt, max_tokens=8000, temperature=0.8)
        
        if "API Hatası" in code or len(code) < 100 or "<!DOCTYPE html>" not in code:
            code = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", glm_prompt, max_tokens=8000, extra_body={"chat_template_kwargs":{"thinking":False}})
        
        if "API Hatası" in code or len(code) < 100 or "<!DOCTYPE html>" not in code:
            code = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", glm_prompt, max_tokens=4000, temperature=0.7)

        # =====================================================================
        # AŞAMA 4: GPT-OSS İLE KODU KONTROL ETME VE DÜZELTME (KALİTE KONTROL)
        # =====================================================================
        if "<!DOCTYPE html>" in code or "<html>" in code:
            gpt_oss_prompt = (
                "You are the QA Engineer. Review the following HTML5 web app code.\n"
                "Ensure it strictly has:\n"
                "1. All buttons use inline onclick (NO addEventListener).\n"
                "2. All JavaScript functions are properly defined and called.\n"
                "3. The UI is mobile-responsive and visually appealing.\n\n"
                "Fix any bugs or broken event listeners.\n"
                "Output ONLY the corrected, raw HTML code. No markdown fences, no explanations.\n\n"
                "CODE TO REVIEW AND FIX:\n"
                + code
            )
            
            reviewed_code = self._nvidia_chat("gpt_oss", "openai/gpt-oss-120b", gpt_oss_prompt, max_tokens=8000)
            
            if "<!DOCTYPE html>" in reviewed_code or "<html>" in reviewed_code:
                code = reviewed_code

        # Markdown temizliği
        code = re.sub(r"^```html\n?", "", code.strip())
        code = re.sub(r"\n?```$", "", code.strip())

        if model_b64:
            code = code.replace("MODEL_BASE64_PLACEHOLDER", "data:application/octet-stream;base64," + model_b64)

        if "<!DOCTYPE html>" in code or "<html>" in code:
            self.raw_game_html = code
            return True
        
        self.raw_game_html = "<h1 style='color:red;text-align:center;'>Uygulama üretilemedi. Lütfen daha basit bir prompt deneyin.</h1>"
        return False
