# 4. Results

## 4.1 Sample Coverage and Evaluation Dataset

本章所有横向比较均基于共同时间交集构建，交集定义为 `with_maintenance valid_time ∩ without_maintenance valid_time ∩ measured timestamp`，并进一步并入气象风速、风向与维护台数。根据 `comparison_results/time_coverage_summary.csv`，共同时间交集共有 19586 个 15 min 时刻，对应时间范围为 2024-01-01 08:00 至 2024-07-29 10:15；其中考虑维护实验相对于完整预报时段额外跳过了 830 个时刻，因此若直接比较两组实验各自原始输出，会把维护缺失导致的时间覆盖差异混入模型效果判断。

从实际可评价样本看，`comparison_results/merged_common_samples.csv` 在共同交集上进一步并入实测功率、限电标记与维护台数。对所有共同时刻去重后，`all_samples` 共有 19586 个时间戳，其中 805 个时刻因 `actual_power_mw` 缺失而不能进入误差计算，因此单个候选组合在 overall 层面的有效 `all_samples` 样本数为 18781；`not_curtailed` 先排除 314 个限电时刻，再经过同样的有限值筛选后得到 18467 个有效样本。候选列 `station_power_*_kW` 在分析中统一转换为 MW，归一化容量 `P_norm` 取共同样本下 `MZS_FAN_ACTIVE_POWER_SUM` 的 95 分位值 288.963 MW。时间覆盖图见 `comparison_results/figures/01_time_coverage.png`。

**证据链：** 分析对象为共同时间交集及其评价样本构造；控制变量为统一时间戳、统一实测目标 `MZS_FAN_ACTIVE_POWER_SUM`、统一 MW 单位与统一限电筛选规则；样本范围为 2024-01-01 08:00 至 2024-07-29 10:15；样本数依次为 19586 个共同时刻、18781 个 `all_samples` 有效评价样本、18467 个 `not_curtailed` 有效评价样本；对应 CSV 为 `comparison_results/time_coverage_summary.csv`、`comparison_results/merged_common_samples.csv`、`comparison_results/candidate_columns_detected.csv`，对应图表为 `comparison_results/figures/01_time_coverage.png`。

**论文可用表述：** 在当前数据处理中，维护版与不维护版输出的可用时间范围并不完全一致，因此后续横向比较必须首先限制在共同时间交集上，并在统一的实测功率口径与单位转换后开展误差评价。

**本节结论：** 综上，本节结果表明后续比较必须同时控制时间覆盖、实测目标与单位口径，否则维护缺失和观测缺测会先于模型差异影响评价结果。

## 4.2 Overview of Single-Experiment Rankings

单实验 ranking 结果分别见：

- `comparison_results/single_experiment_evaluation/ranking_without_maintenance_overall.csv`
- `comparison_results/single_experiment_evaluation/ranking_with_maintenance_overall.csv`
- `comparison_results/single_experiment_evaluation/ranking_without_maintenance_monthly.csv`
- `comparison_results/single_experiment_evaluation/ranking_with_maintenance_monthly.csv`

在共同样本与 `not_curtailed` 条件下，不考虑维护实验的 overall 第一名为 `station_power_from_rotor_disc_upstream50m_mean_kW`（`enable_blockage=True`，`nRMSE=0.1703`，`n=18467`），考虑维护实验的 overall 第一名为 `station_power_from_rotor_disc_upstream70m_mean_kW`（`enable_blockage=True`，`nRMSE=0.1553`，`n=18467`）。这说明在各自实验内部确实存在可排序的优选组合，但这类排序同时混合了候选风速定义、是否启用 blockage 以及是否引入维护状态修正三个因素，因此只能作为实验内部概览，而不能直接用来证明某一个单独因素有效。

