"""Fungsi bersama aplikasi Streamlit: pemuatan data/model, tema grafik, prediksi, dan penjelasan SHAP."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.features import clean_and_engineer  # noqa: E402

DATA_DIR = ROOT / 'app_data'
MODEL_DIR = ROOT / 'models'

# ---------------------------------------------------------------- tema
NAVY, RED, BLUE, GREEN, ORANGE, INK, MUTED, GRID = '#1F3A5F', '#C8553D', '#4A7BA6', '#3E8E6E', '#D9A441', '#2B2B2B', '#7A7A7A', '#E6E6E6'
ZONE_COLORS = {'Approve': GREEN, 'Review': ORANGE, 'Reject': RED}

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1250px;}
.kpi {background: #FFFFFF; border: 1px solid #E4E7EB; border-radius: 10px; padding: 14px 16px; height: 100%;}
.kpi .lbl {font-size: 0.74rem; color: #6B7280; text-transform: uppercase; letter-spacing: .04em;}
.kpi .val {font-size: 1.55rem; font-weight: 700; color: #1F3A5F; margin-top: 2px;}
.kpi .sub {font-size: 0.78rem; color: #6B7280; margin-top: 2px;}
.zone {border-radius: 10px; padding: 18px 20px; color: white;}
.zone h3 {color: white; margin: 0 0 4px 0;}
.note {background: #F4F6F8; border-left: 4px solid #1F3A5F; padding: 10px 14px; border-radius: 6px; font-size: 0.9rem;}
.placeholder {background: #FFF8E6; border: 1px dashed #D9A441; padding: 14px 16px; border-radius: 8px; color: #6B4E00;}
section[data-testid="stSidebar"] .sb-title {font-size: 1.15rem; font-weight: 700; color: #1F3A5F;}
section[data-testid="stSidebar"] .sb-sub {font-size: 0.8rem; color: #6B7280;}
</style>
"""


def kpi(col, label, value, sub=''):
    col.markdown(f'<div class="kpi"><div class="lbl">{label}</div><div class="val">{value}</div><div class="sub">{sub}</div></div>',
                 unsafe_allow_html=True)


def fmt_num(v, d=0):
    return f'{v:,.{d}f}'.replace(',', '#').replace('.', ',').replace('#', '.')


def fmt_pct(v, d=1):
    return fmt_num(v * 100, d) + '%'


def style_fig(fig, title=None, subtitle=None, height=380):
    t = f'<b>{title}</b>' + (f'<br><span style="font-size:12px;color:{MUTED}">{subtitle}</span>' if subtitle else '') if title else None
    fig.update_layout(title=dict(text=t, x=0, xanchor='left', font=dict(size=16, color=INK)) if t else None,
                      height=height, margin=dict(l=10, r=10, t=70 if t else 20, b=10), plot_bgcolor='white', paper_bgcolor='white',
                      font=dict(color=INK, size=12), legend=dict(orientation='h', y=-0.18, x=0))
    fig.update_xaxes(showgrid=False, linecolor='#BFBFBF', ticks='outside', tickcolor='#BFBFBF')
    fig.update_yaxes(showgrid=False, linecolor='#BFBFBF', ticks='outside', tickcolor='#BFBFBF', zeroline=False)
    return fig


# ---------------------------------------------------------------- data & model
@st.cache_data
def load_overview():
    return json.load(open(DATA_DIR / 'overview.json'))


@st.cache_data
def load_segments():
    return pd.read_parquet(DATA_DIR / 'segments.parquet')


@st.cache_data
def load_applicants():
    df = pd.read_parquet(DATA_DIR / 'applicants.parquet')
    ext = [c for c in df.columns if isinstance(df[c].dtype, pd.api.extensions.ExtensionDtype) and pd.api.types.is_numeric_dtype(df[c].dtype)]
    df[ext] = df[ext].astype('float64')
    for c in df.select_dtypes(['object', 'string']).columns:
        df[c] = df[c].astype(object).where(df[c].notna(), np.nan)
    return df


