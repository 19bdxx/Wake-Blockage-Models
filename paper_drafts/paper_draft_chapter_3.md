# 3. Methodology

## 3.1 Overall Modeling Framework

本文方法流程围绕“统一气象驱动—尾流/阻塞建模—运行状态约束—多口径功率构造—一致口径评价”展开。具体实现由 `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/run_five_experiments_维护缺失默认跳过版.py` 驱动：脚本首先读取气象输入时序（`valid_time`, `wind_speed`, `wind_direction`），加载风机布局与机型参数，构建 PyWake 风场模型；随后在每个时刻分别运行 `enable_blockage=True/False` 两种物理配置，并在同一流场解上派生多类等效入流风速与候选功率口径；最后按风机级结果聚合至 `station_power_*` 场站级宽表并输出。

与纯模型计算不同，本文在方法链路中显式引入维护状态约束：在考虑维护实验中，先由维护矩阵确定时刻可运行风机集合，再执行尾流计算与场站聚合，从而保证模型计算对象与实测统计对象具有可比性。评价阶段采用统一脚本对候选口径进行 `all_samples` 与 `not_curtailed` 两个样本域的分层评估，并提供 overall 与 monthly 两级排序结果用于后续控制变量比较。

## 3.2 Baseline Wake Model

基线模型定义为 wake-only 场景，即 `enable_blockage=False`。在实现层面，风场模型由 `pywake_integration/wind_farm_setup.py` 构建，核心对象为 `All2AllIterative`，其 wake deficit 组件为自定义 `ZiyanWakeDeficit`（文件：`pywake_integration/ziyan_deficit.py`）。该模块将原项目 3D-DCE 公式封装为 PyWake 接口，并在注释中明确复用了尾流湍流、近远尾流过渡、尾流半径与双余弦横向速度分布等公式（含 Eq.22 风切变修正）。

基线模型输入包括：风速/风向、风机坐标、轮径/轮毂高度、功率曲线与推力曲线。风机对象通过 `WindTurbines + PowerCtTabular` 构建，`power_unit='kW'`，并按 `turbine_data.csv` 动态封装不同机型曲线；站点对象使用 `UniformSite + PowerShear`，其中 `h_ref=100 m`、`alpha=config.wind_shear_exp`（默认 0.13）。多机尾流叠加默认采用 `SquaredSum`，湍流模型可配置为 `STF2005TurbulenceModel`，并通过 `TI_eff_ilk` 驱动 `ZiyanWakeDeficit` 的局地湍流输入。

当前代码未见显式 `deflection model` 参数注入 `All2AllIterative`，方法上可视为未单独配置偏航偏转子模型。

## 3.3 Blockage Effect Configuration

阻塞效应配置通过 `enable_blockage` 开关控制：

- `enable_blockage=False`：仅尾流（wake-only）；
- `enable_blockage=True`：尾流 + 阻塞（wake + blockage）。

在 `wind_farm_setup.py` 中，阻塞模型由 `_get_blockage_model` 选择，默认配置名为 `SelfSimilarity`，实际映射为 `SelfSimilarityDeficit2020(superpositionModel=LinearSum())`；代码也保留了 `Rathmann` 与 `VortexCylinder` 选项。需要强调的是，本文并未提出新的阻塞理论模型，而是在既有 PyWake 框架中切换阻塞项并构建可控对照。

控制变量原则体现在运行脚本中：同一 `valid_time`、同一气象输入、同一风机集合下，仅切换 `enable_blockage`，并保持其他配置不变。这样可将阻塞项影响与其他因素（维护状态、候选风速口径）分离。

## 3.4 Maintenance-State Correction in Wake Simulation

维护状态通过 `load_maintenance_matrix(...)` 与 `get_maintenance_flags_for_time(...)` 注入模型流程。维护矩阵支持 `时间/timestamp/valid_time` 时间列以及 `是否维护_#i` 或 `is_maintenance_#i` 风机列，映射后形成逐时刻布尔维护向量 `maintenance_flags`。

考虑维护实验中，核心处理在 `run_one_condition_with_maintenance(...)`：

1. 构建可运行集合
\[
A(t)=\{i\mid \text{maintenance\_flags}_i(t)=0\}
\]
2. 仅将 `A(t)` 中风机传入 PyWake；
3. 维护风机行保留在输出表中，但 `power_*_kW` 置零、风速相关列置空，并标记 `is_maintenance=1`；
4. 因维护机组不进入本时刻风场求解，它们同时不作为尾流/阻塞源。

不考虑维护实验中，不传 `--maintenance-matrix`，即默认全部风机可运行。对维护矩阵缺失时刻，脚本提供 `error/all_running/nearest/skip` 策略，默认 `skip`；因此考虑维护实验的有效时刻集合可能短于不考虑维护实验。

