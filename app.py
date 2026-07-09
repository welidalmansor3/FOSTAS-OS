import os
import io
import zipfile
import streamlit as st
from pypdf import PdfReader
import docx

from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS OS - AI Game Studio", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
    .stChatInput, .stChatInputContainer, [data-testid="stChatInput"] { background-color: #000000 !important; }
    .stChatInput textarea { background-color: #0a0a0a !important; color: #ffffff !important; border: 1px solid #333333 !important; }
    .stTextArea textarea { background-color: #0a0a0a; color: #ffffff; border: 1px solid #333333; }
    h1, h2, h3 { color: #ff4b4b; }
    .stButton button { background-color: #1a1a1a; color: white; border: 1px solid #444; border-radius: 8px; }
    .stButton button:hover { background-color: #2a2a2a; border-color: #ff4b4b; }
    .stDownloadButton button { background-color: #ff4b4b; color: white; border: none; border-radius: 8px; }
    .stSelectbox > div > div { background-color: #0a0a0a; color: white; border: 1px solid #333; }
    div.stExpander { background-color: #050505; border: 1px solid #222; border-radius: 8px; }
    [data-testid="stChatMessage"] { background-color: #0a0a0a; border: 1px solid #222; border-radius: 12px; padding: 15px; }
</style>
""", unsafe_allow_html=True)

if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Merhaba Kanka! Ben FOSTAS OS. Aşağıdan bir şeyler yaz, 3D model yükle veya döküman ekle. Örn: 'Yüklediğim car.glb modelini kullanarak bir player yap.'"}]

fostas = st.session_state.fostas

def read_uploaded_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in reader.pages])
    elif uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return uploaded_file.read().decode("utf-8")

# SIDEBAR
with st.sidebar:
    st.header("📁 FOSTAS Workspace")
    
    st.subheader("🔌 AI Engine Status")
    status = fostas.status
    for engine_name, key in [("Gemini", "gemini"), ("Z.AI", "zai")]:
        info = status[key]
        color = "#4caf50" if info["ok"] else "#ff4b4b"
        text = "bağlı" if info["ok"] else f"eksik"
        st.markdown(f"<span style='color:{color}'>●</span> {engine_name}: {text}", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader("📥 Upload Your 3D Models (.glb, .zip)")
    uploaded_3d = st.file_uploader("Kendi modellerini yükle", type=["glb", "gltf", "zip"], key="3d_uploader")
    if uploaded_3d is not None:
        if uploaded_3d.name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_3d) as z:
                for filename in z.namelist():
                    if filename.endswith((".glb", ".gltf")):
                        file_data = z.read(filename)
                        safe_name = os.path.basename(filename)
                        fostas.register_user_asset(safe_name, file_data)
                        st.success(f"Yüklendi: {safe_name}")
        else:
            fostas.register_user_asset(uploaded_3d.name, uploaded_3d.getvalue())
            st.success(f"Yüklendi: {uploaded_3d.name}")
        st.rerun()

    st.markdown("---")
    st.subheader("🎨 3D Asset Registry")
    if fostas.project_memory["assets"]:
        for asset in fostas.project_memory["assets"]:
            st.write(f"📦 {asset['name']}")
    else:
        st.write("Henüz 3D model yok.")

    st.markdown("---")
    st.subheader("📂 Project Files")
    all_files = list(fostas.project_memory["scripts"].keys()) + list(fostas.project_memory["scenes"].keys())
    if all_files:
        selected = st.selectbox("Open File", all_files)
        st.session_state.selected_file = selected
        if st.button("↩️ Undo Last Version"):
            if fostas.undo_last_version(selected):
                st.success("Reverted!")
                st.rerun()
        st.markdown("---")
        if st.button("📦 Download Full Project ZIP"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for path, versions in fostas.project_memory["scripts"].items():
                    zip_file.writestr(path, versions[-1]["code"])
                for path, versions in fostas.project_memory["scenes"].items():
                    zip_file.writestr(path, versions[-1]["code"])
                for asset in fostas.project_memory["assets"]:
                    if asset.get("data"):
                        clean_path = asset["path"].replace("res://", "")
                        zip_file.writestr(clean_path, asset["data"])
                zip_file.writestr("project.godot", 'config_version=5\n[application]\nconfig/name="FOSTAS OS Project"')
            zip_buffer.seek(0)
            st.download_button("⬇️ Download ZIP", data=zip_buffer, file_name="fostas_project.zip", mime="application/zip")

# ANA EKRAN
st.title("🎮 FOSTAS OS")
st.subheader("The AI Operating System for AAA Game Development")

st.header("💬 AI Chat & Prompt")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

with st.container():
    col_tool1, col_tool2 = st.columns([1, 1])
    with col_tool1:
        with st.expander("📎 Doküman Yükle (GDD)"):
            uploaded_file = st.file_uploader("PDF, DOCX, TXT, MD", type=["pdf", "docx", "txt", "md"], label_visibility="collapsed")
            if uploaded_file is not None:
                if st.button("📄 Dökümanı AI'a Okut ve Oyun Yap", key="read_doc"):
                    text = read_uploaded_file(uploaded_file)
                    fostas.upload_document(text)
                    st.session_state.messages.append({"role": "user", "content": "Yüklenen dosyaya göre prototype üret!"})
                    with st.chat_message("user"):
                        st.markdown("Yüklenen dosyaya göre prototype üret!")
                    with st.chat_message("assistant"):
                        response_placeholder = st.empty()
                        full_response = ""
                        for step in fostas.generate_from_doc():
                            full_response += step + "\n"
                            response_placeholder.markdown(full_response + "▌")
                        response_placeholder.markdown(full_response)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.rerun()

    with col_tool2:
        with st.expander("🤖 Hızlı AI Komutu"):
            if st.button("🚀 Tüm Modelleri Sahneye Bağla", key="wire_assets"):
                st.session_state.messages.append({"role": "user", "content": "Yüklediğim tüm 3D modelleri kullanarak bir test sahnesi oluştur."})
                with st.chat_message("user"):
                    st.markdown("Yüklediğim tüm 3D modelleri kullanarak bir test sahnesi oluştur.")
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    full_response = ""
                    for step in fostas.run_fostas_pipeline("Create a scene that imports and places all available 3D assets in the project memory."):
                        full_response += step + "\n"
                        response_placeholder.markdown(full_response + "▌")
                    response_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.rerun()

if prompt := st.chat_input("Ne yapmak istersin? (Örn: Yüklediğim car.glb ile player yap)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        for step_output in fostas.run_fostas_pipeline(prompt):
            full_response += step_output + "\n"
            response_placeholder.markdown(full_response + "▌")
        response_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.rerun()

st.markdown("---")
st.header("💻 Code Editor (IDE)")
if st.session_state.selected_file:
    selected = st.session_state.selected_file
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
    st.info("Sol menüden (Sidebar) bir dosya seçerek kodu düzenleyebilirsin.")
