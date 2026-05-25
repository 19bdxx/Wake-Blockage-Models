#!/usr/bin/env python3
from __future__ import annotations

"""
两个场景（blockage_on / blockage_off）逐时刻运行，宽表直出。

场景定义
--------
blockage_on : enable_blockage=True
blockage_off: enable_blockage=False

每个时刻只做 2 次 PyWake 流场求解（一次 blockage=True，一次 blockage=False），
再从同一次流场结果派生出所有功率口径和风速口径，展开为列，输出宽表 CSV。
不再为不同 power_source_mode 做额外的 PyWake 求解。

风速列名（A/B/C 三类，含义固定）
-------------------------------------------
A 类：WS_eff_pywake_native_m_s              <- sim_res.WS_eff，始终直接来自 PyWake 内部
B 类：WS_probe_upstream_{d}m_m_s            <- flow_map(Points(...)) 前方 dm 探针（d 由 config 动态决定）
C 类：WS_rotor_disc_upstream1m_mean_m_s     <- 转子前缘上游 1m 处圆盘采样点风速的均值

注：上游探针（B 类）用于来流代理和功率重算；下游探针仅输出风速，不参与功率重算。

功率列名
--------
power_pywake_internal_kW
    直接来自 sim_res.Power / 1000。
    ─ 风速输入：PyWake 内部 WS_eff（与 A 类相同）
    ─ 功率曲线求值器：PyWake 内置 PowerCtTabular（线性插值 + 内部边界处理）

power_from_ws_eff_pywake_native_kW
    先取 sim_res.WS_eff（A 类），再通过项目 turbine_model.py 重新查功率曲线。
    ─ 风速输入：与 power_pywake_internal_kW 完全相同（均为 sim_res.WS_eff）
    ─ 功率曲线求值器：项目 turbine_model.py（numpy 一维线性插值，clip 边界处理）
    ─ 与 pywake_internal 的差异：风速输入相同，差异主要来自功率曲线求值器实现不同
      （PyWake 内置 PowerCtTabular 与项目 turbine_model.py 的插值方式、边界处理均不同）

power_from_upstream_{d}m_kW           <- B 类上游 dm 探针重算功率曲线（所有配置距离均输出）
power_from_rotor_disc_upstream1m_mean_kW <- C 类风速重算功率曲线

注：宽表中每行同时含有所有功率口径列，无需再通过 power_source_mode 筛选行。
因此宽表中不再保留 power_source_mode（无意义）和 power_kW（是某个具体口径列的副本）。

输出
----
默认输出到: five_experiments_output/
  blockage_on/
    turbine_power_timeseries.csv  — 每行 = 一台风机 × 一个时刻（所有功率/风速列）
    station_power_timeseries.csv  — 每行 = 一个电站 × 一个时刻（所有功率列 + 风速均值列）
    farm_power_timeseries.csv     — 每行 = 一个时刻（所有功率列 + 风速均值列）
  blockage_off/
    turbine_power_timeseries.csv
    station_power_timeseries.csv
    farm_power_timeseries.csv
  all_experiments_farm_power_timeseries.csv
      （宽表，每个时刻 2 行：enable_blockage=True / False；所有功率口径展开为列）
  all_experiments_station_power_timeseries.csv
      （宽表，每个时刻每电站 2 行：enable_blockage=True / False；所有功率口径展开为列）
"""

import argparse
import os
import sys
import time
from dataclasses import replace
from typing import List

import numpy as np
import pandas as pd

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
PYWAKE_DIR = os.path.join(REPO_DIR, 'pywake_integration')
if PYWAKE_DIR not in sys.path:
    sys.path.insert(0, PYWAKE_DIR)

from pywake_integration.config import IntegrationConfig, resolve_core_python_dir, resolve_forecast_csv_path
from pywake_integration.wind_farm_setup import build_wind_farm_model, turbine_id_to_type
from pywake_integration.run_integration import load_layout, run_one_condition


# 两个场景：blockage_on（enable_blockage=True）/ blockage_off（enable_blockage=False）
_SCENARIOS = [
    {'enable_blockage': True,  'label': 'blockage_on'},
    {'enable_blockage': False, 'label': 'blockage_off'},
]

# 宽表中不保留这些列：在所有功率口径已展开为独立列后，它们无实际意义
_DROP_FROM_WIDE = ('power_kW', 'power_source_mode', 'WS_selected_for_power_curve_m_s')


