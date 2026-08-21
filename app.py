import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASBrain
from database import Database

# Config
st.set_page_config(page_title="FOSTAS v10", page_icon="🌐", layout="wide")

# Database
db = Database("fostas.db")

# Session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

# ===== LOGIN PAGE =====
if not st.session_state.user_id:
    st.title("🌐 FOSTAS v10")
    st.subheader("Website & App Builder")
    
    tab1, tab2 = st.tabs(["Giriş", "Kaydol"])
    
    with tab1:
        st.markdown("### 🔓 Giriş Yap")
        username = st.text_input("Kullanıcı adı:")
        password = st.text_input("Şifre:", type="password")
        
        if st.button("Giriş", use_container_width=True, type="primary"):
            result = db.get_user(username, password)
            if result:
                st.session_state.user_id = result[0]
                st.session_state.username = result[1]
                st.success("✅ Giriş başarılı!")
                st.rerun()
            else:
                st.error("❌ Kullanıcı adı veya şifre yanlış!")
    
    with tab2:
        st.markdown("### 📝 Kaydol")
        new_username = st.text_input("Yeni kullanıcı adı:", key="signup_user")
        new_email = st.text_input("Email:", key="signup_email")
        new_password = st.text_input("Şifre:", type="password", key="signup_pass")
        
        if st.button("Kaydol", use_container_width=True):
            if len(new_username) < 3:
                st.error("Kullanıcı adı en az 3 karakter olmalı!")
            elif len(new_password) < 4:
                st.error("Şifre en az 4 karakter olmalı!")
            else:
                if db.create_user(new_username, new_password, new_email):
                    st.success("✅ Kaydol başarılı! Giriş yapabilirsiniz.")
                else:
                    st.error("❌ Bu kullanıcı adı zaten var!")

# ===== MAIN APP =====
else:
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"🌐 FOSTAS - {st.session_state.username}")
    with col2:
        if st.button("🚪 Çıkış", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📝 Yeni Proje", "📋 Projelerim", "⚙️ Ayarlar"])
    
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
            if not project_name or not prompt:
                st.error("❌ Proje adı ve prompt yazmalısın!")
            else:
                # Create project
                project_id = db.create_project(st.session_state.user_id, project_name, prompt)
                st.session_state.current_project = project_id
                
                with st.spinner("🔄 Website oluşturuluyor..."):
                    brain = FOSTASBrain()
                    html, success, status = brain.generate(prompt)
                
                # Save to database
                db.save_generation(
                    project_id,
                    prompt,
                    html,
                    status,
                    brain.used_models,
                    brain.total_tokens
                )
                
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
        
        projects = db.get_projects(st.session_state.user_id)
        
        if not projects:
            st.info("Henüz proje yok. Yeni bir proje oluştur!")
        else:
            for project in projects:
                proj_id, name, status, created = project
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**{name}** ({status})")
                    st.caption(f"Oluşturuldu: {created}")
                
                with col2:
                    if st.button("👁️ Gör", key=f"view_{proj_id}", use_container_width=True):
                        proj_detail = db.get_project(proj_id, st.session_state.user_id)
                        if proj_detail and proj_detail[3]:
                            components.html(proj_detail[3], height=600, scrolling=True)
                
                with col3:
                    if st.button("⬇️ İndir", key=f"dl_{proj_id}", use_container_width=True):
                        proj_detail = db.get_project(proj_id, st.session_state.user_id)
                        if proj_detail and proj_detail[3]:
                            st.download_button(
                                label="HTML",
                                data=proj_detail[3].encode('utf-8'),
                                file_name=f"{name}.html",
                                mime="text/html",
                                key=f"dlbtn_{proj_id}"
                            )
    
    # ===== TAB 3: SETTINGS =====
    with tab3:
        st.subheader("⚙️ Ayarlar")
        
        st.markdown("### 👤 Profil")
        st.write(f"**Kullanıcı:** {st.session_state.username}")
        
        st.markdown("### 🔐 Güvenlik")
        st.info("🔒 Şifreler güvenli şekilde şifrelenmiştir.")
        
        st.markdown("### 📊 İstatistikler")
        projects = db.get_projects(st.session_state.user_id)
        st.metric("Toplam Projeler", len(projects))
        
        st.markdown("### ℹ️ FOSTAS v10")
        st.markdown("""
        **Düzeltmeler:**
        - ✅ API Keys güvenli (hardcoded)
        - ✅ SQLite Database
        - ✅ Authentication
        - ✅ Project Persistence
        - ✅ HTML Validation
        - ✅ Better Error Handling
        - ✅ Retry Logic (Exponential Backoff)
        - ✅ Full Code QA (not truncated)
        - ✅ Token Tracking
        - ✅ Generation History
        """)
