import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.glossary import glossary_expander

from app.common import (BLUE, GREEN, INK, MUTED, NAVY, ORANGE, RED, ZONE_COLORS, fmt_num, fmt_pct, kpi, load_artifacts, load_model,
                        load_test_scores, model_placeholder, money, policy_eval, readable, style_fig, threshold_curve_nominal)
from app.explain import explain_box, guide, label

st.title('Performa Model & Simulasi Kebijakan')
st.markdown('Halaman ini menjawab tiga pertanyaan: **seberapa baik model membedakan pemohon berisiko**, **berapa uang yang bisa diselamatkan**, '
            'dan **di mana batas keputusan sebaiknya dipasang**. Semua angka dihitung di data uji: 20% pemohon (61.503 orang) yang tidak pernah '
            'dipakai saat melatih atau memilih model, sehingga mencerminkan performa pada pemohon baru. Nilai uang dalam unit mata uang dataset '
            '(M = miliar, jt = juta).')
glossary_expander(['Istilah risiko kredit', 'Istilah keputusan kredit', 'Istilah evaluasi model'], key='kx_model')

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

tab_sim, tab_imp, tab_curve, tab_shap, tab_lim = st.tabs(['Simulator kebijakan (nominal)', 'Dampak bisnis', 'Kurva & perbandingan model',
                                                         'Faktor risiko (SHAP)', 'Keterbatasan & rekomendasi model'])

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
        kpi(k[3], 'Penghematan bersih', ('hemat ' if sv >= 0 else 'rugi ') + money(abs(sv)),
            f"{'lebih hemat' if sv >= 0 else 'lebih mahal'} {fmt_pct(abs(sv) / r['el0'])} dibanding tanpa model")
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
        explain_box(
            apa='Kiri: total biaya risiko sebelum dan sesudah memakai model. Kanan: potensi kerugian (pinjaman gagal bayar x LGD) yang ada di setiap zona keputusan.',
            cara='Batang kiri terdiri dari dua warna: merah = kerugian karena gagal bayar yang tetap disetujui, oranye = margin yang hilang karena nasabah baik ditolak. '
                 'Makin pendek batang "Dengan model" dibanding "Tanpa model", makin besar penghematannya. Di grafik kanan, makin tinggi batang merah (Tolak), makin banyak kerugian yang dihindari.',
            temuan=f"Tanpa model kerugiannya {money(r['el0'])}. Dengan batas {t_app:.3f} / {t_rej:.3f}, kerugian turun menjadi {money(r['el'])}, "
                   f"tetapi margin {money(r['opp'])} ikut hilang. Penghematan bersih {money(sv)} (sekitar {money(sv * per)} per 1.000 pemohon).",
            aksi='Geser slider dan ubah perlakuan zona Review untuk mencari kombinasi yang menekan kerugian tanpa terlalu banyak menolak nasabah baik.')

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
        explain_box(
            apa='Biaya yang terjadi jika semua pemohon dengan probabilitas gagal bayar di atas threshold (sumbu bawah) ditolak.',
            cara='Ikuti garis dari kiri ke kanan. Di kiri (threshold rendah) banyak pemohon ditolak: kerugian gagal bayar (merah) kecil, tetapi margin hilang (oranye) besar. '
                 'Di kanan sebaliknya. Garis hitam adalah jumlah keduanya; titik terendahnya adalah threshold dengan biaya paling kecil. Garis putus-putus abu-abu adalah biaya tanpa model.',
            temuan='Threshold F2 tertinggi berada di kiri titik biaya minimum: menangkap paling banyak gagal bayar, tetapi total biayanya di atas garis tanpa model. '
                   'Batas 12% dipilih karena masih di bawah garis tanpa model sambil tetap menangkap lebih dari separuh gagal bayar.',
            aksi='Batas approve dan batas reject sebaiknya berbeda (kebijakan 3 zona), karena satu batas tidak bisa sekaligus menekan kerugian dan menjaga margin.')

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
    fig = go.Figure(go.Bar(x=xs, y=imp['default_rate_disetujui_%'], marker_color=[NAVY if 'terpilih' in k else '#BFC5CC' for k in imp.index],   # biru tua = kebijakan terpilih, abu = pembanding
                           text=[fmt_pct(v / 100, 2) for v in imp['default_rate_disetujui_%']], textposition='outside', cliponaxis=False))
    style_fig(fig, 'Default rate pinjaman yang disetujui', 'Data test · makin rendah makin baik · biru tua = kebijakan terpilih, abu = pembanding', height=420); fig.update_yaxes(title='%', range=[0, imp['default_rate_disetujui_%'].max() * 1.25])
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
    explain_box(
        apa='Lima kebijakan dibandingkan: tanpa model, aturan sederhana skor eksternal, dan model dengan tiga pilihan threshold.',
        cara='Grafik kiri: makin rendah batang, makin sedikit gagal bayar di antara pinjaman yang disetujui. Grafik kanan: tinggi total batang (merah + oranye) adalah total biaya; '
             'makin rendah makin hemat.',
        temuan='Model menurunkan default rate pinjaman yang disetujui dari 8,07% menjadi 4,34% pada batas 12%, jauh lebih baik daripada aturan skor eksternal (6,34%). '
               'F2 tertinggi paling bersih risikonya, tetapi total biayanya paling mahal karena banyak nasabah baik ikut ditolak.',
        aksi='Pakai batas 12% untuk persetujuan, 22% untuk penolakan, dan kelola pemohon di antaranya dengan limit lebih kecil.')

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
    st.markdown('')
    explain_box(apa='Pembagian pemohon data uji ke tiga zona keputusan berdasarkan probabilitas gagal bayar.',
                cara='Persentase besar = porsi pemohon di zona itu. Default rate = persentase yang benar-benar gagal bayar di zona itu.',
                temuan='Zona Tolak hanya berisi 8% pemohon tetapi menangkap 33% seluruh gagal bayar (default rate 33,6%, lebih dari 4 kali rata-rata). '
                       'Zona Setuju berisi 80% pemohon dengan default rate hanya 4,3%.',
                aksi='Zona Tinjau ulang (12%) adalah tempat analis paling berguna: risikonya dua kali rata-rata, tetapi sebagian besar tetap bisa dilayani dengan syarat lebih ketat.')

