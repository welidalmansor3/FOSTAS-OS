# SIDEBAR
with st.sidebar:
    st.header("📁 FOSTAS Workspace")
    
    st.subheader("🔌 NVIDIA AI Engine Status")
    status = fostas.status
    
    # NVIDIA Modellerinin durumları
    engine_map = {
        "GLM-5.2 (Kod)": "glm",
        "DeepSeek V4 (GDD)": "deepseek",
        "Llama 3.3 (Planlama)": "llama",
        "GPT-OSS (Mantık)": "gpt_oss"
    }
    
    for engine_name, key in engine_map.items():
        info = status[key]
        color = "#4caf50" if info["ok"] else "#ff4b4b"
        text = "bağlı" if info["ok"] else "eksik"
        st.markdown(f"<span style='color:{color}'>●</span> {engine_name}: {text}", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader("📥 Upload Your 3D Models (.glb, .zip)")
    uploaded_3d = st.file_uploader("Kendi modellerini yükle", type=["glb", "gltf", "zip"], key="3d_uploader")
    if uploaded_3d is not None:
        if uploaded_3d.name.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(uploaded_3d) as z:
                for filename in z.namelist():
                    if filename.endswith((".glb", ".gltf")):
                        file_data = z.read(filename)
                        safe_name = os.path.basename(filename)
                        fostas.register_user_asset(safe_name, file_data)
                        st.success(f"Yüklendi: {safe_name}")
        else:
            fostas.register_user_asset(uploaded_3d.name, uploaded_3d.getvalue())
            st.success(f"Yüklendi: {uploaded_3d.name}")
        st.rerun()

    st.markdown("---")
    
    st.subheader("🎨 3D Asset Registry")
    if fostas.project_memory["assets"]:
        for asset in fostas.project_memory["assets"]:
            col_name, col_dl = st.columns([2, 1])
            with col_name:
                st.write(f"📦 {asset['name']}")
            with col_dl:
                if asset.get("data"):
                    st.download_button(label="⬇️", data=asset["data"], file_name=asset["name"], key=f"dl_{asset['name']}")
    else:
        st.write("Henüz 3D model yok.")
