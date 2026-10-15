import numpy as np
import pandas as pd
import streamlit as st

from app.common import (ZONE_COLORS, decide, fmt_num, fmt_pct, kpi, load_applicants, load_model, load_overview, load_test_scores,
                        model_placeholder, predict)
from app.explain import explain_applicant, explain_box, guide, raw_typical_row, risk_meter, shap_chart

st.title('Scoring Pemohon')
st.markdown('Halaman ini menghitung **seberapa besar kemungkinan seorang pemohon akan kesulitan membayar cicilan** '
            '(probabilitas gagal bayar atau *PD*), memberi saran keputusan, lalu menjelaskan **alasan di balik angkanya** '
            'dalam bahasa sehari-hari.')

guide('Cara memakai halaman ini', """
<ol>
<li><b>Pilih sumber data.</b> <i>Pemohon terdaftar</i> mengambil data lengkap seorang pemohon nyata (termasuk riwayat kreditnya) berdasarkan nomor ID.
<i>Isi manual</i> dipakai untuk mencoba profil pemohon sendiri, misalnya calon nasabah yang sedang mengajukan.</li>
<li><b>Untuk isi manual:</b> isi kolom sesuai data pemohon. Kolom yang tidak Anda ubah otomatis memakai <b>nilai tipikal</b> (nilai tengah pemohon lain),
sehingga hasilnya tetap masuk akal. Arahkan kursor ke ikon tanda tanya untuk penjelasan setiap kolom.</li>
<li><b>Baca hasilnya dari atas ke bawah:</b> saran keputusan, posisi risiko dibanding pemohon lain, lalu faktor-faktor yang menaikkan atau menurunkan risiko.</li>
</ol>""")

model, meta = load_model()
apps, ov, ts = load_applicants(), load_overview(), load_test_scores()
AVG = ov['default_rate']
mode = st.radio('Sumber data pemohon', ['Pemohon terdaftar (cari berdasarkan ID)', 'Isi manual'], horizontal=True)
row = None

# =========================================================================== MODE 1: ID
if mode.startswith('Pemohon'):
    st.caption('Data diambil dari daftar pemohon baru (application_test) beserta riwayat kreditnya: pinjaman di lembaga lain, '
               'pengajuan sebelumnya di Home Credit, catatan cicilan, dan kartu kredit.')
    c1, c2 = st.columns([3, 1])
    if 'sid' not in st.session_state:
        st.session_state.sid = int(apps.SK_ID_CURR.iloc[0])
    if c2.button('Pilih pemohon acak', width='stretch'):
        st.session_state.sid = int(apps.SK_ID_CURR.sample(1).iloc[0])
    sid = c1.number_input('Nomor ID pemohon (SK_ID_CURR)', value=st.session_state.sid, step=1, format='%d')
    hit = apps[apps.SK_ID_CURR == sid]
    if hit.empty:
        st.warning('Nomor ID tidak ditemukan. Klik "Pilih pemohon acak" untuk mencoba contoh.')
    else:
        row = hit.copy(); r = row.iloc[0]
        p = st.columns(4)
        kpi(p[0], 'Jumlah pinjaman', fmt_num(r.AMT_CREDIT), 'Pinjaman tunai' if r.NAME_CONTRACT_TYPE == 'Cash loans' else 'Revolving')
        kpi(p[1], 'Pendapatan', fmt_num(r.AMT_INCOME_TOTAL), str(r.NAME_INCOME_TYPE))
        kpi(p[2], 'Usia', f"{-r.DAYS_BIRTH / 365:.0f} tahun", str(r.NAME_EDUCATION_TYPE))
        kpi(p[3], 'Pengajuan sebelumnya', f"{int(r.PREV_CNT) if pd.notna(r.PREV_CNT) else 0} kali", 'di Home Credit')