维护状态修正在方法论上属于运行状态一致性约束，而非尾流物理机制创新。

## 3.5 Equivalent Inflow Wind-Speed Definitions

本研究通过同一时刻同一流场的多风速口径映射，构造多组候选场站功率列（`station_power_*`）。在 `run_integration.py` 与 `run_five_experiments_维护缺失默认跳过版.py` 中，候选口径可归纳为四类：

### A. PyWake internal power

- 示例列：`station_power_pywake_internal_kW`
- 含义：直接使用 `sim_res.Power`（内部有效风速 + 内部曲线计算链）得到功率。

### B. Native effective wind speed + unified curve

- 示例列：`station_power_from_ws_eff_pywake_native_kW`
- 含义：取 `sim_res.WS_eff`，再通过项目 `turbine_model.py` 功率曲线重算功率。
- 作用：在风速定义固定时，尽量分离“功率曲线求值器实现差异”的影响。

### C. Upstream point-speed definitions

- 示例列：`station_power_from_upstream_1m_kW` ... `station_power_from_upstream_400m_kW`
- 距离集合（由输出列可确认）：`[1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 180, 200, 250, 300, 350, 400]` m。
- 含义：在机组上游固定距离单点取风速，经统一功率曲线求得功率。

### D. Rotor-disc upstream mean definitions

- 示例列：`station_power_from_rotor_disc_upstream1m_mean_kW` ... `station_power_from_rotor_disc_upstream160m_mean_kW`
- 距离集合：`[1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160]` m。
- 含义：在转子圆盘区域布点并取面积平均风速，再经统一功率曲线求功率。

对应实现位于 `probe_points.py` 与 `self_blockage_ws.py`。其中转子平均方案通过圆盘采样点的 `flow_map` 求值形成更接近扫掠面积能量输入的等效入流定义；单点上游风速则更强调局部位置代表性。

## 3.6 Station Power Calculation

风机级输出构建后，场站级聚合由 `_build_station_rows(...)` 完成。对每个时刻、每个候选功率口径，场站功率采用求和：
\[
P_{station}^{(k)}(t)=\sum_{i\in A(t)} P_i^{(k)}(t)
\]
其中 `k` 表示候选口径，`A(t)` 为时刻可运行集合。考虑维护实验中，维护风机已在风机级层面置零并标记，因此其对场站和贡献为 0。

文件输出层面，`five_experiments_output_* / all_experiments_station_power_timeseries.csv` 中候选列单位为 `_kW`。评价脚本实际读取的是 `尾流预测与全站实测对比/all_experiments_station_power_timeseries-*.csv`（`_MW` 口径），该文件由 `尾流预测与全站实测对比/#2kw转换为mw.py` 从 `_kW` 列批量转换得到。因此方法章节需明确：模型主输出为 kW，评价前执行统一单位转换为 MW。

## 3.7 Experimental Design

本文数值实验采用“维护状态 × 阻塞开关 × 候选风速口径”的三维组合：

1. **Without maintenance**：不传 `--maintenance-matrix`；
2. **With maintenance**：传 `--maintenance-matrix JMZSFD维护记录/jmzsfd_maintenance_matrix.csv`；

每组内部均运行：
- `enable_blockage=False`（wake-only）
- `enable_blockage=True`（wake+blockage）

且在每个阻塞配置下同时输出 40 个 `station_power_*_kW` 候选功率定义。由此形成可用于后续多层控制变量比较的实验矩阵，而不依赖单一“最优口径”。

在实现上，`run_five_experiments_维护缺失默认跳过版.py` 每个时刻仅执行两次流场求解（对应 blockage on/off），其余候选功率均由同一次流场结果派生，减少了“不同口径来自不同流场解”的方法偏差。

## 3.8 Evaluation Metrics

评价脚本 `evaluate_station_power_accuracy_multi_station_monthly_combined.py` 以
- 实测：`P_{obs}(t)`（`MZS_FAN_ACTIVE_POWER_SUM`）
- 预测：`P_{pred}(t)`（候选 `station_power_*_MW`）
为基础，定义误差 `e(t)=P_{pred}(t)-P_{obs}(t)`，并计算：

\[
\text{MAE}=\mathrm{mean}(|e|),\quad
\text{RMSE}=\sqrt{\mathrm{mean}(e^2)},\quad
\text{Bias}=\mathrm{mean}(e)
\]
\[
\text{nMAE}=\frac{\text{MAE}}{P_{norm}},\quad
\text{nRMSE}=\frac{\text{RMSE}}{P_{norm}},\quad
R^2=1-\frac{\sum(P_{obs}-P_{pred})^2}{\sum(P_{obs}-\overline{P_{obs}})^2}
\]
并计算 `Corr`（皮尔逊相关系数）。

