#!/usr/bin/env python3
# pywake_integration/exact_forecast_run.py
"""
exact_forecast_run.py — 按气象预报逐时刻运行 PyWake，输出逐时刻全场预测功率。
当前版本支持动态汇总所有 probe 列和所有 rotor_disc 多距离列。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import List

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from config import IntegrationConfig, resolve_core_python_dir, resolve_forecast_csv_path
from wind_farm_setup import build_wind_farm_model, turbine_id_to_type
from run_integration import load_layout, run_one_condition


def load_forecast_exact(forecast_csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(forecast_csv_path, parse_dates=['valid_time'])
    df = df.sort_values('valid_time').reset_index(drop=True)
    required = {'valid_time', 'wind_speed', 'wind_direction'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"预报文件缺少必要列：{sorted(missing)}")
    return df


def _write_detail_chunk(df: pd.DataFrame, path: str, first_write: bool):
    if df.empty:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, mode='w' if first_write else 'a', header=first_write, index=False, float_format='%.4f')


def main():
    parser = argparse.ArgumentParser(description='逐时刻 exact 版 PyWake 场站功率预测')
    parser.add_argument('--core-dir', type=str, default='')
    parser.add_argument('--forecast-csv', type=str, default='')
    parser.add_argument('--no-blockage', action='store_true')
    parser.add_argument('--no-rotor-avg', action='store_true')
    parser.add_argument('--no-turbulence', action='store_true')
    parser.add_argument(
        '--power-ws-source',
        choices=['pywake_native', 'probe_upstream', 'rotor_disc_upstream1m_mean'],
        default='pywake_native',
    )
    parser.add_argument('--power-probe-distance', type=float, default=None)
    parser.add_argument('--self-blockage-grid-n', type=int, default=9)
    parser.add_argument('--self-blockage-offset-m', type=float, default=1.0)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument('--end-index', type=int, default=-1)
    parser.add_argument('--save-turbine-details', action='store_true')
    parser.add_argument('--flush-every', type=int, default=20)
    parser.add_argument('--output-dir', type=str, default=os.path.join(_THIS_DIR, 'exact_forecast_output'))
    args = parser.parse_args()

    cfg = IntegrationConfig(
        core_python_dir=args.core_dir,
        forecast_csv_path=args.forecast_csv,
        enable_blockage=not args.no_blockage,
        rotor_avg_n=0 if args.no_rotor_avg else 4,
        enable_turbulence_model=not args.no_turbulence,
        power_ws_mode=args.power_ws_source,
        power_probe_distance_m=float(args.power_probe_distance) if args.power_probe_distance is not None else IntegrationConfig().power_probe_distance_m,
        self_blockage_rotor_grid_n=max(int(args.self_blockage_grid_n), 3),
        self_blockage_upstream_offset_m=max(float(args.self_blockage_offset_m), 0.0),
    )

    blockage_tag = 'blockage_on' if cfg.enable_blockage else 'blockage_off'
    if cfg.power_ws_mode == 'probe_upstream':
        mode_tag = f'probe_upstream_{int(cfg.power_probe_distance_m)}m'
    else:
        mode_tag = cfg.power_ws_mode
    label = f'{blockage_tag}_{mode_tag}'
    out_dir = os.path.join(os.path.abspath(args.output_dir), label)
    os.makedirs(out_dir, exist_ok=True)

    py_dir = resolve_core_python_dir(cfg.core_python_dir)
    forecast_csv = resolve_forecast_csv_path(cfg.forecast_csv_path)

    print('加载风机布局...')
    layout = load_layout(py_dir)
    turbine_ids = layout['turbine_id'].values.astype(int)
    x_wt = layout['x'].values.astype(float)
    y_wt = layout['y'].values.astype(float)

    import importlib
    if py_dir not in sys.path:
        sys.path.insert(0, py_dir)
    tm = importlib.import_module('turbine_model')
    d_wt = np.array([tm.calculate_D(int(tid))[0] for tid in turbine_ids], dtype=float)
    z_wt = np.array([tm.calculate_D(int(tid))[1] for tid in turbine_ids], dtype=float)
    types_arr = np.array([turbine_id_to_type(int(tid), py_dir) for tid in turbine_ids], dtype=int)

    print('构建 PyWake 风场模型...')
    wfm = build_wind_farm_model(cfg)

    print(f'读取预报文件：{forecast_csv}')
    forecast = load_forecast_exact(forecast_csv)
    start = max(int(args.start_index), 0)
    end = len(forecast) if args.end_index < 0 else min(int(args.end_index), len(forecast))
    forecast = forecast.iloc[start:end].reset_index(drop=True)
    if args.limit and args.limit > 0:
        forecast = forecast.iloc[:args.limit].copy()
    print(f'将逐时刻运行 {len(forecast)} 个时刻，label={label}')
    print(f'  blockage={cfg.enable_blockage}, power_ws_mode={cfg.power_ws_mode}')
    print(f'输出目录：{out_dir}')

    station_map: dict = {}
    if 'station' in layout.columns:
        station_map = dict(zip(layout['turbine_id'].astype(int), layout['station']))

    farm_rows: List[dict] = []
    station_rows: List[dict] = []
    detail_buffer: List[pd.DataFrame] = []
    detail_path = os.path.join(out_dir, 'turbine_power_timeseries.csv')
    first_detail_write = True
    t0 = time.time()

    for idx, row in forecast.iterrows():
        ts = pd.Timestamp(row['valid_time'])
        ws = float(row['wind_speed'])
        wd = float(row['wind_direction'])

        df_cond = run_one_condition(
            wfm=wfm,
            turbine_ids=turbine_ids,
            x_wt=x_wt, y_wt=y_wt, z_wt=z_wt, d_wt=d_wt,
            types_arr=types_arr,
            wind_dir=wd,
            u_100=ws,
            config=cfg,
            py_dir=py_dir,
            timestamp_label=ts.isoformat(),
        )

        _mode_label = (
            f'probe_upstream_{int(cfg.power_probe_distance_m)}m'
            if cfg.power_ws_mode == 'probe_upstream'
            else cfg.power_ws_mode
        )

        farm_row: dict = {
            'valid_time': ts,
            'wind_speed': ws,
            'wind_direction': wd,
            'enable_blockage': bool(cfg.enable_blockage),
            'power_source_mode': _mode_label,
            'farm_power_kW': float(df_cond['power_kW'].sum()),
            'farm_power_pywake_internal_kW': float(df_cond['power_pywake_internal_kW'].sum()),
            'farm_power_from_ws_eff_pywake_native_kW': float(df_cond['power_from_ws_eff_pywake_native_kW'].sum()),
            'enable_turbulence_model': bool(cfg.enable_turbulence_model),
            'rotor_avg_n': int(cfg.rotor_avg_n),
        }

        for _col in df_cond.columns:
            if (_col.startswith('power_from_upstream_') or _col.startswith('power_from_rotor_disc_upstream')) and _col.endswith('kW'):
                farm_row[f'farm_{_col}'] = float(df_cond[_col].sum())

        for _col in df_cond.columns:
            if (
                _col == 'WS_eff_pywake_native_m_s'
                or (
                    (
                        _col.startswith('WS_probe_upstream_')
                        or _col.startswith('WS_probe_downstream_')
                        or _col.startswith('WS_rotor_disc_upstream')
                    )
                    and _col.endswith('_m_s')
                )
            ):
                farm_row[f'mean_{_col}'] = float(df_cond[_col].mean())

        farm_rows.append(farm_row)

        if station_map:
            df_cond_st = df_cond.copy()
            df_cond_st['station'] = df_cond_st['turbine_id'].map(station_map)

            _pcols = [
                c for c in df_cond_st.columns
                if c.endswith('_kW') and (
                    c == 'power_kW'
                    or c.startswith('power_')
                )
            ]
            _ws_mean_cols = [
                c for c in df_cond_st.columns
                if c == 'WS_eff_pywake_native_m_s'
                or (
                    (
                        c.startswith('WS_probe_upstream_')
                        or c.startswith('WS_probe_downstream_')
                        or c.startswith('WS_rotor_disc_upstream')
                    ) and c.endswith('_m_s')
                )
            ]

            st_grp_pow = df_cond_st.groupby('station')[_pcols].sum().reset_index()
            st_grp_ws = df_cond_st.groupby('station')[_ws_mean_cols].mean().reset_index() if _ws_mean_cols else None

            for _, st_r in st_grp_pow.iterrows():
                st_entry = {
                    'valid_time': ts,
                    'wind_speed': ws,
                    'wind_direction': wd,
                    'enable_blockage': bool(cfg.enable_blockage),
                    'power_source_mode': _mode_label,
                    'station': st_r['station'],
                }
                for _c in _pcols:
                    st_entry[f'station_{_c}'] = float(st_r[_c])

                if st_grp_ws is not None:
                    _ws_row = st_grp_ws[st_grp_ws['station'] == st_r['station']]
                    if not _ws_row.empty:
                        for _wc in _ws_mean_cols:
                            st_entry[f'mean_{_wc}'] = float(_ws_row.iloc[0][_wc])

                station_rows.append(st_entry)

        if args.save_turbine_details:
            detail_buffer.append(df_cond)
            if len(detail_buffer) >= max(int(args.flush_every), 1):
                _write_detail_chunk(pd.concat(detail_buffer, ignore_index=True), detail_path, first_detail_write)
                first_detail_write = False
                detail_buffer = []

        if (int(idx) + 1) % 10 == 0 or int(idx) == len(forecast) - 1:
            elapsed = time.time() - t0
            print(
                f'  已完成 {int(idx) + 1}/{len(forecast)} 个时刻，最近时刻={ts}, '
                f'当前全场功率={farm_row["farm_power_kW"] / 1e3:.2f} MW, '
                f'累计耗时={elapsed:.1f}s'
            )

    if args.save_turbine_details and detail_buffer:
        _write_detail_chunk(pd.concat(detail_buffer, ignore_index=True), detail_path, first_detail_write)

    farm_df = pd.DataFrame(farm_rows)
    farm_path = os.path.join(out_dir, 'farm_power_timeseries.csv')
    farm_df.to_csv(farm_path, index=False, float_format='%.4f')
    print(f'\n逐时刻全场功率结果已保存：{farm_path}')

    if station_rows:
        station_df = pd.DataFrame(station_rows)
        station_path = os.path.join(out_dir, 'station_power_timeseries.csv')
        station_df.to_csv(station_path, index=False, float_format='%.4f')
        print(f'逐时刻电站级功率结果已保存：{station_path}')

    if args.save_turbine_details:
        print(f'逐时刻单机明细已保存：{detail_path}')
    print(f'输出时刻数：{len(farm_df)}')


if __name__ == '__main__':
    main()