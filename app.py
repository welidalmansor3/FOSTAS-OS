import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASMedo

# Config
st.set_page_config(page_title="FOSTAS", page_icon="🌐", layout="wide")

# Title
st.title("🌐 FOSTAS - Web Sitesi Yap")

# Input
prompt = st.text_input("Prompt yaz:", placeholder="Örn: Bana bir kafe web sitesi yap")

# Create button
if st.button("🚀 Oluştur", use_container_width=True, type="primary"):
    if prompt:
        # Generate
        medo = FOSTASMedo()
        success = medo.create(prompt)
        
        # Show logs
        st.subheader("📊 İşlem")
        for log in medo.logs:
            st.write(log)
        
        st.markdown("---")
        
        # Preview
        if success:
            st.success("✅ Tamamlandı!")
            st.subheader("👀 Ön İzleme")
            components.html(medo.html, height=800, scrolling=True)
            
            # Download
            st.download_button(
                label="⬇️ İndir",
                data=medo.html.encode('utf-8'),
                file_name="site.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.error("Hata!")
    else:
        st.error("Prompt yaz!")
