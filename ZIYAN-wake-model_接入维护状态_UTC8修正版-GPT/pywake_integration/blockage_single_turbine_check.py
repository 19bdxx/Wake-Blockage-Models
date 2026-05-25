"""
blockage_single_turbine_check.py

单机 blockage 验证脚本。

用途
----
在同一台风机、同一风速/风向工况下，分别运行：
  1. 仅尾流（blockage=False）
  2. 尾流 + blockage（blockage=True）

并专门输出（统一列名约定）：
  A 类风速：WS_eff_pywake_native_m_s    <- sim_res.WS_eff，始终直接来自 PyWake
  B 类风速：WS_probe_upstream_40m_m_s   <- 前方 40m 探针
            WS_probe_upstream_120m_m_s  <- 前方 120m 探针
            WS_probe_upstream_300m_m_s  <- 前方 300m 探针
  C 类风速：WS_rotor_disc_upstream1m_mean_m_s <- 转子前缘上游 1m 处圆盘采样点风速均值

  功率列：
    power_pywake_internal_kW              <- sim_res.Power / 1000
    power_from_ws_eff_pywake_native_kW    <- A 类风速重算功率曲线
    power_from_rotor_disc_upstream1m_mean_kW <- C 类风速重算功率曲线
    power_from_upstream_40m_kW            <- B 类 40m 探针重算
    power_from_upstream_120m_kW           <- B 类 120m 探针重算
    power_from_upstream_300m_kW           <- B 类 300m 探针重算

输出 CSV 每行表示一种 blockage 开关状态，便于直接对比。
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from config import IntegrationConfig, resolve_core_python_dir
from wind_farm_setup import build_wind_farm_model, turbine_id_to_type
from probe_points import compute_probe_speeds
from power_utils import calculate_power_from_curve_kw
from self_blockage_ws import compute_self_blockage_rotor_ws
from run_integration import load_layout




def _flatten_sim_values(arr) -> np.ndarray:
    values = np.asarray(arr)
    if values.ndim == 3:
        return values[:, 0, 0]
    if values.ndim == 2:
        return values[:, 0]
    return values.flatten()



def _pick_single_turbine(layout: pd.DataFrame, turbine_id: int | None) -> pd.Series:
    if turbine_id is None:
        return layout.iloc[0]
    matched = layout.loc[layout['turbine_id'].astype(int) == int(turbine_id)]
    if matched.empty:
        all_ids = ', '.join(map(str, layout['turbine_id'].astype(int).tolist()[:20]))
        raise ValueError(f"找不到 turbine_id={turbine_id}。示例可用风机号：{all_ids}")
    return matched.iloc[0]



def _run_one_mode(
    *,
    py_dir: str,
    turbine_id: int,
    x: float,
    y: float,
    z: float,
    diameter: float,
    type_index: int,
    wind_dir: float,
    wind_speed: float,
    enable_blockage: bool,
    rotor_avg_n: int,
    enable_turbulence_model: bool,
    ambient_ti: float,
    wind_shear_exp: float,
    blockage_model_name: str,
    self_blockage_grid_n: int,
    self_blockage_offset_m: float,
) -> dict:
    cfg = IntegrationConfig(
        core_python_dir=py_dir,
        enable_blockage=enable_blockage,
        blockage_model_name=blockage_model_name,
        rotor_avg_n=rotor_avg_n,
        enable_turbulence_model=enable_turbulence_model,
        ambient_turbulence_I0=ambient_ti,
        wind_shear_exp=wind_shear_exp,
        downstream_distances=[],
        power_ws_mode='pywake_native',
    )
    # 从 config 动态派生非零上游探针距离，不再硬编码 [40, 120, 300]
    probe_distances = [d for d in cfg.upstream_distances if d > 0]

    wfm = build_wind_farm_model(cfg)
    sim_res = wfm(
        np.asarray([x], dtype=float),
        np.asarray([y], dtype=float),
        type=np.asarray([type_index], dtype=int),
        wd=[wind_dir],
        ws=[wind_speed],
    )

    # A 类风速（PyWake 原生）
    ws_eff_pywake_native = float(_flatten_sim_values(sim_res.WS_eff.values)[0])

    # C 类风速（转子盘面上游 1m 均值）
    ws_rotor_disc_upstream1m_mean = float(compute_self_blockage_rotor_ws(
        sim_res=sim_res,
        x_wt=np.asarray([x], dtype=float),
        y_wt=np.asarray([y], dtype=float),
        z_wt=np.asarray([z], dtype=float),
        diameters=np.asarray([float(diameter)], dtype=float),
        wind_dir_deg=wind_dir,
        grid_n=int(self_blockage_grid_n),
        upstream_offset_m=float(self_blockage_offset_m),
    )[0])

    # PyWake 内部功率
    power_pywake_internal_kW = float(_flatten_sim_values(sim_res.Power.values)[0] / 1000.0)

    if hasattr(sim_res, 'TI_eff'):
        ti_eff = float(_flatten_sim_values(sim_res.TI_eff.values)[0])
    else:
        ti_eff = np.nan

    # B 类风速（探针）
    probe_dict = compute_probe_speeds(
        sim_res=sim_res,
        x_wt=np.asarray([x], dtype=float),
        y_wt=np.asarray([y], dtype=float),
        z_wt=np.asarray([z], dtype=float),
        wind_dir_deg=wind_dir,
        wind_speed_ms=wind_speed,
        upstream_dists=cfg.upstream_distances,
        downstream_dists=[],
        wind_shear_exp=wind_shear_exp,
    )
    upstream = probe_dict['upstream_speeds'][0]

    row = {
        'turbine_id': int(turbine_id),
        'wind_dir': float(wind_dir),
        'u_ref_100m': float(wind_speed),
        'enable_blockage': bool(enable_blockage),
        'blockage_model': blockage_model_name if enable_blockage else 'None',
        'rotor_avg_n': int(rotor_avg_n),
        'enable_turbulence_model': bool(enable_turbulence_model),
        'ambient_turbulence_I0': float(ambient_ti),
        'wind_shear_exp': float(wind_shear_exp),
        # A 类
        'WS_eff_pywake_native_m_s': float(ws_eff_pywake_native),
        # C 类
        'WS_rotor_disc_upstream1m_mean_m_s': float(ws_rotor_disc_upstream1m_mean),
        'TI_eff': float(ti_eff) if np.isfinite(ti_eff) else np.nan,
        # 功率
        'power_pywake_internal_kW': float(power_pywake_internal_kW),
        'power_from_ws_eff_pywake_native_kW': calculate_power_from_curve_kw(
            turbine_id=int(turbine_id),
            wind_speed=ws_eff_pywake_native,
            core_python_dir=py_dir,
        ),
        'power_from_rotor_disc_upstream1m_mean_kW': calculate_power_from_curve_kw(
            turbine_id=int(turbine_id),
            wind_speed=ws_rotor_disc_upstream1m_mean,
            core_python_dir=py_dir,
        ),
    }

    # B 类风速列（WS_probe_upstream_{d}m_m_s）—— 动态生成，遍历 cfg.upstream_distances
    for d in cfg.upstream_distances:
        key = f'WS_probe_upstream_{int(d)}m_m_s'
        val = upstream.get(float(d), np.nan)
        row[key] = float(val) if np.isfinite(val) else np.nan

    # B 类功率列（仅非零距离参与功率重算）
    for d in probe_distances:
        probe_ws = row[f'WS_probe_upstream_{int(d)}m_m_s']
        row[f'power_from_upstream_{int(d)}m_kW'] = calculate_power_from_curve_kw(
            turbine_id=int(turbine_id),
            wind_speed=probe_ws,
            core_python_dir=py_dir,
        )

    # 差值诊断（以 A 类风速为基准，动态遍历所有 probe 距离）
    for _d in probe_distances:
        _key = f'WS_probe_upstream_{int(_d)}m_m_s'
        if _key in row:
            row[f'delta_probe_{int(_d)}_minus_ws_eff_native_m_s'] = (
                row[_key] - row['WS_eff_pywake_native_m_s']
            )
    row['delta_rotor_disc_minus_ws_eff_native_m_s'] = (
        row['WS_rotor_disc_upstream1m_mean_m_s'] - row['WS_eff_pywake_native_m_s']
    )
    return row



def _print_brief(df: pd.DataFrame) -> None:
    # 动态检测列（不再硬编码 40/120/300）
    base_cols = ['enable_blockage', 'WS_eff_pywake_native_m_s', 'WS_rotor_disc_upstream1m_mean_m_s']
    probe_ws_cols = sorted([c for c in df.columns if c.startswith('WS_probe_upstream_') and c.endswith('_m_s')])
    power_base_cols = ['power_pywake_internal_kW', 'power_from_ws_eff_pywake_native_kW',
                       'power_from_rotor_disc_upstream1m_mean_kW']
    probe_power_cols = sorted([c for c in df.columns if c.startswith('power_from_upstream_') and c.endswith('m_kW')])
    show_cols = base_cols + probe_ws_cols + power_base_cols + probe_power_cols
    available = [c for c in show_cols if c in df.columns]
    print("\n单机 blockage 验证结果：")
    print(df[available].to_string(index=False))

    if len(df) == 2:
        off = df.loc[df['enable_blockage'] == False].iloc[0]
        on = df.loc[df['enable_blockage'] == True].iloc[0]
        diff = {}
        for _c in ['WS_eff_pywake_native_m_s', 'WS_rotor_disc_upstream1m_mean_m_s']:
            if _c in df.columns:
                diff[f'delta_{_c}'] = on[_c] - off[_c]
        for _c in df.columns:
            if _c.startswith('WS_probe_upstream_') and _c.endswith('_m_s'):
                diff[f'delta_{_c}'] = on[_c] - off[_c]
        for _c in df.columns:
            if _c.endswith('_kW') and not _c.startswith('delta_'):
                diff[f'delta_{_c}'] = on[_c] - off[_c]
        print("\nblockage=True 相比 blockage=False 的差值：")
        for k, v in diff.items():
            print(f"  {k}: {v:.6f}")



def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='单机 blockage 验证：对比 A/B/C 三类风速及对应功率')
    parser.add_argument('--turbine-id', type=int, default=None, help='指定单机验证的风机 ID；默认取 turbine_layout.csv 第一台')
    parser.add_argument('--wind-dir', type=float, default=270.0, help='气象风向（度）')
    parser.add_argument('--wind-speed', type=float, default=8.0, help='100m 参考风速（m/s）')
    parser.add_argument('--core-dir', type=str, default='', help='原始项目 python 目录；留空自动查找')
    parser.add_argument('--rotor-avg-n', type=int, default=4, help='EqGridRotorAvg 参数；0 表示关闭转子平均')
    parser.add_argument('--no-turbulence', action='store_true', help='禁用 STF2005TurbulenceModel')
    parser.add_argument('--ambient-ti', type=float, default=0.10, help='环境湍流强度 I0')
    parser.add_argument('--wind-shear-exp', type=float, default=0.13, help='幂律风切变指数 alpha')
    parser.add_argument('--blockage-model', type=str, default='SelfSimilarity',
                        choices=['SelfSimilarity', 'Rathmann', 'VortexCylinder'],
                        help='blockage 模型名称')
    parser.add_argument('--self-blockage-grid-n', type=int, default=9,
                        help='WS_rotor_disc_upstream1m_mean 计算时的转子圆盘采样边长')
    parser.add_argument('--self-blockage-offset-m', type=float, default=1.0,
                        help='WS_rotor_disc_upstream1m_mean 计算时沿来流方向上游平移的距离（m）')
    parser.add_argument('--output-dir', type=str, default='single_turbine_blockage_check_output',
                        help='CSV 输出目录')
    args = parser.parse_args(list(argv) if argv is not None else None)

    py_dir = resolve_core_python_dir(args.core_dir)
    layout = load_layout(py_dir)
    wt_row = _pick_single_turbine(layout, args.turbine_id)

    turbine_id = int(wt_row['turbine_id'])
    x = float(wt_row['x'])
    y = float(wt_row['y'])
    type_index = int(turbine_id_to_type(turbine_id, py_dir))

    import importlib
    if py_dir not in sys.path:
        sys.path.insert(0, py_dir)
    tm = importlib.import_module('turbine_model')
    type_key = tm.find_power_curve(turbine_id)
    if type_key is None:
        raise RuntimeError(f'无法根据 turbine_id={turbine_id} 找到机型')
    z = float(tm.TURBINE_DATA[type_key]['Z'])
    diameter = float(tm.TURBINE_DATA[type_key]['D'])

    rows = []
    for enable_blockage in [False, True]:
        rows.append(_run_one_mode(
            py_dir=py_dir,
            turbine_id=turbine_id,
            x=x,
            y=y,
            z=z,
            diameter=diameter,
            type_index=type_index,
            wind_dir=float(args.wind_dir),
            wind_speed=float(args.wind_speed),
            enable_blockage=enable_blockage,
            rotor_avg_n=int(args.rotor_avg_n),
            enable_turbulence_model=not args.no_turbulence,
            ambient_ti=float(args.ambient_ti),
            wind_shear_exp=float(args.wind_shear_exp),
            blockage_model_name=args.blockage_model,
            self_blockage_grid_n=max(int(args.self_blockage_grid_n), 3),
            self_blockage_offset_m=max(float(args.self_blockage_offset_m), 0.0),
        ))

    df = pd.DataFrame(rows)
    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    out_name = (
        f"single_turbine_blockage_check_"
        f"tid{turbine_id}_wd{int(round(args.wind_dir))}_ws{str(args.wind_speed).replace('.', 'p')}.csv"
    )
    out_path = os.path.join(out_dir, out_name)
    df.to_csv(out_path, index=False, encoding='utf-8-sig')

    print(f"风机 ID: {turbine_id}")
    print(f"坐标: x={x:.3f} m, y={y:.3f} m, z={z:.3f} m")
    print(f"输出文件: {out_path}")
    _print_brief(df)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
