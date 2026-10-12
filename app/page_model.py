import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.common import (BLUE, GREEN, INK, MUTED, NAVY, ORANGE, RED, ZONE_COLORS, fmt_num, fmt_pct, kpi, load_artifacts, load_model,
                        load_test_scores, model_placeholder, money, policy_eval, readable, style_fig, threshold_curve_nominal)

st.title('Performa Model & Simulasi Kebijakan')
st.caption('Evaluasi di data test (20% nasabah yang tidak pernah dipakai saat melatih atau memilih model). '
           'Nilai uang dalam unit mata uang dataset: M = miliar, jt = juta.')

art = load_artifacts(); ts = load_test_scores(); model, meta = load_model()
if art is None:
    model_placeholder('halaman performa model'); st.stop()

test = next(r for r in art['metrics'] if r['model'].endswith('(test)'))
T_APP, T_REJ, T_F2 = art['threshold_approve'], art['threshold_reject'], art.get('threshold_f2_max', 0.09)
c = st.columns(5)
kpi(c[0], 'Model terpilih', art['best_model'], 'PR-AUC CV tertinggi dari 4 model')
kpi(c[1], 'PR-AUC', f"{test['PR-AUC']:.3f}", f"{test['PR-AUC'] / art['pr_curve_test']['base_rate']:.1f}× model acak ({art['pr_curve_test']['base_rate']:.3f})")
kpi(c[2], 'ROC-AUC / Gini', f"{test['ROC-AUC']:.3f} / {test['Gini']:.3f}", f"KS {test['KS']:.3f}")
kpi(c[3], 'F2-score', f"{test['F2']:.3f}", f"recall {fmt_pct(test['recall'])} · precision {fmt_pct(test['precision'])}")
kpi(c[4], 'Batas zona', f"{fmt_pct(T_APP, 0)} / {fmt_pct(T_REJ, 0)}", 'approve / reject')

tab_sim, tab_imp, tab_curve, tab_shap = st.tabs(['Simulator kebijakan (nominal)', 'Dampak bisnis', 'Kurva & perbandingan model', 'Faktor risiko (SHAP)'])

