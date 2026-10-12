"""Membangun proyek Power BI (format PBIP: semantic model TMDL + report PBIR) untuk dashboard kebijakan risiko kredit.

Jalankan:  python powerbi/build_pbip.py [folder_data]
Lalu buka powerbi/HomeCreditRisk.pbip di Power BI Desktop.
folder_data default = folder powerbi/data di komputer ini (path absolut dipakai Power Query).
"""
import json
import shutil
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = 'HomeCreditRisk'
DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else str(HERE / 'data')
if not DATA_DIR.endswith(('\\', '/')):
    DATA_DIR += '\\' if '\\' in DATA_DIR else '/'
META = json.load(open(HERE.parent / 'models' / 'model_metadata.json'))
T_APP, T_REJ = META['threshold_approve'], META['threshold_reject']

SM, RP = HERE / f'{NAME}.SemanticModel', HERE / f'{NAME}.Report'
for d in (SM, RP):
    shutil.rmtree(d, ignore_errors=True)

# warna (sama dengan notebook & Streamlit)
# Palet ala Home Credit: merah khas, abu gelap, putih. Hijau/amber hanya untuk makna (baik / perhatian).
HC_RED, DARK, GREY, LIGHT = '#C62F36', '#3A4149', '#6E7781', '#F3F4F6'
DARK = '#3A4149'                                   # teks: abu arang, bukan hitam
SOFT_RED, SOFT_GREEN, SOFT_AMBER, SLATE, BASE = '#C8574F', '#5E9E78', '#DDAE5B', '#6B7A89', '#C5CCD4'
NAVY, RED, BLUE, GREEN, ORANGE, INK, MUTED = SLATE, SOFT_RED, BASE, SOFT_GREEN, SOFT_AMBER, DARK, GREY
FONT = "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"
FONT_B = "'Segoe UI Bold', wf_segoe-ui_bold, helvetica, arial, sans-serif"
FONT_S = "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif"
S = 'https://developer.microsoft.com/json-schemas/fabric'


def write(path: Path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False), encoding='utf-8')


def uid():
    return uuid.uuid4().hex[:20]


# =====================================================================================================================
# 1. SEMANTIC MODEL (TMDL)
# =====================================================================================================================
write(HERE / f'{NAME}.pbip', {'$schema': f'{S}/pbip/pbipProperties/1.0.0/schema.json', 'version': '1.0',
                               'artifacts': [{'report': {'path': f'{NAME}.Report'}}], 'settings': {'enableAutoRecovery': True}})
write(SM / 'definition.pbism', {'$schema': f'{S}/item/semanticModel/definitionProperties/1.0.0/schema.json', 'version': '4.2',
                                'settings': {'qnaEnabled': False}})
write(SM / '.platform', {'$schema': f'{S}/gitIntegration/platformProperties/2.0.0/schema.json',
                         'metadata': {'type': 'SemanticModel', 'displayName': NAME}, 'config': {'version': '2.0', 'logicalId': str(uuid.uuid4())}})

def quote(n):
    return n if n.replace('_', '').isalnum() else "'" + n.replace("'", "''") + "'"


TABLES = ['Pemohon', 'Batas Approve', 'Batas Reject', 'LGD', 'Limit Review', 'Skenario', 'Kurva Threshold']
write(SM / 'definition/database.tmdl', 'database\n\tcompatibilityLevel: 1600\n')
write(SM / 'definition/model.tmdl', '\n'.join([
    'model Model', '\tculture: en-US', '\tdefaultPowerBIDataSourceVersion: powerBI_V3', '\tdiscourageImplicitMeasures',
    '\tsourceQueryCulture: en-US', '\tdataAccessOptions', '\t\tlegacyRedirects', '\t\treturnErrorValuesAsNull', '',
    'annotation PBI_QueryOrder = ["DataFolder","Pemohon"]', '',
    *[f'ref table {quote(t)}' for t in TABLES], '']))
write(SM / 'definition/expressions.tmdl',
      f'expression DataFolder = "{DATA_DIR}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
      '\tannotation PBI_ResultType = Text\n')

# ---------------------------------------------------------------- tabel fakta
COLS = [  # nama, tipe TMDL, tipe M, format, summarize, sortBy
    ('SK_ID_CURR', 'int64', 'Int64.Type', '0', 'none', None), ('TARGET', 'int64', 'Int64.Type', '0', 'sum', None),
    ('PD', 'double', 'type number', '0.0%', 'none', None), ('AMT_CREDIT', 'double', 'type number', '#,0', 'sum', None),
    ('AMT_ANNUITY', 'double', 'type number', '#,0', 'sum', None), ('AMT_INCOME_TOTAL', 'double', 'type number', '#,0', 'sum', None),
    ('TENOR_BULAN', 'double', 'type number', '0.0', 'none', None), ('KEUNTUNGAN_POTENSIAL', 'double', 'type number', '#,0', 'sum', None),
    ('JENIS_KONTRAK', 'string', 'type text', None, 'none', None), ('DESIL_SKOR_EKSTERNAL', 'string', 'type text', None, 'none', 'DESIL_URUT'),
    ('KELOMPOK_USIA', 'string', 'type text', None, 'none', 'USIA_URUT'), ('SUMBER_PENDAPATAN', 'string', 'type text', None, 'none', None),
    ('PENDIDIKAN', 'string', 'type text', None, 'none', 'PENDIDIKAN_URUT'), ('RATING_WILAYAH', 'string', 'type text', None, 'none', None),
    ('PEKERJAAN', 'string', 'type text', None, 'none', None), ('ZONA', 'string', 'type text', None, 'none', 'ZONA_URUT'),
    ('ZONA_URUT', 'int64', 'Int64.Type', '0', 'none', None), ('DESIL_URUT', 'int64', 'Int64.Type', '0', 'none', None),
    ('USIA_URUT', 'int64', 'Int64.Type', '0', 'none', None), ('PENDIDIKAN_URUT', 'int64', 'Int64.Type', '0', 'none', None),
    ('STATUS', 'string', 'type text', None, 'none', None),
]
HIDDEN = {'ZONA_URUT', 'DESIL_URUT', 'USIA_URUT', 'PENDIDIKAN_URUT', 'AMT_ANNUITY', 'TENOR_BULAN'}

