import os
import io
import zipfile
import streamlit as st
import json
from pypdf import PdfReader
import docx

from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS OS - AI Game Studio", page_icon="🎮", layout="wide")

# CSS Full Black Theme (Saf Siyah)
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
    
    /* Sohbet çubuğu ve arka planı tamamen siyah yapıyoruz */
    .stChatInput, .stChatInputContainer, [data-testid="stChatInput"] {
        background-color: #000000 !important;
    }
    .stChatInput textarea {
        background-color: #0a0a0a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }
    
    .stTextArea textarea { background-color: #0a0a0a; color: #ffffff; border: 1px solid #333333; }
    h1, h2, h3 { color: #ff4b4b; }
    .stButton button { background-color: #1a1a1a; color: white; border: 1px solid #444; border-radius: 8px; }
    .stButton button:hover { background-color: #2a2a2a; border-color: #ff4b4b; }
    .stDownloadButton button { background-color: #ff4b4b; color: white; border: none; border-radius: 8px; }
    .stSelectbox > div > div { background-color: #0a0a0a; color: white; border: 1px solid #333; }
    div.stExpander { background-color: #050505; border: 1px solid #222; border-radius: 8px; }
    
    /* Sohbet mesaj balonları */
    [data-testid="stChatMessage"] {
        background-color: #0a0a0a;
        border: 1px solid #222;
        border-radius: 12px;
        padding: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Init Core
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Merhaba Kanka! Ben FOSTAS OS. Aşağıdan bir şeyler yaz, dosya ekle veya 3D model üret. Örn: 'Mobil oyun için player kodu yaz.'"}]

fostas = st.session_state.fostas

# --- Dosya Okuma ---
def read_uploaded_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    elif uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return uploaded_file.read().decode("utf-8")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📁 FOSTAS Workspace")
    
    st.subheader("🎨 3D Asset Registry")
    if fostas.project_memory["assets"]:
        for asset in fostas.project_memory["assets"]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📦 {asset['name']}")
            with col2:
                if asset.get("data"):
                    st.download_button(
                        label="⬇️ .glb",
                        data=asset["data"],
                        file_name=f"{asset['name'].replace(' ', '_')}.glb",
                        mime="application/octet-stream"
                    )
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

# --- ANA EKRAN ---
st.title("🎮 FOSTAS OS")
st.subheader("The AI Operating System for AAA Game Development")

# Sohbet Ekranı
st.header("💬 AI Chat & Prompt")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sohbet Çubuğunun Hemen Üstündeki Araç Çubuğu (Z.AI / ChatGPT Tarzı)
with st.container():
    col_tool1, col_tool2 = st.columns([1, 1])
    
    with col_tool1:
        # Dosya Ekleme
        with st.expander("📎 Dosya Ekle", expanded=False):
            uploaded_file = st.file_uploader("Geliştirme Dökümanı Yükle", type=["pdf", "docx", "txt", "md"], label_visibility="collapsed")
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
        # Hızlı 3D Model Üretme
        with st.expander("🎨 Hızlı 3D Model Üret", expanded=False):
            quick_3d_prompt = st.text_input("Model adı:", label_visibility="collapsed")
            if st.button("🚀 Generate 3D", key="gen_3d"):
                if quick_3d_prompt:
                    st.session_state.messages.append({"role": "user", "content": f"Şu 3D modeli üret: {quick_3d_prompt}"})
                    with st.chat_message("user"):
                        st.markdown(f"Şu 3D modeli üret: {quick_3d_prompt}")
                    
                    with st.chat_message("assistant"):
                        response_placeholder = st.empty()
                        full_response = ""
                        for step in fostas.generate_3d_asset(quick_3d_prompt):
                            full_response += step + "\n"
                            response_placeholder.markdown(full_response + "▌")
                        response_placeholder.markdown(full_response)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.rerun()

# Sohbet Çubuğu (Prompt Input)
if prompt := st.chat_input("Ne yapmak istersin? (Örn: FPS player kodu yaz)"):
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

# --- KOD EDITÖRÜ ---
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
