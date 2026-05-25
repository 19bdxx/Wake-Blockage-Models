# Copilot 任务说明：海上风电场尾流-阻塞功率模拟论文第 2 章数据章节撰写

> 建议将本文档放在 GitHub 仓库根目录，文件名可设为：  
> `COPILOT_WRITE_CHAPTER_2_REQUEST.md`
>
> 本文档不是让 Copilot 做一次普通的数据分析，而是让 Copilot 先理解整个研究项目背景，然后基于仓库中的完整代码、数据文件和实验输出，撰写一篇期刊论文中的 **第 2 章 Study Site and Data**。  
>
> 本次任务只写第 2 章，不写第 3 章方法，不写第 4 章结果，也不做模型效果分析。

---

# 0. Copilot 需要先理解的项目背景

当前仓库对应一个海上风电场尾流建模与功率模拟研究项目。研究对象为仓库中标记为 `MZS` / `JMZSFD` 的海上风电场。项目中已经包含：

- 风机布局和机组参数；
- 功率曲线与推力曲线；
- 场站附近气象输入；
- 风机级 SCADA 实测功率、风速、状态数据；
- 维护状态矩阵；
- 基于 PyWake / 尾流模型的模型运行脚本；
- 两组模型实验输出；
- 用于从原始 SCADA 数据中提取实测功率对照量的脚本。

本研究最终计划整理成一篇关于海上风电场尾流-阻塞功率模拟的期刊论文。论文不是单纯的软件说明，也不是简单比较两个 CSV 文件，而是围绕以下科学/工程问题展开：

1. 海上风电场中传统尾流模型是否需要考虑阻塞效应；
2. 不同空间位置、不同上游距离的风速与风机/场站功率曲线的适配性是否不同；
3. 哪类等效入流风速口径更适合用于场站功率模拟；
4. 在真实场站运行数据验证时，如何处理维护停机、限电和异常值，保证模型预测对象与实测功率统计对象一致。

前期研究中，激光雷达观测提示：风电场附近流场不仅存在下游尾流亏损，也可能存在风机群对上游来流的阻塞影响；同时，不同距离、不同空间位置的风速与功率曲线之间的匹配程度不同。因此，后续模型实验围绕两个方向展开：

- 在传统尾流模型中引入/开启阻塞效应；
- 比较不同等效入流风速口径，例如上游固定距离风速、转子圆盘上游平均风速等。

仓库中已经运行了两个主要模型实验：

1. **考虑维护状态实验**：模型读取维护矩阵，在每个时刻剔除维护风机；
2. **不考虑维护状态实验**：模型默认所有风机均正常运行。

每个实验内部又包含：

- `enable_blockage=False`
- `enable_blockage=True`

并且输出多个 `station_power_*` 候选功率列，对应不同等效入流风速口径。

---

# 1. 本次任务目标

请 Copilot 基于仓库实际内容撰写论文第 2 章：

```markdown
# 2. Study Site and Data
```

最终输出文件：

```text
paper_drafts/paper_draft_chapter_2.md
```

第 2 章的作用是：

- 交代研究场站；
- 交代风机布局与机型参数；
- 交代激光雷达观测在本文中的角色；
- 交代气象输入；
- 交代 SCADA 实测数据；
- 交代实测功率对照量如何构建；
- 交代维护矩阵；
- 交代限电样本如何识别；
- 交代不同数据源的时间范围、时间分辨率和对齐原则；
- 为后续第 3 章方法和第 4 章结果分析打基础。

请注意：第 2 章不是分析模型结果，不需要回答哪个模型更好。

---

# 2. 本次任务不要做什么

请不要写以下内容：

- 不要写第 3 章 Methodology；
- 不要写尾流模型公式；
- 不要写 PyWake 详细模型配置；
- 不要写阻塞模型计算方法；
- 不要写模型效果改善了多少；
- 不要比较维护和不维护哪个更好；
- 不要比较 blockage on/off 哪个更好；
- 不要推荐最优等效风速距离；
- 不要写论文结论；
- 不要编造仓库中没有的信息。

第 2 章可以简要说明“这些数据将用于后续模型验证”，但不要展开结果分析。

---

# 3. 写作输出要求

请生成：

