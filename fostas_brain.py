import os
import json
import re
import base64
import html as html_module
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.game_html = ""       # Ekranda gösterilecek iframe kodu
        self.raw_game_html = ""   # İndirme butonu için temiz HTML
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
        
        system_prompt = f"""
        You are an expert HTML5 Game Developer. Create a fully playable game in a SINGLE HTML file.
        
        User Request: "{user_prompt}"
        Document Context: "{doc_context}"
        3D Model Info: "{model_info}"
        
        STRICT RULES:
        1. Output ONLY raw HTML code. Start with <!DOCTYPE html>. No markdown.
        2. If a 3D model is provided, use Three.js. Include EXACTLY these scripts:
           <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
           <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
        3. To load the 3D model, write EXACTLY this code:
           const modelUrl = "MODEL_BASE64_PLACEHOLDER";
           const loader = new THREE.GLTFLoader();
           loader.load(modelUrl, function(gltf) {{
               let player = gltf.scene;
               scene.add(player);
           }});
        4. If no 3D model is provided, use standard Canvas 2D or Three.js geometries.
        5. Game must have: Start screen, Game Loop, physics, controls.

        CRITICAL - START BUTTON RULE (PAY EXTREME ATTENTION):
        - The game MUST have a visible Start Screen with a button (id="startBtn").
        - The game loop (requestAnimationFrame) MUST NOT start automatically.
        - You MUST bind the start button click to initialize the game. 
        - EXACT JAVASCRIPT PATTERN TO USE:
          let gameStarted = false;
          function initGame() {{
              // Setup
              gameStarted = true;
              animate();
          }}
          document.getElementById('startBtn').addEventListener('click', function() {{
              document.getElementById('startScreen').style.display = 'none';
              if (!gameStarted) initGame();
          }});
          function animate() {{
              if (!gameStarted) return;
              requestAnimationFrame(animate);
          }}
        """

        # 1. GLM-5.2 ile üret
        code = self._nvidia_chat("glm", "z-ai/glm-5.2", system_prompt, max_tokens=8000, temperature=0.8)
        
        # 2. Hata varsa DeepSeek
        if "API Hatası" in code or len(code) < 100:
            code = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", system_prompt, max_tokens=8000, extra_body={"chat_template_kwargs":{"thinking":False}})
        
        # 3. O da olmazsa Llama
        if "API Hatası" in code or len(code) < 100:
            code = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", system_prompt, max_tokens=4000, temperature=0.7)

        # Markdown temizliği
        code = re.sub(r"^```html\n?", "", code.strip())
        code = re.sub(r"\n?```$", "", code.strip())

        # Modeli HTML'e göm
        if model_b64:
            code = code.replace("MODEL_BASE64_PLACEHOLDER", f"data:application/octet-stream;base64,{model_b64}")

        if "<!DOCTYPE html>" in code or "<html>" in code:
            self.raw_game_html = code # İndirme butonu için temiz HTML
            
            # Senin harika iframe srcdoc önerin:
            escaped_html = html_module.escape(code)
            self.game_html = f'<iframe srcdoc="{escaped_html}" style="width:100%;height:600px;border:none;overflow:hidden;"></iframe>'
            return True
        
        self.game_html = "<h1 style='color:red;text-align:center;'>Oyun üretilemedi. Lütfen daha basit bir prompt deneyin.</h1>"
        return False
