import os
import io
import zipfile
import streamlit as st
import json

# FOSTAS Core'u çağırıyoruz (Anahtar işlerini o kendi içinde halleder)
from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS OS - AI Game Studio", page_icon="🎮", layout="wide")

# CSS Dark IDE Theme
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTextArea textarea { background-color: #1e1e1e; color: #d4d4d4; font-family: monospace; border: 1px solid #444; }
    h1, h2, h3 { color: #ff4b4b; }
    .stButton button { background-color: #2d2d2d; color: white; border: 1px solid #444; }
    .stDownloadButton button { background-color: #ff4b4b; color: white; border: none; }
    .stSelectbox > div > div { background-color: #1e1e1e; color: white; }
</style>
""", unsafe_allow_html=True)

# Init Core
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None

fostas = st.session_state.fostas

# Sidebar - File Explorer & Asset Registry
with st.sidebar:
    st.header("📁 FOSTAS Workspace")
    
    # File Explorer (Scripts & Scenes)
    all_files = list(fostas.project_memory["scripts"].keys()) + list(fostas.project_memory["scenes"].keys())
    
    if all_files:
        selected = st.selectbox("📂 Open File", all_files)
        st.session_state.selected_file = selected
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("↩️ Undo", use_container_width=True):
                if fostas.undo_last_version(selected):
                    st.success("Reverted to previous version!")
                    st.rerun()
                else:
                    st.warning("No previous version to undo.")
    else:
        st.write("Henüz dosya yok.")
        
    st.markdown("---")
    st.subheader("🎨 3D Asset Registry")
    if fostas.project_memory["assets"]:
        for asset in fostas.project_memory["assets"]:
            status = "✅ Downloaded" if asset.get("data") else "⏳ Pending"
            st.write(f"{status} - {asset['name']}")
    else:
        st.write("Henüz 3D model yok.")

    st.markdown("---")
    st.subheader("📦 Export Project")
    
    # ZIP İndirme Mantığı (Geliştirilmiş)
    if all_files or fostas.project_memory["assets"]:
        if st.button("⬇️ Prepare Godot Project ZIP", use_container_width=True):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                # Scriptleri ekle
                for path, versions in fostas.project_memory["scripts"].items():
                    latest_code = versions[-1]["code"]
                    zip_file.writestr(path, latest_code)
                
                # Sahneleri ekle
                for path, versions in fostas.project_memory["scenes"].items():
                    latest_code = versions[-1]["code"]
                    zip_file.writestr(path, latest_code)
                
                # 3D Modelleri binary olarak ekle
                for asset in fostas.project_memory["assets"]:
                    if asset.get("data"):
                        # path: "res://assets/fly.glb" -> "assets/fly.glb"
                        clean_path = asset["path"].replace("res://", "")
                        zip_file.writestr(clean_path, asset["data"])
                
                # Godot project.godot
                godot_project = """config_version=5
[application]
config/name="FOSTAS OS Project"
run/main_scene="res://scenes/main.tscn"
"""
                zip_file.writestr("project.godot", godot_project)
                
            zip_buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download .zip",
                data=zip_buffer,
                file_name="fostas_project.zip",
                mime="application/zip",
                use_container_width=True
            )

# Main Dashboard - IDE Area
st.title("🎮 FOSTAS OS")
st.subheader("The AI Operating System for AAA Game Development")
st.markdown("---")

# Prompt Input
st.header("🚀 Describe your game system")
user_prompt = st.text_area(
    "Prompt Input:", 
    height=100, 
    placeholder="Örn: Düşman için fly_ai.gd ve sahne dosyası oluştur. Ayrıca 3D sinek modeli üret."
)

if st.button("⚡ Run FOSTAS Pipeline", type="primary", use_container_width=True):
    if user_prompt:
        output_container = st.empty()
        full_output = ""
        
        for step_output in fostas.run_fostas_pipeline(user_prompt):
            full_output += step_output + "\n"
            output_container.markdown(full_output)
            
        st.balloons()
        st.success("Pipeline Completed! Check the Workspace sidebar to view files.")
    else:
        st.warning("Lütfen bir prompt gir.")

# Code Editor Area
st.markdown("---")
st.header("💻 Code Editor (IDE)")

if st.session_state.selected_file:
    selected = st.session_state.selected_file
    
    # Dosya türüne göre kodu getir
    if selected.endswith(".gd") and selected in fostas.project_memory["scripts"]:
        code_data = fostas.project_memory["scripts"][selected][-1]["code"]
    elif selected.endswith(".tscn") and selected in fostas.project_memory["scenes"]:
        code_data = fostas.project_memory["scenes"][selected][-1]["code"]
    else:
        code_data = "# File not found"

    edited_code = st.text_area(f"Editing: {selected}", value=code_data, height=400, key="code_editor")
    
    if st.button("💾 Save Changes to Memory"):
        if selected.endswith(".gd"):
            v_num = len(fostas.project_memory["scripts"][selected]) + 1
            fostas.project_memory["scripts"][selected].append({"v": v_num, "code": edited_code})
        elif selected.endswith(".tscn"):
            v_num = len(fostas.project_memory["scenes"][selected]) + 1
            fostas.project_memory["scenes"][selected].append({"v": v_num, "code": edited_code})
        st.success(f"Saved {selected} as version {v_num}!")
        st.rerun()
else:
    st.info("Select a file from the Workspace sidebar to view or edit code.")
