# Chapter 4 Analysis Report

## 1. Executive Summary
- 共同时间交集共有 19586 个 15 min 时刻，但真正进入误差计算的有效样本数为 `all_samples=18781`、`not_curtailed=18467`；因此第 4 章必须明确区分“共同时刻数”和“有效评价样本数”。
- 维护状态修正在固定候选列与固定 blockage 设置后，使 `not_curtailed` overall 的 80/80 个组合都实现了 `nRMSE` 改善，说明它首先是一项评价口径对齐步骤，而不是新的物理建模创新。
- blockage 在 `with_maintenance + not_curtailed` 主线下对 35/40 个组合降低了 `nRMSE`，但 0–20 m 距离带与部分月份会恶化，因此只能写成条件性收益。
- strict overall 最优候选是 `station_power_from_rotor_disc_upstream70m_mean_kW + blockage_on`（`nRMSE=0.1553`），而稳健性排序第一是 `station_power_from_upstream_60m_kW + blockage_on`（`nRMSE=0.1586`，`stability_score=0.4294`）；两者不完全一致。
- 月度第一名在 2024 年 1–7 月没有任何重复候选，说明不能逐月自由切换“最优模型”来代表整体模型能力。
- 风速分箱和风向扇区结果都显示最优候选随工况改变；这些发现适合写入 Results 章节，但其物理机制应留待 Discussion。
- 三个 24 h 典型案例支持统计结论：维护修正表现为持续性整体改善，blockage 与候选替换则表现为“窗口收益为正但局部时刻未必同步改善”。

**适合写入论文主结论的发现：**
- 共同时间交集和统一评价口径是横向比较的前提。
- 维护状态修正会系统性影响验证结果，应定位为运行状态一致性处理。
- blockage 的收益具有候选与工况依赖性。
- 候选风速定义存在明显距离依赖，推荐应以跨月份稳健性为主。

**更适合在 Discussion 中进一步解释的发现：**
- 为什么 2 月维护修正收益远高于 4–6 月。
- 为什么 blockage 在 0–20 m 距离带和 1–3 月份更容易恶化。
- 为什么风向扇区最优距离差异较大，以及其与阵列几何的对应关系。

## 2. Data Coverage and Sample Construction

### 2.1 Common time range
- **分析对象：** 维护版输出、不维护版输出、实测数据和预报输入的时间覆盖。
- **控制变量：** 统一使用 `valid_time` / `timestamp` 对齐后的共同时间交集。
- **样本范围：** `2024-01-01 08:00:00` 至 `2024-07-29 10:15:00`。
- **样本数：** 共同时间交集为 19586 个 15 min 时刻；考虑维护实验相对完整预报时段额外跳过 830 个时刻。
- **对应 CSV：** `comparison_results/time_coverage_summary.csv`
- **对应图表：** `comparison_results/figures/01_time_coverage.png`
- **直接结论：** 横向比较必须基于共同时间交集，否则时间覆盖差异会先于模型差异影响误差指标。

**Paper-ready statement:** 维护版与不维护版实验的可用时段并不完全一致，因此本文所有横向比较均限制在共同时间交集上进行。

### 2.2 all_samples and not_curtailed samples
- **分析对象：** 共同时间交集进入误差评价前后的样本筛选。
- **控制变量：** 统一使用 `actual_power_mw` 作为误差目标，统一采用 `is_curtailed` 标记。
- **样本链条：**
  - 19586 个共同时刻；
  - 其中 805 个时刻 `actual_power_mw` 缺失，不能进入误差计算；
  - `all_samples` 有效评价样本数为 18781；
  - 共同时刻中另有 314 个时刻被标记为 `is_curtailed=True`；
  - `not_curtailed` 去除限电并经过有限值筛选后得到 18467 个有效样本。
- **证据来源：** `comparison_results/merged_common_samples.csv` 与两个 overall ranking CSV 的 `n` 列交叉核对。
- **直接结论：** `not_curtailed` 是第 4 章主评价样本，因为它同时排除了限电影响与缺测时刻对误差的污染。

