# ziyan_deficit.py
"""
ZiyanWakeDeficit — 将原始 3D-DCE（三维双余弦卷吸）尾流模型封装为
PyWake 自定义 WakeDeficitModel。

物理来源
--------
本模块 **仅复用** 原始项目 `wake_model.py` 中的单机尾流核心公式（Bao et al.）：

  输入：上游风机有效风速 u0、推力系数 Ct、风轮直径 D、湍流强度 I0
        评估点到尾流轴的 3D 径向距离 r（cw_ijlk）、下游距离 x（dw_ijlk）
        评估点高度 z（z_ijlk）、源风机轮毂高度 zh（h_ilk）
  输出：评估点处的速度亏损（m/s）

复用的公式（原始 wake_model.py Eq. 编号）：
  Eq.6   : 尾流湍流强度 Iw
  Eq.9   : 近/远尾流转换距离 x0
  Eq.10  : 近尾流半径修正 δr
  Eq.11  : 全域尾流半径 rw
  Eq.16  : 1D 尾流速度比 uw/u0
  Eq.17  : 速度修正项 δu
  Eq.22  : 风切变来流 u0(z) = u0·(z/zh)^α
  Eq.23  : 双余弦周期 k
  Eq.25  : 双余弦幅值 A
  Eq.26  : 3D 分段双余弦速度场

**不包含** 的原始项目逻辑（由 PyWake 框架接管）：
  - 全场顺风排序            → All2AllIterative 接管
  - 转子面积加权积分         → rotorAvgModel（EqGridRotorAvg）接管
  - 多机 RSS 叠加            → superpositionModel（SquaredSum）接管
  - 功率曲线查表             → WindTurbines + PowerCtTabular 接管
  - 阻挡/诱导（上游减速）    → PyWake blockage_deficitModel 接管

I0 / 局地湍流强度处理策略（重要差异说明）
-----------------------------------------
原始 power_single.py 使用 Frandsen 公式对每台风机逐台更新局地湍流强度 I0[i]，
这个动态更新的 I0 影响 rw（尾流半径）和 Iw（尾流湍流强度）。

当前 PyWake 集成版本通过以下策略近似复现这一逻辑：

  ✅ 启用 STF2005TurbulenceModel（IEC61400-1:2005 Frandsen 模型）
     → PyWake 在每次迭代后更新 TI_eff_ilk[i]（每台风机的有效湍流强度）

  ✅ use_effective_ti=True
     → calc_deficit 使用 TI_eff_ilk（逐台更新值）而非全局 TI_ilk

  效果：turbine i 的 I0 = TI_eff_ilk[i]，随机位和受尾流影响程度动态变化，
        接近（但不完全等同于）原始 power_single.py 的 I0 更新方式。

  ⚠️ 与原始模型的残余差异：
     - Frandsen 公式实现版本不同（IEC2005 vs 原始自定义版本）
     - 原始模型先排序后更新，PyWake 迭代全场求解
     - 两种方法在收敛结果上接近，但中间状态可能不同

args4deficit（接口契约，显式定义）
----------------------------------
本类通过 @property 覆盖父类的 args4deficit，显式返回完整参数集合。
这不是注释，而是 PyWake 运行时用来决定向 calc_deficit 传哪些参数的契约。

完整参数列表：
  D_src_il   (n_src, n_dirs)
  dw_ijlk    (n_src, n_tgt, n_dirs, n_speeds)   下游距离
  cw_ijlk    (n_src, n_tgt, n_dirs, n_speeds)   3D 径向距离
  ct_ilk     (n_src, n_dirs, n_speeds)            推力系数
  z_ijlk     (n_src, n_tgt, n_dirs, n_speeds)   目标点高度（Eq.22）
  h_ilk      (n_src, n_dirs, n_speeds)            源轮毂高度（Eq.22）
  WS_eff_ilk (n_src, n_dirs, n_speeds)            源有效风速（use_effective_ws=True）
  TI_eff_ilk (n_src, n_dirs, n_speeds)            源有效湍流强度（use_effective_ti=True）
  D_dst_ijl  (n_src, n_tgt, n_dirs)               目标风机直径（EqGridRotorAvg 需要）
"""

