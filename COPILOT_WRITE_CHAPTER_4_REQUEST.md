# Copilot 任务说明：撰写论文第 4 章 Results

> 建议将本文档放在 GitHub 仓库根目录，文件名可设为：  
> `COPILOT_WRITE_CHAPTER_4_REQUEST.md`
>
> 本文档用于指导 Copilot 基于当前 GitHub 仓库中的完整代码、模型输出、实测数据和已有第 2/3 章草稿，完成期刊论文中的 **第 4 章 Results**。  
>
> 本次任务的重点是：**先进行可复现的结果分析，再撰写第 4 章结果章节初稿**。  
> 不要只写泛泛总结，不要只列 Top 10，不要只比较各自最优模型。  
> 所有结果必须有 CSV、图表和控制变量依据。

---

# 0. Copilot 需要先理解的项目背景

当前仓库对应一个海上风电场尾流建模与场站功率模拟研究项目。研究对象为仓库中标记为 `MZS` / `JMZSFD` 的海上风电场。

论文整体逻辑为：

1. 前期激光雷达观测提示海上风电场附近存在阻塞效应；
2. 不同空间位置、不同上游距离风速与功率曲线的适配性可能不同；
3. 因此，本文在传统尾流模型基础上：
   - 引入/开启阻塞效应；
   - 定义多种等效入流风速口径；
   - 比较不同风速口径与场站功率的适配性；
4. 实测验证中，通过维护状态修正和限电样本筛选，保证模型预测对象与实测统计对象一致；
5. 第 4 章需要基于第 2 章数据和第 3 章方法，给出实验结果。

当前已有论文草稿：

```text
paper_drafts/paper_draft_chapter_2.md
paper_drafts/paper_draft_chapter_3.md
```

请先阅读这两个文件。第 4 章应与第 2/3 章保持术语一致。

---

# 1. 本次任务目标

请 Copilot 完成两类输出：

## 1.1 可复现结果分析输出

在撰写第 4 章前，需要先生成支撑结果章节的 CSV 和图表：

```text
comparison_results/
  time_coverage_summary.csv
  measured_power_quality_check.csv
  candidate_columns_detected.csv
  merged_common_samples.csv 或 .parquet

comparison_results/single_experiment_evaluation/
  *.csv

comparison_results/controlled_comparison/
  *.csv

comparison_results/candidate_analysis/
  *.csv

comparison_results/case_studies/
  *.csv

comparison_results/figures/
  *.png
  *.html 可选
```

如果这些文件已经存在，请检查是否满足本任务要求；如果不满足，请重新生成或补充。

## 1.2 第 4 章论文初稿

最终输出：

```text
paper_drafts/paper_draft_chapter_4.md
```

第 4 章应是论文结果章节初稿，结构清晰、数据充分、图表可引用、结论克制。

---

# 2. 第 4 章写作边界

## 2.1 本章需要写什么

第 4 章应重点回答：

1. 两组实验与实测数据的共同样本范围是什么；
2. 不考虑维护和考虑维护实验各自的总体表现如何；
3. 在控制变量条件下，维护状态修正是否影响模型评价；
4. 在控制变量条件下，阻塞效应是否改善模型误差；
5. 不同等效入流风速口径中，哪类口径整体表现较好；
6. 最优风速距离是否具有跨月份稳定性；
7. 模型误差是否随风速段、风向段或月份变化；
8. 是否存在典型时段可以解释维护、阻塞或风速口径差异；
9. 哪些结果可作为论文主结论，哪些仅作为辅助检查。

## 2.2 本章不要写什么

请不要写：

- 不要重复第 2 章数据介绍；
- 不要重复第 3 章方法细节；
- 不要做过度机理讨论，第 5 章 Discussion 再展开；
- 不要把维护状态修正写成主要模型创新；
- 不要宣称模型已直接用于业务功率预测；
- 不要只给单个最优排名；
- 不要逐月自由选择最终模型；
- 不要在没有控制变量的情况下说“维护有效”或“阻塞有效”；
- 不要编造不存在的图表、数值或文件路径。

---

# 3. 请优先阅读的仓库文件

请 Copilot 在分析和写作前先阅读以下文件。

## 3.1 论文前文草稿

```text
paper_drafts/paper_draft_chapter_2.md
paper_drafts/paper_draft_chapter_3.md
```

需要保证第 4 章术语与前文一致，例如：

