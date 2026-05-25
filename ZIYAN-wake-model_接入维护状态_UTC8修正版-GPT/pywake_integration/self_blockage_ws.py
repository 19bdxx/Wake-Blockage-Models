"""self_blockage_ws.py

通过 ``sim_res.flow_map(Points(...))`` 在风机转子圆盘前方极近处采样，
构造一个“含 self-blockage 的转子面积加权有效风速”。

背景
----
PyWake ``SimulationResult.WS_eff`` 对风机自身使用了 i=j 清零规则，
因此不会把风机对自己前方来流的 self-blockage 直接体现在 turbine-level WS_eff 上。

本模块提供一个工程近似修正：
  1. 在每台风机转子圆盘上布置一组采样点；
  2. 沿来流方向向上游平移一个小距离 ``upstream_offset_m``；
  3. 用 ``flow_map`` 评估这些点的局地风速（含 blockage）；
  4. 对采样点做面积平均，得到 ``ws_eff_self_blockage``。

注意
----
这不是对 PyWake 内核的修改，而是集成层里的显式修正。
它更接近“转子前缘来流的面积平均风速”，可用于让 self-blockage 显式进入功率链。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import numpy as np
from py_wake.flow_map import Points


@dataclass(frozen=True)
class RotorSamplingSpec:
    """转子圆盘采样配置。"""
    grid_n: int = 9
    upstream_offset_m: float = 1.0


def _flatten(arr) -> np.ndarray:
    values = np.asarray(arr)
    if values.ndim == 3:
        return values[:, 0, 0]
    if values.ndim == 2:
        return values[:, 0]
    return values.reshape(-1)


def _flow_basis(wind_dir_deg: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回来流方向、横向方向、竖向方向的单位基向量。"""
    theta = np.deg2rad(270.0 - float(wind_dir_deg))
    e_stream = np.array([np.cos(theta), np.sin(theta), 0.0], dtype=float)
    e_cross = np.array([-np.sin(theta), np.cos(theta), 0.0], dtype=float)
    e_vert = np.array([0.0, 0.0, 1.0], dtype=float)
    return e_stream, e_cross, e_vert


def _unit_disk_square_grid(grid_n: int) -> Tuple[np.ndarray, np.ndarray]:
    """在单位圆内构造均匀方格采样点，返回 (cross, vert)。"""
    n = max(int(grid_n), 3)
    axis = np.linspace(-1.0, 1.0, n)
    cc, vv = np.meshgrid(axis, axis)
    mask = cc**2 + vv**2 <= 1.0 + 1e-12
    return cc[mask].ravel(), vv[mask].ravel()


def compute_rotor_disc_multi_distance_ws(
    sim_res,
    x_wt: np.ndarray,
    y_wt: np.ndarray,
    z_wt: np.ndarray,
    diameters: np.ndarray,
    wind_dir_deg: float,
    offsets_m: Iterable[float],
    grid_n: int = 9,
) -> Dict[float, np.ndarray]:
    """
    计算多个上游距离下、每台风机的“转子盘面面积平均有效风速”。

    参数
    ----
    sim_res : PyWake SimulationResult
    x_wt, y_wt, z_wt : ndarray
        风机中心坐标与轮毂高度
    diameters : ndarray
        风机直径（m）
    wind_dir_deg : float
        气象风向（度）
    offsets_m : iterable[float]
        上游采样距离列表（m）
    grid_n : int
        转子圆盘方格采样边长，实际有效点数约为 ``pi/4 * grid_n^2``

    返回
    ----
    dict[float, ndarray]
        键为距离（m），值为 shape=(n_turbines,) 的数组
    """
    x_wt = np.asarray(x_wt, dtype=float)
    y_wt = np.asarray(y_wt, dtype=float)
    z_wt = np.asarray(z_wt, dtype=float)
    diameters = np.asarray(diameters, dtype=float)

    n_turbines = len(x_wt)
    if not (len(y_wt) == len(z_wt) == len(diameters) == n_turbines):
        raise ValueError("x_wt/y_wt/z_wt/diameters 长度不一致")

    offsets = sorted({float(d) for d in offsets_m if float(d) >= 0.0})
    if not offsets:
        raise ValueError("offsets_m 不能为空，且距离必须 >= 0")

    e_stream, e_cross, e_vert = _flow_basis(float(wind_dir_deg))
    unit_cross, unit_vert = _unit_disk_square_grid(int(grid_n))

    result: Dict[float, np.ndarray] = {}

    for offset in offsets:
        xs = []
        ys = []
        zs = []
        owners = []

        for i in range(n_turbines):
            radius = max(float(diameters[i]) / 2.0, 0.0)
            local_cross = unit_cross * radius
            local_vert = unit_vert * radius
            center = np.array([x_wt[i], y_wt[i], z_wt[i]], dtype=float) - float(offset) * e_stream

            pts = (
                center[None, :]
                + local_cross[:, None] * e_cross[None, :]
                + local_vert[:, None] * e_vert[None, :]
            )
            xs.append(pts[:, 0])
            ys.append(pts[:, 1])
            zs.append(pts[:, 2])
            owners.append(np.full(len(pts), i, dtype=int))

        x_all = np.concatenate(xs) if xs else np.array([], dtype=float)
        y_all = np.concatenate(ys) if ys else np.array([], dtype=float)
        z_all = np.concatenate(zs) if zs else np.array([], dtype=float)
        owner_all = np.concatenate(owners) if owners else np.array([], dtype=int)

        flow = sim_res.flow_map(Points(x_all, y_all, z_all))
        ws_points = np.clip(_flatten(flow.WS_eff.values), 0.0, None)

        ws_rotor = np.full(n_turbines, np.nan, dtype=float)
        for i in range(n_turbines):
            vals = ws_points[owner_all == i]
            if vals.size:
                ws_rotor[i] = float(np.nanmean(vals))

        result[float(offset)] = ws_rotor

    return result


def compute_self_blockage_rotor_ws(
    sim_res,
    x_wt: np.ndarray,
    y_wt: np.ndarray,
    z_wt: np.ndarray,
    diameters: np.ndarray,
    wind_dir_deg: float,
    grid_n: int = 9,
    upstream_offset_m: float = 1.0,
) -> np.ndarray:
    """
    兼容旧接口：计算单一距离下每台风机“含 self-blockage 的转子面积加权有效风速”。

    返回
    ----
    ndarray, shape=(n_turbines,)
    """
    out = compute_rotor_disc_multi_distance_ws(
        sim_res=sim_res,
        x_wt=x_wt,
        y_wt=y_wt,
        z_wt=z_wt,
        diameters=diameters,
        wind_dir_deg=wind_dir_deg,
        offsets_m=[upstream_offset_m],
        grid_n=grid_n,
    )
    return out[float(upstream_offset_m)]