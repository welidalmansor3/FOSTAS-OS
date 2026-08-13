import streamlit as st
import streamlit.components.v1 as components

from fostas_brain import FOSTASCore

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="FOSTAS - GLM App Studio",
    page_icon="🌐",
    layout="wide"
)

# ============ DARK THEME ============
st.markdown("""
<style>
    :root {
        --primary: #667eea;
        --primary-dark: #764ba2;
        --bg-dark: #050505;
        --bg-card: #111111;
        --text-primary: #ffffff;
    }
    
    .stApp {
        background-color: var(--bg-dark);
        color: var(--text-primary);
    }
    
    .stChatInput textarea {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid #333 !important;
    }
    
    .stTextArea textarea {
        background-color: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid #333333;
    }
    
    h1, h2, h3 {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .stButton button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    
    .stButton button:hover {
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: var(--bg-card);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
    }
</style>
""", unsafe_allow_html=True)

# ============ SESSION STATE ============
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()

if 'messages' not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "👋 Hoş geldin! FOSTAS GLM Studio'ya.\n\n🌐 **Prompt yaz:**\n'Bana müze web sitesi yap' → GLM-5.2 otomatik:\n1. Fotoğraf linki ara\n2. HTML kod yaz\n3. Bitir!\n\n✨ Basit ama güçlü!"
    }]

if 'generating' not in st.session_state:
    st.session_state.generating = False

fostas = st.session_state.fostas

# ============ SIDEBAR ============
with st.sidebar:
    st.header("⚙️ FOSTAS Engine")
    
    st.subheader("🤖 Yapyzeka")
    status = fostas.status.get("glm", {"ok": False})
    status_text = "✅ Bağlı" if status["ok"] else "❌ Eksik"
    st.write(f"{status_text} GLM-5.2")
    
    st.markdown("---")
    st.write("📸 **Fotoğraf:** DuckDuckGo + Placeholder")
    st.caption("Otomatik linki ara")

# ============ MAIN ============
st.title("🌐 FOSTAS - GLM-5.2 App Studio")
st.subheader("Tek Yapyzeka, Güçlü Sonuçlar")

tab1, tab2 = st.tabs(["🛠️ Uygulama Yap", "👀 Önizle"])

# ===== TAB 1: CREATE =====
with tab1:
    st.header("💭 Uygulamayı Tarif Et")
    
    st.subheader("🚀 Örnekler")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏛️ Müze", use_container_width=True):
            st.session_state.template = "Bana Irak müzeleri rehberi web sitesi yap"
        if st.button("☕ Kafe", use_container_width=True):
            st.session_state.template = "Bana kafe menüsü web uygulaması yap"
    
    with col2:
        if st.button("💼 Portföy", use_container_width=True):
            st.session_state.template = "Bana profesyonel portföy web sitesi yap"
        if st.button("🏨 Otel", use_container_width=True):
            st.session_state.template = "Bana otel web sitesi yap"
    
    with col3:
        if st.button("🛍️ Mağaza", use_container_width=True):
            st.session_state.template = "Bana ürün satış web sitesi yap"
        if st.button("📚 Blog", use_container_width=True):
            st.session_state.template = "Bana blog web sitesi yap"
    
    st.markdown("---")
    
    # Chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Prompt
    prompt = None
    
    if 'template' in st.session_state:
        prompt = st.session_state.template
        st.session_state.template = None
    else:
        prompt = st.chat_input("Uygulamayı tarif et...")
    
    if prompt and not st.session_state.generating:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        st.session_state.generating = True
        
        with st.chat_message("assistant"):
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                log_area = st.empty()
            
            # Generate
            success = fostas.generate_app(prompt)
            
            # Show logs
            logs = fostas.get_logs()
            
            for i, log in enumerate(logs):
                progress = (i + 1) / len(logs) if logs else 0
                progress_bar.progress(progress)
                
                with log_area.container():
                    for l in logs[:i+1]:
                        st.markdown(f"- {l['action']}")
            
            progress_container.empty()
            
            if success:
                st.success("✅ Tamamlandı!")
                st.info("👉 '👀 Önizle' sekmesine geç!")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "✅ Uygulama tamamlandı! Fotoğraflar otomatik internetten linkler alınarak eklendi."
                })
            else:
                st.error("⚠️ Hata oluştu")
        
        st.session_state.generating = False
        st.rerun()

# ===== TAB 2: PREVIEW =====
with tab2:
    st.header("👀 Uygulamayı Gör")
    
    if fostas.raw_html:
        components.html(fostas.raw_html, height=700, scrolling=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="⬇️ HTML İndir",
                data=fostas.raw_html.encode('utf-8'),
                file_name="app.html",
                mime="text/html",
                use_container_width=True
            )
        
        with col2:
            if st.button("🔄 Yeniden Üret", use_container_width=True):
                fostas.raw_html = ""
                st.rerun()
    else:
        st.info("Henüz uygulama yok")
