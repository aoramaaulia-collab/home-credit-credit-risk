# Panduan Publikasi: Agar Streamlit dan Dashboard Bisa Dilihat Publik

Ada tiga hasil yang bisa dibagikan: **repository GitHub**, **aplikasi Streamlit**, dan **dashboard Power BI**. Kerjakan berurutan, karena Streamlit mengambil kode dari GitHub.

## 1. GitHub (wajib lebih dulu)

Ikuti `PANDUAN_GITHUB.md` sampai repo berstatus **Public** dan semua file sudah ter-push. Link repo inilah yang dicantumkan di PPT.

## 2. Aplikasi Streamlit (gratis, publik, cukup akun GitHub)

1. Buka https://share.streamlit.io lalu klik **Continue with GitHub** dan izinkan akses.
2. Klik **Create app** > **Deploy a public app from GitHub**.
3. Isi:
   - Repository: `USERNAME/home-credit-credit-risk`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: pilih nama pendek, misalnya `homecredit-risk` (hasilnya `https://homecredit-risk.streamlit.app`)
4. Buka **Advanced settings** dan pilih Python **3.12**, lalu klik **Deploy**. Proses pertama 3-8 menit karena menginstal library dari `requirements.txt`.
5. Setelah aplikasi terbuka, uji halaman Scoring Pemohon dan Performa & Kebijakan.
6. Salin link aplikasi ke PPT (slide 10), README, dan bagian About repo GitHub.

**Jika gagal deploy:**
- `ModuleNotFoundError`: nama library belum ada di `requirements.txt`; tambahkan, commit, push, lalu klik **Reboot app**.
- Error versi scikit-learn saat memuat model: jalankan `pip show scikit-learn lightgbm` di laptop, lalu tulis versinya persis di `requirements.txt` (contoh `scikit-learn==1.7.2`), commit dan push.
- Aplikasi "tertidur" setelah beberapa hari tidak dibuka: ini normal di paket gratis; pengunjung cukup klik **Yes, get this app back up**.

## 3. Dashboard Power BI

Power BI punya fitur **Publish to web** yang membuat link publik tanpa perlu login. Syaratnya:
- Login Power BI memakai **akun kerja atau sekolah** (contoh email kampus `nama@student.ac.id`). Email Gmail, Yahoo, atau Outlook pribadi **tidak bisa** dipakai mendaftar Power BI Service.
- Admin organisasi (misalnya IT kampus) mengizinkan fitur Publish to web. Jika tidak diizinkan, menu tersebut tidak muncul atau meminta persetujuan admin.

### Opsi A: punya email kampus/kantor (link interaktif publik)
1. Di Power BI Desktop, buka `powerbi/HomeCreditRisk.pbip`, klik **Refresh**, lalu **File > Save as** dan simpan sebagai `HomeCreditRisk.pbix`.
2. Klik **Home > Publish**, login dengan email kampus/kantor, pilih **My workspace**.
3. Klik **Open 'HomeCreditRisk.pbix' in Power BI** pada jendela sukses (atau buka https://app.powerbi.com > My workspace > report).
4. Di report: **File > Embed report > Publish to web (public)** > **Create embed code** > **Publish**.
5. Salin **Link you can send in email**. Link ini bisa dibuka siapa saja dan tetap interaktif (slicer, sorotan warna, tooltip).
6. Data di dashboard adalah data uji tanpa identitas pribadi (hanya ID nasabah dan atribut segmen), jadi aman dipublikasikan untuk portofolio.

### Opsi B: tidak punya email kampus/kantor (tetap bisa dilihat publik)
1. Di Power BI Desktop: **File > Export > Export to PDF** untuk menyimpan kedua halaman.
2. Ambil screenshot setiap halaman (Windows + Shift + S), simpan sebagai `docs/dashboard_ringkasan.png` dan `docs/dashboard_profil.png`.
3. Opsional: rekam layar 20-30 detik saat menggeser slicer (Windows + Alt + R di Xbox Game Bar), lalu ubah menjadi GIF di https://ezgif.com agar interaktivitas terlihat.
4. Tambahkan ke README:
   ```markdown
   ## Dashboard Power BI
   ![Ringkasan Kebijakan](docs/dashboard_ringkasan.png)
   ![Profil Risiko](docs/dashboard_profil.png)
   File proyek: `powerbi/HomeCreditRisk.pbip` (buka di Power BI Desktop untuk versi interaktif).
   ```
5. Commit dan push. Gambar akan tampil di halaman depan repo GitHub, dan pengunjung yang punya Power BI Desktop tetap bisa membuka versi interaktifnya dari folder `powerbi/`.

## 4. Checklist sebelum dibagikan

- [ ] Repo GitHub public, README tampil rapi
- [ ] Link Streamlit terbuka di browser lain (mode incognito) tanpa login
- [ ] Dashboard Power BI: link Publish to web, atau gambar di README
- [ ] `gcp-key.json` tidak ada di repo
- [ ] Ketiga link tercantum di slide terakhir PPT
