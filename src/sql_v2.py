"""
Query SQL agregasi fitur riwayat (versi 2) untuk data mart.
Ditulis dengan SQL standar yang kompatibel dengan BigQuery dan DuckDB.
`R(nama_tabel)` mengembalikan nama tabel lengkap (mis. `project.dataset.tabel` di BigQuery).
"""


def sql_agg_v2(R):
    return {

        # ---------------- Installments: perilaku membayar cicilan ----------------
        'agg_inst_v2': f"""
WITH i AS (
  SELECT SK_ID_CURR, DAYS_INSTALMENT, AMT_INSTALMENT, AMT_PAYMENT,
         CASE WHEN DAYS_ENTRY_PAYMENT IS NULL THEN NULL ELSE GREATEST(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT, 0) END AS DPD,
         CASE WHEN DAYS_ENTRY_PAYMENT IS NULL THEN NULL ELSE GREATEST(DAYS_INSTALMENT - DAYS_ENTRY_PAYMENT, 0) END AS DBD,
         AMT_INSTALMENT - AMT_PAYMENT AS PAY_DIFF
  FROM {R('installments_payments')})
SELECT SK_ID_CURR,
  COUNT(*)                                                         AS INST_CNT,
  AVG(DPD)                                                         AS INST_DPD_MEAN,
  MAX(DPD)                                                         AS INST_DPD_MAX,
  AVG(DBD)                                                         AS INST_DBD_MEAN,
  AVG(CASE WHEN DPD > 0 THEN 1 ELSE 0 END)                         AS INST_LATE_RATE,
  AVG(CASE WHEN DPD > 30 THEN 1 ELSE 0 END)                        AS INST_LATE30_RATE,
  SUM(PAY_DIFF)                                                    AS INST_PAY_DIFF_SUM,
  AVG(AMT_PAYMENT / NULLIF(AMT_INSTALMENT, 0))                     AS INST_PAYMENT_RATIO_MEAN,
  AVG(CASE WHEN AMT_PAYMENT < AMT_INSTALMENT THEN 1 ELSE 0 END)    AS INST_UNDERPAY_RATE,
  AVG(CASE WHEN DAYS_INSTALMENT >= -365 THEN DPD END)              AS INST_DPD_MEAN_12M,
  AVG(CASE WHEN DAYS_INSTALMENT >= -365 THEN (CASE WHEN DPD > 0 THEN 1 ELSE 0 END) END) AS INST_LATE_RATE_12M,
  AVG(CASE WHEN DAYS_INSTALMENT >= -365 THEN PAY_DIFF END)         AS INST_PAY_DIFF_MEAN_12M,
  MAX(DAYS_INSTALMENT)                                             AS INST_DAYS_LAST
FROM i GROUP BY SK_ID_CURR""",

        # ---------------- Bureau: utang di lembaga lain ----------------
        'agg_bureau_v2': f"""
WITH bb AS (
  SELECT SK_ID_BUREAU,
         MAX(CASE STATUS WHEN '1' THEN 1 WHEN '2' THEN 2 WHEN '3' THEN 3 WHEN '4' THEN 4 WHEN '5' THEN 5 ELSE 0 END) AS WORST_STATUS,
         AVG(CASE WHEN STATUS IN ('1','2','3','4','5') THEN 1 ELSE 0 END) AS DPD_MONTH_RATE,
         AVG(CASE WHEN MONTHS_BALANCE >= -12 THEN (CASE WHEN STATUS IN ('1','2','3','4','5') THEN 1 ELSE 0 END) END) AS DPD_MONTH_RATE_12M
  FROM {R('bureau_balance')} GROUP BY SK_ID_BUREAU)
SELECT b.SK_ID_CURR,
  COUNT(*)                                                                      AS BUREAU_CNT,
  SUM(CASE WHEN b.CREDIT_ACTIVE = 'Active' THEN 1 ELSE 0 END)                   AS BUREAU_ACTIVE_CNT,
  SUM(CASE WHEN b.CREDIT_ACTIVE = 'Bad debt' THEN 1 ELSE 0 END)                 AS BUREAU_BAD_DEBT_CNT,
  SUM(CASE WHEN b.CREDIT_ACTIVE = 'Active' THEN b.AMT_CREDIT_SUM END)           AS BUREAU_ACTIVE_CREDIT_SUM,
  SUM(CASE WHEN b.CREDIT_ACTIVE = 'Active' THEN b.AMT_CREDIT_SUM_DEBT END)      AS BUREAU_ACTIVE_DEBT_SUM,
  SUM(CASE WHEN b.CREDIT_ACTIVE = 'Active' THEN b.AMT_CREDIT_SUM_DEBT END)
    / NULLIF(SUM(CASE WHEN b.CREDIT_ACTIVE = 'Active' THEN b.AMT_CREDIT_SUM END), 0) AS BUREAU_ACTIVE_DEBT_RATIO,
  SUM(b.AMT_CREDIT_SUM_OVERDUE)                                                 AS BUREAU_OVERDUE_SUM,
  MAX(b.AMT_CREDIT_MAX_OVERDUE)                                                 AS BUREAU_MAX_OVERDUE,
  MAX(b.CREDIT_DAY_OVERDUE)                                                     AS BUREAU_DAY_OVERDUE_MAX,
  SUM(b.CNT_CREDIT_PROLONG)                                                     AS BUREAU_PROLONG_SUM,
  AVG(b.DAYS_CREDIT)                                                            AS BUREAU_DAYS_CREDIT_MEAN,
  MAX(b.DAYS_CREDIT)                                                            AS BUREAU_DAYS_CREDIT_LAST,
  MIN(b.DAYS_CREDIT)                                                            AS BUREAU_DAYS_CREDIT_FIRST,
  AVG(b.DAYS_CREDIT_ENDDATE)                                                    AS BUREAU_DAYS_ENDDATE_MEAN,
  SUM(CASE WHEN b.DAYS_CREDIT >= -365 THEN 1 ELSE 0 END)                        AS BUREAU_CNT_12M,
  SUM(CASE WHEN b.CREDIT_TYPE = 'Credit card' THEN 1 ELSE 0 END)                AS BUREAU_CREDIT_CARD_CNT,
  SUM(CASE WHEN b.CREDIT_TYPE = 'Microloan' THEN 1 ELSE 0 END)                  AS BUREAU_MICROLOAN_CNT,
  MAX(bb.WORST_STATUS)                                                          AS BUREAU_WORST_STATUS,
  AVG(bb.DPD_MONTH_RATE)                                                        AS BUREAU_DPD_MONTH_RATE,
  AVG(bb.DPD_MONTH_RATE_12M)                                                    AS BUREAU_DPD_MONTH_RATE_12M
FROM {R('bureau')} b LEFT JOIN bb ON b.SK_ID_BUREAU = bb.SK_ID_BUREAU
GROUP BY b.SK_ID_CURR""",

        # ---------------- Previous application: riwayat pengajuan ----------------
        'agg_prev_v2': f"""
WITH p AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY SK_ID_CURR ORDER BY DAYS_DECISION DESC) AS rn
  FROM {R('previous_application')})
SELECT SK_ID_CURR,
  COUNT(*)                                                                         AS PREV_CNT,
  AVG(CASE WHEN NAME_CONTRACT_STATUS = 'Refused' THEN 1 ELSE 0 END)                AS PREV_REFUSED_RATE,
  AVG(CASE WHEN NAME_CONTRACT_STATUS = 'Approved' THEN 1 ELSE 0 END)               AS PREV_APPROVED_RATE,
  SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Refused' AND DAYS_DECISION >= -365 THEN 1 ELSE 0 END) AS PREV_REFUSED_CNT_12M,
  SUM(CASE WHEN DAYS_DECISION >= -365 THEN 1 ELSE 0 END)                           AS PREV_CNT_12M,
  AVG(AMT_CREDIT)                                                                  AS PREV_AMT_CREDIT_MEAN,
  AVG(CASE WHEN NAME_CONTRACT_STATUS = 'Approved' THEN AMT_CREDIT / NULLIF(AMT_APPLICATION, 0) END) AS PREV_APPROVED_CREDIT_APP_RATIO,
  AVG(CNT_PAYMENT)                                                                 AS PREV_CNT_PAYMENT_MEAN,
  AVG(RATE_DOWN_PAYMENT)                                                           AS PREV_RATE_DOWN_PAYMENT_MEAN,
  AVG(CASE WHEN NAME_YIELD_GROUP = 'high' THEN 1 ELSE 0 END)                       AS PREV_HIGH_YIELD_RATE,
  AVG(AMT_ANNUITY)                                                                 AS PREV_AMT_ANNUITY_MEAN,
  MAX(DAYS_DECISION)                                                               AS PREV_DAYS_LAST_DECISION,
  MAX(CASE WHEN rn = 1 AND NAME_CONTRACT_STATUS = 'Refused' THEN 1 ELSE 0 END)     AS PREV_LAST_REFUSED,
  MAX(CASE WHEN NAME_CONTRACT_STATUS = 'Approved' AND DAYS_LAST_DUE_1ST_VERSION <> 365243 THEN DAYS_LAST_DUE_1ST_VERSION END) AS PREV_DAYS_LAST_DUE_MAX   -- 365243 = kode sistem (tidak ada tanggal)
FROM p GROUP BY SK_ID_CURR""",

        # ---------------- POS / cash: tunggakan bulanan ----------------
        'agg_pos_v2': f"""
SELECT SK_ID_CURR,
  COUNT(*)                                                          AS POS_MONTHS_CNT,
  MAX(SK_DPD)                                                       AS POS_DPD_MAX,
  MAX(SK_DPD_DEF)                                                   AS POS_DPD_DEF_MAX,
  AVG(CASE WHEN SK_DPD > 0 THEN 1 ELSE 0 END)                       AS POS_DPD_RATE,
  AVG(CASE WHEN MONTHS_BALANCE >= -12 THEN (CASE WHEN SK_DPD > 0 THEN 1 ELSE 0 END) END) AS POS_DPD_RATE_12M,
  AVG(CASE WHEN MONTHS_BALANCE >= -12 THEN CNT_INSTALMENT_FUTURE END) AS POS_INST_FUTURE_MEAN_12M,
  SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Completed' THEN 1 ELSE 0 END) AS POS_COMPLETED_CNT
FROM {R('pos_cash_balance')} GROUP BY SK_ID_CURR""",

        # ---------------- Kartu kredit: pemakaian limit & pembayaran ----------------
        'agg_cc_v2': f"""
SELECT SK_ID_CURR,
  COUNT(*)                                                                          AS CC_MONTHS_CNT,
  AVG(AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0))                             AS CC_UTILIZATION_MEAN,
  AVG(CASE WHEN MONTHS_BALANCE >= -6 THEN AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0) END) AS CC_UTILIZATION_6M,
  MAX(AMT_BALANCE / NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0))                             AS CC_UTILIZATION_MAX,
  AVG(AMT_PAYMENT_CURRENT / NULLIF(AMT_INST_MIN_REGULARITY, 0))                     AS CC_PAY_MIN_RATIO_MEAN,
  AVG(AMT_DRAWINGS_CURRENT)                                                         AS CC_DRAWINGS_MEAN,
  AVG(CNT_DRAWINGS_ATM_CURRENT)                                                     AS CC_ATM_DRAWINGS_CNT_MEAN,
  MAX(SK_DPD)                                                                       AS CC_DPD_MAX,
  MAX(SK_DPD_DEF)                                                                   AS CC_DPD_DEF_MAX
FROM {R('credit_card_balance')} GROUP BY SK_ID_CURR""",
    }


def sql_mart_v2(R, M, app_table, except_kw='EXCEPT'):
    """Gabungkan tabel aplikasi dengan seluruh agregasi v2. DuckDB memakai EXCLUDE, BigQuery memakai EXCEPT."""
    j = lambda a: f"{a}.* {except_kw}(SK_ID_CURR)"
    return f"""
SELECT a.*, {j('b')}, {j('p')}, {j('i')}, {j('pc')}, {j('c')}
FROM {R(app_table)} a
LEFT JOIN {M('agg_bureau_v2')} b  USING (SK_ID_CURR)
LEFT JOIN {M('agg_prev_v2')}   p  USING (SK_ID_CURR)
LEFT JOIN {M('agg_inst_v2')}   i  USING (SK_ID_CURR)
LEFT JOIN {M('agg_pos_v2')}    pc USING (SK_ID_CURR)
LEFT JOIN {M('agg_cc_v2')}     c  USING (SK_ID_CURR)"""
