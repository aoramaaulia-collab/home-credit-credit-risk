import streamlit as st

st.title('Tentang Aplikasi')
st.markdown("""
Aplikasi ini adalah alat bantu **tim Credit Risk Home Credit** untuk menilai risiko gagal bayar pemohon kredit,
dibangun sebagai bagian dari proyek *Home Credit Default Risk*.

**Alur proyek**

| Tahap | Notebook | Isi |
|---|---|---|
| Business understanding | 01 | Masalah, KPI, analisis biaya False Negative vs False Positive |
| ETL | 02 | CSV ke Parquet ke BigQuery, data mart (agregasi riwayat kredit dengan SQL) |
| EDA | 03 | Data profiling, uji statistik, business insight |
| Modeling | 04 | Preprocessing pipeline, 4 model + tuning, threshold berbasis F2 dan biaya, SHAP |

**Cara kerja keputusan**
- Model menghasilkan **probabilitas gagal bayar (PD)**.
- **Approve** jika PD di bawah threshold terpilih (F2 tertinggi dengan guardrail biaya).
- **Review / limit dikurangi** jika PD di antara threshold terpilih dan threshold biaya minimum.
- **Reject** jika PD di atas threshold biaya minimum.
- **Expected loss** = PD × jumlah pinjaman × LGD (45%, asumsi konservatif).

**Prinsip keadilan:** gender tidak dipakai sebagai fitur, sesuai prinsip perlakuan adil dan non-diskriminatif (POJK 22/2023).

**Catatan:** skor model adalah alat bantu keputusan. Keputusan akhir tetap mengikuti kebijakan kredit dan pertimbangan analis.
""")
