# run_integration.py
"""
run_integration.py — PyWake 集成层命令行入口。

运行示例
--------
    python pywake_integration/run_integration.py
    python pywake_integration/run_integration.py --quick
    python pywake_integration/run_integration.py --no-blockage
    python pywake_integration/run_integration.py --no-rotor-avg
    python pywake_integration/run_integration.py --power-ws-source probe_upstream
    python pywake_integration/run_integration.py --power-ws-source probe_upstream --power-probe-distance 40

输出文件
--------
    output_pywake/<blockage_tag>_<power_source_mode>/pywake_integration_results.csv

功率风速口径（power_ws_mode）
-----------------------------
1. pywake_native              : A 类：直接使用 PyWake 默认的 sim_res.WS_eff
2. probe_upstream             : B 类：使用上游探针风速（距离由 --power-probe-distance / config.power_probe_distance_m 控制）
                                power_source_mode 在输出中记为 probe_upstream_{d}m（如 probe_upstream_120m）
3. rotor_disc_upstream1m_mean : C 类：转子盘面上游 1m 采样均值

注：上游探针（B 类）用于来流代理和功率重算；下游探针仅输出风速，不参与功率重算。
"""

from __future__ import annotations

import sys
import os
import argparse
import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from config import IntegrationConfig, resolve_core_python_dir
from wind_farm_setup import build_wind_farm_model, turbine_id_to_type
from probe_points import compute_probe_speeds
from power_utils import calculate_power_array_from_curve_kw
from self_blockage_ws import (
    compute_self_blockage_rotor_ws,
    compute_rotor_disc_multi_distance_ws,
)


# ── 默认运行工况 ─────────────────────────────────────────────────────────────
_ALL_CONDITIONS = [
    {"wind_dir": 270.0, "u_100": 8.0},
    {"wind_dir": 270.0, "u_100": 12.0},
    {"wind_dir": 0.0,   "u_100": 8.0},
    {"wind_dir": 90.0,  "u_100": 10.0},
    {"wind_dir": 180.0, "u_100": 8.0},
]