def load_forecast_exact(forecast_csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(forecast_csv_path, parse_dates=['valid_time'])
    df = df.sort_values('valid_time').reset_index(drop=True)
    required = {'valid_time', 'wind_speed', 'wind_direction'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"预报文件缺少必要列：{sorted(missing)}")
    return df


def _as_naive_timestamp(ts) -> pd.Timestamp:
    """将时间统一为无时区 Timestamp，方便维护矩阵严格匹配。"""
    out = pd.Timestamp(ts)
    if out.tzinfo is not None:
        out = out.tz_convert(None)
    return out


def get_maintenance_lookup_time(
    model_ts: pd.Timestamp,
    maintenance_time_offset_hours: float = 0.0,
) -> pd.Timestamp:
    """
    将模型/气象预报时间转换为维护矩阵查询时间。

    当前推荐约定：
        气象预报 valid_time 已经转换为 UTC8；
        场站维护矩阵时间也是 UTC8；
        因此默认 maintenance_time_offset_hours = 0。

    如果以后重新使用 UTC0 的 ERA5 文件，可在运行时传：
        --maintenance-time-offset-hours 8
    """
    return _as_naive_timestamp(model_ts) + pd.Timedelta(hours=float(maintenance_time_offset_hours))


def load_maintenance_matrix(
    maintenance_csv_path: str,
    turbine_ids: np.ndarray,
) -> pd.DataFrame | None:
    """
    读取风机维护矩阵。

    支持列名：
        时间, 是否维护_#1, 是否维护_#2, ...
    或：
        timestamp, is_maintenance_#1, is_maintenance_#2, ...

    返回：
        index   = 场站本地时间（UTC8，无时区）
        columns = int 风机编号，例如 1, 2, ..., 58
        values  = 0/1，1 表示维护，0 表示非维护
    """
    if not maintenance_csv_path:
        print("未提供 --maintenance-matrix，默认所有时刻所有风机均参与计算。")
        return None

    if not os.path.exists(maintenance_csv_path):
        raise FileNotFoundError(f"找不到维护矩阵文件：{maintenance_csv_path}")

    maint = pd.read_csv(maintenance_csv_path, encoding='utf-8-sig')

    if '时间' in maint.columns:
        time_col = '时间'
    elif 'timestamp' in maint.columns:
        time_col = 'timestamp'
    elif 'valid_time' in maint.columns:
        time_col = 'valid_time'
    else:
        raise ValueError("维护矩阵中找不到时间列。要求列名为 '时间'、'timestamp' 或 'valid_time'。")

    maint[time_col] = pd.to_datetime(maint[time_col], errors='coerce')
    maint = maint.dropna(subset=[time_col]).copy()
    # 统一为无时区时间；维护矩阵本身按场站本地时间 UTC8 理解。
    maint[time_col] = maint[time_col].map(_as_naive_timestamp)

    rename_cols = {}
    for col in maint.columns:
        if col == time_col:
            continue
        col_str = str(col).strip()
        if col_str.startswith('是否维护_#'):
            tid = int(col_str.replace('是否维护_#', ''))
            rename_cols[col] = tid
        elif col_str.startswith('is_maintenance_#'):
            tid = int(col_str.replace('is_maintenance_#', ''))
            rename_cols[col] = tid
        elif col_str.startswith('maintenance_#'):
            tid = int(col_str.replace('maintenance_#', ''))
            rename_cols[col] = tid

    maint = maint.rename(columns=rename_cols)

    required_tids = [int(tid) for tid in turbine_ids]
    missing = [tid for tid in required_tids if tid not in maint.columns]
    if missing:
        raise ValueError(
            f"维护矩阵缺少以下风机列：{missing[:20]}"
            + (" ..." if len(missing) > 20 else "")
            + "\n期望列名示例：是否维护_#1, 是否维护_#2, ..."
        )

    maint = maint[[time_col] + required_tids].copy()
    for tid in required_tids:
        maint[tid] = pd.to_numeric(maint[tid], errors='coerce').fillna(0).astype(int).clip(0, 1)

    maint = maint.sort_values(time_col).reset_index(drop=True)
    if maint[time_col].duplicated().any():
        duplicated_times = maint.loc[maint[time_col].duplicated(), time_col].head(10)
        raise ValueError(f"维护矩阵中存在重复时间，例如：{duplicated_times.tolist()}")

    maint = maint.set_index(time_col)

    print(f"已加载维护矩阵：{maintenance_csv_path}")
    print(f"维护矩阵时间范围（场站UTC8）：{maint.index.min()} 至 {maint.index.max()}")
    print(f"维护矩阵行数：{len(maint)}")
    return maint


def get_maintenance_flags_for_time(
    maintenance_df: pd.DataFrame | None,
    model_ts: pd.Timestamp,
    turbine_ids: np.ndarray,
    maintenance_time_offset_hours: float = 0.0,
    missing_maintenance_policy: str = 'skip',
    nearest_tolerance_min: float = 7.5,
) -> tuple[np.ndarray | None, pd.Timestamp | None, str]:
    """
    获取某个模型时刻每台风机是否维护。支持维护矩阵缺失时不中断运行。

    返回：
        maintenance_flags:
            bool 数组，长度等于 turbine_ids；True=维护，False=运行。
            当 missing_maintenance_policy='skip' 且查不到维护时，返回 None。
        maintenance_lookup_time:
            实际用于查询维护矩阵的时间。
        maintenance_match_status:
            exact       : 精确匹配到维护矩阵时刻
            no_matrix   : 未提供维护矩阵，默认全运行
            all_running : 维护矩阵缺失该时刻，按全运行处理
            nearest     : 维护矩阵缺失该时刻，使用最近时刻
            skipped     : 维护矩阵缺失该时刻，跳过该模型时刻
    """
    if maintenance_df is None:
        return np.zeros(len(turbine_ids), dtype=bool), pd.NaT, 'no_matrix'

    policy = str(missing_maintenance_policy).strip().lower()
    allowed = {'error', 'all_running', 'nearest', 'skip'}
    if policy not in allowed:
        raise ValueError(
            f"missing_maintenance_policy={missing_maintenance_policy!r} 不合法，"
            f"可选值为：{sorted(allowed)}"
        )

    target_ts = get_maintenance_lookup_time(model_ts, maintenance_time_offset_hours)

    if target_ts in maintenance_df.index:
        row = maintenance_df.loc[target_ts]
        flags = np.array([int(row[int(tid)]) == 1 for tid in turbine_ids], dtype=bool)
        return flags, target_ts, 'exact'

    if policy == 'error':
        raise ValueError(
            "维护矩阵中找不到对应时刻。\n"
            f"模型/气象预报时刻（UTC8）：{_as_naive_timestamp(model_ts)}\n"
            f"维护矩阵查询时刻（UTC8）：{target_ts}\n"
            f"时间偏移小时数：{maintenance_time_offset_hours}\n"
            "当前采用严格对齐：模型时刻加偏移后必须在维护矩阵中存在。\n"
            "如果希望不中断运行，可使用：\n"
            "  --missing-maintenance-policy all_running\n"
            "或：\n"
            "  --missing-maintenance-policy nearest --maintenance-nearest-tolerance-min 7.5"
        )

    if policy == 'skip':
        return None, target_ts, 'skipped'

    if policy == 'all_running':
        return np.zeros(len(turbine_ids), dtype=bool), target_ts, 'all_running'

    # policy == 'nearest'
    if len(maintenance_df.index) == 0:
        return np.zeros(len(turbine_ids), dtype=bool), target_ts, 'all_running'

    idxer = maintenance_df.index.get_indexer([target_ts], method='nearest')
    nearest_pos = int(idxer[0])
    nearest_ts = maintenance_df.index[nearest_pos]
    gap_min = abs((nearest_ts - target_ts).total_seconds()) / 60.0

    if gap_min > float(nearest_tolerance_min):
        raise ValueError(
            "维护矩阵中找不到对应时刻，且最近时刻超出容许范围。\n"
            f"模型/气象预报时刻（UTC8）：{_as_naive_timestamp(model_ts)}\n"
            f"维护矩阵目标查询时刻（UTC8）：{target_ts}\n"
            f"最近维护矩阵时刻：{nearest_ts}\n"
            f"时间差：{gap_min:.2f} 分钟，容许阈值：{nearest_tolerance_min:.2f} 分钟\n"
            "可以改用 --missing-maintenance-policy skip 直接跳过，或检查维护矩阵缺口。"
        )

    row = maintenance_df.loc[nearest_ts]
    flags = np.array([int(row[int(tid)]) == 1 for tid in turbine_ids], dtype=bool)
    return flags, nearest_ts, 'nearest'


def run_one_condition_with_maintenance(
    *,
    wfm,
    turbine_ids,
    x_wt,
    y_wt,
    z_wt,
    d_wt,
    types_arr,
    maintenance_flags: np.ndarray,
    wind_dir: float,
    u_100: float,
    config: IntegrationConfig,
    py_dir: str,
    timestamp_label: str | None = None,
) -> pd.DataFrame:
    """
    根据 maintenance_flags 处理维护风机。

    maintenance_flags:
        True  = 维护，不参与 PyWake，不作为尾流源，功率置 0
        False = 运行，参与 PyWake

    注意：真正关键的是维护风机不传入 PyWake，而不只是事后把功率置 0。
    """
    turbine_ids = np.asarray(turbine_ids)
    maintenance_flags = np.asarray(maintenance_flags, dtype=bool)
    active_mask = ~maintenance_flags

    n_active = int(active_mask.sum())

    if n_active <= 0:
        # 极端/异常情况：维护矩阵显示该时刻全场所有风机均处于维护状态。
        # PyWake 不能运行空风场，但主程序不应该因此中断。
        # 这里用第 1 台风机做一次“模板计算”来获得标准输出列名，然后丢弃模板数值，
        # 最终仍然输出 58 台维护风机：功率列=0，风速列=NaN，is_maintenance=1。
        print(
            f"警告：时刻 {timestamp_label} 维护矩阵显示全场所有风机均维护；"
            f"将输出全场功率为0的维护状态行，不运行真实空风场。"
        )
        template_df = run_one_condition(
            wfm=wfm,
            turbine_ids=turbine_ids[:1],
            x_wt=np.asarray(x_wt)[:1],
            y_wt=np.asarray(y_wt)[:1],
            z_wt=np.asarray(z_wt)[:1],
            d_wt=np.asarray(d_wt)[:1],
            types_arr=np.asarray(types_arr)[:1],
            wind_dir=wind_dir,
            u_100=u_100,
            config=config,
            py_dir=py_dir,
            timestamp_label=timestamp_label,
        )
        active_df = template_df.iloc[0:0].copy()
    else:
        active_df = run_one_condition(
            wfm=wfm,
            turbine_ids=turbine_ids[active_mask],
            x_wt=np.asarray(x_wt)[active_mask],
            y_wt=np.asarray(y_wt)[active_mask],
            z_wt=np.asarray(z_wt)[active_mask],
            d_wt=np.asarray(d_wt)[active_mask],
            types_arr=np.asarray(types_arr)[active_mask],
            wind_dir=wind_dir,
            u_100=u_100,
            config=config,
            py_dir=py_dir,
            timestamp_label=timestamp_label,
        )
        active_df['is_maintenance'] = 0
        active_df['is_running'] = 1

    inactive_tids = turbine_ids[maintenance_flags]
    inactive_rows = []
    for tid in inactive_tids:
        row = {c: np.nan for c in active_df.columns}
        row['timestamp'] = timestamp_label
        row['turbine_id'] = int(tid)
        row['wind_dir'] = float(wind_dir)
        row['u_ref_100m'] = float(u_100)
        row['is_maintenance'] = 1
        row['is_running'] = 0
        row['enable_blockage'] = bool(config.enable_blockage)
        row['blockage_model'] = config.blockage_model_name if config.enable_blockage else 'None'
        row['enable_turbulence_model'] = bool(config.enable_turbulence_model)

        for c in active_df.columns:
            if c.startswith('power_') and c.endswith('_kW'):
                row[c] = 0.0

        inactive_rows.append(row)

    if inactive_rows:
        out_df = pd.concat([active_df, pd.DataFrame(inactive_rows)], ignore_index=True)
    else:
        out_df = active_df.copy()

    order_map = {int(tid): i for i, tid in enumerate(turbine_ids)}
    out_df['_order'] = out_df['turbine_id'].map(order_map)
    out_df = out_df.sort_values('_order').drop(columns=['_order']).reset_index(drop=True)
    return out_df


def _build_station_rows(df_turbine: pd.DataFrame, ts, ws: float, wd: float, blk: bool) -> list:
    """从风机级宽表按电站聚合：功率列求和，WS 列求均值。"""
    station_col = 'station'
    if station_col not in df_turbine.columns:
        return []
    power_cols = [c for c in df_turbine.columns if c.endswith('_kW') and c.startswith('power_')]
    ws_cols = [c for c in df_turbine.columns if c.startswith('WS_') and c.endswith('_m_s')]
    agg = {c: 'sum' for c in power_cols}
    agg.update({c: 'mean' for c in ws_cols})
    grp = df_turbine.groupby(station_col).agg(agg).reset_index()
    rows = []
    for _, r in grp.iterrows():
        entry: dict = {
            'valid_time': ts,
            'wind_speed': ws,
            'wind_direction': wd,
            'enable_blockage': blk,
            'station': r[station_col],
        }
        if 'is_maintenance' in df_turbine.columns:
            sub = df_turbine[df_turbine[station_col] == r[station_col]]
            entry['station_total_turbines'] = int(len(sub))
            entry['station_maintenance_turbines'] = int(sub['is_maintenance'].sum())
            entry['station_running_turbines'] = int(sub['is_running'].sum())
        for c in power_cols:
            entry[f'station_{c}'] = float(r[c])
        for c in ws_cols:
            entry[f'mean_{c}'] = float(r[c])
        rows.append(entry)
    return rows


def _build_farm_row(df_turbine: pd.DataFrame, ts, ws: float, wd: float, blk: bool) -> dict:
    """从风机级宽表聚合全场：功率列求和，WS 列求均值。"""
    power_cols = [c for c in df_turbine.columns if c.endswith('_kW') and c.startswith('power_')]
    ws_cols = [c for c in df_turbine.columns if c.startswith('WS_') and c.endswith('_m_s')]
    row: dict = {
        'valid_time': ts,
        'wind_speed': ws,
        'wind_direction': wd,
        'enable_blockage': blk,
    }
    if 'is_maintenance' in df_turbine.columns:
        row['farm_total_turbines'] = int(len(df_turbine))
        row['farm_maintenance_turbines'] = int(df_turbine['is_maintenance'].sum())
        row['farm_running_turbines'] = int(df_turbine['is_running'].sum())
    for c in power_cols:
        row[f'farm_{c}'] = float(df_turbine[c].sum())
    for c in ws_cols:
        row[f'mean_{c}'] = float(df_turbine[c].mean())
    return row


def main():
    parser = argparse.ArgumentParser(
        description='两个场景（blockage_on / blockage_off）逐时刻运行，宽表直出'
    )
    parser.add_argument('--core-dir', type=str, default='', help='原始项目 Python 核心目录（留空自动查找）')
    parser.add_argument('--forecast-csv', type=str, default='', help='气象预报 CSV 路径（留空自动查找）')
    parser.add_argument(
        '--maintenance-matrix',
        type=str,
        default='',
        help='风机维护矩阵 CSV 路径。列名支持：时间, 是否维护_#1, 是否维护_#2 ...；不传则默认所有风机均运行。'
    )
    parser.add_argument(
        '--maintenance-time-offset-hours',
        type=float,
        default=0.0,
        help='维护矩阵时间相对气象预报时间的偏移小时数。若气象预报和维护矩阵均为UTC8，则填0。'
    )
    parser.add_argument(
        '--missing-maintenance-policy',
        type=str,
        default='skip',
        choices=['error', 'all_running', 'nearest', 'skip'],
        help=(
            '维护矩阵缺少某个模型时刻时的处理方式：'
            'error=报错中断；all_running=该时刻按全风机运行；'
            'nearest=使用最近维护矩阵时刻；skip=跳过该模型时刻。'
            '默认 skip：维护矩阵缺失该时刻时，直接跳过该气象预报时刻，不输出结果。'
        ),
    )
    parser.add_argument(
        '--maintenance-nearest-tolerance-min',
        type=float,
        default=7.5,
        help='当 --missing-maintenance-policy nearest 时，允许最近维护时刻的最大时间差，单位分钟。'
    )
    parser.add_argument('--output-dir', type=str,
                        default=os.path.join(REPO_DIR, 'five_experiments_output'),
                        help='输出目录（每个场景按 label 建子目录）')
    parser.add_argument('--limit', type=int, default=0, help='仅运行前 N 个时刻，0 表示全量')
    parser.add_argument('--start-index', type=int, default=0, help='起始行号（含）')
    parser.add_argument('--end-index', type=int, default=-1, help='结束行号（不含），-1 表示直到末尾')
    parser.add_argument('--no-turbulence', action='store_true', help='禁用 PyWake 湍流模型')
    parser.add_argument('--no-rotor-avg', action='store_true', help='禁用 PyWake 转子平均')
    parser.add_argument('--self-blockage-grid-n', type=int, default=9,
                        help='WS_rotor_disc_upstream1m_mean 计算时的转子圆盘采样边长')
    parser.add_argument('--self-blockage-offset-m', type=float, default=1.0,
                        help='WS_rotor_disc_upstream1m_mean 计算时沿来流方向上游平移的距离（m）')
    parser.add_argument(
        '--power-probe-distance',
        type=float,
        default=None,
        help=(
            'probe_upstream 模式的上游探针距离（m）。'
            ' 默认使用 config.py 中的 power_probe_distance_m（当前值：120m）。'
        ),
    )
    args = parser.parse_args()

    base_cfg = IntegrationConfig(
        core_python_dir=args.core_dir,
        forecast_csv_path=args.forecast_csv,
        enable_turbulence_model=not args.no_turbulence,
        rotor_avg_n=0 if args.no_rotor_avg else 4,
        self_blockage_rotor_grid_n=max(int(args.self_blockage_grid_n), 3),
        self_blockage_upstream_offset_m=max(float(args.self_blockage_offset_m), 0.0),
        power_probe_distance_m=float(args.power_probe_distance) if args.power_probe_distance is not None else IntegrationConfig().power_probe_distance_m,
        # upstream_distances / downstream_distances 使用 config.py 默认值
    )

    py_dir = resolve_core_python_dir(base_cfg.core_python_dir)
    forecast_csv = resolve_forecast_csv_path(base_cfg.forecast_csv_path)
    forecast = load_forecast_exact(forecast_csv)
    start = max(int(args.start_index), 0)
    end = len(forecast) if args.end_index < 0 else min(int(args.end_index), len(forecast))
    forecast = forecast.iloc[start:end].reset_index(drop=True)
    if args.limit and args.limit > 0:
        forecast = forecast.iloc[:args.limit].copy()

    print('加载风机布局...')
    layout = load_layout(py_dir)
    turbine_ids = layout['turbine_id'].values.astype(int)
    x_wt = layout['x'].values.astype(float)
    y_wt = layout['y'].values.astype(float)

    station_map: dict = {}
    if 'station' in layout.columns:
        station_map = dict(zip(layout['turbine_id'].astype(int), layout['station']))

    import importlib
    if py_dir not in sys.path:
        sys.path.insert(0, py_dir)
    tm = importlib.import_module('turbine_model')
    d_wt = np.array([tm.calculate_D(int(tid))[0] for tid in turbine_ids], dtype=float)
    z_wt = np.array([tm.calculate_D(int(tid))[1] for tid in turbine_ids], dtype=float)
    types_arr = np.array([turbine_id_to_type(int(tid), py_dir) for tid in turbine_ids], dtype=int)

    maintenance_df = load_maintenance_matrix(args.maintenance_matrix, turbine_ids)
    if maintenance_df is not None:
        print(
            f"维护矩阵查询规则：气象预报 valid_time + {args.maintenance_time_offset_hours} 小时 "
            "= 维护矩阵时间（当前推荐二者均为UTC8，因此偏移为0）"
        )

    # 构建两种 wfm（blockage=True / False），避免重复构建
    print('构建 PyWake 模型：blockage=True ...')
    cfg_blk = replace(base_cfg, enable_blockage=True, power_ws_mode='pywake_native')
    wfm_blk = build_wind_farm_model(cfg_blk)
    print('构建 PyWake 模型：blockage=False ...')
    cfg_noblk = replace(base_cfg, enable_blockage=False, power_ws_mode='pywake_native')
    wfm_noblk = build_wind_farm_model(cfg_noblk)

    wfm_map = {True: wfm_blk, False: wfm_noblk}

    print(f'\n将运行 {len(forecast)} 个时刻，共 {len(_SCENARIOS)} 个场景：')
    for sc in _SCENARIOS:
        print(f"  [{sc['label']}]  enable_blockage={sc['enable_blockage']}")
    print('每个时刻只做 2 次 PyWake 流场求解，所有功率口径从同一次结果派生为宽表列。')

    # 按场景收集行
    scen_turbine_rows: dict = {sc['label']: [] for sc in _SCENARIOS}
    scen_station_rows: dict = {sc['label']: [] for sc in _SCENARIOS}
    scen_farm_rows: dict    = {sc['label']: [] for sc in _SCENARIOS}

    t0 = time.time()
    extra_cols = [c for c in ['u100', 'v100', 'is_interpolated'] if c in forecast.columns]

    # 维护矩阵缺失时刻统计
    maintenance_match_counter = {
        'exact': 0,
        'no_matrix': 0,
        'all_running': 0,
        'nearest': 0,
        'skipped': 0,
    }
    missing_maintenance_records: list[dict] = []

    for idx, row_fc in forecast.iterrows():
        ts = pd.Timestamp(row_fc['valid_time'])
        ws = float(row_fc['wind_speed'])
        wd = float(row_fc['wind_direction'])

        maintenance_flags, maintenance_lookup_time, maintenance_match_status = get_maintenance_flags_for_time(
            maintenance_df=maintenance_df,
            model_ts=ts,
            turbine_ids=turbine_ids,
            maintenance_time_offset_hours=args.maintenance_time_offset_hours,
            missing_maintenance_policy=args.missing_maintenance_policy,
            nearest_tolerance_min=args.maintenance_nearest_tolerance_min,
        )
        maintenance_match_counter[maintenance_match_status] = (
            maintenance_match_counter.get(maintenance_match_status, 0) + 1
        )

        if maintenance_match_status in {'all_running', 'nearest', 'skipped'}:
            missing_maintenance_records.append({
                'valid_time': ts,
                'maintenance_lookup_time': maintenance_lookup_time,
                'maintenance_match_status': maintenance_match_status,
            })
            if len(missing_maintenance_records) <= 20 or len(missing_maintenance_records) % 100 == 0:
                print(
                    f"警告：维护矩阵未精确匹配时刻，valid_time={ts}, "
                    f"处理方式={maintenance_match_status}, 使用/目标维护时刻={maintenance_lookup_time}"
                )

        if maintenance_flags is None:
            # --missing-maintenance-policy skip：该模型时刻不输出任何结果
            continue

        n_maint = int(maintenance_flags.sum())

        # ── 每个时刻仅做 2 次 PyWake 流场求解 ────────────────────────────────────────
        base_dfs: dict = {}  # {enable_blockage: DataFrame}
        for _blk in (True, False):
            _cfg = replace(base_cfg, enable_blockage=_blk, power_ws_mode='pywake_native')
            base_dfs[_blk] = run_one_condition_with_maintenance(
                wfm=wfm_map[_blk],
                turbine_ids=turbine_ids,
                x_wt=x_wt, y_wt=y_wt, z_wt=z_wt, d_wt=d_wt,
                types_arr=types_arr,
                maintenance_flags=maintenance_flags,
                wind_dir=wd,
                u_100=ws,
                config=_cfg,
                py_dir=py_dir,
                timestamp_label=ts.isoformat(),
            )

        for sc in _SCENARIOS:
            blk = sc['enable_blockage']
            label = sc['label']

            # 宽表：去掉 power_source_mode / power_kW / WS_selected_for_power_curve_m_s
            # 这些列在宽表中无意义（所有功率口径已展开为独立列）
            df_base = base_dfs[blk].copy()
            drop_cols = [c for c in _DROP_FROM_WIDE if c in df_base.columns]
            df_base = df_base.drop(columns=drop_cols)

            # 加入 station 列（若有）
            if station_map:
                df_base['station'] = df_base['turbine_id'].map(station_map)

            # 添加元数据列
            df_base.insert(0, 'valid_time', ts)
            df_base['maintenance_lookup_time'] = maintenance_lookup_time
            df_base['maintenance_match_status'] = maintenance_match_status
            df_base['wind_speed'] = ws
            df_base['wind_direction'] = wd
            df_base['enable_blockage'] = blk
            for c in extra_cols:
                df_base[c] = row_fc[c]

            # 收集风机级
            scen_turbine_rows[label].append(df_base)

            # 收集电站级
            station_rows = _build_station_rows(df_base, ts, ws, wd, blk)
            for sr in station_rows:
                sr['maintenance_lookup_time'] = maintenance_lookup_time
                sr['maintenance_match_status'] = maintenance_match_status
            for c in extra_cols:
                for sr in station_rows:
                    sr[c] = row_fc[c]
            scen_station_rows[label].extend(station_rows)

            # 收集全场级
            farm_row = _build_farm_row(df_base, ts, ws, wd, blk)
            farm_row['maintenance_lookup_time'] = maintenance_lookup_time
            farm_row['maintenance_match_status'] = maintenance_match_status
            for c in extra_cols:
                farm_row[c] = row_fc[c]
            scen_farm_rows[label].append(farm_row)

        if (int(idx) + 1) % 10 == 0 or int(idx) == len(forecast) - 1:
            elapsed = time.time() - t0
            sample = scen_farm_rows[_SCENARIOS[0]['label']][-1]
            blk_key = next(
                (k for k in sample if k.startswith('farm_power_pywake_internal')), None
            )
            sample_val = f"{sample[blk_key] / 1e3:.2f} MW" if blk_key else 'N/A'
            print(
                f"  已完成 {int(idx) + 1}/{len(forecast)} 个时刻，最近时刻={ts}, "
                f"维护查询时刻={maintenance_lookup_time}, 维护台数={n_maint}, "
                f"farm_power_pywake_internal(blockage_on)={sample_val}, "
                f"累计耗时={elapsed:.1f}s"
            )

    # ── 输出结果文件 ──────────────────────────────────────────────────────────────
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    all_farm_rows: List[dict] = []
    all_station_rows: List[dict] = []

    for sc in _SCENARIOS:
        label = sc['label']
        sc_dir = os.path.join(output_dir, label)
        os.makedirs(sc_dir, exist_ok=True)

        # 风机级
        turbine_chunks = scen_turbine_rows.get(label, [])
        if turbine_chunks:
            turbine_df = pd.concat(turbine_chunks, ignore_index=True)
            turbine_path = os.path.join(sc_dir, 'turbine_power_timeseries.csv')
            turbine_df.to_csv(turbine_path, index=False, float_format='%.4f')
            print(f'  [{label}] 风机级时序已保存：{turbine_path}')

        # 电站级
        station_chunks = scen_station_rows.get(label, [])
        if station_chunks:
            station_df = pd.DataFrame(station_chunks)
            station_path = os.path.join(sc_dir, 'station_power_timeseries.csv')
            station_df.to_csv(station_path, index=False, float_format='%.4f')
            print(f'  [{label}] 电站级时序已保存：{station_path}')
            all_station_rows.extend(station_chunks)

        # 全场级
        farm_chunks = scen_farm_rows.get(label, [])
        if not farm_chunks:
            continue
        farm_df = pd.DataFrame(farm_chunks)
        farm_path = os.path.join(sc_dir, 'farm_power_timeseries.csv')
        farm_df.to_csv(farm_path, index=False, float_format='%.4f')
        print(f'  [{label}] 全场时序已保存：{farm_path}')
        all_farm_rows.extend(farm_chunks)

    # 合并全场宽表（每时刻 2 行：blockage_on / blockage_off）
    if all_farm_rows:
        combined_farm_df = pd.DataFrame(all_farm_rows)
        combined_farm_path = os.path.join(output_dir, 'all_experiments_farm_power_timeseries.csv')
        combined_farm_df.to_csv(combined_farm_path, index=False, float_format='%.4f')
        print(f'\n合并全场对比结果（宽表）已保存：{combined_farm_path}')
        print(f'总行数：{len(combined_farm_df)}（{len(forecast)} 个时刻 x 2 blockage 状态，功率口径已展开为列）')

    # 合并电站宽表（每时刻每电站 2 行：blockage_on / blockage_off）
    if all_station_rows:
        combined_station_df = pd.DataFrame(all_station_rows)
        combined_station_path = os.path.join(output_dir, 'all_experiments_station_power_timeseries.csv')
        combined_station_df.to_csv(combined_station_path, index=False, float_format='%.4f')
        print(f'合并电站对比结果（宽表）已保存：{combined_station_path}')
        n_stations = combined_station_df['station'].nunique() if 'station' in combined_station_df.columns else 'N/A'
        print(f'总行数：{len(combined_station_df)}（{len(forecast)} 个时刻 x {n_stations} 个电站 x 2 blockage 状态）')

    # 输出维护矩阵匹配情况，便于检查是否存在维护状态缺口
    if maintenance_df is not None:
        match_summary_path = os.path.join(output_dir, 'maintenance_match_summary.csv')
        match_summary_df = pd.DataFrame([
            {'maintenance_match_status': k, 'count': v}
            for k, v in maintenance_match_counter.items()
        ])
        match_summary_df.to_csv(match_summary_path, index=False, encoding='utf-8-sig')
        print(f'维护矩阵匹配统计已保存：{match_summary_path}')

        if missing_maintenance_records:
            missing_path = os.path.join(output_dir, 'missing_maintenance_timestamps.csv')
            pd.DataFrame(missing_maintenance_records).to_csv(
                missing_path, index=False, encoding='utf-8-sig'
            )
            print(f'维护矩阵未精确匹配时刻明细已保存：{missing_path}')


if __name__ == '__main__':
    main()
