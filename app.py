import os
import io
import zipfile
import streamlit as st
import json

# Streamlit Cloud fallback (Eğer .env yoksa Streamlit Secrets'dan okur)
try:
    if "ZAI_API_KEY" not in os.environ:
        os.environ["ZAI_API_KEY"] = st.secrets["ZAI_API_KEY"]
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
        os.environ["TRIPO_API_KEY"] = st.secrets["TRIPO_API_KEY"]
except:
    pass

from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS OS - AI Game Studio", page_icon="🎮", layout="wide")

# CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTextArea textarea { background-color: #1a1a1a; color: #ffffff; border: 1px solid #444; }
    h1, h2, h3 { color: #ff4b4b; }
    .sidebar .sidebar-content { background-color: #171717; }
    .stDownloadButton button { background-color: #ff4b4b; color: white; border: none; }
    .stDownloadButton button:hover { background-color: #ff0000; color: white; }
</style>
""", unsafe_allow_html=True)

# Init Core
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()

# Sidebar
with st.sidebar:
    st.header("📁 FOSTAS Workspace")
    fostas = st.session_state.fostas
    
    st.subheader("📜 Scripts")
    if fostas.project_memory["scripts"]:
        for script_name in fostas.project_memory["scripts"].keys():
            st.code(script_name, language="python")
    else:
        st.write("Henüz script yok.")
        
    st.subheader("🌍 Scenes")
    if fostas.project_memory["scenes"]:
        for scene_name in fostas.project_memory["scenes"].keys():
            st.code(scene_name, language="xml")
    else:
        st.write("Henüz sahne yok.")
        
    st.subheader("🎨 Asset Registry")
    if fostas.project_memory["assets"]:
        for asset in fostas.project_memory["assets"]:
            st.write(f"✅ {asset['name']}")
    else:
        st.write("Henüz 3D model yok.")

    st.markdown("---")
    st.subheader("📦 Export Project")
    
    # ZIP İndirme Mantığı
    if fostas.project_memory["scripts"] or fostas.project_memory["scenes"]:
        # Hafızadaki dosyaları byte olarak ZIP'e yazma
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file_path, content in fostas.project_memory["scripts"].items():
                zip_file.writestr(file_path, content)
            for file_path, content in fostas.project_memory["scenes"].items():
                zip_file.writestr(file_path, content)
                
            # Godot project.godot dosyasını otomatik oluşturma
            godot_project = """config_version=5
[application]
config/name="FOSTAS OS Generated Project"
run/main_scene="res://scenes/main.tscn"
"""
            zip_file.writestr("project.godot", godot_project)

        zip_buffer.seek(0)
        
        st.download_button(
            label="⬇️ Download Godot Project (.zip)",
            data=zip_buffer,
            file_name="fostas_godot_project.zip",
            mime="application/zip",
            use_container_width=True
        )
    else:
        st.warning("Indirmek için önce kod üret!")

# Main Dashboard
st.title("🎮 FOSTAS OS")
st.subheader("The AI Operating System for AAA Game Development")
st.markdown("---")

st.header("🚀 Describe your game system")
user_prompt = st.text_area(
    "Prompt Input:", 
    height=150, 
    placeholder="Örn: Tarkov tarzı kanama ve kırık kemik sistemi içeren bir combat system oluştur. Ayrıca asker NPC için 3D model üret."
)

if st.button("⚡ Run FOSTAS Pipeline", type="primary", use_container_width=True):
    if user_prompt:
        output_container = st.empty()
        full_output = ""
        
        for step_output in fostas.run_fostas_pipeline(user_prompt):
            full_output += step_output + "\n"
            output_container.markdown(full_output)
            
        st.balloons()
        st.success("Pipeline Completed! Files are ready to download from the sidebar.")
    else:
        st.warning("Lütfen bir prompt gir.")

st.markdown("---")
st.header("📊 FOSTAS Agents Activity")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🧠 AI Agents Status")
    st.write("✅ **Z.AI (Coder):** Active (Bug Hunter Enabled)")
    st.write("✅ **Gemini (Planner):** Active (Prompt Analyzer Enabled)")
    st.write("✅ **Tripo (3D Artist):** Active (Asset Registry Enabled)")

with col2:
    st.subheader("🛠️ Project Knowledge Base (RAG)")
    st.json(fostas.project_memory["docs"])