月度 ranking 进一步显示，2024 年 1–7 月的月度第一名并不重复：1 月为 `station_power_from_rotor_disc_upstream120m_mean_kW`，2 月为 `station_power_from_upstream_120m_kW`，3 月为 `station_power_from_rotor_disc_upstream100m_mean_kW`，4 月为 `station_power_from_rotor_disc_upstream90m_mean_kW`，5 月为 `station_power_from_upstream_70m_kW`，6 月为 `station_power_from_rotor_disc_upstream60m_mean_kW`，7 月为 `station_power_from_upstream_50m_kW`，且均为 `enable_blockage=True`。因此，overall 第一名并不自动等价于跨月份最稳健方案。

**证据链：** 分析对象为单实验内部的 overall 与 monthly 排名；控制变量为固定实验组后对不同候选列和 blockage 设置进行同口径比较；样本范围为共同样本下的 `all_samples`/`not_curtailed`，其中 `not_curtailed` overall 每个组合的样本数为 18467；核心结果是两组实验的 overall 第一名不同，且 1–7 月的月度第一名没有重复；对应 CSV 为上述四个 ranking 文件。

**论文可用表述：** 单实验 ranking 可以用于识别每组实验内部的较优候选组合，但它不能替代控制变量比较，因为“各自最优”组合同时改变了候选定义与 blockage 设置。

**本节结论：** 综上，本节结果表明 ranking 适合作为概览和筛选入口，但不能单独承担维护修正或 blockage 效果的因果判断。

## 4.3 Effect of Maintenance-State Correction

维护状态修正的控制变量比较结果见：

- `comparison_results/controlled_comparison/maintenance_controlled_overall.csv`
- `comparison_results/controlled_comparison/maintenance_controlled_monthly.csv`
- `comparison_results/controlled_comparison/maintenance_controlled_summary.csv`
- `comparison_results/figures/02_maintenance_effect_by_month.png`

在 `not_curtailed` 条件下，固定 `candidate_power_col` 与 `enable_blockage` 后，共比较 80 个 overall 组合。相对于不考虑维护实验，考虑维护后 `MAE`、`RMSE` 与 `nRMSE` 的改善比例均为 100%，其中 `nRMSE` 平均改善 10.12%、中位改善 11.34%，改善幅度范围为 1.10%–11.83%；`abs_bias` 在 67/80 个组合中改善，中位改善 29.95%，但其均值受极小基准偏差下的百分比放大影响，不宜单独作为主结论。对应的最佳 `nRMSE` 改善组合为 `station_power_from_ws_eff_pywake_native_kW + blockage_on`，最弱改善组合为 `station_power_from_upstream_1m_kW + blockage_on`。

月度层面上，维护状态修正的收益并不均匀。按 `comparison_results/controlled_comparison/maintenance_controlled_monthly.csv` 计算的月均 `nRMSE` 改善在 2 月达到 41.08%，而 4–6 月仅约 0.91%–2.39%，7 月回升至 6.47%。因此，维护状态修正会系统性改变模型验证结果，但其影响强弱依赖于当月样本构成与停机分布；对其形成机制的解释应留待第 5 章讨论。

**证据链：** 分析对象为“是否考虑维护状态”的 controlled comparison；控制变量为固定 `candidate_power_col`、固定 `enable_blockage`、固定 `scope_name`；样本范围为共同样本下的 `not_curtailed` 与 `all_samples`，overall 每个组合的有效样本数为 18467（`not_curtailed`）；样本数为 80 个 overall 组合和 560 个 monthly 组合；核心指标变化为 `MAE/RMSE/nRMSE` 全组合改善、`abs_bias` 多数组合改善但波动更大；对应 CSV 为 `comparison_results/controlled_comparison/maintenance_controlled_overall.csv`、`comparison_results/controlled_comparison/maintenance_controlled_monthly.csv`、`comparison_results/controlled_comparison/maintenance_controlled_summary.csv`，对应图表为 `comparison_results/figures/02_maintenance_effect_by_month.png`。

**论文可用表述：** 在共同时间交集和非限电影响样本上，维护状态修正使相同候选定义与相同 blockage 设置下的 `nRMSE` 全部下降，说明运行状态一致性处理会系统性影响模型验证结果。该处理应被理解为评价口径对齐，而非新的尾流物理建模增益。

