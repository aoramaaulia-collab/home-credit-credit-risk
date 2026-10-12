"""
Fungsi bersama untuk cleaning, feature engineering, dan preprocessing.
Dipakai oleh NB 04 (modeling) dan aplikasi Streamlit agar transformasinya identik.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# Kolom jumlah riwayat: kosong = nasabah memang tidak punya riwayat -> diisi 0
COUNT_COLS = ['BUREAU_CNT', 'BUREAU_ACTIVE_CNT', 'PREV_CNT', 'INST_CNT', 'POS_MONTHS_CNT', 'CC_MONTHS_CNT']
DAYS_COLS = ['DAYS_BIRTH', 'DAYS_EMPLOYED', 'DAYS_LAST_PHONE_CHANGE', 'DAYS_REGISTRATION', 'DAYS_ID_PUBLISH']


def load_mart(path: str) -> pd.DataFrame:
    """Baca data mart Parquet dan seragamkan tipe data (angka nullable -> float, teks -> object)."""
    df = pd.read_parquet(path)
    ext_cols = [c for c in df.columns if isinstance(df[c].dtype, pd.api.extensions.ExtensionDtype)
                and pd.api.types.is_numeric_dtype(df[c].dtype)]           # Int64/Int16/Float64 nullable
    df[ext_cols] = df[ext_cols].astype('float64')
    for c in df.select_dtypes(['object', 'string']).columns:
        df[c] = df[c].astype(object).where(df[c].notna(), np.nan)
    return df


def clean_and_engineer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleaning (keputusan NB 03 Bagian 2.6) + feature engineering.
    Semua langkah bersifat per-baris (tidak mempelajari apa pun dari data),
    sehingga aman diterapkan sebelum split tanpa risiko data leakage.
    """
    df = df.copy()

    # ---------- Cleaning ----------
    df['IS_NOT_EMPLOYED'] = (df['DAYS_EMPLOYED'] == 365243).astype(int)
    df.loc[df['DAYS_EMPLOYED'] == 365243, 'DAYS_EMPLOYED'] = np.nan
    df.loc[df['CODE_GENDER'] == 'XNA', 'CODE_GENDER'] = np.nan
    df.loc[df['NAME_FAMILY_STATUS'] == 'Unknown', 'NAME_FAMILY_STATUS'] = np.nan
    df.loc[df['ORGANIZATION_TYPE'] == 'XNA', 'ORGANIZATION_TYPE'] = 'Not employed'

    df['HAS_BUREAU'] = df['BUREAU_CNT'].notna().astype(int)
    df['HAS_PREV'] = df['PREV_CNT'].notna().astype(int)
    df['HAS_CC'] = df['CC_MONTHS_CNT'].notna().astype(int)
    df[COUNT_COLS] = df[COUNT_COLS].fillna(0)

    # ---------- Feature engineering ----------
    ext = df[['EXT_SOURCE_1', 'EXT_SOURCE_2', 'EXT_SOURCE_3']]
    df['EXT_SOURCE_MEAN'] = ext.mean(axis=1)
    df['EXT_SOURCE_MIN'] = ext.min(axis=1)
    df['EXT_SOURCE_NA_CNT'] = ext.isna().sum(axis=1)

    df['AGE_YEARS'] = -df['DAYS_BIRTH'] / 365
    df['EMPLOYED_YEARS'] = -df['DAYS_EMPLOYED'] / 365
    df['EMPLOYED_TO_AGE'] = df['EMPLOYED_YEARS'] / df['AGE_YEARS']
    df['PHONE_CHANGE_YEARS'] = -df['DAYS_LAST_PHONE_CHANGE'] / 365
    df['REGISTRATION_YEARS'] = -df['DAYS_REGISTRATION'] / 365
    df['ID_PUBLISH_YEARS'] = -df['DAYS_ID_PUBLISH'] / 365

    df['ANNUITY_INCOME'] = df['AMT_ANNUITY'] / df['AMT_INCOME_TOTAL']
    df['CREDIT_INCOME'] = df['AMT_CREDIT'] / df['AMT_INCOME_TOTAL']
    df['CREDIT_GOODS'] = df['AMT_CREDIT'] / df['AMT_GOODS_PRICE']
    df['CREDIT_TERM'] = df['AMT_CREDIT'] / df['AMT_ANNUITY']
    df['INCOME_PER_PERSON'] = df['AMT_INCOME_TOTAL'] / df['CNT_FAM_MEMBERS']
    df['DOC_COUNT'] = df.filter(like='FLAG_DOCUMENT').sum(axis=1)
    df['HAS_DOWN_PAYMENT'] = (df['AMT_CREDIT'] <= df['AMT_GOODS_PRICE']).astype(int)             # NB 03 Q6
    df['ADDRESS_MISMATCH_CNT'] = df[['REG_REGION_NOT_LIVE_REGION', 'REG_REGION_NOT_WORK_REGION', 'LIVE_REGION_NOT_WORK_REGION',
                                     'REG_CITY_NOT_LIVE_CITY', 'REG_CITY_NOT_WORK_CITY', 'LIVE_CITY_NOT_WORK_CITY']].sum(axis=1)  # NB 03 Q10
    if 'BUREAU_ACTIVE_DEBT_SUM' in df.columns:                                                       # NB 03 Q12
        df['BUREAU_DEBT_INCOME'] = df['BUREAU_ACTIVE_DEBT_SUM'].fillna(0) / df['AMT_INCOME_TOTAL']

    df = df.drop(columns=DAYS_COLS)
    return df.replace([np.inf, -np.inf], np.nan)


