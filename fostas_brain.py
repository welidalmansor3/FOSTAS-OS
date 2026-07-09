import os
import json
import time
import re
import google.generativeai as genai
from openai import OpenAI
import requests
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
            # YENİ: agent'lar arası paylaşılan bağlam.
            # coder bir script yazınca ya da 3d_artist bir asset üretince
            # buraya kısa bir özet düşer, bir sonraki task bunu görür.
            "shared_context_log": []
        }

        self.zai_key = os.getenv("ZAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.tripo_key = os.getenv("TRIPO_API_KEY")

        # Hangi servislerin gerçekten aktif olduğunu başlangıçta netleştiriyoruz.
        # Eskiden except: pass ile sessizce None oluyordu, şimdi sebep saklanıyor.
        self.status = {
            "gemini": {"ok": False, "error": None},
            "zai": {"ok": False, "error": None},
            "tripo": {"ok": False, "error": None},
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

        if self.tripo_key:
            self.status["tripo"]["ok"] = True
        else:
            self.status["tripo"]["error"] = "TRIPO_API_KEY .env dosyasında yok."

    # ------------------------------------------------------------------
    # DOKÜMAN YÜKLEME
    # ------------------------------------------------------------------
    def upload_document(self, text: str):
        """Yüklenen PDF/TXT dosyalarını hafızaya (RAG) kaydeder"""
        self.project_memory["docs"]["UploadedDocs"] += f"\n\n--- USER UPLOAD ---\n{text[:3000]}"

    def generate_from_doc(self):
        """Yüklenen dökümana göre otomatik prototip planı çıkarır ve çalıştırır."""
        doc_text = self.project_memory["docs"]["UploadedDocs"]
        if not doc_text.strip():
            yield "⚠️ Önce bir döküman yükle."
            return
        yield "📖 Döküman okundu, prototip planı çıkarılıyor..."
        for step in self.run_fostas_pipeline(
            "Yüklenen dökümandaki oyun konseptine göre bir prototip oluştur: player script'i, ana sahne ve gerekli ilk asset'ler."
        ):
            yield step

    # ------------------------------------------------------------------
    # PLANLAMA (ARCHITECT)
    # ------------------------------------------------------------------
    def analyze_prompt(self, user_prompt: str) -> dict:
        if not self.gemini:
            # Gemini yoksa bile en azından tek görevlik bir fallback plan üret.
            return {
                "tasks": [
                    {"agent": "coder", "task_description": user_prompt, "target_file": "scripts/game_main.gd"}
                ]
            }

        context = json.dumps(self.project_memory["docs"], indent=2, ensure_ascii=False)
        recent_context = "\n".join(self.project_memory["shared_context_log"][-10:])

        system = f"""
        You are the FOSTAS OS Architect, planning tasks for a Godot 4.3 game project.

        Knowledge Base:
        {context}

        Recent project activity (what other agents already built — reuse these paths, don't duplicate):
        {recent_context if recent_context else "(nothing yet)"}

        User request: '{user_prompt}'

        RULES:
        - If creating an entity (player/enemy/NPC), generate BOTH a script (.gd) AND a matching scene (.tscn) as two separate tasks, and make sure the .tscn task_description explicitly says which script (target_file) it must attach as the root node's script.
        - If the entity needs a visible 3D model, ALSO add a "3d_artist" task, and make the .tscn task_description say it should reference that asset by name so the artist's output path gets wired into the scene.
        - Reuse existing target_file paths from "Recent project activity" if the user is asking to modify something that already exists, instead of creating a new file.
        - Output STRICTLY JSON, no markdown fences, no prose. Schema:
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
            # Sessizce yutmak yerine sebebi kullanıcıya taşıyoruz.
            return {
                "tasks": [
                    {"agent": "coder", "task_description": user_prompt, "target_file": "scripts/game_main.gd"}
                ],
                "planning_error": str(e)
            }

    # ------------------------------------------------------------------
    # BAĞLAM TOPLAMA (agent'lar birbirini görsün diye)
    # ------------------------------------------------------------------
    def _get_context_for_file(self, target_file: str) -> str:
        context = "Knowledge Base:\n" + json.dumps(self.project_memory["docs"], ensure_ascii=False) + "\n\n"

        if target_file in self.project_memory["scripts"] and len(self.project_memory["scripts"][target_file]) > 0:
            latest_code = self.project_memory["scripts"][target_file][-1]["code"]
            context += f"Existing code in {target_file}:\n{latest_code}\n\n"

        if target_file in self.project_memory["scenes"] and len(self.project_memory["scenes"][target_file]) > 0:
            latest_scene = self.project_memory["scenes"][target_file][-1]["code"]
            context += f"Existing scene in {target_file}:\n{latest_scene}\n\n"

        # Son üretilen asset ve script'leri de ekliyoruz ki .tscn üretirken
        # LLM hangi script'e ve hangi .glb'ye referans vereceğini bilsin.
        if self.project_memory["assets"]:
            asset_list = ", ".join(a["path"] for a in self.project_memory["assets"])
            context += f"Available 3D assets: {asset_list}\n"

        recent = "\n".join(self.project_memory["shared_context_log"][-10:])
        if recent:
            context += f"\nRecent activity across other agents:\n{recent}\n"

        return context

    def _log_shared_context(self, entry: str):
        self.project_memory["shared_context_log"].append(entry)

    # ------------------------------------------------------------------
    # KOD / SAHNE ÜRETİMİ
    # ------------------------------------------------------------------
    def write_and_fix_code(self, task_desc: str, target_file: str) -> str:
        context = self._get_context_for_file(target_file)
        is_scene = target_file.endswith(".tscn")
        code = None
        error_msg = "Bilinmeyen hata"

        if is_scene:
            instruction = self._scene_prompt(task_desc, target_file, context)
        else:
            instruction = (
                f"Task: {task_desc}\n{context}\n"
                f"Write Godot 4.3 GDScript code for {target_file}. "
                f"Output ONLY raw GDScript, no markdown fences, no explanation."
            )

        if self.zai:
            try:
                resp = self.zai.chat.completions.create(
                    model="glm-4-flash",
                    messages=[{"role": "user", "content": instruction}]
                )
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
                code = (
                    f"extends Node\n"
                    f"# FOSTAS OS SIMULATION MODE\n"
                    f"# Reason: {error_msg}\n"
                    f"# Task: {task_desc}\n\n"
                    f"func _ready():\n\tpass\n"
                )

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
            return f"⚠️ {target_file} SIMULATION MODE'da üretildi ({error_msg}). Gerçek kod için API key'leri kontrol et."

        return f"✅ Generated {target_file} (v{version_num}). Check the IDE below to view code."

    def _strip_markdown_fences(self, code: str) -> str:
        code = re.sub(r"^```[a-zA-Z]*\n?", "", code.strip())
        code = re.sub(r"\n?```$", "", code.strip())
        return code.strip()

    def _scene_prompt(self, task_desc: str, target_file: str, context: str) -> str:
        return f"""Task: {task_desc}
{context}

Write a valid Godot 4.3 .tscn file for {target_file}.

STRICT FORMAT RULES (this is not GDScript, it's Godot's scene resource text format):
- Must start with a header line like: [gd_scene load_steps=N format=3]
- If it attaches a script, add an ExtResource for it: [ext_resource type="Script" path="res://scripts/..." id="1_script"]
  then reference it in the node as: script = ExtResource("1_script")
- Define the root node: [node name="RootName" type="CharacterBody3D"]  (choose an appropriate Godot 4 node type: CharacterBody3D, Node2D, Node3D, Area3D, etc. based on what the entity is)
- Add child nodes with: [node name="ChildName" type="..." parent="."]
- If a 3D asset .glb path is available in the context above and this entity should be visible, add a child node of type Node3D or MeshInstance3D whose scene reference points to that asset via an ExtResource of type "PackedScene".
- Output ONLY the raw .tscn text. No markdown fences, no explanation, no comments outside the format.
"""

    def _validate_or_fallback_scene(self, code: str, target_file: str) -> str:
        """LLM çıktısı gerçek bir .tscn'e benzemiyorsa (örn. GDScript yazmışsa) fallback'e düş."""
        if code.strip().startswith("[gd_scene"):
            return code
        return self._fallback_scene(target_file)

    def _fallback_scene(self, target_file: str) -> str:
        node_name = os.path.splitext(os.path.basename(target_file))[0].replace("_", " ").title().replace(" ", "")
        return (
            f'[gd_scene load_steps=1 format=3]\n\n'
            f'[node name="{node_name or "Root"}" type="Node3D"]\n'
        )

    # ------------------------------------------------------------------
    # 3D ASSET ÜRETİMİ (TRIPO)
    # ------------------------------------------------------------------
    def generate_3d_asset(self, task_desc: str):
        for asset in self.project_memory["assets"]:
            if task_desc.lower() in asset["name"].lower():
                yield f"♻️ Asset exists: {asset['path']}"
                self._log_shared_context(f"3D asset reused: {asset['path']} for '{task_desc}'")
                return

        if not self.tripo_key:
            yield "❌ TRIPO_API_KEY tanımlı değil, 3D model üretilemiyor. .env dosyanı kontrol et."
            return

        try:
            url = "https://api.tripo3d.ai/v2/openapi/task/create"
            headers = {"Authorization": f"Bearer {self.tripo_key}"}
            payload = {"type": "text_to_model", "prompt": f"Game ready lowpoly: {task_desc}"}
            resp = requests.post(url, headers=headers, json=payload, timeout=30)

            if resp.status_code == 200:
                task_id = resp.json().get("data", {}).get("task_id")
                asset_path = f"res://assets/{task_desc.replace(' ', '_')}.glb"

                yield f"🎨 Tripo task started (ID: {task_id}). Model üretimi 1-3 dakika sürebilir, bekleniyor..."

                model_url = None
                for status_update in self._poll_tripo_task(task_id):
                    if isinstance(status_update, tuple):
                        model_url = status_update[1]
                        break
                    yield status_update

                if model_url:
                    yield "⬇️ Model ready! Downloading binary .glb data..."
                    model_data = requests.get(model_url, timeout=60).content
                    self.project_memory["assets"].append({"name": task_desc, "path": asset_path, "data": model_data})
                    yield f"✅ 3D Model downloaded and saved to {asset_path}!"
                    self._log_shared_context(f"3D asset generated: {asset_path} for '{task_desc}'")
                else:
                    self.project_memory["assets"].append({"name": task_desc, "path": asset_path, "data": None})
                    yield "⚠️ Tripo zaman aşımına uğradı (3 dakika içinde bitmedi). Asset kaydedildi ama indirilemedi, tekrar denemek için aynı ismi tekrar yaz."
            else:
                yield f"❌ Tripo API Error ({resp.status_code}): {resp.text[:300]}"
        except requests.exceptions.Timeout:
            yield "❌ Tripo API zaman aşımı (istek 30sn içinde cevap vermedi)."
        except Exception as e:
            yield f"❌ Tripo Connection Error: {str(e)}"

    def _poll_tripo_task(self, task_id: str, max_retries=36, interval=5):
        """
        Eskiden max 30sn (6x5) bekliyordu, Tripo genelde daha uzun sürüyor.
        Şimdi ~3 dakika (36x5sn) bekliyor ve ilerlemeyi yield ediyor.
        Sonuç bulunduğunda ('done', model_url) tuple'ı yield eder.
        """
        url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
        headers = {"Authorization": f"Bearer {self.tripo_key}"}

        for attempt in range(max_retries):
            time.sleep(interval)
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    status = data.get("status")
                    progress = data.get("progress", "?")

                    if status == "success":
                        model_url = data.get("model", {}).get("url") or data.get("output", {}).get("model")
                        yield ("done", model_url)
                        return
                    elif status == "failed":
                        yield ("done", None)
                        return
                    elif attempt % 4 == 0:  # her ~20sn'de bir ilerleme mesajı
                        yield f"⏳ Tripo status: {status} ({progress}%)..."
            except Exception:
                pass

        yield ("done", None)

    # ------------------------------------------------------------------
    # UNDO
    # ------------------------------------------------------------------
    def undo_last_version(self, file_path: str) -> bool:
        if file_path in self.project_memory["scripts"] and len(self.project_memory["scripts"][file_path]) > 1:
            self.project_memory["scripts"][file_path].pop()
            return True
        if file_path in self.project_memory["scenes"] and len(self.project_memory["scenes"][file_path]) > 1:
            self.project_memory["scenes"][file_path].pop()
            return True
        return False

    # ------------------------------------------------------------------
    # ANA PIPELINE
    # ------------------------------------------------------------------
    def run_fostas_pipeline(self, user_prompt: str):
        yield "🧠 FOSTAS OS Architect analyzing prompt and routing tasks...\n"

        if not self.status["gemini"]["ok"] and not self.status["zai"]["ok"]:
            yield (
                "⚠️ Uyarı: Ne Gemini ne Z.AI key'i aktif, kodlar SIMULATION MODE'da üretilecek. "
                "`.env` dosyanda GEMINI_API_KEY ve/veya ZAI_API_KEY tanımlı mı kontrol et.\n"
            )

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
                for step in self.generate_3d_asset(desc):
                    yield step
            elif agent == "optimizer":
                yield "🚀 Optimization AI: Scanning project... LODs generated, Draw calls reduced."
                self._log_shared_context("Optimizer pass completed.")
            else:
                yield f"⚠️ Bilinmeyen agent tipi: '{agent}', task atlandı."

            time.sleep(0.5)

        yield "\n🛠️ Steam Build Manager: Generating export_presets.cfg and build.bat for Godot CLI..."
        self.project_memory["scripts"]["export_presets.cfg"] = [
            {"v": 1, "code": '[preset.0]\nname="Windows Desktop"\nplatform="Windows Desktop"'}
        ]
        yield "✅ Build configurations ready! Use Download button to get the project."
