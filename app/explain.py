"""Penjelasan hasil model untuk orang awam: kamus fitur, nilai tipikal, SHAP per faktor, dan kotak 'cara membaca'."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.common import DATA_DIR, INK, MUTED, clean_and_engineer, fmt_num, fmt_pct, load_applicants, style_fig

UP, DOWN = '#C0504A', '#4E8F69'          # merah = menaikkan risiko, hijau = menurunkan risiko

# --------------------------------------------------------------------------- kamus fitur
# nama: (label, satuan, penjelasan singkat untuk orang awam)
FEAT = {
    'EXT_SOURCE_MEAN': ('Rata-rata skor eksternal', 'score', 'rata-rata penilaian kelayakan dari lembaga lain (0 = buruk, 1 = baik)'),
    'EXT_SOURCE_MIN': ('Skor eksternal terendah', 'score', 'nilai terendah dari tiga skor lembaga lain'),
    'EXT_SOURCE_1': ('Skor eksternal 1', 'score', 'penilaian kelayakan dari lembaga lain, sumber 1'),
    'EXT_SOURCE_2': ('Skor eksternal 2', 'score', 'penilaian kelayakan dari lembaga lain, sumber 2'),
    'EXT_SOURCE_3': ('Skor eksternal 3', 'score', 'penilaian kelayakan dari lembaga lain, sumber 3'),
    'EXT_SOURCE_NA_CNT': ('Jumlah skor eksternal kosong', 'count', 'berapa skor lembaga lain yang tidak tersedia'),
    'AMT_CREDIT': ('Jumlah pinjaman', 'money', 'besar pinjaman yang diajukan'),
    'AMT_ANNUITY': ('Besar cicilan', 'money', 'cicilan per periode'),
    'AMT_INCOME_TOTAL': ('Pendapatan', 'money', 'pendapatan pemohon'),
    'INCOME_PER_PERSON': ('Pendapatan per anggota keluarga', 'money', 'pendapatan dibagi jumlah anggota keluarga'),
    'ANNUITY_INCOME': ('Cicilan dibanding pendapatan', 'pct', 'porsi pendapatan yang terpakai untuk cicilan'),
    'CREDIT_INCOME': ('Pinjaman dibanding pendapatan', 'ratio', 'besar pinjaman dibanding pendapatan'),
    'CREDIT_GOODS': ('Pinjaman dibanding harga barang', 'ratio', 'di atas 1 berarti pinjaman lebih besar dari harga barang (tanpa uang muka)'),
    'HAS_DOWN_PAYMENT': ('Membayar uang muka', 'flag', 'apakah pemohon ikut menanggung sebagian harga barang'),
    'CREDIT_TERM': ('Perkiraan tenor', 'months', 'lama cicilan, dihitung dari pinjaman dibagi cicilan'),
    'AGE_YEARS': ('Usia', 'years', 'usia pemohon'),
    'EMPLOYED_YEARS': ('Lama bekerja', 'years', 'lama bekerja di tempat sekarang'),
    'EMPLOYED_TO_AGE': ('Proporsi usia yang dihabiskan bekerja', 'pct', 'lama bekerja dibanding usia'),
    'IS_NOT_EMPLOYED': ('Tidak bekerja / pensiun', 'flag', 'pemohon tercatat tidak bekerja atau pensiun'),
    'PHONE_CHANGE_YEARS': ('Lama sejak ganti nomor HP', 'years', 'stabilitas kontak'),
    'REGISTRATION_YEARS': ('Lama sejak ganti data alamat', 'years', 'stabilitas tempat tinggal'),
    'ID_PUBLISH_YEARS': ('Lama sejak KTP diterbitkan', 'years', 'stabilitas identitas'),
    'ADDRESS_MISMATCH_CNT': ('Jumlah ketidaksesuaian alamat', 'count', 'alamat KTP, tempat tinggal, dan tempat kerja yang berbeda'),
    'DOC_COUNT': ('Jumlah dokumen pendukung', 'count', 'dokumen yang diserahkan saat pengajuan'),
    'CNT_CHILDREN': ('Jumlah anak', 'count', ''), 'CNT_FAM_MEMBERS': ('Jumlah anggota keluarga', 'count', ''),
    'REGION_RATING_CLIENT_W_CITY': ('Rating wilayah (dengan kota)', 'count', '1 = wilayah terbaik, 3 = paling berisiko'),
    'REGION_POPULATION_RELATIVE': ('Kepadatan penduduk wilayah', 'num', 'makin besar makin padat'),
    'OWN_CAR_AGE': ('Umur mobil', 'years', ''),
    'NAME_CONTRACT_TYPE': ('Jenis kontrak', 'cat', 'pinjaman tunai atau revolving'),
    'NAME_EDUCATION_TYPE': ('Pendidikan', 'cat', ''), 'NAME_INCOME_TYPE': ('Sumber pendapatan', 'cat', ''),
    'NAME_FAMILY_STATUS': ('Status pernikahan', 'cat', ''), 'NAME_HOUSING_TYPE': ('Tempat tinggal', 'cat', ''),
    'NAME_TYPE_SUITE': ('Pendamping saat mengajukan', 'cat', ''),
    'OCCUPATION_TYPE': ('Jenis pekerjaan', 'cat', ''), 'ORGANIZATION_TYPE': ('Sektor tempat kerja', 'cat', ''),
    'FLAG_OWN_CAR': ('Punya mobil', 'cat', ''), 'FLAG_OWN_REALTY': ('Punya rumah', 'cat', ''),
    'DEF_30_CNT_SOCIAL_CIRCLE': ('Kenalan yang telat bayar > 30 hari', 'count', 'jumlah orang di lingkaran sosial yang gagal bayar'),
    'OBS_30_CNT_SOCIAL_CIRCLE': ('Kenalan yang tercatat di sistem', 'count', ''),
    'AMT_REQ_CREDIT_BUREAU_YEAR': ('Pengecekan kredit setahun terakhir', 'count', 'berapa kali riwayat kreditnya dicek lembaga keuangan'),
    'AMT_REQ_CREDIT_BUREAU_QRT': ('Pengecekan kredit 3 bulan terakhir', 'count', ''),
    'HAS_BUREAU': ('Punya riwayat di lembaga lain', 'flag', ''), 'HAS_PREV': ('Pernah mengajukan di Home Credit', 'flag', ''),
    'HAS_CC': ('Punya kartu kredit Home Credit', 'flag', ''),
    'BUREAU_CNT': ('Jumlah pinjaman di lembaga lain', 'count', ''), 'BUREAU_ACTIVE_CNT': ('Pinjaman aktif di lembaga lain', 'count', ''),
    'BUREAU_ACTIVE_DEBT_SUM': ('Total utang aktif di lembaga lain', 'money', ''), 'BUREAU_ACTIVE_CREDIT_SUM': ('Total plafon aktif di lembaga lain', 'money', ''),
    'BUREAU_ACTIVE_DEBT_RATIO': ('Rasio utang aktif terhadap plafon', 'pct', ''), 'BUREAU_DEBT_INCOME': ('Utang di lembaga lain dibanding pendapatan', 'ratio', ''),
    'BUREAU_OVERDUE_SUM': ('Tunggakan di lembaga lain', 'money', ''), 'BUREAU_DAYS_CREDIT_MEAN': ('Rata-rata umur kredit di lembaga lain', 'days', ''),
    'BUREAU_DAYS_CREDIT_LAST': ('Kredit terakhir di lembaga lain', 'days', 'berapa lama sejak kredit terakhir dibuka'),
    'BUREAU_DAYS_ENDDATE_MEAN': ('Rata-rata jatuh tempo kredit lain', 'days', ''),
    'BUREAU_DPD_MONTH_RATE': ('% bulan menunggak di lembaga lain', 'pct', ''), 'BUREAU_DPD_MONTH_RATE_12M': ('% bulan menunggak di lembaga lain (12 bln)', 'pct', ''),
    'PREV_CNT': ('Jumlah pengajuan sebelumnya', 'count', ''), 'PREV_REFUSED_RATE': ('% pengajuan sebelumnya ditolak', 'pct', ''),
    'PREV_APPROVED_RATE': ('% pengajuan sebelumnya disetujui', 'pct', ''), 'PREV_LAST_REFUSED': ('Pengajuan terakhir ditolak', 'flag', ''),
    'PREV_REFUSED_CNT_12M': ('Penolakan 12 bulan terakhir', 'count', ''), 'PREV_AMT_ANNUITY_MEAN': ('Rata-rata cicilan pinjaman sebelumnya', 'money', ''),
    'PREV_AMT_CREDIT_MEAN': ('Rata-rata pinjaman sebelumnya', 'money', ''), 'PREV_CNT_PAYMENT_MEAN': ('Rata-rata tenor pinjaman sebelumnya', 'months', ''),
    'PREV_DAYS_LAST_DECISION': ('Pengajuan terakhir', 'days', 'berapa lama sejak pengajuan terakhir'),
    'PREV_DAYS_LAST_DUE_MAX': ('Jatuh tempo pinjaman sebelumnya', 'days', ''), 'PREV_RATE_DOWN_PAYMENT_MEAN': ('Rata-rata uang muka sebelumnya', 'pct', ''),
    'PREV_HIGH_YIELD_RATE': ('% pinjaman sebelumnya berbunga tinggi', 'pct', ''),
    'INST_CNT': ('Jumlah cicilan yang tercatat', 'count', ''), 'INST_LATE_RATE': ('% cicilan telat (seluruh riwayat)', 'pct', ''),
    'INST_LATE_RATE_12M': ('% cicilan telat (12 bulan)', 'pct', ''), 'INST_DPD_MEAN': ('Rata-rata hari telat bayar', 'num', ''),
    'INST_DPD_MEAN_12M': ('Rata-rata hari telat bayar (12 bulan)', 'num', ''), 'INST_PAYMENT_RATIO_MEAN': ('Rasio pembayaran terhadap tagihan', 'pct', ''),
    'INST_DAYS_LAST': ('Pembayaran cicilan terakhir', 'days', ''), 'INST_UNDERPAY_RATE': ('% cicilan dibayar kurang', 'pct', ''),
    'POS_MONTHS_CNT': ('Lama riwayat kredit barang', 'months', 'jumlah bulan riwayat pinjaman barang (POS)'),
    'POS_INST_FUTURE_MEAN_12M': ('Sisa cicilan kredit barang', 'num', 'rata-rata jumlah cicilan yang masih tersisa'),
    'POS_DPD_RATE_12M': ('% bulan menunggak kredit barang (12 bln)', 'pct', ''), 'POS_COMPLETED_CNT': ('Kredit barang yang sudah lunas', 'count', ''),
    'CC_MONTHS_CNT': ('Lama riwayat kartu kredit', 'months', ''), 'CC_UTILIZATION_MEAN': ('Pemakaian limit kartu kredit', 'pct', ''),
    'CC_UTILIZATION_6M': ('Pemakaian limit kartu (6 bulan)', 'pct', ''), 'CC_UTILIZATION_MAX': ('Pemakaian limit kartu tertinggi', 'pct', ''),
    'CC_DRAWINGS_MEAN': ('Rata-rata penarikan kartu kredit', 'money', ''),
}


def label(f):
    return FEAT.get(f, (f.replace('_', ' ').capitalize(), 'num', ''))[0]


def fmt_value(f, v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return 'tidak tersedia'
    kind = FEAT.get(f, ('', 'num', ''))[1]
    if kind == 'cat' or isinstance(v, str):
        return {'Y': 'Ya', 'N': 'Tidak', 'No': 'Tidak', 'Yes': 'Ya'}.get(str(v), str(v))
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if kind == 'money': return fmt_num(v)
    if kind == 'pct': return fmt_pct(v)
    if kind == 'ratio': return fmt_num(v, 2) + 'x'
    if kind == 'score': return fmt_num(v, 2)
    if kind == 'years': return fmt_num(v, 1) + ' tahun'
    if kind == 'months': return fmt_num(v, 0) + ' bulan'
    if kind == 'days': return fmt_num(abs(v) / 365, 1) + ' tahun'
    if kind == 'flag': return 'Ya' if v >= 0.5 else 'Tidak'
    if kind == 'count': return fmt_num(v, 0)
    return fmt_num(v, 2)


@st.cache_data
def typical_values():
    """Median (angka) / modus (kategori) pemohon di application_test, setelah cleaning & feature engineering."""
    X = clean_and_engineer(load_applicants())
    out = {}
    for c in X.columns:
        s = X[c]
        if pd.api.types.is_numeric_dtype(s):
            out[c] = float(s.median()) if s.notna().any() else np.nan
        else:
            m = s.mode(); out[c] = m.iloc[0] if len(m) else None
    return out


@st.cache_data
def raw_typical_row():
    """Satu baris data mentah berisi nilai tipikal setiap kolom (dasar isian manual)."""
    apps = load_applicants()
    row = {}
    for c in apps.columns:
        s = apps[c]
        if pd.api.types.is_numeric_dtype(s):
            row[c] = s.median() if s.notna().any() else np.nan
        else:
            m = s.dropna().mode(); row[c] = m.iloc[0] if len(m) else np.nan
    return row


# --------------------------------------------------------------------------- SHAP per faktor
@st.cache_resource
def _explainer(_model):
    import shap
    return shap.TreeExplainer(_model[-1])


def base_feature(name, features):
    n = name.split('__', 1)[1] if '__' in name else name
    n = n.replace('missingindicator_', '')
    if n in features:
        return n
    cands = [f for f in features if n.startswith(f + '_')]
    return max(cands, key=len) if cands else n


def explain_applicant(model, meta, raw_row: pd.DataFrame):
    """DataFrame per fitur asli: kontribusi SHAP (log-odds), nilai pemohon, nilai tipikal, arah, kekuatan."""
    X = clean_and_engineer(raw_row).drop(columns=['SK_ID_CURR', 'TARGET'], errors='ignore')
    Xt = np.asarray(model[:-1].transform(X), dtype=float)
    names = model.named_steps['prep'].get_feature_names_out()
    vals = _explainer(model).shap_values(Xt)
    vals = vals[1] if isinstance(vals, list) else vals
    vals = vals[0] if vals.ndim == 2 else vals[0, :, 1]
    feats = meta['features']
    df = pd.DataFrame({'fitur': [base_feature(n, feats) for n in names], 'kontribusi': vals}).groupby('fitur', as_index=False).kontribusi.sum()
    typ = typical_values()
    df['label'] = df.fitur.map(label)
    df['nilai'] = [fmt_value(f, X[f].iloc[0] if f in X.columns else np.nan) for f in df.fitur]
    df['tipikal'] = [fmt_value(f, typ.get(f, np.nan)) for f in df.fitur]
    df['arah'] = np.where(df.kontribusi > 0, 'Menaikkan risiko', 'Menurunkan risiko')
    a = df.kontribusi.abs()
    df['kekuatan'] = np.select([a >= 0.15, a >= 0.05], ['Kuat', 'Sedang'], 'Lemah')
    return df.reindex(a.sort_values(ascending=False).index).reset_index(drop=True)


def shap_chart(contrib: pd.DataFrame, top=10):
    c = contrib.head(top).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=c.kontribusi, y=c.label, orientation='h', marker_color=[UP if v > 0 else DOWN for v in c.kontribusi],
        text=[('risiko naik ' if v > 0 else 'risiko turun ') + fmt_num(abs(v), 2) for v in c.kontribusi], textposition='outside', cliponaxis=False,
        customdata=list(zip(c.nilai, c.tipikal, c.arah)),
        hovertemplate='<b>%{y}</b><br>Nilai pemohon: %{customdata[0]}<br>Nilai tipikal: %{customdata[1]}<br>%{customdata[2]}<extra></extra>'))
    span = max(c.kontribusi.abs().max(), 0.05) * 1.6   # ruang untuk label di kedua sisi
    fig.add_vline(x=0, line_color=INK, line_width=1)
    style_fig(fig, f'{top} faktor yang paling memengaruhi skor pemohon ini',
              'Batang merah ke kanan = menaikkan risiko. Batang hijau ke kiri = menurunkan risiko. Makin panjang, makin besar pengaruhnya.',
              height=44 * len(c) + 140)
    fig.update_xaxes(title='Ke kiri = membuat pemohon lebih aman   |   ke kanan = membuat pemohon lebih berisiko', zeroline=False,
                     range=[-span, span], showticklabels=False)
    fig.update_layout(showlegend=False)
    return fig


def risk_meter(pd_score, t_app, t_rej, avg):
    top = max(0.6, pd_score * 1.15)
    fig = go.Figure()
    for x0, x1, col, lbl in [(0, t_app, '#4E8F69', 'SETUJUI'), (t_app, t_rej, '#D9A23A', 'TINJAU ULANG'), (t_rej, top, '#C0504A', 'TOLAK')]:
        fig.add_shape(type='rect', x0=x0 * 100, x1=x1 * 100, y0=0.35, y1=0.65, fillcolor=col, opacity=0.85, line_width=0)
        fig.add_annotation(x=(x0 + x1) / 2 * 100, y=0.5, text=f'<b>{lbl}</b>', showarrow=False, font=dict(color='white', size=12))
    fig.add_annotation(x=pd_score * 100, y=0.68, ax=0, ay=-38, text=f'<b>Pemohon ini: {fmt_pct(pd_score)}</b>', showarrow=True,
                       arrowhead=2, arrowsize=1.4, arrowcolor=INK, font=dict(size=14, color=INK))
    fig.add_annotation(x=avg * 100, y=0.32, ax=0, ay=34, text=f'Rata-rata semua pemohon: {fmt_pct(avg)}', showarrow=True,
                       arrowhead=0, arrowcolor=MUTED, font=dict(size=11, color=MUTED))
    style_fig(fig, None, None, height=220)
    fig.update_xaxes(range=[0, top * 100], title='Probabilitas gagal bayar (%)', ticksuffix='%')
    fig.update_yaxes(visible=False, range=[0, 1])
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
    return fig


# --------------------------------------------------------------------------- kotak penjelasan
def explain_box(apa=None, cara=None, temuan=None, aksi=None):
    parts = [('Apa yang ditampilkan', apa), ('Cara membaca', cara), ('Temuan', temuan), ('Arti untuk bisnis', aksi)]
    parts = [(h, t) for h, t in parts if t]
    html = ''.join(f'<div class="xb"><div class="xh">{h}</div><div class="xt">{t}</div></div>' for h, t in parts)
    st.markdown(f'<div class="xwrap" style="grid-template-columns: repeat({len(parts)}, 1fr)">{html}</div>', unsafe_allow_html=True)


def guide(title, body):
    st.markdown(f'<div class="guide"><div class="gt">{title}</div>{body}</div>', unsafe_allow_html=True)


CSS_EXTRA = """
<style>
.xwrap {display: grid; gap: 12px; margin: 4px 0 22px 0;}
.xb {background: #F7F8FA; border-radius: 10px; padding: 12px 14px; font-size: 0.93rem; line-height: 1.5;}
.xh {font-size: 0.72rem; font-weight: 700; color: #C8102E; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px;}
.xt {color: #2B3036;}
.guide {background: #FFFFFF; border: 1px solid #E4E7EB; border-radius: 12px; padding: 16px 20px; margin: 6px 0 18px 0; font-size: 0.97rem; line-height: 1.6;}
.guide .gt {font-weight: 700; color: #1F3A5F; margin-bottom: 6px; font-size: 1.02rem;}
.guide ol, .guide ul {margin: 4px 0 0 0; padding-left: 20px;}
.verdict {border-radius: 12px; padding: 18px 22px; color: white; line-height: 1.55;}
.verdict .big {font-size: 1.6rem; font-weight: 800; margin: 2px 0 6px 0;}
@media (max-width: 900px) {.xwrap {grid-template-columns: 1fr !important;}}
</style>
"""
