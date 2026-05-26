# comparison_results 目录说明

本文档说明 `comparison_results` 目录下各文件的用途、数据结构与列含义。

## 1. 目录文件总览

### 根目录
- `candidate_columns_detected.csv`：候选功率列元数据（列名、类型、距离、单位等）。
- `time_coverage_summary.csv`：各数据源时间覆盖与共同交集统计。
- `measured_power_quality_check.csv`：实测功率数据质量检查指标。
- `merged_common_samples.csv`：共同时间样本长表（CSV）。
- `merged_common_samples.parquet`：共同时间样本长表（Parquet，字段与 CSV 一致）。
- `chapter4_analysis_report.md`：第四章自动分析报告正文。
- `README.md`：当前说明文档。

### 子目录
- `single_experiment_evaluation/`：单实验（考虑维护 / 不考虑维护）内部排名结果。
- `controlled_comparison/`：受控对比（仅比较某一因素变化）。
- `candidate_analysis/`：候选列稳健性、距离关系、分箱性能分析。
- `case_studies/`：典型时段案例明细。
- `figures/`：上述分析对应图片（PNG）。

---

## 2. 通用字段字典（多文件复用）

### 2.1 标识与分组字段
- `valid_time`：时间戳（15 分钟粒度）。
- `month`：月份（1~12）。
- `experiment_name`：实验名（`with_maintenance` / `without_maintenance`）。
- `experiment_name_with_maintenance`：对比中“考虑维护”一侧实验名。
- `experiment_name_without_maintenance`：对比中“不考虑维护”一侧实验名。
- `station`：场站标识（本项目为 `MZS`）。
- `scope_name`：样本范围（`all_samples` 或 `not_curtailed`）。
- `enable_blockage`：是否启用阻塞模型（`true`/`false`）。
- `candidate_power_col`：候选预测功率列名（原始来源列）。
- `candidate_type`：候选类型（如 `upstream_point`、`rotor_disc_upstream_mean`、`ws_eff_pywake_native`、`pywake_internal`）。
- `distance_m`：候选点距离（米，若无距离则为空）。
- `period_type`：周期类型（`overall` 或 `month`）。
- `period_value`：周期值（`ALL` 或 `M01`~`M12`）。
- `rank`：同组内按性能排序（1 为最优）。

### 2.2 物理量与状态字段
- `actual_power_mw`：实测总有功功率（MW）。
- `actual_station_power_mw`：实测场站功率（MW）。
- `pred_power_mw`：候选模型预测功率（MW）。
- `limit_power_mw`：限电功率阈值（MW）。
- `wind_speed`：风速。
- `wind_direction`：风向。
- `maintenance_count`：该时刻维护台数。
- `is_curtailed`：是否限电样本。
- `error`：预测误差（`pred_power_mw - actual_power_mw`）。
- `abs_error`：绝对误差。

### 2.3 评估指标字段
- `n`：有效样本数（剔除非有限值后）。
- `MAE`：平均绝对误差（MW）。
- `RMSE`：均方根误差（MW）。
- `Bias`：平均偏差（MW）。
- `abs_bias`：偏差绝对值（MW）。
- `nMAE`：归一化 MAE（`MAE / P_norm`）。
- `nRMSE`：归一化 RMSE（`RMSE / P_norm`）。
- `R2`：决定系数。
- `Corr`：相关系数。
- `median_abs_error`：绝对误差中位数（MW）。
- `p90_abs_error`：绝对误差 90 分位（MW）。
- `energy_error_mwh`：误差能量积分（MWh）。
- `absolute_energy_error_mwh`：绝对误差能量积分（MWh）。
- `maintenance_count_mean`：该组样本维护台数均值。
- `maintenance_count_median`：该组样本维护台数中位数。

### 2.4 对比派生字段（受控比较）
- 前缀/后缀规则：
  - `*_with_maintenance`、`*_without_maintenance`：维护状态受控比较两侧。
  - `*_blockage_on`、`*_blockage_off`：阻塞开关受控比较两侧。
- `delta_X`：基线指标减去对照指标（正值通常表示改进）。
- `percent_improvement_X`：相对改进百分比（`(baseline - compared) / baseline * 100%`）。
- `delta_Bias_abs`：`abs_bias` 的差值（绝对偏差改变量）。

---

## 3. 各文件说明（含数据结构与列）

## 3.1 根目录 CSV/Parquet

### `candidate_columns_detected.csv`
- 结构：候选功率列元数据表；一行对应“某实验中的某候选列”。
- 列：
  - `experiment_name`：实验名。
  - `candidate_power_col`：原始候选功率列名（kW）。
  - `converted_power_col`：转换后的 MW 列名。
  - `candidate_type`：候选类型。
  - `candidate_family`：候选家族说明（文本）。
  - `distance_m`：候选距离（米）。
  - `display_name`：展示用名称。
  - `original_unit`：原单位（`kW`）。
  - `analysis_unit`：分析单位（`MW`）。

