import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASCore

st.set_page_config(page_title="FOSTAS", page_icon="🌐", layout="wide")

st.title("🌐 FOSTAS - 5 Yapyzeka ile Web Sitesi")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📝 Prompt")
    prompt = st.text_area("Web sitesi için:", height=100, placeholder="Örn: Bana profesyonel kafe web sitesi yap")

with col2:
    st.subheader("⚡ Örnekler")
    
    btn1 = st.button("☕ Kafe", use_container_width=True, key="btn_kafe")
    btn2 = st.button("🏛️ Müze", use_container_width=True, key="btn_muze")
    btn3 = st.button("💼 İşletme", use_container_width=True, key="btn_isletme")
    btn4 = st.button("🏨 Otel", use_container_width=True, key="btn_otel")
    btn5 = st.button("📚 Blog", use_container_width=True, key="btn_blog")
    
    if btn1:
        prompt = "Profesyonel kafe web sitesi"
    elif btn2:
        prompt = "Müze web sitesi"
    elif btn3:
        prompt = "İşletme web sitesi"
    elif btn4:
        prompt = "Otel web sitesi"
    elif btn5:
        prompt = "Blog web sitesi"

if 'fostas' not in st.session_state:
    st.session_state.fostas = FOSTASCore()

fostas = st.session_state.fostas

if st.button("🚀 Oluştur", use_container_width=True, key="create"):
    if prompt:
        with st.spinner("5 Yapyzeka çalışıyor..."):
            success = fostas.generate_app(prompt)
        
        st.markdown("---")
        
        # Logs
        st.subheader("📊 İşlem")
        logs = fostas.get_logs()
        for log in logs:
            st.markdown(f"- {log['agent']}: {log['action']}")
        
        st.markdown("---")
        
        if success:
            st.success("✅ Tamamlandı!")
            
            st.subheader("👀 Web Sitesi")
            components.html(fostas.raw_html, height=800, scrolling=True)
            
            st.download_button(
                label="⬇️ İndir (HTML)",
                data=fostas.raw_html.encode('utf-8'),
                file_name="website.html",
                mime="text/html",
                use_container_width=True
            )
    else:
        st.error("❌ Prompt yaz!")

# Status
st.markdown("---")
st.subheader("🤖 Yapyzeka Durumu")

col1, col2, col3, col4, col5 = st.columns(5)

models = {
    "🧠 Nemotron": "nemotron",
    "📚 DeepSeek": "deepseek",
    "💻 GLM": "glm",
    "🔍 GPT-OSS": "gpt_oss",
    "🦙 Llama": "llama"
}

cols = [col1, col2, col3, col4, col5]

for (name, key), col in zip(models.items(), cols):
    with col:
        status = fostas.status.get(key, {"ok": False})
        if status["ok"]:
            st.success(f"{name} ✅")
        else:
            st.error(f"{name} ❌")
