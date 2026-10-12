"""Menyiapkan data ringan untuk aplikasi Streamlit (agregat, tanpa data pribadi tingkat nasabah untuk data train)."""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from src.features import load_mart, clean_and_engineer

OUT = Path('app_data'); OUT.mkdir(exist_ok=True)
tr = clean_and_engineer(load_mart('data/processed/mart_v2_train.parquet'))
y = tr['TARGET'].astype(int); base = y.mean()

def seg(dim, s, order=None, min_n=500):
    t = pd.DataFrame({'segmen': s, 'y': y}).dropna().groupby('segmen', observed=True).y.agg(jumlah='count', default_rate='mean').reset_index()
    t = t[t.jumlah >= min_n]
    t['porsi'] = t.jumlah / len(y); t['dimensi'] = dim; t['segmen'] = t.segmen.astype(str)
    if order: t['urutan'] = t.segmen.map({k: i for i, k in enumerate(order)})
    else: t = t.sort_values('default_rate', ascending=False); t['urutan'] = range(len(t))
    return t

parts = []
dec = pd.qcut(tr.EXT_SOURCE_MEAN, 10, labels=[f'D{i}' for i in range(1, 11)])
parts.append(seg('Skor eksternal (desil)', dec, [f'D{i}' for i in range(1, 11)]))
age_o = ['20-25', '25-30', '30-35', '35-40', '40-50', '50-60', '60-70']
parts.append(seg('Usia', pd.cut(tr.AGE_YEARS, [20, 25, 30, 35, 40, 50, 60, 70], labels=age_o), age_o))
emp_o = ['< 1 th', '1-3 th', '3-5 th', '5-10 th', '> 10 th', 'Tidak bekerja']
emp = pd.cut(tr.EMPLOYED_YEARS, [-0.01, 1, 3, 5, 10, 100], labels=emp_o[:-1]).astype(object)
emp[tr.IS_NOT_EMPLOYED == 1] = 'Tidak bekerja'
parts.append(seg('Lama bekerja', emp, emp_o))
parts.append(seg('Jenis pekerjaan', tr.OCCUPATION_TYPE))
edu = {'Lower secondary': 'SMP', 'Secondary / secondary special': 'SMA/SMK', 'Incomplete higher': 'Kuliah (tidak lulus)',
       'Higher education': 'Sarjana', 'Academic degree': 'Gelar akademik'}
parts.append(seg('Pendidikan', tr.NAME_EDUCATION_TYPE.map(edu), list(edu.values()), min_n=100))
inc = {'Working': 'Karyawan', 'Commercial associate': 'Pekerja komersial', 'State servant': 'PNS', 'Pensioner': 'Pensiunan'}
parts.append(seg('Sumber pendapatan', tr.NAME_INCOME_TYPE.map(inc), list(inc.values())))
reg = {1: 'Rating 1 (terbaik)', 2: 'Rating 2', 3: 'Rating 3 (terburuk)'}
parts.append(seg('Rating wilayah', tr.REGION_RATING_CLIENT_W_CITY.map(reg), list(reg.values())))
late_o = ['Tidak pernah', '<= 5%', '5-15%', '> 15%']
parts.append(seg('Riwayat telat bayar (12 bln)', pd.cut(tr.INST_LATE_RATE_12M, [-0.01, 0, 0.05, 0.15, 1], labels=late_o), late_o))
ccu_o = ['0%', '1-30%', '30-60%', '60-90%', '> 90%']
parts.append(seg('Utilisasi kartu kredit', pd.cut(tr.CC_UTILIZATION_MEAN, [-1, 0, 0.3, 0.6, 0.9, 100], labels=ccu_o), ccu_o, min_n=100))
act_o = ['0', '1', '2', '3', '4', '5', '6+']
act = tr.BUREAU_ACTIVE_CNT.clip(upper=6).map(lambda v: '6+' if v == 6 else str(int(v)))
parts.append(seg('Pinjaman aktif di lembaga lain', act.where(tr.HAS_BUREAU == 1), act_o))
parts.append(seg('Jenis kontrak', tr.NAME_CONTRACT_TYPE.map({'Cash loans': 'Pinjaman tunai', 'Revolving loans': 'Revolving'})))
segments = pd.concat(parts, ignore_index=True)
segments.to_parquet(OUT / 'segments.parquet', index=False)

LGD = 0.45
overview = {'jumlah_pengajuan': int(len(y)), 'jumlah_gagal_bayar': int(y.sum()), 'default_rate': float(base),
            'total_kredit': float(tr.AMT_CREDIT.sum()), 'rata2_kredit': float(tr.AMT_CREDIT.mean()),
            'expected_loss_baseline': float((tr.AMT_CREDIT * LGD)[y == 1].sum()), 'LGD': LGD}
json.dump(overview, open(OUT / 'overview.json', 'w'), indent=2)

# Data pemohon baru (application_test) untuk fitur "cari berdasarkan ID"
test = load_mart('data/processed/mart_v2_test.parquet')
test.to_parquet(OUT / 'applicants.parquet', index=False)
print(segments.dimensi.value_counts().to_dict()); print(overview); print('applicants', test.shape)