# =============================================================================== KURVA
with tab_curve:
    a, b = st.columns(2)
    pr = art['pr_curve_test']
    fig = go.Figure(go.Scatter(x=pr['recall'], y=pr['precision'], mode='lines', line=dict(color=NAVY, width=2.5), name=art['best_model']))
    fig.add_hline(y=pr['base_rate'], line_dash='dash', line_color=MUTED, annotation_text='model acak')
    style_fig(fig, 'Precision-Recall curve (data test)', 'Makin tinggi kurva, makin baik'); fig.update_xaxes(title='Recall', tickformat='.0%', range=[0, 1])
    fig.update_yaxes(title='Precision', tickformat='.0%', range=[0, 1]); a.plotly_chart(fig, width='stretch')
    roc = art['roc_curve_test']
    fig = go.Figure(go.Scatter(x=roc['fpr'], y=roc['tpr'], mode='lines', line=dict(color=NAVY, width=2.5), name=art['best_model']))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', line=dict(color=MUTED, dash='dash'), name='model acak'))
    style_fig(fig, 'ROC curve (data test)', 'Pembanding standar industri'); fig.update_layout(legend=dict(orientation='v', x=0.55, y=0.1))
    fig.update_xaxes(title='% nasabah lancar ikut ditolak', tickformat='.0%'); fig.update_yaxes(title='Recall', tickformat='.0%')
    b.plotly_chart(fig, width='stretch')
    explain_box(
        apa='Kiri: kurva precision-recall. Kanan: kurva ROC. Keduanya menunjukkan kualitas model di semua kemungkinan threshold.',
        cara='PR curve: makin ke kanan berarti makin banyak gagal bayar tertangkap (recall), makin tinggi berarti tolakan makin tepat (precision). '
             'Garis putus-putus = tebakan acak. ROC: makin melengkung ke kiri atas, makin baik model mengurutkan pemohon.',
        temuan='Kurva PR berada jauh di atas garis acak (PR-AUC 0,288 vs 0,081, 3,6 kali lebih baik). Precision turun saat recall dinaikkan: '
               'untuk menangkap 57% gagal bayar, sekitar 1 dari 4 pemohon yang tersaring memang gagal bayar.',
        aksi='Karena precision terbatas, pemohon yang tersaring sebaiknya tidak semuanya ditolak, melainkan sebagian ditinjau ulang.')
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
    explain_box(
        apa='Rata-rata besarnya pengaruh setiap informasi terhadap skor risiko, dihitung dengan metode SHAP pada ribuan pemohon data uji.',
        cara='Makin panjang batang, makin besar pengaruh informasi itu secara umum. Grafik ini tidak menunjukkan arah (naik atau turun); '
             'arah pengaruh untuk satu pemohon bisa dilihat di halaman Scoring Pemohon.',
        temuan='Skor dari lembaga lain paling dominan, diikuti struktur pinjaman (tenor, besar cicilan, pinjaman dibanding harga barang) dan riwayat kredit '
               '(lama riwayat kredit barang, cicilan sebelumnya). Pekerjaan dan sektor tempat kerja juga berpengaruh.',
        aksi='Verifikasi skor eksternal dan struktur pinjaman adalah titik kontrol paling penting dalam proses persetujuan.')


