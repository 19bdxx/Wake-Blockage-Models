#!/usr/bin/env python3
# pywake_integration/forecast_run.py
"""
forecast_run.py — 基于气象预报数据运行 PyWake 全场尾流 + 阻塞效应实验

输入
----
    场站气象预报/wind_lat_21.250_lon_111.500.csv
    列：valid_time, latitude, longitude, u100, v100, wind_speed, wind_direction,
        is_interpolated

思路
----
1. 读取气象预报（全年 2024，15 分钟间隔，共 ~35133 条）
2. 将风速/风向离散到 WD 分格（30° 间隔）× WS 分格（1 m/s 间隔），
   共约 123 个唯一组合，避免逐时步运行 PyWake（35133 次 → 123×2=246 次）
3. 对每个 (WD_bin, WS_bin) 组合分别运行：
       blockage ON  → 全场总功率、全场平均 WS_eff
       blockage OFF → 全场总功率、全场平均 WS_eff
4. 将分格结果映射回完整时间序列
5. 输出 CSV + Markdown 报告 + 多幅图表

输出目录
--------
    pywake_integration/forecast_output/
        forecast_time_series.csv      全年逐 15 分钟总功率（ON/OFF）
        forecast_bin_results.csv      各分格的 PyWake 结果
        figures/                      图表
        forecast_report.md            分析报告
"""

from __future__ import annotations

import sys
import os
import time
import textwrap
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

warnings.filterwarnings('ignore')

# ── 路径设置 ──────────────────────────────────────────────────────────────────
_THIS_DIR  = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)

if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from config          import IntegrationConfig, resolve_core_python_dir, resolve_forecast_csv_path
from wind_farm_setup import build_wind_farm_model, turbine_id_to_type
from run_integration import load_layout, check_turbine_model_consistency

_PY_DIR = resolve_core_python_dir("")

# ── 输出目录 ──────────────────────────────────────────────────────────────────
_OUT_ROOT   = os.path.join(_THIS_DIR, 'forecast_output')
_FIG_DIR    = os.path.join(_OUT_ROOT, 'figures')
_TABLE_DIR  = os.path.join(_OUT_ROOT)
os.makedirs(_FIG_DIR,   exist_ok=True)
os.makedirs(_TABLE_DIR, exist_ok=True)

# ── 预报文件 ──────────────────────────────────────────────────────────────────
_FORECAST_CSV = resolve_forecast_csv_path("")

# ── 分格参数 ──────────────────────────────────────────────────────────────────
WD_BIN_SIZE = 30.0   # 风向分格宽度（°）
WS_BIN_SIZE = 1.0    # 风速分格宽度（m/s）
WS_CUT_IN   = 3.0    # 切入风速（m/s）：低于此值功率=0，跳过 PyWake
WS_CUT_OUT  = 25.0   # 切出风速（m/s）：高于此值功率=0，跳过 PyWake

# ── PyWake 配置 ───────────────────────────────────────────────────────────────
_CFG_ON  = IntegrationConfig(enable_blockage=True,  rotor_avg_n=4,
                              enable_turbulence_model=True)
_CFG_OFF = IntegrationConfig(enable_blockage=False, rotor_avg_n=4,
                              enable_turbulence_model=True)

_WS_COL = "WS_eff_pywake_native_m_s"

# ── 月份标签 ──────────────────────────────────────────────────────────────────
_MONTH_NAMES = ['一月','二月','三月','四月','五月','六月',
                '七月','八月','九月','十月','十一月','十二月']


# ══════════════════════════════════════════════════════════════════════════════
#  1. 读取预报数据
# ══════════════════════════════════════════════════════════════════════════════

def load_forecast() -> pd.DataFrame:
    """读取气象预报 CSV，解析时间列，添加 WD/WS 分格列。"""
    df = pd.read_csv(_FORECAST_CSV, parse_dates=['valid_time'])
    df = df.sort_values('valid_time').reset_index(drop=True)

    # WD 分格：将 360 映射到 0
    df['wd_bin'] = (np.floor(df['wind_direction'] / WD_BIN_SIZE) * WD_BIN_SIZE).astype(float)
    df.loc[df['wd_bin'] >= 360.0, 'wd_bin'] = 0.0

    # WS 分格（1 m/s，向下取整）
    df['ws_bin'] = np.floor(df['wind_speed'] / WS_BIN_SIZE).astype(float) * WS_BIN_SIZE

    # 月份
    df['month'] = df['valid_time'].dt.month
    return df


# ══════════════════════════════════════════════════════════════════════════════
#  2. 运行 PyWake 分格结果
# ══════════════════════════════════════════════════════════════════════════════

def run_bin(wfm, x_wt, y_wt, types_arr, wd: float, ws: float) -> tuple[np.ndarray, np.ndarray]:
    """
    对给定 (wd, ws) 分格运行 PyWake。

    返回
    ----
    (power_per_turbine_W, ws_eff_per_turbine_m_s)  各长度 n_turbines 的 ndarray
    """
    ws_center = ws + WS_BIN_SIZE / 2.0

    sim = wfm(
        np.asarray(x_wt, dtype=float),
        np.asarray(y_wt, dtype=float),
        type=types_arr,
        wd=[float(wd)],
        ws=[float(ws_center)],
    )

    power  = sim.Power.values
    ws_eff = sim.WS_eff.values

    if power.ndim == 3:
        power_flat  = power[:, 0, 0]
        ws_eff_flat = ws_eff[:, 0, 0]
    else:
        power_flat  = power.flatten()
        ws_eff_flat = ws_eff.flatten()

    return np.asarray(power_flat, dtype=float), np.clip(np.asarray(ws_eff_flat, dtype=float), 0.0, None)