```text
paper_drafts/paper_draft_chapter_2.md
```

建议结构如下：

```markdown
# 2. Study Site and Data

## 2.1 Study Site and Wind Farm Layout

## 2.2 Lidar Observation and Research Motivation

## 2.3 Meteorological Input Data

## 2.4 SCADA Power and Turbine Operational Data

## 2.5 Maintenance Matrix

## 2.6 Curtailment Identification and Sample Filtering

## 2.7 Time Alignment and Common Evaluation Period

## 2.8 Summary of Data Sources

# Information Still Needed

# Suggested Figures and Tables
```

如果 Copilot 根据仓库实际情况认为小节标题需要微调，可以调整，但必须保持“只写第 2 章数据部分”的边界。

---

# 4. 写作风格要求

1. 使用中文学术论文风格，接近期刊论文初稿；
2. 正文应有连贯叙述，不要只堆 bullet list；
3. 每节需要结合仓库中的实际文件、字段和处理逻辑；
4. 文件名、字段名、单位、时间范围必须以仓库实际内容为准；
5. 如果本文档中的示例字段和仓库实际字段不一致，以仓库实际字段为准；
6. 如果无法从仓库确认某个信息，请写 `TODO:`，不要编造；
7. 如果发现单位存在 `_kW` 与 `_MW` 混用，必须在文中说明并标记需要统一；
8. 章节末尾必须列出：
   - `Information Still Needed`
   - `Suggested Figures and Tables`
9. 不要把维护状态修正写成论文主要创新点，它是用于保证模型预测对象与实测功率统计对象一致的数据处理步骤；
10. 不要把激光雷达写成后续所有模型计算的唯一输入，除非仓库代码确实如此。当前更合适的表述是：激光雷达观测为阻塞效应和风速代表性问题提供研究动机。

---

# 5. 请优先阅读的仓库文件

请 Copilot 在写作前先阅读以下文件。不要只根据本文档泛泛写作。

---

## 5.1 风机布局、机型参数和功率/推力曲线

请查找并阅读类似以下文件：

```text
风机布局及功率推力曲线/turbine_layout.csv
风机布局及功率推力曲线/turbine_data.csv
```

以及相关代码：

```text
pywake_integration/wind_farm_setup.py
pywake_integration/turbine_model.py
run_five_experiments_维护缺失默认跳过版.py
```

请从中提取并写入第 2.1 节：

- 场站名称；
- 风机数量；
- 风机编号；
- 风机坐标；
- 经纬度范围或平面坐标范围；
- 风机类型；
- 额定功率；
- 轮径；
- 轮毂高度；
- 功率曲线来源；
- 推力曲线来源；
- 建模中如何映射机型和风机编号。

如果无法确认某些信息，请写：

```text
TODO: 补充风机型号、额定功率、轮径或轮毂高度等信息。
```

---

## 5.2 激光雷达相关数据或说明

请在仓库中搜索是否存在激光雷达数据、图片或说明文件。

可搜索关键词：

```text
lidar
Lidar
激光雷达
雷达
测风
扫描
阻塞
blockage
```

如果找到相关文件，请在第 2.2 节结合实际文件描述：

- 激光雷达观测位置；
- 观测时段；
- 观测变量；
- 时间分辨率；
- 空间分辨率；
- 观测到的阻塞或空间风速差异现象；
- 这些观测如何引出本文后续模型问题。

如果仓库中没有完整激光雷达文件，请不要编造仪器型号和观测细节。请写：

```text
TODO: 补充激光雷达观测文件、观测时段、仪器参数和典型流场图。
```

建议表述：

> 激光雷达观测在本文中主要用于揭示风电场周边流场结构特征，并为阻塞效应与等效入流风速口径分析提供物理动机，而不是作为后续所有时刻模型计算的唯一输入。

---

## 5.3 气象输入数据

请阅读：

```text
场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv
```

以及主运行脚本中读取该文件的部分。

请确认并写入第 2.3 节：

- 数据来源：ERA5、EC 预报或其他；若无法确认请写 TODO；
- 文件时间字段；
- 风速字段；
- 风向字段；
- u/v 分量字段；
- 经纬度；
- 时间分辨率；
- 时间范围；
- 是否为 UTC+8；
- 是否有插值标记，例如 `is_interpolated`；
- 所有模型实验是否使用同一个气象输入文件。

