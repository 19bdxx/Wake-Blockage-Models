# turbine_model.py

"""
风机性能参数模块
提供功能：
- 根据风机编号查找风机型号（从布局文件动态读取）
- 根据风速插值得到发电功率
- 根据风速插值得到推力系数
- 返回风机直径与轮毂高度
- 返回风机所在电厂、电厂内机位号等信息

数据来源
--------
使用 <repo>/风机布局及功率推力曲线/ 目录下的两个文件：
    turbine_data.csv   : 各型号风机的功率/推力曲线，含"风机型号"列
    turbine_layout.csv : 全场风机布局及型号对应关系，含"风机型号"列

两个文件均以"风机型号"列直接匹配，不存在硬编码风机范围。
"""

import os
import numpy as np
from scipy.interpolate import interp1d
import pandas as pd


# ── 数据文件路径解析 ──────────────────────────────────────────────────────────

def _find_data_dir() -> str:
    """
    查找包含 turbine_data.csv 和 turbine_layout.csv 的目录。

    搜索顺序：
    1. <this_file>/../../.. / 风机布局及功率推力曲线  （标准位置）
    2. <this_file>/../..   / 风机布局及功率推力曲线
    3. <this_file>/..      / 风机布局及功率推力曲线
    """
    _here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(_here, '..', '..', '..', '风机布局及功率推力曲线'),
        os.path.join(_here, '..', '..', '风机布局及功率推力曲线'),
        os.path.join(_here, '..', '风机布局及功率推力曲线'),
    ]
    for c in candidates:
        c = os.path.normpath(c)
        if os.path.isfile(os.path.join(c, 'turbine_data.csv')):
            return c
    raise FileNotFoundError(
        "无法找到 turbine_data.csv。\n"
        f"已搜索：{[os.path.normpath(c) for c in candidates]}"
    )


_DATA_DIR   = _find_data_dir()
_DATA_CSV   = os.path.join(_DATA_DIR, 'turbine_data.csv')
_LAYOUT_CSV = os.path.join(_DATA_DIR, 'turbine_layout.csv')


# ── 加载功率/推力曲线数据 ──────────────────────────────────────────────────────

def _read_csv_auto(path: str) -> pd.DataFrame:
    """自动尝试 UTF-8-BOM → GBK → latin1 编码读取 CSV。"""
    for enc in ('utf-8-sig', 'gbk', 'gb18030', 'latin1'):
        try:
            df = pd.read_csv(path, encoding=enc)
            # 确保列名是 str（避免 latin1 乱码）
            if any('\x00' in str(c) for c in df.columns):
                continue
            return df
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法以任何已知编码读取文件：{path}")


def load_turbine_data(csv_path: str = None) -> dict:
    """
    加载风机功率/推力曲线数据，返回 {type_id: {...}} 字典。

    参数
    ----
    csv_path : str, optional
        turbine_data.csv 路径；默认使用 _DATA_CSV。

    返回
    ----
    dict  {int type_id: {"speed": ndarray, "power": ndarray,
                         "thrust": ndarray, "D": float, "Z": float,
                         "model_name": str}}
    """
    if csv_path is None:
        csv_path = _DATA_CSV
    df = _read_csv_auto(csv_path)

    turbine_data = {}
    for type_id, group in df.groupby('type_id'):
        entry = {
            "speed":      group['speed'].values,
            "power":      group['power'].values,
            "thrust":     group['thrust'].values,
            "D":          float(group['D'].iloc[0]),
            "Z":          float(group['Z'].iloc[0]),
            "model_name": str(group['风机型号'].iloc[0]),
        }
        turbine_data[int(type_id)] = entry
    return turbine_data


TURBINE_DATA = load_turbine_data()


# ── 加载风机布局（编号→型号→type_id 映射） ───────────────────────────────────

def load_turbine_layout(csv_path: str = None) -> dict:
    """
    加载风机布局文件，返回 {turbine_id: {...}} 字典。

    参数
    ----
    csv_path : str, optional
        turbine_layout.csv 路径；默认使用 _LAYOUT_CSV。

    返回
    ----
    dict  {int turbine_id:
              {"model": str, "station": str, "station_slot": str,
               "type_id": int, "x": float, "y": float}}
    """
    if csv_path is None:
        csv_path = _LAYOUT_CSV
    if not os.path.isfile(csv_path):
        return {}

    df = _read_csv_auto(csv_path)

    # 建立 model_name → type_id 的映射（从 TURBINE_DATA 反查）
    model_to_typeid = {
        info['model_name']: tid
        for tid, info in TURBINE_DATA.items()
    }

    layout = {}
    for _, row in df.iterrows():
        tid   = int(row['编号'])
        model = str(row['风机型号']).strip()
        type_id = model_to_typeid.get(model, None)
        layout[tid] = {
            'model':        model,
            'station':      str(row.get('电厂', '')).strip(),
            'station_slot': str(row.get('电厂内机位号', '')).strip(),
            'type_id':      type_id,
            'x':            float(row['X']) if 'X' in row else np.nan,
            'y':            float(row['Y']) if 'Y' in row else np.nan,
        }
    return layout


TURBINE_LAYOUT = load_turbine_layout()


# ── 核心查询函数 ──────────────────────────────────────────────────────────────

def find_power_curve(n: int):
    """
    根据风机编号 n 返回其 type_id（int）。

    从 turbine_layout.csv 动态查找，找不到时返回 None。

    参数
    ----
    n : int  风机全场编号

    返回
    ----
    int  type_id，找不到时返回 None
    """
    info = TURBINE_LAYOUT.get(int(n))
    if info is not None:
        return info['type_id']
    return None


def get_turbine_info(n: int) -> dict:
    """
    返回风机 n 的完整信息字典（model, station, station_slot, type_id, x, y）。
    若布局文件未加载，返回空字典。
    """
    return TURBINE_LAYOUT.get(int(n), {})

def calculate_p(n, u):
    """
    根据风机编号n和风速u插值得到发电功率（kW）
    """
    type_id = find_power_curve(n)

    speed = TURBINE_DATA[type_id]['speed']
    power = TURBINE_DATA[type_id]['power']

    interp_func = interp1d(speed, power, kind='cubic', fill_value="extrapolate")
    return float(interp_func(u))

def calculate_ct(n, u):
    """
    根据风机编号n和风速u插值得到推力系数Ct

    参数：
        n : int
            风机编号
        u : float
            当前风速（m/s）

    返回：
        float
            推力系数Ct（无量纲）
    """
    # 找到风机型号
    type_id = find_power_curve(n)

    # 找不到对应风机，返回NaN
    if type_id is None:
        return np.nan

    # 使用三次样条插值方法，根据风速查对应推力系数
    interp_func = interp1d(TURBINE_DATA[type_id]['speed'], TURBINE_DATA[type_id]['thrust'], kind='cubic', fill_value="extrapolate")
    return float(interp_func(u))

def calculate_D(n):
    """
    根据风机编号n返回该风机的直径D（米）和轮毂高度Z（米）

    参数：
        n : int
            风机编号

    返回：
        (float, float)
            (直径D，轮毂高度Z)
    """
    # 找到风机型号
    type_id = find_power_curve(n)

    # 找不到对应风机，返回空值
    if type_id is None:
        return np.nan, np.nan

    # 返回直径D与轮毂高度Z
    return TURBINE_DATA[type_id]['D'], TURBINE_DATA[type_id]['Z']