import os
import io
import zipfile
import streamlit as st
import json
from pypdf import PdfReader
import docx

from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS OS - AI Game Studio", page_icon="🎮", layout="wide")

# CSS Dark Theme
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTextArea textarea, .stChatInput textarea { background-color: #1e1e1e; color: #d4d4d4; font-family: monospace; border: 1px solid #444; }
    h1, h2, h3 { color: #ff4b4b; }
    .stButton button { background-color: #2d2d2d; color: white; border: 1px solid #444; }
    .stDownloadButton button { background-color: #ff4b4b; color: white; border: none; }
    .stSelectbox > div > div { background-color: #1e1e1e; color: white; }
    iframe { border: 2px solid #333; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# Init Core
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None
if 'messages' not in st.session_state:
    # Karşılama mesajı
    st.session_state.messages = [{"role": "assistant", "content": "Merhaba Kanka! Ben FOSTAS OS. Oyununu tasarlamak için bana bir şeyler yaz. Örn: 'FPS player kodu yaz ve 3D tüfek modeli üret.'"}]

fostas = st.session_state.fostas

# --- Dosya Okuma Fonksiyonu ---
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

# --- SIDEBAR (Workspace) ---
with st.sidebar:
    st.header("📁 FOSTAS Workspace")
    
    # 3D İndirme Listesi
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
    
    # File Explorer
    st.subheader("📂 Project Files")
    all_files = list(fostas.project_memory["scripts"].keys()) + list(fostas.project_memory["scenes"].keys())
    
    if all_files:
        selected = st.selectbox("Open File", all_files)
        st.session_state.selected_file = selected
        
        if st.button("↩️ Undo Last Version"):
            if fostas.undo_last_version(selected):
                st.success("Reverted!")
                st.rerun()
                
        # Full Project ZIP
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

# --- ANA EKRAN (Chat ve Oyun Test Ekranı) ---
st.title("🎮 FOSTAS OS")
st.subheader("The AI Operating System for AAA Game Development")

# Ekrayı İkiye Böl: Sol Sohbet, Sağ Oyun Test
col_chat, col_game = st.columns([1.5, 1.0])

with col_chat:
    st.header("💬 AI Chat & Prompt")
    
    # Sohbet Geçmişini Göster
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Dosya Ekleme ve Hızlı 3D Model Üretme (Sohbet çubuğunun üstünde)
    with st.expander("📎 Dosya Ekle veya Hızlı 3D Model Üret"):
        uploaded_file = st.file_uploader("Geliştirme Dökümanı Yükle (PDF, DOCX, TXT, MD)", type=["pdf", "docx", "txt", "md"])
        if uploaded_file is not None:
            if st.button("📄 Dökümanı AI'a Okut"):
                text = read_uploaded_file(uploaded_file)
                fostas.upload_document(text)
                st.session_state.messages.append({"role": "assistant", "content": f"✅ {uploaded_file.name} başarıyla hafızama yüklendi! Artık bu dokümana göre kod yazabilirim."})
                st.rerun()
        
        st.markdown("---")
        quick_3d_prompt = st.text_input("Hızlı 3D Model Üret:")
        if st.button("🎨 Generate 3D"):
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
        # Kullanıcı mesajını ekrana bas
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI Cevabını Üret ve Ekrana Bas
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            for step_output in fostas.run_fostas_pipeline(prompt):
                full_response += step_output + "\n"
                response_placeholder.markdown(full_response + "▌")
                
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.rerun()

with col_game:
    st.header("🎮 Game Test Screen")
    st.caption("Oyun kodu tamamlanınca sol menüden ZIP indir, buradaki Godot editörüne sürükle ve anında oyna!")
    # Godot Web Editor Sağ Tarafta Açık Duruyor
    st.components.v1.iframe("https://editor.godotengine.org/releases/4.3.stable/godot.editor.html", height=650, scrolling=True)

# --- KOD EDITÖRÜ (Sayfanın En Altı) ---
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