当前脚本中 `P_norm` 并非固定额定容量，而是 `actual_col` 的 95 分位值（`capacity_mw = percentile95(P_obs)`）；同时脚本还定义了限电判定 `LIMIT_POWER < RATED_LIMIT_POWER * 0.95`（当前 `MZS` 为 300.0），并输出 `all_samples` 与 `not_curtailed` 两个样本域的 overall/monthly 排名。

TODO: 代码当前未实现 median absolute error、p90 absolute error 与 energy error 指标，若论文方法需要，应在评价脚本中补充并统一定义。

## 3.9 Controlled Comparison Strategy

为避免“自由选最优”导致的比较偏差，后续比较需在统一键下做配对。可复用的主键维度包括：`valid_time`、`station`、`scope_name`、`period_type/month`、`enable_blockage`、`candidate_power_col`。

### 3.9.1 Maintenance comparison

目的：识别维护状态修正对验证结果的影响。比较时固定 `enable_blockage`、`candidate_power_col`、`scope_name`、`period_type/month` 与共同时间集合，仅改变实验组（with vs without maintenance）。

### 3.9.2 Blockage comparison

目的：识别阻塞项对 baseline wake 的影响。比较时固定实验组（是否维护）、`candidate_power_col`、`scope_name`、`period_type/month`，仅改变 `enable_blockage=False/True`。

### 3.9.3 Candidate inflow-definition comparison

目的：识别哪类等效入流定义更适合功率曲线映射。比较时固定实验组、`enable_blockage`、`scope_name`、`period_type/month`，仅改变 `candidate_power_col`。

需要强调：不能将“各自最优 ranking”的横向对比直接解释为维护或阻塞的净效应，必须采用同口径、同样本、同时间集合的配对比较。

## 3.10 Robustness Assessment of Candidate Wind-Speed Definitions

当前代码已提供 overall 与月度 (`period_type=month`) 排名基础，但“稳健性评分”尚未固化为独立脚本。基于现有输出，方法上可定义以下跨月稳健性统计：

- `monthly_nrmse_mean`
- `monthly_nrmse_std`
- `monthly_nrmse_max`
- `monthly_rank_mean`
- `monthly_rank_std`
- `top1_month_count`, `top3_month_count`, `top5_month_count`
- `worst_month_nrmse`

其目标是筛选跨月份可复用的候选口径，而非每月切换“当月最优”口径。可选的综合分数形式为：
\[
\text{stability\_score}=\text{monthly\_nrmse\_mean}+\alpha\cdot\text{monthly\_nrmse\_std}+\beta\cdot\text{monthly\_nrmse\_max}
\]

TODO: 当前仓库尚未给出固定的 `stability_score` 权重 `\alpha,\beta` 与最终筛选准则，需要在后续分析脚本中明确。

# Information Still Needed

- TODO: 明确论文正文中采用的阻塞模型固定配置（当前代码支持 `SelfSimilarityDeficit2020/Rathmann/VortexCylinder`）。
- TODO: 明确是否需要在论文主方法中展开 `ZiyanWakeDeficit` 公式推导细节（当前代码注释给出 Eq 编号，但论文版公式排版尚未整理）。
- TODO: 明确是否需要把 `deflection model` 显式声明为“未使用”或补充可比配置。
- TODO: 明确空气密度、功率曲线外推边界与插值策略在论文中的统一表述（`PowerCtTabular` 与 `turbine_model.py` 重算链并存）。
- TODO: 统一 `nMAE/nRMSE` 的归一化口径（95 分位 vs 额定容量）并给出最终准则。
- TODO: 在评价脚本中补充并固化 median absolute error、p90 absolute error、energy error（若论文需要这些指标）。
- TODO: 明确稳健性评分权重与阈值，形成可复现的候选口径筛选规则。

# Suggested Figures and Tables

## Suggested Figures

- Figure 4. Wake-blockage 场站功率模拟与评价总体流程图。
- Figure 5. 基线尾流与阻塞开启配置示意（`enable_blockage` 控制）。
- Figure 6. 等效入流风速口径示意：上游点风速与转子圆盘上游平均风速。
- Figure 7. 维护、阻塞与候选口径三类控制变量比较框架图。

## Suggested Tables

- Table 5. 候选 `station_power_*` 定义与等效入流物理含义对应表。
- Table 6. 实验矩阵（with/without maintenance × blockage off/on × candidate definitions）。
- Table 7. 评价指标与归一化定义（MAE, RMSE, Bias, nMAE, nRMSE, R², Corr）。
- Table 8. 控制变量比较所用主键与允许变化因子。
- Table 9. 候选口径跨月稳健性统计指标定义。
