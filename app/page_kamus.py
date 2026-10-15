import streamlit as st

from app.glossary import render_glossary

st.title('Kamus Istilah')
st.markdown('Halaman ini menjelaskan semua istilah yang muncul di aplikasi, dari istilah risiko kredit seperti PD dan LGD, '
            'istilah keputusan seperti batas approve dan batas reject, sampai istilah evaluasi model seperti recall dan F2-score. '
            'Ketik kata kunci di kotak pencarian untuk langsung menemukan istilah yang dicari.')
render_glossary()
