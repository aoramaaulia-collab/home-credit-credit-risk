"""Kamus istilah untuk pembaca dari semua latar belakang (sama dengan kamus di artikel Medium)."""
import streamlit as st

G = [
 ('Istilah risiko kredit', [
  ('Default (gagal bayar)', 'Kondisi ketika nasabah mengalami kesulitan membayar cicilan. Di dataset ini ditandai dengan TARGET = 1, sedangkan nasabah yang membayar lancar ditandai TARGET = 0.'),
  ('Default rate', 'Persentase pemohon yang gagal bayar dalam suatu kelompok. Contohnya, default rate 8,1% berarti dari 100 pemohon, sekitar 8 orang mengalami kesulitan membayar.'),
  ('PD (Probability of Default)', 'Perkiraan peluang seorang pemohon akan gagal bayar, dihasilkan oleh model dalam bentuk persen. PD 15% berarti dari 100 pemohon dengan profil serupa, sekitar 15 orang diperkirakan gagal bayar.'),
  ('LGD (Loss Given Default)', 'Bagian pinjaman yang benar-benar hilang ketika nasabah gagal bayar, setelah dikurangi hasil penagihan. LGD 45% berarti dari pinjaman 10 juta yang macet, sekitar 4,5 juta tidak kembali.'),
  ('Expected loss (perkiraan kerugian)', 'Perkiraan uang yang hilang akibat gagal bayar, dihitung sebagai jumlah pinjaman dikali LGD. Angka ini dipakai untuk membandingkan kebijakan tanpa model dan dengan model.'),
  ('Kerugian dicegah', 'Selisih expected loss tanpa model dan dengan model, yaitu kerugian yang tidak terjadi karena pemohon berisiko tinggi tidak langsung disetujui.'),
  ('Margin bunga bersih (NIM)', 'Keuntungan bunga yang diperoleh perusahaan dari setiap rupiah pinjaman dalam setahun. Di proyek ini dipakai 13,6% per tahun, dihitung dari laporan publik Home Credit Indonesia.'),
  ('Keuntungan hilang', 'Pendapatan bunga yang tidak jadi diperoleh karena nasabah yang sebenarnya akan membayar lancar ikut ditolak. Ini adalah "harga" dari bersikap terlalu ketat.'),
  ('Penghematan bersih', 'Kerugian yang dicegah dikurangi keuntungan yang hilang. Jika positif, kebijakan dengan model lebih menguntungkan daripada menyetujui semua pemohon.'),
  ('Skor eksternal', 'Skor kelayakan kredit dari lembaga lain di luar Home Credit (EXT_SOURCE_1 sampai 3). Makin tinggi skornya, makin kecil risiko gagal bayar.'),
  ('Desil', 'Cara membagi pemohon menjadi 10 kelompok sama besar menurut suatu nilai. D1 adalah 10% pemohon dengan skor eksternal terendah, D10 adalah 10% dengan skor tertinggi.'),
 ]),
 ('Istilah keputusan kredit', [
  ('Threshold (batas keputusan)', 'Angka PD yang dipakai sebagai garis pemisah keputusan. Pemohon dengan PD di atas batas dianggap berisiko, di bawah batas dianggap aman.'),
  ('Batas approve (12%)', 'Pemohon dengan PD di bawah 12% langsung disetujui. Batas ini dipilih dengan mencari F2-score setinggi mungkin, tetapi dengan syarat total biaya tidak boleh lebih mahal daripada tanpa model.'),
  ('Batas reject (22%)', 'Pemohon dengan PD 22% atau lebih ditolak. Batas ini dipilih karena di titik inilah total biaya (kerugian ditambah keuntungan hilang) paling kecil.'),
  ('Zona Approve, Review, Reject', 'Tiga kelompok keputusan hasil dua batas di atas. Approve (PD di bawah 12%) disetujui otomatis, Review (12% sampai 22%) diperiksa analis atau diberi limit lebih kecil, dan Reject (22% ke atas) ditolak.'),
  ('Limit di zona Review', 'Skenario ketika pemohon zona Review tetap dilayani tetapi dengan pinjaman yang dipotong, misalnya hanya 50% dari pengajuan. Tujuannya menjaga pendapatan sambil membatasi risiko.'),
 ]),
 ('Istilah evaluasi model', [
  ('False Negative (FN)', 'Pemohon yang nantinya gagal bayar, tetapi diprediksi aman dan disetujui. Kesalahan ini menimbulkan kerugian pinjaman.'),
  ('False Positive (FP)', 'Pemohon yang sebenarnya membayar lancar, tetapi diprediksi berisiko dan ditolak. Kesalahan ini menghilangkan keuntungan bunga.'),
  ('Confusion matrix', 'Tabel 2x2 yang menghitung berapa banyak keputusan benar dan salah: benar disetujui, nasabah baik tersaring (FP), gagal bayar lolos (FN), dan gagal bayar tertangkap.'),
  ('Recall', 'Dari semua pemohon yang benar-benar gagal bayar, berapa persen yang berhasil ditangkap model. Recall 57% berarti 57 dari 100 calon gagal bayar tersaring.'),
  ('Precision', 'Dari semua pemohon yang ditandai berisiko oleh model, berapa persen yang benar-benar gagal bayar. Precision 23% berarti sekitar 1 dari 4 pemohon yang tersaring memang gagal bayar.'),
  ('F2-score', 'Gabungan recall dan precision yang memberi bobot recall empat kali lebih besar. Dipakai karena meloloskan calon gagal bayar jauh lebih mahal daripada menolak nasabah baik.'),
  ('PR-AUC', 'Luas di bawah kurva Precision-Recall, ukuran utama untuk memilih model pada data tidak seimbang. Tebakan acak hanya mendapat 0,081, model ini 0,288.'),
  ('ROC-AUC dan Gini', 'Ukuran seberapa baik model mengurutkan pemohon dari paling aman ke paling berisiko. ROC-AUC 0,5 berarti acak, 1 berarti sempurna. Gini adalah 2 x ROC-AUC dikurangi 1, ukuran yang umum di industri kredit.'),
  ('KS (Kolmogorov-Smirnov)', 'Jarak terbesar antara sebaran skor nasabah lancar dan nasabah gagal bayar. Makin besar, makin jelas model memisahkan keduanya.'),
  ('Brier score', 'Ukuran ketepatan angka probabilitas. Makin kecil makin baik. Brier 0,0655 menunjukkan PD model bisa dibaca apa adanya.'),
  ('Kalibrasi', 'Kesesuaian antara PD yang diprediksi dan kenyataan. Model terkalibrasi baik jika kelompok dengan PD 10% memang gagal bayar sekitar 10%.'),
  ('Validasi silang (OOF)', 'Cara menguji model dengan membagi data latih menjadi beberapa bagian, lalu setiap bagian diprediksi oleh model yang tidak pernah melihatnya. Hasilnya lebih jujur daripada menguji di data yang dipakai untuk belajar.'),
  ('Class weight', 'Teknik memberi bobot lebih pada kelas yang jarang (gagal bayar). Di proyek ini tidak dipakai karena tidak menaikkan PR-AUC dan justru merusak ketepatan angka probabilitas.'),
  ('Data leakage', 'Kebocoran informasi dari masa depan ke dalam data latih, misalnya memakai data yang baru ada setelah pinjaman disetujui. Leakage membuat model terlihat hebat saat diuji tetapi gagal saat dipakai.'),
  ('SHAP', 'Metode untuk menjelaskan mengapa model memberi skor tertentu, dengan membagi skor menjadi sumbangan setiap faktor. Faktor yang menaikkan risiko dan yang menurunkan risiko bisa dilihat satu per satu.'),
  ('Log-odds', 'Skala internal yang dipakai model sebelum hasilnya diubah menjadi persen. Nilai SHAP dinyatakan dalam satuan ini, sehingga yang perlu dibaca adalah arah dan besarnya, bukan angka persennya.'),
 ]),
 ('Istilah teknis dan alat', [
  ('LightGBM', 'Algoritma machine learning berbasis gabungan banyak pohon keputusan. Dipilih sebagai model final karena PR-AUC-nya tertinggi dan cepat dilatih.'),
  ('ETL dan data mart', 'ETL (Extract, Transform, Load) adalah proses mengambil data mentah, merapikannya, lalu memuatnya ke gudang data. Data mart adalah tabel siap analisis hasil proses itu, di proyek ini dibuat di Google BigQuery.'),
  ('Streamlit', 'Pustaka Python untuk membuat aplikasi web interaktif. Di proyek ini dipakai untuk menghitung risiko pemohon dan menampilkan alasannya.'),
  ('Power BI', 'Aplikasi dashboard dari Microsoft. Di proyek ini dipakai untuk simulasi kebijakan dan melihat profil risiko per kelompok pemohon.'),
 ]),
]


def render_glossary(sections=None, search=True, key='kamus'):
    """Tampilkan kamus per kelompok. sections = daftar nama kelompok (None = semua)."""
    q = st.text_input('Cari istilah', placeholder='contoh: LGD, batas reject, recall', key=key).strip().lower() if search else ''
    found = 0
    for sec, items in G:
        if sections and sec not in sections:
            continue
        rows = [(t, d) for t, d in items if not q or q in t.lower() or q in d.lower()]
        if not rows:
            continue
        st.markdown(f'#### {sec}')
        st.markdown('\n'.join(f'- **{t}**: {d}' for t, d in rows))
        found += len(rows)
    if q and not found:
        st.info('Istilah tidak ditemukan. Coba kata kunci lain.')


def glossary_expander(sections=None, key='kamus_x'):
    with st.expander('Kamus istilah (klik untuk melihat arti istilah di halaman ini)'):
        render_glossary(sections, search=False, key=key)
        st.caption('Daftar lengkap ada di halaman Kamus Istilah.')