# =============================================================================== SIMULATOR
with tab_sim:
    if ts is None:
        st.info('File `app_data/test_scores.parquet` belum ada. Jalankan `python build_policy_data.py` untuk mengaktifkan simulator nominal.')
    else:
        st.caption('Skor simulator berasal dari model yang dilatih ulang di data train saja (build_policy_data.py) agar data test tetap tidak bocor. '
                   'ROC-AUC replikasi 0,788 vs 0,793 di NB 04; selisih kecil karena acak di cross-fitting TargetEncoder, sehingga angka bisa berbeda tipis dari tabel NB 04.')
        st.markdown('Atur batas zona dan asumsi, lalu lihat **berapa uang** yang terselamatkan pada **'
                    f'{fmt_num(len(ts))} pemohon data test** (dengan total pinjaman {money(ts.AMT_CREDIT.sum())}).')
        s = st.columns([1.2, 1.2, 0.8, 1.3])
        t_app = s[0].slider('Batas approve (PD di bawah ini disetujui)', 0.03, 0.40, float(T_APP), 0.005, format='%.3f')
        t_rej = s[1].slider('Batas reject (PD di atas ini ditolak)', 0.03, 0.60, float(max(T_REJ, t_app)), 0.005, format='%.3f')
        t_rej = max(t_rej, t_app)
        lgd = s[2].selectbox('LGD', [0.45, 0.60, 0.75], format_func=lambda v: f'{int(v * 100)}%',
                             help='Loss Given Default. 45% = batas bawah konservatif (NB 01); 60-75% = kisaran pinjaman tanpa agunan.')
        review = s[3].radio('Perlakuan zona Review', ['Ditolak', 'Disetujui, limit dipotong'], horizontal=True,
                            help='Ditolak = sama dengan kebijakan "terpilih" di NB 04. Limit dipotong = skenario what-if.')
        cut = 0.0
        if review != 'Ditolak':
            cut = st.slider('Potongan limit di zona Review (asumsi skenario)', 0.1, 0.9, 0.5, 0.05, format='%.2f')
        r = policy_eval(ts, t_app, t_rej, lgd, review, cut)

        k = st.columns(5)
        kpi(k[0], 'Expected loss tanpa model', money(r['el0']), f"{fmt_num(r['n_def'])} gagal bayar × pinjaman × LGD")
        kpi(k[1], 'Expected loss dengan model', money(r['el']), f"turun {money(r['el_saved'])} ({fmt_pct(r['el_saved'] / r['el0'])})")
        kpi(k[2], 'Keuntungan hilang', money(r['opp']), 'margin dari nasabah baik yang ditolak / dipotong')
        sv = r['saving']
        kpi(k[3], 'Penghematan bersih', ('+' if sv >= 0 else '') + money(sv), f"{fmt_pct(sv / r['el0'])} dari biaya tanpa model")
        kpi(k[4], 'Default rate disetujui', fmt_pct(r['dr_approved'], 2), f"sebelumnya {fmt_pct(r['n_def'] / r['n'], 2)} · disetujui {fmt_pct(r['approved_pct'])}")

        a, b = st.columns([1.15, 1])
        with a:
            fig = go.Figure()
            cats = ['Tanpa model', 'Dengan model']
            fig.add_trace(go.Bar(x=cats, y=[r['el0'] / 1e9, r['el'] / 1e9], name='Expected loss (gagal bayar lolos)', marker_color=RED,
                                 text=[money(r['el0']), money(r['el'])], textposition='inside'))
            fig.add_trace(go.Bar(x=cats, y=[0, r['opp'] / 1e9], name='Keuntungan hilang (nasabah baik ditolak)', marker_color=ORANGE,
                                 text=['', money(r['opp'])], textposition='inside'))
            fig.add_trace(go.Scatter(x=cats, y=[r['el0'] / 1e9, r['total'] / 1e9], mode='text', text=[f"<b>Total {money(r['el0'])}</b>", f"<b>Total {money(r['total'])}</b>"],
                                     textposition='top center', showlegend=False, hoverinfo='skip'))
            fig.update_layout(barmode='stack')
            style_fig(fig, 'Total biaya risiko: sebelum vs sesudah', 'Merah + oranye = total biaya. Makin pendek batang kanan, makin besar penghematan', height=420)
            fig.update_yaxes(title='Miliar (unit mata uang dataset)', range=[0, max(r['el0'], r['total']) / 1e9 * 1.18])
            st.plotly_chart(fig, width='stretch')
        with b:
            z = pd.DataFrame({'zona': ['Approve', 'Review', 'Reject'], 'n': r['zone_n'], 'dr': r['zone_dr'], 'dfl': r['zone_def'], 'el0': r['zone_el0']})
            fig = go.Figure(go.Bar(x=z.zona, y=z.el0 / 1e9, marker_color=[ZONE_COLORS[v] for v in z.zona],
                                   text=[f"{money(e)}<br>{fmt_pct(n / r['n'])} pemohon · DR {fmt_pct(d)}" for e, n, d in zip(z.el0, z.n, z.dr)],
                                   textposition='outside', cliponaxis=False,
                                   hovertemplate='%{x}<br>potensi kerugian %{y:.2f} M<extra></extra>'))
            style_fig(fig, 'Potensi kerugian per zona', 'Pinjaman gagal bayar × LGD di setiap zona (sebelum tindakan)', height=420)
            fig.update_yaxes(title='Miliar', range=[0, z.el0.max() / 1e9 * 1.35])
            st.plotly_chart(fig, width='stretch')

        per = 1000 / r['n']
        st.markdown(f"<div class='note'><b>Cara membaca:</b> tanpa model, gagal bayar yang lolos menimbulkan kerugian <b>{money(r['el0'])}</b>. "
                    f"Dengan batas {t_app:.3f} / {t_rej:.3f}, kerugian itu turun menjadi <b>{money(r['el'])}</b>, tetapi ada keuntungan yang hilang "
                    f"<b>{money(r['opp'])}</b> karena nasabah baik ikut ditolak. Penghematan bersih <b>{money(sv)}</b>, "
                    f"atau sekitar <b>{money(sv * per)}</b> per 1.000 pemohon.</div>", unsafe_allow_html=True)

        cur = threshold_curve_nominal(ts, lgd)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cur.threshold, y=cur.el / 1e9, name='Expected loss', line=dict(color=RED, width=2)))
        fig.add_trace(go.Scatter(x=cur.threshold, y=cur.opp / 1e9, name='Keuntungan hilang', line=dict(color=ORANGE, width=2)))
        fig.add_trace(go.Scatter(x=cur.threshold, y=cur.total / 1e9, name='Total biaya', line=dict(color=INK, width=3)))
        fig.add_hline(y=r['el0'] / 1e9, line_dash='dot', line_color=MUTED, annotation_text='total biaya tanpa model', annotation_position='top right')
        i_min = cur.total.idxmin(); i_f2 = cur.F2.idxmax()
        for (t, lbl, col), yy in zip([(cur.threshold[i_f2], f'F2 tertinggi ({cur.threshold[i_f2]:.3f})', BLUE),
                                      (T_APP, f'batas approve ({T_APP:.3f})', GREEN),
                                      (cur.threshold[i_min], f'biaya minimum ({cur.threshold[i_min]:.3f})', NAVY)], [1.0, 0.9, 0.8]):
            fig.add_vline(x=t, line_dash='dash', line_color=col)
            fig.add_annotation(x=t, y=yy, yref='paper', text=lbl, showarrow=False, xanchor='left', xshift=4, font=dict(color=col, size=11))
        style_fig(fig, f'Biaya nominal di setiap threshold (satu batas, LGD {int(lgd * 100)}%)',
                  'Threshold makin kecil: expected loss turun (merah), tetapi keuntungan hilang naik (oranye). Titik terendah garis hitam = biaya minimum', height=430)
        fig.update_xaxes(title='Threshold (tolak jika PD ≥ nilai ini)', range=[0.02, 0.45]); fig.update_yaxes(title='Miliar', range=[0, 3])
        st.plotly_chart(fig, width='stretch')

        with st.expander('Kenapa batas approve bukan di F2 tertinggi?', expanded=False):
            f2r, gr, mn = cur.loc[i_f2], cur.loc[(cur.threshold - T_APP).abs().idxmin()], cur.loc[i_min]
            tbl = pd.DataFrame({
                'Threshold': [f2r.threshold, gr.threshold, mn.threshold],
                'F2': [f2r.F2, gr.F2, mn.F2], 'Recall': [f2r.recall, gr.recall, mn.recall], 'Ditolak': [f2r.ditolak, gr.ditolak, mn.ditolak],
                'Expected loss': [money(v) for v in (f2r.el, gr.el, mn.el)], 'Keuntungan hilang': [money(v) for v in (f2r.opp, gr.opp, mn.opp)],
                'Total biaya': [money(v) for v in (f2r.total, gr.total, mn.total)],
                'vs tanpa model': [money(r['el0'] - v) for v in (f2r.total, gr.total, mn.total)]},
                index=['F2 tertinggi', 'Terpilih (F2 + guardrail)', 'Biaya minimum'])
            st.dataframe(tbl.style.format({'Threshold': '{:.3f}', 'F2': '{:.3f}', 'Recall': '{:.1%}', 'Ditolak': '{:.1%}'}), width='stretch')
            st.markdown(
                '- **F2 tertinggi** menekan expected loss paling dalam (merah paling kecil), tetapi menolak terlalu banyak nasabah baik, '
                'sehingga keuntungan hilang (oranye) lebih besar daripada kerugian yang dicegah. Total biaya justru **lebih besar** daripada tanpa model.\n'
                '- **Biaya minimum** memberi total biaya terkecil, tetapi recall hanya sekitar sepertiga: dua dari tiga calon gagal bayar tetap lolos, '
                'bertentangan dengan tujuan F2 (menangkap sebanyak mungkin gagal bayar).\n'
                '- Karena itu dipakai **keduanya** dalam kebijakan 3 zona: batas F2 + guardrail menjadi batas **Approve** (recall tetap tinggi), '
                'batas biaya minimum menjadi batas **Reject**. Pemohon di antaranya masuk **Review**, tidak langsung ditolak. '
                'Pilih "Disetujui, limit dipotong" di atas untuk melihat bahwa memotong limit di zona Review memberi penghematan lebih besar daripada menolaknya.')