- `MZS` / `JMZSFD` 命名；
- `MZS_FAN_ACTIVE_POWER_SUM` 主评价对象；
- `with maintenance` / `without maintenance`；
- `enable_blockage=False/True`；
- `station_power_*_kW` 与 `station_power_*_MW` 单位转换；
- `all_samples` 与 `not_curtailed` / `non_curtailed` 命名；
- 候选等效入流风速口径分类。

## 3.2 模型输出

```text
five_experiments_output_考虑维护-全月份/all_experiments_station_power_timeseries.csv
five_experiments_output_不考虑维护-全月份/all_experiments_station_power_timeseries.csv
```

以及如果存在的转换后输出：

```text
尾流预测与全站实测对比/all_experiments_station_power_timeseries-*.csv
```

请确认：

- 候选列是 `_kW` 还是 `_MW`；
- 是否需要统一转换到 MW；
- 两组实验输出字段是否一致；
- `enable_blockage` 是否包含 True/False；
- 维护版和不维护版时间范围差异。

## 3.3 实测功率文件

请自动查找第 2 章中使用的轻量实测 CSV，例如：

```text
场站实测数据/JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv
```

主评价对象应优先使用：

```text
MZS_FAN_ACTIVE_POWER_SUM
```

或仓库实际字段名。

同时保留：

```text
MZS_ACTIVE_POWER_STATION
MZS_LIMIT_POWER
MZS_FAN_WINDSPEED_MEAN
```

用于质量检查、限电判断和风速分箱。

## 3.4 维护矩阵

```text
JMZSFD维护记录/jmzsfd_maintenance_matrix.csv
```

用于：

- 计算每个 15 min 模型时刻的维护风机数量；
- 按月份统计维护数量；
- 解释维护状态修正对结果的影响；
- 筛选维护改善明显的典型案例。

## 3.5 气象输入

```text
场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv
```

用于：

- 合并风速；
- 合并风向；
- 风速分箱；
- 风向分箱；
- 检查 `is_interpolated` 对结果是否有影响，若有必要。

## 3.6 评价脚本

请阅读已有评价脚本，例如：

```text
evaluate_station_power_accuracy_multi_station.py
evaluate_station_power_accuracy_multi_station_monthly_combined.py
```

或仓库中实际存在的评价脚本。  
可以复用其指标计算逻辑，但不能只依赖旧 ranking，因为第 4 章需要控制变量比较。

---

# 4. 分析前必须构建统一长表

## 4.1 输出文件

请首先生成或检查：

```text
comparison_results/merged_common_samples.csv
```

如果数据量较大，可同时生成：

```text
comparison_results/merged_common_samples.parquet
```

## 4.2 长表字段要求

`merged_common_samples` 至少包含：

```text
valid_time
month
experiment_name
station
enable_blockage
candidate_power_col
pred_power_mw
actual_power_mw
actual_station_power_mw
limit_power_mw
is_curtailed
scope_name
wind_speed
wind_direction
maintenance_count
candidate_type
distance_m
error
abs_error
```

说明：

- `experiment_name` 应区分 `with_maintenance` 与 `without_maintenance`；
- `candidate_power_col` 为原始候选列；
- `candidate_type` 应自动解析，例如：
  - `pywake_internal`
  - `ws_eff_pywake_native`
  - `upstream_point`
  - `rotor_disc_upstream_mean`
  - `other`
- `distance_m` 应从候选列中自动解析；
- `pred_power_mw` 必须统一为 MW；
- 如果原始列为 `_kW`，必须先转换为 MW；
- `actual_power_mw` 应优先使用 `MZS_FAN_ACTIVE_POWER_SUM`；
- `scope_name` 应包含 `all_samples` 和 `not_curtailed` 或 `non_curtailed`；
- 如果某字段无法获取，请保留空列并在报告中说明原因。

## 4.3 时间交集要求

涉及横向比较时必须使用共同时间交集：

```text
with_maintenance valid_time
∩ without_maintenance valid_time
∩ measured timestamp
```

尤其是维护比较，不能用两组实验各自不同的时间范围。

---

# 5. 必须计算的评价指标

至少计算：

```text
n
MAE
RMSE
Bias
abs_bias
nMAE
nRMSE
R2
Corr
median_abs_error
p90_abs_error
energy_error_mwh
absolute_energy_error_mwh
```

如果已有脚本没有 median、p90、energy error，请补充。

## 5.1 归一化容量

需要明确 `nMAE` / `nRMSE` 的归一化容量 `P_norm`。可选：

