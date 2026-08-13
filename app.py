import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASCore

# Config
st.set_page_config(page_title="FOSTAS", page_icon="🌐", layout="wide")

# Theme
st.markdown("""
<style>
    body { background-color: #050505; color: #ffffff; }
    .stApp { background-color: #050505; }
    h1 { color: #667eea; text-align: center; }
    h2 { color: #667eea; }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🌐 FOSTAS - Web Uygulaması Yap")

# Main area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Prompt Yaz")
    
    prompt = st.text_area(
        "Uygulamayı tarif et:",
        placeholder="Örn: Bana bir kafe web sitesi yap",
        height=100
    )
    
    if st.button("🚀 Oluştur", use_container_width=True):
        if prompt:
            st.session_state.generating = True
        else:
            st.error("Lütfen bir prompt yaz!")

with col2:
    st.subheader("📚 Örnekler")
    
    if st.button("☕ Kafe", use_container_width=True):
        st.session_state.prompt_template = "Bana profesyonel bir kafe web sitesi yap"
    
    if st.button("🏛️ Müze", use_container_width=True):
        st.session_state.prompt_template = "Bana bir müze web sitesi yap"
    
    if st.button("💼 Portföy", use_container_width=True):
        st.session_state.prompt_template = "Bana bir portföy web sitesi yap"
    
    if st.button("🏨 Otel", use_container_width=True):
        st.session_state.prompt_template = "Bana bir otel web sitesi yap"
    
    if st.button("📚 Blog", use_container_width=True):
        st.session_state.prompt_template = "Bana bir blog web sitesi yap"

# Use template if selected
if 'prompt_template' in st.session_state:
    prompt = st.session_state.prompt_template
    st.session_state.generating = True
    st.session_state.prompt_template = None

# Initialize FOSTAS
if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()

fostas = st.session_state.fostas

# Generate
if st.session_state.get('generating', False):
    if prompt:
        st.markdown("---")
        
        with st.spinner("🚀 FOSTAS çalışıyor..."):
            progress_bar = st.progress(0)
            status = st.empty()
            
            # Get logs
            def update_progress():
                logs = fostas.generation_log
                for i, log in enumerate(logs):
                    progress = (i + 1) / len(logs) if logs else 0
                    progress_bar.progress(progress)
                    status.write(f"📌 {log['action']}")
            
            # Generate
            success = fostas.generate_app(prompt)
            update_progress()
        
        st.session_state.generating = False
        
        if success:
            st.success("✅ Tamamlandı!")
            
            # Preview
            st.markdown("---")
            st.subheader("👀 Uygulamayı Gör")
            
            components.html(fostas.raw_html, height=700, scrolling=True)
            
            # Download
            st.download_button(
                label="⬇️ HTML İndir",
                data=fostas.raw_html.encode('utf-8'),
                file_name="app.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.error("❌ Hata oluştu!")

# Status
st.markdown("---")
st.subheader("⚙️ Durum")

status_col1, status_col2 = st.columns(2)

with status_col1:
    glm_status = fostas.status.get("glm", {"ok": False})
    if glm_status["ok"]:
        st.success("✅ GLM-5.2 Bağlı")
    else:
        st.error("❌ GLM-5.2 Eksik")

with status_col2:
    st.info("📸 Fotoğraf: Picsum Photos (Ücretsiz)")
