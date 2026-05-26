# 4. Results

## 4.1 Sample Coverage and Evaluation Dataset

本章所有横向比较均基于共同时间交集构建，交集定义为 `with_maintenance valid_time ∩ without_maintenance valid_time ∩ measured timestamp`，并进一步并入气象风速、风向与维护台数。根据 `comparison_results/time_coverage_summary.csv`，共同评价样本共有 19586 个 15 min 时刻，对应时间范围为 2024-01-01 08:00 至 2024-07-29 10:15。其中，考虑维护实验相对于完整预报时段额外跳过了 830 个时刻，这与维护矩阵缺失时的 `missing_maintenance_policy=skip` 一致。因此，后续维护状态比较均不能直接使用两组实验各自原始时间范围，而必须使用共同交集样本。

共同样本长表文件为 `comparison_results/merged_common_samples.csv`（并同步保存 `comparison_results/merged_common_samples.parquet`），其中统一将候选 `station_power_*_kW` 转换为 MW。归一化容量 `P_norm` 统一取共同样本下实测 `MZS_FAN_ACTIVE_POWER_SUM` 的 95 分位值，即 288.900 MW，以保持与现有评价脚本的口径一致。时间覆盖图见 `comparison_results/figures/01_time_coverage.png`。

## 4.2 Overview of Single-Experiment Rankings

单实验 ranking 结果分别见：

- `comparison_results/single_experiment_evaluation/ranking_without_maintenance_overall.csv`
- `comparison_results/single_experiment_evaluation/ranking_with_maintenance_overall.csv`
- `comparison_results/single_experiment_evaluation/ranking_without_maintenance_monthly.csv`
- `comparison_results/single_experiment_evaluation/ranking_with_maintenance_monthly.csv`

在共同样本与 `not_curtailed` 条件下，不考虑维护实验的 overall 最优组合为 `station_power_from_rotor_disc_upstream50m_mean_kW`（`enable_blockage=True`，`nRMSE=0.1703`），而考虑维护实验的 overall 最优组合为 `station_power_from_rotor_disc_upstream70m_mean_kW`（`enable_blockage=True`，`nRMSE=0.1553`）。这一结果可作为实验内部概览，但不能直接证明维护修正或阻塞项本身有效，因为不同实验之间若直接比较“各自最优”组合，会同时混入候选风速口径与 blockage 开关差异。

月度 ranking 也显示最优候选并非逐月完全固定，因此 overall 第一名并不自动等价于跨月份最稳健方案。后续各节因此统一采用控制变量比较，而不以“各自最优”作为唯一结论依据。

## 4.3 Effect of Maintenance-State Correction

维护状态修正的控制变量比较结果见：

- `comparison_results/controlled_comparison/maintenance_controlled_overall.csv`
- `comparison_results/controlled_comparison/maintenance_controlled_monthly.csv`
- `comparison_results/controlled_comparison/maintenance_controlled_summary.csv`
- `comparison_results/figures/02_maintenance_effect_by_month.png`

在 `not_curtailed` 条件下，固定 `candidate_power_col` 与 `enable_blockage` 后，共比较 80 个 overall 组合；其中 `nRMSE` 改善的组合占比为 100.00%，平均改善幅度为 10.12% ，中位改善幅度为 11.34% 。就当前共同样本而言，overall 层面的误差改善在候选组合上具有一致方向，但月度改善幅度仍存在波动，因此维护修正的收益更适合被解释为“评价对象对齐”带来的稳定影响，而非新的物理建模增益。

月度结果进一步表明，维护修正的收益存在明显时间波动，并与维护台数变化同步出现起伏（见 `02_maintenance_effect_by_month.png`）。因此，维护状态修正更适合被解释为“保证模型计算对象与实测统计对象一致”的数据一致性步骤，而不应被表述为新的尾流物理机制。

## 4.4 Effect of Blockage

阻塞控制变量比较结果见：

- `comparison_results/controlled_comparison/blockage_controlled_overall.csv`
- `comparison_results/controlled_comparison/blockage_controlled_monthly.csv`
- `comparison_results/controlled_comparison/blockage_controlled_summary.csv`
- `comparison_results/figures/03_blockage_effect_summary.png`

以 `with_maintenance + not_curtailed` 为主线，固定实验组与候选口径后，共比较 40 个 overall 组合；其中 `nRMSE` 改善组合占比为 87.50%，平均改善幅度为 3.43% ，中位改善幅度为 6.64% 。从 `03_blockage_effect_summary.png` 可见，阻塞项的净效果并非对所有候选口径一致，其改善程度受候选类型与距离定义影响。

因此，第 4 章对 blockage 的表述应限定为：在控制变量条件下，阻塞开启对部分候选风速口径表现出平均误差改善，但其收益大小依赖候选定义、月份与样本域，不能由单个 overall 最优排名直接推出全局性结论。

## 4.5 Performance of Equivalent Inflow Wind-Speed Definitions

候选口径整体表现与稳健性排序见：

- `comparison_results/candidate_analysis/robust_candidate_selection.csv`
- `comparison_results/candidate_analysis/distance_error_curve.csv`
- `comparison_results/figures/04_distance_vs_nrmse.png`
- `comparison_results/figures/05_distance_vs_bias.png`

