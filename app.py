import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASMedo

st.set_page_config(page_title="FOSTAS Medo", page_icon="🌐", layout="wide")

st.title("🌐 FOSTAS - Medo Tarzı Site/App")
st.subheader("Web Sitesi + Mobil Uygulama (5 Yapyzeka ile)")

# Input area
col1, col2 = st.columns([2, 1])

with col1:
    prompt = st.text_input(
        "Site/App için prompt yaz:",
        placeholder="Örn: Bana bir sağlık klinigi web sitesi ve uygulaması yap, Medo tarzı"
    )

with col2:
    st.subheader("⚡ Örnekler")

# Quick templates
col1, col2, col3, col4 = st.columns(4)

templates = {
    col1: ("🏥 Hastane", "Hastane web sitesi ve uygulaması"),
    col2: ("☕ Restoran", "Restoran web sitesi ve uygulaması"),
    col3: ("💇 Kuaför", "Kuaför web sitesi ve uygulaması"),
    col4: ("🏋️ Fitness", "Fitness web sitesi ve uygulaması"),
}

for col, (emoji, text) in templates.items():
    with col:
        if st.button(emoji, use_container_width=True, key=text):
            prompt = text

# Create button
if st.button("🚀 Medo Site/App Oluştur", use_container_width=True, type="primary", key="create_btn"):
    if prompt:
        with st.spinner("5 Yapyzeka çalışıyor... (Nemotron → DeepSeek → GLM-5.2 → GPT-OSS → Llama)"):
            medo = FOSTASMedo()
            success = medo.create(prompt)
        
        st.markdown("---")
        
        # Show logs
        st.subheader("📊 Üretim İşlemleri")
        for log in medo.logs:
            st.markdown(f"- {log}")
        
        st.markdown("---")
        
        if success:
            st.success("✅ Site/App Tamamlandı!")
            
            # Preview
            st.subheader("👀 Ön İzleme")
            st.info("📱 Mobil cihazda test et - hamburger menü görünecek!")
            
            components.html(medo.html, height=1000, scrolling=True)
            
            # Download
            st.markdown("---")
            st.download_button(
                label="⬇️ HTML İndir (Web + App)",
                data=medo.html.encode('utf-8'),
                file_name="medo_site.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.error("❌ Hata oluştu")
    else:
        st.error("❌ Prompt yaz!")

# Info
st.markdown("---")
st.subheader("ℹ️ FOSTAS Medo Sistemi")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **🧠 5 Yapyzeka:**
    - Nemotron (Plan)
    - DeepSeek (Spec)
    - GLM-5.2 (Kod)
    - GPT-OSS (QA)
    - Llama (Backup)
    """)

with col2:
    st.markdown("""
    **🎨 Özellikler:**
    - Responsive design
    - Mobile menü
    - Modern CSS
    - JavaScript toggle
    - Fotoğraflar
    """)

with col3:
    st.markdown("""
    **📦 Tek Dosya:**
    - HTML
    - CSS
    - JavaScript
    - Tüm sayfalar
    - SPA (Single Page)
    """)
