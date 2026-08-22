import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASBrain

# Config
st.set_page_config(page_title="FOSTAS v10", page_icon="🌐", layout="wide")

# Session state
if 'projects' not in st.session_state:
    st.session_state.projects = {}

# Header
st.title("🌐 FOSTAS v10 - Website Builder")
st.subheader("5 Yapyzeka ile Website Oluştur")

# Tabs
tab1, tab2 = st.tabs(["📝 Yeni Website", "📋 Projelerim"])

# ===== TAB 1: CREATE =====
with tab1:
    st.subheader("Yeni Website Oluştur")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        project_name = st.text_input("Proje adı:", placeholder="Örn: Kafe Web Sitesi")
        prompt = st.text_area("Website için prompt:", height=100, placeholder="Bana bir kafe web sitesi yap...")
    
    with col2:
        st.markdown("### ⚡ Şablonlar")
        if st.button("☕ Kafe", use_container_width=True, key="tpl_kafe"):
            prompt = "Profesyonel kafe web sitesi"
            project_name = "Kafe Sitesi"
        if st.button("🏛️ Müze", use_container_width=True, key="tpl_muze"):
            prompt = "Müze rehberi web sitesi"
            project_name = "Müze Sitesi"
        if st.button("💼 İşletme", use_container_width=True, key="tpl_isletme"):
            prompt = "Profesyonel işletme web sitesi"
            project_name = "İşletme Sitesi"
    
    if st.button("🚀 Oluştur", use_container_width=True, type="primary"):
        if not prompt:
            st.error("❌ Prompt yazmalısın!")
        else:
            if not project_name:
                project_name = "Website"
            
            with st.spinner("🔄 Website oluşturuluyor..."):
                brain = FOSTASBrain()
                html, success, status = brain.generate(prompt)
            
            # Save to session
            if project_name not in st.session_state.projects:
                st.session_state.projects[project_name] = []
            
            st.session_state.projects[project_name].append({
                "html": html,
                "prompt": prompt,
                "status": status,
                "tokens": brain.total_tokens
            })
            
            st.markdown("---")
            
            # Logs
            st.subheader("📊 İşlem Günlüğü")
            for log in brain.logs:
                st.markdown(f"- {log}")
            
            st.markdown("---")
            
            if success:
                st.success("✅ Website Tamamlandı!")
                
                # Preview
                st.subheader("👀 Ön İzleme")
                components.html(html, height=800, scrolling=True)
                
                st.markdown("---")
                
                # Download
                st.download_button(
                    label="⬇️ HTML İndir",
                    data=html.encode('utf-8'),
                    file_name=f"{project_name}.html",
                    mime="text/html",
                    use_container_width=True
                )
                
                st.info(f"📌 **Tokens Kullanılan:** {brain.total_tokens}")

# ===== TAB 2: PROJECTS =====
with tab2:
    st.subheader("📋 Projelerim")
    
    if not st.session_state.projects:
        st.info("Henüz website oluşturmadın. Yeni bir website yap!")
    else:
        for project_name, versions in st.session_state.projects.items():
            st.markdown(f"### {project_name}")
            
            for i, version in enumerate(versions):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Versiyon {i+1}** - {version['status']}")
                    st.caption(f"Tokens: {version['tokens']}")
                
                with col2:
                    st.download_button(
                        label="⬇️ İndir",
                        data=version['html'].encode('utf-8'),
                        file_name=f"{project_name}_v{i+1}.html",
                        mime="text/html",
                        use_container_width=True,
                        key=f"dl_{project_name}_{i}"
                    )

# Info
st.markdown("---")
st.markdown("""
### ℹ️ FOSTAS v10

**Yapılan Düzeltmeler:**
- ✅ API Keys güvenli (hardcoded, ZIP'de yok)
- ✅ HTML Validation (HTMLParser)
- ✅ Better Error Handling (try-catch)
- ✅ Retry Logic (Exponential Backoff)
- ✅ Full Code QA (2000 char truncate kaldırıldı)
- ✅ Token Tracking
- ✅ Image Download (base64 embed)
- ✅ Session-based Projects
""")
