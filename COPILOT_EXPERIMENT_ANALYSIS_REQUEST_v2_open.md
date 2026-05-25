# Copilot 实验分析说明：尾流-阻塞模型与等效入流风速适配性研究

> 本文档用于帮助 Copilot 快速理解当前仓库中的实验背景、数据结构、已有输出和分析目标。  
> 请在阅读代码和数据后，优先基于实际文件内容自行梳理分析路径；本文档只提供研究意图、关键变量和希望回答的问题，不要求严格照搬某一种固定分析流程。

---

## 1. 研究背景

当前研究对象是 JMZSFD 海上风电场的场站级功率模拟问题。

前期基于激光雷达观测发现：

1. 海上风电场附近流场中存在阻塞效应，风机群运行会影响上游及场内风速分布；
2. 不同空间位置、不同上游距离的风速与场站功率曲线的适配性不同；
3. 传统尾流模型如果只考虑尾流亏损，而不考虑阻塞效应和等效入流风速位置，可能存在系统性偏差。

因此，当前工作的核心目标不是单纯比较两个输出文件，而是希望系统分析：

- 阻塞效应是否能改善传统尾流模型的功率模拟效果；
- 维护状态修正是否是必要的数据一致性处理；
- 哪一种等效入流风速口径更适合输入功率曲线；
- 不同月份、不同风速范围、不同风向/工况下，模型表现是否存在差异；
- 是否可以形成一个具有跨月份稳定性的模型方案，而不是每个月单独挑最优口径。

---

## 2. 当前已有实验

目前已经基于同一个气象输入文件运行了两组实验。

### 2.1 考虑维护状态实验

```bash
python run_five_experiments_维护缺失默认跳过版.py \
  --forecast-csv 场站气象预报\wind_lat_33.250_lon_121.500-UTC8.csv \
  --maintenance-matrix JMZSFD维护记录\jmzsfd_maintenance_matrix.csv \
  --output-dir five_experiments_output_考虑维护-全月份
```

该实验会读取维护矩阵。若某一时刻维护矩阵缺失，则该时刻跳过。维护风机不应作为正常运行风机参与功率汇总，也不应作为正常运行机组参与尾流/阻塞计算。

### 2.2 不考虑维护状态实验

```bash
python run_five_experiments_维护缺失默认跳过版.py \
  --forecast-csv 场站气象预报\wind_lat_33.250_lon_121.500-UTC8.csv \
  --output-dir five_experiments_output_不考虑维护-全月份
```

该实验不使用维护矩阵，默认所有风机均按正常运行处理。

---

## 3. 主要输出文件

请优先检查两个实验输出目录中的以下文件：

```text
five_experiments_output_考虑维护-全月份/
  all_experiments_station_power_timeseries.csv

five_experiments_output_不考虑维护-全月份/
  all_experiments_station_power_timeseries.csv
```

其中 `all_experiments_station_power_timeseries.csv` 是后续分析的核心模型输出表。一般包含：

- `valid_time`
- `station`
- `enable_blockage`
- 多个 `station_power_*_MW` 候选功率列
- 可能包含维护台数、风速、风向或其他辅助字段

请以实际 CSV 字段为准，自动识别所有 `station_power_*_MW` 列。

---

## 4. 实测数据来源与评价目标

仓库中有脚本：

```text
获取风机功率之和用于尾流比较.py
```

该脚本用于从原始场站-风机分钟级宽表中提取场站级轻量 CSV。

原始实测数据大致包括：

```text
timestamp
ACTIVE_POWER_STATION
LIMIT_POWER
ACTIVE_POWER_#1 ... ACTIVE_POWER_#58
WINDSPEED_#1 ... WINDSPEED_#58
STATUS_#1 ... STATUS_#58
```

提取后的核心字段大致包括：

```text
timestamp
JMZS_ACTIVE_POWER_STATION
JMZS_LIMIT_POWER
JMZS_FAN_ACTIVE_POWER_SUM
JMZS_FAN_WINDSPEED_MEAN
```

其中：

- `JMZS_ACTIVE_POWER_STATION`：原始场站总有功功率；
- `JMZS_LIMIT_POWER`：限电值；
- `JMZS_FAN_ACTIVE_POWER_SUM`：所有非维护风机的有功功率加和；
- `JMZS_FAN_WINDSPEED_MEAN`：所有非维护风机的平均风速。

主评价目标建议优先使用：

```text
JMZS_FAN_ACTIVE_POWER_SUM
```

原因是模型端考虑维护时，预测对象是非维护运行风机；实测端也应使用非维护风机功率加和，保证预测功率与实测功率统计口径一致。

但也建议检查：

```text
JMZS_ACTIVE_POWER_STATION - JMZS_FAN_ACTIVE_POWER_SUM
```

用于判断场站总功率和风机加和之间是否存在显著差异。

---

## 5. 希望 Copilot 重点回答的研究问题

