import streamlit as st
import json
from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS OS - AI Game Studio", page_icon="🎮", layout="wide")

# CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTextArea textarea { background-color: #1a1a1a; color: #ffffff; border: 1px solid #444; }
    h1, h2, h3 { color: #ff4b4b; }
    .sidebar .sidebar-content { background-color: #171717; }
</style>
""", unsafe_allow_html=True)

# Init Core
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()
if 'history' not in st.session_state:
    st.session_state.history = []

# Sidebar - 9. Project Memory & 10. Asset Registry
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

# Main Dashboard
st.title("🎮 FOSTAS OS")
st.subheader("The AI Operating System for AAA Game Development")
st.markdown("---")

# 12. Prompt Analyzer
st.header("🚀 Describe your game system")
user_prompt = st.text_area(
    "Prompt Input:", 
    height=100, 
    placeholder="Örn: Tarkov tarzı kanama ve kırık kemik sistemi içeren bir combat system oluştur. Ayrıca asker NPC için 3D model üret."
)

if st.button("⚡ Run FOSTAS Pipeline", type="primary", use_container_width=True):
    if user_prompt:
        output_container = st.empty()
        full_output = ""
        
        # Run Agentic Pipeline
        for step_output in fostas.run_fostas_pipeline(user_prompt):
            full_output += step_output + "\n"
            output_container.markdown(full_output)
            
        st.balloons()
        st.success("Pipeline Completed! All modules updated.")
    else:
        st.warning("Lütfen bir prompt gir.")

# 13. Task Queue & History Visualization
st.markdown("---")
st.header("📊 FOSTAS Agents Activity")
col1, col2 = st.columns(2)

with col1:
    st.subheader("🧠 AI Agents Status")
    st.write("✅ **Z.AI (Coder):** Active (Bug Hunter Enabled)")
    st.write("✅ **Gemini (Planner):** Active (Prompt Analyzer Enabled)")
    st.write("✅ **Tripo (3D Artist):** Active (Asset Registry Enabled)")
    st.write("✅ **Optimizer AI:** Idle")
    st.write("✅ **Steam Manager:** Idle")

with col2:
    st.subheader("🛠️ Project Knowledge Base (RAG)")
    st.json(fostas.project_memory["docs"])