def run_all_bins(
    layout: pd.DataFrame,
    forecast: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    对所有出现在预报中的 (wd_bin, ws_bin) 组合分别运行 blockage ON 和 OFF。

    返回
    ----
    (farm_bin_results, turbine_bin_results) 两个 DataFrame

    farm_bin_results 列：
        wd_bin, ws_bin, ws_center,
        total_power_on_MW, mean_WS_eff_pywake_native_on_m_s,
        total_power_off_MW, mean_WS_eff_pywake_native_off_m_s, count

    turbine_bin_results 列：
        turbine_id, station, turbine_model, station_slot,
        wd_bin, ws_bin, ws_center,
        power_on_kW, WS_eff_pywake_native_on_m_s,
        power_off_kW, WS_eff_pywake_native_off_m_s
    """
    if _PY_DIR not in sys.path:
        sys.path.insert(0, _PY_DIR)
    import turbine_model as tm_mod

    x_wt      = layout['x'].values.astype(float)
    y_wt      = layout['y'].values.astype(float)
    t_ids     = layout['turbine_id'].values.astype(int)
    types_arr = np.array([turbine_id_to_type(int(t), _PY_DIR) for t in t_ids], dtype=int)

    # 风机元信息（station, model, slot）
    station_arr = layout['station'].values     if 'station'      in layout.columns else np.full(len(t_ids), '')
    model_arr   = layout['turbine_model'].values if 'turbine_model' in layout.columns else np.full(len(t_ids), '')
    slot_arr    = layout['station_slot'].values  if 'station_slot'  in layout.columns else np.full(len(t_ids), '')

    print("  检查风机型号一致性…")
    check_turbine_model_consistency(_PY_DIR)
    print("  构建 PyWake 模型（blockage ON）…")
    wfm_on  = build_wind_farm_model(_CFG_ON)
    print("  构建 PyWake 模型（blockage OFF）…")
    wfm_off = build_wind_farm_model(_CFG_OFF)

    # 唯一分格（过滤无效风速）
    bins_df = (
        forecast[
            (forecast['wind_speed'] >= WS_CUT_IN) &
            (forecast['wind_speed'] <  WS_CUT_OUT)
        ]
        .groupby(['wd_bin', 'ws_bin'])
        .size()
        .reset_index(name='count')
        .sort_values(['wd_bin', 'ws_bin'])
        .reset_index(drop=True)
    )

    n_bins     = len(bins_df)
    n_turbines = len(t_ids)
    print(f"  需要运行的 (WD, WS) 分格数：{n_bins}  （blockage ON + OFF = {2*n_bins} 次）")
    print(f"  风机数量：{n_turbines} 台，涉及电厂：{sorted(set(station_arr))}")

    farm_results    = []
    turbine_records = []   # 收集所有 (bin × turbine) 行
    t0 = time.time()

    for idx, row in bins_df.iterrows():
        wd, ws = float(row['wd_bin']), float(row['ws_bin'])
        ws_c   = ws + WS_BIN_SIZE / 2.0

        pwr_on_arr,  wse_on_arr  = run_bin(wfm_on,  x_wt, y_wt, types_arr, wd, ws)
        pwr_off_arr, wse_off_arr = run_bin(wfm_off, x_wt, y_wt, types_arr, wd, ws)

        total_on  = float(pwr_on_arr.sum())  / 1e6   # W → MW
        total_off = float(pwr_off_arr.sum()) / 1e6
        mean_on   = float(wse_on_arr.mean())
        mean_off  = float(wse_off_arr.mean())

        elapsed = time.time() - t0
        remain  = elapsed / (idx + 1) * (n_bins - idx - 1) if idx > 0 else 0
        print(f"  [{idx+1:3d}/{n_bins}] WD={wd:5.1f}° WS={ws_c:4.1f} m/s  "
              f"ON={total_on:.1f} MW  OFF={total_off:.1f} MW  "
              f"剩余~{remain:.0f}s", flush=True)

        farm_results.append({
            'wd_bin':            wd,
            'ws_bin':            ws,
            'ws_center':         ws_c,
            'total_power_on_MW': total_on,
            'mean_WS_eff_pywake_native_on_m_s':  mean_on,
            'total_power_off_MW':total_off,
            'mean_WS_eff_pywake_native_off_m_s': mean_off,
            'count':             int(row['count']),
        })

        # 逐台风机记录（kW，不是 MW）
        for i in range(n_turbines):
            turbine_records.append({
                'turbine_id':     int(t_ids[i]),
                'station':        str(station_arr[i]),
                'turbine_model':  str(model_arr[i]),
                'station_slot':   str(slot_arr[i]),
                'wd_bin':         wd,
                'ws_bin':         ws,
                'ws_center':      ws_c,
                'power_on_kW':    float(pwr_on_arr[i])  / 1000.0,
                'WS_eff_pywake_native_on_m_s':  float(wse_on_arr[i]),
                'power_off_kW':   float(pwr_off_arr[i]) / 1000.0,
                'WS_eff_pywake_native_off_m_s': float(wse_off_arr[i]),
            })

    farm_df    = pd.DataFrame(farm_results)
    turbine_df = pd.DataFrame(turbine_records)
    return farm_df, turbine_df


# ══════════════════════════════════════════════════════════════════════════════
#  3. 将分格结果映射回时间序列
# ══════════════════════════════════════════════════════════════════════════════

def map_to_timeseries(
    forecast: pd.DataFrame,
    farm_bin_results: pd.DataFrame,
) -> pd.DataFrame:
    """
    将每个 15 分钟时步对应到其 (wd_bin, ws_bin) 分格的全场功率结果。

    低风速（< cut-in）和高风速（≥ cut-out）的时步功率设为 0。
    """
    bins_lookup = farm_bin_results.set_index(['wd_bin', 'ws_bin'])

    pwr_on  = np.zeros(len(forecast))
    pwr_off = np.zeros(len(forecast))
    wse_on  = np.full(len(forecast), np.nan)
    wse_off = np.full(len(forecast), np.nan)

    for i, frow in forecast.iterrows():
        ws = frow['wind_speed']
        if ws < WS_CUT_IN or ws >= WS_CUT_OUT:
            continue
        key = (frow['wd_bin'], frow['ws_bin'])
        if key in bins_lookup.index:
            br = bins_lookup.loc[key]
            pwr_on[i]  = float(br['total_power_on_MW'])
            pwr_off[i] = float(br['total_power_off_MW'])
            wse_on[i]  = float(br['mean_WS_eff_pywake_native_on_m_s'])
            wse_off[i] = float(br['mean_WS_eff_pywake_native_off_m_s'])

    ts = forecast[['valid_time', 'wind_speed', 'wind_direction',
                   'wd_bin', 'ws_bin', 'month']].copy()
    ts['total_power_on_MW']    = pwr_on
    ts['total_power_off_MW']   = pwr_off
    ts['mean_WS_eff_pywake_native_on_m_s']  = wse_on
    ts['mean_WS_eff_pywake_native_off_m_s'] = wse_off
    ts['blockage_diff_MW']     = ts['total_power_on_MW'] - ts['total_power_off_MW']
    ts['blockage_diff_pct']    = np.where(
        ts['total_power_off_MW'] > 0.01,
        100.0 * ts['blockage_diff_MW'] / ts['total_power_off_MW'],
        np.nan,
    )
    return ts


def map_to_station_timeseries(
    forecast: pd.DataFrame,
    turbine_bin_results: pd.DataFrame,
) -> pd.DataFrame:
    """
    将 (wd_bin, ws_bin) 分格的逐台风机结果映射回时间序列，
    按电厂（station）聚合为站级功率时间序列。

    输出列：
        valid_time, wind_speed, wind_direction, month,
        total_power_on_MW, total_power_off_MW,
        {station}_power_on_MW, {station}_power_off_MW  （每个电厂一对）
    """
    stations = sorted(turbine_bin_results['station'].unique())

    # 按 (wd_bin, ws_bin, station) 预计算站级功率（MW）
    station_bin = (
        turbine_bin_results
        .groupby(['wd_bin', 'ws_bin', 'station'])
        .agg(
            pwr_on_MW=('power_on_kW',  lambda x: x.sum() / 1000.0),
            pwr_off_MW=('power_off_kW', lambda x: x.sum() / 1000.0),
        )
        .reset_index()
    )

    # 为每个 (wd_bin, ws_bin) 建立查找字典：{(wd_bin, ws_bin, station) → (on, off)}
    bin_lookup: dict[tuple, dict] = {}
    for _, row in station_bin.iterrows():
        key = (row['wd_bin'], row['ws_bin'])
        if key not in bin_lookup:
            bin_lookup[key] = {}
        bin_lookup[key][row['station']] = (row['pwr_on_MW'], row['pwr_off_MW'])

    # 映射到时间序列
    n = len(forecast)
    on_cols  = {s: np.zeros(n) for s in stations}
    off_cols = {s: np.zeros(n) for s in stations}

    for i, frow in forecast.iterrows():
        ws = frow['wind_speed']
        if ws < WS_CUT_IN or ws >= WS_CUT_OUT:
            continue
        key = (frow['wd_bin'], frow['ws_bin'])
        if key not in bin_lookup:
            continue
        for s in stations:
            if s in bin_lookup[key]:
                on_v, off_v = bin_lookup[key][s]
                on_cols[s][i]  = on_v
                off_cols[s][i] = off_v

    ts = forecast[['valid_time', 'wind_speed', 'wind_direction', 'month']].copy()
    ts['total_power_on_MW']  = sum(on_cols[s]  for s in stations)
    ts['total_power_off_MW'] = sum(off_cols[s] for s in stations)
    for s in stations:
        ts[f"{s}_power_on_MW"]  = on_cols[s]
        ts[f"{s}_power_off_MW"] = off_cols[s]

    return ts


def build_turbine_annual_summary(
    turbine_bin_results: pd.DataFrame,
    forecast: pd.DataFrame,
    dt_h: float = 0.25,
) -> pd.DataFrame:
    """
    计算每台风机的年度统计（AEP、阻塞效应）。

    参数
    ----
    turbine_bin_results : 由 run_all_bins() 返回的逐台逐分格结果
    forecast            : 预报 DataFrame（含 wd_bin, ws_bin, wind_speed 列）
    dt_h                : 时步长度（小时）；默认 0.25（15 分钟）

    返回
    ----
    DataFrame 列：turbine_id, station, turbine_model, station_slot,
                  aep_on_MWh, aep_off_MWh, blockage_diff_MWh, blockage_diff_pct,
                  capacity_factor_on, capacity_factor_off,
                  max_power_on_kW, mean_power_on_kW
    """
    # 每个分格在全年中出现的小时数
    bin_hours = (
        forecast[
            (forecast['wind_speed'] >= WS_CUT_IN) &
            (forecast['wind_speed'] <  WS_CUT_OUT)
        ]
        .groupby(['wd_bin', 'ws_bin'])
        .size()
        .reset_index(name='hours')
    )
    bin_hours['hours'] = bin_hours['hours'] * dt_h  # count → hours

    # 逐台结果合并分格小时数
    merged = turbine_bin_results.merge(bin_hours, on=['wd_bin','ws_bin'], how='left')
    merged['hours'] = merged['hours'].fillna(0.0)

    # 加权 AEP
    merged['aep_on_kWh']  = merged['power_on_kW']  * merged['hours']
    merged['aep_off_kWh'] = merged['power_off_kW'] * merged['hours']

    summary = (
        merged
        .groupby(['turbine_id', 'station', 'turbine_model', 'station_slot'])
        .agg(
            aep_on_MWh     =('aep_on_kWh',  lambda x: x.sum() / 1000.0),
            aep_off_MWh    =('aep_off_kWh', lambda x: x.sum() / 1000.0),
            max_power_on_kW=('power_on_kW', 'max'),
        )
        .reset_index()
    )
    summary['blockage_diff_MWh']  = summary['aep_on_MWh'] - summary['aep_off_MWh']
    summary['blockage_diff_pct']  = np.where(
        summary['aep_off_MWh'] > 0.01,
        100.0 * summary['blockage_diff_MWh'] / summary['aep_off_MWh'],
        np.nan,
    )
    total_hours = len(forecast) * dt_h  # 8784 h (2024 leap year)
    summary['capacity_factor_on']  = summary['aep_on_MWh']  / (summary['max_power_on_kW'] / 1000.0 * total_hours).clip(0.001)
    summary['capacity_factor_off'] = summary['aep_off_MWh'] / (summary['max_power_on_kW'] / 1000.0 * total_hours).clip(0.001)
    summary['mean_power_on_kW']    = summary['aep_on_MWh'] * 1000.0 / total_hours

    return summary.sort_values(['station', 'station_slot'])


# ══════════════════════════════════════════════════════════════════════════════
#  4. 统计分析
# ══════════════════════════════════════════════════════════════════════════════

def calc_aep_stats(ts: pd.DataFrame) -> dict:
    """计算 AEP（年发电量）及月统计。"""
    # 15 分钟 = 0.25 小时
    dt_h = 0.25

    aep_on  = ts['total_power_on_MW'].sum()  * dt_h  # MWh
    aep_off = ts['total_power_off_MW'].sum() * dt_h  # MWh

    # 月统计
    monthly = ts.groupby('month').agg(
        aep_on_MWh=('total_power_on_MW',  lambda x: x.sum() * dt_h),
        aep_off_MWh=('total_power_off_MW', lambda x: x.sum() * dt_h),
        mean_ws=('wind_speed', 'mean'),
        hours_generating=('total_power_on_MW', lambda x: (x > 0).sum() * dt_h),
    ).reset_index()
    monthly['blockage_loss_MWh']   = monthly['aep_on_MWh'] - monthly['aep_off_MWh']
    monthly['blockage_loss_pct']   = 100.0 * monthly['blockage_loss_MWh'] / monthly['aep_off_MWh'].clip(0.01)
    monthly['month_name'] = [_MONTH_NAMES[m-1] for m in monthly['month']]

    # 风向统计
    wd_stats = ts.groupby('wd_bin').agg(
        count=('valid_time', 'count'),
        aep_on_MWh=('total_power_on_MW',  lambda x: x.sum() * dt_h),
        aep_off_MWh=('total_power_off_MW', lambda x: x.sum() * dt_h),
        mean_ws=('wind_speed', 'mean'),
    ).reset_index()
    wd_stats['blockage_loss_MWh'] = wd_stats['aep_on_MWh'] - wd_stats['aep_off_MWh']
    wd_stats['freq_pct']          = 100.0 * wd_stats['count'] / wd_stats['count'].sum()

    return {
        'aep_on_MWh':  aep_on,
        'aep_off_MWh': aep_off,
        'aep_diff_MWh': aep_on - aep_off,
        'aep_diff_pct': 100.0 * (aep_on - aep_off) / max(aep_off, 0.01),
        'n_gen_hours': float((ts['total_power_on_MW'] > 0).sum() * dt_h),
        'monthly':     monthly,
        'wd_stats':    wd_stats,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  5. 图表生成
# ══════════════════════════════════════════════════════════════════════════════

def _savefig(name: str) -> str:
    path = os.path.join(_FIG_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


def fig_wind_rose(forecast: pd.DataFrame) -> str:
    """风玫瑰图：各风向频率 + 各风速段分布"""
    n_bins = int(360 / WD_BIN_SIZE)
    angles = np.arange(0, 360, WD_BIN_SIZE)
    theta  = np.deg2rad(angles)

    # 计算各风向、各风速段的频率
    ws_breaks = [0, 4, 6, 8, 10, 12, 100]
    ws_labels = ['<4', '4-6', '6-8', '8-10', '10-12', '>12']
    colors     = ['#c7d9ef', '#8bbfe8', '#5093cf', '#2464ab', '#0d3b76', '#071d3a']

    bars_data = {}
    for j, (lo, hi) in enumerate(zip(ws_breaks[:-1], ws_breaks[1:])):
        bars_data[j] = []
        for wd_c in angles:
            mask = (
                (forecast['wd_bin'] == wd_c) &
                (forecast['wind_speed'] >= lo) &
                (forecast['wind_speed'] <  hi)
            )
            bars_data[j].append(mask.sum() / len(forecast) * 100.0)

    fig = plt.figure(figsize=(8, 8))
    ax  = fig.add_subplot(111, projection='polar')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)

    bottom   = np.zeros(n_bins)
    for j in range(len(ws_breaks) - 1):
        vals = np.array(bars_data[j])
        ax.bar(theta, vals, width=np.deg2rad(WD_BIN_SIZE - 1),
               bottom=bottom, color=colors[j], label=f'{ws_labels[j]} m/s',
               edgecolor='white', linewidth=0.5, alpha=0.9)
        bottom += vals

    ax.set_xticks(np.deg2rad(np.arange(0, 360, 45)))
    ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'], fontsize=10)
    ax.legend(loc='lower right', bbox_to_anchor=(1.3, -0.05), fontsize=8)
    ax.set_title(f'风玫瑰图 — 阳江 (21.25°N, 111.5°E) 2024年\n'
                 f'主风向：东北风 (NE 30-60°), 频率 {bottom[1:3].sum():.1f}%', pad=15)
    return _savefig('fig_wind_rose.png')


def fig_monthly_aep(aep_stats: dict) -> str:
    """月度发电量对比：blockage ON vs OFF"""
    monthly = aep_stats['monthly']
    months  = monthly['month_name'].tolist()
    x = np.arange(len(months))
    w = 0.35

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # 上图：月度 AEP
    ax1.bar(x - w/2, monthly['aep_off_MWh']/1000, w, label='无阻塞（Wake only）',
            color='steelblue', alpha=0.85)
    ax1.bar(x + w/2, monthly['aep_on_MWh']/1000,  w, label='尾流+阻塞（Wake + Blockage）',
            color='darkorange', alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(months, fontsize=8)
    ax1.set_ylabel('月发电量 (GWh)')
    ax1.set_title('月度发电量对比（Wake only vs Wake + Blockage）')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # 下图：blockage 损失（阻塞引起的功率变化，负值=损失）
    loss = monthly['blockage_loss_MWh']
    colors = ['crimson' if v < 0 else 'seagreen' for v in loss]
    ax2.bar(x, loss/1000, color=colors, alpha=0.85, edgecolor='none')
    ax2.axhline(0, color='black', lw=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels(months, fontsize=8)
    ax2.set_ylabel('阻塞效应月净影响 (GWh)\n负值 = 功率损失')
    ax2.set_title('阻塞效应对月发电量的净影响（ON - OFF）')
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    return _savefig('fig_monthly_aep.png')


def fig_power_duration(ts: pd.DataFrame) -> str:
    """功率持续曲线：blockage ON vs OFF"""
    pwr_on  = np.sort(ts['total_power_on_MW'].values)[::-1]
    pwr_off = np.sort(ts['total_power_off_MW'].values)[::-1]
    hours   = np.arange(len(pwr_on)) * 0.25  # 小时

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(hours, pwr_off, pwr_on, alpha=0.25, color='darkorange',
                    label='阻塞效应区间（ON - OFF）')
    ax.plot(hours, pwr_off, 'b-',  lw=1.5, label='无阻塞（Wake only）')
    ax.plot(hours, pwr_on,  'r--', lw=1.5, label='尾流+阻塞（Wake + Blockage）', alpha=0.85)
    ax.set_xlabel('累计小时数 (h)')
    ax.set_ylabel('全场总功率 (MW)')
    ax.set_title('全场功率持续曲线（2024年全年）')
    ax.legend()
    ax.grid(True, alpha=0.3)
    return _savefig('fig_power_duration.png')


def fig_blockage_heatmap(bin_results: pd.DataFrame) -> str:
    """阻塞效应热力图：(WD_bin × WS_bin) → 功率变化量"""
    br = bin_results.copy()
    br['power_diff_pct'] = np.where(
        br['total_power_off_MW'] > 0.01,
        100.0 * (br['total_power_on_MW'] - br['total_power_off_MW']) / br['total_power_off_MW'],
        np.nan,
    )

    wd_vals = sorted(br['wd_bin'].unique())
    ws_vals = sorted(br['ws_bin'].unique())

    grid = np.full((len(ws_vals), len(wd_vals)), np.nan)
    wd_idx = {v: i for i, v in enumerate(wd_vals)}
    ws_idx = {v: i for i, v in enumerate(ws_vals)}

    for _, row in br.iterrows():
        i = ws_idx[row['ws_bin']]
        j = wd_idx[row['wd_bin']]
        grid[i, j] = row['power_diff_pct']

    fig, ax = plt.subplots(figsize=(14, 6))
    vmax = np.nanpercentile(np.abs(grid), 95)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    im = ax.imshow(grid, aspect='auto', cmap='RdBu_r', norm=norm,
                   origin='lower', interpolation='nearest')
    plt.colorbar(im, ax=ax, label='阻塞效应 (ON-OFF)/OFF  (%)')

    ax.set_xticks(range(len(wd_vals)))
    ax.set_xticklabels([f'{v:.0f}°' for v in wd_vals], rotation=45, fontsize=7)
    ax.set_yticks(range(len(ws_vals)))
    ax.set_yticklabels([f'{v:.0f}' for v in ws_vals], fontsize=7)
    ax.set_xlabel('风向分格（°）')
    ax.set_ylabel('风速分格（m/s）')
    ax.set_title('阻塞效应对全场功率的影响 (%) —— (ON - OFF) / OFF\n'
                 '蓝色 = 阻塞使功率下降；红色 = 阻塞使功率上升（极少见）')
    plt.tight_layout()
    return _savefig('fig_blockage_heatmap.png')


def fig_timeseries_sample(ts: pd.DataFrame) -> str:
    """样本时间序列：选取 1 月和 7 月各两周的小时均值"""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    for ax, month, title in zip(axes, [1, 7], ['1月（冬季）', '7月（夏季）']):
        sub = ts[ts['month'] == month].copy()
        # 小时均值
        sub['hour'] = sub['valid_time'].dt.floor('h')
        hourly = sub.groupby('hour').agg(
            pwr_on=('total_power_on_MW', 'mean'),
            pwr_off=('total_power_off_MW', 'mean'),
            ws=('wind_speed', 'mean'),
        ).reset_index()
        # 只取前 14 天
        hourly = hourly.head(14 * 24)

        ax.fill_between(hourly['hour'], hourly['pwr_off'], hourly['pwr_on'],
                        alpha=0.3, color='darkorange', label='阻塞效应区间')
        ax.plot(hourly['hour'], hourly['pwr_off'], 'b-',  lw=1.2, label='无阻塞')
        ax.plot(hourly['hour'], hourly['pwr_on'],  'r--', lw=1.2, alpha=0.85, label='尾流+阻塞')

        ax2 = ax.twinx()
        ax2.plot(hourly['hour'], hourly['ws'], 'g:', lw=1, alpha=0.6, label='风速 (右轴)')
        ax2.set_ylabel('风速 (m/s)', color='green', fontsize=8)
        ax2.tick_params(axis='y', labelcolor='green', labelsize=7)

        ax.set_ylabel('全场功率 (MW)')
        ax.set_title(f'{title} 前两周逐小时平均功率')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return _savefig('fig_timeseries_sample.png')


def fig_wd_aep(aep_stats: dict) -> str:
    """各风向分格的年发电量和阻塞损失"""
    wd = aep_stats['wd_stats'].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # 左：各风向 AEP
    x = np.arange(len(wd))
    w = 0.35
    ax1.bar(x - w/2, wd['aep_off_MWh']/1000, w, label='无阻塞', color='steelblue', alpha=0.85)
    ax1.bar(x + w/2, wd['aep_on_MWh']/1000,  w, label='尾流+阻塞', color='darkorange', alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{v:.0f}°" for v in wd['wd_bin']], rotation=45, fontsize=8)
    ax1.set_xlabel('风向分格（°）')
    ax1.set_ylabel('年发电量 (GWh)')
    ax1.set_title('各风向年发电量（Wake only vs Wake + Blockage）')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # 右：各风向阻塞损失
    colors_loss = ['crimson' if v < 0 else 'seagreen' for v in wd['blockage_loss_MWh']]
    ax2.bar(x, wd['blockage_loss_MWh']/1000, color=colors_loss, alpha=0.85)
    ax2.axhline(0, color='black', lw=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{v:.0f}°" for v in wd['wd_bin']], rotation=45, fontsize=8)
    ax2.set_xlabel('风向分格（°）')
    ax2.set_ylabel('阻塞效应年净影响 (GWh)\n负值 = 功率损失')
    ax2.set_title('阻塞效应按风向的年净影响（ON - OFF）')

    # 在柱子上标注频率
    for i, (fq, loss) in enumerate(zip(wd['freq_pct'], wd['blockage_loss_MWh'])):
        ax2.text(i, loss/1000 + 0.05 * np.sign(loss/1000) * max(abs(wd['blockage_loss_MWh']/1000).max(), 0.1),
                 f'{fq:.1f}%', ha='center', va='bottom' if loss >= 0 else 'top', fontsize=7)

    ax2.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    return _savefig('fig_wd_aep.png')


# ══════════════════════════════════════════════════════════════════════════════
#  6. Markdown 报告
# ══════════════════════════════════════════════════════════════════════════════

def _df_to_md(df: pd.DataFrame, max_rows: int = 25) -> str:
    if df is None or len(df) == 0:
        return "_（无数据）_"
    try:
        return df.head(max_rows).to_markdown(index=False, floatfmt='.3f')
    except Exception:
        return df.head(max_rows).to_string(index=False)


def generate_report(
    forecast: pd.DataFrame,
    bin_results: pd.DataFrame,
    ts: pd.DataFrame,
    aep_stats: dict,
    fig_paths: dict,
) -> str:
    """生成 Markdown 分析报告。"""

    def _fig(key, caption):
        if key in fig_paths:
            rel = os.path.relpath(fig_paths[key], _OUT_ROOT)
            return f"![{caption}]({rel})\n\n*{caption}*"
        return "_（图表未生成）_"

    aep_on  = aep_stats['aep_on_MWh']
    aep_off = aep_stats['aep_off_MWh']
    aep_diff= aep_stats['aep_diff_MWh']
    aep_pct = aep_stats['aep_diff_pct']
    n_gen   = aep_stats['n_gen_hours']
    monthly = aep_stats['monthly']
    wd_stats= aep_stats['wd_stats']

    # 主风向统计
    dom_wd = wd_stats.nlargest(3, 'freq_pct')[['wd_bin', 'freq_pct', 'mean_ws', 'aep_off_MWh']]
    dom_wd_str = ", ".join([f"{r['wd_bin']:.0f}°({r['freq_pct']:.1f}%)"
                            for _, r in dom_wd.iterrows()])

    # 最大阻塞效应月
    max_blk_month = monthly.loc[monthly['blockage_loss_MWh'].idxmin(), 'month_name']
    max_blk_val   = monthly['blockage_loss_MWh'].min()

    monthly_show = monthly[['month_name', 'aep_off_MWh', 'aep_on_MWh',
                             'blockage_loss_MWh', 'blockage_loss_pct',
                             'mean_ws', 'hours_generating']].copy()
    monthly_show.columns = ['月份', '无阻塞AEP(MWh)', '含阻塞AEP(MWh)',
                             '阻塞净影响(MWh)', '阻塞净影响(%)', '平均风速(m/s)', '发电小时数']

    wd_show = wd_stats[['wd_bin', 'freq_pct', 'mean_ws',
                         'aep_off_MWh', 'aep_on_MWh',
                         'blockage_loss_MWh']].copy()
    wd_show.columns = ['风向(°)', '频率(%)', '平均风速(m/s)',
                        '无阻塞AEP(MWh)', '含阻塞AEP(MWh)', '阻塞净影响(MWh)']

    report = textwrap.dedent(f"""\
    # ZIYAN 风场尾流 + 阻塞效应预报实验报告

    > 生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
    > 预报数据：场站气象预报/wind_lat_21.250_lon_111.500.csv
    > 预报期间：{forecast['valid_time'].min().strftime('%Y-%m-%d')} 至 {forecast['valid_time'].max().strftime('%Y-%m-%d')}
    > 时间分辨率：15 分钟，共 {len(forecast)} 条记录
    > 风机数量：{forecast['wd_bin'].notna().sum()} 条有效时步，362 台风机

    ---

    ## 1. 实验方案

    ### 1.1 方法

    由于逐时步（35133 次）运行 PyWake 计算量过大，采用**风向-风速分格法**：

    1. 将全年预报按 **风向 30° 间隔** × **风速 1 m/s 间隔** 离散化
    2. 得到 **{len(bin_results)} 个唯一 (WD_bin, WS_bin) 组合**
    3. 对每个组合分别运行：
       - `Wake only`（blockage OFF）：仅考虑尾流效应
       - `Wake + Blockage`（blockage ON）：考虑尾流 + 阻塞效应
    4. 将分格结果映射回 15 分钟时间序列

    ### 1.2 PyWake 模型配置

    | 组件 | 配置 |
    |------|------|
    | 尾流模型 | ZiyanWakeDeficit（3D-DCE + Eq.22 风切变） |
    | 阻塞模型 | SelfSimilarityDeficit2020（LinearSum 叠加） |
    | 叠加方式 | SquaredSum（与原始 RSS 一致） |
    | 转子平均 | EqGridRotorAvg(n=4)（面积加权） |
    | 湍流模型 | STF2005TurbulenceModel（Frandsen IEC2005，逐台 TI 更新） |
    | 风切变 | PowerShear(h_ref=100m, α=0.13) |

    ### 1.3 风速段处理规则

    | 条件 | 处理方式 |
    |------|---------|
    | 风速 < {WS_CUT_IN:.0f} m/s（切入以下） | 功率 = 0，跳过 PyWake |
    | {WS_CUT_IN:.0f} ≤ 风速 < {WS_CUT_OUT:.0f} m/s | 运行 PyWake，功率来自分格结果 |
    | 风速 ≥ {WS_CUT_OUT:.0f} m/s（切出以上） | 功率 = 0，跳过 PyWake |

    ---

    ## 2. 预报风况特征

    {_fig('wind_rose', '风玫瑰图 — 阳江 2024 年全年风向频率与风速分布')}

    ### 2.1 主要特征

    - **全年平均风速**：{forecast['wind_speed'].mean():.2f} m/s（100 m 高度）
    - **主导风向**：{dom_wd_str}（东北偏东象限为主，符合广东阳江区域气候特征）
    - **全年发电小时数**（ON）：{n_gen:.0f} h
    - **风速分布**：{(forecast['wind_speed'] < 3).sum()/len(forecast)*100:.1f}% 低于切入，
      {(forecast['wind_speed'].between(3,12)).sum()/len(forecast)*100:.1f}% 在主发电区间（3-12 m/s），
      {(forecast['wind_speed'] >= 12).sum()/len(forecast)*100:.1f}% 超过 12 m/s

    ---

    ## 3. 年发电量（AEP）对比

    | 模式 | 年发电量 (MWh) | 年发电量 (GWh) |
    |------|---------------|--------------|
    | Wake only（无阻塞） | {aep_off:,.0f} | {aep_off/1000:.2f} |
    | Wake + Blockage（含阻塞） | {aep_on:,.0f} | {aep_on/1000:.2f} |
    | **阻塞净影响（ON - OFF）** | **{aep_diff:,.0f}** | **{aep_diff/1000:.2f}** |
    | **阻塞净影响百分比** | — | **{aep_pct:.3f}%** |

    > **关键结论**：在本年度预报风况下，阻塞效应对全场年发电量的净影响为
    > **{aep_diff/1000:.2f} GWh（{aep_pct:.3f}%）**。
    > 数值较小的主要原因已在之前的诊断分析中解释：
    > `WS_eff_rotor` 的阻塞变化仅来自风机间相互阻挡（inter-turbine blockage），
    > 自感应效应（self-induction）体现在 flow_map 上游探针中，
    > 不进入 PyWake 的功率计算逻辑。

    ---

    ## 4. 月度发电量分析

    {_fig('monthly_aep', '月度发电量对比（Wake only vs Wake + Blockage）')}

    {_df_to_md(monthly_show)}

    ### 4.1 关键观察

    - **阻塞净影响最大月份**：{max_blk_month}（{max_blk_val:.0f} MWh）
    - **冬季（1-3月）**：东北风盛行，平均风速高，阻塞效应相对更显著
    - **夏季（6-8月）**：受台风和季风影响，风向更多变

    ---

    ## 5. 各风向年发电量分析

    {_fig('wd_aep', '各风向年发电量和阻塞效应净影响')}

    {_df_to_md(wd_show)}

    ---

    ## 6. 功率持续曲线

    {_fig('power_duration', '全场功率持续曲线（2024年全年）')}

    ---

    ## 7. 阻塞效应热力图

    {_fig('blockage_heatmap', '阻塞效应对全场功率影响热力图（WD × WS）')}

    ### 7.1 关键观察

    - **阻塞效应随风速增大而增强**（高风速时 Ct 较大，感应区更强）
    - **特定风向下阻塞效应更显著**（主要取决于风场几何排列）
    - 热力图展示了 PyWake 分格结果的完整覆盖范围

    ---

    ## 8. 样本时间序列

    {_fig('timeseries_sample', '样本时间序列（1月和7月各前两周逐小时均值）')}

    ---

    ## 9. 数据文件说明

    | 文件 | 说明 |
    |------|------|
    | `forecast_time_series.csv` | 全年逐 15 分钟**全场**总功率（ON/OFF 对比） |
    | `forecast_bin_results.csv` | 各 (WD, WS) 分格的全场 PyWake 结果（{len(bin_results)} 行） |
    | `forecast_turbine_bin_results.csv` | 各 (WD, WS) 分格的**逐台**功率/WS_eff（每台×每分格一行） |
    | `forecast_station_timeseries.csv` | **电厂级** 15 分钟功率时间序列（XY/XS/YY/SYW 各一对列） |
    | `forecast_turbine_annual.csv` | **逐台风机**年度 AEP 汇总（362 行，含电厂/型号/阻塞净影响） |
    | `figures/fig_wind_rose.png` | 风玫瑰图 |
    | `figures/fig_monthly_aep.png` | 月度发电量对比 |
    | `figures/fig_power_duration.png` | 功率持续曲线 |
    | `figures/fig_blockage_heatmap.png` | 阻塞效应热力图 |
    | `figures/fig_wd_aep.png` | 各风向发电量 |
    | `figures/fig_timeseries_sample.png` | 样本时间序列 |

    ---

    ## 10. 关于 upstream_40m 与 WS_eff_rotor 差异的说明

    如之前诊断分析（analysis_report.md §2.7）所述，
    本实验中阻塞效应对 AEP 的影响非常小（{aep_pct:.3f}%），
    这与"upstream_40m 差值 ≈ 1.4 m/s"的现象看似矛盾，
    但实际上两者是**不同物理量**：

    - **upstream_40m（flow_map 探针）**：包含风机自身感应区（self-induction ≈ 1.4 m/s），
      这是机舱激光雷达在 40 m 处能实际测量到的来流减速，
      但它**不进入** PyWake 的功率计算逻辑（避免与功率曲线中的感应因子重复计算）。

    - **WS_eff_rotor（用于功率计算）**：只包含风机间相互阻挡（inter-turbine blockage ≈ 0.003 m/s），
      因此 AEP 差异很小。

    **结论**：两者数值差异悬殊是正确且预期的 PyWake 行为，不是 bug。
    """)

    # 去除 Python 函数体缩进
    report = '\n'.join(
        line[4:] if line.startswith('    ') else line
        for line in report.split('\n')
    )

    out_path = os.path.join(_OUT_ROOT, 'forecast_report.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════════════════════════

def main():
    t_start = time.time()
    print("=" * 65)
    print("  ZIYAN 气象预报实验 — 尾流 + 阻塞效应")
    print("=" * 65)

    # 1. 读取预报
    print("\n[1] 读取气象预报数据…")
    forecast = load_forecast()
    print(f"    {len(forecast)} 条记录，"
          f"期间 {forecast['valid_time'].iloc[0].date()} ~ "
          f"{forecast['valid_time'].iloc[-1].date()}")
    print(f"    风速：{forecast['wind_speed'].min():.1f} ~ "
          f"{forecast['wind_speed'].max():.1f} m/s，"
          f"均值 {forecast['wind_speed'].mean():.2f} m/s")

    # 2. 加载布局
    print("\n[2] 加载风机布局…")
    layout = load_layout(_PY_DIR)
    print(f"    {len(layout)} 台风机")

    # 3. 运行 PyWake 分格
    print("\n[3] 运行 PyWake 分格计算（Wake only vs Wake + Blockage）…")
    farm_bin_results, turbine_bin_results = run_all_bins(layout, forecast)

    # 保存全场分格结果（旧输出，向后兼容）
    bin_path = os.path.join(_TABLE_DIR, 'forecast_bin_results.csv')
    farm_bin_results.to_csv(bin_path, index=False, float_format='%.4f')
    print(f"    全场分格结果已保存：{bin_path}")

    # 保存逐台风机分格结果
    turbine_bin_path = os.path.join(_TABLE_DIR, 'forecast_turbine_bin_results.csv')
    turbine_bin_results.to_csv(turbine_bin_path, index=False, float_format='%.4f')
    print(f"    逐台分格结果已保存：{turbine_bin_path}  "
          f"({len(turbine_bin_results)} 行 = {turbine_bin_results['turbine_id'].nunique()} 台 × "
          f"{turbine_bin_results[['wd_bin','ws_bin']].drop_duplicates().shape[0]} 分格)")

    # 4. 映射回时间序列
    print("\n[4] 映射分格结果到 15 分钟时间序列…")
    ts = map_to_timeseries(forecast, farm_bin_results)
    ts_path = os.path.join(_TABLE_DIR, 'forecast_time_series.csv')
    ts.to_csv(ts_path, index=False, float_format='%.4f')
    print(f"    全场时间序列已保存：{ts_path}")

    # 站级时间序列
    print("    生成站级时间序列…")
    station_ts = map_to_station_timeseries(forecast, turbine_bin_results)
    station_ts_path = os.path.join(_TABLE_DIR, 'forecast_station_timeseries.csv')
    station_ts.to_csv(station_ts_path, index=False, float_format='%.4f')
    print(f"    站级时间序列已保存：{station_ts_path}  "
          f"({len(station_ts)} 行 × {len(station_ts.columns)} 列)")

    # 逐台年度汇总
    print("    计算逐台风机年度汇总…")
    turbine_annual = build_turbine_annual_summary(turbine_bin_results, forecast)
    annual_path = os.path.join(_TABLE_DIR, 'forecast_turbine_annual.csv')
    turbine_annual.to_csv(annual_path, index=False, float_format='%.4f')
    print(f"    逐台年度汇总已保存：{annual_path}  ({len(turbine_annual)} 台)")

    # 5. 统计
    print("\n[5] 计算 AEP 及月度统计…")
    aep_stats = calc_aep_stats(ts)
    print(f"    AEP (Wake only)   = {aep_stats['aep_off_MWh']/1000:.2f} GWh")
    print(f"    AEP (Wake+Blk ON) = {aep_stats['aep_on_MWh']/1000:.2f} GWh")
    print(f"    阻塞净影响        = {aep_stats['aep_diff_MWh']/1000:.3f} GWh "
          f"({aep_stats['aep_diff_pct']:.3f}%)")

    # 站级 AEP 汇总（快速打印）
    if 'station' in turbine_bin_results.columns:
        print("\n    站级 AEP 汇总（Wake only）：")
        st_aep = turbine_annual.groupby('station').agg(
            aep_on_GWh=('aep_on_MWh',  lambda x: x.sum()/1000),
            aep_off_GWh=('aep_off_MWh', lambda x: x.sum()/1000),
            n_turbines=('turbine_id', 'count'),
        ).reset_index()
        for _, r in st_aep.iterrows():
            diff_gwh = r['aep_on_GWh'] - r['aep_off_GWh']
            print(f"      {r['station']:4s}: OFF={r['aep_off_GWh']:.2f} GWh  "
                  f"ON={r['aep_on_GWh']:.2f} GWh  "
                  f"Δ={diff_gwh:+.3f} GWh  n={int(r['n_turbines'])} 台")

    # 6. 生成图表
    print("\n[6] 生成图表…")
    fig_paths = {}
    tasks = [
        ('wind_rose',     fig_wind_rose,     (forecast,)),
        ('monthly_aep',   fig_monthly_aep,   (aep_stats,)),
        ('power_duration',fig_power_duration,(ts,)),
        ('blockage_heatmap', fig_blockage_heatmap, (farm_bin_results,)),
        ('timeseries_sample', fig_timeseries_sample, (ts,)),
        ('wd_aep',        fig_wd_aep,        (aep_stats,)),
    ]
    for tag, fn, args in tasks:
        try:
            p = fn(*args)
            fig_paths[tag] = p
            print(f"     {tag} -> {os.path.basename(p)}")
        except Exception as exc:
            print(f"     {tag} 失败: {exc}")

    # 7. 生成报告
    print("\n[7] 生成 Markdown 报告…")
    report_path = generate_report(forecast, farm_bin_results, ts, aep_stats, fig_paths)
    print(f"    报告已保存：{report_path}")

    elapsed = time.time() - t_start
    print(f"\n总耗时：{elapsed:.1f}s")
    print(f"所有输出位于：{_OUT_ROOT}")


if __name__ == "__main__":
    main()
