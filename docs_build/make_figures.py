"""Grafik statis untuk README, artikel Medium, dan portfolio (docs/assets/*.png).
Sumber angka: models/eval_artifacts.json, app_data/segments.parquet, app_data/test_scores.parquet."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'assets'
OUT.mkdir(parents=True, exist_ok=True)
for f in Path('/usr/share/fonts/truetype/google-fonts').glob('Poppins-*.ttf'):
    fm.fontManager.addfont(str(f))
plt.rcParams.update({'font.family': 'Poppins', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#BFC5CC', 'axes.labelcolor': '#4A5058', 'xtick.color': '#4A5058', 'ytick.color': '#4A5058',
                     'axes.grid': False, 'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'savefig.dpi': 170})
RED, DARK, GREY, SOFT, GREEN, AMBER = '#C8102E', '#2B3036', '#6B7280', '#C9CED6', '#3E8E63', '#D9A23A'
NAVY = '#2F4B6E'   # sorotan netral: model terpilih / fitur terpenting (bukan arti baik atau buruk)
# Aturan warna: merah = risiko atau kerugian, hijau = aman atau benar, amber = waspada, abu = netral, biru tua = sorotan netral

art = json.load(open(ROOT / 'models/eval_artifacts.json'))
seg = pd.read_parquet(ROOT / 'app_data/segments.parquet')
ts = pd.read_parquet(ROOT / 'app_data/test_scores.parquet')


def title(ax, t, sub=None):
    ax.set_title(t, loc='left', fontsize=14, fontweight='bold', color=DARK, pad=26 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=10, color=GREY, va='bottom')


def idn(t):
    return t.replace('.', '#').replace(',', '.').replace('#', ',')


def bars(ax, labels, vals, colors, fmt='{:.1f}%', horizontal=False):
    if horizontal:
        b = ax.barh(labels, vals, color=colors, height=0.6)
        for r, v in zip(b, vals):
            ax.text(r.get_width() + max(vals) * 0.01, r.get_y() + r.get_height() / 2, idn(fmt.format(v)), va='center', fontsize=10, color=DARK)
        ax.set_xticks([]); ax.spines['bottom'].set_visible(False)
    else:
        b = ax.bar(labels, vals, color=colors, width=0.65)
        for r, v in zip(b, vals):
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + max(vals) * 0.015, idn(fmt.format(v)), ha='center', fontsize=10, color=DARK)
        ax.set_yticks([]); ax.spines['left'].set_visible(False)
    return b


# 1. desil skor eksternal
d = seg[seg.dimensi == 'Skor eksternal (desil)'].sort_values('urutan')
fig, ax = plt.subplots(figsize=(10, 4.6))
v = d.default_rate.values * 100
bars(ax, d.segmen, v, [RED, RED] + [SOFT] * 7 + [GREEN])
ax.axhline(8.07, color=DARK, ls=(0, (4, 3)), lw=1); ax.text(9.45, 8.4, 'rata-rata 8,1%', ha='right', fontsize=9, color=DARK)
title(ax, 'Default rate per desil skor eksternal', 'D1 = 10% pemohon dengan skor terendah. D1 dan D2 menyumbang 46% seluruh gagal bayar')
fig.tight_layout(); fig.savefig(OUT / 'fig_desil.png'); plt.close(fig)

# 2. sinyal terlilit utang
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, dim, t, cols in [(axes[0], 'Utilisasi kartu kredit', 'Pemakaian limit kartu kredit', [SOFT, SOFT, SOFT, AMBER, RED]),
                         (axes[1], 'Pinjaman aktif di lembaga lain', 'Jumlah pinjaman aktif di lembaga lain', [SOFT] * 5 + [AMBER, RED])]:
    x = seg[seg.dimensi == dim].sort_values('urutan')
    bars(ax, x.segmen, x.default_rate.values * 100, cols)
    title(ax, t)
fig.suptitle('Makin terlilit utang, makin tinggi risiko gagal bayar', x=0.01, ha='left', fontsize=15, fontweight='bold', color=DARK)
fig.tight_layout(); fig.savefig(OUT / 'fig_utang.png'); plt.close(fig)

# 3. perbandingan model
cmp = pd.DataFrame(art['compare_oof']).set_index('model')
order = ['Dummy', 'Aturan: skor eksternal', 'Random Forest', 'Logistic Regression', 'XGBoost', 'LightGBM']
lab = ['Tebakan acak', 'Aturan skor eksternal', 'Random Forest', 'Logistic Regression', 'XGBoost', 'LightGBM']
vals = cmp.loc[order, 'PR-AUC'].values
fig, ax = plt.subplots(figsize=(9, 4.4))
bars(ax, lab, vals, [SOFT] * 5 + [NAVY], fmt='{:.3f}', horizontal=True)
title(ax, 'PR-AUC hasil validasi silang (data latih)', 'Makin tinggi makin baik. LightGBM terbaik, 3,5x tebakan acak')
fig.tight_layout(); fig.savefig(OUT / 'fig_model.png'); plt.close(fig)

# 4. PR & ROC curve
pr, roc = art['pr_curve_test'], art['roc_curve_test']
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
ax = axes[0]; ax.plot(pr['recall'], pr['precision'], color=NAVY, lw=2.2, label='LightGBM (PR-AUC 0,288)')
ax.axhline(pr['base_rate'], color=GREY, ls='--', lw=1, label='Tebakan acak (0,081)')
ax.scatter([0.571], [0.228], color=DARK, zorder=5); ax.annotate('batas 12%\nrecall 57%, precision 23%', (0.571, 0.228), (0.62, 0.45), fontsize=9, arrowprops=dict(arrowstyle='-', color=GREY))
ax.set_xlabel('Recall (gagal bayar yang tertangkap)'); ax.set_ylabel('Precision (tolakan yang tepat)'); ax.legend(frameon=False, fontsize=9)
title(ax, 'Precision-Recall curve (data uji)')
ax = axes[1]; ax.plot(roc['fpr'], roc['tpr'], color=NAVY, lw=2.2, label='LightGBM (ROC-AUC 0,793)')
ax.plot([0, 1], [0, 1], color=GREY, ls='--', lw=1, label='Tebakan acak'); ax.legend(frameon=False, fontsize=9, loc='lower right')
ax.set_xlabel('% nasabah lancar ikut tersaring'); ax.set_ylabel('Recall'); title(ax, 'ROC curve (data uji)')
fig.tight_layout(); fig.savefig(OUT / 'fig_pr_roc.png'); plt.close(fig)

# 5. biaya per threshold (nominal)
y = ts.TARGET.values == 1; p = ts.PD.values; fn = ts.AMT_CREDIT.values * 0.45; fp = ts.KEUNTUNGAN_POTENSIAL.values
grid = np.round(np.arange(0.03, 0.45, 0.005), 3)
el = np.array([fn[(p < t) & y].sum() for t in grid]) / 1e9; op = np.array([fp[(p >= t) & ~y].sum() for t in grid]) / 1e9
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(grid, el, color=RED, lw=2, label='Expected loss (gagal bayar yang lolos)')
ax.plot(grid, op, color=AMBER, lw=2, label='Keuntungan hilang (nasabah baik ditolak)')
ax.plot(grid, el + op, color=DARK, lw=2.6, label='Total biaya')
ax.axhline(fn[y].sum() / 1e9, color=GREY, ls=':', lw=1.2); ax.text(0.445, fn[y].sum() / 1e9 + 0.04, 'total biaya tanpa model', ha='right', fontsize=9, color=GREY)
for t, l in [(0.12, 'batas approve 12%'), (0.22, 'batas reject 22%')]:
    ax.axvline(t, color=GREY, ls='--', lw=1); ax.text(t + 0.004, 2.6, l, fontsize=9, color=DARK)
ax.set_ylim(0, 3); ax.set_xlabel('Threshold (tolak jika probabilitas gagal bayar di atas nilai ini)'); ax.set_ylabel('Miliar (unit dataset)')
ax.legend(frameon=False, fontsize=9, loc='upper right', bbox_to_anchor=(1, 0.85))
title(ax, 'Trade-off biaya di setiap threshold (data uji, LGD 45%)', 'Threshold rendah menekan expected loss, tetapi keuntungan dari nasabah baik ikut hilang')
fig.tight_layout(); fig.savefig(OUT / 'fig_biaya_threshold.png'); plt.close(fig)

# 6. komposisi biaya per kebijakan
imp = pd.DataFrame(art['impact'])
lab = ['Tanpa model', 'Aturan skor\neksternal', 'F2 tertinggi\n(9%)', 'Terpilih\n(12%)', 'Biaya minimum\n(22%)']
fig, ax = plt.subplots(figsize=(10, 4.8))
e, k = imp.expected_loss.values / 1e9, imp.keuntungan_hilang.values / 1e9
ax.bar(lab, e, color=RED, width=0.6, label='Expected loss'); ax.bar(lab, k, bottom=e, color=AMBER, width=0.6, label='Keuntungan hilang')
for i, (a_, b_) in enumerate(zip(e, k)):
    ax.text(i, a_ / 2, idn(f'{a_:.2f}'), ha='center', color='white', fontsize=10, fontweight='bold')
    if b_ > 0.05: ax.text(i, a_ + b_ / 2, idn(f'{b_:.2f}'), ha='center', color='white', fontsize=10, fontweight='bold')
    ax.text(i, a_ + b_ + 0.03, idn(f'Total {a_ + b_:.2f} M'), ha='center', fontsize=10, color=DARK, fontweight='bold')
ax.set_yticks([]); ax.spines['left'].set_visible(False); ax.legend(frameon=False, loc='upper right', fontsize=9); ax.set_ylim(0, 1.7)
title(ax, 'Total biaya per kebijakan (miliar, data uji, LGD 45%)', 'Merah = kerugian gagal bayar, amber = margin hilang dari nasabah baik yang ditolak')
fig.tight_layout(); fig.savefig(OUT / 'fig_kebijakan.png'); plt.close(fig)

# 7. zona
z = pd.DataFrame(art['zones'])
fig, ax = plt.subplots(figsize=(9, 4.4))
b = ax.bar(['Approve\n(PD < 12%)', 'Review\n(12-22%)', 'Reject\n(PD >= 22%)'], z['default_rate_%'], color=[GREEN, AMBER, RED], width=0.6)
for r, (_, row) in zip(b, z.iterrows()):
    ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.6, idn(f"{row['default_rate_%']:.1f}%"), ha='center', fontweight='bold', color=DARK)
    ax.text(r.get_x() + r.get_width() / 2, -4.8, f"{row['porsi_%']:.0f}% pemohon\n{row['porsi_seluruh_gagal_bayar_%']:.0f}% gagal bayar",
            ha='center', va='center', color=GREY, fontsize=9)
ax.axhline(8.07, color=DARK, ls=(0, (4, 3)), lw=1); ax.text(0.5, 8.6, 'rata-rata 8,1%', ha='center', fontsize=9)
ax.set_yticks([]); ax.spines['left'].set_visible(False); ax.set_ylim(-9, 38); ax.tick_params(axis='x', pad=26)
title(ax, 'Kebijakan 3 zona: default rate per zona (data uji)')
fig.tight_layout(); fig.savefig(OUT / 'fig_zona.png'); plt.close(fig)

# 8. SHAP
names = {'EXT_SOURCE_MEAN': 'Rata-rata skor eksternal', 'CREDIT_TERM': 'Perkiraan tenor', 'AMT_ANNUITY': 'Besar cicilan',
         'EXT_SOURCE_2': 'Skor eksternal 2', 'CREDIT_GOODS': 'Pinjaman / harga barang', 'EXT_SOURCE_3': 'Skor eksternal 3',
         'POS_MONTHS_CNT': 'Lama riwayat kredit barang', 'EXT_SOURCE_MIN': 'Skor eksternal terendah', 'PREV_AMT_ANNUITY_MEAN': 'Cicilan pinjaman sebelumnya',
         'ORGANIZATION_TYPE': 'Sektor tempat kerja', 'POS_INST_FUTURE_MEAN_12M': 'Sisa cicilan barang', 'OCCUPATION_TYPE': 'Jenis pekerjaan'}
sh = pd.Series(art['shap_importance']).head(12)
fig, ax = plt.subplots(figsize=(9, 5))
lab = [names.get(i, i) for i in sh.index][::-1]
bars(ax, lab, sh.values[::-1], [SOFT] * 11 + [NAVY], fmt='{:.3f}', horizontal=True)
title(ax, 'Faktor paling berpengaruh terhadap skor risiko (SHAP)', 'Rata-rata |nilai SHAP| di data uji')
fig.tight_layout(); fig.savefig(OUT / 'fig_shap.png'); plt.close(fig)

# 9. confusion matrix
cm = np.array(art['confusion_matrix'])
fig, ax = plt.subplots(figsize=(6, 4.6))
cols = np.array([['#DCEFE3', '#F6D2D8'], ['#F6D2D8', '#DCEFE3']])   # hijau muda = keputusan benar, merah muda = keputusan salah
lbl = np.array([['Benar disetujui', 'Nasabah baik tersaring'], ['Gagal bayar lolos', 'Gagal bayar tertangkap']])
for i in range(2):
    for j in range(2):
        ax.add_patch(plt.Rectangle((j, 1 - i), 1, 1, color=cols[i, j]))
        c = DARK
        ax.text(j + 0.5, 1.58 - i, f'{cm[i, j]:,}'.replace(',', '.'), ha='center', fontsize=20, fontweight='bold', color=c)
        ax.text(j + 0.5, 1.3 - i, lbl[i, j], ha='center', fontsize=9.5, color=c)
ax.set_xlim(0, 2); ax.set_ylim(0, 2); ax.set_xticks([0.5, 1.5]); ax.set_xticklabels(['Diprediksi lancar', 'Diprediksi gagal bayar'])
ax.set_yticks([1.5, 0.5]); ax.set_yticklabels(['Aktual lancar', 'Aktual\ngagal bayar']); ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
title(ax, 'Confusion matrix (batas 12%)', 'Hijau = keputusan benar, merah muda = keputusan salah')
fig.tight_layout(); fig.savefig(OUT / 'fig_cm.png'); plt.close(fig)

# 10. alur proyek
fig, ax = plt.subplots(figsize=(14, 2.4)); ax.axis('off')
steps = ['CSV mentah\n7 tabel, 2,7 GB', 'Parquet\nstaging', 'BigQuery\n+ SQL data mart', 'EDA &\nuji statistik', 'Pipeline +\n4 model + tuning', 'Threshold\nF2 + biaya', 'Streamlit &\nPower BI']
for i, s in enumerate(steps):
    x = i * 1.0
    ax.add_patch(plt.Rectangle((x, 0.15), 0.86, 0.7, color=NAVY if i in (2, 4) else '#F1F3F5', ec='none'))
    ax.text(x + 0.43, 0.5, s, ha='center', va='center', fontsize=9, color='white' if i in (2, 4) else DARK, fontweight='bold')
    if i < len(steps) - 1: ax.annotate('', (x + 0.99, 0.5), (x + 0.87, 0.5), arrowprops=dict(arrowstyle='->', color=GREY))
ax.set_xlim(-0.05, len(steps) - 0.1); ax.set_ylim(0, 1)
fig.savefig(OUT / 'fig_alur.png', bbox_inches='tight'); plt.close(fig)
print(sorted(p.name for p in OUT.glob('*.png')))
