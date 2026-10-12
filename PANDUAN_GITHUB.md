# Panduan GitHub: dari Membuat Repositori sampai File Masuk

Panduan ini untuk folder `C:\Users\LOQ\Downloads\home-credit-project`. Ikuti berurutan.

## Tahap 1. Rancangan repositori

| Item | Isi |
|---|---|
| Nama repo | `home-credit-credit-risk` |
| Deskripsi | Credit scoring & kebijakan kredit Home Credit: ETL BigQuery, EDA, LightGBM (F2 / PR-AUC), simulasi dampak nominal, Streamlit, Power BI |
| Visibilitas | Public (agar link bisa dimasukkan ke PPT) |
| Topics | `credit-scoring`, `machine-learning`, `lightgbm`, `streamlit`, `power-bi`, `bigquery`, `shap` |
| Branch utama | `main` |

**Isi repo (yang ikut di-push):**

```
home-credit-credit-risk/
|-- README.md                         ringkasan proyek & hasil (halaman depan repo)
|-- requirements.txt                  library Python
|-- .gitignore                        daftar file yang TIDAK di-push
|-- 01_business_understanding.ipynb
|-- 02_etl.ipynb
|-- 03_eda.ipynb
|-- 04_modeling.ipynb
|-- src/                              feature engineering, preprocessing, SQL data mart
|-- models/                           model final, metadata, artefak evaluasi
|-- app/  streamlit_app.py  .streamlit/   aplikasi Streamlit
|-- app_data/                         data ringan untuk aplikasi
|-- powerbi/                          dashboard Power BI (PBIP) + data CSV
|-- build_app_data.py  build_policy_data.py
|-- submission.csv                    prediksi application_test
```

**Yang TIDAK boleh di-push** (sudah diatur di `.gitignore`):
- `gcp-key.json`: kunci akses BigQuery. Jika bocor, orang lain bisa memakai akun Google Cloud Anda.
- `data/`: data mentah dan parquet besar (ratusan MB, melebihi batas GitHub 100 MB per file).
- `04_modeling_v4.ipynb`, `__pycache__/`, `desktop.ini`: duplikat dan file sistem.

## Tahap 2. Persiapan (sekali saja)

1. Instal Git: https://git-scm.com/download/win, semua pilihan default.
2. Tutup dan buka lagi VS Code, buka terminal (Ctrl + `), lalu:
   ```
   git --version
   git config --global user.name "Nama Anda"
   git config --global user.email "aoramaaulia@gmail.com"
   ```
   Email harus sama dengan email akun GitHub agar commit tercatat atas nama Anda.

## Tahap 3. Membuat repositori di GitHub

1. Login ke https://github.com, klik **+** (kanan atas) > **New repository**.
2. Repository name: `home-credit-credit-risk`. Description: salin dari tabel Tahap 1.
3. Pilih **Public**.
4. **Jangan** centang *Add a README*, *.gitignore*, atau *license* (sudah ada di folder; jika dicentang akan bentrok saat push).
5. Klik **Create repository**, salin URL `https://github.com/USERNAME/home-credit-credit-risk.git`.

## Tahap 4. Memasukkan file

Di terminal VS Code:

```
cd C:\Users\LOQ\Downloads\home-credit-project
git init
git add .
git status
```

**Cek keamanan sebelum lanjut.** Di daftar hijau `git status`:
- TIDAK boleh ada `gcp-key.json` dan folder `data/`.
- Harus ada notebook 01-04, `README.md`, `src/`, `models/`, `app/`, `powerbi/`.

Jika `gcp-key.json` ikut muncul, jalankan `git rm --cached gcp-key.json` lalu cek lagi `.gitignore`.

Lalu:

```
git commit -m "Home Credit credit risk: ETL, EDA, modeling, Streamlit, Power BI"
git branch -M main
git remote add origin https://github.com/USERNAME/home-credit-credit-risk.git
git push -u origin main
```

Saat push pertama, jendela login muncul: pilih **Sign in with your browser** > **Authorize git-ecosystem**.

## Tahap 5. Merapikan halaman repo

1. Refresh halaman repo: README tampil di bawah daftar file.
2. Klik ikon gerigi di samping **About** (kanan): isi deskripsi, website (link Streamlit nanti), dan topics dari Tahap 1.
3. Buka `04_modeling.ipynb` di GitHub untuk memastikan grafik tampil. Jika muncul "Unable to render", buka lewat https://nbviewer.org dengan menempel URL file.

## Tahap 6. Deploy Streamlit dari GitHub

1. Buka https://share.streamlit.io, login dengan GitHub.
2. **Create app** > repo `home-credit-credit-risk`, branch `main`, main file `streamlit_app.py` > **Deploy**.
3. Salin link aplikasi, tempel di bagian About repo dan di README (baris *Demo*).

## Tahap 7. Update berikutnya

```
git add .
git commit -m "jelaskan perubahan, misal: perbaiki dashboard Power BI"
git push
```

## Checklist akhir (untuk PPT)

- [ ] Repo public dan bisa dibuka tanpa login
- [ ] README tampil dengan ringkasan hasil
- [ ] Notebook 01-04 ada dan output-nya terlihat
- [ ] `gcp-key.json` tidak ada di repo
- [ ] Link GitHub (dan link Streamlit) dimasukkan ke slide terakhir PPT
