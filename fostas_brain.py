import os
import json
import re
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.game_html = ""
        self.raw_game_html = ""
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
            return f"Hata: {model_client} client bağlı değil."
        
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
            return f"API Hatası ({model_name}): {str(e)}"

    def upload_document(self, text: str):
        self.project_memory["docs"] += f"\n\n--- USER UPLOAD ---\n{text[:3000]}"

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
                "path": f"res://assets/{safe_name}", 
                "data": file_data,
                "b64": encoded_data
            })
        return f"res://assets/{safe_name}"

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
            model_info = f"Kullanıcı '{model['name']}' adında bir 3D model yükledi. Bu modeli oyunda kullanmak ZORUNDASIN."
        
        # =====================================================================
        # AŞAMA 1: LLAMA 3.3 İLE OYUN MEKANİKLERİNİ PLANLAMA (MİMAR)
        # =====================================================================
        llama_prompt = f"""
        You are the Game Architect. User wants a game: "{user_prompt}".
        Context: "{doc_context}"
        Model Info: "{model_info}"
        Define the game mechanics, win/lose conditions, controls, and physics in 3 short bullet points.
        """
        game_plan = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", llama_prompt, max_tokens=1000, temperature=0.5)

        # =====================================================================
        # AŞAMA 2: DEEPSEEK V4 İLE TEKNİK ŞARTNAME HAZIRLAMA (MÜHENDİS)
        # =====================================================================
        deepseek_prompt = f"""
        You are the Technical Engineer. Based on this game plan: "{game_plan}", write a detailed technical specification for an HTML5 game.
        List the required JavaScript variables, functions (initGame, animate), and CSS elements (startBtn, startScreen).
        Do NOT write the full HTML yet. Just the technical blueprint.
        """
        tech_spec = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", deepseek_prompt, max_tokens=2000, extra_body={"chat_template_kwargs":{"thinking":False}})

        # =====================================================================
        # AŞAMA 3: GLM-5.2 İLE KODU YAZMA (KODLAYICI)
        # =====================================================================
        glm_prompt = f"""
        You are the HTML5 Coder. Write a fully playable game in a SINGLE HTML file using HTML5 Canvas or Three.js.
        
        Game Request: "{user_prompt}"
        Model Info: "{model_info}"
        Game Plan: "{game_plan}"
        Technical Spec: "{tech_spec}"
        
        STRICT RULES:
        1. Output ONLY raw HTML code. Start with <!DOCTYPE html>. No markdown.
        2. If a 3D model is provided, use Three.js. Include EXACTLY these scripts:
           <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
           <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
        3. To load the 3D model, write EXACTLY this code:
           const modelUrl = "MODEL_BASE64_PLACEHOLDER";
           const loader = new THREE.GLTFLoader();
           loader.load(modelUrl, function(gltf) {{ scene.add(gltf.scene); }});
        4. Game MUST have: Start screen (id="startScreen"), Start button (id="startBtn"), Game Loop.
        5. Use this EXACT JavaScript pattern for the start button:
           let gameStarted = false;
           function initGame() {{ gameStarted = true; animate(); }}
           document.addEventListener('DOMContentLoaded', function() {{
               document.getElementById('startBtn').addEventListener('click', function() {{
                   document.getElementById('startScreen').style.display = 'none';
                   if (!gameStarted) initGame();
               }});
           }});
           function animate() {{ if (!gameStarted) return; requestAnimationFrame(animate); }}
        """
        
        code = self._nvidia_chat("glm", "z-ai/glm-5.2", glm_prompt, max_tokens=8000, temperature=0.8)
        
        # Eğer GLM başarısız olursa (çekilirsek), DeepSeek'in yazmasını istiyoruz
        if "API Hatası" in code or len(code) < 100 or "<!DOCTYPE html>" not in code:
            code = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", glm_prompt, max_tokens=8000, extra_body={"chat_template_kwargs":{"thinking":False}})

        # =====================================================================
        # AŞAMA 4: GPT-OSS İLE KODU KONTROL ETME VE DÜZELTME (KALİTE KONTROL)
        # =====================================================================
        if "<!DOCTYPE html>" in code or "<html>" in code:
            gpt_oss_prompt = f"""
            You are the QA Engineer. Review the following HTML5 game code.
            Ensure it strictly has:
            1. A start button with id="startBtn".
            2. A start screen with id="startScreen".
            3. The game loop is NOT auto-starting (no direct call to animate() on load).
            4. The startBtn correctly hides the startScreen and calls initGame().