重要：  
如果无法确认气象数据来源，不要混写 ERA5 和 EC。请写：

```text
TODO: 需要人工确认 wind_lat_33.250_lon_121.500-UTC8.csv 的数据来源。
```

建议说明：

> 两组模型实验共享同一气象输入，因此后续模型差异可主要归因于维护处理、阻塞设置和等效入流风速口径，而非气象驱动差异。

---

## 5.4 原始 SCADA 与实测功率提取脚本

请阅读：

```text
获取风机功率之和用于尾流比较.py
```

以及该脚本生成的轻量实测 CSV，例如：

```text
JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv
```

或仓库中类似命名文件。

请重点确认并写入第 2.4 节：

原始数据字段是否包括：

```text
timestamp
ACTIVE_POWER_STATION
LIMIT_POWER
ACTIVE_POWER_#1 ... ACTIVE_POWER_#58
WINDSPEED_#1 ... WINDSPEED_#58
STATUS_#1 ... STATUS_#58
```

轻量输出字段是否包括：

```text
timestamp
JMZS_ACTIVE_POWER_STATION / MZS_ACTIVE_POWER_STATION
JMZS_LIMIT_POWER / MZS_LIMIT_POWER
JMZS_FAN_ACTIVE_POWER_SUM / MZS_FAN_ACTIVE_POWER_SUM
JMZS_FAN_WINDSPEED_MEAN / MZS_FAN_WINDSPEED_MEAN
```

请详细解释实测功率和的构造方法：

- `99999` 如何处理；
- `STATUS_#i == 6` 的含义；
- 非维护风机如何筛选；
- 状态为空或异常时如何处理；
- 单机负功率是否裁剪为 0；
- 所有非维护风机功率如何求和；
- 是否进行了 kW → MW 转换；
- 风机平均风速如何计算；
- 为什么主评价对象选择非维护风机功率和，而不是只用场站总功率。

建议公式：

```text
P_meas(t) = Σ max(0, P_i(t)), i ∈ A_obs(t)
```

其中：

```text
A_obs(t) = {i | STATUS_#i(t) is valid and STATUS_#i(t) != 6}
```

如仓库实际逻辑不同，请以代码为准。

---

## 5.5 维护矩阵

请阅读：

```text
JMZSFD维护记录/jmzsfd_maintenance_matrix.csv
```

以及主运行脚本中接入维护矩阵的代码。

请确认并写入第 2.5 节：

- 维护矩阵时间字段；
- 风机列命名方式；
- 维护状态取值含义；
- 维护矩阵时间分辨率；
- 与模型 `valid_time` 如何匹配；
- 维护缺失时刻如何处理；
- 维护风机在模型端如何处理；
- 维护风机是否从尾流/阻塞计算中剔除；
- 考虑维护实验和不考虑维护实验的区别。

注意：  
本章只需要说明维护数据和处理原则，不要展开维护修正带来的误差改善结果。

---

## 5.6 限电数据与样本筛选

请阅读评价脚本，例如：

```text
evaluate_station_power_accuracy_multi_station.py
evaluate_station_power_accuracy_multi_station_monthly_combined.py
```

或仓库中的实际评价脚本。

请确认并写入第 2.6 节：

- 限电字段名称；
- 限电字段单位；
- 限电阈值；
- 是否使用 `LIMIT_POWER < rated_capacity * 0.95`；
- `rated_capacity` 或归一化容量如何设定；
- all samples 与 non-curtailed samples 如何区分；
- 为什么尾流模型主评价应优先使用 non-curtailed samples。

如果阈值或容量基准不统一，请写：

```text
TODO: 需要统一限电识别阈值和归一化容量定义。
```

---

## 5.7 两组模型输出与时间范围

请检查以下两个文件：

```text
five_experiments_output_考虑维护-全月份/all_experiments_station_power_timeseries.csv
five_experiments_output_不考虑维护-全月份/all_experiments_station_power_timeseries.csv
```

请在第 2.7 节写明：

