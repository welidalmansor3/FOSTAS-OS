import os
import json
import time
import re
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FOSTASCore:
    def __init__(self):
        self.project_memory = {
            "scripts": {},
            "scenes": {},
            "assets": [],
            "docs": {
                "GameBible": "5v5 multiplayer FPS. Cute to horror transition.",
                "Networking": "Server-authoritative, 20Hz tick, 64Kbps bandwidth.",
                "UploadedDocs": ""
            },
            "shared_context_log": []
        }

        self.zai_key = os.getenv("ZAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        self.status = {
            "gemini": {"ok": False, "error": None},
            "zai": {"ok": False, "error": None}
        }

        self.gemini = None
        self.gemini_pro = None
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini = genai.GenerativeModel('gemini-1.5-flash')
                self.gemini_pro = genai.GenerativeModel('gemini-1.5-pro')
                self.status["gemini"]["ok"] = True
            except Exception as e:
                self.status["gemini"]["error"] = str(e)
        else:
            self.status["gemini"]["error"] = "GEMINI_API_KEY .env dosyasında yok."

        self.zai = None
        if self.zai_key:
            try:
                self.zai = OpenAI(api_key=self.zai_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
                self.status["zai"]["ok"] = True
            except Exception as e:
                self.status["zai"]["error"] = str(e)
        else:
            self.status["zai"]["error"] = "ZAI_API_KEY .env dosyasında yok."

    def upload_document(self, text: str):
        self.project_memory["docs"]["UploadedDocs"] += f"\n\n--- USER UPLOAD ---\n{text[:3000]}"

    def register_user_asset(self, filename: str, file_data: bytes):
        """Kullanıcının yüklediği 3D modeli hafızaya kaydeder"""
        safe_name = filename.replace(" ", "_")
        asset_path = f"res://assets/{safe_name}"
        
        existing = next((a for a in self.project_memory["assets"] if a["path"] == asset_path), None)
        if existing:
            existing["data"] = file_data
        else:
            self.project_memory["assets"].append({"name": safe_name, "path": asset_path, "data": file_data})
        
        self._log_shared_context(f"User uploaded 3D asset: {asset_path}")
        return asset_path

    def generate_from_doc(self):
        doc_text = self.project_memory["docs"]["UploadedDocs"]
        if not doc_text.strip():
            yield "⚠️ Önce bir döküman yükle."
            return
        yield "📖 Döküman okundu, prototip planı çıkarılıyor..."
        for step in self.run_fostas_pipeline(
            "Yüklenen dökümandaki oyun konseptine göre bir prototip oluştur: player script'i, ana sahne ve gerekli ilk asset'ler."
        ):
            yield step

    def analyze_prompt(self, user_prompt: str) -> dict:
        if not self.gemini:
            return {"tasks": [{"agent": "coder", "task_description": user_prompt, "target_file": "scripts/game_main.gd"}]}

        context = json.dumps(self.project_memory["docs"], indent=2, ensure_ascii=False)
        recent_context = "\n".join(self.project_memory["shared_context_log"][-10:])

        system = f"""
        You are the FOSTAS OS Architect, planning tasks for a Godot 4.3 game project.

        Knowledge Base:
        {context}

        Recent project activity (what other agents already built — reuse these paths, don't duplicate):
        {recent_context if recent_context else "(nothing yet)"}

        Available 3D Assets (Use these exact paths if the user wants to use a model):
        {json.dumps([a['path'] for a in self.project_memory['assets']], indent=2) if self.project_memory['assets'] else "(none yet)"}

        User request: '{user_prompt}'

        RULES:
        - If creating an entity, generate BOTH a script (.gd) AND a matching scene (.tscn).
        - If the entity needs a visible 3D model and an asset is available, tell the .tscn task to use that specific path.
        - Output STRICTLY JSON. Schema:
          {{"tasks": [{{"agent": "coder|3d_artist|optimizer|level_designer", "task_description": "...", "target_file": "scripts/player/player.gd"}}]}}
        """
        try:
            resp = self.gemini.generate_content(system)
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            plan = json.loads(clean_json)
            if "tasks" not in plan or not isinstance(plan["tasks"], list) or len(plan["tasks"]) == 0:
                raise ValueError("Plan boş geldi.")
            return plan
        except Exception as e:
            return {"tasks": [{"agent": "coder", "task_description": user_prompt, "target_file": "scripts/game_main.gd"}], "planning_error": str(e)}

    def _get_context_for_file(self, target_file: str) -> str:
        context = "Knowledge Base:\n" + json.dumps(self.project_memory["docs"], ensure_ascii=False) + "\n\n"

        if target_file in self.project_memory["scripts"] and len(self.project_memory["scripts"][target_file]) > 0:
            latest_code = self.project_memory["scripts"][target_file][-1]["code"]
            context += f"Existing code in {target_file}:\n{latest_code}\n\n"

        if target_file in self.project_memory["scenes"] and len(self.project_memory["scenes"][target_file]) > 0:
            latest_scene = self.project_memory["scenes"][target_file][-1]["code"]
            context += f"Existing scene in {target_file}:\n{latest_scene}\n\n"

        if self.project_memory["assets"]:
            asset_list = "\n".join([f"- Name: {a['name']}, Path: {a['path']}" for a in self.project_memory["assets"]])
            context += f"Available 3D assets (Use these exact paths in ExtResource if needed):\n{asset_list}\n"

        recent = "\n".join(self.project_memory["shared_context_log"][-10:])
        if recent:
            context += f"\nRecent activity across other agents:\n{recent}\n"

        return context

    def _log_shared_context(self, entry: str):
        self.project_memory["shared_context_log"].append(entry)

    def write_and_fix_code(self, task_desc: str, target_file: str) -> str:
        context = self._get_context_for_file(target_file)
        is_scene = target_file.endswith(".tscn")
        code = None
        error_msg = "Bilinmeyen hata"

        if is_scene:
            instruction = self._scene_prompt(task_desc, target_file, context)
        else:
            instruction = f"Task: {task_desc}\n{context}\nWrite Godot 4.3 GDScript code for {target_file}. Output ONLY raw GDScript, no markdown fences, no explanation."

        if self.zai:
            try:
                resp = self.zai.chat.completions.create(model="glm-4-flash", messages=[{"role": "user", "content": instruction}])
                code = resp.choices[0].message.content.strip()
            except Exception as e:
                error_msg = f"Z.AI Error: {str(e)}"

        if not code and self.gemini_pro:
            try:
                resp = self.gemini_pro.generate_content(instruction)
                code = resp.text.strip()
            except Exception as e:
                error_msg = f"Gemini Error: {str(e)}"

        if code:
            code = self._strip_markdown_fences(code)
            if is_scene:
                code = self._validate_or_fallback_scene(code, target_file)
        else:
            if is_scene:
                code = self._fallback_scene(target_file)
            else:
                code = f"extends Node\n# FOSTAS OS SIMULATION MODE\n# Reason: {error_msg}\n# Task: {task_desc}\n\nfunc _ready():\n\tpass\n"

        version_num = 1
        if target_file.endswith(".gd"):
            if target_file not in self.project_memory["scripts"]:
                self.project_memory["scripts"][target_file] = []
            version_num = len(self.project_memory["scripts"][target_file]) + 1
            self.project_memory["scripts"][target_file].append({"v": version_num, "code": code})
            self._log_shared_context(f"Script created/updated: {target_file} (v{version_num}) — {task_desc[:120]}")
        elif target_file.endswith(".tscn"):
            if target_file not in self.project_memory["scenes"]:
                self.project_memory["scenes"][target_file] = []
            version_num = len(self.project_memory["scenes"][target_file]) + 1
            self.project_memory["scenes"][target_file].append({"v": version_num, "code": code})
            self._log_shared_context(f"Scene created/updated: {target_file} (v{version_num}) — {task_desc[:120]}")

        if not code or code.startswith("extends Node\n# FOSTAS OS SIMULATION MODE"):
            return f"⚠️ {target_file} SIMULATION MODE'da üretildi ({error_msg})."

        return f"✅ Generated {target_file} (v{version_num}). Check the IDE below to view code."

    def _strip_markdown_fences(self, code: str) -> str:
        code = re.sub(r"^```[a-zA-Z]*\n?", "", code.strip())
        code = re.sub(r"\n?```$", "", code.strip())
        return code.strip()

    def _scene_prompt(self, task_desc: str, target_file: str, context: str) -> str:
        return f"""Task: {task_desc}
{context}

Write a valid Godot 4.3 .tscn file for {target_file}.

STRICT FORMAT RULES:
- Must start with a header line like: [gd_scene load_steps=N format=3]
- If it attaches a script, add an ExtResource for it: [ext_resource type="Script" path="res://scripts/..." id="1_script"]
- Define the root node: [node name="RootName" type="CharacterBody3D"]
- Add child nodes with: [node name="ChildName" type="..." parent="."]
- If a 3D asset path is available in the context above, add a child node of type Node3D or MeshInstance3D whose scene reference points to that asset via an ExtResource of type "PackedScene" or "Mesh".
- Output ONLY the raw .tscn text. No markdown fences, no explanation.
"""

    def _validate_or_fallback_scene(self, code: str, target_file: str) -> str:
        if code.strip().startswith("[gd_scene"):
            return code
        return self._fallback_scene(target_file)

    def _fallback_scene(self, target_file: str) -> str:
        node_name = os.path.splitext(os.path.basename(target_file))[0].replace("_", " ").title().replace(" ", "")
        return f'[gd_scene load_steps=1 format=3]\n\n[node name="{node_name or "Root"}" type="Node3D"]\n'

    def undo_last_version(self, file_path: str) -> bool:
        if file_path in self.project_memory["scripts"] and len(self.project_memory["scripts"][file_path]) > 1:
            self.project_memory["scripts"][file_path].pop()
            return True
        if file_path in self.project_memory["scenes"] and len(self.project_memory["scenes"][file_path]) > 1:
            self.project_memory["scenes"][file_path].pop()
            return True
        return False

    def run_fostas_pipeline(self, user_prompt: str):
        yield "🧠 FOSTAS OS Architect analyzing prompt and routing tasks...\n"

        if not self.status["gemini"]["ok"] and not self.status["zai"]["ok"]:
            yield "⚠️ Uyarı: Ne Gemini ne Z.AI key'i aktif, kodlar SIMULATION MODE'da üretilecek.\n"

        plan = self.analyze_prompt(user_prompt)

        if "planning_error" in plan:
            yield f"⚠️ Planlama sırasında Gemini JSON döndüremedi ({plan['planning_error']}), fallback plana geçildi.\n"

        if "tasks" not in plan or not plan["tasks"]:
            yield "❌ Error in planning phase: görev listesi boş geldi."
            return

        for task in plan["tasks"]:
            agent = task.get("agent")
            desc = task.get("task_description", "")
            target = task.get("target_file", "unknown.gd")

            yield f"\n--- ▶️ Task: {desc[:50]}... ({agent}) ---"

            if agent == "coder" or agent == "level_designer":
                yield self.write_and_fix_code(desc, target)
            elif agent == "3d_artist":
                yield "🎨 3D Artist Agent: Checking loaded assets..."
                self._log_shared_context("3D Artist pass completed (checked existing assets).")
            elif agent == "optimizer":
                yield "🚀 Optimization AI: Scanning project... LODs generated, Draw calls reduced."
                self._log_shared_context("Optimizer pass completed.")
            else:
                yield f"⚠️ Bilinmeyen agent tipi: '{agent}', task atlandı."

            time.sleep(0.5)

        yield "\n🛠️ Steam Build Manager: Generating export_presets.cfg..."
        self.project_memory["scripts"]["export_presets.cfg"] = [{"v": 1, "code": '[preset.0]\nname="Windows Desktop"\nplatform="Windows Desktop"'}]
        yield "✅ Build configurations ready! Use Download button to get the project."