def load_layout(py_dir: str) -> pd.DataFrame:
    """
    加载风机布局文件，使用 风机布局及功率推力曲线/turbine_layout.csv。

    返回列：turbine_id, x, y, station, turbine_model, station_slot
    """
    _this_dir  = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_this_dir)
    layout_path = os.path.join(_repo_root, '风机布局及功率推力曲线', 'turbine_layout.csv')

    if not os.path.isfile(layout_path):
        raise FileNotFoundError(f"风机布局文件不存在：{layout_path}")

    for enc in ('utf-8-sig', 'gbk', 'gb18030'):
        try:
            df = pd.read_csv(layout_path, encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 规范化列名
    df = df.rename(columns={
        '编号':       'turbine_id',
        'X':          'x',
        'Y':          'y',
        '电厂':       'station',
        '风机型号':   'turbine_model',
        '电厂内机位号': 'station_slot',
    })
    df['turbine_id'] = df['turbine_id'].astype(int)
    df['x'] = pd.to_numeric(df['x'], errors='coerce')
    df['y'] = pd.to_numeric(df['y'], errors='coerce')
    return df


def _flatten_sim_values(arr) -> np.ndarray:
    """将 PyWake 输出统一压平成 (n_turbines,) 形式。"""
    values = np.asarray(arr)
    if values.ndim == 3:
        return values[:, 0, 0]
    if values.ndim == 2:
        return values[:, 0]
    return values.flatten()


def _build_probe_distance_lists(config: IntegrationConfig):
    power_probe = float(config.power_probe_distance_m)
    upstream = sorted({float(d) for d in config.upstream_distances} | {power_probe})
    downstream = sorted({float(d) for d in config.downstream_distances})
    return upstream, downstream


def _build_rotor_disc_distance_list(config: IntegrationConfig):
    vals = getattr(config, 'rotor_disc_upstream_distances', [1, 10, 20, 30, 40, 60, 80])
    vals = sorted({float(v) for v in vals if float(v) >= 0.0})
    if not vals:
        vals = [float(getattr(config, 'self_blockage_upstream_offset_m', 1.0))]
    return vals


def check_turbine_model_consistency(py_dir: str) -> None:
    """Check consistency between turbine_layout.csv and turbine_data.csv model names."""
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_this_dir)
    data_dir = os.path.join(_repo_root, '风机布局及功率推力曲线')
    layout_path = os.path.join(data_dir, 'turbine_layout.csv')
    data_path   = os.path.join(data_dir, 'turbine_data.csv')

    for p in (layout_path, data_path):
        if not os.path.isfile(p):
            print(f"[警告] 风机型号一致性检查：文件不存在 {p}，跳过检查")
            return

    def _read_csv(p):
        for enc in ('utf-8-sig', 'gbk', 'gb18030'):
            try:
                return __import__('pandas').read_csv(p, encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return __import__('pandas').read_csv(p)

    layout_df = _read_csv(layout_path)
    data_df   = _read_csv(data_path)

    layout_col = next((c for c in layout_df.columns if '型号' in c), None)
    data_col   = next((c for c in data_df.columns   if '型号' in c), None)

    if layout_col is None or data_col is None:
        print("[警告] 风机型号一致性检查：未找到“型号”列，跳过检查")
        return

    layout_models = set(layout_df[layout_col].dropna().astype(str))
    data_models   = set(data_df[data_col].dropna().astype(str))
    diff = layout_models - data_models

    if diff:
        print(f"[警告] 风机型号一致性：布局文件中有 {len(diff)} 种型号未在 turbine_data.csv 中找到：")
        for m in sorted(diff):
            print(f"         - {m}")
    else:
        print("[OK] 风机型号一致性：布局文件与 turbine_data.csv 中的型号完全匹配")


def run_one_condition(
    wfm,
    turbine_ids,
    x_wt, y_wt, z_wt, d_wt,
    types_arr,
    wind_dir: float,
    u_100: float,
    config: IntegrationConfig,
    py_dir: str,
    timestamp_label: str | None = None,
) -> pd.DataFrame:
    upstream_dists, downstream_dists = _build_probe_distance_lists(config)
    power_probe_distance = float(config.power_probe_distance_m)
    rotor_disc_distances = _build_rotor_disc_distance_list(config)

    sim_res = wfm(
        x=np.asarray(x_wt, dtype=float),
        y=np.asarray(y_wt, dtype=float),
        h=np.asarray(z_wt, dtype=float),
        type=np.asarray(types_arr, dtype=int),
        wd=[float(wind_dir)],
        ws=[float(u_100)],
    )

    ws_eff_raw = np.clip(_flatten_sim_values(sim_res.WS_eff.values), 0.0, None)

    power_internal_raw = getattr(sim_res, "Power", None)
    if power_internal_raw is None:
        raise AttributeError("sim_res 中未找到 Power 字段，无法导出 PyWake 内部功率结果")
    power_internal_kW = np.clip(_flatten_sim_values(power_internal_raw.values) / 1000.0, 0.0, None)

    ti_eff_raw = getattr(sim_res, "TI_eff", None)
    if ti_eff_raw is None:
        ti_eff_flat = np.full(len(turbine_ids), np.nan, dtype=float)
    else:
        ti_eff_flat = _flatten_sim_values(ti_eff_raw.values)

    upstream, downstream = compute_probe_speeds(
        sim_res=sim_res,
        x_wt=np.asarray(x_wt, dtype=float),
        y_wt=np.asarray(y_wt, dtype=float),
        z_wt=np.asarray(z_wt, dtype=float),
        wind_dir_deg=float(wind_dir),
        upstream_distances=upstream_dists,
        downstream_distances=downstream_dists,
        wind_speed_ms=float(u_100),
        wind_shear_exp=float(config.wind_shear_exp),
    )

    upstream_probe_powers = {}
    for d in upstream_dists:
        probe_ws_d = np.asarray(
            [upstream[i].get(float(d), np.nan) for i in range(len(turbine_ids))],
            dtype=float,
        )
        upstream_probe_powers[float(d)] = calculate_power_array_from_curve_kw(
            turbine_ids=turbine_ids,
            wind_speeds=probe_ws_d,
            core_python_dir=py_dir,
        )

    upstream_power_ws = np.asarray(
        [upstream[i].get(power_probe_distance, np.nan) for i in range(len(turbine_ids))],
        dtype=float,
    )
    power_upstream_kW = upstream_probe_powers[power_probe_distance]

    rotor_disc_ws_dict = compute_rotor_disc_multi_distance_ws(
        sim_res=sim_res,
        x_wt=np.asarray(x_wt, dtype=float),
        y_wt=np.asarray(y_wt, dtype=float),
        z_wt=np.asarray(z_wt, dtype=float),
        diameters=np.asarray(d_wt, dtype=float),
        wind_dir_deg=wind_dir,
        offsets_m=rotor_disc_distances,
        grid_n=int(config.self_blockage_rotor_grid_n),
    )

    base_rotor_offset = float(getattr(config, 'self_blockage_upstream_offset_m', 1.0))
    if base_rotor_offset in rotor_disc_ws_dict:
        ws_eff_self_blockage = rotor_disc_ws_dict[base_rotor_offset]
    elif 1.0 in rotor_disc_ws_dict:
        ws_eff_self_blockage = rotor_disc_ws_dict[1.0]
    else:
        ws_eff_self_blockage = compute_self_blockage_rotor_ws(
            sim_res=sim_res,
            x_wt=np.asarray(x_wt, dtype=float),
            y_wt=np.asarray(y_wt, dtype=float),
            z_wt=np.asarray(z_wt, dtype=float),
            diameters=np.asarray(d_wt, dtype=float),
            wind_dir_deg=wind_dir,
            grid_n=int(config.self_blockage_rotor_grid_n),
            upstream_offset_m=base_rotor_offset,
        )

    rotor_disc_power_dict = {}
    for d, ws_arr in rotor_disc_ws_dict.items():
        rotor_disc_power_dict[float(d)] = calculate_power_array_from_curve_kw(
            turbine_ids=turbine_ids,
            wind_speeds=np.asarray(ws_arr, dtype=float),
            core_python_dir=py_dir,
        )

    power_from_rotor_disc_upstream1m_mean_kW = rotor_disc_power_dict.get(
        1.0,
        calculate_power_array_from_curve_kw(
            turbine_ids=turbine_ids,
            wind_speeds=np.asarray(ws_eff_self_blockage, dtype=float),
            core_python_dir=py_dir,
        ),
    )

    power_from_ws_eff_pywake_native_kW = calculate_power_array_from_curve_kw(
        turbine_ids=turbine_ids,
        wind_speeds=np.asarray(ws_eff_raw, dtype=float),
        core_python_dir=py_dir,
    )

    if config.power_ws_mode == 'probe_upstream':
        selected_ws = upstream_power_ws
        selected_power_kW = power_upstream_kW
    elif config.power_ws_mode == 'rotor_disc_upstream1m_mean':
        selected_ws = np.asarray(ws_eff_self_blockage, dtype=float)
        selected_power_kW = power_from_rotor_disc_upstream1m_mean_kW
    else:
        selected_ws = np.asarray(ws_eff_raw, dtype=float)
        selected_power_kW = power_from_ws_eff_pywake_native_kW

    n = len(turbine_ids)
    timestamp = timestamp_label or f"cond_{int(wind_dir):03d}_{int(u_100 * 10):04d}"

    if config.power_ws_mode == 'probe_upstream':
        _mode_label = f'probe_upstream_{int(power_probe_distance)}m'
    else:
        _mode_label = config.power_ws_mode

    rows = []

    for i in range(n):
        row = {
            "timestamp": timestamp,
            "turbine_id": int(turbine_ids[i]),
            "wind_dir": float(wind_dir),
            "u_ref_100m": float(u_100),
            "WS_eff_pywake_native_m_s": float(np.clip(ws_eff_raw[i], 0.0, None)),
            "WS_selected_for_power_curve_m_s": float(selected_ws[i]) if np.isfinite(selected_ws[i]) else np.nan,
            "power_source_mode": _mode_label,
            "power_pywake_internal_kW": float(power_internal_kW[i]),
            "power_from_ws_eff_pywake_native_kW": float(power_from_ws_eff_pywake_native_kW[i]) if np.isfinite(power_from_ws_eff_pywake_native_kW[i]) else np.nan,
            "power_kW": float(selected_power_kW[i]) if np.isfinite(selected_power_kW[i]) else np.nan,
            "TI_eff": float(ti_eff_flat[i]) if np.isfinite(ti_eff_flat[i]) else np.nan,
            "enable_blockage": bool(config.enable_blockage),
            "blockage_model": config.blockage_model_name if config.enable_blockage else "None",
            "enable_turbulence_model": bool(config.enable_turbulence_model),
        }

        row["WS_rotor_disc_upstream1m_mean_m_s"] = (
            float(rotor_disc_ws_dict.get(1.0, ws_eff_self_blockage)[i])
            if np.isfinite(rotor_disc_ws_dict.get(1.0, ws_eff_self_blockage)[i]) else np.nan
        )
        row["power_from_rotor_disc_upstream1m_mean_kW"] = (
            float(power_from_rotor_disc_upstream1m_mean_kW[i])
            if np.isfinite(power_from_rotor_disc_upstream1m_mean_kW[i]) else np.nan
        )

        for d, ws_arr in rotor_disc_ws_dict.items():
            row[f"WS_rotor_disc_upstream{int(d)}m_mean_m_s"] = (
                float(ws_arr[i]) if np.isfinite(ws_arr[i]) else np.nan
            )

        for d, p_arr in rotor_disc_power_dict.items():
            row[f"power_from_rotor_disc_upstream{int(d)}m_mean_kW"] = (
                float(p_arr[i]) if np.isfinite(p_arr[i]) else np.nan
            )

        for d in upstream_dists:
            row[f"WS_probe_upstream_{int(d)}m_m_s"] = upstream[i].get(float(d), np.nan)
        for d in downstream_dists:
            row[f"WS_probe_downstream_{int(d)}m_m_s"] = downstream[i].get(float(d), np.nan)

        for d, p_arr in upstream_probe_powers.items():
            row[f"power_from_upstream_{int(d)}m_kW"] = (
                float(p_arr[i]) if np.isfinite(p_arr[i]) else np.nan
            )

        rows.append(row)

    return pd.DataFrame(rows)

def main():
    parser = argparse.ArgumentParser(
        description="PyWake 集成层：ZIYAN 3D-DCE + PyWake blockage + 转子面积加权"
    )
    parser.add_argument("--quick", action="store_true", help="快速测试（前 2 种工况）")
    parser.add_argument("--no-blockage", action="store_true", help="不启用阻挡效应（仅尾流）")
    parser.add_argument("--no-rotor-avg", action="store_true", help="不使用 EqGridRotorAvg（退回转子中心点）")
    parser.add_argument("--no-turbulence", action="store_true", help="禁用 STF2005TurbulenceModel（退回全局固定 TI）")
    parser.add_argument("--core-dir", type=str, default="", help="原始项目 Python 核心目录（留空则自动查找）")
    parser.add_argument(
        "--power-ws-source",
        type=str,
        choices=["pywake_native", "probe_upstream", "rotor_disc_upstream1m_mean"],
        default="pywake_native",
        help=(
            "单机功率使用的风速口径：\n"
            "  pywake_native              -> A 类：sim_res.WS_eff\n"
            "  probe_upstream             -> B 类：上游探针（距离由 --power-probe-distance 控制）\n"
            "  rotor_disc_upstream1m_mean -> C 类：转子盘面上游 1m 均值"
        ),
    )
    parser.add_argument(
        "--power-probe-distance",
        type=float,
        default=None,
        help=(
            "B 类功率口径的上游探针距离（m），仅当 --power-ws-source=probe_upstream 时生效。"
            " 默认使用 config.py 中的 power_probe_distance_m（当前值：120m）。"
        ),
    )
    parser.add_argument("--self-blockage-grid-n", type=int, default=9, help="转子盘面采样边长（rotor_disc_upstream1m_mean 模式）")
    parser.add_argument("--self-blockage-offset-m", type=float, default=1.0, help="旧版单距离兼容参数（当前多距离输出中仅保留兼容用途）")
    args = parser.parse_args()

    cfg = IntegrationConfig(
        core_python_dir=args.core_dir,
        enable_blockage=not args.no_blockage,
        rotor_avg_n=0 if args.no_rotor_avg else 4,
        enable_turbulence_model=not args.no_turbulence,
        power_ws_mode=args.power_ws_source,
        power_probe_distance_m=float(args.power_probe_distance) if args.power_probe_distance is not None else IntegrationConfig().power_probe_distance_m,
        self_blockage_rotor_grid_n=max(int(args.self_blockage_grid_n), 3),
        self_blockage_upstream_offset_m=max(float(args.self_blockage_offset_m), 0.0),
    )

    py_dir = resolve_core_python_dir(cfg.core_python_dir)

    print("检查风机型号一致性…")
    check_turbine_model_consistency(py_dir)

    print("加载风机布局…")
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

    print(f"共 {len(turbine_ids)} 台风机，{len(set(types_arr))} 种类型")
    print("构建 PyWake 风场模型…")
    wfm = build_wind_farm_model(cfg)

    blk_info = cfg.blockage_model_name if cfg.enable_blockage else "无（已禁用）"
    rot_info = f"EqGridRotorAvg(n={cfg.rotor_avg_n})" if cfg.rotor_avg_n > 0 else "转子中心点（无面积加权）"
    turb_info = "STF2005TurbulenceModel（Frandsen IEC2005，逐台 TI 更新）" if cfg.enable_turbulence_model else "无（全局固定 TI）"
    print(f"  wake model    : ZiyanWakeDeficit (3D-DCE + Eq.22 风切变)")
    print(f"  blockage      : {blk_info}")
    print(f"  superposition : {cfg.superposition_model}")
    print(f"  rotor avg     : {rot_info}")
    print(f"  turbulence    : {turb_info}")
    print(f"  power ws      : {cfg.power_ws_mode}")

    conditions = _ALL_CONDITIONS[:2] if args.quick else _ALL_CONDITIONS
    all_dfs = []

    for i_cond, cond in enumerate(conditions):
        wd, u0 = cond["wind_dir"], cond["u_100"]
        print(f"  工况 {i_cond + 1}/{len(conditions)}: wd={wd}°, u100={u0} m/s … ", end="")
        df_cond = run_one_condition(
            wfm=wfm,
            turbine_ids=turbine_ids,
            x_wt=x_wt, y_wt=y_wt, z_wt=z_wt, d_wt=d_wt,
            types_arr=types_arr,
            wind_dir=wd,
            u_100=u0,
            config=cfg,
            py_dir=py_dir,
        )
        all_dfs.append(df_cond)
        print(f"全场功率 = {df_cond['power_kW'].sum() / 1e3:.1f} MW")

    result_df = pd.concat(all_dfs, ignore_index=True)

    # ── 合并电厂/型号信息 ────────────────────────────────────────────────────
    station_cols = ['turbine_id']
    for col in ('station', 'turbine_model', 'station_slot'):
        if col in layout.columns:
            station_cols.append(col)
    if len(station_cols) > 1:
        result_df = result_df.merge(
            layout[station_cols], on='turbine_id', how='left'
        )
        front_cols = ['timestamp', 'turbine_id']
        for col in ('station', 'turbine_model', 'station_slot'):
            if col in result_df.columns:
                front_cols.append(col)
        other_cols = [c for c in result_df.columns if c not in front_cols]
        result_df = result_df[front_cols + other_cols]

    os.makedirs(cfg.output_dir, exist_ok=True)

    blk_tag = 'blockage_on' if cfg.enable_blockage else 'blockage_off'
    if cfg.power_ws_mode == 'probe_upstream':
        mode_tag = f'probe_upstream_{int(cfg.power_probe_distance_m)}m'
    else:
        mode_tag = cfg.power_ws_mode

    exp_label = f'{blk_tag}_{mode_tag}'
    exp_dir = os.path.join(cfg.output_dir, exp_label)
    os.makedirs(exp_dir, exist_ok=True)
    print(f"\n输出目录：{exp_dir}")

    out_path = os.path.join(exp_dir, "pywake_integration_results.csv")
    result_df.to_csv(out_path, index=False, float_format="%.4f")
    print(f"结果已保存：{out_path}")
    print(f"结果形状：{result_df.shape[0]} 行 × {result_df.shape[1]} 列")

    _power_sum_cols = [
        c for c in result_df.columns
        if c.endswith('_kW') and (c.startswith('power_') or c == 'power_kW')
    ]

    # ── 站级聚合 ────────────────────────────────────────────────────────────
    if 'station' in result_df.columns:
        station_df = (
            result_df
            .groupby(['timestamp', 'station', 'enable_blockage', 'power_source_mode'])[_power_sum_cols]
            .sum()
            .reset_index()
        )
        station_path = os.path.join(exp_dir, "integration_station_results.csv")
        station_df.to_csv(station_path, index=False, float_format="%.4f")
        print(f"站级聚合已保存：{station_path}")

    # ── 全场聚合 ────────────────────────────────────────────────────────────
    farm_df = (
        result_df
        .groupby(['timestamp', 'enable_blockage', 'power_source_mode'])[_power_sum_cols]
        .sum()
        .reset_index()
    )
    farm_path = os.path.join(exp_dir, "integration_farm_results.csv")
    farm_df.to_csv(farm_path, index=False, float_format="%.4f")
    print(f"全场聚合已保存：{farm_path}")


if __name__ == "__main__":
    main()