- 考虑维护实验 `valid_time` 范围；
- 不考虑维护实验 `valid_time` 范围；
- 实测数据时间范围；
- 维护矩阵时间范围；
- 气象输入时间范围；
- 共同评价时间范围；
- 为什么后续横向比较必须使用共同时间交集。

如果已有 `time_coverage_summary.csv`，可引用其中信息。  
如果没有，请 Copilot 可用脚本快速读取 CSV 统计时间范围和样本数，但不要在第 2 章写模型效果，只写数据覆盖和对齐原则。

---

# 6. 第 2 章具体写作要求

---

## 6.1 2.1 Study Site and Wind Farm Layout

这一节应包含：

- 研究场站名称；
- 海上风电场属性；
- 风机数量；
- 风机编号范围；
- 风机空间分布；
- 风机类型；
- 主要机组参数；
- 研究时间范围；
- 后续建模对象是场站级功率。

建议写作逻辑：

1. 先介绍研究对象；
2. 再介绍风机数量和布局；
3. 再介绍机型和参数；
4. 最后说明这些信息如何用于尾流模型。

建议加入表格草案：

```markdown
Table 1. Basic information of the wind farm and turbine types.

| Item | Value | Source file | Notes |
|---|---|---|---|
| Wind farm | TODO/MZS/JMZSFD | turbine_layout.csv | TODO |
| Number of turbines | 58 | turbine_layout.csv | Turbine IDs #1–#58 |
| Turbine types | TODO | turbine_data.csv | TODO |
| Rotor diameter | TODO | turbine_data.csv | TODO |
| Hub height | TODO | turbine_data.csv | TODO |
| Rated power | TODO | turbine_data.csv | TODO |
```

---

## 6.2 2.2 Lidar Observation and Research Motivation

这一节应说明：

- 激光雷达观测是本文研究问题的来源；
- 它提示风电场存在阻塞效应；
- 它提示不同上游距离风速与功率曲线适配性不同；
- 后文将基于模型实验验证这些问题；
- 如果数据缺失，用 TODO 标注。

建议避免写成：

```text
本文使用激光雷达数据作为所有模型输入。
```

建议写成：

```text
激光雷达观测在本文中主要用于揭示风电场周边流场结构特征，并为阻塞效应与等效入流风速口径分析提供物理动机。
```

---

## 6.3 2.3 Meteorological Input Data

这一节应包含：

- 气象输入文件；
- 数据来源；
- 坐标；
- 时间分辨率；
- 时间范围；
- 变量；
- 时间区；
- 插值标记；
- 所有实验共享该气象输入。

建议加入表格草案：

```markdown
Table 2. Meteorological variables used in wake simulations.

| Variable | Meaning | Unit | Used for |
|---|---|---|---|
| valid_time | timestamp | TODO | Time alignment |
| wind_speed | wind speed | m/s | Wake simulation input |
| wind_direction | wind direction | degree | Wake simulation input |
| u100 | zonal wind component | m/s | Derived wind speed/direction |
| v100 | meridional wind component | m/s | Derived wind speed/direction |
| is_interpolated | interpolation flag | - | Data quality flag |
```

---

## 6.4 2.4 SCADA Power and Turbine Operational Data

这一节是第 2 章重点之一，需要写得具体。

必须解释：

```text
MZS_FAN_ACTIVE_POWER_SUM
```

或实际字段名。

建议正文包含：

- 原始 SCADA 宽表结构；
- 58 台风机逐机功率、风速、状态；
- 场站总有功功率；
- 限电字段；
- 轻量表构建逻辑；
- 主实测评价对象；
- 与模型预测对象保持一致的原因。

建议给出简化公式：

```text
P_meas(t) = Σ max(0, P_i(t)), i ∈ A_obs(t)
```

其中：

```text
A_obs(t) = {i | STATUS_#i(t) != 6 and STATUS_#i(t) is valid}
```

并说明 `99999` 作为无效值不参与计算。

---

## 6.5 2.5 Maintenance Matrix

这一节应包含：

- 维护矩阵文件；
- 时间字段；
- 风机维护状态列；
- 维护状态取值；
- 与模型时间对齐；
- 维护缺失时刻处理；
- 维护风机从模型可运行集合中剔除；
- 维护风机不作为尾流/阻塞源；
- 不考虑维护实验默认所有风机运行。

