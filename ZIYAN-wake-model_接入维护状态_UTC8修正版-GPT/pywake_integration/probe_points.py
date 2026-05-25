# probe_points.py
"""
probe_points — 利用 PyWake flow_map API 计算风机上/下游任意距离处的风速。

当前版本统一为“新接口”：
    upstream, downstream = compute_probe_speeds(...)

返回
----
upstream / downstream 都是长度 = n_turbines 的 list[dict]
    upstream[i][10.0]   = 第 i 台风机上游 10m 的风速
    downstream[i][50.0] = 第 i 台风机下游 50m 的风速

说明
----
1. d=0 的上游探针不再放置 flow_map 点，直接返回 sim_res.WS_eff；
2. 其它距离使用 flow_map(Points(...)) 查询；
3. 保留风切变上界裁剪，避免探针值异常飙高。
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple
import numpy as np
from py_wake.flow_map import Points


def _flatten(arr) -> np.ndarray:
    values = np.asarray(arr)
    if values.ndim == 3:
        return values[:, 0, 0]
    if values.ndim == 2:
        return values[:, 0]
    return values.reshape(-1)


def _flow_basis(wind_dir_deg: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    根据气象风向返回：
    - e_stream: 来流方向单位向量（指向下游）
    - e_cross : 横向单位向量
    """
    theta = np.deg2rad(270.0 - float(wind_dir_deg))
    e_stream = np.array([np.cos(theta), np.sin(theta), 0.0], dtype=float)
    e_cross = np.array([-np.sin(theta), np.cos(theta), 0.0], dtype=float)
    return e_stream, e_cross


def compute_probe_speeds(
    sim_res,
    x_wt: np.ndarray,
    y_wt: np.ndarray,
    z_wt: np.ndarray,
    wind_dir_deg: float,
    upstream_distances: Iterable[float],
    downstream_distances: Iterable[float],
    wind_speed_ms: float | None = None,
    wind_shear_exp: float = 0.13,
) -> Tuple[List[Dict[float, float]], List[Dict[float, float]]]:
    """
    在每台风机轮毂高度上，计算多个上游/下游距离的单点风速。

    参数
    ----
    sim_res : PyWake SimulationResult
    x_wt, y_wt, z_wt : ndarray
    wind_dir_deg : float
    upstream_distances, downstream_distances : iterable[float]
    wind_speed_ms : float | None
        若提供，则按风切变计算探针风速上界，并裁剪到 [0, 1.1*u_free]
    wind_shear_exp : float
        幂律风切变指数

    返回
    ----
    upstream, downstream
        均为长度 = n_turbines 的 list[dict]
    """
    x_wt = np.asarray(x_wt, dtype=float)
    y_wt = np.asarray(y_wt, dtype=float)
    z_wt = np.asarray(z_wt, dtype=float)

    n_turbines = len(x_wt)
    if not (len(y_wt) == len(z_wt) == n_turbines):
        raise ValueError("x_wt/y_wt/z_wt 长度不一致")

    upstream_distances = [float(d) for d in upstream_distances]
    downstream_distances = [float(d) for d in downstream_distances]

    e_stream, _ = _flow_basis(float(wind_dir_deg))
    upstream: List[Dict[float, float]] = [dict() for _ in range(n_turbines)]
    downstream: List[Dict[float, float]] = [dict() for _ in range(n_turbines)]

    # d=0 的上游探针：直接使用 sim_res.WS_eff
    ws_eff_arr = _flatten(sim_res.WS_eff.values)
    for i in range(n_turbines):
        for d in upstream_distances:
            if float(d) == 0.0:
                upstream[i][0.0] = float(np.clip(ws_eff_arr[i], 0.0, None))

    # 上游真实探针点
    real_up_recs = []
    for i in range(n_turbines):
        center = np.array([x_wt[i], y_wt[i], z_wt[i]], dtype=float)
        for d in upstream_distances:
            if float(d) == 0.0:
                continue
            pt = center - float(d) * e_stream
            real_up_recs.append((i, float(d), pt[0], pt[1], pt[2]))

    if real_up_recs:
        x_all = np.array([r[2] for r in real_up_recs], dtype=float)
        y_all = np.array([r[3] for r in real_up_recs], dtype=float)
        z_all = np.array([r[4] for r in real_up_recs], dtype=float)
        fm = sim_res.flow_map(Points(x_all, y_all, z_all))
        ws = np.clip(_flatten(fm.WS_eff.values), 0.0, None)

        for (owner, d, _, _, z_probe), val in zip(real_up_recs, ws):
            if wind_speed_ms is not None:
                u_free = float(wind_speed_ms) * (float(z_probe) / 100.0) ** float(wind_shear_exp)
                val = float(np.clip(val, 0.0, u_free * 1.1))
            upstream[owner][float(d)] = float(val)

    # 下游真实探针点
    real_dn_recs = []
    for i in range(n_turbines):
        center = np.array([x_wt[i], y_wt[i], z_wt[i]], dtype=float)
        for d in downstream_distances:
            pt = center + float(d) * e_stream
            real_dn_recs.append((i, float(d), pt[0], pt[1], pt[2]))

    if real_dn_recs:
        x_all = np.array([r[2] for r in real_dn_recs], dtype=float)
        y_all = np.array([r[3] for r in real_dn_recs], dtype=float)
        z_all = np.array([r[4] for r in real_dn_recs], dtype=float)
        fm = sim_res.flow_map(Points(x_all, y_all, z_all))
        ws = np.clip(_flatten(fm.WS_eff.values), 0.0, None)

        for (owner, d, _, _, z_probe), val in zip(real_dn_recs, ws):
            if wind_speed_ms is not None:
                u_free = float(wind_speed_ms) * (float(z_probe) / 100.0) ** float(wind_shear_exp)
                val = float(np.clip(val, 0.0, u_free * 1.1))
            downstream[owner][float(d)] = float(val)

    return upstream, downstream