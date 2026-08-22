import streamlit as st
import streamlit.components.v1 as components
from fostas_brain import FOSTASBrain, ENV_KEYS

st.set_page_config(page_title="FOSTAS", page_icon="🌐", layout="wide")

if "history" not in st.session_state:
    st.session_state.history = []
if "prompt_input" not in st.session_state:
    st.session_state.prompt_input = ""

st.title("🌐 FOSTAS - Website Builder")

brain = FOSTASBrain()

# ===== API durumu =====
status_cols = st.columns(5)
for col, (agent, ok) in zip(status_cols, brain.key_status.items()):
    with col:
        st.write(("✅ " if ok else "❌ ") + agent)

missing = [agent for agent, ok in brain.key_status.items() if not ok]
if missing:
    missing_envs = ", ".join(ENV_KEYS[a] for a in missing)
    st.warning(f"⚠️ Eksik key'ler: **{missing_envs}**. Render'da Settings → Environment kısmından ekle, sonra redeploy et.")

with st.expander("🔧 API bağlantılarını test et (website üretmeden önce bunu dene)"):
    if st.button("Test Et"):
        with st.spinner("5 model test ediliyor..."):
            results = brain.test_connections()
        for agent, (ok, msg) in results.items():
            if ok:
                st.success(f"**{agent}**: bağlantı OK — cevap: {msg}")
            else:
                st.error(f"**{agent}**: {msg}")

st.markdown("---")

# ===== Şablonlar =====
templates = {
    "☕ Kafe": "Profesyonel bir kafe için web sitesi yap: menü, hakkımızda, iletişim bölümleri olsun.",
    "🏛️ Müze": "Bir müze için web sitesi yap: sergiler, ziyaret saatleri, iletişim bölümleri olsun.",
    "💼 İşletme": "Küçük bir işletme için kurumsal web sitesi yap: hizmetler, hakkımızda, iletişim bölümleri olsun.",
}
tcols = st.columns(len(templates))
for tcol, (label, tpl) in zip(tcols, templates.items()):
    if tcol.button(label, use_container_width=True):
        st.session_state.prompt_input = tpl
        st.rerun()

st.text_area("Website için ne istediğini yaz:", height=100, key="prompt_input")

generate_clicked = st.button("🚀 Oluştur", type="primary", use_container_width=True)

if generate_clicked:
    prompt = st.session_state.prompt_input.strip()
    if not prompt:
        st.error("Önce bir prompt yaz.")
    else:
        with st.spinner("5 yapay zeka çalışıyor (~30-60 saniye sürebilir)..."):
            html, success, status = brain.generate(prompt)

        st.session_state.history.append({"prompt": prompt, "html": html, "status": status})

        with st.expander("📋 İşlem günlüğü", expanded=(status != "SUCCESS")):
            for line in brain.logs:
                st.write("•", line)

        if status == "SUCCESS":
            st.success("✅ Website oluşturuldu!")
        else:
            st.warning(
                "⚠️ AI modelleri geçerli kod döndürmedi, hazır şablon gösteriliyor. "
                "Yukarıdaki işlem günlüğünde hangi modelin neden başarısız olduğu yazıyor."
            )

        st.subheader("👀 Önizleme")
        components.html(html, height=750, scrolling=True)

        st.download_button(
            "⬇️ HTML indir",
            data=html.encode("utf-8"),
            file_name="website.html",
            mime="text/html",
            use_container_width=True,
        )

# ===== Geçmiş =====
if st.session_state.history:
    st.markdown("---")
    st.subheader("📋 Geçmiş (bu oturumda)")
    for i, item in enumerate(reversed(st.session_state.history)):
        idx = len(st.session_state.history) - i
        with st.expander(f"{idx}. {item['prompt'][:60]} ({item['status']})"):
            st.download_button(
                "⬇️ İndir",
                data=item["html"].encode("utf-8"),
                file_name=f"website_{idx}.html",
                mime="text/html",
                key=f"hist_dl_{idx}",
            )