# Measure: (nama, format, folder, deskripsi, DAX)
F_MONEY, F_PCT, F_PCT2, F_INT = '#,0.00" M";-#,0.00" M"', '0.0%', '0.00%', '#,0'
VARS = 'VAR ta = [Batas Approve Aktif]\nVAR tr = [Batas Reject Aktif]\nVAR k = [Limit Review Aktif]\nVAR lgd = [LGD Aktif]'
MEASURES = [
    # parameter
    ('Batas Approve Aktif', '0.0%', '0 Parameter', 'Batas approve dari slicer (default hasil NB 04)', f"SELECTEDVALUE('Batas Approve'[Batas Approve], {round(T_APP*100)}) / 100"),
    ('Batas Reject Aktif', '0.0%', '0 Parameter', 'Batas reject dari slicer, minimal sama dengan batas approve',
     f"MAX(SELECTEDVALUE('Batas Reject'[Batas Reject], {round(T_REJ*100)}) / 100, [Batas Approve Aktif])"),
    ('LGD Aktif', '0%', '0 Parameter', 'Loss Given Default dari slicer (default 45%)', "SELECTEDVALUE('LGD'[LGD], 45) / 100"),
    ('Limit Review Aktif', '0%', '0 Parameter', 'Porsi limit yang tetap diberikan di zona Review. 0% = Review ditolak', "SELECTEDVALUE('Limit Review'[Limit Review], 0) / 100"),
    # portofolio
    ('Jumlah Pemohon', F_INT, '1 Portofolio', 'Jumlah pemohon', 'COUNTROWS(Pemohon)'),
    ('Jumlah Gagal Bayar', F_INT, '1 Portofolio', 'Jumlah pemohon yang gagal bayar', 'SUM(Pemohon[TARGET])'),
    ('Default Rate', F_PCT, '1 Portofolio', 'Persentase gagal bayar', 'DIVIDE([Jumlah Gagal Bayar], [Jumlah Pemohon])'),
    ('Rata-rata PD', F_PCT, '1 Portofolio', 'Rata-rata probabilitas gagal bayar dari model', 'AVERAGE(Pemohon[PD])'),
    ('Total Pinjaman', F_MONEY, '1 Portofolio', 'Total nilai pinjaman', 'SUM(Pemohon[AMT_CREDIT]) / 1e9'),
    ('Porsi Pemohon', F_PCT, '1 Portofolio', 'Porsi pemohon terhadap seluruh pemohon (mengikuti slicer lain)',
     'DIVIDE([Jumlah Pemohon], CALCULATE([Jumlah Pemohon], ALLSELECTED(Pemohon[ZONA])))'),
    ('Porsi Gagal Bayar', F_PCT, '1 Portofolio', 'Porsi gagal bayar segmen ini dari seluruh gagal bayar',
     'DIVIDE([Jumlah Gagal Bayar], CALCULATE([Jumlah Gagal Bayar], ALLSELECTED(Pemohon[ZONA])))'),
    ('Potensi Kerugian', F_MONEY, '1 Portofolio', 'Pinjaman gagal bayar x LGD (sebelum tindakan)',
     'CALCULATE(SUM(Pemohon[AMT_CREDIT]), Pemohon[TARGET] = 1) * [LGD Aktif] / 1e9'),
    # kebijakan (nominal)
    ('Expected Loss Tanpa Model', F_MONEY, '2 Kebijakan', 'Kerugian jika semua pengajuan disetujui: pinjaman gagal bayar x LGD', '[Potensi Kerugian]'),
    ('Expected Loss Dengan Model', F_MONEY, '2 Kebijakan', 'Kerugian dari gagal bayar yang tetap disetujui (zona Review mengikuti porsi limit)',
     f"{VARS}\nRETURN\n    SUMX(\n        FILTER(Pemohon, Pemohon[TARGET] = 1 && Pemohon[PD] < tr),\n        Pemohon[AMT_CREDIT] * lgd * IF(Pemohon[PD] < ta, 1, k)\n    ) / 1e9"),
    ('Keuntungan Hilang', F_MONEY, '2 Kebijakan', 'Margin yang hilang dari nasabah baik yang ditolak atau limitnya dipotong',
     f"{VARS}\nRETURN\n    SUMX(\n        FILTER(Pemohon, Pemohon[TARGET] = 0 && Pemohon[PD] >= ta),\n        Pemohon[KEUNTUNGAN_POTENSIAL] * IF(Pemohon[PD] >= tr, 1, 1 - k)\n    ) / 1e9"),
    ('Total Biaya Dengan Model', F_MONEY, '2 Kebijakan', 'Expected loss + keuntungan hilang', '[Expected Loss Dengan Model] + [Keuntungan Hilang]'),
    ('Expected Loss Dicegah', F_MONEY, '2 Kebijakan', 'Selisih expected loss tanpa dan dengan model', '[Expected Loss Tanpa Model] - [Expected Loss Dengan Model]'),
    ('Expected Loss Turun %', F_PCT, '2 Kebijakan', 'Persentase expected loss yang dicegah', 'DIVIDE([Expected Loss Dicegah], [Expected Loss Tanpa Model])'),
    ('Penghematan Bersih', F_MONEY, '2 Kebijakan', 'Total biaya tanpa model dikurangi total biaya dengan model', '[Expected Loss Tanpa Model] - [Total Biaya Dengan Model]'),
    ('Penghematan Bersih %', '+0.0%;-0.0%;0.0%', '2 Kebijakan', 'Penghematan bersih dibanding total biaya tanpa model',
     'DIVIDE([Penghematan Bersih], [Expected Loss Tanpa Model])'),
    ('Penghematan per 1.000 Pemohon', '#,0', '2 Kebijakan', 'Penghematan bersih dibagi jumlah pemohon x 1.000', 'DIVIDE([Penghematan Bersih] * 1e9, [Jumlah Pemohon]) * 1000'),
    ('Pemohon Disetujui', F_INT, '2 Kebijakan', 'Approve + Review (jika limit Review > 0%)',
     f"{VARS}\nRETURN\n    COUNTROWS(FILTER(Pemohon, Pemohon[PD] < ta || (k > 0 && Pemohon[PD] < tr)))"),
    ('Persen Disetujui', F_PCT, '2 Kebijakan', 'Approval rate', 'DIVIDE([Pemohon Disetujui], [Jumlah Pemohon])'),
    ('Default Rate Disetujui', F_PCT2, '2 Kebijakan', 'Default rate di antara pinjaman yang disetujui',
     f"{VARS}\nRETURN\n    DIVIDE(\n        COUNTROWS(FILTER(Pemohon, Pemohon[TARGET] = 1 && (Pemohon[PD] < ta || (k > 0 && Pemohon[PD] < tr)))),\n        [Pemohon Disetujui]\n    )"),
    ('Gagal Bayar Tertangkap', F_INT, '2 Kebijakan', 'Gagal bayar dengan PD >= batas approve',
     "VAR ta = [Batas Approve Aktif]\nRETURN COUNTROWS(FILTER(Pemohon, Pemohon[TARGET] = 1 && Pemohon[PD] >= ta))"),
    ('Recall', F_PCT, '2 Kebijakan', 'Persentase gagal bayar yang tertangkap model', 'DIVIDE([Gagal Bayar Tertangkap], [Jumlah Gagal Bayar])'),
    ('Precision', F_PCT, '2 Kebijakan', 'Persentase tolakan yang memang gagal bayar',
     "VAR ta = [Batas Approve Aktif]\nRETURN DIVIDE([Gagal Bayar Tertangkap], COUNTROWS(FILTER(Pemohon, Pemohon[PD] >= ta)))"),
    ('F2 Score', '0.000', '2 Kebijakan', 'F2 pada batas approve aktif (recall diberi bobot 4x precision)',
     'VAR p = [Precision]\nVAR r = [Recall]\nRETURN DIVIDE(5 * p * r, 4 * p + r)'),
    # skenario (grafik sebelum vs sesudah)
    ('Expected Loss Skenario', F_MONEY, '3 Grafik', 'Expected loss per skenario',
     "SWITCH(SELECTEDVALUE(Skenario[Skenario]), \"Tanpa model\", [Expected Loss Tanpa Model], \"Dengan model\", [Expected Loss Dengan Model])"),
    ('Keuntungan Hilang Skenario', F_MONEY, '3 Grafik', 'Keuntungan hilang per skenario',
     "IF(SELECTEDVALUE(Skenario[Skenario]) = \"Dengan model\", [Keuntungan Hilang], 0)"),
    # kurva threshold
    ('Expected Loss Kurva', F_MONEY, '3 Grafik', 'Expected loss jika tolak semua PD >= threshold pada sumbu X',
     "VAR t = SELECTEDVALUE('Kurva Threshold'[Threshold])\nVAR lgd = [LGD Aktif]\nRETURN SUMX(FILTER(Pemohon, Pemohon[TARGET] = 1 && Pemohon[PD] < t), Pemohon[AMT_CREDIT]) * lgd / 1e9"),
    ('Keuntungan Hilang Kurva', F_MONEY, '3 Grafik', 'Keuntungan hilang jika tolak semua PD >= threshold pada sumbu X',
     "VAR t = SELECTEDVALUE('Kurva Threshold'[Threshold])\nRETURN SUMX(FILTER(Pemohon, Pemohon[TARGET] = 0 && Pemohon[PD] >= t), Pemohon[KEUNTUNGAN_POTENSIAL]) / 1e9"),
    ('Total Biaya Kurva', F_MONEY, '3 Grafik', 'Expected loss + keuntungan hilang per threshold', '[Expected Loss Kurva] + [Keuntungan Hilang Kurva]'),
    ('Total Biaya Tanpa Model', F_MONEY, '3 Grafik', 'Garis pembanding: total biaya tanpa model', 'CALCULATE([Expected Loss Tanpa Model], ALL(\'Kurva Threshold\'))'),
    ('Judul Dinamis', None, '3 Grafik', 'Ringkasan kebijakan aktif untuk subjudul',
     '"Batas approve " & FORMAT([Batas Approve Aktif], "0.0%") & " | batas reject " & FORMAT([Batas Reject Aktif], "0.0%") & '
     '" | LGD " & FORMAT([LGD Aktif], "0%") & " | limit di zona Review " & FORMAT([Limit Review Aktif], "0%")'),
    # scorecard: warna & pembanding
    ('Warna Positif Hijau', None, '4 Format', 'Hijau jika penghematan >= 0, merah jika negatif',
     'IF([Penghematan Bersih] >= 0, "#4E8F69", "#C0504A")'),
    ('Warna Default Rate', None, '4 Format', 'Hijau jika default rate disetujui di bawah default rate tanpa model',
     'IF([Default Rate Disetujui] <= [Default Rate], "#4E8F69", "#C0504A")'),
    ('Warna Netral', None, '4 Format', 'Warna angka netral', '"#3A4149"'),
    ('Warna Dicegah', None, '4 Format', 'Hijau jika ada kerugian yang dicegah', 'IF([Expected Loss Dicegah] > 0, "#4E8F69", "#C0504A")'),
    ('Sub EL Tanpa', None, '4 Format', 'Teks pembanding', '"semua disetujui | LGD " & FORMAT([LGD Aktif], "0%")'),
    ('Sub EL Dengan', None, '4 Format', 'Teks pembanding', '"-" & FORMAT([Expected Loss Turun %], "0.0%") & " vs tanpa model"'),
    ('Sub Dicegah', None, '4 Format', 'Teks pembanding', 'FORMAT([Gagal Bayar Tertangkap], "#,0") & " gagal bayar tertangkap"'),
    ('Sub Hilang', None, '4 Format', 'Teks pembanding', '"margin nasabah baik ditolak"'),
    ('Sub Hemat', None, '4 Format', 'Teks pembanding', 'FORMAT([Penghematan Bersih %], "+0.0%;-0.0%") & " vs tanpa model"'),
    ('Sub DR', None, '4 Format', 'Teks pembanding', '"sebelumnya " & FORMAT([Default Rate], "0.00%")'),
    ('Sub F2', None, '4 Format', 'Teks pembanding', '"recall " & FORMAT([Recall], "0%") & " | prec " & FORMAT([Precision], "0%")'),
    ('Warna Sorot Desil', None, '4 Format', 'Merah = default rate tertinggi, hijau = terendah (ikut filter)', '''VAR cur = [Default Rate]\nVAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[DESIL_SKOR_EKSTERNAL]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nRETURN SWITCH(TRUE(), cur = MAXX(t, [@dr]), "#C8574F", cur = MINX(t, [@dr]), "#5E9E78", "#C5CCD4")'''),
    ('Info Sorot Desil', None, '4 Format', 'Teks sorotan dinamis', 'VAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[DESIL_SKOR_EKSTERNAL]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nVAR hi = TOPN(1, t, [@dr], DESC)\nVAR lo = TOPN(1, t, [@dr], ASC)\nRETURN "Merah tertinggi: " & MAXX(hi, Pemohon[DESIL_SKOR_EKSTERNAL]) & " (" & FORMAT(MAXX(hi, [@dr]), "0.0%") & ")  |  hijau terendah: " & MAXX(lo, Pemohon[DESIL_SKOR_EKSTERNAL]) & " (" & FORMAT(MAXX(lo, [@dr]), "0.0%") & ")"'),
    ('Warna Sorot Usia', None, '4 Format', 'Merah = default rate tertinggi, hijau = terendah (ikut filter)', '''VAR cur = [Default Rate]\nVAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[KELOMPOK_USIA]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nRETURN SWITCH(TRUE(), cur = MAXX(t, [@dr]), "#C8574F", cur = MINX(t, [@dr]), "#5E9E78", "#C5CCD4")'''),
    ('Info Sorot Usia', None, '4 Format', 'Teks sorotan dinamis', 'VAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[KELOMPOK_USIA]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nVAR hi = TOPN(1, t, [@dr], DESC)\nVAR lo = TOPN(1, t, [@dr], ASC)\nRETURN "Merah tertinggi: " & MAXX(hi, Pemohon[KELOMPOK_USIA]) & " (" & FORMAT(MAXX(hi, [@dr]), "0.0%") & ")  |  hijau terendah: " & MAXX(lo, Pemohon[KELOMPOK_USIA]) & " (" & FORMAT(MAXX(lo, [@dr]), "0.0%") & ")"'),
    ('Warna Sorot Pendidikan', None, '4 Format', 'Merah = default rate tertinggi, hijau = terendah (ikut filter)', '''VAR cur = [Default Rate]\nVAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[PENDIDIKAN]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nRETURN SWITCH(TRUE(), cur = MAXX(t, [@dr]), "#C8574F", cur = MINX(t, [@dr]), "#5E9E78", "#C5CCD4")'''),
    ('Info Sorot Pendidikan', None, '4 Format', 'Teks sorotan dinamis', 'VAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[PENDIDIKAN]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nVAR hi = TOPN(1, t, [@dr], DESC)\nVAR lo = TOPN(1, t, [@dr], ASC)\nRETURN "Merah tertinggi: " & MAXX(hi, Pemohon[PENDIDIKAN]) & " (" & FORMAT(MAXX(hi, [@dr]), "0.0%") & ")  |  hijau terendah: " & MAXX(lo, Pemohon[PENDIDIKAN]) & " (" & FORMAT(MAXX(lo, [@dr]), "0.0%") & ")"'),
    ('Warna Sorot Wilayah', None, '4 Format', 'Merah = default rate tertinggi, hijau = terendah (ikut filter)', '''VAR cur = [Default Rate]\nVAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[RATING_WILAYAH]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nRETURN SWITCH(TRUE(), cur = MAXX(t, [@dr]), "#C8574F", cur = MINX(t, [@dr]), "#5E9E78", "#C5CCD4")'''),
    ('Info Sorot Wilayah', None, '4 Format', 'Teks sorotan dinamis', 'VAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[RATING_WILAYAH]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nVAR hi = TOPN(1, t, [@dr], DESC)\nVAR lo = TOPN(1, t, [@dr], ASC)\nRETURN "Merah tertinggi: " & MAXX(hi, Pemohon[RATING_WILAYAH]) & " (" & FORMAT(MAXX(hi, [@dr]), "0.0%") & ")  |  hijau terendah: " & MAXX(lo, Pemohon[RATING_WILAYAH]) & " (" & FORMAT(MAXX(lo, [@dr]), "0.0%") & ")"'),
    ('Warna Sorot Pekerjaan', None, '4 Format', 'Merah = default rate tertinggi, hijau = terendah (ikut filter)', '''VAR cur = [Default Rate]\nVAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[PEKERJAAN]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nRETURN SWITCH(TRUE(), cur = MAXX(t, [@dr]), "#C8574F", cur = MINX(t, [@dr]), "#5E9E78", "#C5CCD4")'''),
    ('Info Sorot Pekerjaan', None, '4 Format', 'Teks sorotan dinamis', 'VAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[PEKERJAAN]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nVAR hi = TOPN(1, t, [@dr], DESC)\nVAR lo = TOPN(1, t, [@dr], ASC)\nRETURN "Merah tertinggi: " & MAXX(hi, Pemohon[PEKERJAAN]) & " (" & FORMAT(MAXX(hi, [@dr]), "0.0%") & ")  |  hijau terendah: " & MAXX(lo, Pemohon[PEKERJAAN]) & " (" & FORMAT(MAXX(lo, [@dr]), "0.0%") & ")"'),
    ('Warna Sorot Pendapatan', None, '4 Format', 'Merah = default rate tertinggi, hijau = terendah (ikut filter)', '''VAR cur = [Default Rate]\nVAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[SUMBER_PENDAPATAN]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nRETURN SWITCH(TRUE(), cur = MAXX(t, [@dr]), "#C8574F", cur = MINX(t, [@dr]), "#5E9E78", "#C5CCD4")'''),
    ('Info Sorot Pendapatan', None, '4 Format', 'Teks sorotan dinamis', 'VAR t = FILTER(ADDCOLUMNS(ALLSELECTED(Pemohon[SUMBER_PENDAPATAN]), "@dr", [Default Rate], "@n", [Jumlah Pemohon]), [@n] >= 100)\nVAR hi = TOPN(1, t, [@dr], DESC)\nVAR lo = TOPN(1, t, [@dr], ASC)\nRETURN "Merah tertinggi: " & MAXX(hi, Pemohon[SUMBER_PENDAPATAN]) & " (" & FORMAT(MAXX(hi, [@dr]), "0.0%") & ")  |  hijau terendah: " & MAXX(lo, Pemohon[SUMBER_PENDAPATAN]) & " (" & FORMAT(MAXX(lo, [@dr]), "0.0%") & ")"'),
    ('Banding EL Tanpa', None, '5 Pembanding', 'Teks pembanding dinamis', '''FORMAT([Jumlah Gagal Bayar], "#,0") & " gagal bayar x LGD " & FORMAT([LGD Aktif], "0%")'''),
    ('Warna Banding EL Tanpa', None, '5 Pembanding', 'Warna pembanding', '''"#6E7781"'''),
    ('Banding EL Dengan', None, '5 Pembanding', 'Teks pembanding dinamis', '''"▼ " & FORMAT([Expected Loss Turun %], "0.0%") & " vs tanpa model"'''),
    ('Warna Banding EL Dengan', None, '5 Pembanding', 'Warna pembanding', '''IF([Expected Loss Turun %] > 0, "#4E8F69", "#C0504A")'''),
    ('Banding Dicegah', None, '5 Pembanding', 'Teks pembanding dinamis', '''"▲ " & FORMAT([Recall], "0%") & " gagal bayar tertangkap"'''),
    ('Warna Banding Dicegah', None, '5 Pembanding', 'Warna pembanding', '''IF([Expected Loss Dicegah] > 0, "#4E8F69", "#C0504A")'''),
    ('Banding Hilang', None, '5 Pembanding', 'Teks pembanding dinamis', '''FORMAT(DIVIDE([Keuntungan Hilang], [Expected Loss Tanpa Model]), "0%") & " dari kerugian awal"'''),
    ('Warna Banding Hilang', None, '5 Pembanding', 'Warna pembanding', '''"#B7862F"'''),
    ('Banding Hemat', None, '5 Pembanding', 'Teks pembanding dinamis', '''IF([Penghematan Bersih] >= 0, "▲ ", "▼ ") & FORMAT(ABS([Penghematan Bersih %]), "0.0%") & " vs tanpa model"'''),
    ('Warna Banding Hemat', None, '5 Pembanding', 'Warna pembanding', '''IF([Penghematan Bersih] >= 0, "#4E8F69", "#C0504A")'''),
    ('Banding DR', None, '5 Pembanding', 'Teks pembanding dinamis', '''"▼ " & FORMAT(([Default Rate] - [Default Rate Disetujui]) * 100, "0.0") & " poin dari " & FORMAT([Default Rate], "0.0%")'''),
    ('Warna Banding DR', None, '5 Pembanding', 'Warna pembanding', '''IF([Default Rate Disetujui] <= [Default Rate], "#4E8F69", "#C0504A")'''),
    ('Banding F2', None, '5 Pembanding', 'Teks pembanding dinamis', '''VAR p = [Default Rate]\nVAR b = DIVIDE(5 * p, 4 * p + 1)\nRETURN IF([F2 Score] >= b, "▲ +", "▼ ") & FORMAT([F2 Score] - b, "0.000") & " vs tanpa model"'''),
    ('Warna Banding F2', None, '5 Pembanding', 'Warna pembanding', '''VAR p = [Default Rate]\nRETURN IF([F2 Score] >= DIVIDE(5 * p, 4 * p + 1), "#4E8F69", "#C0504A")'''),
    ('Banding Pemohon', None, '5 Pembanding', 'Teks pembanding dinamis', '''FORMAT(DIVIDE([Jumlah Pemohon], CALCULATE([Jumlah Pemohon], ALL(Pemohon))), "0%") & " dari seluruh pemohon"'''),
    ('Warna Banding Pemohon', None, '5 Pembanding', 'Warna pembanding', '''"#6E7781"'''),
    ('Banding Default Rate', None, '5 Pembanding', 'Teks pembanding dinamis', '''VAR d = [Default Rate] - CALCULATE([Default Rate], ALL(Pemohon))\nRETURN IF(d > 0, "▲ +", "▼ ") & FORMAT(d * 100, "0.0") & " poin vs rata-rata"'''),
    ('Warna Banding Default Rate', None, '5 Pembanding', 'Warna pembanding', '''IF([Default Rate] > CALCULATE([Default Rate], ALL(Pemohon)), "#C0504A", "#4E8F69")'''),
    ('Banding PD', None, '5 Pembanding', 'Teks pembanding dinamis', '''"selisih " & FORMAT(ABS([Rata-rata PD] - [Default Rate]) * 100, "0.0") & " poin dari aktual"'''),
    ('Warna Banding PD', None, '5 Pembanding', 'Warna pembanding', '''IF(ABS([Rata-rata PD] - [Default Rate]) < 0.01, "#4E8F69", "#B7862F")'''),
    ('Banding Pinjaman', None, '5 Pembanding', 'Teks pembanding dinamis', '''FORMAT(DIVIDE([Total Pinjaman], CALCULATE([Total Pinjaman], ALL(Pemohon))), "0%") & " dari total pinjaman"'''),
    ('Warna Banding Pinjaman', None, '5 Pembanding', 'Warna pembanding', '''"#6E7781"'''),
    ('Banding Potensi', None, '5 Pembanding', 'Teks pembanding dinamis', '''FORMAT(DIVIDE([Potensi Kerugian], CALCULATE([Potensi Kerugian], ALL(Pemohon))), "0%") & " dari total potensi kerugian"'''),
    ('Warna Banding Potensi', None, '5 Pembanding', 'Warna pembanding', '''"#6E7781"'''),
    ('Expected Loss Tersisa', F_MONEY, '3 Grafik', 'Expected loss yang masih terjadi (untuk grafik per segmen)', '[Expected Loss Dengan Model]'),
]



