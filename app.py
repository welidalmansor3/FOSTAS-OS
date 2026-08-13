import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
import docx
import json

from fostas_brain import FOSTASCore

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="FOSTAS - Web & Mobile Apps",
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
        "content": "👋 Hoş geldin! FOSTAS v8'e.\n\n🌐 **Bağlı Yapyzekalar:**\n1. Nemotron (Plan)\n2. DeepSeek (Araştırma)\n3. Image Search Agent (Fotoğraf linki)\n4. GLM-5.2 (Kod)\n5. GPT-OSS (QA)\n6. Llama (Fallback)\n\n✨ **Prompt yaz:**\n'Bana müze web sitesi yap' → Otomatik fotoğraf linki ara + HTML üret!"
    }]

if 'generating' not in st.session_state:
    st.session_state.generating = False

fostas = st.session_state.fostas

# ============ SIDEBAR ============
with st.sidebar:
    st.header("⚙️ FOSTAS Engine")
    
    st.subheader("🤖 Yapyzekalar")
    models = {
        "🧠 Nemotron": "nemotron",
        "📚 DeepSeek": "deepseek",
        "💻 GLM-5.2": "glm",
        "🔍 GPT-OSS": "gpt_oss",
        "🦙 Llama": "llama",
    }
    
    for name, key in models.items():
        info = fostas.status.get(key, {"ok": False})
        status = "✅" if info["ok"] else "❌"
        st.write(f"{status} {name}")
    
    st.markdown("---")
    st.write("📸 **Fotoğraf Kaynağı:** DuckDuckGo, Google, Pexels")
    st.caption("Otomatik linki ara (indirme değil)")

# ============ MAIN ============
st.title("🌐 FOSTAS v8 - Connected AI Apps")
st.subheader("Yapyzekalar Birbirine Bağlı, Otomatik Fotoğraf Linki")

tab1, tab2, tab3 = st.tabs(["🛠️ Uygulama Yap", "👀 Önizle", "📊 Detaylar"])

# ===== TAB 1: CREATE =====
with tab1:
    st.header("💭 Uygulamayı Tarif Et")
    
    st.subheader("🚀 Örnekler")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏛️ Müze Rehberi", use_container_width=True):
            st.session_state.template = "Bana Irak müzeleri rehberi web sitesi yap, her müzeye açılış saatleri ve fotoğraflar ekle"
        if st.button("☕ Kafe Menüsü", use_container_width=True):
            st.session_state.template = "Bana bir kafe için menü uygulaması yap, içecekler ve yemekler fotoğraflar ile göster"
    
    with col2:
        if st.button("💼 Portföy", use_container_width=True):
            st.session_state.template = "Bana profesyonel portföy web sitesi yap, proje örnekleri fotoğraflar ile ekle"
        if st.button("🏨 Otel", use_container_width=True):
            st.session_state.template = "Bana bir otel web sitesi yap, odaları fotoğraflar ile göster"
    
    with col3:
        if st.button("🛍️ Mağaza", use_container_width=True):
            st.session_state.template = "Bana bir ürün satış web sitesi yap, ürünleri fotoğraflar ile ekle"
        if st.button("📚 Blog", use_container_width=True):
            st.session_state.template = "Bana kişisel blog web sitesi yap, makaleler başlıkları ve kapak fotoğrafları ile"
    
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
        prompt = st.chat_input("Uygulamayı tarif et... (Örn: Bana bir fotoğraf galerisi web sitesi yap)")
    
    if prompt and not st.session_state.generating:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        st.session_state.generating = True
        
        with st.chat_message("assistant"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("### 🚀 FOSTAS Fabrikası Çalışıyor...\n")
            
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
                
                log_text = f"{log['agent']} → {log['action']}"
                with log_area.container():
                    for l in logs[:i+1]:
                        st.markdown(f"- {l['agent']}: {l['action']}")
            
            progress_container.empty()
            
            if success:
                st.success("✅ Uygulama Tamamlandı!")
                st.info("👉 '👀 Önizle' sekmesine geç!")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "✅ Tamamlandı! Fotoğraflar otomatik internetten linkler alınarak eklendi. '👀 Önizle' sekmesinde görebilirsin."
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
        st.info("Henüz uygulama yok. Sol taraftan bir prompt yaz!")

# ===== TAB 3: DETAILS =====
with tab3:
    st.header("📊 Üretim Detayları")
    
    if fostas.generation_log:
        st.subheader("📝 İşlem Logları")
        
        for log in fostas.generation_log:
            st.markdown(f"**{log['agent']}**  \n{log['action']}")
        
        st.markdown("---")
        
        st.subheader("💾 Shared Memory")
        
        memory = fostas.get_memory()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Kullanıcı Prompt:**")
            st.write(memory.get("user_prompt", "")[:100])
            
            st.markdown("**Arama Terimleri:**")
            for term in memory.get("search_queries", [])[:5]:
                st.write(f"- {term}")
        
        with col2:
            st.markdown("**Bulunan Fotoğraf Linkleri:**")
            image_links = memory.get("image_links", [])
            st.write(f"Toplam: {len(image_links)} fotoğraf")
            
            for img in image_links[:3]:
                st.write(f"- {img['title']}")
    else:
        st.info("Henüz işlem yapılmadı")