import numpy as np
from py_wake.deficit_models.deficit_model import WakeDeficitModel
from py_wake.utils.model_utils import RotorAvgAndGroundModelContainer

_na = np.newaxis


# ──────────────────────────────────────────────────────────────────────────────
#  向量化 3D-DCE 子函数（来自 wake_model.py，重写为 NumPy 广播形式）
# ──────────────────────────────────────────────────────────────────────────────

def _iw_vec(x_D, Ct, I0):
    """
    尾流湍流强度 Iw（Eq.6）

        dI = 0.4 + 2·I0
        Iw = (dI/2)·Ct^(dI/4)·I0^(−dI/8)·(x/D)^(−dI·I0^(1.1·I0))

    I0 来源：
    - use_effective_ti=True（默认）→ TI_eff_ilk，即 STF2005 更新后的逐台值
    - use_effective_ti=False → 全局固定 TI_ilk
    """
    dI  = 0.4 + 2.0 * I0
    exp = -dI * np.power(np.clip(I0, 1e-6, 1.0), 1.1 * I0)
    Iw  = (dI / 2.0) \
          * np.power(np.clip(Ct, 1e-9, 0.9999), dI / 4.0) \
          * np.power(np.clip(I0, 1e-6, 1.0), -dI / 8.0) \
          * np.power(np.maximum(x_D, 1e-6), exp)
    return np.maximum(Iw, 1e-6)


def _x0_vec(D, Ct, I0):
    """
    近/远尾流转换距离 x0（Eq.9）

        x0 = (1 + √(1−Ct)) / (1.6971·(2.32·I0 + 0.154·(1−√(1−Ct)))) · D
    """
    sq  = np.sqrt(np.maximum(1.0 - Ct, 0.0))
    den = 1.6971 * (2.32 * I0 + 0.154 * (1.0 - sq))
    return (1.0 + sq) * D / np.maximum(den, 1e-10)


def _rw_vec(x, D, Ct, I0):
    """
    全域（近/远）尾流半径（Eq.11）

        rw = 3·rd·Ct^0.35·I0^0.175·Iw^0.175·(x/D)^0.35 − rd·δr

    注：I0 通过 TI_eff_ilk 传入，因此 rw 会随上游尾流累积而扩大，
        近似复现原始模型中 I0 更新对 rw 的影响。

    delta_r（Eq.10）修正项：
        当 x0_D ≤ 1.0（高 Ct + 高 TI 条件，例如 Ct≥0.90, I0≥0.29）时，
        原始 compute_rw() 直接返回 dr=0。PyWake 矢量化版本用
        log_ratio 回退值 1.0（而非 0.0）来确保 dr=0，保持与原始一致。
    """
    rd  = D / 2.0
    x_D = np.maximum(x / np.maximum(D, 1e-3), 1e-3)

    Iw = _iw_vec(x_D, Ct, I0)
    x0 = _x0_vec(D, Ct, I0)

    x0_D      = x0 / np.maximum(D, 1e-3)
    log_x0_D  = np.log(np.maximum(x0_D, 1.0 + 1e-10))   # prevent division by zero in log_ratio
    log_x_D   = np.log(np.maximum(x_D, 1e-10))
    # IMPORTANT: when x0_D <= 1.0, original compute_delta_r returns 0.
    # Use fallback 1.0 (not 0.0) so that dr = max(-0.1*(1-1), 0) = 0.
    log_ratio = np.where(x0_D > 1.0, log_x_D / log_x0_D, 1.0)
    dr        = np.maximum(-0.1 * (log_ratio - 1.0), 0.0)

    rw_far = 3.0 * rd \
             * np.power(np.clip(Ct, 1e-9, 0.9999), 0.35) \
             * np.power(np.clip(I0, 1e-6, 1.0), 0.175) \
             * np.power(Iw, 0.175) \
             * np.power(x_D, 0.35)
    return np.maximum(rw_far - rd * dr, rd * 0.3)