# =============================================================================== DAMPAK BISNIS
with tab_imp:
    imp = pd.DataFrame(art['impact']).set_index('kebijakan')
    base_el = imp.expected_loss.iloc[0]

    def short(k):
        if k.startswith('Sebelum'): return 'Tanpa model'
        if k.startswith('Aturan'): return 'Aturan skor<br>eksternal'
        num = k[k.find('(') + 1:k.find(')')]
        return ('F2 tertinggi' if 'F2' in k else 'Terpilih' if 'terpilih' in k else 'Biaya minimum') + f'<br>({num})'
    xs = [short(k) for k in imp.index]
    a, b = st.columns(2)
    fig = go.Figure(go.Bar(x=xs, y=imp['default_rate_disetujui_%'], marker_color=[MUTED, BLUE, '#BFBFBF', NAVY, GREEN][:len(imp)],
                           text=[fmt_pct(v / 100, 2) for v in imp['default_rate_disetujui_%']], textposition='outside', cliponaxis=False))
    style_fig(fig, 'Default rate pinjaman yang disetujui', 'Data test · makin rendah makin baik', height=420); fig.update_yaxes(title='%', range=[0, imp['default_rate_disetujui_%'].max() * 1.25])
    a.plotly_chart(fig, width='stretch')
    fig = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=imp.expected_loss / 1e9, name='Expected loss', marker_color=RED, text=[money(v) for v in imp.expected_loss], textposition='inside'))
    fig.add_trace(go.Bar(x=xs, y=imp.keuntungan_hilang / 1e9, name='Keuntungan hilang', marker_color=ORANGE,
                         text=[money(v) if v > 0 else '' for v in imp.keuntungan_hilang], textposition='inside'))
    fig.add_trace(go.Scatter(x=xs, y=imp.total_biaya / 1e9, mode='text', text=[f'<b>{money(v)}</b>' for v in imp.total_biaya],
                             textposition='top center', showlegend=False, hoverinfo='skip'))
    fig.update_layout(barmode='stack')
    style_fig(fig, 'Total biaya per kebijakan (nominal)', 'Merah + oranye = total biaya; angka tebal = total', height=420); fig.update_yaxes(title='Miliar', range=[0, imp.total_biaya.max() / 1e9 * 1.2])
    b.plotly_chart(fig, width='stretch')

    show = pd.DataFrame({
        'Disetujui': imp['disetujui_%'] / 100, 'Default rate disetujui': imp['default_rate_disetujui_%'] / 100,
        'Gagal bayar dicegah': imp.gagal_bayar_dicegah, 'Nasabah baik ditolak': imp.nasabah_baik_ditolak,
        'Expected loss': [money(v) for v in imp.expected_loss], 'Expected loss turun': [money(base_el - v) for v in imp.expected_loss],
        'Keuntungan hilang': [money(v) for v in imp.keuntungan_hilang], 'Total biaya': [money(v) for v in imp.total_biaya],
        'Penghematan bersih': [money(imp.total_biaya.iloc[0] - v) for v in imp.total_biaya], 'Penghematan %': imp['hemat_total_%'] / 100})
    st.dataframe(show.style.format({'Disetujui': '{:.1%}', 'Default rate disetujui': '{:.2%}', 'Gagal bayar dicegah': '{:,.0f}',
                                    'Nasabah baik ditolak': '{:,.0f}', 'Penghematan %': '{:+.1%}'}), width='stretch')
    st.caption(f'Data test: {fmt_num(art["confusion_matrix"][0][0] + sum(art["confusion_matrix"][0][1:]) + sum(art["confusion_matrix"][1]))} pemohon, LGD 45%. '
               'Untuk skala seluruh portofolio, kalikan sekitar 5× (data test = 20% data historis).')

    z = pd.DataFrame(art['zones'])
    st.markdown('**Kebijakan 3 zona (data test)**')
    zc = st.columns(3)
    for col, (_, row) in zip(zc, z.iterrows()):
        key = 'Approve' if row.zona.startswith('Approve') else 'Review' if row.zona.startswith('Review') else 'Reject'
        col.markdown(f"<div class='zone' style='background:{ZONE_COLORS[key]}'><div style='font-size:.8rem;opacity:.9'>{row.zona.upper()}</div>"
                     f"<h3>{fmt_pct(row['porsi_%'] / 100)} pemohon</h3>default rate {fmt_pct(row['default_rate_%'] / 100)} · "
                     f"{fmt_pct(row['porsi_seluruh_gagal_bayar_%'] / 100)} dari seluruh gagal bayar</div>", unsafe_allow_html=True)