def quote(n):
    return n if n.replace('_', '').isalnum() else "'" + n.replace("'", "''") + "'"


def tmdl_measure(name, fmt, folder, desc, dax):
    lines = [f'\t/// {desc}']
    if '\n' in dax:
        lines += [f'\tmeasure {quote(name)} = ```', '\n'.join('\t\t\t' + ln for ln in dax.split('\n')), '\t\t\t```']
    else:
        lines += [f'\tmeasure {quote(name)} = {dax}']
    if fmt:
        lines.append(f'\t\tformatString: {fmt}')
    lines.append(f'\t\tdisplayFolder: {folder}')
    return '\n'.join(lines) + '\n'


fact = ['table Pemohon', '']
for name, fmt, folder, desc, dax in MEASURES:
    fact.append(tmdl_measure(name, fmt, folder, desc, dax))
for c, t, _, fmt, summ, sort in COLS:
    fact += [f'\tcolumn {c}', f'\t\tdataType: {t}']
    if fmt:
        fact.append(f'\t\tformatString: {fmt}')
    if c in HIDDEN:
        fact.append('\t\tisHidden')
    fact += [f'\t\tsummarizeBy: {summ}', f'\t\tsourceColumn: {c}']
    if sort:
        fact.append(f'\t\tsortByColumn: {sort}')
    fact.append('')
