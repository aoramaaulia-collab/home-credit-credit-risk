import plotly.graph_objects as go
import streamlit as st

from app.common import (BLUE, NAVY, RED, fmt_num, fmt_pct, kpi, load_artifacts, load_overview, load_segments, money, style_fig)
from app.explain import explain_box, guide

ov, seg, art = load_overview(), load_segments(), load_artifacts()
base = ov['default_rate']

st.title('Profil Risiko Portofolio')
st.markdown('Aplikasi ini membantu tim kredit Home Credit **menilai risiko gagal bayar pemohon sejak tahap pengajuan**. '
            'Halaman ini adalah titik awal: gambaran risiko dari **307.511 pengajuan historis**, dan kelompok pemohon mana yang paling '
            'dan paling tidak berisiko. Semua angka berasal dari data historis yang sudah diketahui hasil pembayarannya.')

guide('Isi aplikasi', """
<ul>
<li><b>Profil Risiko Portofolio</b> (halaman ini): siapa yang paling berisiko, dibaca per kelompok.</li>
<li><b>Scoring Pemohon</b>: hitung risiko satu pemohon dan lihat alasannya.</li>
<li><b>Scoring Batch</b>: hitung risiko banyak pemohon sekaligus dari file CSV.</li>
<li><b>Performa & Kebijakan</b>: seberapa akurat model, simulasi batas keputusan, dan dampaknya dalam uang.</li>
<li><b>Tentang</b>: alur proyek, cara kerja keputusan, dan kamus istilah.</li>
</ul>""")

c = st.columns(5)
kpi(c[0], 'Total pengajuan', fmt_num(ov['jumlah_pengajuan']), 'data historis berlabel')
kpi(c[1], 'Default rate', fmt_pct(base), f"{fmt_num(ov['jumlah_gagal_bayar'])} pemohon kesulitan membayar")
kpi(c[2], 'Expected loss historis', money(ov['expected_loss_baseline']), f"pinjaman gagal bayar x LGD {int(ov['LGD'] * 100)}%")
if art:
    m = next(r for r in art['metrics'] if r['model'].endswith('(test)'))
    kpi(c[3], 'Kemampuan model (PR-AUC)', f"{m['PR-AUC']:.3f}", f"{m['PR-AUC'] / base:.1f} kali tebakan acak ({base:.3f})")
    imp = next(r for r in art['impact'] if r['kebijakan'].startswith('Model, terpilih'))
    el_saved = imp['expected_loss_turun_%'] / 100 * ov['expected_loss_baseline']
    kpi(c[4], 'Potensi kerugian dicegah', money(el_saved), f"{fmt_pct(imp['expected_loss_turun_%'] / 100)} dari kerugian historis")
st.caption('Default rate = persentase pemohon yang mengalami kesulitan membayar. Expected loss = perkiraan uang yang hilang dari pinjaman gagal bayar, '
           'dengan asumsi 45% pinjaman tidak kembali (LGD). Nilai uang dalam unit mata uang dataset, M = miliar.')

st.subheader('Siapa yang paling berisiko?')
st.markdown('Pilih tab untuk melihat default rate per kelompok. Setiap grafik dilengkapi penjelasan cara membaca, temuan, dan arti bisnisnya.')

