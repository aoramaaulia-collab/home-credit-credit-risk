import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.common import (GREEN, INK, MUTED, NAVY, ORANGE, RED, ZONE_COLORS, decide, explain_one, fmt_num, fmt_pct, kpi,
                        load_applicants, load_model, load_overview, model_placeholder, predict, shap_bar, style_fig)

st.title('Scoring Pemohon')
st.caption('Hitung probabilitas gagal bayar (PD) satu pemohon, keputusan yang disarankan, dan alasan di balik skornya.')

model, meta = load_model()
apps, ov = load_applicants(), load_overview()
TEMPLATE = apps.iloc[:0].copy()

mode = st.radio('Sumber data pemohon', ['Pemohon terdaftar (cari ID)', 'Input manual'], horizontal=True)
row = None

# ------------------------------------------------------------------ mode 1: ID
if mode.startswith('Pemohon'):
    st.markdown('Data diambil dari `application_test` beserta seluruh riwayat kreditnya (bureau, pengajuan sebelumnya, cicilan, kartu kredit).')
    c1, c2 = st.columns([3, 1])
    if 'sid' not in st.session_state:
        st.session_state.sid = int(apps.SK_ID_CURR.iloc[0])
    if c2.button('Pilih ID acak', width='stretch'):
        st.session_state.sid = int(apps.SK_ID_CURR.sample(1).iloc[0])
    sid = c1.number_input('SK_ID_CURR', value=st.session_state.sid, step=1, format='%d')
    hit = apps[apps.SK_ID_CURR == sid]
    if hit.empty:
        st.warning('ID tidak ditemukan di data pemohon.')
    else:
        row = hit.copy()
        r = row.iloc[0]
        p = st.columns(4)
        kpi(p[0], 'Pinjaman', fmt_num(r.AMT_CREDIT), r.NAME_CONTRACT_TYPE)
        kpi(p[1], 'Pendapatan', fmt_num(r.AMT_INCOME_TOTAL), str(r.NAME_INCOME_TYPE))
        kpi(p[2], 'Usia', f"{-r.DAYS_BIRTH / 365:.0f} tahun", str(r.NAME_EDUCATION_TYPE))
        kpi(p[3], 'Riwayat', f"{int(r.PREV_CNT) if pd.notna(r.PREV_CNT) else 0} pengajuan", 'di Home Credit sebelumnya')