### `time_coverage_summary.csv`
- 结构：各输入/输出数据集时间覆盖统计表。
- 列：
  - `dataset_name`：数据集名称。
  - `row_count`：总行数。
  - `unique_time_count`：唯一时间点数。
  - `start_time`：开始时间。
  - `end_time`：结束时间。
  - `common_time_overlap_count`：与共同交集重叠的时间点数。
  - `common_time_overlap_ratio`：重叠比例。

### `measured_power_quality_check.csv`
- 结构：实测数据质量指标键值表。
- 列：
  - `metric`：指标名。
  - `value`：指标值。

### `merged_common_samples.csv` / `merged_common_samples.parquet`
- 结构：共同时间交集长表；一行对应“某时刻-某实验-某阻塞开关-某候选列-某样本范围”。
- 列：
  - `valid_time`,`month`,`experiment_name`,`station`,`enable_blockage`
  - `wind_speed`,`wind_direction`,`maintenance_count`
  - `actual_power_mw`,`actual_station_power_mw`,`limit_power_mw`,`is_curtailed`
  - `candidate_power_col`,`candidate_type`,`distance_m`
  - `pred_power_mw`,`error`,`abs_error`
  - `scope_name`
  - 含义见“通用字段字典”。

## 3.2 `single_experiment_evaluation/`

### 文件
- `ranking_with_maintenance_overall.csv`
- `ranking_with_maintenance_monthly.csv`
- `ranking_without_maintenance_overall.csv`
- `ranking_without_maintenance_monthly.csv`

### 结构
- `overall`：每个候选在整体样本上的指标与排名。
- `monthly`：每个候选在每月样本上的指标与排名。
- 一行对应“实验 + 范围(+月份) + 阻塞开关 + 候选列”。

### 列
- `overall` 文件列：
  - `experiment_name,scope_name,enable_blockage,candidate_power_col,candidate_type,distance_m`
  - `n,MAE,RMSE,Bias,abs_bias,nMAE,nRMSE,R2,Corr,median_abs_error,p90_abs_error,energy_error_mwh,absolute_energy_error_mwh`
  - `maintenance_count_mean,maintenance_count_median,period_type,period_value,rank`
- `monthly` 文件在上述基础上额外包含：`month`。
- 含义见“通用字段字典”。

## 3.3 `controlled_comparison/`

### `maintenance_controlled_overall.csv` / `maintenance_controlled_monthly.csv`
- 结构：固定 `enable_blockage + candidate_power_col` 后，对比“无维护实验 vs 有维护实验”。
- 关键列模式：
  - 维度列：`scope_name`,`enable_blockage`,`candidate_power_col`,`candidate_type`,`distance_m`（monthly 还含 `month`）。
  - 无维护侧指标：`*_without_maintenance`。
  - 有维护侧指标：`*_with_maintenance`。
  - 差值与改进：`delta_*`,`percent_improvement_*`,`delta_Bias_abs`。
- 说明：两文件字段完全同构，`monthly` 比 `overall` 多 `month` 与对应 `period_type/period_value`。

### `maintenance_controlled_summary.csv`
- 结构：维护受控比较汇总统计。
- 列：
  - `summary_level`：汇总层级（overall/monthly等）。
  - `scope_name`：样本范围。
  - `metric`：汇总指标名。
  - `total_combinations`：组合总数。
  - `improved_count`：改进组合数。
  - `improved_ratio`：改进占比。
  - `mean_improvement_pct`,`median_improvement_pct`,`max_improvement_pct`,`min_improvement_pct`：改进百分比统计。
  - `value`：某些非计数型汇总项的值（如相关性或 JSON 描述）。

### `blockage_controlled_overall.csv` / `blockage_controlled_monthly.csv`
- 结构：固定实验与候选后，对比“blockage_off vs blockage_on”。
- 关键列模式：
  - 维度列：`experiment_name`,`scope_name`,`candidate_power_col`,`candidate_type`,`distance_m`（monthly 还含 `month`）。
  - 关闭阻塞侧指标：`*_blockage_off`。
  - 开启阻塞侧指标：`*_blockage_on`。
  - 差值与改进：`delta_*`,`percent_improvement_*`。

### `blockage_controlled_summary.csv`
- 结构：阻塞受控比较汇总统计。
- 列：
  - `summary_level`：汇总层级（overall/monthly/candidate_type/distance_band/focus 等）。
  - `experiment_name`,`scope_name`：实验与范围。
  - `metric`：汇总指标名。
  - `total_combinations`,`improved_count`,`improved_ratio`。
  - `mean_improvement_pct`,`median_improvement_pct`,`max_improvement_pct`,`min_improvement_pct`。
  - `candidate_type`：候选类型分组（可为空）。
  - `value`：汇总值（可能是数值或 JSON）。
  - `n_candidates`：该汇总分组候选数量。
  - `distance_band`：距离分段（如 `0-20m`）。

