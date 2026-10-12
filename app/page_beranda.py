import plotly.graph_objects as go
import streamlit as st

from app.common import (BLUE, NAVY, RED, fmt_num, fmt_pct, kpi, load_artifacts, load_overview, load_segments, money, style_fig)

ov, seg, art = load_overview(), load_segments(), load_artifacts()
base = ov['default_rate']

st.title('Profil Risiko Portofolio')
st.caption('Ringkasan risiko gagal bayar dari 307.511 pengajuan historis (data latih), sebagai dasar kebijakan kredit.')

c = st.columns(5)
kpi(c[0], 'Total pengajuan', fmt_num(ov['jumlah_pengajuan']), 'data historis')
kpi(c[1], 'Default rate', fmt_pct(base), f"{fmt_num(ov['jumlah_gagal_bayar'])} nasabah gagal bayar")
kpi(c[2], 'Expected loss historis', money(ov['expected_loss_baseline']), f"LGD {int(ov['LGD'] * 100)}% · unit mata uang dataset")
if art:
    m = next(r for r in art['metrics'] if r['model'].endswith('(test)'))
    kpi(c[3], 'PR-AUC model (test)', f"{m['PR-AUC']:.3f}", f"model acak = {base:.3f}")
    imp = next(r for r in art['impact'] if r['kebijakan'].startswith('Model, terpilih'))
    el_saved = imp['expected_loss_turun_%'] / 100 * ov['expected_loss_baseline']
    kpi(c[4], 'Expected loss turun', money(el_saved), f"{fmt_pct(imp['expected_loss_turun_%'] / 100)} dari kerugian historis")
else:
    kpi(c[3], 'PR-AUC model', '-', 'menunggu hasil NB 04')
    kpi(c[4], 'Expected loss turun', '-', 'menunggu hasil NB 04')

st.markdown('')
INSIGHT = {
    'Skor eksternal (desil)': 'Pembeda risiko terkuat: desil terendah (D1) gagal bayar hampir 3× rata-rata. 20% pemohon berskor terendah menyumbang 46% seluruh gagal bayar.',
    'Usia': 'Risiko turun seiring usia, tetapi efeknya hilang jika skor eksternal tinggi. Jangan menolak berdasarkan usia.',
    'Lama bekerja': 'Masa kerja kurang dari 3 tahun paling berisiko. Pensiunan justru aman karena berpenghasilan tetap.',
    'Jenis pekerjaan': 'Low-skill laborers paling berisiko; akuntan, staf IT, dan manajer paling aman.',
    'Pendidikan': 'Lulusan sarjana jauh lebih aman, tetapi porsinya baru sekitar 24% dari pengajuan.',
    'Sumber pendapatan': 'PNS dan pensiunan berisiko rendah tetapi porsinya kecil: peluang kemitraan payroll.',
    'Rating wilayah': 'Wilayah rating 3 berisiko lebih dari 2× wilayah rating 1.',
    'Riwayat telat bayar (12 bln)': 'Perilaku bayar 12 bulan terakhir adalah sinyal kuat risiko ke depan.',
    'Utilisasi kartu kredit': 'Limit yang selalu terpakai penuh menandakan ketergantungan pada utang.',
    'Pinjaman aktif di lembaga lain': 'Risiko naik bertahap seiring jumlah pinjaman aktif di lembaga lain.',
    'Jenis kontrak': 'Pinjaman tunai lebih berisiko daripada revolving.',
}
dims = list(INSIGHT)
tabs = st.tabs(dims)
for tab, d in zip(tabs, dims):
    with tab:
        t = seg[seg.dimensi == d].sort_values('urutan')
        horizontal = len(t) > 8
        colors = [RED if v > base else BLUE for v in t.default_rate]
        hover = '<b>%{customdata[0]}</b><br>default rate %{customdata[1]}<br>%{customdata[2]} nasabah (%{customdata[3]})<extra></extra>'
        cd = list(zip(t.segmen, [fmt_pct(v) for v in t.default_rate], [fmt_num(v) for v in t.jumlah], [fmt_pct(v) for v in t.porsi]))
        if horizontal:
            t = t.iloc[::-1]; colors = colors[::-1]; cd = cd[::-1]
            fig = go.Figure(go.Bar(x=t.default_rate * 100, y=t.segmen, orientation='h', marker_color=colors, customdata=cd,
                                   text=[fmt_pct(v) for v in t.default_rate], textposition='outside', cliponaxis=False, hovertemplate=hover))
            fig.add_vline(x=base * 100, line_dash='dash', line_color=NAVY, annotation_text=f'rata-rata {fmt_pct(base)}', annotation_position='bottom right')
            fig.update_xaxes(title='Default rate (%)'); h = 28 * len(t) + 140
        else:
            fig = go.Figure(go.Bar(x=t.segmen, y=t.default_rate * 100, marker_color=colors, customdata=cd,
                                   text=[f'{fmt_pct(v)}<br><span style="font-size:10px">{fmt_pct(p)} nasabah</span>' for v, p in zip(t.default_rate, t.porsi)],
                                   textposition='outside', cliponaxis=False, hovertemplate=hover))
            fig.add_hline(y=base * 100, line_dash='dash', line_color=NAVY, annotation_text=f'rata-rata {fmt_pct(base)}', annotation_position='top right')
            fig.update_yaxes(title='Default rate (%)', range=[0, t.default_rate.max() * 130]); h = 420
        style_fig(fig, f'Default rate per {d.lower()}', 'Merah = di atas rata-rata (lebih berisiko), biru = di bawah rata-rata', height=h)
        st.plotly_chart(fig, width='stretch')
        st.markdown(f'<div class="note"><b>Temuan:</b> {INSIGHT[d]}</div>', unsafe_allow_html=True)