mtypes = ', '.join(f'{{"{c}", {m}}}' for c, _, m, *_ in COLS)
fact += ['\tpartition Pemohon = m', '\t\tmode: import', '\t\tsource =', '\t\t\t\tlet',
         '\t\t\t\t    Source = Csv.Document(File.Contents(DataFolder & "pemohon_test.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
         '\t\t\t\t    Header = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),',
         f'\t\t\t\t    Typed = Table.TransformColumnTypes(Header, {{{mtypes}}}, "en-US")',
         '\t\t\t\tin', '\t\t\t\t    Typed', '']
write(SM / 'definition/tables/Pemohon.tmdl', '\n'.join(fact))


def calc_table(name, cols, dax, fname=None):
    """cols: list of (nama kolom, sumber [Value]/[Nama], tipe, format, sortBy, hidden)"""
    out = [f'table {quote(name)}', '']
    for c, src, t, fmt, sort, hid in cols:
        out += [f'\tcolumn {quote(c)}', f'\t\tdataType: {t}']
        if fmt:
            out.append(f'\t\tformatString: {fmt}')
        if hid:
            out.append('\t\tisHidden')
        out += ['\t\tsummarizeBy: none', f'\t\tsourceColumn: [{src}]']
        if sort:
            out.append(f'\t\tsortByColumn: {quote(sort)}')
        out.append('')
    out += [f'\tpartition {quote(name)} = calculated', '\t\tmode: import', f'\t\tsource = {dax}', '']
    write(SM / f'definition/tables/{fname or name}.tmdl', '\n'.join(out))