# =========================================================================== MODE 2: MANUAL
else:
    st.info('Isian di bawah hanya memuat informasi yang **benar-benar dipakai model**. Gender sengaja tidak ditanyakan karena tidak dipakai '
            '(prinsip perlakuan adil, POJK 22/2023). Penjelasan lengkap hubungan isian dengan fitur model ada di bagian paling bawah formulir.')
    base = raw_typical_row()
    opts = lambda c: sorted(apps[c].dropna().unique().tolist())
    idx = lambda c, v: opts(c).index(v) if v in opts(c) else 0
    with st.form('manual'):
        st.subheader('1. Pinjaman yang diajukan')
        a = st.columns(4)
        contract = a[0].selectbox('Jenis kontrak', opts('NAME_CONTRACT_TYPE'), help='Cash loans = pinjaman tunai dengan cicilan tetap. Revolving = kartu/limit yang bisa dipakai berulang.')
        credit = a[1].number_input('Jumlah pinjaman', 10_000.0, 5_000_000.0, 500_000.0, 10_000.0, help='Besar pinjaman yang diajukan (unit mata uang dataset).')
        goods = a[2].number_input('Harga barang', 10_000.0, 5_000_000.0, 450_000.0, 10_000.0,
                                  help='Harga barang yang dibiayai. Dipakai untuk menghitung rasio pinjaman terhadap harga barang dan apakah pemohon membayar uang muka. '
                                       'Harga barang tidak dimasukkan langsung ke model karena hampir identik dengan jumlah pinjaman.')
        annuity = a[3].number_input('Cicilan per bulan', 1_000.0, 300_000.0, 25_000.0, 500.0, help='Dipakai untuk menghitung tenor (pinjaman dibagi cicilan) dan beban cicilan terhadap pendapatan.')

        st.subheader('2. Profil pemohon')
        b = st.columns(4)
        age = b[0].slider('Usia (tahun)', 20, 70, 35)
        income = b[1].number_input('Pendapatan', 20_000.0, 5_000_000.0, 150_000.0, 5_000.0, help='Pendapatan pemohon per periode yang sama dengan data (unit dataset).')
        children = b[2].number_input('Jumlah anak', 0, 10, 0)
        fam = b[3].number_input('Jumlah anggota keluarga', 1, 12, 2, help='Termasuk pemohon. Dipakai untuk menghitung pendapatan per anggota keluarga.')
        b2 = st.columns(5)
        edu = b2[0].selectbox('Pendidikan', opts('NAME_EDUCATION_TYPE'), index=idx('NAME_EDUCATION_TYPE', 'Secondary / secondary special'))
        fam_status = b2[1].selectbox('Status pernikahan', opts('NAME_FAMILY_STATUS'), index=idx('NAME_FAMILY_STATUS', 'Married'))
        housing = b2[2].selectbox('Tempat tinggal', opts('NAME_HOUSING_TYPE'), index=idx('NAME_HOUSING_TYPE', 'House / apartment'))
        own_car = b2[3].selectbox('Punya mobil', ['N', 'Y'], format_func=lambda v: 'Ya' if v == 'Y' else 'Tidak')
        own_realty = b2[4].selectbox('Punya rumah', ['Y', 'N'], format_func=lambda v: 'Ya' if v == 'Y' else 'Tidak')

        st.subheader('3. Pekerjaan')
        c = st.columns(4)
        inc_type = c[0].selectbox('Sumber pendapatan', opts('NAME_INCOME_TYPE'), index=idx('NAME_INCOME_TYPE', 'Working'))
        occ = c[1].selectbox('Jenis pekerjaan', ['(tidak diisi)'] + opts('OCCUPATION_TYPE'), help='Boleh dikosongkan. Model memperlakukan pekerjaan kosong sebagai kategori tersendiri.')
        org = c[2].selectbox('Sektor tempat kerja', opts('ORGANIZATION_TYPE'), index=idx('ORGANIZATION_TYPE', 'Business Entity Type 3'))
        emp = c[3].number_input('Lama bekerja (tahun)', 0.0, 50.0, 3.0, 0.5, help='Untuk pensiunan atau tidak bekerja: isi 0 dan pilih sumber pendapatan Pensioner/Unemployed.')

        st.subheader('4. Stabilitas dan administrasi')
        d = st.columns(4)
        phone = d[0].number_input('Lama sejak ganti nomor HP (tahun)', 0.0, 15.0, 2.0, 0.5, help='Nomor yang lama tidak berganti menandakan kontak yang stabil dan mudah dihubungi.')
        reg = d[1].number_input('Lama sejak ganti data alamat (tahun)', 0.0, 60.0, 12.0, 0.5, help='Berapa tahun sejak pemohon terakhir mengubah data registrasi alamat.')
        idp = d[2].number_input('Lama sejak KTP diterbitkan (tahun)', 0.0, 25.0, 8.0, 0.5)
        region = d[3].selectbox('Rating wilayah tempat tinggal', [1, 2, 3], index=1, help='Penilaian risiko wilayah (termasuk kota): 1 = terbaik, 3 = paling berisiko.')
        d2 = st.columns(4)
        diff_city = d2[0].checkbox('Kota KTP beda dengan kota kerja', help='Ketidaksesuaian alamat membuat penagihan lebih sulit.')
        docs = d2[1].number_input('Jumlah dokumen pendukung', 0, 5, 1, help='Jumlah dokumen yang diserahkan (fotokopi KTP, slip gaji, dan sebagainya).')

        st.subheader('5. Skor dari lembaga lain (skor eksternal)')
        st.caption('Skor kelayakan kredit dari lembaga lain, skala 0 sampai 1 (makin tinggi makin baik). Ini faktor terkuat di model. Centang "tidak tersedia" bila pemohon belum punya skor dari sumber tersebut.')
        e = st.columns(3); ext = []
        for i, col in enumerate(e):
            na = col.checkbox(f'Skor {i + 1} tidak tersedia', value=(i == 0))
            v = col.slider(f'Skor eksternal {i + 1}', 0.0, 1.0, 0.5, 0.01)
            ext.append(np.nan if na else v)

        st.subheader('6. Riwayat kredit (lewati jika pemohon baru)')
        h = st.columns(4)
        has_bureau = h[0].checkbox('Ada pinjaman di lembaga lain')
        b_active = h[0].number_input('Jumlah pinjaman aktif', 0, 30, 1)
        b_debt = h[0].number_input('Total utang aktif', 0.0, 1e8, 0.0, 10_000.0)
        b_overdue = h[0].number_input('Tunggakan saat ini', 0.0, 1e7, 0.0, 1_000.0)
        has_prev = h[1].checkbox('Pernah mengajukan sebelumnya')
        p_cnt = h[1].number_input('Jumlah pengajuan sebelumnya', 1, 50, 2)
        p_ref = h[1].slider('% pengajuan yang ditolak', 0, 100, 0) / 100
        p_last_ref = h[1].checkbox('Pengajuan terakhir ditolak')
        has_inst = h[2].checkbox('Punya riwayat cicilan')
        i_late = h[2].slider('% cicilan telat (12 bulan terakhir)', 0, 100, 0) / 100
        i_late_all = h[2].slider('% cicilan telat (seluruh riwayat)', 0, 100, 0) / 100
        has_cc = h[3].checkbox('Punya kartu kredit')
        cc_util = h[3].slider('Pemakaian limit kartu (%)', 0, 150, 30, help='Saldo terpakai dibagi limit. Di atas 90% menandakan ketergantungan pada utang.') / 100

        with st.expander('Bagaimana isian ini dipakai model, dan kolom apa yang sengaja tidak ditanyakan'):
            st.markdown("""
| Isian | Fitur yang dihitung model |
|---|---|
| Jumlah pinjaman, cicilan, harga barang, pendapatan | Jumlah pinjaman, besar cicilan, tenor, cicilan/pendapatan, pinjaman/pendapatan, pinjaman/harga barang, uang muka |
| Usia, lama bekerja | Usia, lama bekerja, proporsi usia yang dihabiskan bekerja, status tidak bekerja |
| Jumlah anggota keluarga | Pendapatan per anggota keluarga |
| Lama ganti HP, alamat, KTP | Stabilitas kontak, tempat tinggal, dan identitas |
| Kota KTP berbeda | Jumlah ketidaksesuaian alamat |
| Jumlah dokumen | Jumlah dokumen pendukung |
| Skor eksternal 1-3 | Ketiga skor, rata-rata, nilai terendah, dan jumlah skor yang kosong |
| Riwayat kredit | Pinjaman aktif, utang/pendapatan, tunggakan, penolakan, cicilan telat, pemakaian limit |

**Tidak ditanyakan karena tidak dipakai model:** gender (keadilan), rating wilayah tanpa kota (duplikat), jam dan hari pengajuan
(atribut proses, bukan profil), status nomor HP aktif (hampir semua pemohon sama), dan 20 jenis dokumen satu per satu (sudah diringkas menjadi jumlah dokumen).

**Kolom lain yang dipakai model tetapi tidak ditanyakan** (misalnya data bangunan tempat tinggal atau jumlah pengecekan kredit) diisi
dengan nilai tipikal pemohon lain, sehingga tidak mendorong hasil ke arah mana pun.""")
        submitted = st.form_submit_button('Hitung skor risiko', type='primary', width='stretch')

    if submitted:
        r = dict(base)
        hist_cols = {'BUREAU_': has_bureau, 'PREV_': has_prev, 'INST_': has_inst, 'CC_': has_cc, 'POS_': has_prev}
        for c in list(r):
            for pre, has in hist_cols.items():
                if c.startswith(pre) and not has:
                    r[c] = np.nan
        r.update(SK_ID_CURR=0, NAME_CONTRACT_TYPE=contract, AMT_CREDIT=credit, AMT_GOODS_PRICE=goods, AMT_ANNUITY=annuity,
                 AMT_INCOME_TOTAL=income, CNT_CHILDREN=children, CNT_FAM_MEMBERS=fam, NAME_EDUCATION_TYPE=edu,
                 NAME_FAMILY_STATUS=fam_status, NAME_HOUSING_TYPE=housing, REGION_RATING_CLIENT_W_CITY=region,
                 NAME_INCOME_TYPE=inc_type, OCCUPATION_TYPE=np.nan if occ.startswith('(') else occ, ORGANIZATION_TYPE=org,
                 DAYS_BIRTH=-age * 365, DAYS_EMPLOYED=365243 if inc_type in ('Pensioner', 'Unemployed') and emp == 0 else -emp * 365,
                 DAYS_LAST_PHONE_CHANGE=-phone * 365, DAYS_REGISTRATION=-reg * 365, DAYS_ID_PUBLISH=-idp * 365,
                 FLAG_OWN_CAR=own_car, FLAG_OWN_REALTY=own_realty,
                 REG_CITY_NOT_WORK_CITY=int(diff_city), LIVE_CITY_NOT_WORK_CITY=int(diff_city),
                 REG_REGION_NOT_LIVE_REGION=0, REG_REGION_NOT_WORK_REGION=0, LIVE_REGION_NOT_WORK_REGION=0, REG_CITY_NOT_LIVE_CITY=0,
                 EXT_SOURCE_1=ext[0], EXT_SOURCE_2=ext[1], EXT_SOURCE_3=ext[2])
        flags = sorted([c for c in r if c.startswith('FLAG_DOCUMENT')], key=lambda c: int(c.split('_')[-1]))
        for i, k in enumerate(flags):
            r[k] = 1 if i < docs else 0
        if has_bureau:
            r.update(BUREAU_CNT=max(b_active, r.get('BUREAU_CNT') or 1), BUREAU_ACTIVE_CNT=b_active, BUREAU_ACTIVE_DEBT_SUM=b_debt, BUREAU_OVERDUE_SUM=b_overdue)
        if has_prev:
            r.update(PREV_CNT=p_cnt, PREV_REFUSED_RATE=p_ref, PREV_APPROVED_RATE=1 - p_ref, PREV_LAST_REFUSED=int(p_last_ref))
        if has_inst:
            r.update(INST_LATE_RATE_12M=i_late, INST_LATE_RATE=i_late_all)
        if has_cc:
            r.update(CC_UTILIZATION_MEAN=cc_util, CC_UTILIZATION_6M=cc_util)
        tmpl = apps.iloc[:0]
        row = pd.DataFrame([r])[tmpl.columns]
        for c in tmpl.columns:
            if pd.api.types.is_numeric_dtype(tmpl[c]):
                row[c] = pd.to_numeric(row[c], errors='coerce')
        st.session_state.manual_row = row
    elif 'manual_row' in st.session_state:
        row = st.session_state.manual_row

