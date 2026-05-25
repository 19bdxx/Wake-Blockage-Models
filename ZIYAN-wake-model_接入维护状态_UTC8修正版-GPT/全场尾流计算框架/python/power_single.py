# power_single.py

import numpy as np
from turbine_model import find_power_curve, calculate_p, calculate_ct, calculate_D
from wake_model import compute_rw, wake_model


def calculate_power_single(u_100, X1, Y1, sorted_C, return_state=False):
    """
    单时刻全场尾流计算主函数（3D-DCE 模型）

    参数：
        u_100        —— 100 m 高度处来流风速 (m/s)
        X1           —— 旋转后按顺风方向排序的风机 x 坐标数组
        Y1           —— 旋转后按顺风方向排序的风机 y 坐标数组
        sorted_C     —— 排序后的风机编号数组
        return_state —— 若 True，额外返回 C_T、I_0 数组（供尾流场计算使用）

    返回：
        u_j, P, P_total, sorted_C
        若 return_state=True，还额外返回 C_T, I_0
    """
    n  = len(X1)
    A  = np.array([X1, Y1, sorted_C])
    u_j = np.zeros(n)
    C_T = np.zeros(n)
    P   = np.zeros(n)
    I_0 = np.zeros(n)

    I_0[0] = 0.1   # 首台风机处环境湍流强度（初始值）
    a2     = 0.13  # 风切变指数

    # 离散风轮：N=8 个方位角扇区，M=20 个径向环带
    M, N = 20, 8
    # 面积权重矩阵 (N, M) ——与 MATLAB repmat((1:M).^2−(0:M-1).^2,...) 一致
    W = np.tile(((np.arange(1, M + 1)**2 - np.arange(M)**2) / (M**2 * N)), (N, 1))

    # 各方位角预计算 (N,)
    a_angles = 2 * np.pi / N * np.arange(N)
    k_arr    = np.arange(M)                   # 径向环带索引 0..M−1

    # ── 第一台风机 ──────────────────────────────────────────────────────
    D, z_h = calculate_D(A[2, 0])
    u_j[0] = u_100 * (z_h / 100) ** a2

    if 3 <= u_j[0] <= 25:
        C_T[0] = calculate_ct(A[2, 0], u_j[0])
        P[0]   = calculate_p(A[2, 0], u_j[0])

        # ── 后续机组 ──────────────────────────────────────────────────────
        for i in range(1, n):
            D, z_h = calculate_D(A[2, i])
            r0 = D / 2.0

            # 径向环带中心半径（1-indexed 公式：与 MATLAB 一致）
            r1_arr = r0 / (2 * M) * (2 * k_arr + 1)   # (M,)

            # ── 湍流强度计算（Frandsen 附加湍流模型） ─────────────────────
            I   = np.zeros(i)
            b   = 0
            for j in range(i):
                D1, z_h1 = calculate_D(A[2, j])
                rd = D1 / 2.0
                x_j_i = abs(X1[i] - X1[j])
                y_j_i = abs(Y1[i] - Y1[j])
                z_j_i = abs(z_h - z_h1)
                r_dist = np.sqrt(y_j_i**2 + z_j_i**2)
                # 使用 3D-DCE 尾流半径（Eq. 11）判断湍流影响范围
                rw_check = compute_rw(x_j_i, D1, C_T[j], I_0[j]) if x_j_i > 1.0 else 0.0
                if r_dist <= rw_check:
                    b += 1
                    I[j] = 0.25 * (C_T[j]**0.125) * (I_0[j]**-0.0625) * (x_j_i / D)**-0.5
                else:
                    I[j] = I_0[0]

            I_0[i] = np.sqrt(max(I)**2 + I_0[0]**2) if b >= 1 else I_0[0]

            # ── 尾流速度分布（向量化内循环） ──────────────────────────────
            dim = np.zeros((N, M), dtype=float)
            u   = np.zeros((N, M, i))
            Q   = np.zeros((N, M, i))

            # 当前风机 i 风轮离散点坐标 (N, M)
            a_g  = a_angles[:, np.newaxis]          # (N, 1)
            r1_g = r1_arr[np.newaxis, :]            # (1, M)
            y2_g = Y1[i] - r1_g * np.cos(a_g)      # (N, M)
            z_g  = z_h   + r1_g * np.sin(a_g)      # (N, M)

            for j in range(i):
                D1, z_h1 = calculate_D(A[2, j])
                x_j_i = abs(X1[i] - X1[j])
                if x_j_i < 1.0:           # 同行风机，跳过
                    u[:, :, j] = u_j[0] * (z_g / z_h1)**a2
                    continue

                # 3D-DCE 尾流半径（Eq. 11）
                rw = compute_rw(x_j_i, D1, C_T[j], I_0[j])

                # 当前风机 i 各离散点到上游风机 j 轴的径向距离 (N, M)
                r_g     = np.sqrt((y2_g - Y1[j])**2 + (z_g - z_h1)**2)
                in_wake = r_g <= rw

                # 3D-DCE 尾流速度（Eq. 26）
                u_wake = wake_model(u_j[j], C_T[j], D1, z_h1, r_g, z_g, a2, x_j_i, rw, I_0[j])
                u_out  = u_j[0] * (z_g / z_h1)**a2

                u[:, :, j] = np.where(in_wake, u_wake, u_out)
                Q[:, :, j] = in_wake.astype(float)
                dim        += in_wake.astype(float)

            # ── 尾流速度叠加（RSS 方法） ──────────────────────────────────
            dim1 = (dim == 0)
            dim2 = (dim == 1)
            dim3 = (dim >  1)

            U = np.zeros((N, M))
            U[dim1] = np.max(u, axis=2)[dim1]
            U[dim2] = np.min(u, axis=2)[dim2]

            res     = np.sum(Q * (u_j[:i][None, None, :] - u)**2, axis=2)
            U[dim3] = u_j[0] - np.sqrt(res[dim3])

            u_j[i] = np.sum(U * W)

            if 3 <= u_j[i] <= 25:
                C_T[i] = calculate_ct(A[2, i], u_j[i])
                P[i]   = calculate_p(A[2, i], u_j[i])
            else:
                u_j[i] = 0.0
                C_T[i] = 0.0
                P[i]   = 0.0

    P_total = float(np.sum(P))

    if return_state:
        return u_j, P, P_total, sorted_C, C_T, I_0
    return u_j, P, P_total, sorted_C