**本节结论：** 综上，本节结果表明维护状态修正会稳定改变误差评价，并且是保证模型计算对象与实测统计对象一致的必要步骤，但其收益大小具有月份依赖性。

## 4.4 Effect of Blockage

阻塞控制变量比较结果见：

- `comparison_results/controlled_comparison/blockage_controlled_overall.csv`
- `comparison_results/controlled_comparison/blockage_controlled_monthly.csv`
- `comparison_results/controlled_comparison/blockage_controlled_summary.csv`
- `comparison_results/figures/03_blockage_effect_summary.png`

以 `with_maintenance + not_curtailed` 为主线，固定实验组与候选口径后，共比较 40 个 overall 组合；其中 `MAE`、`RMSE`、`nRMSE` 与 `abs_bias` 的改善比例均为 87.5%，`nRMSE` 平均改善 3.43%、中位改善 6.64%，改善范围为 -27.21% 至 9.78%。因此，阻塞项在当前样本上总体更常带来误差下降，但并非对所有候选口径都有效。

候选类型与距离带的分组结果进一步显示，阻塞收益具有明显条件性。在 `with_maintenance + not_curtailed` 下，`rotor_disc_upstream_mean` 的平均 `nRMSE` 改善为 7.30%，显著高于 `upstream_point` 的 1.45%，而 `WS_eff native` 与 `PyWake internal` 的平均改善仅约 0.06%。按距离带汇总时，61–100 m 与 101–160 m 的平均改善分别为 8.86% 与 7.10%，21–60 m 为 5.51%，160 m 以上为 3.07%，但 0–20 m 反而平均恶化 8.60%。月度层面上，1–3 月的平均改善为负，5–7 月则转为正值并在 5 月达到 12.53%，说明 blockage 的净效果同时受月份与样本域影响。

**证据链：** 分析对象为 blockage on/off 的 controlled comparison；控制变量为固定 `experiment_name`、固定 `candidate_power_col`、固定 `scope_name`；样本范围以 `with_maintenance + not_curtailed` 为主，overall 每个组合的有效样本数为 18467；样本数为 40 个 overall 组合和 280 个 monthly 组合；核心指标变化为 `nRMSE` 改善占比 87.5%、平均改善 3.43%，且收益在候选类型与距离带上分化明显；对应 CSV 为 `comparison_results/controlled_comparison/blockage_controlled_overall.csv`、`comparison_results/controlled_comparison/blockage_controlled_monthly.csv`、`comparison_results/controlled_comparison/blockage_controlled_summary.csv`，对应图表为 `comparison_results/figures/03_blockage_effect_summary.png`。

**论文可用表述：** 在控制实验组与候选定义后，启用 blockage 在大多数组合上降低了误差，但其收益主要集中在 rotor-disc upstream mean 及 61–160 m 距离带，不能由单个最佳组合外推为全局一致结论。

**本节结论：** 综上，本节结果表明 blockage 在当前样本上具有平均改进倾向，但这种收益受候选类型、距离与月份共同约束，因此应被写成条件性结果而非普适性结论。

## 4.5 Performance of Equivalent Inflow Wind-Speed Definitions

候选口径整体表现与稳健性排序见：

- `comparison_results/candidate_analysis/robust_candidate_selection.csv`
- `comparison_results/candidate_analysis/distance_error_curve.csv`
- `comparison_results/figures/04_distance_vs_nrmse.png`
- `comparison_results/figures/05_distance_vs_bias.png`

若仅按 `with_maintenance + not_curtailed` 的 overall `nRMSE` 排序，当前最优组合为 `station_power_from_rotor_disc_upstream70m_mean_kW + blockage_on`，`nRMSE=0.1553`；但若同时考虑月度均值、波动和最差月份，稳健性排序第一的组合变为 `station_power_from_upstream_60m_kW + blockage_on`，其 overall `nRMSE=0.1586`、`stability_score=0.4294`。这表明“strict metric-optimal”与“robustly recommended”并不完全重合，最终推荐不能只由单一 overall 指标决定。