# =============================================================================== KETERBATASAN
with tab_lim:
    st.subheader('Apakah PR-AUC 0,288 dan F2 0,44 itu jelek?')
    st.markdown("""
Sekilas angkanya terlihat kecil, tetapi perlu dibandingkan dengan **titik awalnya**. Hanya 8,1% pemohon yang gagal bayar, sehingga tebakan acak
hanya mendapat PR-AUC 0,081 dan F2 0,305. Model mencapai PR-AUC **0,288 (3,6 kali tebakan acak)** dan ROC-AUC **0,793**, setara solusi kuat
yang pernah dipublikasikan untuk dataset ini (sekitar 0,80). Berbeda dengan kasus seperti pembatalan hotel (sekitar 28% pembatalan),
gagal bayar adalah kejadian langka sehingga precision secara alami rendah.

Berbagai cara peningkatan sudah diuji: menambah fitur baru (+0,001), seleksi fitur otomatis (justru turun 0,002-0,006), menggabungkan model
(+0,0004), memberi bobot kelas (tidak naik, probabilitas jadi kurang akurat), dan tuning luas. Semuanya hanya menggeser hasil sangat kecil.
Artinya model sudah **mendekati batas informasi yang ada di data**; peningkatan berarti memerlukan **data baru**, bukan algoritma yang lebih rumit.
""")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Keterbatasan model")
        st.markdown("""
1. **Batas informasi data.** Data didominasi profil pengajuan dan ringkasan riwayat; tidak ada data transaksi atau pendapatan terverifikasi.
2. **Precision rendah karena gagal bayar langka.** Dari 4 pemohon yang tersaring, 1 benar-benar gagal bayar, walaupun kelompok ini 2,8 kali lebih berisiko dari rata-rata.
3. **Bias seleksi.** Label hanya ada untuk pemohon yang dulu disetujui; profil yang dulu ditolak tidak pernah terlihat hasilnya.
4. **Validasi acak, bukan berdasarkan waktu.** Dataset tidak memiliki tanggal pengajuan, sehingga ketahanan model terhadap perubahan ekonomi belum teruji.
5. **Produk revolving lebih lemah** (PR-AUC 0,224, recall 41%) karena datanya hanya 9%.
6. **Asumsi bisnis.** LGD dan margin adalah perkiraan dari laporan publik; nilai uang dampak bergantung pada asumsi ini.
7. **Ketergantungan pada skor eksternal**, yang merupakan kotak hitam dari lembaga lain.
8. **Keadilan.** Gender tidak dipakai, tetapi variabel yang berkaitan (usia, status keluarga, pekerjaan) masih perlu diaudit.

**Yang sudah aman: kalibrasi.** Kalibrasi sudah dicek (notebook 04 bagian 14.1). Pada 10 kelompok pemohon, kurva kalibrasi menempel garis diagonal dan Brier score di data uji 0,0655. Artinya angka PD bisa dibaca langsung sebagai peluang gagal bayar dan aman dipakai untuk menghitung expected loss, sehingga kalibrasi ulang (isotonic atau Platt) tidak diperlukan. Ini hasil dari keputusan tidak memakai class weight.
""")
    with c2:
        st.markdown("#### Rekomendasi pengembangan model")
        st.markdown("""
1. **Tambah data baru:** riwayat SLIK OJK yang lebih rinci, data alternatif (pembayaran tagihan, e-wallet, telco), dan pendapatan terverifikasi. Ini cara paling efektif menaikkan performa.
2. **Validasi berdasarkan waktu dan monitoring bulanan** (PSI/CSI), lalu latih ulang setiap label 12 bulan tersedia.
3. **Reject inference atau uji coba kecil** pada profil yang biasanya ditolak, agar model belajar dari kelompok itu.
4. **Model atau threshold terpisah per produk** (tunai vs revolving) dan per segmen.
5. **Batasan monotonik** (misalnya skor eksternal naik, risiko harus turun) dan scorecard WOE + Logistic Regression sebagai pembanding yang mudah diaudit.
6. **Tuning Bayesian (Optuna) dan CatBoost** sebagai eksperimen lanjutan.
7. **Fungsi tujuan berbasis profit** memakai LGD dan nilai pinjaman aktual internal.
8. **Audit keadilan** dan alasan penolakan per nasabah dari SHAP.
9. **MLOps:** registri model, API scoring, dan peluncuran bertahap (A/B).
""")