**Paper-ready statement:** 本文以 `not_curtailed` 样本作为主评价域，用于避免限电影响与功率缺测共同干扰模型误差判断。

### 2.3 Unit consistency
- **分析对象：** 候选功率列单位与分析单位。
- **控制变量：** 所有 `station_power_*_kW` 候选统一转换为 MW 后再参与误差计算。
- **证据来源：** `comparison_results/candidate_columns_detected.csv`、`comparison_results/merged_common_samples.csv`
- **直接结论：** 本章所有功率误差指标均在 MW 单位下计算，不应直接将原始 `*_kW` 数值写入正文。

**Paper-ready statement:** 为保证误差指标口径一致，所有候选功率列均由原始 kW 单位转换为 MW 后再参与评价。

### 2.4 Main measured target
- **分析对象：** 误差评价所对应的实测目标。
- **控制变量：** 误差计算使用 `MZS_FAN_ACTIVE_POWER_SUM` 对应的 `actual_power_mw`，限电识别使用 `MZS_LIMIT_POWER`，归一化容量使用共同样本 `actual_power_mw` 的 95 分位值。
- **关键数值：** `P_norm=288.963 MW`；全量实测文件 `actual_power_p95_mw=292.255686 MW`，说明共同样本下的归一化容量略低于全量观测。
- **对应 CSV：** `comparison_results/measured_power_quality_check.csv`、`comparison_results/merged_common_samples.csv`
- **直接结论：** 第 4 章使用的是共同样本下的归一化口径，而不是全量观测期的 95 分位值。

**Paper-ready statement:** 为保持比较口径一致，本文使用共同样本下实测功率的 95 分位值作为归一化容量，而非全量实测时段的统计量。

### Figure note: `comparison_results/figures/01_time_coverage.png`
- **Figure path:** `comparison_results/figures/01_time_coverage.png`
- **Data source CSV:** `comparison_results/time_coverage_summary.csv`
- **What it shows:** 四类数据源与共同交集的起止时间段。
- **Main observation:** 维护版输出结束于 2024-07-29 10:15，而不维护版与预报输入延伸到 2024-07-31 23:45。
- **How it supports the Results chapter:** 直接支撑“必须使用共同时间交集”的结论。
- **Potential caveat:** 该图只显示时间覆盖，不显示其中有多少时刻因实测缺测或限电而退出误差计算。

## 3. Single-Experiment Ranking

### 3.1 Key rankings
- **分析对象：** 各实验内部的 overall/monthly 排名。
- **控制变量：** 固定实验组，仅比较候选定义与 blockage 设置。
- **样本范围：** `not_curtailed` overall 每个组合 18467 个样本；monthly 结果覆盖 2024 年 1–7 月。
- **关键结果：**
  - `with_maintenance` overall 第一名：`station_power_from_rotor_disc_upstream70m_mean_kW + blockage_on`，`nRMSE=0.1553069`。
  - `without_maintenance` overall 第一名：`station_power_from_rotor_disc_upstream50m_mean_kW + blockage_on`，`nRMSE=0.1702597`。

### 3.2 Why ranking alone is insufficient
- 两个实验的 overall 第一名并不相同，说明“最佳组合”本身已经混入了维护修正与 blockage 设置差异。
- 2024 年 1–7 月的月度第一名分别为 120m rotor-disc、120m point、100m rotor-disc、90m rotor-disc、70m point、60m rotor-disc、50m point，说明月度第一名没有重复。
- 因此，ranking 可以用来描述实验内部排序，但不能代替 controlled comparison 来回答“维护修正是否有效”或“blockage 是否有效”。

### 3.3 Paper-ready statement
**Paper-ready statement:** 单实验 ranking 仅能反映每组实验内部的相对优劣，而不能单独用于判断维护修正或 blockage 的净效果，因为“各自最优”组合同时改变了多个比较因素。

## 4. Maintenance-State Correction

### 4.1 Controlled variables
- **分析对象：** `without_maintenance` 与 `with_maintenance` 的差异。
- **控制变量：** 固定 `candidate_power_col`、固定 `enable_blockage`、固定 `scope_name`。
- **比较文件：**
  - `comparison_results/controlled_comparison/maintenance_controlled_overall.csv`
  - `comparison_results/controlled_comparison/maintenance_controlled_monthly.csv`
  - `comparison_results/controlled_comparison/maintenance_controlled_summary.csv`

