# power_utils.py
"""功率曲线与风速口径辅助函数。"""

from __future__ import annotations

import importlib
import sys
from typing import Iterable

import numpy as np


def _load_turbine_model(core_python_dir: str):
    if core_python_dir not in sys.path:
        sys.path.insert(0, core_python_dir)
    if 'turbine_model' in sys.modules:
        return sys.modules['turbine_model']
    return importlib.import_module('turbine_model')


def calculate_power_from_curve_kw(turbine_id: int, wind_speed: float, core_python_dir: str) -> float:
    """
    按原始 turbine_model.py 中的功率曲线，根据给定风速计算单机功率。

    规则：
      - 风速缺失或 < 0 → NaN / 0
      - 低于曲线最小风速（通常 3m/s）→ 0
      - 高于曲线最大风速 → 取最大曲线风速处功率（通常额定）
    """
    if wind_speed is None or not np.isfinite(wind_speed):
        return float('nan')

    ws = float(max(wind_speed, 0.0))
    tm = _load_turbine_model(core_python_dir)
    type_id = tm.find_power_curve(int(turbine_id))
    if type_id is None:
        return float('nan')

    curve_ws = np.asarray(tm.TURBINE_DATA[type_id]['speed'], dtype=float)
    if ws < float(curve_ws.min()):
        return 0.0

    ws_eval = min(ws, float(curve_ws.max()))
    power_kw = float(tm.calculate_p(int(turbine_id), ws_eval))
    return float(max(power_kw, 0.0))


def calculate_power_array_from_curve_kw(
    turbine_ids: Iterable[int],
    wind_speeds: Iterable[float],
    core_python_dir: str,
) -> np.ndarray:
    """按给定风速数组批量计算单机功率（kW）。"""
    return np.asarray([
        calculate_power_from_curve_kw(int(tid), float(ws), core_python_dir)
        for tid, ws in zip(turbine_ids, wind_speeds)
    ], dtype=float)
