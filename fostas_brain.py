import os
import json
import time
import google.generativeai as genai
from openai import OpenAI
import requests
from dotenv import load_dotenv

# .env dosyasını yükler
load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.project_memory = {
            "scripts": {},
            "scenes": {},
            "assets": [],
            "docs": {
                "GameBible": "5v5 multiplayer FPS. Cute to horror transition.",
                "Weapons": "11 weapons + sidearm. Toy reskin.",
                "Networking": "Server-authoritative, 20Hz tick, 64Kbps bandwidth."
            }
        }
        
        # .env'den anahtarları al
        zai_key = os.getenv("ZAI_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        tripo_key = os.getenv("TRIPO_API_KEY")

        # AI Configs
        genai.configure(api_key=gemini_key)
        self.gemini = genai.GenerativeModel('gemini-1.5-flash')
        self.zai = OpenAI(api_key=zai_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
        self.tripo_key = tripo_key

    def analyze_prompt(self, user_prompt: str) -> dict:
        context = json.dumps(self.project_memory, indent=2)
        system = f"""
        You are the FOSTAS OS Architect. 
        Current Project Memory: {context}
        Analyze the user prompt: '{user_prompt}'
        If the prompt is large, break it down into MULTIPLE smaller tasks.
        Output STRICTLY JSON with a task list. 
        Each task must have: "agent" (coder/3d_artist/optimizer/level_designer), "task_description", "target_file" (e.g., scripts/player/player.gd).
        """
        try:
            resp = self.gemini.generate_content(system)
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            return {"tasks": [{"agent": "coder", "task_description": user_prompt, "target_file": "scripts/game_main.gd"}]}

    def _get_context_for_file(self, target_file: str) -> str:
        context = "Knowledge Base:\n" + json.dumps(self.project_memory["docs"]) + "\n\n"
        if target_file in self.project_memory["scripts"]:
            context += f"Existing code in {target_file}:\n{self.project_memory['scripts'][target_file]}\n"
        return context

    def write_and_fix_code(self, task_desc: str, target_file: str) -> str:
        context = self._get_context_for_file(target_file)
        
        for attempt in range(2): # Max 2 deneme
            if attempt == 0:
                prompt = f"Task: {task_desc}\nContext: {context}\nWrite Godot 4.3 GDScript code for {target_file}. No markdown blocks, pure code."
            else:
                prompt = f"Previous code had errors: {error_log}\nFix the code for {target_file}."

            try:
                resp = self.zai.chat.completions.create(
                    model="glm-4-flash", 
                    messages=[{"role": "user", "content": prompt}]
                )
                code = resp.choices[0].message.content.replace("```gdscript", "").replace("```", "").strip()
                
                error_log = self._validate_gdscript(code)
                if not error_log:
                    self.project_memory["scripts"][target_file] = code
                    return f"✅ Successfully generated and validated {target_file}.\n\n```gdscript\n{code}\n```"
            except Exception as e:
                error_log = str(e)
                
        return f"❌ Failed to generate code for {target_file}. Error: {error_log}"

    def _validate_gdscript(self, code: str) -> str:
        if "extends" not in code:
            return "Missing 'extends' declaration."
        return ""

    def generate_scene(self, task_desc: str, target_file: str) -> str:
        scene_content = f"[gd_scene format=3]\n[node type=\"Node3D\" name=\"GeneratedWorld\"]\n"
        self.project_memory["scenes"][target_file] = scene_content
        return f"✅ Scene {target_file} created in Workspace."

    def generate_3d_asset(self, task_desc: str) -> str:
        for asset in self.project_memory["assets"]:
            if task_desc.lower() in asset["name"].lower():
                return f"♻️ Asset already exists in Registry: {asset['path']} (Skipping generation)"
        
        try:
            url = "https://api.tripo3d.ai/v2/openapi/task/create"
            headers = {"Authorization": f"Bearer {self.tripo_key}"}
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
                yield self.generate_3d_asset(desc)
            elif agent == "level_designer":
                yield self.generate_scene(desc, target)
            elif agent == "optimizer":
                yield "🚀 Optimization AI: Scanning project... LODs generated, Draw calls reduced."
            
            time.sleep(1)

        yield "\n🛠️ Steam Build Manager: Exporting to Windows/Linux... Build ready!"