### 4.2 Overall results
#### `not_curtailed` overall (80 combinations)
| Metric | Improved count | Improved ratio | Mean improvement (%) | Median improvement (%) | Min (%) | Max (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MAE | 80 | 100.0% | 14.14 | 15.63 | 3.09 | 16.07 |
| RMSE | 80 | 100.0% | 10.12 | 11.34 | 1.10 | 11.83 |
| nRMSE | 80 | 100.0% | 10.12 | 11.34 | 1.10 | 11.83 |
| abs_bias | 67 | 83.75% | -183.57 | 29.95 | -10060.36 | 96.47 |

- `nRMSE` 最佳改善组合：`station_power_from_ws_eff_pywake_native_kW + blockage_on`，改善 11.83%。
- `nRMSE` 最弱改善组合：`station_power_from_upstream_1m_kW + blockage_on`，改善 1.10%。
- `abs_bias` 的平均改善率不宜直接引用为主结论，因为当基准偏差极小时，百分比会被极度放大。

### 4.3 Monthly results
- `not_curtailed` monthly 共有 560 个组合月结果，`nRMSE` 改善占比为 93.21%。
- 按月份取 80 个组合的平均 `nRMSE` 改善：
  - 1 月：3.26%
  - 2 月：41.08%
  - 3 月：2.61%
  - 4 月：0.91%
  - 5 月：2.38%
  - 6 月：2.39%
  - 7 月：6.47%
- 改善方向在大多数月份保持为正，但收益大小明显波动，说明维护修正的影响与当月停机样本构成密切相关。

### 4.4 Relation with maintenance count
- `maintenance_controlled_summary.csv` 中的 overall `maintenance_count_vs_nRMSE_improvement_corr` 没有给出有限值，原因是 overall 聚合后的 `maintenance_count_mean` 在各组合之间几乎不变化，难以构成有意义的相关系数。
- 因此，维护数量关系更适合通过月度波动和案例窗口做描述性解释，而不宜在第 4 章写成正式相关性结论。
- This point should be further discussed in Chapter 5.

### 4.5 Paper-ready statement
**Paper-ready statement:** 在共同时间交集和非限电影响样本上，维护状态修正使相同候选定义与相同 blockage 设置下的 `nRMSE` 全部下降，说明运行状态一致性处理会系统性影响模型验证结果。

### 4.6 What should be discussed later
- 为什么 2 月收益特别高。
- 维护记录缺失、停机台数分布与误差改善之间的具体机理。
- 维护修正是否改变了不同风速/风向工况的样本组成。

### Figure note: `comparison_results/figures/02_maintenance_effect_by_month.png`
- **Figure path:** `comparison_results/figures/02_maintenance_effect_by_month.png`
- **Data source CSV:** `comparison_results/controlled_comparison/maintenance_controlled_monthly.csv`
- **What it shows:** `not_curtailed` 样本下，各月份 80 个受控组合的平均 `nRMSE` 改善率。
- **Main observation:** 2 月收益最高，4–6 月收益明显较弱。
- **How it supports the Results chapter:** 支撑“维护修正会系统性影响验证结果，但收益具有月份依赖性”。
- **Potential caveat:** 图中展示的是组合平均值，而不是逐组合分布，因此不能替代更细的机理分析。

## 5. Blockage Effect

### 5.1 Controlled variables
- **分析对象：** blockage off 与 blockage on 的差异。
- **控制变量：** 固定 `experiment_name`、固定 `candidate_power_col`、固定 `scope_name`。
- **主比较域：** `with_maintenance + not_curtailed`
- **比较文件：**
  - `comparison_results/controlled_comparison/blockage_controlled_overall.csv`
  - `comparison_results/controlled_comparison/blockage_controlled_monthly.csv`
  - `comparison_results/controlled_comparison/blockage_controlled_summary.csv`

### 5.2 Overall results
#### `with_maintenance + not_curtailed` overall (40 combinations)
| Metric | Improved count | Improved ratio | Mean improvement (%) | Median improvement (%) | Min (%) | Max (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MAE | 35 | 87.5% | 5.42 | 9.60 | -31.86 | 13.42 |
| RMSE | 35 | 87.5% | 3.43 | 6.64 | -27.21 | 9.78 |
| nRMSE | 35 | 87.5% | 3.43 | 6.64 | -27.21 | 9.78 |
| abs_bias | 35 | 87.5% | 40.63 | 53.35 | -88.86 | 98.79 |

- `nRMSE` 最佳改善候选：`station_power_from_upstream_80m_kW`，改善 9.78%。
- `nRMSE` 最差候选：`station_power_from_upstream_1m_kW`，恶化 27.21%。

### 5.3 Candidate-type dependence
- `rotor_disc_upstream_mean` 的平均 `nRMSE` 改善为 7.30%（14 个候选）。
- `upstream_point` 的平均 `nRMSE` 改善为 1.45%（24 个候选）。
- `WS_eff native` 与 `PyWake internal` 的平均改善仅约 0.06%。
- 距离带平均改善：
  - `0-20m`: -8.60%
  - `21-60m`: 5.51%
  - `61-100m`: 8.86%
  - `101-160m`: 7.10%
  - `160m+`: 3.07%
- 这说明 blockage 的收益主要集中在中等距离带，而非所有距离都受益。

### 5.4 Monthly / wind-speed / wind-direction dependence
- `with_maintenance + not_curtailed` 月均 `nRMSE` 改善在 1–3 月分别为 -4.44%、-4.34%、-2.37%，4 月转正到 0.84%，5–7 月分别升至 12.53%、8.94%、5.82%。
- 风速/风向分析并不是 blockage 的直接 controlled comparison，但 `candidate_performance_by_wind_speed_bin.csv` 和 `candidate_performance_by_wind_direction_bin.csv` 中最优组合的 blockage 设置会随工况改变：
  - 低风速 `0-3`、`3-5` 的最优组合均为 `blockage_off`；
  - 多数中高风速段的最优组合转为 `blockage_on`；
  - 风向 `60-90` 的最优组合为 `blockage_off`，而 `0-30`、`120-150`、`180-210` 等扇区则为 `blockage_on`。
- 因此可以在 Results 中写“blockage 收益具有工况依赖性”，但不宜把这种依赖写成已完成的机理解释。

### 5.5 Paper-ready statement
**Paper-ready statement:** 在控制实验组与候选定义后，启用 blockage 在大多数组合上降低了 `nRMSE`，但其收益主要集中在 rotor-disc upstream mean 与中等距离带，因此 blockage 的效果应被写成条件性改进而非一致性提升。

### 5.6 Open questions
- 为什么 0–20 m 距离带会平均恶化。
- 为什么 blockage 在 1–3 月的组合平均收益为负而在 5–7 月转正。
- blockage 收益与风向几何、阵列排布的对应关系。

### Figure note: `comparison_results/figures/03_blockage_effect_summary.png`
- **Figure path:** `comparison_results/figures/03_blockage_effect_summary.png`
- **Data source CSV:** `comparison_results/controlled_comparison/blockage_controlled_overall.csv`（图中先按 `candidate_type` 聚合）
- **What it shows:** 不同候选类型下 blockage 对平均 `nRMSE` 和平均 `|Bias|` 的影响。
- **Main observation:** rotor-disc upstream mean 的平均收益明显高于 upstream point，内部变量和原生 `WS_eff` 几乎不受影响。
- **How it supports the Results chapter:** 直接支撑“blockage 收益依赖候选类型”的结论。
- **Potential caveat:** 图是候选类型均值，不展示同一类型内部的距离差异和离散程度。

## 6. Equivalent Inflow Wind-Speed Definitions

### 6.1 Overall ranking
- **Strict overall optimal:** `station_power_from_rotor_disc_upstream70m_mean_kW + blockage_on`，`nRMSE=0.1553069`。
- **Robust overall recommendation:** `station_power_from_upstream_60m_kW + blockage_on`，`nRMSE=0.1585644`，`stability_score=0.4293943`。
- **解释边界：** 前者回答“当前 overall 指标最小是谁”，后者回答“跨月份更稳健的推荐是谁”。

### 6.2 Distance-error relationship
- `upstream_point + blockage_off`：最佳 `nRMSE` 在 400 m，最差在 1 m。
- `upstream_point + blockage_on`：最佳 `nRMSE` 在 80 m，最差在 1 m。
- `rotor_disc_upstream_mean + blockage_off`：最佳 `nRMSE` 在 160 m。
- `rotor_disc_upstream_mean + blockage_on`：最佳 `nRMSE` 在 70 m。
- 因此 blockage 不仅改变误差大小，也改变“最优距离带”本身。

### 6.3 Point speed vs rotor-disc mean
- 在 blockage on 情况下，稳健前列同时包含 upstream point（60 m、70 m、80 m）与 rotor-disc mean（30–70 m）。
- 在 blockage off 情况下，两类候选的最佳 `nRMSE` 都出现在更长距离，且整体误差水平明显高于 blockage on 的前列组合。
- 结果上更像“距离带竞争”而不是单纯的“点风速一定优于面平均”或相反。

### 6.4 Bias and nRMSE consistency
- `rotor_disc_upstream_mean + blockage_on` 的最优 `nRMSE` 距离是 70 m，但最小 `abs_bias` 距离是 60 m。
- `upstream_point + blockage_on` 的最优 `nRMSE` 与最小 `abs_bias` 同时出现在 80 m。
- 这说明候选筛选不能只凭一个指标，也不能假设 `nRMSE` 与 Bias 必然同步改善。

### 6.5 Paper-ready statement
**Paper-ready statement:** 等效入流风速定义存在明显距离依赖，且 blockage 会改变最优距离带；因此候选推荐应同时考虑整体误差、稳健性和物理可解释性。

### 6.6 Open questions
- 为什么 blockage on 后最优距离整体向中等距离带迁移。
- 为什么 rotor-disc mean 的 `nRMSE` 最优与 Bias 最优不完全一致。
- strict overall optimal 与 robust optimal 在工程含义上应如何权衡。

### Figure note: `comparison_results/figures/04_distance_vs_nrmse.png`
- **Figure path:** `comparison_results/figures/04_distance_vs_nrmse.png`
- **Data source CSV:** `comparison_results/candidate_analysis/distance_error_curve.csv`
- **What it shows:** 两类有距离定义的候选在不同 blockage 设置下的 `nRMSE`-距离曲线。
- **Main observation:** blockage off 的最优点偏向较长距离，blockage on 的最优点偏向中等距离。
- **How it supports the Results chapter:** 支撑“候选定义存在距离依赖，且 blockage 会改变最优距离带”的结论。
- **Potential caveat:** 图中不包含月度波动信息，只反映 overall 结果。

### Figure note: `comparison_results/figures/05_distance_vs_bias.png`
- **Figure path:** `comparison_results/figures/05_distance_vs_bias.png`
- **Data source CSV:** `comparison_results/candidate_analysis/distance_error_curve.csv`
- **What it shows:** 两类有距离定义的候选在不同 blockage 设置下的 Bias/`abs_bias` 响应。
- **Main observation:** 最小偏差距离不总是与最小 `nRMSE` 距离相同。
- **How it supports the Results chapter:** 支撑“候选筛选不能只依赖单一误差指标”的结论。
- **Potential caveat:** Bias 对基准接近零的组合较敏感，需要结合 `nRMSE` 一起解读。

## 7. Monthly Robustness

### 7.1 Monthly best candidates
| Month | Monthly top-1 candidate | Blockage | nRMSE | n |
| --- | --- | --- | ---: | ---: |
| 1 | `station_power_from_rotor_disc_upstream120m_mean_kW` | on | 0.0955 | 2282 |
| 2 | `station_power_from_upstream_120m_kW` | on | 0.1237 | 2526 |
| 3 | `station_power_from_rotor_disc_upstream100m_mean_kW` | on | 0.1660 | 2836 |
| 4 | `station_power_from_rotor_disc_upstream90m_mean_kW` | on | 0.1524 | 2742 |
| 5 | `station_power_from_upstream_70m_kW` | on | 0.1258 | 2924 |
| 6 | `station_power_from_rotor_disc_upstream60m_mean_kW` | on | 0.1228 | 2515 |
| 7 | `station_power_from_upstream_50m_kW` | on | 0.2363 | 2642 |

### 7.2 Stable candidates
- 稳健性前 10 名全部为 `blockage_on`。
- 排名前 10 的距离大多集中在 upstream 60–80 m 与 rotor-disc mean 30–70 m。
- `station_power_from_upstream_60m_kW + blockage_on` 的 `top1_month_count=0`，但 `monthly_nRMSE_mean=0.1525`、`monthly_nRMSE_std=0.0402`、`monthly_nRMSE_max=0.2368`，因此综合得分最低。
- 这一结果强调“稳定前列”比“偶尔第一”更适合做论文推荐。

### 7.3 Stability score definition
- 定义：`stability_score = monthly_nRMSE_mean + 1.0 × monthly_nRMSE_std + 1.0 × monthly_nRMSE_max`
- 作用：作为结果章节中的可复现筛选指标，用于平衡平均水平、波动性和最差月份。
- 边界：该权重是当前分析脚本设定，不应被写成仓库既有规范或最终工程准则。

### 7.4 Paper-ready statement
**Paper-ready statement:** 月度热力图表明，候选定义的优劣随月份变化，因此结果章节更适合推荐跨月份稳定前列的候选距离带，而不是逐月切换局部最优组合。

### Figure note: `comparison_results/figures/06_monthly_nrmse_heatmap.png`
- **Figure path:** `comparison_results/figures/06_monthly_nrmse_heatmap.png`
- **Data source CSV:** `comparison_results/candidate_analysis/monthly_candidate_rank.csv`
- **What it shows:** 各候选定义在 1–7 月的 `nRMSE` 热力图。
- **Main observation:** 各月份低误差区域并不完全重合。
- **How it supports the Results chapter:** 支撑“月度最优候选并不固定”的结论。
- **Potential caveat:** 热力图不直接展示 overall 排名，需要与稳健性排序表联读。

### Figure note: `comparison_results/figures/07_candidate_rank_heatmap.png`
- **Figure path:** `comparison_results/figures/07_candidate_rank_heatmap.png`
- **Data source CSV:** `comparison_results/candidate_analysis/monthly_candidate_rank.csv`
- **What it shows:** 各候选定义在 1–7 月的月度名次热力图。
- **Main observation:** 没有单一候选在所有月份都稳定占据第一。
- **How it supports the Results chapter:** 直接支撑“不能逐月自由选择最优口径来代表整体模型能力”。
- **Potential caveat:** 名次只反映相对顺序，不反映不同候选之间的绝对误差差距大小。

## 8. Wind-Speed and Wind-Direction Dependence

### 8.1 Wind-speed bins
- **样本数：** `0-3=1582`，`3-5=2980`，`5-7=3679`，`7-9=3802`，`9-11=2961`，`11-13=1942`，`13+=1521`。
- **各分箱最佳组合：**
  - `0-3`: `station_power_from_ws_eff_pywake_native_kW + blockage_off`，`nRMSE=0.0563`
  - `3-5`: `station_power_pywake_internal_kW + blockage_off`，`nRMSE=0.1009`
  - `5-7`: `station_power_from_rotor_disc_upstream140m_mean_kW + blockage_on`，`nRMSE=0.1294`
  - `7-9`: `station_power_from_rotor_disc_upstream90m_mean_kW + blockage_on`，`nRMSE=0.1771`
  - `9-11`: `station_power_from_rotor_disc_upstream40m_mean_kW + blockage_on`，`nRMSE=0.2122`
  - `11-13`: `station_power_from_upstream_20m_kW + blockage_on`，`nRMSE=0.1854`
  - `13+`: `station_power_from_upstream_1m_kW + blockage_on`，`nRMSE=0.0769`
- **直接结论：** 最优候选与最优 blockage 设置都随风速分箱变化。

### 8.2 Wind-direction sectors
- **样本数范围：** 622–2781。
- **代表性扇区结果：**
  - `0-30`: `station_power_from_upstream_250m_kW + blockage_on`，`nRMSE=0.1263`
  - `60-90`: `station_power_from_rotor_disc_upstream1m_mean_kW + blockage_off`，`nRMSE=0.1053`
  - `180-210`: `station_power_from_upstream_50m_kW + blockage_on`，`nRMSE=0.2008`
  - `330-360`: `station_power_from_upstream_130m_kW + blockage_on`，`nRMSE=0.1155`
- **直接结论：** 风向扇区不仅改变候选优劣，也改变最优 blockage 设置。

### 8.3 Paper-ready statement
**Paper-ready statement:** 风速分箱和风向扇区结果都表明，候选风速定义的相对优劣具有工况依赖性，因此整体推荐应强调稳健性，而不是声称某一候选在所有工况下均最优。

### 8.4 What needs Discussion
- 风速中段（特别是 `9-11`）误差较高的物理原因。
- 风向扇区差异与阵列几何的对应关系。
- blockage on/off 在不同工况下切换的机制解释。

### Figure note: `comparison_results/figures/08_wind_speed_bin_performance.png`
- **Figure path:** `comparison_results/figures/08_wind_speed_bin_performance.png`
- **Data source CSV:** `comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`
- **What it shows:** 不同候选类型在各风速分箱下的平均 `nRMSE` 曲线。
- **Main observation:** 最优候选会在低风速、 中风速和高风速段之间切换。
- **How it supports the Results chapter:** 支撑“模型表现受风速工况影响”的结论。
- **Potential caveat:** 图中按候选类型聚合，会弱化同一类型内部的距离差异。

### Figure note: `comparison_results/figures/09_wind_direction_bin_performance.png`
- **Figure path:** `comparison_results/figures/09_wind_direction_bin_performance.png`
- **Data source CSV:** `comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`
- **What it shows:** 不同候选类型在各风向扇区下的平均 `nRMSE` 曲线。
- **Main observation:** 不同扇区的低误差类型和距离带并不一致。
- **How it supports the Results chapter:** 支撑“模型表现受风向工况影响”的结论。
- **Potential caveat:** 风向扇区样本数不均衡，尤其 `240-270` 与 `270-300` 样本较少。

## 9. Case Studies

### 9.1 Maintenance case
- **CSV:** `comparison_results/case_studies/case_maintenance_improvement.csv`
- **窗口：** `2024-02-24 17:00:00` 至 `2024-02-25 16:45:00`
- **样本数：** 96 个 15 min 时刻
- **主要现象：** 逐时刻 `improvement_abs_error` 全为正，平均每步改善 71.54 MW。
- **支持结论：** 维护修正的收益可以在连续时段内稳定体现，而不是只体现在离散单点上。

### 9.2 Blockage case
- **CSV:** `comparison_results/case_studies/case_blockage_improvement.csv`
- **窗口：** `2024-05-14 08:15:00` 至 `2024-05-15 08:00:00`
- **样本数：** 96 个 15 min 时刻
- **主要现象：** 平均每步改善 31.09 MW，但窗口内仍存在负改善时刻（最小值 -21.54 MW）。
- **支持结论：** blockage 在窗口总体上有收益，但收益不是逐时刻无条件成立。

### 9.3 Candidate-distance case
- **CSV:** `comparison_results/case_studies/case_candidate_difference.csv`
- **窗口：** `2024-05-14 08:15:00` 至 `2024-05-15 08:00:00`
- **样本数：** 96 个 15 min 时刻
- **主要现象：** 推荐候选相对 `WS_eff native` 的平均每步改善为 41.17 MW，但同样出现局部负改善时刻（最小值 -31.98 MW）。
- **支持结论：** 候选替换的收益更适合写成连续窗口上的总体优势，而不是所有时刻都严格占优。

### 9.4 What each case supports
- maintenance case → 支持“维护修正会系统性影响验证结果”；
- blockage case → 支持“blockage 收益具有条件性”；
- candidate-distance case → 支持“候选推荐应基于总体稳健性，而不是单个时间点的局部最好”。

### Figure note: `comparison_results/figures/case_maintenance_improvement.png`
- **Figure path:** `comparison_results/figures/case_maintenance_improvement.png`
- **Data source CSV:** `comparison_results/case_studies/case_maintenance_improvement.csv`
- **What it shows:** 维护修正前后与实测功率的时间序列、误差序列及辅助变量。
- **Main observation:** 整个 24 h 窗口中，维护修正后的误差曲线持续低于不维护版本。
- **How it supports the Results chapter:** 支撑“维护修正带来持续性改善”。
- **Potential caveat:** 这是代表性窗口，不等价于全时段都具有相同改善幅度。

### Figure note: `comparison_results/figures/case_blockage_improvement.png`
- **Figure path:** `comparison_results/figures/case_blockage_improvement.png`
- **Data source CSV:** `comparison_results/case_studies/case_blockage_improvement.csv`
- **What it shows:** blockage off/on 与实测功率的时间序列对比及误差序列。
- **Main observation:** blockage on 在多数时刻减小误差，但局部仍存在反向时刻。
- **How it supports the Results chapter:** 支撑“blockage 的收益具有条件性”。
- **Potential caveat:** 图中案例对应最佳连续窗口，不能外推为所有时段都同等改善。

### Figure note: `comparison_results/figures/case_candidate_difference.png`
- **Figure path:** `comparison_results/figures/case_candidate_difference.png`
- **Data source CSV:** `comparison_results/case_studies/case_candidate_difference.csv`
- **What it shows:** 推荐候选与 `WS_eff native` 的时间序列对比及误差序列。
- **Main observation:** 推荐候选在窗口总体上优于传统候选，但局部时刻仍有误差回升。
- **How it supports the Results chapter:** 支撑“候选推荐依赖整体窗口表现与稳健性，而非逐时刻完全占优”。
- **Potential caveat:** 比较对象是当前分析中定义的传统基线，不代表所有可能基线都得到同样结论。

## 10. Recommended Statements for the Paper

### 10.1 Results section statements
- 在共同时间交集上，维护版与不维护版实验的有效评价样本并不完全等于共同时刻数，因此后续比较必须基于统一样本域开展。
- 在控制候选定义和 blockage 设置后，维护状态修正使 `not_curtailed` overall 的 `nRMSE` 全部下降，说明运行状态一致性处理会系统性影响模型验证结果。
- 在控制实验组与候选定义后，blockage 在大多数组合上降低了误差，但其收益主要集中在 rotor-disc upstream mean 与中等距离带。
- 候选风速定义存在明显距离依赖，且 strict overall 最优与跨月份稳健最优不完全一致。
- 风速与风向工况都会改变优选候选，因此推荐应强调稳健性而非单一工况下的局部最优。

### 10.2 Discussion section statements
- 2 月维护修正收益偏高、而 4–6 月收益较弱，可能与停机分布和样本构成有关，需要结合维护记录进一步解释。
- blockage 在短距离带与冬季月份的负收益提示其效果可能依赖于来流结构和阵列几何。
- 风向扇区差异需要与风机布局和主来流方向共同解释。

### 10.3 Conclusion section statements
- 本研究表明，统一样本域和运行状态口径是风电场功率模型公平验证的必要前提。
- 维护状态修正对误差评价具有一致影响，但应被定位为数据一致性处理。
- blockage 与等效入流风速定义的收益均具有条件性，推荐应基于稳健性而非单一局部最优。

## 11. Limitations and TODO
- 当前结论全部基于描述性统计，未进行显著性检验，因此不应使用“显著提升”等表述。
- `maintenance_count_vs_nRMSE_improvement_corr` 在 overall 摘要中没有有限值，说明维护数量关系尚缺少稳健的量化证据。
- 风速/风向分析说明了工况依赖性，但不等于已经完成物理机制解释；相关内容应在 Chapter 5 继续展开。
- 若论文定稿需要固定的稳健性权重，应确认 `stability_score` 的正式定义是否仍采用当前等权形式。
- 若需要经营含义解释，应另外确认实测功率与限电口径在业务上的正式定义。