INFO = {
    'Skor eksternal (desil)': ('Skor kelayakan dari lembaga lain dikelompokkan menjadi 10 bagian sama besar (desil). D1 = 10% pemohon dengan skor terendah, D10 = 10% tertinggi.',
        'Desil D1 gagal bayar 22,9%, hampir 3 kali rata-rata; D10 hanya 2,0%. Gabungan D1 dan D2 (20% pemohon) menyumbang 46% seluruh gagal bayar.',
        'Pemohon D1-D2 perlu verifikasi tambahan dan uang muka; D8-D10 layak mendapat jalur persetujuan cepat dan limit lebih tinggi.'),
    'Usia': ('Default rate per kelompok usia pemohon.', 'Risiko turun seiring usia: usia 20-25 tahun 12,3%, usia 60-70 tahun 4,9%.',
        'Pemohon muda tetap bisa dilayani dengan limit awal lebih kecil yang naik bertahap sesuai riwayat bayar. Usia tidak dijadikan alasan penolakan.'),
    'Lama bekerja': ('Default rate menurut lama bekerja di tempat sekarang. "Tidak bekerja" sebagian besar adalah pensiunan.',
        'Masa kerja kurang dari 3 tahun paling berisiko (sekitar 11%), lebih dari 10 tahun hanya 5,2%. Pensiunan justru aman (5,4%) karena penghasilannya tetap.',
        'Untuk masa kerja pendek, minta bukti penghasilan tambahan atau tawarkan tenor lebih pendek.'),
    'Jenis pekerjaan': ('Default rate per jenis pekerjaan, diurutkan dari paling berisiko.', 'Low-skill laborers paling berisiko (17,2%), disusul drivers dan waiters (11,3%); akuntan (4,8%), manajer, dan staf teknis berkeahlian tinggi (6,2%) paling aman.',
        'Segmen berisiko tinggi memerlukan verifikasi penghasilan; segmen aman bisa menjadi target pemasaran.'),
    'Pendidikan': ('Default rate per jenjang pendidikan terakhir.', 'Lulusan sarjana jauh lebih aman (5,4%) dibanding SMP (10,9%), tetapi porsinya baru sekitar 24% pengajuan.',
        'Pendidikan sudah dipakai model; tidak perlu aturan manual terpisah.'),
    'Sumber pendapatan': ('Default rate menurut sumber pendapatan.', 'Pensiunan (5,4%) dan PNS (5,8%) berisiko paling rendah, karyawan swasta 9,6%.',
        'Peluang kerja sama payroll dengan instansi pemerintah dan dana pensiun untuk menambah nasabah berisiko rendah.'),
    'Rating wilayah': ('Default rate per penilaian risiko wilayah tempat tinggal (1 = terbaik, 3 = terburuk).', 'Wilayah rating 3 gagal bayar 11,4%, lebih dari 2 kali wilayah rating 1 (4,8%).',
        'Strategi penagihan dan limit bisa disesuaikan per wilayah.'),
    'Riwayat telat bayar (12 bln)': ('Default rate menurut persentase cicilan Home Credit yang dibayar telat dalam 12 bulan terakhir.',
        'Pemohon yang tidak pernah telat gagal bayar 6,7%; yang telat lebih dari 15% cicilan gagal bayar sekitar 13%.',
        'Perilaku bayar terbaru adalah sinyal kuat; nasabah lama yang sering telat perlu syarat lebih ketat.'),
    'Utilisasi kartu kredit': ('Default rate menurut seberapa penuh limit kartu kredit dipakai.', 'Pemakaian limit di atas 90% berisiko 19,3%, 3,6 kali pemohon yang tidak memakai limitnya.',
        'Limit yang selalu penuh menandakan ketergantungan pada utang: kurangi limit baru atau perpendek tenor.'),
    'Pinjaman aktif di lembaga lain': ('Default rate menurut jumlah pinjaman yang masih berjalan di lembaga keuangan lain.', 'Risiko naik bertahap: 5,7% tanpa pinjaman aktif hingga 13,4% untuk 6 pinjaman atau lebih.',
        'Hitung total beban cicilan dari semua lembaga sebelum menentukan limit.'),
    'Jenis kontrak': ('Default rate pinjaman tunai dibanding revolving.', 'Pinjaman tunai lebih berisiko daripada revolving.',
        'Batas keputusan bisa dibedakan per produk.'),
}
dims = [d for d in INFO if d in set(seg.dimensi)]
tabs = st.tabs(dims)
for tab, d in zip(tabs, dims):
    with tab:
        t = seg[seg.dimensi == d].sort_values('urutan')
        horizontal = len(t) > 8
        mx, mn = t.default_rate.max(), t.default_rate.min()
        colors = ['#C0504A' if v == mx else '#4E8F69' if v == mn else ('#E3A9A5' if v > base else '#C5CCD4') for v in t.default_rate]
        hover = '<b>%{customdata[0]}</b><br>default rate %{customdata[1]}<br>%{customdata[2]} pemohon (%{customdata[3]} dari total)<extra></extra>'
        cd = list(zip(t.segmen, [fmt_pct(v) for v in t.default_rate], [fmt_num(v) for v in t.jumlah], [fmt_pct(v) for v in t.porsi]))
        if horizontal:
            t = t.iloc[::-1]; colors = colors[::-1]; cd = cd[::-1]
            fig = go.Figure(go.Bar(x=t.default_rate * 100, y=t.segmen, orientation='h', marker_color=colors, customdata=cd,
                                   text=[fmt_pct(v) for v in t.default_rate], textposition='outside', cliponaxis=False, hovertemplate=hover))
            fig.add_vline(x=base * 100, line_dash='dash', line_color=NAVY, annotation_text=f'rata-rata {fmt_pct(base)}', annotation_position='bottom right')
            fig.update_xaxes(title='Default rate (%)'); h = 28 * len(t) + 150
        else:
            fig = go.Figure(go.Bar(x=t.segmen, y=t.default_rate * 100, marker_color=colors, customdata=cd,
                                   text=[f'{fmt_pct(v)}<br><span style="font-size:10px">{fmt_pct(p)} pemohon</span>' for v, p in zip(t.default_rate, t.porsi)],
                                   textposition='outside', cliponaxis=False, hovertemplate=hover))
            fig.add_hline(y=base * 100, line_dash='dash', line_color=NAVY, annotation_text=f'rata-rata {fmt_pct(base)}', annotation_position='top right')
            fig.update_yaxes(title='Default rate (%)', range=[0, t.default_rate.max() * 130]); h = 430
        style_fig(fig, f'Default rate per {d.lower()}', 'Merah tua = kelompok paling berisiko, hijau = paling aman, merah muda = di atas rata-rata, abu = di bawah rata-rata', height=h)
        st.plotly_chart(fig, width='stretch')
        apa, temuan, aksi = INFO[d]
        explain_box(apa=apa,
                    cara='Tinggi (atau panjang) batang = persentase pemohon di kelompok itu yang gagal bayar. Garis putus-putus = rata-rata semua pemohon (8,1%). '
                         'Batang di atas garis berarti kelompok itu lebih berisiko dari rata-rata. Arahkan kursor ke batang untuk melihat jumlah pemohonnya.',
                    temuan=temuan, aksi=aksi)