距离误差曲线进一步显示出清晰的距离依赖性。对 `upstream_point` 而言，未启用 blockage 时 `nRMSE` 最优点出现在 400 m，而启用 blockage 后最优点转移到 80 m；对 `rotor_disc_upstream_mean` 而言，未启用 blockage 时最优 `nRMSE` 出现在 160 m，而启用 blockage 后最优点转移到 70 m。与此同时，`rotor_disc_upstream_mean + blockage_on` 的最小 `abs_bias` 出现在 60 m，而不是 `nRMSE` 最优的 70 m，说明 `nRMSE` 与 Bias 对距离的响应并不总是同步。

**证据链：** 分析对象为不同等效入流风速候选定义；控制变量为主线实验 `with_maintenance + not_curtailed`，并分别比较 blockage on/off；样本范围为每个 overall 组合 18467 个有效样本；核心结果包括 strict overall 最优与稳健最优不一致、距离最优点随 blockage 设置迁移、`nRMSE` 与 `abs_bias` 最优距离不完全一致；对应 CSV 为 `comparison_results/candidate_analysis/robust_candidate_selection.csv`、`comparison_results/candidate_analysis/distance_error_curve.csv`，对应图表为 `comparison_results/figures/04_distance_vs_nrmse.png` 与 `comparison_results/figures/05_distance_vs_bias.png`。

**论文可用表述：** 等效入流风速口径的优劣不仅取决于候选类型，还取决于距离定义与是否启用 blockage；因此最终推荐应兼顾整体误差、月度稳健性与物理可解释性，而非只追求单一 overall 指标最小。

**本节结论：** 综上，本节结果表明等效入流风速口径具有明显距离依赖，且最优距离会随 blockage 设置与误差指标而变化。

## 4.6 Monthly Robustness of Candidate Wind-Speed Definitions

跨月份稳健性结果见：

- `comparison_results/candidate_analysis/monthly_candidate_rank.csv`
- `comparison_results/candidate_analysis/monthly_performance_summary.csv`
- `comparison_results/figures/06_monthly_nrmse_heatmap.png`
- `comparison_results/figures/07_candidate_rank_heatmap.png`

本研究对每个候选定义统计 `monthly_nRMSE_mean`、`monthly_nRMSE_std`、`monthly_nRMSE_max`、`monthly_rank_mean`、`monthly_rank_std`、`top1_month_count`、`top3_month_count`、`top5_month_count` 与 `worst_month_nRMSE`，并采用 `stability_score = mean + 1.0×std + 1.0×max` 的等权复合形式进行排序。当前稳健性排序前 10 名全部来自 `enable_blockage=True` 组合，主要集中在 upstream 60–80 m 与 rotor-disc upstream mean 30–70 m 范围内。

更关键的是，2024 年 1–7 月的月度第一名在候选定义上完全不重复，说明不存在一个可在所有月份稳定保持第一的单一距离。稳健性排序第一的 `station_power_from_upstream_60m_kW + blockage_on` 虽然在 7 个月中没有任何一个月获得第一，但其 `monthly_nRMSE_mean=0.1525`、`monthly_nRMSE_std=0.0402`、`monthly_nRMSE_max=0.2368`，因此在“均值 + 波动 + 最差月”综合意义下更稳健。这也说明跨月份推荐更接近“稳定前列”而不是“单月第一”。

**证据链：** 分析对象为候选定义的月度稳健性；控制变量为 `with_maintenance + not_curtailed`，并在同一 `stability_score` 公式下排序；样本范围为 2024 年 1–7 月的月度结果；样本数为 7 个月 × 40 个候选组合；核心结果是月度第一名每月变化、稳健前列集中在 blockage on 的中等距离带；对应 CSV 为 `comparison_results/candidate_analysis/monthly_candidate_rank.csv` 与 `comparison_results/candidate_analysis/monthly_performance_summary.csv`，对应图表为 `comparison_results/figures/06_monthly_nrmse_heatmap.png` 与 `comparison_results/figures/07_candidate_rank_heatmap.png`。

