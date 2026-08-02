import os
import re
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.raw_game_html = "" # Sadece temiz HTML tutulacak, iframe enjeksiyonu yok.
        self.project_memory = {
            "assets": [], 
            "docs": ""
        }
        
        self.nv_keys = {
            "glm": os.getenv("NV_GLM_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY")
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

    def generate_game_from_doc(self):
        if not self.project_memory["docs"].strip():
            return False
        return self.generate_game("Yüklenen dökümana göre bir oyun yap.")

    def generate_game(self, user_prompt: str) -> bool:
        doc_context = self.project_memory["docs"] if self.project_memory["docs"] else "Yok."
        
        model_info = "Kullanıcı 3D model yüklemedi. Standart şekillerle oyunu yap."
        model_b64 = None
        
        if self.project_memory["assets"]:
            model = self.project_memory["assets"][0]
            model_b64 = model["b64"]
            model_info = "Kullanıcı '" + model["name"] + "' adında bir 3D model yükledi. Bu modeli oyunda kullanmak ZORUNDASIN."
        
        # =====================================================================
        # AŞAMA 1: LLAMA 3.3 İLE OYUN MEKANİKLERİNİ PLANLAMA (MİMAR)
        # =====================================================================
        llama_prompt = (
            "You are the Game Architect. User wants a game: \"" + user_prompt + "\".\n"
            "Context: \"" + doc_context + "\"\n"
            "Model Info: \"" + model_info + "\"\n"
            "Define the game mechanics, win/lose conditions, controls, and physics in 3 short bullet points."
        )
        game_plan = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", llama_prompt, max_tokens=1000, temperature=0.5)

        # =====================================================================
        # AŞAMA 2: DEEPSEEK V4 İLE TEKNİK ŞARTNAME HAZIRLAMA (MÜHENDİS)
        # =====================================================================
        deepseek_prompt = (
            "You are the Technical Engineer. Based on this game plan: \"" + game_plan + "\", write a detailed technical specification for an HTML5 game.\n"
            "List the required JavaScript variables, functions (initGame, animate), and CSS elements (startBtn, startScreen).\n"
            "Do NOT write the full HTML yet. Just the technical blueprint."
        )
        tech_spec = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", deepseek_prompt, max_tokens=2000, extra_body={"chat_template_kwargs":{"thinking":False}})

        # =====================================================================
        # AŞAMA 3: GLM-5.2 İLE KODU YAZMA (KODLAYICI)
        # =====================================================================
        glm_prompt = (
            "You are the HTML5 Coder. Write a fully playable game in a SINGLE HTML file using HTML5 Canvas or Three.js.\n\n"
            "Game Request: \"" + user_prompt + "\"\n"
            "Model Info: \"" + model_info + "\"\n"
            "Game Plan: \"" + game_plan + "\"\n"
            "Technical Spec: \"" + tech_spec + "\"\n\n"
            "STRICT RULES:\n"
            "1. Output ONLY raw HTML code. Start with <!DOCTYPE html>. No markdown.\n"
            "2. If a 3D model is provided, use Three.js. Include EXACTLY these scripts:\n"
            "   <script src=\"https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js\"></script>\n"
            "   <script src=\"https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js\"></script>\n"
            "3. To load the 3D model, write EXACTLY this code:\n"
            "   const modelUrl = \"MODEL_BASE64_PLACEHOLDER\";\n"
            "   const loader = new THREE.GLTFLoader();\n"
            "   loader.load(modelUrl, function(gltf) { scene.add(gltf.scene); });\n"
            "4. Game MUST have: Start screen (id=\"startScreen\"), Start button (id=\"startBtn\"), Game Loop.\n"
            "5. Use this EXACT JavaScript pattern for the start button:\n"
            "   let gameStarted = false;\n"
            "   function initGame() { gameStarted = true; animate(); }\n"
            "   document.addEventListener('DOMContentLoaded', function() {\n"
            "       document.getElementById('startBtn').addEventListener('click', function() {\n"
            "           document.getElementById('startScreen').style.display = 'none';\n"
            "           if (!gameStarted) initGame();\n"
            "       });\n"
            "   });\n"
            "   function animate() { if (!gameStarted) return; requestAnimationFrame(animate); }"
        )
        
        code = self._nvidia_chat("glm", "z-ai/glm-5.2", glm_prompt, max_tokens=8000, temperature=0.8)
        
        # Fallback: GLM başarısız olursa DeepSeek yazsın
        if "API Hatası" in code or len(code) < 100 or "<!DOCTYPE html>" not in code:
            code = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", glm_prompt, max_tokens=8000, extra_body={"chat_template_kwargs":{"thinking":False}})

        # =====================================================================
        # AŞAMA 4: GPT-OSS İLE KODU KONTROL ETME VE DÜZELTME (KALİTE KONTROL)
        # =====================================================================
        if "<!DOCTYPE html>" in code or "<html>" in code:
            gpt_oss_prompt = (
                "You are the QA Engineer. Review the following HTML5 game code.\n"
                "Ensure it strictly has:\n"
                "1. A start button with id=\"startBtn\".\n"
                "2. A start screen with id=\"startScreen\".\n"
                "3. The game loop is NOT auto-starting.\n"
                "4. The startBtn correctly hides the startScreen and calls initGame().\n\n"
                "Fix any bugs, missing tags, or broken event listeners.\n"
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

        # Modeli HTML'e göm
        if model_b64:
            code = code.replace("MODEL_BASE64_PLACEHOLDER", "data:application/octet-stream;base64," + model_b64)

        # ARTIK HİÇBİR JAVASCRIPT ENJEKSİYONU YAPILMIYOR!
        # AI'ın yazdığı kod direkt kabul ediliyor.
        if "<!DOCTYPE html>" in code or "<html>" in code:
            self.raw_game_html = code
            return True
        
        self.raw_game_html = "<h1 style='color:red;text-align:center;'>Oyun üretilemedi. Lütfen daha basit bir prompt deneyin.</h1>"
        return False