建议写成数据处理逻辑，而不是结果结论。

---

## 6.6 2.6 Curtailment Identification and Sample Filtering

这一节应包含：

- 限电字段；
- 限电判定规则；
- all samples 和 non-curtailed samples；
- 为什么限电会影响模型评价；
- 主结论优先基于 non-curtailed。

不要写具体模型哪个更好，只写评价样本如何构建。

---

## 6.7 2.7 Time Alignment and Common Evaluation Period

这一节应包含：

- 气象数据为 15 min；
- SCADA 和维护矩阵可能为 1 min；
- 模型输出为 15 min；
- 时间统一为 UTC+8 或本地时间；
- 维护矩阵缺失会导致维护实验跳过部分时刻；
- 比较两个实验时必须使用共同时间交集。

如果能从仓库中统计具体时间范围和样本数，可以写；否则标 TODO。

---

## 6.8 2.8 Summary of Data Sources

请生成表格：

```markdown
Table 3. Summary of data sources used in this study.

| Data type | File | Time range | Resolution | Key variables | Purpose |
|---|---|---|---|---|---|
| Wind farm layout | TODO | - | - | turbine id, coordinates | Wake model setup |
| Turbine data | TODO | - | - | power curve, Ct curve, D, H | Turbine model |
| Meteorological input | TODO | TODO | 15 min | wind_speed, wind_direction | Wake model forcing |
| SCADA raw data | TODO | TODO | TODO | active power, wind speed, status | Measured reference |
| Maintenance matrix | TODO | TODO | TODO | turbine maintenance flags | Operational-state correction |
| Model outputs | TODO | TODO | 15 min | station_power_* | Model evaluation |
```

---

# 7. 最终文件末尾必须包含

## 7.1 Information Still Needed

请列出所有无法确认但论文需要补充的信息，例如：

- 激光雷达仪器型号；
- 激光雷达观测时间；
- 激光雷达空间/时间分辨率；
- 气象数据来源；
- 风机额定容量；
- 功率曲线/推力曲线来源；
- 限电阈值；
- 归一化容量定义；
- 场站实际名称是否统一为 MZS/JMZSFD。

## 7.2 Suggested Figures and Tables

请列出建议图表，例如：

```markdown
## Suggested Figures

- Figure 1. Layout of the JMZSFD offshore wind farm and turbine indexing.
- Figure 2. Lidar-observed flow features motivating blockage-aware wake modeling.
- Figure 3. Workflow for constructing measured power reference from turbine-level SCADA data.
- Figure 4. Time coverage of meteorological input, maintenance matrix, SCADA data and model outputs.

## Suggested Tables

- Table 1. Basic information of the wind farm and turbine types.
- Table 2. Meteorological input variables.
- Table 3. SCADA-derived validation variables.
- Table 4. Maintenance and curtailment treatment rules.
- Table 5. Summary of data sources.
```

---

# 8. Copilot 输出前自查清单

在提交 `paper_drafts/paper_draft_chapter_2.md` 前，请 Copilot 自查：

- [ ] 是否只写了第 2 章，没有写第 3 章；
- [ ] 是否使用仓库实际文件名；
- [ ] 是否明确了风机数量；
- [ ] 是否明确了气象输入字段；
- [ ] 是否说明了实测功率和的构造逻辑；
- [ ] 是否说明了维护矩阵；
- [ ] 是否说明了限电样本处理；
- [ ] 是否说明了时间对齐；
- [ ] 是否把无法确认的信息标记为 TODO；
- [ ] 是否没有编造激光雷达细节；
- [ ] 是否没有写模型结果分析；
- [ ] 是否列出了建议图表和仍需补充信息。

---

# 9. 推荐给 Copilot 的启动指令

将本文件放入仓库后，请对 Copilot 发送：

```text
请阅读 COPILOT_WRITE_CHAPTER_2_REQUEST.md。现在只完成论文第 2 章 Study Site and Data，不要写第 3 章，也不要做结果分析。请结合仓库中的完整代码、数据和输出文件，生成 paper_drafts/paper_draft_chapter_2.md。无法从仓库确认的信息请用 TODO 标注，不要编造。
```