# ------------------------------------------------------------------ mode 2: manual
else:
    opts = lambda c: sorted(apps[c].dropna().unique().tolist())
    with st.form('manual'):
        st.subheader('Data pengajuan')
        a = st.columns(4)
        contract = a[0].selectbox('Jenis kontrak', opts('NAME_CONTRACT_TYPE'))
        credit = a[1].number_input('Jumlah pinjaman', 10_000.0, 5_000_000.0, 500_000.0, 10_000.0)
        goods = a[2].number_input('Harga barang', 10_000.0, 5_000_000.0, 450_000.0, 10_000.0)
        annuity = a[3].number_input('Cicilan per bulan', 1_000.0, 300_000.0, 25_000.0, 500.0)

        st.subheader('Profil pemohon')
        b = st.columns(4)
        age = b[0].slider('Usia (tahun)', 20, 70, 35)
        income = b[1].number_input('Pendapatan', 20_000.0, 5_000_000.0, 150_000.0, 5_000.0)
        children = b[2].number_input('Jumlah anak', 0, 10, 0)
        fam = b[3].number_input('Jumlah anggota keluarga', 1, 12, 2)
        b2 = st.columns(4)
        edu = b2[0].selectbox('Pendidikan', opts('NAME_EDUCATION_TYPE'), index=opts('NAME_EDUCATION_TYPE').index('Secondary / secondary special'))
        fam_status = b2[1].selectbox('Status pernikahan', opts('NAME_FAMILY_STATUS'))
        housing = b2[2].selectbox('Tempat tinggal', opts('NAME_HOUSING_TYPE'))
        region = b2[3].selectbox('Rating wilayah', [1, 2, 3], index=1, help='1 = terbaik, 3 = terburuk')

        st.subheader('Pekerjaan & stabilitas')
        c = st.columns(4)
        inc_type = c[0].selectbox('Sumber pendapatan', opts('NAME_INCOME_TYPE'))
        occ = c[1].selectbox('Jenis pekerjaan', ['(tidak diisi)'] + opts('OCCUPATION_TYPE'))
        org = c[2].selectbox('Sektor tempat kerja', opts('ORGANIZATION_TYPE'))
        emp = c[3].number_input('Lama bekerja (tahun)', 0.0, 50.0, 3.0, 0.5, help='Isi 0 dan pilih sumber pendapatan Pensioner jika tidak bekerja')
        c2 = st.columns(4)
        phone = c2[0].number_input('Lama sejak ganti nomor HP (tahun)', 0.0, 15.0, 2.0, 0.5)
        own_car = c2[1].selectbox('Punya mobil', ['N', 'Y'])
        own_realty = c2[2].selectbox('Punya rumah', ['Y', 'N'])
        diff_city = c2[3].checkbox('Kota KTP berbeda dengan kota kerja')

        st.subheader('Skor eksternal')
        e = st.columns(3)
        ext = []
        for i, col in enumerate(e):
            na = col.checkbox(f'Skor {i + 1} tidak tersedia', value=(i == 0))
            v = col.slider(f'Skor eksternal {i + 1}', 0.0, 1.0, 0.5, 0.01, disabled=False)
            ext.append(np.nan if na else v)

        with st.expander('Riwayat kredit (opsional; kosongkan jika pemohon baru)'):
            h = st.columns(4)
            has_bureau = h[0].checkbox('Punya riwayat di lembaga lain')
            b_active = h[0].number_input('Pinjaman aktif di lembaga lain', 0, 30, 1)
            b_debt = h[0].number_input('Total utang aktif', 0.0, 1e8, 0.0, 10_000.0)
            b_overdue = h[0].number_input('Tunggakan saat ini', 0.0, 1e7, 0.0, 1_000.0)
            has_prev = h[1].checkbox('Pernah mengajukan di Home Credit')
            p_cnt = h[1].number_input('Jumlah pengajuan sebelumnya', 0, 50, 2)
            p_ref = h[1].slider('% pengajuan ditolak', 0, 100, 0) / 100
            p_last_ref = h[1].checkbox('Pengajuan terakhir ditolak')
            has_inst = h[2].checkbox('Punya riwayat cicilan')
            i_late = h[2].slider('% cicilan telat (12 bulan)', 0, 100, 0) / 100
            i_late_all = h[2].slider('% cicilan telat (semua)', 0, 100, 0) / 100
            has_cc = h[3].checkbox('Punya kartu kredit Home Credit')
            cc_util = h[3].slider('Utilisasi kartu kredit (%)', 0, 150, 30) / 100
        submitted = st.form_submit_button('Hitung skor risiko', type='primary', width='stretch')

    if submitted:
        r = {c: np.nan for c in TEMPLATE.columns}
        r.update(SK_ID_CURR=0, NAME_CONTRACT_TYPE=contract, AMT_CREDIT=credit, AMT_GOODS_PRICE=goods, AMT_ANNUITY=annuity,
                 AMT_INCOME_TOTAL=income, CNT_CHILDREN=children, CNT_FAM_MEMBERS=fam, NAME_EDUCATION_TYPE=edu,
                 NAME_FAMILY_STATUS=fam_status, NAME_HOUSING_TYPE=housing, REGION_RATING_CLIENT=region, REGION_RATING_CLIENT_W_CITY=region,
                 NAME_INCOME_TYPE=inc_type, OCCUPATION_TYPE=np.nan if occ.startswith('(') else occ, ORGANIZATION_TYPE=org,
                 DAYS_BIRTH=-age * 365, DAYS_EMPLOYED=365243 if inc_type in ('Pensioner', 'Unemployed') and emp == 0 else -emp * 365,
                 DAYS_LAST_PHONE_CHANGE=-phone * 365, FLAG_OWN_CAR=own_car, FLAG_OWN_REALTY=own_realty,
                 REG_CITY_NOT_WORK_CITY=int(diff_city), LIVE_CITY_NOT_WORK_CITY=int(diff_city),
                 REG_REGION_NOT_LIVE_REGION=0, REG_REGION_NOT_WORK_REGION=0, LIVE_REGION_NOT_WORK_REGION=0, REG_CITY_NOT_LIVE_CITY=0,
                 EXT_SOURCE_1=ext[0], EXT_SOURCE_2=ext[1], EXT_SOURCE_3=ext[2])
        for k in [c for c in TEMPLATE.columns if c.startswith('FLAG_DOCUMENT')]:
            r[k] = 0
        r['FLAG_DOCUMENT_3'] = 1
        if has_bureau:
            r.update(BUREAU_CNT=max(b_active, 1), BUREAU_ACTIVE_CNT=b_active, BUREAU_ACTIVE_DEBT_SUM=b_debt, BUREAU_OVERDUE_SUM=b_overdue)
        if has_prev:
            r.update(PREV_CNT=p_cnt, PREV_REFUSED_RATE=p_ref, PREV_APPROVED_RATE=1 - p_ref, PREV_LAST_REFUSED=int(p_last_ref))
        if has_inst:
            r.update(INST_CNT=12, INST_LATE_RATE_12M=i_late, INST_LATE_RATE=i_late_all)
        if has_cc:
            r.update(CC_MONTHS_CNT=12, CC_UTILIZATION_MEAN=cc_util, CC_UTILIZATION_6M=cc_util)
        row = pd.DataFrame([r])[TEMPLATE.columns]
        for c in TEMPLATE.columns:
            if pd.api.types.is_numeric_dtype(TEMPLATE[c]):
                row[c] = pd.to_numeric(row[c], errors='coerce')
        st.session_state.manual_row = row
    elif 'manual_row' in st.session_state:
        row = st.session_state.manual_row
    st.caption('Input manual hanya mencakup informasi utama. Riwayat yang tidak diisi dianggap tidak ada / tidak diketahui dan ditangani oleh pipeline (imputasi + penanda kosong).')

