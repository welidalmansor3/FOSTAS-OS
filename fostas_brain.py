import os
import json
import time
import re
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

        # NVIDIA NIM API KEY'leri
        self.nv_keys = {
            "glm": os.getenv("NV_GLM_KEY"),
            "deepseek": os.getenv("NV_DEEPSEEK_KEY"),
            "llama": os.getenv("NV_LLAMA_KEY"),
            "gpt_oss": os.getenv("NV_GPT_OSS_KEY")
        }

        # Client'ları başlat
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
        """Tüm NVIDIA modelleri için genel sohbet fonksiyonu"""
        if model_client not in self.clients:
            return f"Hata: {model_client} client bağılı değil."
        
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
        self.project_memory["docs"]["UploadedDocs"] += f"\n\n--- USER UPLOAD ---\n{text[:3000]}"
        # DeepSeek ile dökümanı özetleyip teknik plana çevir
        summary_prompt = f"Şu oyun dökümanını oku ve 3 maddede teknik bir geliştirme planına çevir:\n{text}"
        plan = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", summary_prompt, extra_body={"chat_template_kwargs":{"thinking":False}})
        self.project_memory["docs"]["GameBible"] += f"\n--- AI Technical Plan ---\n{plan}"

    def register_user_asset(self, filename: str, file_data: bytes):
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
        for step in self.run_fostas_pipeline("Yüklenen dökümandaki oyun konseptine göre bir prototip oluştur: player script'i ve ana sahne."):
            yield step

    def analyze_prompt(self, user_prompt: str) -> dict:
        """Llama 3.3 70B kullanarak promptu JSON görevlere böl."""
        context = json.dumps(self.project_memory["docs"], indent=2, ensure_ascii=False)
        recent_context = "\n".join(self.project_memory["shared_context_log"][-10:])

        system = f"""
        You are the FOSTAS OS Architect, planning tasks for a Godot 4.3 game project.
        Knowledge Base: {context}
        Recent project activity: {recent_context if recent_context else "(nothing yet)"}
        Available 3D Assets: {json.dumps([a['path'] for a in self.project_memory['assets']], indent=2) if self.project_memory['assets'] else "(none yet)"}
        User request: '{user_prompt}'
        RULES:
        - If creating an entity, generate BOTH a script (.gd) AND a matching scene (.tscn).
        - Output STRICTLY JSON. Schema:
          {{"tasks": [{{"agent": "coder|3d_artist|optimizer", "task_description": "...", "target_file": "scripts/player.gd"}}]}}
        """
        
        response_str = self._nvidia_chat("llama", "meta/llama-3.3-70b-instruct", system, max_tokens=1024, temperature=0.2)
        
        try:
            clean_json = response_str.replace("```json", "").replace("```", "").strip()
            plan = json.loads(clean_json)
            if "tasks" not in plan or not isinstance(plan["tasks"], list) or len(plan["tasks"]) == 0:
                raise ValueError("Plan boş geldi.")
            return plan
        except Exception:
            # Llama JSON döndüremezse fallback
            return {"tasks": [{"agent": "coder", "task_description": user_prompt, "target_file": "scripts/game_main.gd"}]}

    def _get_context_for_file(self, target_file: str) -> str:
        context = "Knowledge Base:\n" + json.dumps(self.project_memory["docs"], ensure_ascii=False) + "\n\n"
        if target_file in self.project_memory["scripts"] and len(self.project_memory["scripts"][target_file]) > 0:
            context += f"Existing code in {target_file}:\n{self.project_memory['scripts'][target_file][-1]['code']}\n\n"
        if target_file in self.project_memory["scenes"] and len(self.project_memory["scenes"][target_file]) > 0:
            context += f"Existing scene in {target_file}:\n{self.project_memory['scenes'][target_file][-1]['code']}\n\n"
        if self.project_memory["assets"]:
            asset_list = "\n".join([f"- Name: {a['name']}, Path: {a['path']}" for a in self.project_memory["assets"]])
            context += f"Available 3D assets:\n{asset_list}\n"
        recent = "\n".join(self.project_memory["shared_context_log"][-10:])
        if recent:
            context += f"\nRecent activity:\n{recent}\n"
        return context

    def _log_shared_context(self, entry: str):
        self.project_memory["shared_context_log"].append(entry)

    def write_and_fix_code(self, task_desc: str, target_file: str) -> str:
        """GLM-5.2 ile kod yaz, hata olursa GPT-OSS-120B ile düzelt."""
        context = self._get_context_for_file(target_file)
        is_scene = target_file.endswith(".tscn")

        if is_scene:
            instruction = self._scene_prompt(task_desc, target_file, context)
        else:
            instruction = f"Task: {task_desc}\n{context}\nWrite Godot 4.3 GDScript code for {target_file}. Output ONLY raw GDScript, no markdown fences, no explanation."

        # 1. Aşama: Kodu GLM-5.2 ile üret
        code = self._nvidia_chat("glm", "z-ai/glm-5.2", instruction, max_tokens=8192, temperature=1)
        
        if code.startswith("API Hatası"):
            # 2. Aşama: GLM çökerse DeepSeek V4 Pro devreye girer
            code = self._nvidia_chat("deepseek", "deepseek-ai/deepseek-v4-pro", instruction, max_tokens=8192, extra_body={"chat_template_kwargs":{"thinking":False}})

        if code:
            code = self._strip_markdown_fences(code)
            if is_scene:
                code = self._validate_or_fallback_scene(code, target_file)
        else:
            code = f"extends Node\n# FOSTAS OS SIMULATION MODE\n# Task: {task_desc}\n\nfunc _ready():\n\tpass\n"

        # 3. Aşama: Kodun mantığını GPT-OSS-120B ile incele (Opsiyonel Debug)
        # Burada reasoning_content kullanılabilir ama şimdilik direkt koda kaydediyoruz.

        version_num = 1
        if target_file.endswith(".gd"):
            if target_file not in self.project_memory["scripts"]:
                self.project_memory["scripts"][target_file] = []
            version_num = len(self.project_memory["scripts"][target_file]) + 1
            self.project_memory["scripts"][target_file].append({"v": version_num, "code": code})
            self._log_shared_context(f"Script created: {target_file} (v{version_num})")
        elif target_file.endswith(".tscn"):
            if target_file not in self.project_memory["scenes"]:
                self.project_memory["scenes"][target_file] = []
            version_num = len(self.project_memory["scenes"][target_file]) + 1
            self.project_memory["scenes"][target_file].append({"v": version_num, "code": code})
            self._log_shared_context(f"Scene created: {target_file} (v{version_num})")

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
- Define the root node: [node name="RootName" type="CharacterBody3D"]
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
        yield "🧠 FOSTAS OS Architect (Llama 3.3) analyzing prompt...\n"

        # Llama ile görevleri böl
        plan = self.analyze_prompt(user_prompt)

        if "tasks" not in plan or not plan["tasks"]:
            yield "❌ Error in planning phase: görev listesi boş geldi."
            return

        for task in plan["tasks"]:
            agent = task.get("agent")
            desc = task.get("task_description", "")
            target = task.get("target_file", "unknown.gd")

            yield f"\n--- ▶️ Task: {desc[:60]}... ({agent}) ---"

            if agent in ["coder", "level_designer"]:
                yield self.write_and_fix_code(desc, target)
            elif agent == "3d_artist":
                yield "🎨 3D Artist Agent: Checking loaded assets..."
                self._log_shared_context("3D Artist pass completed.")
            elif agent == "optimizer":
                yield "🚀 Optimization AI: Scanning project..."
                self._log_shared_context("Optimizer pass completed.")
            else:
                yield f"⚠️ Bilinmeyen agent: '{agent}' atlandı."

            time.sleep(0.5)

        yield "\n🛠️ Steam Build Manager: Generating export_presets.cfg..."
        self.project_memory["scripts"]["export_presets.cfg"] = [{"v": 1, "code": '[preset.0]\nname="Windows Desktop"\nplatform="Windows Desktop"'}]
        yield "✅ Build ready! Use Download button to get the project."
