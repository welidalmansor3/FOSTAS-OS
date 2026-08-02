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
        self.project_memory = {
            "assets": [], # Yüklenen modellerin hem adı hem Base64 verisi burada
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
        # 3D modeli Base64 formatına çeviriyoruz ki HTML'in içine gömebilelim
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
        """Kullanıcının 3D modelini ve promptunu alır, WebGL (Three.js) oyunu üretir."""
        
        doc_context = self.project_memory["docs"] if self.project_memory["docs"] else "Yok."
        
        # Yüklenen 3D modeli alıyoruz
        model_info = "Kullanıcı 3D model yüklemedi. Standart şekillerle (kutu, küre) oyunu yap."
        model_b64 = None
        
        if self.project_memory["assets"]:
            model = self.project_memory["assets"][0]
            model_b64 = model["b64"]
            model_info = f"Kullanıcı '{model['name']}' adında bir 3D model yükledi. Bu modeli oyunda kullanmak ZORUNDASIN."
        
        system_prompt = f"""
        You are an expert WebGL Game Developer using Three.js. Create a fully playable game in a SINGLE HTML file.
        
        User Request: "{user_prompt}"
        Document Context: "{doc_context}"
        3D Model Info: "{model_info}"
        
        STRICT RULES:
        1. Output ONLY raw HTML code. Start with <!DOCTYPE html>. No markdown.
        2. If a 3D model is provided, you MUST use Three.js. Include Three.js from CDN:
           <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
           <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
        3. To load the user's 3D model, write EXACTLY this code in your JavaScript:
           const modelUrl = "MODEL_BASE64_PLACEHOLDER";
           const loader = new THREE.GLTFLoader();
           loader.load(modelUrl, function(gltf) {{
               let player = gltf.scene;
               scene.add(player);
               // Player fizikleri ve hareketleri buraya eklenecek
           }});
        4. If no 3D model is provided, use standard Three.js geometries (Box, Sphere).
        5. Game must have: Start screen, Game Loop (requestAnimationFrame), basic physics (gravity, collision), keyboard controls.
        6. Canvas size: 800x600. Center it with a dark background.
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

        # Eğer kullanıcı model yüklediyse, HTML'in içine modelin Base64 verisini gömüyoruz
        if model_b64:
            code = code.replace("MODEL_BASE64_PLACEHOLDER", f"data:application/octet-stream;base64,{model_b64}")

        if "<!DOCTYPE html>" in code or "<html>" in code:
            self.game_html = code
            return True
        
        self.game_html = "<h1 style='color:red;text-align:center;'>Oyun üretilemedi. Lütfen daha basit bir prompt deneyin.</h1>"
        return False