请 Copilot 在理解仓库代码、输出数据和字段含义后，自行设计分析脚本和图表。下面这些问题是希望最终回答的方向，而不是固定流程。

### Q1. 两组实验的数据覆盖是否一致？

需要检查：

- 考虑维护实验有多少个 `valid_time`；
- 不考虑维护实验有多少个 `valid_time`；
- 两者与实测数据共同匹配的时间有多少；
- 考虑维护实验中因维护矩阵缺失而跳过的时间是否会影响比较；
- 后续所有横向比较是否应限定在共同时间交集上。

### Q2. 维护状态修正是否有效？

请注意控制变量。

比较“考虑维护”和“不考虑维护”时，应尽量固定：

- `valid_time` 范围；
- `station`;
- `enable_blockage`;
- `candidate_power_col`;
- 样本范围，例如 all samples / non-curtailed samples；
- 月份或其他分组条件。

只改变是否引入维护矩阵。

希望判断：

- 在相同功率口径下，考虑维护是否降低 MAE / RMSE / nRMSE；
- 是否降低系统性偏差 Bias；
- 改善是否集中在维护风机数量较多的月份；
- 维护状态修正是否只是数据一致性处理，还是对结果影响显著。

### Q3. 阻塞效应是否有效？

比较 `enable_blockage=False` 与 `enable_blockage=True` 时，也需要控制变量。

应尽量固定：

- 是否考虑维护；
- `candidate_power_col`;
- 样本范围；
- 月份/风速段/风向段。

希望判断：

- 开启阻塞后，误差是否普遍降低；
- 阻塞是否主要改善 Bias；
- 阻塞效果在哪些风速范围或风向工况下最明显；
- 阻塞对不同等效风速口径的影响是否一致。

### Q4. 哪个等效入流风速口径最适合功率曲线？

这是当前最核心但也最不确定的问题。

仓库中模型输出包含多个 `station_power_*_MW` 候选功率列，这些列可能对应：

- PyWake 内部有效风速功率；
- 上游固定距离风速输入功率曲线；
- 转子圆盘上游不同距离平均风速输入功率曲线；
- 其他候选口径。

希望 Copilot 自动识别候选列，并分析：

- 哪些口径整体表现最好；
- 单点上游风速与转子圆盘上游平均风速哪个更稳健；
- 最优距离是否集中在某个距离带；
- 是否存在单月最优不稳定的问题；
- 是否可以推荐一个跨月份稳定的固定口径，或推荐一个距离带而不是单一距离。

不要只输出“overall 第一名”。需要关注跨月份稳定性和泛化能力。

### Q5. 模型效果是否随风速范围变化？

希望进一步按风速分箱分析模型表现。

可考虑使用：

- ERA5/预报输入风速；
- 模型输出中的自由来流风速；
- `JMZS_FAN_WINDSPEED_MEAN`;
- 其他仓库中存在的风速字段。

请根据实际数据判断最合适的分箱变量。

可探索的分箱方式：

```text
0–3 m/s
3–5 m/s
5–7 m/s
7–9 m/s
9–11 m/s
11–13 m/s
13+ m/s
```

也可以根据功率曲线关键区间或样本分布自行调整。

希望判断：

- 尾流-阻塞模型在哪些风速段改善明显；
- 不同距离风速口径是否在不同风速段表现不同；
- 是否存在低风速、高风速或额定附近的系统性偏差。

### Q6. 模型效果是否随风向变化？

如果输出或气象数据中有风向字段，希望按风向扇区分析，或根据风电场主导风向、风机排布方向自定义分组。

希望判断：

- 某些风向下尾流/阻塞效果是否更明显；
- 最优等效风速距离是否受风向影响；
- 是否存在明显的阵列方向效应。

### Q7. 是否需要典型案例分析？

建议 Copilot 自动寻找若干典型时段，例如：

- 维护风机数量多且考虑维护改善明显的时段；
- 阻塞开启前后误差差异最大的时段；
- 不同风速口径差异显著的时段；
- 预测明显高估或低估的异常时段。

对这些时段绘制时间序列图，帮助解释整体统计结果背后的物理原因。

---

## 6. 建议生成的分析结果

以下输出是建议，不要求完全照搬。Copilot 可以根据实际数据结构优化。

```text
comparison_results/
  time_coverage_summary.csv
  measured_power_quality_check.csv
  candidate_columns_detected.csv

single_experiment_evaluation/
  ranking_no_maintenance_overall.csv
  ranking_maintenance_overall.csv
  ranking_no_maintenance_monthly.csv
  ranking_maintenance_monthly.csv

controlled_comparison/
  maintenance_controlled_overall.csv
  maintenance_controlled_monthly.csv
  blockage_controlled_overall.csv
  blockage_controlled_monthly.csv

candidate_analysis/
  robust_candidate_selection.csv
  monthly_candidate_rank.csv
  distance_error_curve.csv
  candidate_performance_by_wind_speed_bin.csv
  candidate_performance_by_wind_direction_bin.csv

figures/
  distance_vs_nrmse.png
  distance_vs_bias.png
  monthly_nrmse_heatmap.png
  blockage_effect_summary.png
  maintenance_effect_by_month.png
  wind_speed_bin_performance.png
  wind_direction_bin_performance.png
  case_timeseries_*.png
```

