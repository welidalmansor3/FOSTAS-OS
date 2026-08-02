import os
import io
import zipfile
import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
import docx

from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS OS - AI Game Studio", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #050505; color: #ffffff; }
    .stChatInput, .stChatInputContainer, [data-testid="stChatInput"] { background-color: #050505 !important; }
    .stChatInput textarea { background-color: #111 !important; color: #fff !important; border: 1px solid #333 !important; }
    .stTextArea textarea { background-color: #0a0a0a; color: #ffffff; border: 1px solid #333333; }
    h1, h2, h3 { color: #ff4b4b; }
    .stButton button { background-color: #ff4b4b; color: white; border: none; border-radius: 8px; font-weight: bold; }
    .stButton button:hover { background-color: #cc3333; }
    .stDownloadButton button { background-color: #1a1a1a; color: white; border: 1px solid #444; border-radius: 8px; }
    .stDownloadButton button:hover { background-color: #2a2a2a; border-color: #ff4b4b; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { background-color: #111; border-radius: 8px 8px 0px 0px; padding: 10px 20px; color: #fff; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# Session state başlatma
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Kanka hoş geldin! 3D modelini yükle, bir şablon seç veya kendi fikrini yaz. Oyunu anında 'Oyna' sekmesinde oynar ve bilgisayarına indirebilirsin!"}]

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
    
    st.subheader("🔌 NVIDIA AI Engine Status")
    status = fostas.status
    engine_map = {
        "GLM-5.2 (Kod)": "glm",
        "DeepSeek V4 (GDD)": "deepseek",
        "Llama 3.3 (Planlama)": "llama",
        "GPT-OSS (Mantık)": "gpt_oss"
    }
    for engine_name, key in engine_map.items():
        info = status[key]
        color = "#4caf50" if info["ok"] else "#ff4b4b"
        text = "bağlı" if info["ok"] else "eksik"
        st.markdown(f"<span style='color:{color}'>●</span> {engine_name}: {text}", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader("📥 3D Model Yükle (Max 200MB)")
    st.warning("ZIP, GLB veya GLTF yükleyebilirsin.")
    uploaded_3d = st.file_uploader("Model Yükle", type=["zip", "glb", "gltf"], key="3d_uploader")
    
    if uploaded_3d is not None:
        if uploaded_3d.name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_3d) as z:
                for filename in z.namelist():
                    if filename.endswith((".glb", ".gltf")):
                        file_data = z.read(filename)
                        safe_name = os.path.basename(filename)
                        fostas.register_user_asset(safe_name, file_data)
                        st.success(f"ZIP'ten çıkarıldı: {safe_name}")
        else:
            fostas.register_user_asset(uploaded_3d.name, uploaded_3d.getvalue())
            st.success(f"Yüklendi: {uploaded_3d.name}")
        st.rerun()

    st.markdown("---")
    
    st.subheader("🎨 Yüklü Dosyalar (İndir)")
    if fostas.project_memory["assets"]:
        for asset in fostas.project_memory["assets"]:
            st.write(f"📦 {asset['name']}")
            st.download_button(
                label=f"⬇️ {asset['name']} İndir",
                data=asset["data"],
                file_name=asset["name"],
                key=f"dl_asset_{asset['name']}"
            )
    else:
        st.write("Henüz 3D model yok.")

# ANA EKRAN
st.title("🎮 FOSTAS OS - AI Game Studio")
st.subheader("Irak'ın Oyun Endüstrisine Açılan Kapı 🇮🇶")

tab1, tab2 = st.tabs(["🛠️ Oyun Üret", "🕹️ Oyunu Dene ve İndir"])

with tab1:
    st.header("💬 Oyun Fikrini Yaz veya Yükle")
    
    # ŞABLLOLAR
    st.subheader("🚀 Hızlı Başlangıç Şablonları")
    templates = [
        "Serbest (Kendi Promptunu Yaz)",
        "2D Araba Yarışı Oyunu (Fizikli)",
        "Gerilim Korku Oyunu (Karanlık ortam, el feneri)",
        "Platform Oyunu (Mario gibi zıplamalı)",
        "Uzay Saldırısı (Meteorlara ateş et)",
        "3D Birinci Şahıs FPS Savaşı"
    ]
    selected_template = st.selectbox("Bir şablon seç veya kendi promptunu yaz:", templates)
    
    with st.expander("📎 Doküman Yükle (GDD / Fikir)"):
        uploaded_file = st.file_uploader("PDF, DOCX, TXT, MD", type=["pdf", "docx", "txt", "md"], label_visibility="collapsed")
        if uploaded_file is not None:
            if st.button("📄 Dökümanı AI'a Okut ve Oyun Yap", key="read_doc"):
                text = read_uploaded_file(uploaded_file)
                fostas.upload_document(text)
                st.session_state.messages.append({"role": "user", "content": "Yüklenen dosyaya göre oyun üret!"})
                with st.chat_message("user"):
                    st.markdown("Yüklenen dosyaya göre oyun üret!")
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    response_placeholder.markdown("🧠 Döküman okunuyor ve NVIDIA modelleriyle oyun yazılıyor... ⏳")
                    success = fostas.generate_game_from_doc()
                    if success:
                        response_placeholder.markdown("✅ Oyun hazır! **'🕹️ Oyunu Dene'** sekmesine geç!")
                    else:
                        response_placeholder.markdown("⚠️ Oyun üretilirken bir sorun oluştu.")
                st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Şablon seçildiyse buton göster, yoksa normal chat input
    if selected_template != "Serbest (Kendi Promptunu Yaz)":
        if st.button(f"🚀 '{selected_template}' Şablonunu AI'a Gönder", use_container_width=True):
            prompt = selected_template
        else:
            prompt = None
    else:
        prompt = st.chat_input("Ne oyunu yapalım? (Örn: Yüklediğim modelle bir korku oyunu yap)")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("🧠 NVIDIA GLM-5.2 devreye giriyor, oyun ve fizik kodları yazılıyor... ⏳")
            success = fostas.generate_game(prompt)
            if success:
                response_placeholder.markdown("✅ Oyun hazır! Üstteki **'🕹️ Oyunu Dene'** sekmesine geç!")
                st.session_state.messages.append({"role": "assistant", "content": "✅ Oyun hazır! 'Oyunu Dene' sekmesine geç."})
            else:
                response_placeholder.markdown("⚠️ Oyun üretilirken bir sorun oluştu. Lütfen farklı bir prompt dene.")
            st.rerun()

with tab2:
    st.header("🕹️ Oyun Alanı")
    
    if fostas.game_html:
        # iframe srcdoc ile gösterim (buton sorunu kesin çözüm)
        components.html(fostas.game_html, height=650, scrolling=False)
        
        # OYUNU İNDİRME BUTONU
        st.markdown("---")
        if fostas.raw_game_html:
            st.download_button(
                label="⬇️ Oyunu Bilgisayara İndir (HTML)",
                data=fostas.raw_game_html.encode('utf-8'),
                file_name="fostas_oyunum.html",
                mime="text/html"
            )
    else:
        st.warning("Henüz bir oyun üretilmedi. Lütfen 'Oyun Üret' sekmesine git ve bir oyun fikri yaz!")