- 场站额定容量；
- `MZS_LIMIT_POWER` 高分位；
- 实测功率 95 分位；
- 评价脚本已有定义。

请在结果报告和第 4 章中说明采用哪一种。  
如果代码中不同脚本不一致，请统一，并在 `Information Still Needed` 或第 4 章注释中标记。

## 5.2 能量误差

如果数据时间间隔为 15 min：

```text
energy_error_mwh = sum(pred_power_mw - actual_power_mw) * 0.25
absolute_energy_error_mwh = sum(abs(pred_power_mw - actual_power_mw)) * 0.25
```

如果时间间隔不同，请自动计算时间间隔，不要写死。

---

# 6. 第 4 章必须包含的分析

---

## 6.1 数据覆盖与样本构成

生成：

```text
comparison_results/time_coverage_summary.csv
comparison_results/measured_power_quality_check.csv
comparison_results/figures/01_time_coverage.png
```

第 4 章需要写：

- 两组实验各自时间范围；
- 实测数据时间范围；
- 共同时间交集；
- all_samples 样本数；
- not_curtailed 样本数；
- 限电样本比例；
- 维护缺失导致跳过的样本情况；
- 为什么后续比较使用共同时间交集。

注意：这部分是结果章节的“实验样本说明”，不要重复第 2 章所有数据来源。

---

## 6.2 单实验 ranking 概览

生成：

```text
comparison_results/single_experiment_evaluation/ranking_without_maintenance_overall.csv
comparison_results/single_experiment_evaluation/ranking_with_maintenance_overall.csv
comparison_results/single_experiment_evaluation/ranking_without_maintenance_monthly.csv
comparison_results/single_experiment_evaluation/ranking_with_maintenance_monthly.csv
```

第 4 章需要写：

- 不考虑维护实验内部 ranking；
- 考虑维护实验内部 ranking；
- overall 最优候选；
- `not_curtailed` 下最优候选；
- 月度最优是否稳定；
- 但必须强调：ranking 只是概览，不能直接证明维护或阻塞有效。

---

## 6.3 维护状态控制变量比较

生成：

```text
comparison_results/controlled_comparison/maintenance_controlled_overall.csv
comparison_results/controlled_comparison/maintenance_controlled_monthly.csv
comparison_results/controlled_comparison/maintenance_controlled_summary.csv
comparison_results/figures/02_maintenance_effect_by_month.png
```

比较时固定：

```text
valid_time common set
station
scope_name
period_type / month
enable_blockage
candidate_power_col
```

只改变：

```text
with_maintenance vs without_maintenance
```

必须统计并写入第 4 章：

- overall + not_curtailed 下总组合数；
- MAE 改善数量和比例；
- RMSE 改善数量和比例；
- nRMSE 改善数量和比例；
- |Bias| 改善数量和比例；
- 平均改善百分比；
- 中位改善百分比；
- 按月份改善情况；
- 维护风机数量与改善幅度是否相关；
- 改善最明显和恶化最明显的组合。

第 4 章表述重点：

> 维护状态修正是否改变模型评价结果，以及这种改变是否与维护风机数量和持续时间有关。

不要把维护写成模型创新，只写成运行状态一致性处理。

---

## 6.4 阻塞效应控制变量比较

生成：

```text
comparison_results/controlled_comparison/blockage_controlled_overall.csv
comparison_results/controlled_comparison/blockage_controlled_monthly.csv
comparison_results/controlled_comparison/blockage_controlled_summary.csv
comparison_results/figures/03_blockage_effect_summary.png
```

比较时固定：

```text
experiment_name
maintenance setting
candidate_power_col
scope_name
period_type / month
```

只改变：

```text
enable_blockage=False vs enable_blockage=True
```

必须统计并写入第 4 章：

- 在 `with_maintenance + not_curtailed` 下，总候选口径数；
- MAE 改善数量和比例；
- RMSE / nRMSE 改善数量和比例；
- |Bias| 改善数量和比例；
- 平均/中位 ΔMAE、ΔnRMSE、ΔBias；
- 分 candidate_type 的阻塞改善；
- 分距离段的阻塞改善；
- 分月份的阻塞改善；
- 分风速段 / 风向段的阻塞改善。

如果出现：

```text
平均阻塞改善，但最终 robust_score 推荐 blockage=False
```

必须解释原因，不允许直接简单推荐关闭阻塞。

---

## 6.5 等效入流风速口径总体表现

生成：