def _wake_deficit_3d(u0_ref, Ct, D, r, x, rw):
    """
    3D-DCE 速度亏损（Eqs.16–17, 23–26）。

    参数（全部 ndarray，可广播）
    ----------------------------
    u0_ref : 评估点处的参考风速（已含 Eq.22 风切变）(m/s)
    Ct     : 推力系数
    D      : 风轮直径 (m)
    r      : 评估点到尾流轴线的 3D 径向距离 (m)
    x      : 下游距离 (m)
    rw     : 尾流半径 (m)

    返回：速度亏损 Δu = u0_ref − u_wake (m/s)，尾流锥外为 0
    """
    rd  = D / 2.0
    x_D = np.maximum(x / np.maximum(D, 1e-3), 1e-3)

    # Eq.(17): δu = max(−0.1·ln(x/D) + 1.3, 1)
    delta_u = np.maximum(-0.1 * np.log(x_D) + 1.3, 1.0)

    # Eq.(16): 1D 速度比 uw/u0
    ratio    = np.maximum((rw / np.maximum(rd, 1e-3)) ** 2 - 2.0 * Ct, 0.0)
    uw_ratio = np.clip(
        (1.0 / delta_u) * (0.5 + 0.5 * (rd / np.maximum(rw, 1e-3)) * np.sqrt(ratio)),
        0.0, 1.0
    )
    du_star = 1.0 - uw_ratio

    # 双余弦几何参数
    r_alpha = 0.6 * rd
    Delta_r = np.maximum(rw - r_alpha, rw * 0.01)
    k       = np.pi / (2.0 * Delta_r)

    # Eq.(25): 幅值 A = (π·rw)/(4·Δr) · Δu*
    A = np.maximum((np.pi * rw) / (4.0 * Delta_r) * du_star, 0.0)

    # Eq.(26): 分段双余弦速度场
    boundary    = Delta_r - r_alpha
    cos_r_minus = np.cos(k * (r - r_alpha))
    cos_r_plus  = np.cos(k * (r + r_alpha))

    u_outer = u0_ref * (1.0 - A * cos_r_minus)
    u_inner = u0_ref * (1.0 - A * (cos_r_minus + cos_r_plus))
    u_wake  = np.where((boundary > 0) & (r < boundary), u_inner, u_outer)
    u_wake  = np.clip(u_wake, 0.0, u0_ref)

    return np.maximum(u0_ref - u_wake, 0.0)


# ──────────────────────────────────────────────────────────────────────────────
#  自定义 PyWake WakeDeficitModel
# ──────────────────────────────────────────────────────────────────────────────

