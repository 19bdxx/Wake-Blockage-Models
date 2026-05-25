# wind_farm_setup.py
"""
wind_farm_setup — 构建 PyWake 风场模型（WindTurbines + Site + All2AllIterative）。

设计说明
--------
* WindTurbines：依据 turbine_data.csv 中的风机型号动态构建 PowerCtTabular，
  每台风机以 type 索引（turbine_data.csv 中 type_id 的排序位置）区分。
* Site：UniformSite + PowerShear（h_ref=100 m, α=config.wind_shear_exp），
  与原始 power_single.py 中 u(z)=u_100·(z/100)^0.13 保持一致。
* wake_deficitModel：ZiyanWakeDeficit（3D-DCE，含 Eq.22 风切变 + EqGridRotorAvg）。
* blockage_deficitModel：PyWake 内置（SelfSimilarityDeficit2020 等），可选。
* superpositionModel：SquaredSum（与原始 RSS 方法一致）。

路径解析
--------
原始项目 Python 核心目录通过 config.core_python_dir 配置（或自动查找）。
此模块 **不修改** 任何原始项目文件，仅以只读方式访问 turbine_model.py。
"""

import sys
import os
import importlib
import numpy as np
from typing import Optional

from py_wake.site import UniformSite
from py_wake.site.shear import PowerShear
from py_wake.wind_turbines import WindTurbines
from py_wake.wind_turbines.power_ct_functions import PowerCtTabular
from py_wake.wind_farm_models import All2AllIterative
from py_wake.superposition_models import SquaredSum, LinearSum
from py_wake.deficit_models.selfsimilarity import SelfSimilarityDeficit2020
from py_wake.deficit_models.rathmann import Rathmann
from py_wake.deficit_models.vortexcylinder import VortexCylinder
from py_wake.rotor_avg_models import EqGridRotorAvg
from py_wake.turbulence_models.stf import STF2005TurbulenceModel

from config import IntegrationConfig
from config import resolve_core_python_dir


# ── 延迟加载的原始模块（避免模块级路径硬编码） ──────────────────────────────
_turbine_model   = None
_ziyan_deficit   = None


def _load_core_modules(core_python_dir: str):
    """
    确保原始项目核心 Python 目录在 sys.path 中，并返回 turbine_model 模块。

    参数
    ----
    core_python_dir : str  已解析的绝对路径（来自 resolve_core_python_dir）

    返回
    ----
    turbine_model module
    """
    global _turbine_model

    _this_dir = os.path.dirname(os.path.abspath(__file__))
    for _p in (core_python_dir, _this_dir):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    # 强制重新加载（防止 sys.path 更新前已被错误缓存）
    if 'turbine_model' in sys.modules:
        _turbine_model = sys.modules['turbine_model']
    else:
        _turbine_model = importlib.import_module('turbine_model')

    return _turbine_model


def build_wind_turbines(core_python_dir: str) -> WindTurbines:
    """
    根据 turbine_model.TURBINE_DATA 构建 PyWake WindTurbines 对象。

    风机类型数量和型号名称完全由 turbine_data.csv 决定，
    type 索引对应 TURBINE_DATA 中 type_id 升序排列的位置。

    参数
    ----
    core_python_dir : str  已解析的原始 Python 目录路径

    返回
    ----
    WindTurbines  每种 type_id 对应一个 PowerCtTabular
    """
    tm = _load_core_modules(core_python_dir)

    sorted_type_keys = sorted(tm.TURBINE_DATA.keys())
    diameters   = []
    hub_heights = []
    pct_funcs   = []
    names       = []

    for type_key in sorted_type_keys:
        data   = tm.TURBINE_DATA[type_key]
        D      = float(data['D'])
        Z      = float(data['Z'])
        speed  = np.asarray(data['speed'],  dtype=float)
        power  = np.clip(np.asarray(data['power'],   dtype=float), 0.0, None)  # kW
        thrust = np.clip(np.asarray(data['thrust'],  dtype=float), 0.01, 0.99)

        diameters.append(D)
        hub_heights.append(Z)
        pct_funcs.append(
            PowerCtTabular(ws=speed, power=power, power_unit='kW', ct=thrust)
        )
        names.append(data.get('model_name', f'Type{type_key}'))

    return WindTurbines(
        names=names,
        diameters=diameters,
        hub_heights=hub_heights,
        powerCtFunctions=pct_funcs,
    )


def turbine_id_to_type(turbine_id: int, core_python_dir: str) -> int:
    """
    将原始风机编号转换为 PyWake type 索引（从 0 开始）。

    type 索引对应 TURBINE_DATA 中 type_id 升序排列的位置。
    找不到 type_id 时返回 0（第一种风机型号作为默认）。

    参数
    ----
    turbine_id    : int  原始风机 ID
    core_python_dir : str

    返回
    ----
    int  PyWake type 索引
    """
    tm = _load_core_modules(core_python_dir)
    type_key = tm.find_power_curve(turbine_id)
    if type_key is None:
        return 0
    sorted_type_keys = sorted(tm.TURBINE_DATA.keys())
    try:
        return sorted_type_keys.index(type_key)
    except ValueError:
        return 0


def build_site(config: IntegrationConfig) -> UniformSite:
    """
    构建 PyWake Site（UniformSite + PowerShear）。

    使用幂律风切变 u(z) = u_hub·(z/100)^α，
    与原始 power_single.py 中的 wind_shear_exp=0.13 保持一致。
    """
    return UniformSite(
        p_wd=[1],
        ti=float(config.ambient_turbulence_I0),
        shear=PowerShear(h_ref=100.0, alpha=float(config.wind_shear_exp)),
    )