PCTF = '0"%"'
calc_table('Batas Approve', [('Batas Approve', 'Value', 'int64', PCTF, None, False)], 'GENERATESERIES(5, 40, 1)')
calc_table('Batas Reject', [('Batas Reject', 'Value', 'int64', PCTF, None, False)], 'GENERATESERIES(10, 60, 1)')
calc_table('LGD', [('LGD', 'LGD', 'int64', PCTF, None, False)], 'DATATABLE("LGD", INTEGER, {{45}, {60}, {75}})')
calc_table('Limit Review', [('Limit Review', 'Limit Review', 'int64', PCTF, None, False)],
           'DATATABLE("Limit Review", INTEGER, {{0}, {25}, {50}, {75}})')
calc_table('Skenario', [('Skenario', 'Skenario', 'string', None, 'Urut', False), ('Urut', 'Urut', 'int64', '0', None, True)],
           'DATATABLE("Skenario", STRING, "Urut", INTEGER, {{"Tanpa model", 1}, {"Dengan model", 2}})')
calc_table('Kurva Threshold', [('Threshold', 'Value', 'double', '0.00', None, False)], 'GENERATESERIES(0.03, 0.45, 0.01)')

# =====================================================================================================================
# 2. REPORT (PBIR)
# =====================================================================================================================
write(RP / 'definition.pbir', {'$schema': f'{S}/item/report/definitionProperties/2.0.0/schema.json', 'version': '4.0',
                               'datasetReference': {'byPath': {'path': f'../{NAME}.SemanticModel'}}})
write(RP / '.platform', {'$schema': f'{S}/gitIntegration/platformProperties/2.0.0/schema.json',
                         'metadata': {'type': 'Report', 'displayName': NAME}, 'config': {'version': '2.0', 'logicalId': str(uuid.uuid4())}})
write(RP / 'definition/version.json', {'$schema': f'{S}/item/report/definition/versionMetadata/1.0.0/schema.json', 'version': '2.0.0'})

THEME = {
    'name': 'HomeCreditRisk',
    'dataColors': [SLATE, SOFT_RED, SOFT_AMBER, SOFT_GREEN, BASE, '#8C96A0', '#A8786F', '#D9DEE3'],
    'background': '#FFFFFF', 'foreground': INK, 'tableAccent': NAVY, 'good': GREEN, 'neutral': ORANGE, 'bad': RED,
    'textClasses': {'title': {'fontFace': 'Segoe UI Semibold', 'fontSize': 12, 'color': DARK},
                    'label': {'fontFace': 'Segoe UI', 'fontSize': 10, 'color': INK},
                    'callout': {'fontFace': 'Segoe UI Bold', 'fontSize': 24, 'color': DARK}},
    'visualStyles': {
        '*': {'*': {
            'valueAxis': [{'gridlineShow': False}], 'categoryAxis': [{'gridlineShow': False}],
            'background': [{'show': True, 'color': {'solid': {'color': '#FFFFFF'}}, 'transparency': 0}],
            'border': [{'show': True, 'color': {'solid': {'color': '#E4E7EB'}}, 'radius': 8}],
            'title': [{'show': True, 'fontColor': {'solid': {'color': INK}}, 'fontSize': 12}],
            'subTitle': [{'show': True, 'fontColor': {'solid': {'color': MUTED}}, 'fontSize': 9}],
            'dropShadow': [{'show': False}],
        }},
        'page': {'*': {'background': [{'color': {'solid': {'color': LIGHT}}, 'transparency': 0}]}},
    },
}
write(RP / 'StaticResources/RegisteredResources/HomeCreditRisk.json', THEME)
write(RP / 'definition/report.json', {
    '$schema': f'{S}/item/report/definition/report/3.0.0/schema.json',
    'themeCollection': {
        'baseTheme': {'name': 'CY24SU10', 'reportVersionAtImport': {'visual': '1.8.97', 'report': '2.0.97', 'page': '1.3.97'}, 'type': 'SharedResources'},
        'customTheme': {'name': 'HomeCreditRisk.json', 'reportVersionAtImport': {'visual': '1.8.97', 'report': '2.0.97', 'page': '1.3.97'},
                        'type': 'RegisteredResources'}},
    'resourcePackages': [
        {'name': 'SharedResources', 'type': 'SharedResources', 'items': [{'name': 'CY24SU10', 'path': 'BaseThemes/CY24SU10.json', 'type': 'BaseTheme'}]},
        {'name': 'RegisteredResources', 'type': 'RegisteredResources',
         'items': [{'name': 'HomeCreditRisk.json', 'path': 'HomeCreditRisk.json', 'type': 'CustomTheme'}]}],
    'settings': {'useStylableVisualContainerHeader': True, 'defaultFilterActionIsDataFilter': True, 'defaultDrillFilterOtherVisuals': True,
                 'allowChangeFilterTypes': True, 'useEnhancedTooltips': True},
})

# ---------------------------------------------------------------- helper visual
VC = f'{S}/item/report/definition/visualContainer/2.1.0/schema.json'
lit = lambda v: {'expr': {'Literal': {'Value': v}}}
txt = lambda s: lit("'" + s.replace("'", "''") + "'")
col_ = lambda e, p: {'Column': {'Expression': {'SourceRef': {'Entity': e}}, 'Property': p}}
mea_ = lambda p, e='Pemohon': {'Measure': {'Expression': {'SourceRef': {'Entity': e}}, 'Property': p}}


def proj(kind, prop, ent='Pemohon', display=None):
    f = col_(ent, prop) if kind == 'c' else mea_(prop, ent)
    p = {'field': f, 'queryRef': f'{ent}.{prop}', 'nativeQueryRef': prop}
    if kind == 'c':
        p['active'] = True
    if display:
        p['displayName'] = display
    return p