## 3.4 `candidate_analysis/`

### `robust_candidate_selection.csv`
- 结构：稳健候选综合评分表（以 `with_maintenance + not_curtailed` 为主）。
- 列：
  - 含单实验总体指标列（同 ranking overall 的主指标）。
  - 稳健性列：
    - `monthly_nRMSE_mean`,`monthly_nRMSE_std`,`monthly_nRMSE_max`
    - `monthly_rank_mean`,`monthly_rank_std`
    - `top1_month_count`,`top3_month_count`,`top5_month_count`
    - `worst_month`,`worst_month_nRMSE`
    - `stability_score`（综合稳健分）
    - `robust_rank`（稳健排名）

### `monthly_performance_summary.csv`
- 结构与列：与 `robust_candidate_selection.csv` 相同（用于月度稳健性汇总展示）。

### `monthly_candidate_rank.csv`
- 结构：候选月度排名明细。
- 列：
  - `experiment_name,scope_name,month,enable_blockage,candidate_power_col,candidate_type,distance_m`
  - 指标列：`n,MAE,RMSE,Bias,abs_bias,nMAE,nRMSE,R2,Corr,median_abs_error,p90_abs_error,energy_error_mwh,absolute_energy_error_mwh`
  - `maintenance_count_mean,maintenance_count_median,period_type,period_value,rank`

### `distance_error_curve.csv`
- 结构：按距离排序的误差曲线数据（常用于画距离-误差图）。
- 列：
  - `experiment_name,scope_name,enable_blockage,candidate_power_col,candidate_type,distance_m`
  - 指标列同上
  - `period_type,period_value,rank`

### `candidate_performance_by_wind_speed_bin.csv`
- 结构：风速分箱性能统计；一行对应“候选 + 风速箱”。
- 列：
  - 维度列：`enable_blockage,candidate_power_col,candidate_type,distance_m,wind_speed_bin`
  - 指标列：`n,MAE,RMSE,Bias,abs_bias,nMAE,nRMSE,R2,Corr,median_abs_error,p90_abs_error,energy_error_mwh,absolute_energy_error_mwh`
  - `maintenance_count_mean,maintenance_count_median`

### `candidate_performance_by_wind_direction_bin.csv`
- 结构：风向分箱性能统计；一行对应“候选 + 风向箱”。
- 列与上文件一致，仅分箱列改为 `wind_direction_bin`。

## 3.5 `case_studies/`

### `case_maintenance_improvement.csv`
- 结构：维护状态改进案例时间窗。
- 列：
  - `valid_time,actual_power_mw,wind_speed,wind_direction,maintenance_count,is_curtailed`
  - `with_maintenance`：考虑维护预测值（MW）。
  - `without_maintenance`：不考虑维护预测值（MW）。
  - `improvement_abs_error`：绝对误差改进量（正值表示考虑维护更好）。

### `case_blockage_improvement.csv`
- 结构：阻塞开关改进案例时间窗。
- 列：
  - `valid_time,actual_power_mw,wind_speed,wind_direction,maintenance_count,is_curtailed`
  - `blockage_off`：关闭阻塞预测值（MW）。
  - `blockage_on`：开启阻塞预测值（MW）。
  - `improvement_abs_error`：绝对误差改进量（正值表示开启阻塞更好）。

### `case_candidate_difference.csv`
- 结构：推荐候选 vs 传统候选差异案例时间窗。
- 列：
  - `valid_time,actual_power_mw,wind_speed,wind_direction,maintenance_count,is_curtailed`
  - `station_power_from_upstream_60m_kW`：推荐候选预测列（字段名保留原命名，值为 MW）。
  - `station_power_from_ws_eff_pywake_native_kW`：传统候选预测列（字段名保留原命名，值为 MW）。
  - `improvement_abs_error`：推荐候选相对传统候选的绝对误差改进量（正值表示推荐更好）。

## 3.6 `figures/`（图片文件）

以下文件均为可视化结果（PNG，非表格数据，无“列”概念）：
- `01_time_coverage.png`
- `02_maintenance_effect_by_month.png`
- `03_blockage_effect_summary.png`
- `04_distance_vs_nrmse.png`
- `05_distance_vs_bias.png`
- `06_monthly_nrmse_heatmap.png`
- `07_candidate_rank_heatmap.png`
- `08_wind_speed_bin_performance.png`
- `09_wind_direction_bin_performance.png`
- `case_maintenance_improvement.png`
- `case_blockage_improvement.png`
- `case_candidate_difference.png`

---

## 4. 备注
- `merged_common_samples.parquet` 与 `merged_common_samples.csv` 字段一致，仅存储格式不同。
- 某些汇总文件中的 `value` 字段可能存储 JSON 字符串，用于表达“最佳/最差组合”等结构化结论。