@st.cache_resource
def load_model():
    """Mengembalikan (model, metadata) atau (None, None) jika model belum dilatih (NB 04)."""
    m, meta = MODEL_DIR / 'credit_risk_model.joblib', MODEL_DIR / 'model_metadata.json'
    if not (m.exists() and meta.exists()):
        return None, None
    md = json.load(open(meta))
    required = {'threshold_approve', 'threshold_reject', 'test_pr_auc', 'test_roc_auc', 'test_f2', 'features', 'groups'}
    if not required.issubset(md):        # file model versi lama (sebelum pipeline baru) -> abaikan
        st.session_state['old_model'] = True
        return None, None
    import joblib
    return joblib.load(m), md


@st.cache_data
def load_artifacts():
    p = MODEL_DIR / 'eval_artifacts.json'
    return json.load(open(p)) if p.exists() else None


def model_placeholder(what='fitur ini'):
    if st.session_state.get('old_model'):
        st.markdown('<div class="placeholder"><b>File model di folder <code>models/</code> adalah versi lama</b> (dari run NB 04 sebelum pipeline baru) '
                    'dan tidak cocok dengan fitur saat ini. Jalankan ulang <code>04_modeling.ipynb</code> versi terbaru untuk menimpanya.</div>',
                    unsafe_allow_html=True)
        return
    st.markdown(f'<div class="placeholder"><b>Model belum tersedia.</b> {what.capitalize()} akan aktif setelah NB 04 selesai dijalankan '
                'dan menghasilkan <code>models/credit_risk_model.joblib</code>, <code>models/model_metadata.json</code>, '
                'serta <code>models/eval_artifacts.json</code>.</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- keputusan
def decide(pd_score, meta):
    """Zona keputusan berdasarkan dua threshold dari NB 04 (F2 + guardrail biaya, dan biaya minimum)."""
    t_app, t_rej = meta['threshold_approve'], meta['threshold_reject']
    if pd_score < t_app:
        return 'Approve', 'Setujui sesuai pengajuan. Risiko di bawah batas yang ditetapkan.'
    if pd_score < t_rej:
        return 'Review', 'Review analis kredit. Pertimbangkan limit lebih kecil, uang muka lebih besar, atau dokumen tambahan.'
    return 'Reject', 'Tolak atau tunda. Kerugian yang diperkirakan lebih besar daripada potensi keuntungannya.'


def predict(model, raw_rows: pd.DataFrame) -> np.ndarray:
    X = clean_and_engineer(raw_rows)
    X = X.drop(columns=[c for c in ('SK_ID_CURR', 'TARGET') if c in X.columns])
    return model.predict_proba(X)[:, 1]


# ---------------------------------------------------------------- SHAP
FEATURE_LABELS = {
    'EXT_SOURCE_MEAN': 'Rata-rata skor eksternal', 'EXT_SOURCE_MIN': 'Skor eksternal terendah', 'EXT_SOURCE_1': 'Skor eksternal 1',
    'EXT_SOURCE_2': 'Skor eksternal 2', 'EXT_SOURCE_3': 'Skor eksternal 3', 'EXT_SOURCE_NA_CNT': 'Jumlah skor eksternal kosong',
    'AGE_YEARS': 'Usia', 'EMPLOYED_YEARS': 'Lama bekerja', 'EMPLOYED_TO_AGE': 'Proporsi usia yang dihabiskan bekerja',
    'IS_NOT_EMPLOYED': 'Tidak bekerja / pensiun', 'AMT_CREDIT': 'Jumlah pinjaman', 'AMT_ANNUITY': 'Cicilan',
    'AMT_INCOME_TOTAL': 'Pendapatan', 'ANNUITY_INCOME': 'Cicilan / pendapatan', 'CREDIT_INCOME': 'Pinjaman / pendapatan',
    'CREDIT_GOODS': 'Pinjaman / harga barang', 'HAS_DOWN_PAYMENT': 'Membayar uang muka', 'CREDIT_TERM': 'Tenor (perkiraan)',
    'INCOME_PER_PERSON': 'Pendapatan per anggota keluarga', 'PHONE_CHANGE_YEARS': 'Lama sejak ganti nomor HP',
    'REGISTRATION_YEARS': 'Lama sejak ganti alamat', 'ID_PUBLISH_YEARS': 'Lama sejak ganti KTP',
    'ADDRESS_MISMATCH_CNT': 'Ketidaksesuaian alamat', 'BUREAU_DEBT_INCOME': 'Utang di lembaga lain / pendapatan',
    'OCCUPATION_TYPE': 'Jenis pekerjaan', 'ORGANIZATION_TYPE': 'Sektor tempat kerja', 'NAME_EDUCATION_TYPE': 'Pendidikan',
    'REGION_RATING_CLIENT_W_CITY': 'Rating wilayah', 'INST_LATE_RATE_12M': '% cicilan telat (12 bulan)',
    'INST_DPD_MEAN': 'Rata-rata hari telat bayar', 'INST_DPD_MEAN_12M': 'Rata-rata hari telat (12 bulan)',
    'INST_PAY_DIFF_MEAN_12M': 'Selisih bayar vs tagihan (12 bulan)', 'PREV_REFUSED_RATE': '% pengajuan ditolak',
    'PREV_LAST_REFUSED': 'Pengajuan terakhir ditolak', 'PREV_REFUSED_CNT_12M': 'Penolakan 12 bulan terakhir',
    'BUREAU_ACTIVE_CNT': 'Pinjaman aktif di lembaga lain', 'BUREAU_ACTIVE_DEBT_RATIO': 'Rasio utang aktif (bureau)',
    'BUREAU_DAYS_CREDIT_MEAN': 'Usia rata-rata kredit di bureau', 'BUREAU_DAYS_CREDIT_LAST': 'Kredit bureau terakhir',
    'CC_UTILIZATION_MEAN': 'Utilisasi kartu kredit', 'CC_UTILIZATION_6M': 'Utilisasi kartu kredit (6 bulan)',
    'POS_DPD_RATE_12M': '% bulan menunggak POS (12 bulan)', 'DEF_30_CNT_SOCIAL_CIRCLE': 'Kenalan yang gagal bayar',
    'CODE_GENDER': 'Gender', 'NAME_CONTRACT_TYPE': 'Jenis kontrak', 'DAYS_EMPLOYED': 'Lama bekerja',
}


def readable(name: str) -> str:
    base = name.split('__', 1)[1] if '__' in name else name
    if base.startswith('missingindicator_'):
        col = base.replace('missingindicator_', '')
        return f'{FEATURE_LABELS.get(col, col)} tidak tersedia'
    for col, lbl in sorted(FEATURE_LABELS.items(), key=lambda kv: -len(kv[0])):
        if base == col:
            return lbl
        if base.startswith(col + '_'):
            return f'{lbl}: {base[len(col) + 1:]}'
    return base


@st.cache_resource
def get_explainer(_model):
    import shap
    mdl = _model[-1] if hasattr(_model, 'steps') else _model.named_estimators_['lgbm'][-1]
    try:
        return shap.TreeExplainer(mdl), 'tree'
    except Exception:
        return None, 'none'


def explain_one(model, raw_row: pd.DataFrame, top=10):
    """Kontribusi SHAP untuk satu pemohon, dikembalikan sebagai DataFrame (fitur, kontribusi)."""
    pipe = model if hasattr(model, 'steps') else model.named_estimators_['lgbm']
    explainer, kind = get_explainer(model)
    if explainer is None:
        return None
    X = clean_and_engineer(raw_row).drop(columns=[c for c in ('SK_ID_CURR', 'TARGET') if c in raw_row.columns], errors='ignore')
    Xt = np.asarray(pipe[:-1].transform(X), dtype=float)
    names = pipe.named_steps['prep'].get_feature_names_out()
    vals = explainer.shap_values(Xt)
    vals = vals[1] if isinstance(vals, list) else vals
    vals = vals[0] if vals.ndim == 2 else vals[0, :, 1]
    s = pd.DataFrame({'fitur': [readable(n) for n in names], 'kontribusi': vals})
    s = s.groupby('fitur', as_index=False).kontribusi.sum()
    return s.reindex(s.kontribusi.abs().sort_values(ascending=False).index).head(top)


def shap_bar(contrib: pd.DataFrame, title='Faktor yang paling memengaruhi skor'):
    c = contrib.iloc[::-1]
    fig = go.Figure(go.Bar(x=c.kontribusi, y=c.fitur, orientation='h', marker_color=[RED if v > 0 else BLUE for v in c.kontribusi],
                           text=[f'{v:+.3f}' for v in c.kontribusi], textposition='outside', cliponaxis=False,
                           hovertemplate='%{y}<br>kontribusi %{x:+.3f}<extra></extra>'))
    fig.add_vline(x=0, line_color=INK, line_width=1)
    style_fig(fig, title, 'Merah = menaikkan risiko, biru = menurunkan risiko (nilai SHAP)', height=40 * len(c) + 120)
    fig.update_xaxes(title='Kontribusi terhadap skor risiko')
    return fig


# ---------------------------------------------------------------- nominal uang & simulasi kebijakan
def money(v, unit='auto'):
    """Format nominal dalam unit mata uang dataset: M = miliar, jt = juta."""
    a = abs(v)
    if unit == 'M' or (unit == 'auto' and a >= 1e9):
        return fmt_num(v / 1e9, 2) + ' M'
    if unit == 'jt' or (unit == 'auto' and a >= 1e6):
        return fmt_num(v / 1e6, 1) + ' jt'
    return fmt_num(v)


@st.cache_data
def load_test_scores():
    """Skor data test 20% dari model yang dilatih di data train saja (build_policy_data.py)."""
    p = DATA_DIR / 'test_scores.parquet'
    return pd.read_parquet(p) if p.exists() else None


def policy_eval(ts, t_app, t_rej, lgd=0.45, review='Ditolak', cut=0.0):
    """Hitung dampak kebijakan 3 zona secara nominal.
    expected loss  = pinjaman x LGD untuk gagal bayar yang disetujui (limit ikut dikurangi di zona Review jika dipilih)
    keuntungan hilang = pinjaman/2 x NIM x tenor untuk nasabah baik yang ditolak (atau porsi limit yang dipotong)"""
    y = ts.TARGET.values == 1; p = ts.PD.values; cr = ts.AMT_CREDIT.values; prof = ts.KEUNTUNGAN_POTENSIAL.values
    app_, rev, rej = p < t_app, (p >= t_app) & (p < t_rej), p >= t_rej
    keep = 0.0 if review == 'Ditolak' else 1 - cut          # porsi limit yang tetap diberikan di zona Review
    el = (cr * lgd)[y & app_].sum() + (cr * lgd * keep)[y & rev].sum()
    opp = prof[~y & rej].sum() + (prof * (1 - keep))[~y & rev].sum()
    el0 = (cr * lgd)[y].sum()
    approved = app_ | (rev & (keep > 0))
    return dict(el0=el0, el=el, opp=opp, total=el + opp, saving=el0 - (el + opp), el_saved=el0 - el,
                approved_pct=approved.mean(), dr_approved=y[approved].mean() if approved.any() else np.nan,
                caught=int((y & ~app_).sum()), good_rejected=int((~y & rej).sum() + (~y & rev).sum() * (keep == 0)),
                n=len(y), n_def=int(y.sum()),
                zone_n=[int(app_.sum()), int(rev.sum()), int(rej.sum())],
                zone_dr=[y[m].mean() if m.any() else np.nan for m in (app_, rev, rej)],
                zone_def=[int((y & m).sum()) for m in (app_, rev, rej)],
                zone_el0=[(cr * lgd)[y & m].sum() for m in (app_, rev, rej)])


def threshold_curve_nominal(ts, lgd=0.45, grid=None):
    """Kurva single-threshold (tolak jika PD >= t): expected loss, keuntungan hilang, total biaya (nominal)."""
    grid = np.round(np.arange(0.02, 0.61, 0.005), 3) if grid is None else grid
    y = ts.TARGET.values == 1; p = ts.PD.values; fn = ts.AMT_CREDIT.values * lgd; fp = ts.KEUNTUNGAN_POTENSIAL.values
    rows = []
    for t in grid:
        r = p >= t; tp = (r & y).sum(); fpn = (r & ~y).sum(); fnn = (~r & y).sum()
        prec = tp / max(tp + fpn, 1); rec = tp / max(tp + fnn, 1)
        f2 = 5 * prec * rec / (4 * prec + rec) if prec + rec > 0 else 0
        rows.append(dict(threshold=t, F2=f2, recall=rec, precision=prec, ditolak=r.mean(),
                         el=fn[~r & y].sum(), opp=fp[r & ~y].sum()))
    c = pd.DataFrame(rows); c['total'] = c.el + c.opp; return c