def container(title=None, subtitle=None, dyn_subtitle=False):
    o = {'title': [{'properties': {'show': lit('true' if title else 'false'), 'fontSize': lit('11D'), 'fontFamily': txt(FONT_S),
                                   'fontColor': {'solid': {'color': lit(f"'{DARK}'")}}, **({'text': txt(title)} if title else {})}}]}
    if subtitle or dyn_subtitle:
        st = {'show': lit('true'), 'fontSize': lit('9D'), 'fontFamily': txt(FONT), 'fontColor': {'solid': {'color': lit(f"'{GREY}'")}}}
        name = dyn_subtitle if isinstance(dyn_subtitle, str) else 'Judul Dinamis'
        st['text'] = ({'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Pemohon'}}, 'Property': name}}}
                      if dyn_subtitle else txt(subtitle))
        o['subTitle'] = [{'properties': st}]
    return o


class Page:
    def __init__(self, name, display, height=760):
        self.name, self.display, self.height, self.z = name, display, height, 1000
        self.dir = RP / f'definition/pages/{name}'
        write(self.dir / 'page.json', {'$schema': f'{S}/item/report/definition/page/1.4.0/schema.json', 'name': name, 'displayName': display,
                                       'displayOption': 'FitToWidth', 'height': height, 'width': 1280})

    def add(self, key, x, y, w, h, visual):
        # pakai ulang nama folder versi sebelumnya agar file lama tertimpa (tidak ada visual lama yang tersisa)
        key = {'kpi_0': 'kpi', 'temuan': 'cara_baca', 'segmen': 'aksi', 'kalibrasi': 'pendapatan'}.get(key, key)
        self.z += 100
        write(self.dir / f'visuals/{key}/visual.json', {'$schema': VC, 'name': key, 'position': {'x': x, 'y': y, 'z': self.z, 'width': w, 'height': h,
                                                                                                    'tabOrder': self.z}, 'visual': visual})

    # ---- jenis visual
    def textbox(self, key, x, y, w, h, runs, bg=None):
        paras = []
        for para in runs:
            paras.append({'textRuns': [{'value': t, 'textStyle': {'fontFamily': FONT_B if b else FONT, 'fontSize': f'{sz}pt', 'color': c}}
                                       for t, sz, c, b in para]})
        vis = {'visualType': 'textbox', 'objects': {'general': [{'properties': {'paragraphs': paras}}]},
               'visualContainerObjects': {'background': [{'properties': {'show': lit('true' if bg else 'false'),
                                                                         **({'color': {'solid': {'color': lit(f"'{bg}'")}}} if bg else {})}}],
                                          'border': [{'properties': {'show': lit('false')}}]}, 'drillFilterOtherVisuals': True}
        self.add(key, x, y, w, h, vis)

    def slicer(self, key, x, y, w, h, ent, prop, title, mode='Dropdown', single=True, default=None):
        objs = {'data': [{'properties': {'mode': txt(mode)}}],
                'selection': [{'properties': {'singleSelect': lit('true' if single else 'false')}}],
                'header': [{'properties': {'show': lit('true'), 'text': txt(title), 'fontColor': {'solid': {'color': lit(f"'{GREY}'")}},
                                           'fontFamily': txt(FONT), 'textSize': lit('9D')}}],
                'items': [{'properties': {'fontColor': {'solid': {'color': lit(f"'{DARK}'")}}, 'textSize': lit('11D')}}]}
        if default is not None:   # pilihan awal slicer = nilai hasil NB 04
            objs['general'] = [{'properties': {'filter': {'filter': {
                'Version': 2, 'From': [{'Name': 't', 'Entity': ent, 'Type': 0}],
                'Where': [{'Condition': {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 't'}}, 'Property': prop}}],
                                                'Values': [[{'Literal': {'Value': f'{default}L'}}]]}}}]}}}}]
        vis = {'visualType': 'slicer', 'query': {'queryState': {'Values': {'projections': [proj('c', prop, ent)]}}}, 'objects': objs,
               'visualContainerObjects': {'title': [{'properties': {'show': lit('false')}}],
                                          'border': [{'properties': {'show': lit('true'), 'color': {'solid': {'color': lit("'#E0E0E0'")}}}}]},
               'drillFilterOtherVisuals': True}
        self.add(key, x, y, w, h, vis)

    def score(self, key, x, y, w, h, measure, title, cmp, color):
        """Scorecard 2 baris: angka utama (warna kondisional) + pembanding dinamis berwarna (ikut slicer)."""
        m = lambda n: {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Pemohon'}}, 'Property': n}}}
        box = lambda: {'border': [{'properties': {'show': lit('false')}}], 'visualHeader': [{'properties': {'show': lit('false')}}],
                       'background': [{'properties': {'show': lit('true'), 'color': {'solid': {'color': lit("'#FFFFFF'")}}}}]}
        main = {'visualType': 'card', 'query': {'queryState': {'Values': {'projections': [proj('m', measure)]}}},
                'objects': {'labels': [{'properties': {'color': {'solid': {'color': m(color)}}, 'fontSize': lit('22D'),
                                                       'fontFamily': txt(FONT_B), 'labelDisplayUnits': lit('1D')}}],
                            'categoryLabels': [{'properties': {'show': lit('false')}}]},
                'visualContainerObjects': {**box(), 'title': [{'properties': {'show': lit('true'), 'text': txt(title), 'fontSize': lit('10D'),
                                                                              'fontFamily': txt(FONT), 'fontColor': {'solid': {'color': lit(f"'{GREY}'")}}}}]},
                'drillFilterOtherVisuals': True}
        sub = {'visualType': 'card', 'query': {'queryState': {'Values': {'projections': [proj('m', cmp)]}}},
               'objects': {'labels': [{'properties': {'color': {'solid': {'color': m('Warna ' + cmp)}}, 'fontSize': lit('9D'),
                                                      'fontFamily': txt(FONT_S)}}],
                           'categoryLabels': [{'properties': {'show': lit('false')}}], 'wordWrap': [{'properties': {'show': lit('true')}}]},
               'visualContainerObjects': {**box(), 'title': [{'properties': {'show': lit('false')}}]}, 'drillFilterOtherVisuals': True}
        self.add(key, x, y, w, h * 0.66, main)
        self.add(key + '_cmp', x, y + h * 0.66, w, h * 0.34, sub)

    def cards(self, key, x, y, w, h, measures, cols):
        vis = {'visualType': 'cardVisual',
               'query': {'queryState': {'Data': {'projections': [proj('m', m, display=d) for m, d in measures]}}},
               'objects': {'layout': [{'properties': {'columnCount': lit(f'{cols}L'), 'style': txt('Cards'), 'alignment': txt('left')}}],
                           'value': [{'properties': {'fontSize': lit('20D'), 'fontColor': {'solid': {'color': lit(f"'{NAVY}'")}}}, 'selector': {'id': 'default'}}],
                           'accentBar': [{'properties': {'show': lit('true'), 'color': {'solid': {'color': lit(f"'{NAVY}'")}}}, 'selector': {'id': 'default'}}]},
               'visualContainerObjects': {'title': [{'properties': {'show': lit('false')}}], 'border': [{'properties': {'show': lit('false')}}],
                                          'background': [{'properties': {'show': lit('false')}}]},
               'drillFilterOtherVisuals': True}
        self.add(key, x, y, w, h, vis)

    def chart(self, key, x, y, w, h, vtype, cat, ys, title, subtitle=None, sort=None, labels=True, colors=None, dyn=False, tooltips=None,
              series_colors=None, label_fmt=None, fill_measure=None):
        qs = {'Category': {'projections': [proj('c', cat[1], cat[0])]}, 'Y': {'projections': [proj('m', m, display=d) for m, d in ys]}}
        if tooltips:
            qs['Tooltips'] = {'projections': [proj('m', m) for m in tooltips]}
        query = {'queryState': qs}
        if sort:
            ent, prop, kind, direction = sort
            query['sortDefinition'] = {'sort': [{'field': col_(ent, prop) if kind == 'c' else mea_(prop, ent), 'direction': direction}], 'isDefaultSort': True}
        objs = {'labels': [{'properties': {'show': lit('true' if labels else 'false'), 'fontSize': lit('9D'), 'fontFamily': txt(FONT),
                                           **({'labelDisplayUnits': lit(label_fmt)} if label_fmt else {})}}],
                'legend': [{'properties': {'show': lit('true' if len(ys) > 1 else 'false'), 'position': txt('Top')}}],
                'valueAxis': [{'properties': {'gridlineShow': lit('false'), 'show': lit('false' if labels else 'true'), 'showAxisTitle': lit('false'),
                                              'fontFamily': txt(FONT), 'fontSize': lit('9D'), 'labelColor': {'solid': {'color': lit(f"'{GREY}'")}}}}],
                'categoryAxis': [{'properties': {'gridlineShow': lit('false'), 'showAxisTitle': lit('false'), 'fontFamily': txt(FONT),
                                                 'fontSize': lit('9D'), 'labelColor': {'solid': {'color': lit(f"'{DARK}'")}}}}]}
        if len(ys) > 1:
            objs['legend'][0]['properties'].update({'fontFamily': txt(FONT), 'fontSize': lit('9D')})
        dp = []
        if colors:   # warna per kategori
            for val, c in colors.items():
                dp.append({'properties': {'fill': {'solid': {'color': lit(f"'{c}'")}}},
                           'selector': {'data': [{'scopeId': {'Comparison': {'ComparisonKind': 0, 'Left': col_(cat[0], cat[1]),
                                                                             'Right': {'Literal': {'Value': f"'{val}'"}}}}}]}})
        if series_colors:   # warna per measure
            for m, c in series_colors.items():
                dp.append({'properties': {'fill': {'solid': {'color': lit(f"'{c}'")}}}, 'selector': {'metadata': f'Pemohon.{m}'}})
        if fill_measure:   # warna kondisional dari measure: berubah mengikuti filter
            dp.append({'properties': {'fill': {'solid': {'color': {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Pemohon'}},
                                                                                       'Property': fill_measure}}}}}},
                       'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}]}})
        if dp:
            objs['dataPoint'] = dp
        objs['labels'][0]['properties']['color'] = {'solid': {'color': lit(f"'{DARK}'")}}
        vis = {'visualType': vtype, 'query': query, 'objects': objs, 'visualContainerObjects': container(title, subtitle, dyn), 'drillFilterOtherVisuals': True}
        self.add(key, x, y, w, h, vis)

    def table(self, key, x, y, w, h, columns, measures, title, subtitle=None):
        vis = {'visualType': 'tableEx',
               'query': {'queryState': {'Values': {'projections': [proj('c', c, display=d) for c, d in columns] + [proj('m', m, display=d) for m, d in measures]}},
                         'sortDefinition': {'sort': [{'field': mea_(measures[0][0]), 'direction': 'Descending'}], 'isDefaultSort': True}},
               'objects': {'columnHeaders': [{'properties': {'fontColor': {'solid': {'color': lit("'#FFFFFF'")}}, 'backColor': {'solid': {'color': lit(f"'{NAVY}'")}},
                                                             'wordWrap': lit('true')}}],
                           'grid': [{'properties': {'gridHorizontal': lit('false'), 'gridVertical': lit('false'), 'rowPadding': lit('4D')}}],
                           'total': [{'properties': {'totals': lit('true')}}]},
               'visualContainerObjects': container(title, subtitle), 'drillFilterOtherVisuals': True}
        self.add(key, x, y, w, h, vis)


ZC = {'Approve': GREEN, 'Review': ORANGE, 'Reject': HC_RED}
MARGIN, GAP, W = 16, 12, 1280
FULL = W - 2 * MARGIN


def header(page, title, subtitle):
    page.textbox('header_bar', 0, 0, W, 6, [[(' ', 1, HC_RED, False)]], bg=HC_RED)
    page.textbox('judul', MARGIN, 14, 640, 64, [[('Home Credit', 20, HC_RED, True), (f'  |  {title}', 20, DARK, True)],
                                               [(subtitle, 9, GREY, False)]])


def insight_box(page, key, y, h, items):
    paras = [[('Temuan utama', 11, HC_RED, True)]]
    for i, (head, body) in enumerate(items, 1):
        paras.append([(f'{i}. {head} ', 9, DARK, True), (body, 9, DARK, False)])
    page.textbox(key, MARGIN, y, FULL, h, paras, bg='#FFFFFF')


# =====================================================================================================================
# HALAMAN 1: Ringkasan Kebijakan (pola Z)
#   kiri atas judul -> kanan atas slicer kebijakan
#   baris scorecard (kiri -> kanan: sebelum, sesudah, dampak)
#   tengah: kurva biaya per threshold -> komposisi biaya sebelum vs sesudah
#   bawah (kiri -> kanan): desil skor -> zona model -> dampak per segmen
#   paling bawah: temuan utama + aksi
# =====================================================================================================================
p1 = Page('ringkasan', 'Ringkasan Kebijakan', 1060)
header(p1, 'Dampak Model Risiko Kredit', 'Data test 61.503 pemohon | nilai uang dalam miliar (M)')
SW = (FULL - 640 - 3 * GAP) / 4
for i, (key, ent, prop, title, dflt) in enumerate([('sl_approve', 'Batas Approve', 'Batas Approve', 'Batas approve', round(T_APP * 100)),
                                                   ('sl_reject', 'Batas Reject', 'Batas Reject', 'Batas reject', round(T_REJ * 100)),
                                                   ('sl_lgd', 'LGD', 'LGD', 'LGD', 45),
                                                   ('sl_limit', 'Limit Review', 'Limit Review', 'Limit zona Review', 0)]):
    p1.slicer(key, MARGIN + 640 + i * (SW + GAP), 16, SW, 60, ent, prop, title, default=dflt)

CARDS = [('Expected Loss Tanpa Model', 'EL tanpa model', 'Banding EL Tanpa', 'Warna Netral'),
         ('Expected Loss Dengan Model', 'EL dengan model', 'Banding EL Dengan', 'Warna Netral'),
         ('Expected Loss Dicegah', 'Kerugian dicegah', 'Banding Dicegah', 'Warna Dicegah'),
         ('Keuntungan Hilang', 'Keuntungan hilang', 'Banding Hilang', 'Warna Netral'),
         ('Penghematan Bersih', 'Hemat bersih', 'Banding Hemat', 'Warna Positif Hijau'),
         ('Default Rate Disetujui', 'DR disetujui', 'Banding DR', 'Warna Default Rate'),
         ('F2 Score', 'F2-score', 'Banding F2', 'Warna Netral')]
CW = (FULL - (len(CARDS) - 1) * GAP) / len(CARDS)
for i, (m, t, sub, col) in enumerate(CARDS):
    p1.score(f'kpi_{i}', MARGIN + i * (CW + GAP), 90, CW, 104, m, t, sub, col)

W2 = FULL - GAP
p1.chart('kurva', MARGIN, 206, W2 * 0.6, 280, 'lineChart', ('Kurva Threshold', 'Threshold'),
         [('Expected Loss Kurva', 'Expected loss'), ('Keuntungan Hilang Kurva', 'Keuntungan hilang'), ('Total Biaya Kurva', 'Total biaya'),
          ('Total Biaya Tanpa Model', 'Tanpa model')],
         'Biaya di setiap threshold (miliar)', 'Titik terendah garis abu tua = biaya minimum',
         sort=('Kurva Threshold', 'Threshold', 'c', 'Ascending'), labels=False,
         series_colors={'Expected Loss Kurva': SOFT_RED, 'Keuntungan Hilang Kurva': SOFT_AMBER, 'Total Biaya Kurva': SLATE, 'Total Biaya Tanpa Model': BASE})
p1.chart('sebelum_sesudah', MARGIN + W2 * 0.6 + GAP, 206, W2 * 0.4, 280, 'columnChart', ('Skenario', 'Skenario'),
         [('Expected Loss Skenario', 'Expected loss'), ('Keuntungan Hilang Skenario', 'Keuntungan hilang')],
         'Total biaya: tanpa vs dengan model (miliar)', dyn=True, sort=('Skenario', 'Skenario', 'c', 'Ascending'),
         series_colors={'Expected Loss Skenario': SOFT_RED, 'Keuntungan Hilang Skenario': SOFT_AMBER})

W3 = (FULL - 2 * GAP) / 3
p1.chart('desil', MARGIN, 498, W3, 280, 'clusteredColumnChart', ('Pemohon', 'DESIL_SKOR_EKSTERNAL'), [('Default Rate', 'Default rate')],
         'Default rate per desil skor (D1 = terendah)', dyn='Info Sorot Desil',
         sort=('Pemohon', 'DESIL_SKOR_EKSTERNAL', 'c', 'Ascending'), tooltips=['Jumlah Pemohon', 'Rata-rata PD'], fill_measure='Warna Sorot Desil')
p1.chart('zona', MARGIN + W3 + GAP, 498, W3, 280, 'clusteredColumnChart', ('Pemohon', 'ZONA'), [('Default Rate', 'Default rate')],
         f'Default rate per zona model ({T_APP:.0%} / {T_REJ:.0%})', 'Hijau setujui | amber review | merah tolak',
         sort=('Pemohon', 'ZONA', 'c', 'Ascending'), colors={'Approve': SOFT_GREEN, 'Review': SOFT_AMBER, 'Reject': SOFT_RED},
         tooltips=['Jumlah Pemohon', 'Porsi Pemohon', 'Porsi Gagal Bayar', 'Potensi Kerugian'])
p1.chart('segmen', MARGIN + 2 * (W3 + GAP), 498, W3, 280, 'barChart', ('Pemohon', 'SUMBER_PENDAPATAN'),
         [('Expected Loss Dicegah', 'Dicegah'), ('Expected Loss Tersisa', 'Tersisa')],
         'Kerugian dicegah vs tersisa (miliar)', 'Per sumber pendapatan; hijau = dicegah model',
         sort=('Pemohon', 'Potensi Kerugian', 'm', 'Descending'), tooltips=['Default Rate', 'Jumlah Pemohon'],
         series_colors={'Expected Loss Dicegah': SOFT_GREEN, 'Expected Loss Tersisa': SOFT_RED})

insight_box(p1, 'temuan', 790, 250, [
    ('Kerugian turun lebih dari separuh.', 'Batas 12%: expected loss 1,24 M menjadi 0,59 M (-53%); default rate disetujui 8,07% menjadi 4,4%; 80% pengajuan tetap disetujui.'),
    ('Menolak terlalu banyak itu mahal.', 'Di LGD 45% hasil bersih impas karena margin nasabah baik ikut hilang. Di LGD 60-75% (kredit tanpa agunan) hemat bersih 13-21%.'),
    ('Zona Review = tuas profit.', 'Set "Limit zona Review" 50%: 12% pemohon berisiko menengah tetap dilayani dengan limit kecil, hemat bersih naik.'),
    ('Skor eksternal pembeda terkuat.', 'D1-D2 (20% pemohon) menyumbang 46% gagal bayar. Aksi: verifikasi tambahan dan uang muka untuk D1-D2.'),
    ('Karyawan = kerugian terbesar.', 'Sekitar 60% potensi kerugian; PNS dan pensiunan paling aman (5-6%), prioritaskan lewat kerja sama payroll.'),
])

# =====================================================================================================================
# HALAMAN 2: Profil Risiko Pemohon
# =====================================================================================================================
p2 = Page('profil', 'Profil Risiko Pemohon', 1060)
header(p2, 'Profil Risiko Pemohon', 'Klik batang mana pun untuk cross-highlight; warna sorotan ikut filter')
p2.slicer('sl_kontrak', W - MARGIN - 2 * 260 - GAP, 16, 260, 60, 'Pemohon', 'JENIS_KONTRAK', 'Jenis kontrak', single=False)
p2.slicer('sl_zona', W - MARGIN - 260, 16, 260, 60, 'Pemohon', 'ZONA', 'Zona model', single=False)
C2 = [('Jumlah Pemohon', 'Pemohon', 'Banding Pemohon', 'Warna Netral'), ('Default Rate', 'Default rate', 'Banding Default Rate', 'Warna Netral'),
      ('Rata-rata PD', 'Rata-rata PD', 'Banding PD', 'Warna Netral'), ('Total Pinjaman', 'Total pinjaman', 'Banding Pinjaman', 'Warna Netral'),
      ('Potensi Kerugian', 'Potensi kerugian', 'Banding Potensi', 'Warna Netral')]
CW2 = (FULL - 4 * GAP) / 5
for i, (m, t, sub, col) in enumerate(C2):
    p2.score(f'kpi_{i}', MARGIN + i * (CW2 + GAP), 90, CW2, 104, m, t, sub, col)
for k, (key, col, title, dim) in enumerate([('usia', 'KELOMPOK_USIA', 'Default rate per usia', 'Usia'),
                                            ('pendidikan', 'PENDIDIKAN', 'Default rate per pendidikan', 'Pendidikan'),
                                            ('wilayah', 'RATING_WILAYAH', 'Default rate per rating wilayah', 'Wilayah')]):
    p2.chart(key, MARGIN + k * (W3 + GAP), 206, W3, 280, 'clusteredColumnChart', ('Pemohon', col), [('Default Rate', 'Default rate')],
             title, dyn=f'Info Sorot {dim}', sort=('Pemohon', col, 'c', 'Ascending'), tooltips=['Jumlah Pemohon', 'Rata-rata PD'],
             fill_measure=f'Warna Sorot {dim}')
p2.chart('pekerjaan', MARGIN, 498, W2 * 0.55, 280, 'clusteredBarChart', ('Pemohon', 'PEKERJAAN'), [('Default Rate', 'Default rate')],
         'Default rate per jenis pekerjaan', dyn='Info Sorot Pekerjaan',
         sort=('Pemohon', 'Default Rate', 'm', 'Descending'), tooltips=['Jumlah Pemohon', 'Rata-rata PD'], fill_measure='Warna Sorot Pekerjaan')
p2.chart('kalibrasi', MARGIN + W2 * 0.55 + GAP, 498, W2 * 0.45, 280, 'clusteredBarChart', ('Pemohon', 'DESIL_SKOR_EKSTERNAL'),
         [('Default Rate', 'Aktual'), ('Rata-rata PD', 'Prediksi model')],
         'Aktual vs prediksi model per desil', 'Batang berdekatan = prediksi akurat',
         sort=('Pemohon', 'DESIL_SKOR_EKSTERNAL', 'c', 'Ascending'), series_colors={'Default Rate': SLATE, 'Rata-rata PD': SOFT_AMBER})
insight_box(p2, 'temuan', 790, 250, [
    ('Usia muda paling berisiko.', 'Di bawah 25 tahun 12,6%, hampir 3x usia 60+ (4,7%). Aksi: limit awal kecil, naik bertahap sesuai riwayat bayar.'),
    ('Pendidikan dan wilayah memperkuat sinyal.', 'Sarjana 5,4% vs SMP 11,4%; wilayah rating 3 berisiko 2,3x rating 1.'),
    ('Pekerjaan berisiko tinggi.', 'Low-skill laborers 16%, security staff 13%, drivers 12% (rata-rata 8,1%). Aksi: minta bukti penghasilan tambahan.'),
    ('Prediksi model akurat.', 'Rata-rata PD 8,04% vs default rate aktual 8,07%, pola per desil sama; PD layak dipakai untuk menghitung expected loss.'),
])

write(RP / 'definition/pages/pages.json', {'$schema': f'{S}/item/report/definition/pagesMetadata/1.0.0/schema.json',
                                           'pageOrder': ['ringkasan', 'profil'], 'activePageName': 'ringkasan'})
print('PBIP dibuat:', HERE / f'{NAME}.pbip', '| folder data:', DATA_DIR)
