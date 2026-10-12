import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.common import (ZONE_COLORS, decide, fmt_num, fmt_pct, kpi, load_applicants, load_model, model_placeholder, predict, style_fig)

st.title('Scoring Batch (CSV)')
st.caption('Skor banyak pemohon sekaligus. Format kolom sama dengan data mart (`mart_v2_test`).')

model, meta = load_model()
apps = load_applicants()

c1, c2 = st.columns([2, 1])
up = c1.file_uploader('Unggah file CSV pemohon', type='csv')
use_sample = c2.checkbox('Pakai contoh: 1.000 pemohon dari application_test', value=up is None)
tmpl = io.StringIO(); apps.head(5).to_csv(tmpl, index=False)
c2.download_button('Unduh template CSV', tmpl.getvalue(), 'template_pemohon.csv', 'text/csv', width='stretch')

df = None
if up is not None:
    df = pd.read_csv(up)
    missing = [c for c in apps.columns if c not in df.columns]
    if missing:
        st.info(f'{len(missing)} kolom tidak ada di file dan dianggap kosong (ditangani pipeline).')
        for c in missing:
            df[c] = np.nan
    df = df[apps.columns]
elif use_sample:
    df = apps.sample(1000, random_state=7).reset_index(drop=True)

if df is not None:
    st.write(f'{fmt_num(len(df))} pemohon dimuat.')
    if model is None:
        model_placeholder('scoring batch'); st.dataframe(df.head(20), width='stretch'); st.stop()
    with st.spinner('Menghitung skor...'):
        p = predict(model, df)
    out = pd.DataFrame({'SK_ID_CURR': df.SK_ID_CURR, 'probabilitas_gagal_bayar': p,
                        'zona': [decide(v, meta)[0] for v in p], 'jumlah_pinjaman': df.AMT_CREDIT})
    out['expected_loss'] = out.probabilitas_gagal_bayar * out.jumlah_pinjaman * meta.get('LGD', 0.45)

    k = st.columns(4)
    for col, z in zip(k[:3], ['Approve', 'Review', 'Reject']):
        n = (out.zona == z).sum(); kpi(col, z, fmt_num(n), f'{fmt_pct(n / len(out))} pemohon')
    kpi(k[3], 'Total expected loss', fmt_num(out.expected_loss.sum() / 1e6, 1) + ' jt', 'seluruh batch')

    a, b = st.columns(2)
    fig = go.Figure(go.Histogram(x=out.probabilitas_gagal_bayar * 100, nbinsx=40, marker_color='#4A7BA6'))
    for t, lbl, pos in [(meta['threshold_approve'], 'batas approve', 'top left'), (meta['threshold_reject'], 'batas reject', 'top right')]:
        fig.add_vline(x=t * 100, line_dash='dash', annotation_text=lbl, annotation_position=pos)
    style_fig(fig, 'Sebaran probabilitas gagal bayar', 'Garis putus-putus = batas zona keputusan')
    fig.update_xaxes(title='Probabilitas gagal bayar (%)'); fig.update_yaxes(title='Jumlah pemohon')
    a.plotly_chart(fig, width='stretch')
    zs = out.groupby('zona').agg(jumlah=('SK_ID_CURR', 'size'), el=('expected_loss', 'sum')).reindex(['Approve', 'Review', 'Reject']).fillna(0)
    fig2 = go.Figure(go.Bar(x=zs.index, y=zs.el / 1e6, marker_color=[ZONE_COLORS[z] for z in zs.index],
                            text=[fmt_num(v / 1e6, 1) + ' jt' for v in zs.el], textposition='outside', cliponaxis=False))
    style_fig(fig2, 'Expected loss per zona', 'Total perkiraan kerugian (PD × pinjaman × LGD) di setiap zona')
    fig2.update_yaxes(title='Expected loss (juta)')
    b.plotly_chart(fig2, width='stretch')

    st.dataframe(out.sort_values('probabilitas_gagal_bayar', ascending=False).style.format(
        {'probabilitas_gagal_bayar': '{:.2%}', 'jumlah_pinjaman': '{:,.0f}', 'expected_loss': '{:,.0f}'}), width='stretch', height=360)
    st.download_button('Unduh hasil scoring (CSV)', out.to_csv(index=False), 'hasil_scoring.csv', 'text/csv', type='primary')
