import os
import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS OS - AI Game Maker", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #050505; color: #ffffff; }
    .stChatInput, .stChatInputContainer, [data-testid="stChatInput"] { background-color: #050505 !important; }
    .stChatInput textarea { background-color: #111 !important; color: #fff !important; border: 1px solid #333 !important; }
    h1, h2, h3 { color: #ff4b4b; }
    .stButton button { background-color: #ff4b4b; color: white; border: none; border-radius: 8px; font-weight: bold; }
    .stButton button:hover { background-color: #cc3333; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { background-color: #111; border-radius: 8px 8px 0px 0px; padding: 10px 20px; color: #fff; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Kanka hoş geldin! Aklındaki oyunu bana yaz, anında kodlayıp 'Oyna' sekmesine atayım. Örn: 'Uzayda meteorlardan kaçan bir uzay gemisi oyunu yap'"}]

fostas = st.session_state.fostas

st.title("🎮 FOSTAS OS - AI Game Maker")
st.subheader("Prompt Yaz, Anında Oyna!")

# SEKME SİSTEMİ
tab1, tab2 = st.tabs(["🛠️ Oyun Üret (Prompt)", "🕹️ Oyunu Dene (Play)"])

with tab1:
    st.header("💬 Oyun Fikrini Yaz")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ne oyunu yapalım? (Örn: Top sektirme, yılan, uzay savaşı...)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("🧠 NVIDIA GLM-5.2 & DeepSeek devreye giriyor, oyun kodları yazılıyor... ⏳")
            
            # Oyunu üret
            success = fostas.generate_game(prompt)
            
            if success:
                response_placeholder.markdown("✅ Oyun hazır! Üstteki **'🕹️ Oyunu Dene (Play)'** sekmesine geçip hemen oynayabilirsin!")
                st.session_state.messages.append({"role": "assistant", "content": "✅ Oyun hazır! 'Oyunu Dene' sekmesine geç."})
            else:
                response_placeholder.markdown("⚠️ Oyun üretilirken bir sorun oluştu. Lütfen farklı bir prompt dene.")
                st.session_state.messages.append({"role": "assistant", "content": "⚠️ Hata oluştu."})
            
            st.rerun()

with tab2:
    st.header("🕹️ Oyun Alanı")
    st.write("Ürettiğin oyun aşağıda yüklenecek. Bekleyin yükleniyorsa biraz zaman alabilir...")
    
    if fostas.game_html:
        # Oyunu güvenli bir iframe içinde oynat
        components.html(fostas.game_html, height=650, scrolling=False)
    else:
        st.warning("Henüz bir oyun üretilmedi. Lütfen 'Oyun Üret' sekmesine git ve bir oyun fikri yaz!")