**论文可用表述：** 月度热力图显示最优候选随月份变化，因此本研究更倾向于推荐跨月份保持稳定前列的候选距离带，而不是为每个月单独切换局部最优组合。

**本节结论：** 综上，本节结果表明不能逐月自由选择最优口径来代表模型能力，更合理的做法是基于跨月份稳健性选择稳定候选。

## 4.7 Wind-Speed-Dependent Performance

风速分箱结果见：

- `comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`
- `comparison_results/figures/08_wind_speed_bin_performance.png`

本次结果分析采用风速分箱 `0-3, 3-5, 5-7, 7-9, 9-11, 11-13, 13+`，各分箱样本数分别为 1582、2980、3679、3802、2961、1942 和 1521。在各风速段内，最优候选并不一致：`0-3` 风速段最优为 `station_power_from_ws_eff_pywake_native_kW + blockage_off`（`nRMSE=0.0563`），`3-5` 为 `station_power_pywake_internal_kW + blockage_off`（`nRMSE=0.1009`），`5-11` 的最优组合则主要转为启用 blockage 的 rotor-disc upstream mean 候选，而 `11-13` 与 `13+` 又分别转为 `station_power_from_upstream_20m_kW + blockage_on` 和 `station_power_from_upstream_1m_kW + blockage_on`。

从各风速段的最优可达 `nRMSE` 看，`9-11` 风速段的最优值最高（`nRMSE=0.2122`），说明该工况下不同候选都更难逼近实测功率；而 `0-3` 与 `13+` 两端风速段的最优值相对较低。该结果说明候选风速口径与来流强度存在明显耦合，但其物理解释应在第 5 章进一步展开。

**证据链：** 分析对象为风速分箱下的候选表现；控制变量为 `with_maintenance + not_curtailed` 的统一样本域；样本范围为 7 个风速分箱共 18467 个有效样本；样本数按分箱分别见上文；核心结果是 7 个风速段的最优候选均不完全相同，且 `9-11` 风速段的最优可达误差最高；对应 CSV 为 `comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`，对应图表为 `comparison_results/figures/08_wind_speed_bin_performance.png`。

**论文可用表述：** 风速分箱结果显示，不同来流强度下的优选候选定义并不一致，表明模型表现具有明确的工况依赖性。

**本节结论：** 综上，本节结果表明模型表现会随风速工况变化，同一候选定义不能在所有风速段同时保持最优。

## 4.8 Wind-Direction-Dependent Performance

风向扇区结果见：

- `comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`
- `comparison_results/figures/09_wind_direction_bin_performance.png`

本次分析按 30° 扇区组织风向样本，12 个扇区的样本数介于 622（`240-270`）至 2781（`150-180`）之间。当前结果中，不同扇区的最优候选也不完全相同，例如 `0-30` 扇区的最优组合为 `station_power_from_upstream_250m_kW + blockage_on`（`nRMSE=0.1263`），`60-90` 扇区为 `station_power_from_rotor_disc_upstream1m_mean_kW + blockage_off`（`nRMSE=0.1053`），而 `180-210` 扇区的最优可达误差升高到 `nRMSE=0.2008`。

这种差异表明候选风速口径及 blockage 设置对来流方向具有条件依赖性，但仅凭结果章节尚不能进一步区分是阵列几何、机组遮挡关系还是样本分布差异所致，因此更深入的机理解释应放在 Discussion 章节展开。

**证据链：** 分析对象为风向扇区下的候选表现；控制变量为 `with_maintenance + not_curtailed` 的统一样本域；样本范围为 12 个 30° 扇区，共 18467 个有效样本；样本数按扇区介于 622–2781；核心结果是不同扇区的最优候选与最优 blockage 设置都发生变化；对应 CSV 为 `comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`，对应图表为 `comparison_results/figures/09_wind_direction_bin_performance.png`。

