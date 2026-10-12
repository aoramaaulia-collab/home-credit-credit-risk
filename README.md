# Home Credit Default Risk: Credit Scoring & Kebijakan Kredit

Proyek akhir **Home Credit Indonesia x Rakamin (VIX Data Scientist)**. Tujuannya membantu tim Credit Risk **memisahkan pemohon yang mampu bayar dan yang berisiko gagal bayar sejak tahap pengajuan**, lalu menerjemahkan skor model menjadi kebijakan yang bisa diukur dalam uang.

**Demo Streamlit:** [(Aplikasi deploy)](https://home-credit-credit-risk-emvn4romwxnpwuyke5nquy.streamlit.app/page_scoring)  

## Ringkasan hasil

| Item | Hasil (data test 20%, 61.503 pemohon) |
|---|---|
| Model terpilih | LightGBM (dibandingkan dengan Logistic Regression, Random Forest, XGBoost; tuning RandomizedSearchCV, metrik PR-AUC) |
| PR-AUC / ROC-AUC / Gini | 0,288 / 0,793 / 0,586 (PR-AUC model acak = 0,081) |
| F2-score (metrik utama) | 0,439 pada batas approve 12% (recall 57%, precision 23%) |
| Default rate pinjaman disetujui | turun dari 8,07% menjadi 4,34% (80% pengajuan tetap disetujui) |
| Expected loss (LGD 45%) | turun 53,7%: dari 1,24 M menjadi 0,57 M (unit mata uang dataset) |
| Kebijakan 3 zona | Approve 80% (DR 4,3%), Review 12% (DR 15,7%), Reject 8% (DR 33,6%, menangkap 33% seluruh gagal bayar) |
| Penghematan bersih | impas pada LGD 45%; 13-21% pada LGD 60-75% |

## Alur proyek

| Tahap | File | Isi |
|---|---|---|
| 1. Business understanding | `01_business_understanding.ipynb` | Masalah, KPI, biaya False Negative vs False Positive, pemilihan metrik F2 & PR curve |
| 2. ETL | `02_etl.ipynb`, `src/sql_v2.py` | CSV -> Parquet (staging) -> BigQuery; data mart riwayat kredit dengan SQL |
| 3. EDA | `03_eda.ipynb` | Data profiling, kualitas data, uji statistik (Mann-Whitney, chi-square, IV, VIF), business insight |
| 4. Modeling | `04_modeling.ipynb`, `src/features.py` | Pipeline preprocessing, eksperimen class weight, tuning 4 model, seleksi fitur, threshold F2 + guardrail biaya, dampak bisnis nominal, SHAP, fairness |
| 5. Aplikasi | `streamlit_app.py`, `app/` | Scoring pemohon, scoring batch CSV, simulator kebijakan nominal |
| 6. Dashboard | `powerbi/HomeCreditRisk.pbip` | Dashboard Power BI (format PBIP) dengan simulasi threshold, LGD, dan limit zona Review |

## Struktur folder

```
app/                 halaman Streamlit
app_data/            data ringan untuk aplikasi (agregat segmen, pemohon application_test, skor data test)
models/              model final (joblib), metadata, artefak evaluasi
powerbi/             proyek Power BI (PBIP) + data CSV + skrip pembangun
src/                 fungsi feature engineering & preprocessing (dipakai notebook dan aplikasi)
```

## Menjalankan

```bash
pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Notebook 02 membutuhkan dataset mentah dan kredensial BigQuery sendiri (`gcp-key.json`, tidak disertakan di repo).

**Dashboard Power BI:** buka `powerbi/HomeCreditRisk.pbip` di Power BI Desktop. Jika lokasi folder berbeda, ubah parameter `DataFolder` (Transform data > Manage parameters) ke path folder `powerbi/data` di komputer Anda, lalu Refresh.

## Catatan

- Negara dan mata uang dataset tidak disebutkan, sehingga nilai uang disajikan dalam unit dataset. Parameter keuangan (margin 13,6%) diambil sebagai persentase dari laporan Home Credit Indonesia 2023.
- Gender tidak dipakai sebagai fitur (prinsip perlakuan adil, POJK 22/2023).
- Skor model adalah alat bantu keputusan; keputusan akhir tetap mengikuti kebijakan kredit dan analis.
