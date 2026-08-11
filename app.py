import os
import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
import docx

from fostas_brain import FOSTASCore

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="FOSTAS OS - AI App Studio",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ DARK THEME STYLING ============
st.markdown("""
<style>
    :root {
        --primary: #667eea;
        --primary-dark: #764ba2;
        --accent: #ff4b4b;
        --bg-dark: #050505;
        --bg-card: #111111;
        --text-primary: #ffffff;
        --text-secondary: #cccccc;
        --success: #4caf50;
        --warning: #ff9800;
    }
    
    .stApp {
        background-color: var(--bg-dark);
        color: var(--text-primary);
    }
    
    .stChatInput, .stChatInputContainer, [data-testid="stChatInput"] {
        background-color: var(--bg-dark) !important;
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
    
    h1, h2, h3, h4, h5, h6 {
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
        transition: all 0.3s;
    }
    
    .stButton button:hover {
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        transform: translateY(-2px);
    }
    
    .stDownloadButton button {
        background-color: var(--bg-card);
        color: white;
        border: 1px solid var(--primary);
        border-radius: 8px;
        transition: all 0.3s;
    }
    
    .stDownloadButton button:hover {
        background-color: var(--primary);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: var(--bg-card);
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        color: var(--text-secondary);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: white !important;
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    
    .status-ok {
        background-color: #4caf50;
        color: white;
    }
    
    .status-error {
        background-color: #ff4b4b;
        color: white;
    }
    
    .agent-log {
        background-color: var(--bg-card);
        border-left: 3px solid var(--primary);
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 14px;
    }
    
    .warning-box {
        background-color: #ff9800;
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
    
    .success-box {
        background-color: #4caf50;
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============ SESSION STATE INIT ============
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()

if 'messages' not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "👋 Kanka hoş geldin! FOSTAS Multi-Agent AI Studio'ya.\n\n🎮 **Oyun** yap: 'Bana 2D araba yarışı oyunu yap'\n🌐 **Web sitesi** yap: 'Bana Irak Müzeleri rehberi web uygulaması yap'\n📱 **App** yap: 'Bana restoran menüsü uygulaması yap'\n\nNe istersen söyle, anında yapayım!"
    }]

if 'generation_in_progress' not in st.session_state:
    st.session_state.generation_in_progress = False

fostas = st.session_state.fostas

# ============ FILE READERS ============
def read_uploaded_file(uploaded_file):
    """Read PDF, DOCX, or TXT files"""
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in reader.pages])
    elif uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return uploaded_file.read().decode("utf-8")

# ============ SIDEBAR ============
with st.sidebar:
    st.header("📁 FOSTAS Workspace")
    
    # Model Status
    st.subheader("🔌 AI Engine Status")
    status = fostas.status
    engine_map = {
        "🧠 Nemotron": "nemotron",
        "⚙️ DeepSeek": "deepseek",
        "💻 GLM-5.2": "glm",
        "🔍 GPT-OSS": "gpt_oss",
        "🦙 Llama 3.3": "llama",
    }
    
    for engine_name, key in engine_map.items():
        info = status.get(key, {"ok": False, "error": "Tanımlı değil"})
        color = "#4caf50" if info["ok"] else "#ff4b4b"
        text = "✅ Bağlı" if info["ok"] else "❌ Eksik"
        st.markdown(f"<span style='color:{color};font-weight:bold'>{text}</span> {engine_name}", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Asset Upload
    st.subheader("📥 Logo / Resim Yükle")
    st.caption("Uygulamada kullanmak için PNG/JPG yükle")
    uploaded_asset = st.file_uploader("Dosya Seç", type=["png", "jpg", "jpeg", "gif", "svg", "webp"], key="asset_uploader")
    
    if uploaded_asset is not None:
        fostas.register_user_asset(uploaded_asset.name, uploaded_asset.getvalue())
        st.success(f"✅ Yüklendi: {uploaded_asset.name}")
        st.rerun()
    
    st.markdown("---")
    
    # Asset Manager
    st.subheader("📦 Yüklü Dosyalar")
    if fostas.project_memory["assets"]:
        for asset in fostas.project_memory["assets"]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📄 {asset['name']}")
            with col2:
                st.download_button(
                    label="⬇️",
                    data=asset["data"],
                    file_name=asset["name"],
                    key=f"dl_{asset['name']}"
                )
    else:
        st.info("Henüz dosya yok")

# ============ MAIN CONTENT ============
st.title("📱 FOSTAS OS - Multi-Agent AI App Studio")
st.subheader("🇮🇶 Irak'ın Teknoloji Gücü | Oyun • Web • App")

tab1, tab2, tab3 = st.tabs(["🛠️ Uygulama Üret", "📲 Uygulamayı Dene", "ℹ️ Hakkında"])

# ============ TAB 1: APP GENERATION ============
with tab1:
    st.header("💭 Fikrinizi Söyleyin")
    
    # Quick templates
    st.subheader("🚀 Hızlı Başlangıç Şablonları")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎮 2D Oyun", use_container_width=True):
            st.session_state.quick_template = "2D Canvas oyunu (araba yarışı, yılan, vs.)"
        if st.button("🏛️ Müze Rehberi", use_container_width=True):
            st.session_state.quick_template = "Irak Müzeleri rehberi web sitesi"
        if st.button("💼 Portföy", use_container_width=True):
            st.session_state.quick_template = "Kişisel portföy / CV web sitesi"
    
    with col2:
        if st.button("🍕 Restoran Menüsü", use_container_width=True):
            st.session_state.quick_template = "Mobil uyumlu restoran menüsü uygulaması"
        if st.button("🛒 E-Ticaret", use_container_width=True):
            st.session_state.quick_template = "Basit alışveriş sepeti web uygulaması"
        if st.button("📱 Custom", use_container_width=True):
            st.session_state.quick_template = None
    
    with col3:
        if st.button("🎯 3D Oyun", use_container_width=True):
            st.session_state.quick_template = "Three.js ile basit 3D oyun"
        if st.button("📝 Blog", use_container_width=True):
            st.session_state.quick_template = "Kişisel blog web sitesi"
        if st.button("🎨 Landing Page", use_container_width=True):
            st.session_state.quick_template = "Modern landing page"
    
    st.markdown("---")
    
    # Document upload
    with st.expander("📎 Doküman Yükle", expanded=False):
        st.caption("PDF, DOCX, TXT veya Markdown dosyası yükleyebilirsin")
        uploaded_doc = st.file_uploader("Dosya Seç", type=["pdf", "docx", "txt", "md"], key="doc_uploader")
        
        if uploaded_doc is not None:
            if st.button("📄 Dökümanı AI'a Okut", key="read_doc"):
                with st.spinner("Doküman okunuyor..."):
                    text = read_uploaded_file(uploaded_doc)
                    fostas.upload_document(text)
                    st.success(f"✅ Doküman yüklendi ({len(text)} karakter)")
    
    st.markdown("---")
    
    # Chat interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Get prompt
    prompt = None
    
    if 'quick_template' in st.session_state and st.session_state.quick_template:
        prompt = st.session_state.quick_template
        st.session_state.quick_template = None
    else:
        prompt = st.chat_input("Ne uygulaması yapalım? (Örn: Bana yılan oyunu yap)")
    
    # Generate app
    if prompt and not st.session_state.generation_in_progress:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        st.session_state.generation_in_progress = True
        
        with st.chat_message("assistant"):
            # Progress area
            progress_placeholder = st.empty()
            log_placeholder = st.empty()
            
            with progress_placeholder.container():
                st.markdown("### 🚀 AI Fabrikası Çalışıyor...")
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            # Clear generation log
            fostas.generation_log = []
            
            # Call generation
            success = fostas.generate_app(prompt)
            
            # Update progress
            stages = [
                (0.2, "🧠 Nemotron: Architekt Planlıyor..."),
                (0.4, "⚙️ DeepSeek: Teknik Spesifikasyon Yazıyor..."),
                (0.6, "💻 GLM-5.2: Kod Yazıyor..."),
                (0.8, "🔍 GPT-OSS: Kalite Kontrolü Yapıyor..."),
                (1.0, "✅ Tamamlandı!")
            ]
            
            for progress_val, stage_text in stages:
                progress_bar.progress(progress_val)
                status_text.markdown(f"#### {stage_text}")
                import time
                time.sleep(0.3)
            
            # Clear progress area
            progress_placeholder.empty()
            
            if success:
                st.markdown("### ✅ Uygulama Hazır!")
                st.markdown("👉 **'📲 Uygulamayı Dene'** sekmesine geç ve uygulamayı test et!")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "✅ Uygulama hazır! 👉 'Uygulamayı Dene' sekmesine geç"
                })
            else:
                st.error("⚠️ Uygulama üretilirken bir sorun oluştu. Lütfen farklı bir prompt dene.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "⚠️ Bir hata oluştu. Lütfen tekrar dene."
                })
        
        st.session_state.generation_in_progress = False
        st.rerun()

# ============ TAB 2: APP PREVIEW ============
with tab2:
    st.header("📲 Uygulamayı Test Et")
    
    if fostas.raw_game_html:
        st.write("Aşağıdaki uygulamayı test edebilirsin:")
        
        # Preview
        components.html(fostas.raw_game_html, height=700, scrolling=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="⬇️ HTML Olarak İndir",
                data=fostas.raw_game_html.encode('utf-8'),
                file_name="fostas_uygulamam.html",
                mime="text/html",
                use_container_width=True
            )
        
        with col2:
            if st.button("🔄 Yeniden Üret", use_container_width=True):
                fostas.raw_game_html = ""
                st.rerun()
    else:
        st.warning("⚠️ Henüz bir uygulama üretilmedi.")
        st.info("👈 'Uygulama Üret' sekmesine git ve bir fikir yaz!")

# ============ TAB 3: ABOUT ============
with tab3:
    st.header("ℹ️ FOSTAS OS Hakkında")
    
    st.markdown("""
    ### 🚀 Multi-Agent AI System
    
    FOSTAS OS, **5 yapay zeka modelinin** birlikte çalışarak uygulamalar oluşturan devrimci bir sistemdir.
    
    **Ekip Üyeleri:**
    
    1. 🧠 **Nemotron** - Başmimar
       - Kullanıcı fikrini analiz eder
       - Uygulama mimarisini planlar
       - Reasoning ile derinlemesine düşünür
    
    2. ⚙️ **DeepSeek** - Mühendis
       - Teknik spesifikasyon hazırlar
       - HTML/CSS/JS yapısını tasarlar
       - Algoritmaları belirler
    
    3. 💻 **GLM-5.2** - Kodlama Ustası
       - Hızlı ve verimli kod yazar
       - Responsive tasarımlar oluşturur
       - Canvas oyunları yazabilir
    
    4. 🔍 **GPT-OSS** - Kalite Kontrol
       - Kodu gözden geçirir
       - Hataları düzeltir
       - Optimizasyonları yapar
    
    5. 🦙 **Llama 3.3** - Yedek Güç
       - Diğer modeller başarısız olursa devreye girer
       - Sistemi ayakta tutar
       - Fallback çözümleri sağlar
    
    ### 🎯 Yetenekler
    
    ✅ **Oyunlar** - 2D/3D Canvas oyunları, interaktif deneyimler
    ✅ **Web Siteleri** - Portföyler, bloglar, landing pages
    ✅ **Uygulamalar** - E-ticaret, müze rehberleri, restoran menüleri
    ✅ **Responsive** - Tüm cihazlarda mükemmel çalışır
    ✅ **VPN-Free** - Irak'ta çalışır (CDN sorunu yok)
    ✅ **Hızlı** - Dakikalar içinde tamamlanır
    
    ### 🇮🇶 Irak İçin Tasarlandı
    
    - VPN/CORS sorunlarına karşı güçlü
    - Türkçe ve Arapça desteği
    - Düşük bant genişliği için optimize
    - Lokal resimleri base64 olarak gömme
    
    ### 📱 Nasıl Kullanılır?
    
    1. Sol taraftan resim yükle (opsiyonel)
    2. Aşağıdaki şablonlardan birini seç VEYA kendi fikirni yaz
    3. AI fabrikası çalışmaya başlar
    4. Sonuç 20-30 saniye içinde hazır olur
    5. 'Uygulamayı Dene' sekmesinde test et
    6. HTML olarak indir ve kullan
    
    ---
    
    **Yapıcı:** FOSTAS Dev Team 🚀
    **Teknoloji:** NVIDIA AI Engines + Streamlit
    """)