在 `with_maintenance + not_curtailed` 主线下，稳健性排序第一的候选为 `station_power_from_upstream_60m_kW`（`enable_blockage=True`），其 overall `nRMSE=0.1586`，`stability_score=0.4294`。从距离误差曲线可以看出，upstream point 与 rotor-disc upstream mean 两类候选随距离变化均呈现明显的距离依赖性，且不同 blockage 设置下曲线位置并不完全重合。这说明等效入流风速口径的差异不仅体现为“哪一列更好”，更体现为特定距离带的整体误差特征。

同时，`04_distance_vs_nrmse.png` 与 `05_distance_vs_bias.png` 显示 nRMSE 与 Bias 对距离的响应并不总是同步，因此最终候选筛选不能只依据单一误差指标，也不能逐月自由选择局部最优距离。

## 4.6 Monthly Robustness of Candidate Wind-Speed Definitions

跨月份稳健性结果见：

- `comparison_results/candidate_analysis/monthly_candidate_rank.csv`
- `comparison_results/candidate_analysis/monthly_performance_summary.csv`
- `comparison_results/figures/06_monthly_nrmse_heatmap.png`
- `comparison_results/figures/07_candidate_rank_heatmap.png`

本研究对每个候选定义统计 `monthly_nRMSE_mean`、`monthly_nRMSE_std`、`monthly_nRMSE_max`、`monthly_rank_mean`、`monthly_rank_std`、`top1_month_count`、`top3_month_count`、`top5_month_count` 与 `worst_month_nRMSE`，并采用 `stability_score = mean + 1.0×std + 1.0×max` 的等权复合形式进行排序。该评分用于结果章节的可复现筛选，不代表仓库已有固定权重规范。

热力图结果表明，月度最优候选并不完全一致，但部分候选在多数月份保持前列。因此，本研究更倾向于选择跨月份稳定的候选或距离带，而不是为每个月单独切换最优模型。

## 4.7 Wind-Speed-Dependent Performance

风速分箱结果见：

- `comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`
- `comparison_results/figures/08_wind_speed_bin_performance.png`

本次结果分析采用风速分箱 `0-3, 3-5, 5-7, 7-9, 9-11, 11-13, 13+`。在各风速段内，最优候选并不完全一致：例如，`0-3` 风速段下当前最优候选为 `station_power_from_ws_eff_pywake_native_kW`，而更高风速段会出现不同候选进入前列。该结果说明候选口径差异与来流强度相关，且阻塞收益并非在所有风速段均等出现。对误差最大的风速段及其物理解释，可留待第 5 章进一步讨论。

## 4.8 Wind-Direction-Dependent Performance

风向扇区结果见：

- `comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`
- `comparison_results/figures/09_wind_direction_bin_performance.png`

本次分析按 30° 扇区组织风向样本。在当前结果中，不同扇区的最优候选并不完全相同，例如 `0-30` 扇区下最优候选为 `station_power_from_upstream_250m_kW`。这意味着候选风速口径与 blockage 收益都可能受到阵列相对来流方向的影响，但更深入的阵列几何解释应放在 Discussion 章节展开。

## 4.9 Case Studies

典型案例结果见：

- `comparison_results/case_studies/case_maintenance_improvement.csv`
- `comparison_results/case_studies/case_blockage_improvement.csv`
- `comparison_results/case_studies/case_candidate_difference.csv`
- `comparison_results/figures/case_maintenance_improvement.png`
- `comparison_results/figures/case_blockage_improvement.png`
- `comparison_results/figures/case_candidate_difference.png`

维护修正改善最明显的连续时段为 `2024-02-24 17:00:00` 至 `2024-02-25 16:45:00`；阻塞改善最明显的连续时段为 `2024-05-14 08:15:00` 至 `2024-05-15 08:00:00`；推荐口径相对于传统 `WS_eff native` 差异最明显的连续时段为 `2024-05-14 08:15:00` 至 `2024-05-15 08:00:00`。这些案例均使用连续 6–24 h 窗口识别，而非孤立单点，因此更适合展示模型差异在时间序列上的累积表现。

## 4.10 Summary of Main Findings

综合本章结果，可得到以下几点：

1. 维护版与不维护版输出存在时间覆盖差异，因此任何横向比较都必须基于共同时间交集；
2. 单实验 ranking 只能作为概览，不能替代控制变量比较；
3. 维护状态修正会改变模型评价结果，但其作用应被理解为运行状态一致性处理；
4. 阻塞效应在部分候选口径上呈现平均误差改善，但其收益具有候选类型、月份与样本域依赖性；
5. 等效入流风速口径存在明显距离依赖，且跨月份稳健性比单月第一名更重要；
6. 风速段、风向扇区和典型连续时段均表明，不同候选口径的表现差异具有条件性，因此最终推荐应优先考虑稳健且可解释的距离带，而不是逐月自由切换局部最优组合。

# Information Still Needed

- TODO: 若论文定稿需要固定的 robustness 权重，应进一步确认 `stability_score` 的正式定义是否保留当前等权形式。
- TODO: 若需要更严格的风向机理解释，还应结合阵列方向、排布密度与阻塞证据做补充分析。
- TODO: 如需报告能量误差的经营含义，还应确认实测功率与限电口径在业务上的正式解释。
