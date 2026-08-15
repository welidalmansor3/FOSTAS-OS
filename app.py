import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import WebBuilder

st.set_page_config(page_title="FOSTAS", page_icon="🌐", layout="wide")

st.title("🌐 FOSTAS - Web Sitesi")

prompt = st.text_input("Prompt:", placeholder="Bana bir web sitesi yap")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("☕", use_container_width=True):
        prompt = "Kafe web sitesi"
with c2:
    if st.button("🏛️", use_container_width=True):
        prompt = "Müze web sitesi"
with c3:
    if st.button("💼", use_container_width=True):
        prompt = "İşletme web sitesi"

if st.button("🚀 Yap", use_container_width=True):
    if prompt:
        with st.spinner("Yapılıyor..."):
            wb = WebBuilder()
            wb.build(prompt)
        
        st.subheader("Web Sitesi")
        components.html(wb.html, height=800, scrolling=True)
        
        st.download_button("⬇️ İndir", wb.html.encode('utf-8'), "site.html", "text/html", use_container_width=True)
    else:
        st.error("Prompt yaz!")
