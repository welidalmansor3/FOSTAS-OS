import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASWeb

st.set_page_config(page_title="FOSTAS", page_icon="🌐", layout="wide")

st.title("🌐 FOSTAS - Web Sitesi Yap")

# Buttons
col1, col2, col3 = st.columns(3)

prompt_override = None

with col1:
    if st.button("☕ Kafe Sitesi", use_container_width=True, key="btn_kafe"):
        prompt_override = "Profesyonel kafe web sitesi"

with col2:
    if st.button("🏛️ Müze Sitesi", use_container_width=True, key="btn_muze"):
        prompt_override = "Müze web sitesi"

with col3:
    if st.button("💼 İşletme Sitesi", use_container_width=True, key="btn_isletme"):
        prompt_override = "İşletme web sitesi"

# Input
prompt = st.text_input("Web sitesi için prompt yaz:", placeholder="Örn: Bana bir kafe web sitesi yap", value=prompt_override or "")

if prompt_override:
    prompt = prompt_override

# Create button
if st.button("🚀 Oluştur", use_container_width=True, type="primary"):
    if prompt:
        with st.spinner("Web sitesi oluşturuluyor..."):
            fostas = FOSTASWeb()
            
            if fostas.ok:
                success = fostas.create(prompt)
                
                if success:
                    st.success("✅ Tamamlandı!")
                    
                    # Preview
                    st.subheader("👀 Web Sitesi")
                    components.html(fostas.html, height=900, scrolling=True)
                    
                    # Download
                    st.download_button(
                        label="⬇️ HTML İndir",
                        data=fostas.html.encode('utf-8'),
                        file_name="website.html",
                        mime="text/html",
                        use_container_width=True
                    )
                else:
                    st.error("Hata oluştu")
            else:
                st.error("❌ API Key yok!")
    else:
        st.error("Prompt yaz!")