```text
comparison_results/candidate_analysis/robust_candidate_selection.csv
comparison_results/candidate_analysis/distance_error_curve.csv
comparison_results/figures/04_distance_vs_nrmse.png
comparison_results/figures/05_distance_vs_bias.png
```

分析条件建议主线使用：

```text
experiment_name = with_maintenance
scope_name = not_curtailed
```

同时比较：

```text
enable_blockage=False
enable_blockage=True
```

第 4 章需要写：

- 各类候选口径总体表现；
- PyWake internal、ws_eff_native、upstream point、rotor_disc mean 的差异；
- nRMSE 随距离变化趋势；
- Bias 随距离变化趋势；
- 是否存在 U 型、单调变化或距离带最优；
- rotor_disc mean 是否优于 upstream point；
- 最优距离是否集中于某个范围；
- 若最优为 160 m 或更远距离，需要说明其统计表现，并在讨论章节进一步解释其物理含义。

注意：本章可以报告“结果显示什么”，但较深入的物理解释可以留给第 5 章。

---

## 6.6 跨月份稳健性分析

生成：

```text
comparison_results/candidate_analysis/monthly_candidate_rank.csv
comparison_results/candidate_analysis/monthly_performance_summary.csv
comparison_results/figures/06_monthly_nrmse_heatmap.png
comparison_results/figures/07_candidate_rank_heatmap.png
```

必须计算：

```text
monthly_nrmse_mean
monthly_nrmse_std
monthly_nrmse_max
monthly_rank_mean
monthly_rank_std
top1_month_count
top3_month_count
top5_month_count
worst_month
worst_month_nrmse
stability_score
```

第 4 章需要写：

- 每个月最优候选是否一致；
- 月度最优是否存在波动；
- 哪些候选在多数月份保持前列；
- strict metric 最优候选；
- physically interpretable 候选或距离带；
- 不采用逐月自由选择最优口径的原因。

---

## 6.7 风速分箱分析

生成：

```text
comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv
comparison_results/figures/08_wind_speed_bin_performance.png
```

建议风速分箱：

```text
0–3
3–5
5–7
7–9
9–11
11–13
13+
```

也可根据样本分布调整，但必须说明。

第 4 章需要写：

- 每个风速段样本数；
- 各风速段最优候选；
- 哪些风速段误差最大；
- 阻塞效应在哪些风速段改善明显；
- 不同距离风速口径在哪些风速段差异明显；
- 是否存在低风速、高风速或额定附近系统性偏差。

---

## 6.8 风向分箱分析

生成：

```text
comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv
comparison_results/figures/09_wind_direction_bin_performance.png
```

如果存在风向字段，按 30° 或 45° 扇区分析。

第 4 章需要写：

- 每个风向扇区样本数；
- 哪些风向误差较大；
- 哪些风向阻塞改善明显；
- 最优等效风速口径是否随风向变化；
- 是否可能与风机阵列方向有关。

如果无法进行风向分析，请说明字段缺失或样本不足原因。

---

## 6.9 典型案例分析

请自动寻找至少 3 类连续时段案例：

1. 维护修正改善最明显的连续时段；
2. 阻塞开启改善最明显的连续时段；
3. 推荐口径与传统口径差异最明显的连续时段。

不要只给单个时间点。  
尽量找连续 6–24 小时的时段。

生成：

```text
comparison_results/case_studies/case_maintenance_improvement.csv
comparison_results/case_studies/case_blockage_improvement.csv
comparison_results/case_studies/case_candidate_difference.csv

comparison_results/figures/case_maintenance_improvement.png
comparison_results/figures/case_blockage_improvement.png
comparison_results/figures/case_candidate_difference.png
```

每个案例图至少包含：

- 实测功率；
- baseline 预测；
- proposed 预测；
- 误差；
- 风速；
- 风向；
- 维护台数；
- 限电状态。

第 4 章中案例分析要简洁，更多物理解释可留到第 5 章。

---

# 7. 第 4 章建议结构

请最终输出：

```text
paper_drafts/paper_draft_chapter_4.md
```

建议章节结构如下：

```markdown
# 4. Results

## 4.1 Sample Coverage and Evaluation Dataset

## 4.2 Overview of Single-Experiment Rankings

## 4.3 Effect of Maintenance-State Correction

## 4.4 Effect of Blockage

## 4.5 Performance of Equivalent Inflow Wind-Speed Definitions

## 4.6 Monthly Robustness of Candidate Wind-Speed Definitions

## 4.7 Wind-Speed-Dependent Performance

## 4.8 Wind-Direction-Dependent Performance

## 4.9 Case Studies

## 4.10 Summary of Main Findings
```

