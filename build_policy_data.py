"""Skor data test (20%) dengan model yang dilatih di data train saja (sama seperti NB 04 Bagian 14),
untuk simulator kebijakan Streamlit dan dashboard Power BI. Model final (dilatih 100% data) tidak dipakai di sini agar tidak bocor."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd, joblib
from sklearn.base import clone
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score
sys.path.insert(0, str(Path(__file__).parent))
from src.features import load_mart, clean_and_engineer

SEED = 42
md = json.load(open('models/model_metadata.json'))
data = clean_and_engineer(load_mart('data/processed/mart_v2_train.parquet'))
X_all = data.drop(columns=['SK_ID_CURR', 'TARGET']); y_all = data['TARGET'].astype(int)
X_tr, X_te, y_tr, y_te = train_test_split(X_all, y_all, test_size=0.20, stratify=y_all, random_state=SEED)
pipe = clone(joblib.load('models/credit_risk_model.joblib'))
pipe.fit(X_tr, y_tr)
p = pipe.predict_proba(X_te)[:, 1]
print('test ROC', roc_auc_score(y_te, p), 'PR', average_precision_score(y_te, p), '| NB04:', md['test_roc_auc'], md['test_pr_auc'])

NIM = md['NIM']
tenor_bln = X_te.AMT_CREDIT / X_te.AMT_ANNUITY
out = pd.DataFrame({
    'SK_ID_CURR': data.loc[X_te.index, 'SK_ID_CURR'].astype(int).values,
    'TARGET': y_te.values, 'PD': p,
    'AMT_CREDIT': X_te.AMT_CREDIT.values, 'AMT_ANNUITY': X_te.AMT_ANNUITY.values, 'AMT_INCOME_TOTAL': X_te.AMT_INCOME_TOTAL.values,
    'TENOR_BULAN': tenor_bln.fillna(tenor_bln.median()).values,
})
out['KEUNTUNGAN_POTENSIAL'] = out.AMT_CREDIT / 2 * NIM * out.TENOR_BULAN / 12      # = biaya jika nasabah baik ditolak
# atribut segmen (untuk analisis per segmen di Power BI)
out['JENIS_KONTRAK'] = X_te.NAME_CONTRACT_TYPE.map({'Cash loans': 'Pinjaman tunai', 'Revolving loans': 'Revolving'}).values
out['DESIL_SKOR_EKSTERNAL'] = pd.qcut(X_te.EXT_SOURCE_MEAN.rank(method='first'), 10, labels=[f'D{i}' for i in range(1, 11)]).astype(str).values
out['KELOMPOK_USIA'] = pd.cut(X_te.AGE_YEARS, [0, 25, 30, 35, 40, 50, 60, 100], labels=['< 25', '25-30', '30-35', '35-40', '40-50', '50-60', '60+']).astype(str).values
out['SUMBER_PENDAPATAN'] = X_te.NAME_INCOME_TYPE.map({'Working': 'Karyawan', 'Commercial associate': 'Pekerja komersial', 'State servant': 'PNS',
                                                     'Pensioner': 'Pensiunan'}).fillna('Lainnya').values
out['PENDIDIKAN'] = X_te.NAME_EDUCATION_TYPE.map({'Lower secondary': 'SMP', 'Secondary / secondary special': 'SMA/SMK', 'Incomplete higher': 'Kuliah (tidak lulus)',
                                                 'Higher education': 'Sarjana', 'Academic degree': 'Sarjana'}).values
out['RATING_WILAYAH'] = X_te.REGION_RATING_CLIENT_W_CITY.map({1: 'Rating 1', 2: 'Rating 2', 3: 'Rating 3'}).values
out['PEKERJAAN'] = X_te.OCCUPATION_TYPE.fillna('Tidak diisi').values
out['SKOR_EKSTERNAL_RATA2'] = X_te.EXT_SOURCE_MEAN.values
Path('app_data').mkdir(exist_ok=True)
out.to_parquet('app_data/test_scores.parquet', index=False)
print(out.shape, out.PD.describe().round(3).to_dict())