def information_value(x: pd.Series, y: pd.Series, bins: int = 10) -> float:
    """Information Value (Siddiqi, 2017). Nilai kosong diperlakukan sebagai kelompok tersendiri."""
    d = pd.DataFrame({'x': x.values, 'y': y.values})
    if pd.api.types.is_numeric_dtype(d['x']) and d['x'].nunique() > bins:
        d['bin'] = pd.qcut(d['x'], bins, duplicates='drop').astype(str)
    else:
        d['bin'] = d['x'].astype(str)
    d.loc[d['x'].isna(), 'bin'] = 'Kosong'
    g = d.groupby('bin')['y'].agg(bad='sum', total='count')
    g['good'] = g['total'] - g['bad']
    db = (g['bad'] + 0.5) / g['bad'].sum()
    dg = (g['good'] + 0.5) / g['good'].sum()
    return float(((dg - db) * np.log(dg / db)).sum())


class Winsorizer(BaseEstimator, TransformerMixin):
    """Membatasi nilai ekstrem pada persentil bawah/atas yang dipelajari dari data train saja."""
    def __init__(self, lower: float = 0.01, upper: float = 0.99):
        self.lower, self.upper = lower, upper

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        self.lo_ = np.nanquantile(X, self.lower, axis=0)
        self.hi_ = np.nanquantile(X, self.upper, axis=0)
        return self

    def transform(self, X):
        return np.clip(np.asarray(X, dtype=float), self.lo_, self.hi_)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(input_features)


class ToCategory(BaseEstimator, TransformerMixin):
    """Ubah kolom teks menjadi tipe 'category' dengan daftar kategori yang dipelajari dari train (untuk LightGBM)."""
    def __init__(self, cat_cols=None):
        self.cat_cols = cat_cols

    def fit(self, X, y=None):
        self.categories_ = {c: pd.Categorical(X[c].dropna()).categories for c in self.cat_cols}
        return self

    def transform(self, X):
        X = X.copy()
        for c in self.cat_cols:
            X[c] = pd.Categorical(X[c], categories=self.categories_[c])
        return X


class ColumnSelector(BaseEstimator, TransformerMixin):
    """Memilih subset kolom, sehingga pipeline bisa menerima seluruh data mentah hasil clean_and_engineer."""
    def __init__(self, cols=None):
        self.cols = cols

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X[self.cols]


# =====================================================================
# Seleksi kolom berbasis domain (dipakai semua model)
# =====================================================================
def domain_drop_columns(columns):
    """
    Kolom yang dibuang sebelum modeling, beserta alasannya.
    Mengembalikan dict {kolom: alasan}.
    """
    reasons = {}
    for c in columns:
        if c in ('SK_ID_CURR', 'TARGET'):
            continue
        if c == 'CODE_GENDER':
            reasons[c] = 'Keadilan: tidak boleh menjadi dasar keputusan kredit (POJK 22/2023)'
        elif c.endswith(('_MODE', '_MEDI')) and c not in ('FONDKAPREMONT_MODE', 'HOUSETYPE_MODE', 'WALLSMATERIAL_MODE', 'EMERGENCYSTATE_MODE'):
            reasons[c] = 'Redundan: versi _MODE/_MEDI berkorelasi > 0,99 dengan versi _AVG (NB 03 Bagian 3.5)'
        elif c.startswith('FLAG_DOCUMENT_'):
            reasons[c] = 'Diringkas menjadi DOC_COUNT; masing-masing kolom IV < 0,02 (NB 03 Bagian 3.7)'
        elif c in ('FLAG_MOBIL', 'FLAG_CONT_MOBILE'):
            reasons[c] = 'Hampir konstan (> 99% bernilai sama), tidak membawa informasi'
        elif c in ('WEEKDAY_APPR_PROCESS_START', 'HOUR_APPR_PROCESS_START'):
            reasons[c] = 'Atribut proses pengajuan, bukan profil kelayakan kredit; rawan berubah jika proses operasional berubah'
        elif c in ('OBS_60_CNT_SOCIAL_CIRCLE', 'DEF_60_CNT_SOCIAL_CIRCLE'):
            reasons[c] = 'Redundan dengan versi 30 hari (korelasi 0,85-0,99, NB 03 Bagian 3.5)'
        elif c == 'REGION_RATING_CLIENT':
            reasons[c] = 'Redundan dengan REGION_RATING_CLIENT_W_CITY (VIF 10,7, NB 03 Bagian 3.6)'
        elif c == 'AMT_GOODS_PRICE':
            reasons[c] = 'Redundan dengan AMT_CREDIT (VIF 115, NB 03 Bagian 3.6); informasinya disimpan di rasio CREDIT_GOODS'
    return reasons