如果某些分析暂时无法完成，可保留小节并写 `TODO:`，但不能编造数值。

---

# 8. 第 4 章写作要求

1. 使用中文学术论文风格；
2. 结果章节要“展示和解释结果”，但不要像 Discussion 那样过度展开；
3. 每个小节必须引用对应 CSV 和图表路径；
4. 关键统计必须包含样本数；
5. 维护和阻塞必须使用控制变量比较；
6. 不要只比较各自最优模型；
7. 不要逐月自由选择最终模型；
8. 不要把辅助检查写成主结论；
9. 对矛盾结果必须说明，例如：
   - 阻塞平均改善，但 robust_score 推荐关闭；
   - 160 m 统计最优，但物理解释不如 50–70 m 清晰；
   - all_samples 与 not_curtailed 结论不一致；
10. 如果某些结果不稳定，应如实说明。

---

# 9. 第 4 章中建议使用的表格

至少建议生成以下表格草案并在正文引用：

```text
Table 9. Sample coverage and valid evaluation records.
Table 10. Overall ranking of candidate power definitions under each experiment.
Table 11. Controlled comparison of maintenance-state correction.
Table 12. Controlled comparison of blockage effect.
Table 13. Robustness ranking of equivalent inflow wind-speed definitions.
Table 14. Performance by wind-speed bins.
Table 15. Performance by wind-direction sectors.
Table 16. Summary of selected case studies.
```

表格可在 Markdown 中放简化版，完整结果以 CSV 路径引用。

---

# 10. 第 4 章中建议使用的图

至少建议生成并引用：

```text
Figure 8. Time coverage and common evaluation samples.
Figure 9. Monthly effect of maintenance-state correction.
Figure 10. Overall effect of blockage on nRMSE and Bias.
Figure 11. Distance-dependent nRMSE for upstream point and rotor-disc averaged definitions.
Figure 12. Distance-dependent Bias for upstream point and rotor-disc averaged definitions.
Figure 13. Monthly nRMSE heatmap of candidate wind-speed definitions.
Figure 14. Wind-speed-bin performance.
Figure 15. Wind-direction-sector performance.
Figure 16. Case study of maintenance-state correction.
Figure 17. Case study of blockage effect.
Figure 18. Case study of candidate wind-speed definition.
```

图表文件建议存放：

```text
comparison_results/figures/
```

---

# 11. 输出前自查清单

在提交 `paper_drafts/paper_draft_chapter_4.md` 前，请 Copilot 自查：

- [ ] 是否先生成了必要的 CSV 和图；
- [ ] 是否构建了共同样本数据集；
- [ ] 是否统一预测功率和实测功率单位为 MW；
- [ ] 是否明确主评价目标是 `MZS_FAN_ACTIVE_POWER_SUM` 或实际字段；
- [ ] 是否区分 `all_samples` 和 `not_curtailed`；
- [ ] 是否每个关键统计都有样本数；
- [ ] 是否维护比较控制了 blockage 和 candidate；
- [ ] 是否阻塞比较控制了 maintenance 和 candidate；
- [ ] 是否候选风速口径比较控制了 maintenance 和 blockage；
- [ ] 是否解释了月度最优不稳定问题；
- [ ] 是否避免逐月自由选择最终模型；
- [ ] 是否对矛盾结果做了说明；
- [ ] 是否没有编造不存在的数值；
- [ ] 是否所有图表和 CSV 路径真实存在；
- [ ] 是否第 4 章没有重复第 2/3 章的大量方法内容；
- [ ] 是否没有写成第 5 章讨论。

---

# 12. 推荐给 Copilot 的启动指令

将本文件放入仓库后，请对 Copilot 发送：

```text
请阅读 COPILOT_WRITE_CHAPTER_4_REQUEST.md，以及 paper_drafts/paper_draft_chapter_2.md 和 paper_drafts/paper_draft_chapter_3.md。现在开始完成论文第 4 章 Results。请先生成支撑结果章节的 comparison_results CSV 和 figures，再撰写 paper_drafts/paper_draft_chapter_4.md。不要只写泛泛总结，不要只比较各自最优 ranking。维护、阻塞和候选风速口径分析必须采用控制变量比较。无法确认或无法完成的内容请用 TODO 标注，不要编造。
```
