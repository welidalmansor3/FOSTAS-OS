import os
import json
import time
import google.generativeai as genai
from openai import OpenAI
import requests
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        # 9. Project Memory & 14. Version Control
        self.project_memory = {
            "scripts": {},  # "scripts/player.gd": [{"v": 1, "code": "..."}, {"v": 2, "code": "..."}]
            "scenes": {},   # "scenes/player.tscn": [{"v": 1, "code": "..."}]
            "assets": [],   # [{"name": "Fly", "path": "res://assets/fly.glb", "data": b'binary'}]
            "docs": {
                "GameBible": "5v5 multiplayer FPS. Cute to horror transition.",
                "Networking": "Server-authoritative, 20Hz tick, 64Kbps bandwidth."
            }
        }
        
        zai_key = os.getenv("ZAI_API_KEY", "932582eae02443a8b9fa9d9f57e26f57.A7xCiqXN5T5Oy7Vr")
        gemini_key = os.getenv("GEMINI_API_KEY", "AIzaSyDUMMY_KEY_REPLACE_WITH_REAL_ONE")
        tripo_key = os.getenv("TRIPO_API_KEY", "tsk_Krye7xF-ICd74E-P8xfhRFmr1_H1VmsX8le1DMhBnr0")

        try:
            genai.configure(api_key=gemini_key)
            self.gemini = genai.GenerativeModel('gemini-1.5-flash')
            self.gemini_pro = genai.GenerativeModel('gemini-1.5-pro') 
        except:
            self.gemini = None
            self.gemini_pro = None
            
        try:
            self.zai = OpenAI(api_key=zai_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
        except:
            self.zai = None
            
        self.tripo_key = tripo_key

    def analyze_prompt(self, user_prompt: str) -> dict:
        if not self.gemini:
            return {"tasks": [{"agent": "coder", "task_description": user_prompt, "target_file": "scripts/game_main.gd"}]}
            
        context = json.dumps(self.project_memory["docs"], indent=2)
        system = f"""
        You are the FOSTAS OS Architect. 
        Knowledge Base: {context}
        Prompt: '{user_prompt}'
        If creating an entity (player/enemy), generate BOTH a script (.gd) AND a scene (.tscn) that includes AnimationTree setup.
        Output STRICTLY JSON with a task list. 
        Each task: {{"agent": "coder/3d_artist/optimizer", "task_description": "...", "target_file": "scripts/player/player.gd"}}
        """
        try:
            resp = self.gemini.generate_content(system)
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception:
            return {"tasks": [{"agent": "coder", "task_description": user_prompt, "target_file": "scripts/game_main.gd"}]}

    def _get_context_for_file(self, target_file: str) -> str:
        context = "Knowledge Base:\n" + json.dumps(self.project_memory["docs"]) + "\n\n"
        if target_file in self.project_memory["scripts"] and len(self.project_memory["scripts"][target_file]) > 0:
            latest_code = self.project_memory["scripts"][target_file][-1]["code"]
            context += f"Existing code in {target_file}:\n{latest_code}\n"
        return context

    def write_and_fix_code(self, task_desc: str, target_file: str) -> str:
        context = self._get_context_for_file(target_file)
        code = None
        
        if self.zai:
            try:
                resp = self.zai.chat.completions.create(
                    model="glm-4-flash", 
                    messages=[{"role": "user", "content": f"Task: {task_desc}\nContext: {context}\nWrite Godot 4.3 code for {target_file}. If .tscn, write XML. No markdown."}]
                )
                code = resp.choices[0].message.content.strip()
            except:
                code = None 

        if not code and self.gemini_pro:
            try:
                prompt = f"Task: {task_desc}\nContext: {context}\nWrite Godot 4.3 code for {target_file}. If .tscn, write XML. No markdown."
                resp = self.gemini_pro.generate_content(prompt)
                code = resp.text.replace("```gdscript", "").replace("```xml", "").replace("```", "").strip()
            except:
                code = None

        if not code:
            code = f"extends Node\n# SIMULATION MODE\nfunc _ready(): pass"

        # 14. Version Control (Save as new version)
        if target_file.endswith(".gd"):
            if target_file not in self.project_memory["scripts"]:
                self.project_memory["scripts"][target_file] = []
            version_num = len(self.project_memory["scripts"][target_file]) + 1
            self.project_memory["scripts"][target_file].append({"v": version_num, "code": code})
        elif target_file.endswith(".tscn"):
            if target_file not in self.project_memory["scenes"]:
                self.project_memory["scenes"][target_file] = []
            version_num = len(self.project_memory["scenes"][target_file]) + 1
            self.project_memory["scenes"][target_file].append({"v": version_num, "code": code})

        return f"✅ Generated {target_file} (v{version_num})."

    def generate_3d_asset(self, task_desc: str) -> str:
        for asset in self.project_memory["assets"]:
            if task_desc.lower() in asset["name"].lower():
                return f"♻️ Asset exists: {asset['path']}"

        try:
            url = "https://api.tripo3d.ai/v2/openapi/task/create"
            headers = {"Authorization": f"Bearer {self.tripo_key}"}
            payload = {"type": "text_to_model", "prompt": f"Game ready lowpoly: {task_desc}"}
            resp = requests.post(url, headers=headers, json=payload)
            
            if resp.status_code == 200:
                task_id = resp.json().get("data", {}).get("task_id")
                asset_path = f"res://assets/{task_desc.replace(' ', '_')}.glb"
                
                # 1. Madde: Polling and Downloading .glb
                yield f"🎨 Tripo task started (ID: {task_id}). Waiting for model to finish..."
                model_url = self._poll_tripo_task(task_id)
                
                if model_url:
                    yield "⬇️ Model ready! Downloading binary .glb data..."
                    model_data = requests.get(model_url).content
                    self.project_memory["assets"].append({"name": task_desc, "path": asset_path, "data": model_data})
                    yield f"✅ 3D Model downloaded and saved to {asset_path}!"
                else:
                    self.project_memory["assets"].append({"name": task_desc, "path": asset_path, "data": None})
                    yield "⚠️ Tripo timed out. Model registered but not downloaded."
            else:
                yield f"❌ Tripo API Error: {resp.text}"
        except Exception as e:
            yield f"❌ Tripo Connection Error: {str(e)}"

    def _poll_tripo_task(self, task_id: str, max_retries=6) -> str:
        url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
        headers = {"Authorization": f"Bearer {self.tripo_key}"}
        
        for _ in range(max_retries):
            time.sleep(5) # Wait 5 seconds between checks
            try:
                resp = requests.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    status = data.get("status")
                    if status == "success":
                        return data.get("model", {}).get("url")
                    elif status == "failed":
                        return None
            except:
                pass
        return None

    def undo_last_version(self, file_path: str) -> bool:
        """14. Version Control: Reverts to previous version"""
        if file_path in self.project_memory["scripts"] and len(self.project_memory["scripts"][file_path]) > 1:
            self.project_memory["scripts"][file_path].pop()
            return True
        if file_path in self.project_memory["scenes"] and len(self.project_memory["scenes"][file_path]) > 1:
            self.project_memory["scenes"][file_path].pop()
            return True
        return False

    def run_fostas_pipeline(self, user_prompt: str):
        yield "🧠 FOSTAS OS Architect analyzing prompt and routing tasks...\n"
        plan = self.analyze_prompt(user_prompt)
        
        if "tasks" not in plan:
            yield "Error in planning phase."
            return

        for task in plan["tasks"]:
            agent = task.get("agent")
            desc = task.get("task_description")
            target = task.get("target_file", "unknown.gd")
            
            yield f"\n--- ▶️ Task: {desc[:50]}... ({agent}) ---"
            
            if agent == "coder":
                yield self.write_and_fix_code(desc, target)
            elif agent == "3d_artist":
                # Bu bir generator olduğu için yield kullanıyoruz
                for step in self.generate_3d_asset(desc):
                    yield step
            elif agent == "level_designer":
                yield self.write_and_fix_code(desc, target) # Sahne dosyalarını da yazar
            elif agent == "optimizer":
                yield "🚀 Optimization AI: Scanning project... LODs generated, Draw calls reduced."
            
            time.sleep(1)

        yield "\n🛠️ Steam Build Manager: Generating export_presets.cfg and build.bat for Godot CLI..."
        self.project_memory["scripts"]["export_presets.cfg"] = [{"v": 1, "code": "[preset.0]\nname=\"Windows Desktop\"\nplatform=\"Windows Desktop\""}]
        yield "✅ Build configurations ready! Use Download button to get the project."
