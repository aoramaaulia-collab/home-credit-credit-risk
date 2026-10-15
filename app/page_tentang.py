import streamlit as st

from app.explain import guide

st.title('Tentang Aplikasi')
st.markdown("""
Aplikasi ini adalah alat bantu **tim Credit Risk Home Credit** untuk menilai risiko gagal bayar pemohon kredit. Dibangun sebagai proyek akhir
**Home Credit Indonesia x Rakamin Academy (Data Scientist Project Based Virtual Internship)**.

### Masalah yang diselesaikan
Sekitar **8,1%** pemohon historis mengalami kesulitan membayar cicilan. Meloloskan pemohon berisiko menimbulkan kerugian besar, tetapi menolak
pemohon yang sebenarnya mampu membayar juga merugikan karena keuntungan dari bunga ikut hilang. Kerugian dari satu gagal bayar yang lolos
diperkirakan **3,7-6,1 kali** lebih besar daripada keuntungan yang hilang dari satu nasabah baik yang ditolak. Karena itu model dinilai dengan
**F2-score** (menangkap gagal bayar diberi bobot lebih besar) dan **PR curve**, lalu dampaknya dihitung dalam uang.

### Alur proyek
| Tahap | Isi |
|---|---|
| 1. Business understanding | Masalah, KPI, analisis biaya salah menolak vs salah menyetujui, pemilihan metrik |
| 2. ETL | CSV ke Parquet ke BigQuery, lalu tujuh tabel riwayat diringkas menjadi satu tabel per pemohon dengan SQL |
| 3. EDA | Profiling data, uji statistik, dan insight bisnis |
| 4. Modeling | Pipeline pengolahan data, 4 model dibandingkan, tuning, pemilihan threshold berdasarkan F2 dan biaya, penjelasan SHAP |
| 5. Deployment | Aplikasi Streamlit ini dan dashboard Power BI |

### Bagaimana keputusan dibuat
""")
guide('Tiga zona keputusan', """<ul>
<li><b>Setujui</b> jika probabilitas gagal bayar di bawah <b>12%</b>. Batas ini adalah F2 tertinggi yang total biayanya tidak lebih buruk daripada tanpa model.</li>
<li><b>Tinjau ulang</b> jika 12% sampai 22%. Pemohon tetap bisa dilayani dengan limit lebih kecil, tenor lebih pendek, atau uang muka.</li>
<li><b>Tolak</b> jika 22% ke atas. Pada batas ini total biaya paling kecil: kerugian yang diperkirakan lebih besar daripada keuntungannya.</li>
</ul>""")
st.markdown("""
### Kamus istilah
| Istilah | Arti sederhana |
|---|---|
| Probabilitas gagal bayar (PD) | Peluang pemohon kesulitan membayar cicilan, dari 0% sampai 100% |
| Default rate | Persentase pemohon dalam suatu kelompok yang benar-benar gagal bayar |
| Expected loss | Perkiraan uang yang hilang = pinjaman gagal bayar x LGD |
| LGD | Bagian pinjaman yang tidak kembali saat gagal bayar (diasumsikan 45%) |
| Recall | Persentase gagal bayar yang berhasil ditandai model |
| Precision | Persentase pemohon yang ditandai berisiko yang memang gagal bayar |
| F2-score | Gabungan recall dan precision, recall diberi bobot 4 kali |
| PR-AUC | Ukuran kualitas model pada data tidak seimbang; tebakan acak = 0,081 |
| SHAP | Metode untuk membagi skor akhir menjadi sumbangan setiap faktor |
| Skor eksternal | Skor kelayakan kredit dari lembaga lain (0 sampai 1) |

### Prinsip dan batasan
- **Keadilan:** gender tidak dipakai sebagai faktor penilaian (POJK 22/2023).
- **Alat bantu, bukan pengganti analis:** keputusan akhir tetap mengikuti kebijakan kredit dan pertimbangan analis.
- **Keterbatasan:** model dilatih dari data historis pemohon yang dulu disetujui; performa perlu dipantau setiap bulan.
  Penjelasan lengkap ada di halaman *Performa & Kebijakan*, tab *Keterbatasan & rekomendasi model*.
- Nilai uang dalam unit mata uang dataset karena dataset tidak menyebut negara asalnya.

### Tautan
- Kode dan notebook: [GitHub](https://github.com/aoramaaulia-collab/home-credit-credit-risk)
- Ringkasan proyek: [Portfolio](https://aoramaaulia-collab.github.io/home-credit-credit-risk/)
""")