# ------------------------------------------------------------------ hasil
if row is not None:
    st.divider()
    if model is None:
        model_placeholder('perhitungan skor dan penjelasan SHAP')
        st.stop()
    pd_score = float(predict(model, row)[0])
    zone, action = decide(pd_score, meta)
    credit_amt = float(row.AMT_CREDIT.iloc[0]); lgd = meta.get('LGD', 0.45)
    el = pd_score * credit_amt * lgd

    left, right = st.columns([1.05, 1])
    with left:
        st.markdown(f'<div class="zone" style="background:{ZONE_COLORS[zone]}"><div style="font-size:.8rem;opacity:.9">KEPUTUSAN YANG DISARANKAN</div>'
                    f'<h3>{zone}</h3><div>{action}</div></div>', unsafe_allow_html=True)
        st.markdown('')
        k = st.columns(3)
        kpi(k[0], 'Probabilitas gagal bayar', fmt_pct(pd_score), f"{pd_score / ov['default_rate']:.1f}× rata-rata portofolio")
        kpi(k[1], 'Expected loss', fmt_num(el), f'PD × pinjaman × LGD {int(lgd * 100)}%')
        kpi(k[2], 'Batas keputusan', f"{fmt_pct(meta['threshold_approve'])} / {fmt_pct(meta['threshold_reject'])}", 'approve / reject')
    with right:
        t_a, t_r, top = meta['threshold_approve'], meta['threshold_reject'], max(0.6, pd_score * 1.15)
        fig = go.Figure()
        for x0, x1, col, lbl in [(0, t_a, GREEN, 'Approve'), (t_a, t_r, ORANGE, 'Review'), (t_r, top, RED, 'Reject')]:
            fig.add_shape(type='rect', x0=x0 * 100, x1=x1 * 100, y0=0, y1=1, fillcolor=col, opacity=0.18, line_width=0)
            fig.add_annotation(x=(x0 + x1) / 2 * 100, y=1.12, text=lbl, showarrow=False, font=dict(color=col, size=12))
        fig.add_trace(go.Scatter(x=[pd_score * 100], y=[0.5], mode='markers+text', marker=dict(size=18, color=INK, symbol='diamond'),
                                 text=[fmt_pct(pd_score)], textposition='bottom center', hoverinfo='skip'))
        fig.add_vline(x=ov['default_rate'] * 100, line_dash='dot', line_color=NAVY,
                      annotation_text=f"rata-rata {fmt_pct(ov['default_rate'])}", annotation_position='bottom right')
        style_fig(fig, 'Posisi skor terhadap zona keputusan', 'Batas zona dari NB 04: F2 dengan guardrail biaya, dan biaya minimum', height=230)
        fig.update_xaxes(range=[0, top * 100], title='Probabilitas gagal bayar (%)'); fig.update_yaxes(visible=False, range=[0, 1.25])
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')

    contrib = explain_one(model, row)
    if contrib is not None:
        st.plotly_chart(shap_bar(contrib, 'Alasan di balik skor pemohon ini'), width='stretch')
        up = contrib[contrib.kontribusi > 0].head(3).fitur.tolist(); down = contrib[contrib.kontribusi < 0].head(3).fitur.tolist()
        st.markdown(f'<div class="note"><b>Ringkasan untuk analis:</b> faktor yang paling <b>menaikkan</b> risiko: {", ".join(up) or "-"}. '
                    f'Faktor yang paling <b>menurunkan</b> risiko: {", ".join(down) or "-"}.</div>', unsafe_allow_html=True)
