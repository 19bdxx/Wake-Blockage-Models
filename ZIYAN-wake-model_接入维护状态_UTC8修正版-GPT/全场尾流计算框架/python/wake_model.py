# wake_model.py
"""
3D-DCE（三维双余弦卷吸）单机尾流模型

论文：Bao et al., "A novel three-dimensional dual-cosine wake model
      for wind turbine full wake predictions"

核心方程：
  Eq.(6)  — 尾流湍流强度 I_w
  Eq.(7)  — 湍流参数 δ_I = 0.4 + 2·I_0
  Eq.(9)  — 近/远尾流转换距离 x_0（Soesanto et al.）
  Eq.(10) — 近尾流半径修正项 δ_r
  Eq.(11) — 全域尾流半径 r_w
  Eq.(16) — 含近尾流修正的1D轮廓速度
  Eq.(17) — 速度修正项 δ_u = −0.1·ln(x/D) + 1.3
  Eq.(23) — 双余弦周期 k = π/[2(r_w − r_α)]
  Eq.(25) — 双余弦幅值 A
  Eq.(26) — 3D速度场（分段双余弦公式）
"""

import numpy as np


# ──────────────────────────────────────────────────────────────────
#  辅助函数：构成 3D-DCE 模型的各子模块
# ──────────────────────────────────────────────────────────────────

def compute_Iw(x_D, Ct, I0):
    """
    尾流湍流强度 I_w（Eq. 6）

      I_w = (δ_I/2)·C_t^(δ_I/4)·I_0^(−δ_I/8)·(x/D)^(−δ_I·I_0^(1.1·I_0))

    参数：
        x_D : float  归一化下游距离 x/D（> 0）
        Ct  : float  推力系数
        I0  : float  环境湍流强度（0–1）
    返回：
        float  尾流湍流强度 I_w
    """
    dI  = 0.4 + 2.0 * I0                        # Eq.(7): δ_I
    exp = -dI * (I0 ** (1.1 * I0))              # (x/D) 上的指数
    Iw  = (dI / 2.0) * (Ct ** (dI / 4.0)) * (I0 ** (-dI / 8.0)) * (x_D ** exp)
    return float(max(Iw, 1e-6))


def compute_x0(D, Ct, I0):
    """
    近/远尾流转换距离 x_0（Eq. 9，Soesanto et al.）

      x_0 = (1 + √(1−C_t)) / [1.6971·(2.32·I_0 + 0.154·(1−√(1−C_t)))] · D

    参数：
        D   : float  风轮直径 (m)
        Ct  : float  推力系数
        I0  : float  环境湍流强度
    返回：
        float  转换距离 x_0 (m)
    """
    sq  = np.sqrt(max(0.0, 1.0 - Ct))
    num = (1.0 + sq) * D
    den = 1.6971 * (2.32 * I0 + 0.154 * (1.0 - sq))
    return num / den if den > 0.0 else 3.0 * D


def compute_delta_r(x, D, x0):
    """
    近尾流半径修正项 δ_r（Eq. 10）

      δ_r = max[−0.1·(log_{x_0/D}(x/D) − 1), 0]
           = max[−0.1·(ln(x/D)/ln(x_0/D) − 1), 0]

    在 x < x_0（近尾流）时为正，x ≥ x_0（远尾流）时为 0。

    返回：
        float  无量纲修正量（乘以 r_d 得到修正量，单位：m）
    """
    if x <= 0.0 or D <= 0.0:
        return 0.0
    x0_D = x0 / D
    if x0_D <= 1.0:
        return 0.0
    x_D = x / D
    if x_D <= 0.0:
        return 0.0
    log_ratio = np.log(x_D) / np.log(x0_D)   # log_{x_0/D}(x/D)
    return float(max(-0.1 * (log_ratio - 1.0), 0.0))


def compute_rw(x, D, Ct, I0):
    """
    全域（近/远）尾流半径（Eq. 11）

      r_w = 3·r_d·C_t^0.35·I_0^0.175·I_w^0.175·(x/D)^0.35 − r_d·δ_r

    参数：
        x  : float  下游距离 (m)
        D  : float  风轮直径 (m)
        Ct : float  推力系数
        I0 : float  上游风机处环境湍流强度
    返回：
        float  尾流半径 r_w (m)
    """
    rd  = D / 2.0
    x_D = max(x / D, 1e-3)

    Iw = compute_Iw(x_D, Ct, I0)     # Eq.(6)
    x0 = compute_x0(D, Ct, I0)       # Eq.(9)
    dr = compute_delta_r(x, D, x0)   # Eq.(10)

    rw_far = 3.0 * rd * (Ct ** 0.35) * (I0 ** 0.175) * (Iw ** 0.175) * (x_D ** 0.35)
    rw     = rw_far - rd * dr
    return float(max(rw, rd * 0.3))  # 物理下界：至少 0.3·r_d