# =============================================================================== KURVA
with tab_curve:
    a, b = st.columns(2)
    pr = art['pr_curve_test']
    fig = go.Figure(go.Scatter(x=pr['recall'], y=pr['precision'], mode='lines', line=dict(color=RED, width=2.5), name=art['best_model']))
    fig.add_hline(y=pr['base_rate'], line_dash='dash', line_color=MUTED, annotation_text='model acak')
    style_fig(fig, 'Precision-Recall curve (data test)', 'Makin tinggi kurva, makin baik'); fig.update_xaxes(title='Recall', tickformat='.0%', range=[0, 1])
    fig.update_yaxes(title='Precision', tickformat='.0%', range=[0, 1]); a.plotly_chart(fig, width='stretch')
    roc = art['roc_curve_test']
    fig = go.Figure(go.Scatter(x=roc['fpr'], y=roc['tpr'], mode='lines', line=dict(color=NAVY, width=2.5), name=art['best_model']))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', line=dict(color=MUTED, dash='dash'), name='model acak'))
    style_fig(fig, 'ROC curve (data test)', 'Pembanding standar industri'); fig.update_layout(legend=dict(orientation='v', x=0.55, y=0.1))
    fig.update_xaxes(title='% nasabah lancar ikut ditolak', tickformat='.0%'); fig.update_yaxes(title='Recall', tickformat='.0%')
    b.plotly_chart(fig, width='stretch')
    cmp = pd.DataFrame(art['compare_oof']).set_index('model')[['PR-AUC', 'ROC-AUC', 'Gini', 'KS', 'F2', 'recall', 'precision', 'Brier']]
    st.markdown('**Perbandingan model (prediksi out-of-fold di data train)**')
    st.dataframe(cmp.style.format('{:.4f}', na_rep='-').highlight_max(subset=['PR-AUC', 'ROC-AUC', 'F2'], color='#DCEFE4'), width='stretch')
    seg = pd.DataFrame(art.get('segment_contract', []))
    if not seg.empty:
        st.markdown('**Performa per jenis kontrak (data test)**')
        st.dataframe(seg.set_index('jenis_kontrak').style.format({'jumlah': '{:,.0f}', 'default_rate_%': '{:.2f}', 'PR-AUC': '{:.3f}',
                                                                  'ROC-AUC': '{:.3f}', 'F2': '{:.3f}', 'recall': '{:.1%}'}), width='stretch')

# =============================================================================== SHAP
with tab_shap:
    s = pd.Series(art['shap_importance']).sort_values()
    s.index = [readable(i) for i in s.index]
    fig = go.Figure(go.Bar(x=s.values, y=s.index, orientation='h', marker_color=NAVY, text=[f'{v:.3f}' for v in s.values],
                           textposition='outside', cliponaxis=False))
    style_fig(fig, 'Fitur paling berpengaruh terhadap skor risiko', 'Rata-rata |nilai SHAP| pada sampel data test', height=30 * len(s) + 120)
    fig.update_xaxes(title='Rata-rata |SHAP|'); st.plotly_chart(fig, width='stretch')
    st.markdown('<div class="note"><b>Cara membaca:</b> makin panjang batang, makin besar pengaruh fitur terhadap skor. '
                'Skor eksternal (penilaian lembaga lain) paling dominan, diikuti struktur pinjaman (tenor, cicilan, rasio pinjaman terhadap harga barang) '
                'dan riwayat kredit. Pengaruh per pemohon dapat dilihat di halaman Scoring Pemohon.</div>', unsafe_allow_html=True)
