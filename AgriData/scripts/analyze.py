# -*- coding: utf-8 -*-
"""
AgriData 資料清理與分析指標計算
輸入：data/veg_taipei_raw.csv
輸出：data/veg_taipei_clean.csv、data/veg_stats.csv
"""

import os
import re
import pandas as pd

DATA_DIR   = os.path.join(os.path.dirname(__file__), '..', 'data')
RAW_FILE   = os.path.join(DATA_DIR, 'veg_taipei_raw.csv')
CLEAN_FILE = os.path.join(DATA_DIR, 'veg_taipei_clean.csv')
STATS_FILE = os.path.join(DATA_DIR, 'veg_stats.csv')

# 常見燙青菜清單（待確認後填入，目前停用）
BLANCHED_VEGS = []


def roc_to_ad_year(roc_str):
    """從民國年字串取出西元年整數，例如 '113/05/01' → 2024"""
    try:
        parts = re.split(r'[/.-]', str(roc_str).strip())
        return int(parts[0]) + 1911
    except Exception:
        return None


def load_and_clean(path: str) -> pd.DataFrame:
    """載入原始 CSV，清理並轉換欄位"""
    df = pd.read_csv(path, encoding='utf-8-sig', low_memory=False)
    print(f"原始資料：{len(df):,} 筆，欄位：{list(df.columns)}")

    # 移除小計列（產品欄位為「小計」或含 NaN 的資料列）
    # 實際欄位名稱：日期、市場、產品、上價、中價、下價、平均價 (元/公斤)、交易量 (公斤)
    crop_col = '產品' if '產品' in df.columns else '作物名稱'
    df = df[df[crop_col].notna()]
    df = df[~df[crop_col].astype(str).str.contains('小計|合計')]

    # 重新命名欄位（統一英文）
    rename_map = {
        '日期'              : 'date_roc',
        '交易日期'           : 'date_roc',
        '市場'              : 'market',
        '市場名稱'           : 'market',
        '產品'              : 'crop',
        '作物名稱'           : 'crop',
        '上價'              : 'price_high',
        '中價'              : 'price_mid',
        '下價'              : 'price_low',
        '平均價 (元/公斤)'   : 'avg_price',
        '平均價(元/公斤)'    : 'avg_price',
        '交易量 (公斤)'      : 'volume',
        '交易量(公斤)'       : 'volume',
    }
    # 只 rename 存在的欄位
    rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # 西元年
    df['year'] = df['date_roc'].apply(roc_to_ad_year)

    # 月份（從 _month 欄位，格式 '113/05'）
    if '_month' in df.columns:
        df['month_roc'] = df['_month']
        df['year_month'] = df['_month'].apply(
            lambda s: f"{int(str(s)[:3]) + 1911}/{str(s)[4:6]}" if pd.notna(s) else None
        )

    # 數值型態轉換
    for col in ['avg_price', 'volume', 'price_high', 'price_mid', 'price_low']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 過濾無效均價
    df = df[df['avg_price'].notna() & (df['avg_price'] > 0)]

    # 移除交易量為 0 或 NaN 的列
    if 'volume' in df.columns:
        df = df[df['volume'].notna() & (df['volume'] > 0)]

    # 標注是否為常見燙青菜
    df['is_blanched'] = df['crop'].apply(
        lambda c: any(v in str(c) for v in BLANCHED_VEGS)
    )

    df = df.reset_index(drop=True)
    print(f"清理後資料：{len(df):,} 筆")
    return df


def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    """對每種作物計算分析指標

    均價：交易量加權，全期 + 分兩年
    CV  ：不加權，分兩年（每日價格波動程度，不受整體漲跌影響）
    交易量：日均量 = 總量 ÷ 供貨天數
    供貨率：有交易日數 ÷ 資料期間總日數
    上下價差率：全期平均（品質結構特性，不分年）
    """
    # 年份分界：第一年 2024/05~2025/04，第二年 2025/05~2026/05
    CUTOFF = '2025/05'
    df_y1 = df[df['year_month'] < CUTOFF].copy()
    df_y2 = df[df['year_month'] >= CUTOFF].copy()
    total_days = df['date_roc'].nunique()   # 資料期間不重複總天數

    # ── 交易量加權均價 ──────────────────────────────────────────
    # 先算 price × volume，再 groupby 加總相除
    def wavg(sub):
        """交易量加權均價"""
        vol = sub['volume'].sum()
        return (sub['avg_price'] * sub['volume']).sum() / vol if vol > 0 else float('nan')

    wavg_all = df.groupby('crop').apply(wavg, include_groups=False)
    wavg_y1  = df_y1.groupby('crop').apply(wavg, include_groups=False)
    wavg_y2  = df_y2.groupby('crop').apply(wavg, include_groups=False)

    # ── CV（不加權：反映每日價格是否穩定，不管交易量大小）───────
    def cv(series):
        m = series.mean()
        return series.std() / m if m > 0 else float('nan')

    cv_y1 = df_y1.groupby('crop')['avg_price'].agg(cv)
    cv_y2 = df_y2.groupby('crop')['avg_price'].agg(cv)

    # ── 基本量統計 ───────────────────────────────────────────────
    grp = df.groupby('crop')
    total_volume = grp['volume'].sum()
    trade_days   = grp['date_roc'].nunique()

    # ── 合併成一張表 ─────────────────────────────────────────────
    stats = pd.DataFrame({
        'wavg_price'   : wavg_all,
        'wavg_price_y1': wavg_y1,
        'wavg_price_y2': wavg_y2,
        'price_cv_y1'  : cv_y1,
        'price_cv_y2'  : cv_y2,
        'total_volume' : total_volume,
        'trade_days'   : trade_days,
        'is_blanched'  : grp['is_blanched'].first(),
    }).reset_index()

    stats['avg_daily_volume'] = stats['total_volume'] / stats['trade_days']
    stats['availability']     = stats['trade_days'] / total_days

    # ── 上下價差率（品質分散度，全期平均）──────────────────────
    if 'price_high' in df.columns and 'price_low' in df.columns:
        df_v = df[df['avg_price'] > 0].copy()
        df_v['spread_ratio'] = (df_v['price_high'] - df_v['price_low']) / df_v['avg_price']
        spread = df_v.groupby('crop')['spread_ratio'].mean()
        stats = stats.merge(spread.rename('price_spread_ratio'), on='crop', how='left')
    else:
        stats['price_spread_ratio'] = float('nan')

    # 排序：總交易量由大到小
    stats = stats.sort_values('total_volume', ascending=False).reset_index(drop=True)

    print(f"\n分析指標計算完成：{len(stats)} 種作物")
    print(f"  （第一年 < {CUTOFF}，第二年 >= {CUTOFF}）")
    print("\n  交易量 Top 10：")
    for _, row in stats.head(10).iterrows():
        print(f"    {row['crop']:<14}"
              f"均價(全)={row['wavg_price']:5.1f}  "
              f"Y1={row['wavg_price_y1']:5.1f}  Y2={row['wavg_price_y2']:5.1f}  "
              f"CV_Y1={row['price_cv_y1']:.2f}  CV_Y2={row['price_cv_y2']:.2f}  "
              f"供貨率={row['availability']:.2f}")
    return stats


def main():
    df    = load_and_clean(RAW_FILE)
    df.to_csv(CLEAN_FILE, index=False, encoding='utf-8-sig')
    print(f"\n已儲存：{CLEAN_FILE}")

    stats = compute_stats(df)
    stats.to_csv(STATS_FILE, index=False, encoding='utf-8-sig')
    print(f"已儲存：{STATS_FILE}")


if __name__ == '__main__':
    main()