# ──────────────────────────────────────────────────────────────────
#  主函数：3D-DCE 尾流速度场
# ──────────────────────────────────────────────────────────────────

def wake_model(u0, Ct, D, z_hub, r, z, a2, x, rw, I0):
    """
    3D-DCE 单机尾流速度场（Eqs. 16–17, 23–26）

    参数：
        u0   : float    上游风机轮毂风速 (m/s)
        Ct   : float    推力系数
        D    : float    风轮直径 (m)
        z_hub: float    轮毂高度 (m)
        r    : ndarray  各评估点到尾流中心线的径向距离 (m)
        z    : ndarray  各评估点高度 (m)，与 r 同形状
        a2   : float    风切变指数 α
        x    : float    下游距离 (m)
        rw   : float    尾流半径 (m)，由 compute_rw() 预计算
        I0   : float    上游风机处环境湍流强度

    返回：
        ndarray  尾流速度场 (m/s)，与 r 同形状
    """
    rd  = D / 2.0
    x_D = max(x / D, 1e-3)

    # ── Eq.(17): 速度修正项 δ_u = −0.1·ln(x/D) + 1.3  (且 ≥ 1) ──────
    delta_u = max(-0.1 * np.log(x_D) + 1.3, 1.0)

    # ── Eq.(16): 1D 尾流速度比  u_w/u_0 = (1/δ_u)·[½ + ½·(r_d/r_w)·√((r_w/r_d)²−2C_t)]
    ratio    = max((rw / rd) ** 2 - 2.0 * Ct, 0.0)
    uw_ratio = float(np.clip(
        (1.0 / delta_u) * (0.5 + 0.5 * (rd / rw) * np.sqrt(ratio)),
        0.0, 1.0
    ))

    # ── Eq.(18): 归一化速度亏损 Δu* = 1 − u_w/u_0 ────────────────────
    du_star = 1.0 - uw_ratio

    # ── 双余弦几何参数 ─────────────────────────────────────────────────
    # r_α = 0.6·r_d：单峰函数极值点半径，取自 Tian et al. [47]（经验常数）
    r_alpha = 0.6 * rd                        # r_α（Eq. 26 参数，来源：Tian et al. [47]）
    Delta_r = max(rw - r_alpha, rw * 0.01)   # Δr = r_w − r_α（形状参数）
    k       = np.pi / (2.0 * Delta_r)        # Eq.(23): k = π/(2·Δr)

    # ── Eq.(25): 幅值 A = (π·r_w)/(4·Δr)·Δu* ─────────────────────────
    A = max((np.pi * rw) / (4.0 * Delta_r) * du_star, 0.0)

    # ── Eq.(22): 风切变来流速度 u_0(z) = u_0·(z/z_h)^α ─────────────
    u0_z = u0 * (z / z_hub) ** a2

    # ── Eq.(26): 分段双余弦速度场 ─────────────────────────────────────
    #   外区（Δr−r_α ≤ r < r_w）：  u = u_0(z)·{1 − A·cos[k(r−r_α)]}
    #   内区（0 ≤ r < Δr−r_α）    ：  u = u_0(z)·{1 − A·cos[k(r−r_α)] − A·cos[k(r+r_α)]}
    boundary    = Delta_r - r_alpha           # = r_w − 2·r_α
    cos_r_minus = np.cos(k * (r - r_alpha))  # cos[k(r−r_α)]：两区共用

    if boundary <= 0.0:
        # r_w ≤ 2·r_α：仅外区（单余弦）
        u_wake = u0_z * (1.0 - A * cos_r_minus)
    else:
        inner      = r < boundary
        u_outer    = u0_z * (1.0 - A * cos_r_minus)
        cos_r_plus = np.cos(k * (r + r_alpha))             # cos[k(r+r_α)]
        u_inner    = u0_z * (1.0 - A * (cos_r_minus + cos_r_plus))
        u_wake     = np.where(inner, u_inner, u_outer)

    # 速度物理下界：非负且不超过自由来流
    return np.clip(u_wake, 0.0, u0_z)