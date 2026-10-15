"""Menyiapkan data untuk dashboard Power BI dari app_data/test_scores.parquet (hasil build_policy_data.py)."""
import json, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ts = pd.read_parquet(ROOT / 'app_data/test_scores.parquet'); md = json.load(open(ROOT / 'models/model_metadata.json'))
ta, tr = md['threshold_approve'], md['threshold_reject']
ts['ZONA'] = pd.cut(ts.PD, [0, ta, tr, 1.0001], right=False, labels=['Approve', 'Review', 'Reject']).astype(str)
ts['ZONA_URUT'] = ts.ZONA.map({'Approve': 1, 'Review': 2, 'Reject': 3})
ts['DESIL_SKOR_EKSTERNAL'] = ts.DESIL_SKOR_EKSTERNAL.astype(object).where(lambda s: s.notna() & (s != 'nan'), 'Tanpa skor')
ts['DESIL_URUT'] = ts.DESIL_SKOR_EKSTERNAL.map(lambda s: 11 if s == 'Tanpa skor' else int(s[1:]))
ts['USIA_URUT'] = ts.KELOMPOK_USIA.map({'< 25': 1, '25-30': 2, '30-35': 3, '35-40': 4, '40-50': 5, '50-60': 6, '60+': 7}).fillna(8).astype(int)
ts['PENDIDIKAN'] = ts.PENDIDIKAN.fillna('Lainnya')
ts['PENDIDIKAN_URUT'] = ts.PENDIDIKAN.map({'SMP': 1, 'SMA/SMK': 2, 'Kuliah (tidak lulus)': 3, 'Sarjana': 4}).fillna(5).astype(int)
ts['RATING_WILAYAH'] = ts.RATING_WILAYAH.fillna('Tidak diketahui')
vc = ts.PEKERJAAN.value_counts(); ts['PEKERJAAN'] = ts.PEKERJAAN.where(ts.PEKERJAAN.map(vc) >= 300, 'Lainnya')
ts['STATUS'] = ts.TARGET.map({1: 'Gagal bayar', 0: 'Lancar'})
ts[ts.select_dtypes('float32').columns] = ts.select_dtypes('float32').astype('float64')
ts = ts.drop(columns=['SKOR_EKSTERNAL_RATA2']).round({'PD': 6, 'KEUNTUNGAN_POTENSIAL': 2, 'TENOR_BULAN': 2, 'AMT_ANNUITY': 2, 'AMT_CREDIT': 2})
ts.to_csv(Path(__file__).parent / 'data/pemohon_test.csv', index=False)
print(ts.shape, ts.ZONA.value_counts().to_dict()); print(ts.dtypes.to_string())
