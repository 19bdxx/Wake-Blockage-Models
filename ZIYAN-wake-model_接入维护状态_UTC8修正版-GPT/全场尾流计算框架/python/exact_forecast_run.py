#!/usr/bin/env python3
from __future__ import annotations

"""逐时刻运行原始“全场尾流计算框架”，输出场站总功率时序。"""

import argparse
import os
import pandas as pd
import numpy as np

from power_single import calculate_power_single


def load_layout(py_dir: str) -> pd.DataFrame:
    path = os.path.join(py_dir, 'data', 'turbine_layout.csv')
    return pd.read_csv(path)


def load_forecast(forecast_csv: str) -> pd.DataFrame:
    df = pd.read_csv(forecast_csv, parse_dates=['valid_time'])
    required = {'valid_time', 'wind_speed', 'wind_direction'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'预报文件缺少必要列：{sorted(missing)}')
    return df.sort_values('valid_time').reset_index(drop=True)


def run_one_condition(u_100: float, wind_dir: float, x_coords: np.ndarray, y_coords: np.ndarray) -> float:
    n_turbines = len(x_coords)
    X1 = x_coords * np.cos(np.deg2rad(270.0 - wind_dir)) - y_coords * np.sin(np.deg2rad(270.0 - wind_dir))
    Y1 = y_coords * np.cos(np.deg2rad(270.0 - wind_dir)) + x_coords * np.sin(np.deg2rad(270.0 - wind_dir))
    A = np.vstack((X1, Y1, np.arange(1, n_turbines + 1)))
    idx_sort = np.argsort(A[0, :])
    _, _, p_total, _ = calculate_power_single(float(u_100), A[0, idx_sort], A[1, idx_sort], A[2, idx_sort])
    return float(p_total)


def main():
    parser = argparse.ArgumentParser(description='逐时刻运行原始全场尾流框架')
    parser.add_argument('--forecast-csv', required=True, help='气象预报 CSV 路径')
    parser.add_argument('--output-csv', default='original_exact_farm_power_timeseries.csv', help='输出 CSV 路径')
    parser.add_argument('--limit', type=int, default=0, help='仅运行前 N 个时刻，0 表示全量')
    args = parser.parse_args()

    py_dir = os.path.dirname(os.path.abspath(__file__))
    layout = load_layout(py_dir)
    x_coords = layout['x'].values.astype(float)
    y_coords = layout['y'].values.astype(float)
    forecast = load_forecast(args.forecast_csv)
    if args.limit and args.limit > 0:
        forecast = forecast.iloc[:args.limit].copy()

    rows = []
    for _, row in forecast.iterrows():
        rows.append({
            'valid_time': row['valid_time'],
            'wind_speed': float(row['wind_speed']),
            'wind_direction': float(row['wind_direction']),
            'farm_power_kW': run_one_condition(float(row['wind_speed']), float(row['wind_direction']), x_coords, y_coords),
        })

    out = pd.DataFrame(rows)
    out.to_csv(args.output_csv, index=False, float_format='%.4f')
    print(f'已保存：{os.path.abspath(args.output_csv)}')


if __name__ == '__main__':
    main()
