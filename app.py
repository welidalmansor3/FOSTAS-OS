import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import MEDOSite

st.set_page_config(page_title="MEDO Kliniği", page_icon="🏥", layout="wide")

st.title("🏥 MEDO - Tıbbi Kliniği Web Sitesi")

if st.button("🚀 MEDO Sitesi Oluştur", use_container_width=True, type="primary"):
    with st.spinner("5 Yapyzeka çalışıyor... Nemotron → DeepSeek → GLM → GPT-OSS → Llama"):
        medo = MEDOSite()
        success = medo.create()
    
    if success:
        st.success("✅ MEDO Web Sitesi Tamamlandı!")
        
        st.subheader("👀 Sitesi Önizleme")
        components.html(medo.html, height=1200, scrolling=True)
        
        st.download_button(
            label="⬇️ MEDO Sitesini İndir (HTML)",
            data=medo.html.encode('utf-8'),
            file_name="MEDO_Kliniği.html",
            mime="text/html",
            use_container_width=True
        )
    else:
        st.error("Hata oluştu")

st.markdown("---")
st.info("🏥 MEDO profesyonel tıbbi kliniği web sitesi - 5 yapyzeka tarafından oluşturuldu!")
