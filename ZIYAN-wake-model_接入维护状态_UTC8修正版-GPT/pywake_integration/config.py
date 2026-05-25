# config.py
"""
IntegrationConfig — PyWake 集成层的运行配置。

所有参数均提供合理默认值，最简调用无需传任何参数。
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class IntegrationConfig:
    """
    PyWake 集成运行配置。
    """

    core_python_dir: str = ""        # 空 = 自动查找

    enable_blockage: bool = True

    blockage_model_name: str = "SelfSimilarity"

    upstream_distances: List[float] = field(
        default_factory=lambda: [1, 5, 10, 20, 30, 40,50, 60, 70,80, 90,100, 110,120, 130,140, 150,160, 180,200, 250, 300, 350, 400]
    )



    downstream_distances: List[float] = field(
        default_factory=lambda: [50, 100, 200, 400, 500, 600, 700]
    )


    # 新增：rotor_disc 上游多距离采样列表
    rotor_disc_upstream_distances: List[float] = field(
        default_factory=lambda: [1, 10, 20, 30, 40, 50,60, 70,80,90,100,120,140,160]
    )



    wind_shear_exp: float = 0.13

    ambient_turbulence_I0: float = 0.10

    rotor_avg_n: int = 4             # EqGridRotorAvg 参数；0 = 禁用

    enable_turbulence_model: bool = True

    output_dir: str = "output_pywake"

    power_ws_mode: str = "pywake_native"

    power_probe_distance_m: float = 120.0

    # self-blockage-aware WS_eff 的转子面采样参数
    self_blockage_rotor_grid_n: int = 9
    self_blockage_upstream_offset_m: float = 1.0

    forecast_csv_path: str = ""

    superposition_model: str = "SquaredSum"


def _resolve_repo_root() -> str:
    """返回 pywake_integration 所在仓库根目录。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_forecast_csv_path(config_path: str = "") -> str:
    """
    解析场站气象预报 CSV 路径。
    """
    if config_path:
        p = os.path.abspath(config_path)
        if not os.path.isfile(p):
            raise FileNotFoundError(f"forecast_csv_path 不存在：{p!r}")
        return p

    repo_root = _resolve_repo_root()
    filename = 'wind_lat_21.250_lon_111.500.csv'
    candidates = [
        os.path.join(repo_root, '场站气象预报', filename),
        os.path.join(repo_root, '#U573a#U7ad9#U6c14#U8c61#U9884#U62a5', filename),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    try:
        for sub in os.listdir(repo_root):
            c = os.path.join(repo_root, sub, filename)
            if os.path.isfile(c):
                return c
    except OSError:
        pass

    raise FileNotFoundError(
        "无法自动找到场站气象预报 CSV。\n"
        "请在 IntegrationConfig.forecast_csv_path 中手动指定路径，例如：\n"
        "  IntegrationConfig(forecast_csv_path='/path/to/wind_lat_21.250_lon_111.500.csv')"
    )


def resolve_core_python_dir(config_dir: str = "") -> str:
    """
    解析原始项目核心 Python 目录路径。
    """
    if config_dir:
        d = os.path.abspath(config_dir)
        if not os.path.isdir(d):
            raise FileNotFoundError(f"core_python_dir 不存在：{d!r}")
        return d

    _this_dir  = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_this_dir)

    _candidates = [
        os.path.join(_repo_root, '全场尾流计算框架', 'python'),
        os.path.join(_repo_root, 'core', 'python'),
        os.path.join(_repo_root, 'wake_core'),
    ]
    try:
        for sub in os.listdir(_repo_root):
            candidate = os.path.join(_repo_root, sub, 'python')
            if candidate not in _candidates:
                _candidates.append(candidate)
    except OSError:
        pass

    for c in _candidates:
        if os.path.isfile(os.path.join(c, 'turbine_model.py')):
            return c

    raise FileNotFoundError(
        "无法自动找到包含 turbine_model.py 的原始项目目录。\n"
        "请在 IntegrationConfig.core_python_dir 中手动指定路径，例如：\n"
        "  IntegrationConfig(core_python_dir='/path/to/project/python')\n"
        f"已搜索的候选路径：{_candidates[:3]}"
    )