如果条件允许，也可以输出 Plotly HTML，便于鼠标悬停查看时间、功率、误差和维护台数。

---

## 7. 评价指标建议

至少计算：

```text
n
MAE
RMSE
Bias
nMAE
nRMSE
R2
Corr
```

建议额外计算：

```text
abs_bias
median_abs_error
p90_abs_error
mean_error
energy_error_mwh
```

15 min 数据可用：

```text
energy_error_mwh = sum(pred_mw - actual_mw) * 0.25
absolute_energy_error_mwh = sum(abs(pred_mw - actual_mw)) * 0.25
```

如果实际数据是 1 min，需要根据时间分辨率调整。

归一化容量 `capacity_mw` 可以用以下方式之一：

- 场站额定容量；
- 实测功率 95 分位数；
- `JMZS_LIMIT_POWER` 的高分位数；
- 由代码中已有设置决定。

请在脚本输出中明确记录采用的归一化基准。

---

## 8. 分析原则

1. **控制变量优先**  
   不要只比较两个实验各自的最佳结果。比较维护、阻塞、风速口径时，都应尽量固定其他变量。

2. **共同时间范围优先**  
   考虑维护实验可能因为维护矩阵缺失而跳过部分时刻，横向比较应使用共同时间交集。

3. **非限电样本作为主评价**  
   限电会使实际功率低于可发功率，不完全反映尾流模型能力。建议同时输出 all samples 和 non-curtailed samples，但主结论优先基于 non-curtailed。

4. **不要逐月自由选择最终模型**  
   月度最优口径可以分析，但最终推荐应基于跨月份稳健性，而不是每个月单独挑一个最优距离。

5. **保留探索空间**  
   除上述建议外，请 Copilot 主动检查数据字段、异常值、时间对齐、功率单位、风速单位和潜在更好的分组方式。如果发现更合理的分析路径，可以补充新的脚本和结论。

---

## 9. 希望最终形成的结论方向

最终希望通过数据分析回答：

1. 维护状态修正是否显著影响模型验证结果；
2. 阻塞效应是否能在相同功率口径下降低误差；
3. 哪类等效入流风速口径最适合功率曲线；
4. 最优风速距离是否具有跨月份稳定性；
5. 模型改善是否与风速范围、风向、维护数量等工况有关；
6. 是否可以形成一个推荐模型组合，例如：

```text
考虑维护状态
+ 开启阻塞效应
+ 采用某个稳健等效入流风速口径或距离带
```

请 Copilot 在分析过程中尽量生成可复现脚本，并在每个结果 CSV 中保留足够的中间字段，方便后续人工检查和论文制图。

---

## 10. 代码风格与复现要求

希望新增脚本尽量满足：

- 使用 `argparse` 支持输入输出路径；
- 自动识别 `station_power_*_MW` 候选列；
- 自动处理时间列格式，统一为无时区本地时间；
- 输出 CSV 使用 `utf-8-sig` 编码；
- 对关键步骤打印样本数、共同时间范围、限电样本数等日志；
- 避免覆盖原始输出；
- 所有新结果输出到独立目录，例如 `comparison_results/`。

---

## 11. 建议 Copilot 首先阅读/检查的文件

请优先检查仓库中的以下内容：

```text
run_five_experiments_维护缺失默认跳过版.py
获取风机功率之和用于尾流比较.py
five_experiments_output_考虑维护-全月份/all_experiments_station_power_timeseries.csv
five_experiments_output_不考虑维护-全月份/all_experiments_station_power_timeseries.csv
JMZSFD维护记录/jmzsfd_maintenance_matrix.csv
场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv
```

如果仓库中已有评价脚本，例如：

```text
evaluate_station_power_accuracy_multi_station.py
evaluate_station_power_accuracy_multi_station_monthly_combined.py
```

也请阅读并尽量复用其中的指标计算逻辑，但不要受限于原 ranking 输出。新的分析重点是控制变量比较和稳健性分析。

---

## 12. 最重要的一句话

本项目当前不是要简单找“哪个实验排名第一”，而是要在实测运行数据约束下，系统判断：

> 阻塞效应、维护状态修正、以及不同空间距离风速口径分别对海上风电场尾流功率模拟精度产生了什么影响，并找出具有跨月份稳定性的等效入流风速方案。

## 13. 输出要求

最终需要形成一份完整的分析报告，输出为 Markdown 文件，例如：

```text
comparison_results/analysis_report.md