class ZiyanWakeDeficit(WakeDeficitModel):
    """
    基于 ZIYAN 3D-DCE 公式的自定义 PyWake WakeDeficitModel。

    接口契约（args4deficit）
    ------------------------
    本类通过 @property 显式覆盖父类 args4deficit，明确声明 PyWake 在调用
    calc_deficit 时需要传入的所有参数。这不是注释，而是 PyWake 运行时行为
    的接口契约，确保 All2AllIterative + rotorAvgModel 包装层正确传参。

    I0 / 湍流强度处理
    -----------------
    当 use_effective_ti=True 且 All2AllIterative 配合 STF2005TurbulenceModel 时：
      - TI_eff_ilk[i] = 经 Frandsen (IEC2005) 叠加后的逐台有效湍流强度
      - 这个 TI_eff_ilk 随上游尾流叠加而逐台增大
      - calc_deficit 用 TI_eff_ilk 作为 I0，影响 rw 和 Iw（Eqs.6, 11）
      效果近似复现原始 power_single.py 中逐台更新 I0 的物理逻辑

    已实现的物理特性
    ----------------
    1. 3D-DCE 尾流半径（近/远尾流转换，Eqs.9–11）
    2. 双余弦横向速度剖面（Eqs.23–26）
    3. Eq.22 风切变修正：u0_ref = WS_eff · (z_ijlk / h_ilk)^α
    4. 转子面积加权（EqGridRotorAvg 在转子圆面多点采样）
    5. 局地 TI 演化（STF2005 + TI_eff_ilk，近似 Frandsen 逐台更新）

    与原始模型的已知残余差异
    --------------------------
    - STF2005 Frandsen 公式版本 ≠ 原始自定义 Frandsen 版本
    - 转子积分：EqGridRotorAvg(n) 笛卡尔网格 ≠ 原始 8×20 极坐标网格
    - 全场求解：PyWake 迭代 ≠ 原始顺风排序

    参数
    ----
    alpha : float
        风切变指数 α（默认 0.13）
    use_effective_ws : bool
        True（默认）→ WS_eff_ilk（迭代有效风速）
        False        → WS_ilk（自由来流）
    use_effective_ti : bool
        True（默认）→ TI_eff_ilk（逐台更新，配合 STF2005TurbulenceModel）
        False        → TI_ilk（全局固定值）
    rotorAvgModel :
        转子平均模型（由 wind_farm_setup 传入 EqGridRotorAvg(n)）
    """

    def __init__(
        self,
        alpha: float = 0.13,
        use_effective_ws: bool = True,
        use_effective_ti: bool = True,
        rotorAvgModel=None,
    ):
        WakeDeficitModel.__init__(
            self,
            use_effective_ws=use_effective_ws,
            use_effective_ti=use_effective_ti,
            rotorAvgModel=rotorAvgModel,
        )
        self.alpha = float(alpha)

    # ── 接口契约：显式 args4deficit（覆盖父类属性）──────────────────────────

    @property
    def args4deficit(self):
        """
        ZiyanWakeDeficit 需要的完整参数集合（PyWake 接口契约，显式定义）。

        这个 property 覆盖了父类 DeficitModel.args4deficit，
        明确列出所有 calc_deficit 和 wake_radius 实际使用的参数。
        PyWake 的 All2AllIterative 在运行时通过此属性决定传哪些参数，
        因此这里的声明必须完整且准确。

        参数说明
        --------
        D_src_il    : 源风机直径 (n_src, n_dirs)
        dw_ijlk     : 下游距离 (n_src, n_tgt, n_dirs, n_speeds)
        cw_ijlk     : 3D 径向距离 sqrt(hcw²+dh²) (n_src, n_tgt, n_dirs, n_speeds)
        ct_ilk      : 推力系数 (n_src, n_dirs, n_speeds)
        z_ijlk      : 目标点高度，Eq.22 风切变 (n_src, n_tgt, n_dirs, n_speeds)
        h_ilk       : 源轮毂高度，Eq.22 风切变 (n_src, n_dirs, n_speeds)
        WS_eff_ilk  : 源有效风速（use_effective_ws=True 时）
        TI_eff_ilk  : 源有效湍流强度（use_effective_ti=True 时，含 STF2005 更新值）
        D_dst_ijl   : 目标直径（EqGridRotorAvg 转子积分需要）
        """
        args = {
            'D_src_il',       # 源风机直径
            'dw_ijlk',        # 下游距离
            'cw_ijlk',        # 3D 径向距离
            'ct_ilk',         # 推力系数
            'z_ijlk',         # 目标点高度（Eq.22 风切变修正）
            'h_ilk',          # 源轮毂高度（Eq.22 风切变修正）
            self.WS_key,      # 'WS_eff_ilk' 或 'WS_ilk'
            self.TI_key,      # 'TI_eff_ilk' 或 'TI_ilk'
        }
        # rotorAvgModel（EqGridRotorAvg）额外需要 D_dst_ijl 来布置转子采样点
        if self.rotorAvgModel is not None:
            args |= self.rotorAvgModel.args4model   # 通常为 {'D_dst_ijl'}
        return args

    # ── 主计算接口 ────────────────────────────────────────────────────────────

    def calc_deficit(
        self,
        D_src_il,   # (n_src, n_dirs)
        dw_ijlk,    # (n_src, n_tgt, n_dirs, n_speeds[, n_pts])  下游距离
        cw_ijlk,    # (n_src, n_tgt, n_dirs, n_speeds[, n_pts])  3D 径向距离
        ct_ilk,     # (n_src, n_dirs, n_speeds)
        z_ijlk,     # (n_src, n_tgt, n_dirs, n_speeds[, n_pts])  目标点高度
        h_ilk,      # (n_src, n_dirs, n_speeds)                   源轮毂高度
        **kwargs,
    ):
        """
        计算 3D-DCE 速度亏损（含 Eq.22 风切变修正）。

        I0 取值：
          - use_effective_ti=True（默认）: TI_eff_ilk[i] = Frandsen 更新后的逐台 TI
          - use_effective_ti=False        : TI_ilk（全局固定值）

        风切变修正（Eq.22）：
          u0_ref = WS_eff_ilk · (z_ijlk / h_ilk)^α
          z_ijlk 由 EqGridRotorAvg 在转子圆面各采样点上赋值不同高度，
          使转子面积加权与风切变完全耦合。

        返回
        ----
        deficit_ijlk[...] : ndarray  速度亏损 (m/s)，尾流锥外为 0
        """
        WS_ref = kwargs.get(self.WS_key)
        TI_ref = kwargs.get(self.TI_key)

        D  = np.asarray(D_src_il, dtype=float)[:, _na, :, _na]
        Ct = np.asarray(ct_ilk,   dtype=float)[:, _na]
        I0 = np.maximum(np.asarray(TI_ref, dtype=float)[:, _na], 1e-3)
        u0 = np.asarray(WS_ref,   dtype=float)[:, _na]

        dw = np.asarray(dw_ijlk, dtype=float)
        r  = np.abs(np.asarray(cw_ijlk, dtype=float))

        # ── Eq.22 风切变修正 ─────────────────────────────────────────────────
        z   = np.asarray(z_ijlk, dtype=float)
        zh  = np.maximum(np.asarray(h_ilk, dtype=float)[:, _na], 0.1)
        z_s = np.maximum(z, 0.1)
        u0_ref = u0 * (z_s / zh) ** self.alpha

        # ── 仅在下游（dw > 0）且在尾流锥内计算 ─────────────────────────────
        dw_pos  = np.maximum(dw, 1e-3)
        in_wake = dw > 0.0

        rw      = _rw_vec(dw_pos, D, Ct, I0)
        in_wake = in_wake & (r <= rw)

        deficit = _wake_deficit_3d(u0_ref, Ct, D, r, dw_pos, rw)
        return np.where(in_wake, deficit, 0.0)

    def wake_radius(self, D_src_il, dw_ijlk, ct_ilk, **kwargs):
        """
        3D-DCE 尾流半径（Eq.11）。

        使用 TI_key（TI_eff_ilk 或 TI_ilk）作为 I0，
        与 calc_deficit 中的 rw 保持一致。
        """
        TI_ref = kwargs.get(self.TI_key)
        D  = np.asarray(D_src_il, dtype=float)[:, _na, :, _na]
        Ct = np.asarray(ct_ilk,   dtype=float)[:, _na]
        I0 = np.maximum(np.asarray(TI_ref, dtype=float)[:, _na], 1e-3)
        dw = np.maximum(np.asarray(dw_ijlk, dtype=float), 1e-3)
        return _rw_vec(dw, D, Ct, I0)