def _get_blockage_model(config: IntegrationConfig):
    """
    根据配置返回 PyWake 阻挡模型（或 None）。

    阻挡模型负责上游速度降低（induction zone），与激光雷达在
    100–120 m 处观测到的来流减速对应。

    注意：blockage 模型始终使用 LinearSum 叠加，
    因为 SelfSimilarityDeficit2020 等可产生"speedup"（负亏损），
    SquaredSum 不支持负值。
    """
    if not config.enable_blockage:
        return None

    name = config.blockage_model_name
    if name in ('SelfSimilarity', 'SelfSimilarityDeficit2020'):
        return SelfSimilarityDeficit2020(superpositionModel=LinearSum())
    elif name == 'Rathmann':
        return Rathmann(superpositionModel=LinearSum())
    elif name == 'VortexCylinder':
        return VortexCylinder(superpositionModel=LinearSum())
    elif name in ('None', 'NoBlockage', 'none'):
        return None
    else:
        raise ValueError(
            f"未知阻挡模型 {name!r}。可选值：'SelfSimilarity', 'Rathmann', 'VortexCylinder', 'None'"
        )


def _get_rotor_avg_model(config: IntegrationConfig):
    """
    根据 config.rotor_avg_n 返回 EqGridRotorAvg(n) 或 None。

    EqGridRotorAvg(n) 在转子圆面上均匀布置约 n²×π/4 个采样点，
    对速度亏损做面积平均，使 WS_eff 成为真正的"转子面积加权平均风速"。

    n=0 或 None → 不做面积加权（使用转子中心点，与原始 WS_eff 接近）
    n=4 (默认) → ~8 个采样点，计算效率与精度的合理平衡
    n=8        → ~40 个采样点，更接近原始 N=8×M=20 极坐标网格
    """
    n = int(getattr(config, 'rotor_avg_n', 4))
    if n <= 0:
        return None
    return EqGridRotorAvg(n)


def _get_turbulence_model(config: IntegrationConfig):
    """
    根据配置返回湍流模型（或 None）。

    STF2005TurbulenceModel 实现 IEC 61400-1:2005 Frandsen 方案：
      TI_add[i←j] = 0.9 / (1.5 + 0.3·(x/D)·√u0)

    All2AllIterative 在迭代中调用该模型更新每台风机的 TI_eff_ilk[i]，
    使其随上游尾流影响逐步叠加，近似复现原始 power_single.py 中
    对每台风机动态计算局地湍流强度 I0 的逻辑。

    ZiyanWakeDeficit 以 use_effective_ti=True 接收 TI_eff_ilk 作为 I0，
    影响 rw（尾流半径）和 Iw（尾流湍流强度），从而改善多排风机的尾流精度。
    """
    if config.enable_turbulence_model:
        return STF2005TurbulenceModel()
    return None


def _get_superposition_model(config: IntegrationConfig):
    """SquaredSum 对应原始 RSS 叠加；LinearSum 为备选。"""
    if config.superposition_model == 'LinearSum':
        return LinearSum()
    return SquaredSum()


def build_wind_farm_model(config: IntegrationConfig) -> All2AllIterative:
    """
    完整构建 PyWake All2AllIterative 风场模型。

    模型架构
    --------
    wake         : ZiyanWakeDeficit（3D-DCE + Eq.22 风切变 + EqGridRotorAvg）
    blockage     : SelfSimilarityDeficit2020 等 PyWake 内置（可选）
    superposition: SquaredSum（与原始 RSS 一致）
    turbulence   : STF2005TurbulenceModel（Frandsen IEC2005，可选）
                   → 逐台更新 TI_eff_ilk，ZiyanWakeDeficit 以此为 I0
                   → 近似复现原始模型中逐台更新局地湍流强度的逻辑
    site         : UniformSite + PowerShear(h_ref=100 m, α=0.13)
    turbines     : 由 turbine_data.csv 动态确定的风机型号（来自 turbine_model.TURBINE_DATA）

    与原始模型的已知差异
    --------------------
    - STF2005 Frandsen 公式 ≠ 原始自定义 Frandsen
    - EqGridRotorAvg 笛卡尔网格 ≠ 原始 8×20 极坐标网格
    - PyWake 迭代求解 ≠ 原始顺风排序

    参数
    ----
    config : IntegrationConfig

    返回
    ----
    All2AllIterative
    """
    from ziyan_deficit import ZiyanWakeDeficit

    py_dir  = resolve_core_python_dir(config.core_python_dir)
    site    = build_site(config)
    wt      = build_wind_turbines(py_dir)
    rot_avg = _get_rotor_avg_model(config)
    turb_m  = _get_turbulence_model(config)

    # use_effective_ti=True 时，ZiyanWakeDeficit 使用 TI_eff_ilk（逐台更新）作为 I0
    # 只有同时启用 turbulenceModel 才有意义；否则退回到全局 TI_ilk
    use_eff_ti = config.enable_turbulence_model

    wfm = All2AllIterative(
        site=site,
        windTurbines=wt,
        wake_deficitModel=ZiyanWakeDeficit(
            alpha=float(config.wind_shear_exp),
            use_effective_ws=True,
            use_effective_ti=use_eff_ti,
            rotorAvgModel=rot_avg,
        ),
        superpositionModel=_get_superposition_model(config),
        blockage_deficitModel=_get_blockage_model(config),
        turbulenceModel=turb_m,
    )
    return wfm