**论文可用表述：** 风向扇区分析表明，候选风速定义的相对优劣会随来流方向改变，因此结果章节只能给出方向相关性结论，而更深入的阵列几何解释需要在第 5 章继续讨论。

**本节结论：** 综上，本节结果表明模型表现同样受到风向工况影响，风向依赖性不能在结果章节中被简化为单一固定候选的全局优势。

## 4.9 Case Studies

典型案例结果见：

- `comparison_results/case_studies/case_maintenance_improvement.csv`
- `comparison_results/case_studies/case_blockage_improvement.csv`
- `comparison_results/case_studies/case_candidate_difference.csv`
- `comparison_results/figures/case_maintenance_improvement.png`
- `comparison_results/figures/case_blockage_improvement.png`
- `comparison_results/figures/case_candidate_difference.png`

三个典型案例均基于连续 96 个 15 min 时刻（24 h 窗口）识别，而非孤立单点。维护修正改善最明显的连续时段为 `2024-02-24 17:00:00` 至 `2024-02-25 16:45:00`，该窗口内逐时刻绝对误差改善均为正，平均每步改善 71.54 MW；阻塞改善最明显的连续时段为 `2024-05-14 08:15:00` 至 `2024-05-15 08:00:00`，平均每步改善 31.09 MW，但窗口内仍出现少量负改善时刻；推荐口径相对于传统 `WS_eff native` 差异最明显的窗口与 blockage 案例相同，平均每步改善 41.17 MW，同样存在局部反向时刻。

这些案例与前述统计结果是一致的：维护修正在最佳窗口内表现为持续性的整体改善，而 blockage 与候选切换则更像“窗口总体收益为正，但局部时间点未必同步改善”的条件性结果。因此，案例分析更适合用来支撑统计结论，而不是替代统计结论。

**证据链：** 分析对象为维护修正、blockage 和候选替换的连续时间窗口案例；控制变量分别对应固定候选 + 固定 blockage、固定实验组 + 固定候选、固定实验组 + 固定 blockage；样本范围为每个案例 96 个连续 15 min 时刻；核心指标为逐时刻绝对误差改善序列及其窗口平均水平；对应 CSV 为上述三个 case study 文件，对应图表为三个 case study PNG。

**论文可用表述：** 典型连续时段分析支持总体统计结论：维护修正在代表性窗口内表现出持续改善，而 blockage 与候选替换的收益更具有条件性和时段依赖性。

**本节结论：** 综上，本节结果表明典型案例能够为前述统计判断提供时序层面的支撑，但也进一步说明 blockage 与候选收益并非逐时刻无条件成立。

## 4.10 Summary of Main Findings

综合本章结果，可得到以下几点：

1. 维护版与不维护版输出存在时间覆盖差异，且共同时间交集中的部分时刻还会因实测缺测或限电筛选退出误差计算，因此任何横向比较都必须基于统一样本域；
2. 单实验 ranking 只能作为实验内部概览，不能替代控制变量比较；
3. 维护状态修正会系统性改变模型评价结果，但其作用应被理解为运行状态一致性处理，而不是新的模型创新；
4. 阻塞效应在部分候选口径上呈现平均误差改善，但其收益具有候选类型、距离、月份与样本域依赖性；
5. 等效入流风速口径存在明显距离依赖，且 strict overall 最优与跨月份稳健最优并不完全一致；
6. 风速段、风向扇区和典型连续时段均表明，不同候选口径的表现差异具有工况条件性，因此最终推荐应优先考虑稳健且可解释的候选距离带，而不是逐月自由切换局部最优组合。

# Information Still Needed

- TODO: 若论文定稿需要固定的 robustness 权重，应进一步确认 `stability_score` 的正式定义是否保留当前等权形式。
- TODO: 若需要更严格的风向机理解释，还应结合阵列方向、排布密度与阻塞证据做补充分析。
- TODO: 如需报告能量误差的经营含义，还应确认实测功率与限电口径在业务上的正式解释。
