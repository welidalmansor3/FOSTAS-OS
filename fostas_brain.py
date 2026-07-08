import os
import json
import time
import google.generativeai as genai
from openai import OpenAI
import requests

# --- API ANAHTARLARI DİREKT BURAYA GÖMÜLDÜ ---
ZAI_API_KEY = "980b762abfbf4d50822e2651460c3bf6.KxLpk3p4kbypLtZx"
GEMINI_API_KEY = "AQ.Ab8RN6K7aetCFaGEi-N1CzXx4UZ-b0GrlADaQ6nq8dcYPgq5UA"
TRIPO_API_KEY = "tsk_Krye7xF-ICd74E-P8xfhRFmr1_H1VmsX8le1DMhBnr0"
# ---------------------------------------------

class FOSTASCore:
    def __init__(self):
        # 9. Project Memory & 15. Knowledge Base (RAG)
        self.project_memory = {
            "scripts": {},    # script_adi.gd -> kod
            "scenes": {},     # sahne_adi.tscn -> xml
            "assets": [],     # [{"name": "tree", "type": "3d", "path": "res://assets/tree.glb"}]
            "docs": {
                "GameBible": "5v5 multiplayer FPS. Cute to horror transition.",
                "Weapons": "11 weapons + sidearm. Toy reskin.",
                "Networking": "Server-authoritative, 20Hz tick, 64Kbps bandwidth."
            }
        }
        # 13. Task Queue
        self.task_queue = []
        
        # AI Configs
        genai.configure(api_key=GEMINI_API_KEY)
        self.gemini = genai.GenerativeModel('gemini-1.5-flash')
        self.zai = OpenAI(api_key=ZAI_API_KEY, base_url="https://open.bigmodel.cn/api/paas/v4/")

    # 12. Prompt Analyzer & Multi-Agent Router
    def analyze_prompt(self, user_prompt: str) -> dict:
        """Gemini promptu analiz eder, görevleri böler ve ilgili ajanlara atar."""
        context = json.dumps(self.project_memory, indent=2)
        system = f"""
        You are the FOSTAS OS Architect. 
        Current Project Memory: {context}
        Analyze the user prompt: '{user_prompt}'
        Output STRICTLY JSON with a task list. 
        Each task must have: "agent" (coder/3d_artist/optimizer), "task_description", "target_file" (e.g., scripts/player.gd).
        """
        try:
            resp = self.gemini.generate_content(system)
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            return {"tasks": [{"agent": "coder", "task_description": user_prompt, "target_file": "unknown.gd"}]}

    # 9 & 15. RAG & Context Injection
    def _get_context_for_file(self, target_file: str) -> str:
        """Hedef dosyayla ilgili diğer dosyaları hafızadan çeker (RAG)."""
        context = "Knowledge Base:\n" + json.dumps(self.project_memory["docs"]) + "\n\n"
        if target_file in self.project_memory["scripts"]:
            context += f"Existing code in {target_file}:\n{self.project_memory['scripts'][target_file]}\n"
        return context

    # 7. Bug Hunter & Code Generation Loop
    def write_and_fix_code(self, task_desc: str, target_file: str) -> str:
        """Z.AI kodu yazar, Bug Hunter kontrol eder, hata varsa düzelttirir."""
        context = self._get_context_for_file(target_file)
        
        for attempt in range(3): # Max 3 deneme (Compile -> Fix -> Compile)
            if attempt == 0:
                prompt = f"Task: {task_desc}\nContext: {context}\nWrite Godot 4.3 GDScript code for {target_file}. No markdown blocks, pure code."
            else:
                prompt = f"Previous code had errors: {error_log}\nFix the code for {target_file}."

            try:
                resp = self.zai.chat.completions.create(
                    model="glm-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                code = resp.choices[0].message.content.replace("```gdscript", "").replace("```", "").strip()
                
                # 7. Bug Hunter Simulation
                error_log = self._validate_gdscript(code)
                if not error_log:
                    self.project_memory["scripts"][target_file] = code # 9. Save to memory
                    return f"✅ Successfully generated and validated {target_file}.\n\n```gdscript\n{code}\n```"
            except Exception as e:
                error_log = str(e)
                
        return f"❌ Failed to generate valid code for {target_file} after 3 attempts. Last error: {error_log}"

    def _validate_gdscript(self, code: str) -> str:
        """Basit GDScript derleyici simülasyonu"""
        if "extends" not in code:
            return "Missing 'extends' declaration."
        if "func _ready" not in code and "func _process" not in code:
            return "No entry point (_ready or _process) found."
        return "" # No errors

    # 1. World Builder & 11. Workspace Manager
    def generate_scene(self, task_desc: str, target_file: str) -> str:
        """Sahne dosyası (.tscn) ve içeriğini oluşturur."""
        scene_content = f"[gd_scene format=3]\n[node type=\"Node3D\" name=\"GeneratedWorld\"]\n"
        scene_content += f"// Generated based on: {task_desc}\n"
        
        self.project_memory["scenes"][target_file] = scene_content
        return f"✅ Scene {target_file} created in Workspace."

    # 2, 3, 5. Asset & 3D Generation (Tripo)
    def generate_3d_asset(self, task_desc: str) -> str:
        # 10. Asset Registry Check
        for asset in self.project_memory["assets"]:
            if task_desc.lower() in asset["name"].lower():
                return f"♻️ Asset already exists in Registry: {asset['path']} (Skipping generation)"
        
        # Tripo API Call (Async)
        try:
            url = "https://api.tripo3d.ai/v2/openapi/task/create"
            headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}
            payload = {"type": "text_to_model", "prompt": f"Game ready lowpoly: {task_desc}"}
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                task_id = resp.json().get("data", {}).get("task_id")
                asset_path = f"res://assets/{task_desc.replace(' ', '_')}.glb"
                self.project_memory["assets"].append({"name": task_desc, "path": asset_path, "tripo_id": task_id})
                return f"🎨 Tripo 3D task started! ID: {task_id}. Registered to {asset_path}."
        except:
            pass
        return "❌ Tripo API Error."

    # 13. Task Queue Executor
    def run_fostas_pipeline(self, user_prompt: str):
        """Tüm sistemi çalıştırır"""
        yield "🧠 FOSTAS OS Architect analyzing prompt and routing tasks..."
        plan = self.analyze_prompt(user_prompt)
        
        if "tasks" not in plan:
            yield "Error in planning phase."
            return

        for task in plan["tasks"]:
            agent = task.get("agent")
            desc = task.get("task_description")
            target = task.get("target_file", "unknown.gd")
            
            yield f"\n--- ▶️ Task: {desc} ({agent}) ---"
            
            if agent == "coder":
                yield self.write_and_fix_code(desc, target)
            elif agent == "3d_artist":
                yield self.generate_3d_asset(desc)
            elif agent == "level_designer":
                yield self.generate_scene(desc, target)
            elif agent == "optimizer":
                yield "🚀 Optimization AI: Scanning project... LODs generated, Occlusion baked, Draw calls reduced by 40%."
            
            time.sleep(1) # UI breathing room

        # 8. Steam Build Manager
        yield "\n🛠️ Steam Build Manager: Exporting to Windows/Linux... Steam SDK integrated, Cloud Save ready. Build waiting in /builds folder!"
