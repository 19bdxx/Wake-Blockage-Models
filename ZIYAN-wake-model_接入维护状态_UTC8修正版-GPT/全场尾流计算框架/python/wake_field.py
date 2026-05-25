# wake_field.py

"""
全场尾流风速场计算模块（3D-DCE 模型）
功能：
- 在给定风速风向下，计算风机布置区域的二维水平风速分布
- 支持任意网格点处的尾流速度计算（使用 3D-DCE 模型）
- 供可视化分析使用
"""

import numpy as np
from turbine_model import calculate_D
from wake_model import compute_rw, compute_x0, compute_Iw
from power_single import calculate_power_single


def calculate_wake_field(u_100, a_wind, x_coords, y_coords, turbine_ids,
                         nx=200, ny=120, z_eval=None,
                         x_pad_up=1000, x_pad_dn=3000, y_pad=1500):
    """
    计算给定风速风向下的二维水平尾流风速场（3D-DCE 模型）。

    参数：
        u_100      —— 100m高度参考风速 (m/s)
        a_wind     —— 气象风向角（正北为0°，顺时针，度）
        x_coords   —— 风机原始x坐标数组 (m，高斯投影)
        y_coords   —— 风机原始y坐标数组 (m，高斯投影)
        turbine_ids—— 风机编号数组
        nx, ny     —— 计算网格分辨率（默认200×120）
        z_eval     —— 计算高度 (m)；默认取所有风机轮毂高度均值
        x_pad_up   —— 上游方向网格边距 (m)
        x_pad_dn   —— 下游方向网格边距 (m)
        y_pad      —— 横向网格边距 (m)

    返回：
        X_orig     —— 原始坐标系下网格x坐标 (ny×nx)
        Y_orig     —— 原始坐标系下网格y坐标 (ny×nx)
        U_grid     —— 网格各点处风速 (ny×nx，m/s)
        turbine_info —— dict，含各风机信息（排序后坐标、hub速度、功率等）
    """
    a2 = 0.13
    n  = len(x_coords)

    # 旋转坐标到顺风坐标系（x轴为顺风方向）
    angle = np.deg2rad(270 - a_wind)
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    X1_rot = x_coords * cos_a - y_coords * sin_a
    Y1_rot = y_coords * cos_a + x_coords * sin_a

    # 按顺风方向升序排序
    idx_sort  = np.argsort(X1_rot)
    X1        = X1_rot[idx_sort]
    Y1        = Y1_rot[idx_sort]
    sorted_ids = np.asarray(turbine_ids)[idx_sort].astype(int)

    # 取得各风机几何参数
    D_arr = np.array([calculate_D(tid)[0] for tid in sorted_ids])
    Z_arr = np.array([calculate_D(tid)[1] for tid in sorted_ids])

    if z_eval is None:
        z_eval = float(np.mean(Z_arr))

    # 运行单时刻功率计算，获取各风机状态（3D-DCE 模型）
    uj, P, P_total, _, C_T, I_0 = calculate_power_single(
        u_100, X1, Y1, sorted_ids, return_state=True
    )

    # 在顺风坐标系中建立计算网格
    x_min = X1.min() - x_pad_up
    x_max = X1.max() + x_pad_dn
    y_min = Y1.min() - y_pad
    y_max = Y1.max() + y_pad

    xg = np.linspace(x_min, x_max, nx)
    yg = np.linspace(y_min, y_max, ny)
    Xg, Yg = np.meshgrid(xg, yg)

    # 参考环境风速（在 z_eval 高度处）
    u_ref = u_100 * (z_eval / 100) ** a2

    # 初始化：各网格点的尾流亏损平方和与尾流计数（用于 RSS 叠加）
    deficit_sq = np.zeros(Xg.shape)
    n_wakes    = np.zeros(Xg.shape, dtype=int)

    for j in range(n):
        # 跳过停机或风速越限的风机
        if C_T[j] <= 0 or uj[j] < 1.0:
            continue

        D1   = D_arr[j]
        z_h1 = Z_arr[j]

        # 网格点相对于本风机的下游距离与横向距离
        dx  = Xg - X1[j]               # 顺风向距离（>0 = 该点在下游）
        dy  = Yg - Y1[j]               # 横向距离
        r3d = np.sqrt(dy**2 + (z_eval - z_h1)**2)   # 3D径向距离

        # 仅处理下游网格点
        mask_ds = dx > 0.0
        if not np.any(mask_ds):
            continue

        # 向量化计算 3D-DCE 尾流半径（Eq.11）：对每个下游网格点
        with np.errstate(invalid='ignore', divide='ignore'):
            # I_0[j] 为标量，对整个下游区统一使用
            x_D    = np.where(mask_ds, np.maximum(dx / D1, 1e-3), np.nan)
            dI     = 0.4 + 2.0 * I_0[j]
            exp_xD = -dI * (I_0[j] ** (1.1 * I_0[j]))
            Iw_g   = np.where(mask_ds,
                               (dI / 2.0) * (C_T[j] ** (dI / 4.0)) * (I_0[j] ** (-dI / 8.0))
                               * np.power(np.maximum(x_D, 1e-3), exp_xD),
                               1e-6)
            x0     = compute_x0(D1, C_T[j], I_0[j])
            x0_D   = x0 / D1
            if x0_D > 1.0:
                lr = np.where(mask_ds,
                               np.log(np.maximum(x_D, 1e-6)) / np.log(x0_D),
                               1.0)
                dr_g = np.where(mask_ds, np.maximum(-0.1 * (lr - 1.0), 0.0), 0.0)
            else:
                dr_g = np.zeros_like(Xg)
            rd = D1 / 2.0
            rw_grid = np.where(
                mask_ds,
                np.maximum(
                    3.0 * rd * (C_T[j] ** 0.35) * (I_0[j] ** 0.175)
                    * (np.maximum(Iw_g, 1e-6) ** 0.175) * (np.maximum(x_D, 1e-3) ** 0.35)
                    - rd * dr_g,
                    rd * 0.3
                ),
                0.0
            )

        # 判断是否在尾流内
        in_wake = mask_ds & (r3d <= rw_grid)
        if not np.any(in_wake):
            continue

        # 3D-DCE 尾流速度（完全向量化：内联 Eq.16–26）
        rows, cols = np.where(in_wake)
        r_pts   = r3d[rows, cols]
        z_pts   = np.full(r_pts.shape, z_eval)
        dx_pts  = np.maximum(dx[rows, cols], 1e-3)
        rw_pts  = rw_grid[rows, cols]
        rd      = D1 / 2.0

        # Eq.(17): δ_u（各点对应不同 x/D）
        xD_pts    = np.maximum(dx_pts / D1, 1e-3)
        delta_u_v = np.maximum(-0.1 * np.log(xD_pts) + 1.3, 1.0)

        # Eq.(16): u_w/u_0
        ratio_v   = np.maximum((rw_pts / rd) ** 2 - 2.0 * C_T[j], 0.0)
        uw_rat_v  = np.clip(
            (1.0 / delta_u_v) * (0.5 + 0.5 * (rd / rw_pts) * np.sqrt(ratio_v)),
            0.0, 1.0
        )

        # Eq.(18): Δu*，Eq.(25): A，几何参数
        du_star_v  = 1.0 - uw_rat_v
        r_alpha_v  = 0.6 * rd
        Delta_r_v  = np.maximum(rw_pts - r_alpha_v, rw_pts * 0.01)
        k_v        = np.pi / (2.0 * Delta_r_v)
        A_v        = np.maximum((np.pi * rw_pts) / (4.0 * Delta_r_v) * du_star_v, 0.0)

        # Eq.(22): 风切变
        u0z_pts = uj[j] * (z_pts / z_h1) ** a2

        # Eq.(26): 分段双余弦
        boundary_v    = Delta_r_v - r_alpha_v
        cos_minus_v   = np.cos(k_v * (r_pts - r_alpha_v))
        cos_plus_v    = np.cos(k_v * (r_pts + r_alpha_v))
        inner_mask_v  = r_pts < boundary_v
        u_outer_v     = u0z_pts * (1.0 - A_v * cos_minus_v)
        u_inner_v     = u0z_pts * (1.0 - A_v * (cos_minus_v + cos_plus_v))
        u_wake_pts    = np.where(inner_mask_v, u_inner_v, u_outer_v)
        u_wake_pts    = np.clip(u_wake_pts, 0.0, u0z_pts)

        deficit_pts = np.maximum(0.0, u_ref - u_wake_pts)
        deficit_sq_update = np.zeros_like(deficit_sq)
        np.add.at(deficit_sq_update, (rows, cols), deficit_pts ** 2)
        deficit_sq += deficit_sq_update
        n_wakes[in_wake] += 1

    # RSS 叠加合成风速
    U_grid = np.where(
        n_wakes > 0,
        np.maximum(0.0, u_ref - np.sqrt(deficit_sq)),
        u_ref
    )

    # 将顺风坐标系网格点转换回原始坐标系（逆旋转）
    cos_b, sin_b = np.cos(-angle), np.sin(-angle)
    X_orig = Xg * cos_b - Yg * sin_b
    Y_orig = Yg * cos_b + Xg * sin_b

    # 将排序后的风机坐标也转回原始坐标系（供绘图用）
    x_t_orig = X1 * cos_b - Y1 * sin_b
    y_t_orig = Y1 * cos_b + X1 * sin_b

    turbine_info = {
        'x_rot':  X1,
        'y_rot':  Y1,
        'x_orig': x_t_orig,
        'y_orig': y_t_orig,
        'ids':    sorted_ids,
        'uj':     uj,
        'P':      P,
        'C_T':    C_T,
        'P_total': P_total,
        'u_ref':  u_ref,
    }

    return X_orig, Y_orig, U_grid, turbine_info

