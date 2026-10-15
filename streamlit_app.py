"""Home Credit Risk Scoring - aplikasi Streamlit (halaman utama & navigasi)."""
import streamlit as st

st.set_page_config(page_title='Home Credit Risk Scoring', page_icon=':material/credit_score:', layout='wide')

from app.common import CSS, load_model, load_overview, fmt_pct  # noqa: E402
from app.explain import CSS_EXTRA  # noqa: E402

st.markdown(CSS + CSS_EXTRA, unsafe_allow_html=True)

pages = [
    st.Page('app/page_beranda.py', title='Profil Risiko Portofolio', icon=':material/dashboard:', default=True),
    st.Page('app/page_scoring.py', title='Scoring Pemohon', icon=':material/person_search:'),
    st.Page('app/page_batch.py', title='Scoring Batch (CSV)', icon=':material/table_view:'),
    st.Page('app/page_model.py', title='Performa & Kebijakan', icon=':material/monitoring:'),
    st.Page('app/page_kamus.py', title='Kamus Istilah', icon=':material/menu_book:'),
    st.Page('app/page_tentang.py', title='Tentang', icon=':material/info:'),
]
nav = st.navigation(pages)

with st.sidebar:
    st.markdown('<div class="sb-title">Home Credit Risk Scoring</div><div class="sb-sub">Prediksi probabilitas gagal bayar pemohon kredit</div>',
                unsafe_allow_html=True)
    st.divider()
    model, meta = load_model()
    ov = load_overview()
    st.caption('INFO MODEL')
    if meta:
        st.markdown(f"**Algoritma:** {meta['model']}  \n**PR-AUC (test):** {meta['test_pr_auc']:.3f}  \n"
                    f"**ROC-AUC (test):** {meta['test_roc_auc']:.3f}  \n**F2 (test):** {meta['test_f2']:.3f}  \n"
                    f"**Batas approve:** {fmt_pct(meta['threshold_approve'])}  \n**Batas reject:** {fmt_pct(meta['threshold_reject'])}")
    else:
        st.info('Model belum dimuat. Jalankan NB 04 untuk menghasilkan file model.')
    st.caption(f"Data historis: {ov['jumlah_pengajuan']:,}".replace(',', '.') + f" pengajuan · default rate {fmt_pct(ov['default_rate'])}")

nav.run()