EDUCATION_ORDER = ['Lower secondary', 'Secondary / secondary special', 'Incomplete higher', 'Higher education', 'Academic degree']


def column_groups(X: pd.DataFrame, high_card: int = 10, skew_limit: float = 1.0) -> dict:
    """
    Kelompokkan kolom berdasarkan tipe & sifat datanya (ditentukan dari data TRAIN saja).
      binary     : angka 0/1 (penanda)                 -> imputasi modus, tanpa scaling
      ordinal    : kategori berurutan (pendidikan)     -> ordinal encoding sesuai urutan
      cat_low    : kategori <= high_card nilai         -> one-hot
      cat_high   : kategori >  high_card nilai         -> target encoding (cross-fitted)
      num_log    : angka >= 0 dan menceng (skew > 1)   -> winsorize, log1p, StandardScaler
      num_robust : angka bisa negatif dan menceng      -> winsorize, RobustScaler
      num_std    : angka relatif simetris              -> StandardScaler
    """
    g = {k: [] for k in ['binary', 'ordinal', 'cat_low', 'cat_high', 'num_log', 'num_robust', 'num_std']}
    for c in X.columns:
        s = X[c]
        if not pd.api.types.is_numeric_dtype(s):
            if c == 'NAME_EDUCATION_TYPE':
                g['ordinal'].append(c)
            elif s.nunique() > high_card:
                g['cat_high'].append(c)
            else:
                g['cat_low'].append(c)
            continue
        vals = s.dropna().unique()
        if len(vals) <= 2 and set(np.unique(vals)).issubset({0, 1}):
            g['binary'].append(c)
        elif abs(s.skew()) > skew_limit:
            g['num_log' if s.min() >= 0 else 'num_robust'].append(c)
        else:
            g['num_std'].append(c)
    return g


def build_preprocessor(groups: dict):
    """Satu ColumnTransformer untuk semua model; setiap kelompok kolom diproses sesuai sifatnya."""
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer, MissingIndicator
    from sklearn.preprocessing import (StandardScaler, RobustScaler, FunctionTransformer, OneHotEncoder,
                                       OrdinalEncoder, TargetEncoder)
    num_all = groups['num_log'] + groups['num_robust'] + groups['num_std']
    return ColumnTransformer([
        ('num_log', Pipeline([('impute', SimpleImputer(strategy='median')), ('winsor', Winsorizer()),
                              ('log', FunctionTransformer(np.log1p, feature_names_out='one-to-one')),
                              ('scale', StandardScaler())]), groups['num_log']),
        ('num_robust', Pipeline([('impute', SimpleImputer(strategy='median')), ('winsor', Winsorizer()),
                                 ('scale', RobustScaler())]), groups['num_robust']),
        ('num_std', Pipeline([('impute', SimpleImputer(strategy='median')), ('scale', StandardScaler())]), groups['num_std']),
        ('missing_flag', MissingIndicator(features='missing-only', error_on_new=False), num_all),
        ('binary', SimpleImputer(strategy='most_frequent'), groups['binary']),
        ('ordinal', Pipeline([('impute', SimpleImputer(strategy='most_frequent')),
                              ('encode', OrdinalEncoder(categories=[EDUCATION_ORDER], handle_unknown='use_encoded_value',
                                                        unknown_value=-1))]), groups['ordinal']),
        ('cat_low', Pipeline([('impute', SimpleImputer(strategy='constant', fill_value='Missing')),
                              ('encode', OneHotEncoder(drop='if_binary', handle_unknown='infrequent_if_exist',
                                                       min_frequency=0.005, sparse_output=False))]), groups['cat_low']),
        ('cat_high', Pipeline([('impute', SimpleImputer(strategy='constant', fill_value='Missing')),
                               ('encode', TargetEncoder(target_type='binary', cv=5))]), groups['cat_high']),
    ], verbose_feature_names_out=True)