# =========================================================================== HASIL
if row is not None:
    st.divider()
    if model is None:
        model_placeholder('perhitungan skor dan penjelasan'); st.stop()
    pd_score = float(predict(model, row)[0])
    zone, action = decide(pd_score, meta)
    t_app, t_rej = meta['threshold_approve'], meta['threshold_reject']
    credit_amt = float(row.AMT_CREDIT.iloc[0]); lgd = meta.get('LGD', 0.45)
    el = pd_score * credit_amt * lgd
    pct_rank = float((ts.PD < pd_score).mean()) if ts is not None else None
    per100 = round(pd_score * 100)
    zone_id = {'Approve': 'SETUJUI', 'Review': 'TINJAU ULANG', 'Reject': 'TOLAK'}[zone]

    st.header('Hasil penilaian')
    st.markdown(f'<div class="verdict" style="background:{ZONE_COLORS[zone]}">SARAN KEPUTUSAN<div class="big">{zone_id}</div>{action}</div>',
                unsafe_allow_html=True)
    st.markdown('')
    k = st.columns(4)
    kpi(k[0], 'Probabilitas gagal bayar', fmt_pct(pd_score), f'{fmt_num(pd_score / AVG, 1)} kali rata-rata pemohon ({fmt_pct(AVG)})')
    kpi(k[1], 'Lebih berisiko daripada', fmt_pct(pct_rank, 0) if pct_rank is not None else '-', 'pemohon lain di data uji')
    kpi(k[2], 'Perkiraan kerugian (expected loss)', fmt_num(el), f'PD x pinjaman x LGD {int(lgd * 100)}%')
    kpi(k[3], 'Batas keputusan', f'{fmt_pct(t_app, 0)} / {fmt_pct(t_rej, 0)}', 'setujui di bawah / tolak di atas')

    guide('Apa arti angka ini?', f"""
Probabilitas gagal bayar <b>{fmt_pct(pd_score)}</b> berarti: dari <b>100 pemohon dengan profil serupa</b>, sekitar <b>{per100} orang</b>
diperkirakan akan kesulitan membayar cicilan, dan sekitar {100 - per100} orang akan membayar lancar.
Angka ini bukan vonis untuk satu orang, melainkan ukuran risiko yang dipakai untuk menentukan perlakuan:
di bawah <b>{fmt_pct(t_app, 0)}</b> disarankan disetujui, antara {fmt_pct(t_app, 0)} dan {fmt_pct(t_rej, 0)} ditinjau ulang
(misalnya limit dikurangi atau minta uang muka), dan di atas <b>{fmt_pct(t_rej, 0)}</b> disarankan ditolak.
Perkiraan kerugian <b>{fmt_num(el)}</b> adalah rata-rata uang yang mungkin hilang dari pinjaman ini bila disetujui
(probabilitas gagal bayar x jumlah pinjaman x {int(lgd * 100)}% bagian pinjaman yang diasumsikan tidak kembali).""")

    st.subheader('Posisi pemohon pada skala risiko')
    st.plotly_chart(risk_meter(pd_score, t_app, t_rej, AVG), width='stretch')
    explain_box(
        apa='Garis berwarna adalah skala probabilitas gagal bayar dari 0% (paling aman) ke kanan (paling berisiko), dibagi menjadi tiga zona keputusan.',
        cara=f'Panah hitam menunjukkan posisi pemohon ini. Garis abu-abu kecil di bawah menunjukkan rata-rata semua pemohon ({fmt_pct(AVG)}). '
             'Makin ke kanan panahnya, makin besar risikonya.',
        temuan=f'Pemohon ini berada di zona <b>{zone_id}</b>, dengan risiko {fmt_num(pd_score / AVG, 1)} kali rata-rata. '
               + (f'Ia lebih berisiko daripada {fmt_pct(pct_rank, 0)} pemohon lain.' if pct_rank is not None else ''),
        aksi={'Approve': 'Proses persetujuan normal; limit sesuai pengajuan.',
              'Review': 'Analis meninjau ulang: kurangi limit, perpendek tenor, minta uang muka atau dokumen penghasilan tambahan.',
              'Reject': 'Tolak atau tunda. Perkiraan kerugian lebih besar daripada potensi keuntungan dari pinjaman ini.'}[zone])

    st.subheader('Mengapa skornya seperti ini?')
    contrib = explain_applicant(model, meta, row)
    st.plotly_chart(shap_chart(contrib), width='stretch')
    explain_box(
        apa='Setiap batang adalah satu informasi tentang pemohon (misalnya skor eksternal atau besar cicilan) dan seberapa kuat informasi itu menggeser skor risikonya. '
            'Perhitungan memakai metode SHAP, yang membagi skor akhir menjadi sumbangan masing-masing faktor.',
        cara='Merah ke kanan berarti faktor itu <b>membuat pemohon lebih berisiko</b>; hijau ke kiri berarti faktor itu <b>membuatnya lebih aman</b>. '
             'Makin panjang batang, makin besar pengaruhnya. Arahkan kursor ke batang untuk melihat nilai pemohon dibanding nilai tipikal.',
        temuan='Lihat ringkasan tertulis di bawah grafik.',
        aksi='Faktor merah yang paling panjang adalah hal pertama yang perlu diverifikasi atau dimitigasi oleh analis kredit.')
    up = contrib[contrib.kontribusi > 0].head(3); dn = contrib[contrib.kontribusi < 0].head(3)
    line = lambda r: f'<li><b>{r.label}</b>: nilai pemohon {r.nilai} (tipikal pemohon lain {r.tipikal}), pengaruh {r.kekuatan.lower()}.</li>'
    guide('Ringkasan untuk analis kredit',
          '<b>Yang paling memberatkan (menaikkan risiko):</b><ul>' + ''.join(line(r) for r in up.itertuples()) + '</ul>'
          + '<b>Yang paling meringankan (menurunkan risiko):</b><ul>' + ''.join(line(r) for r in dn.itertuples()) + '</ul>')
    with st.expander('Tabel lengkap 15 faktor teratas'):
        show = contrib.head(15)[['label', 'nilai', 'tipikal', 'arah', 'kekuatan', 'kontribusi']].copy()
        show['kontribusi'] = show.kontribusi.abs()
        show.columns = ['Faktor', 'Nilai pemohon', 'Nilai tipikal', 'Arah pengaruh', 'Kekuatan', 'Besar pengaruh (SHAP)']
        st.dataframe(show.style.format({'Besar pengaruh (SHAP)': '{:.3f}'}), width='stretch', hide_index=True)
    with st.expander('Mengapa satuannya bukan persen?'):
        st.markdown('Model menghitung risiko dalam satuan **log-odds** (skala internal model), lalu mengubahnya menjadi persen di akhir. '
                    'Karena perubahan dari log-odds ke persen tidak lurus (tidak linear), sumbangan setiap faktor tidak bisa dijumlahkan '
                    'langsung dalam persen. Yang penting dibaca adalah **arah** (merah atau hijau) dan **panjang batang** relatif satu sama lain. '
                    'Sebagai patokan: pengaruh di atas 0,15 tergolong kuat, 0,05-0,15 sedang, dan di bawah 0,05 lemah.')
    st.caption('Skor model adalah alat bantu keputusan. Keputusan akhir tetap mengikuti kebijakan kredit dan pertimbangan analis.')
