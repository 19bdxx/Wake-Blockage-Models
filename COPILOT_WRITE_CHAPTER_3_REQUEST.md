# Copilot 任务说明：撰写论文第 3 章 Methodology

> 建议将本文档放在 GitHub 仓库根目录，文件名可设为：  
> `COPILOT_WRITE_CHAPTER_3_REQUEST.md`
>
> 本文档用于指导 Copilot 基于当前 GitHub 仓库中的完整代码、数据文件和实验输出，撰写期刊论文中的 **第 3 章 Methodology**。  
>
> 本次任务只写第 3 章方法部分，不写第 2 章数据部分，不写第 4 章结果分析，也不做模型优劣结论。  
> 第 3 章的目标是把当前代码中的建模流程、实验设计、功率计算口径和评价方法整理成可读、可复现、可写入论文的方法章节。

---

# 0. Copilot 需要先理解的项目背景

当前仓库对应一个海上风电场尾流建模与场站功率模拟研究项目。研究对象为仓库中标记为 `MZS` / `JMZSFD` 的海上风电场。

项目已经具备以下内容：

- 风机布局和风机类型参数；
- 功率曲线和推力曲线；
- 场站附近统一气象输入；
- 风机级 SCADA 实测数据；
- 维护状态矩阵；
- 基于 PyWake 或自定义尾流模型的模型运行脚本；
- 两组模型实验输出：
  - 考虑维护状态；
  - 不考虑维护状态；
- 每组实验内部均包含：
  - `enable_blockage=False`
  - `enable_blockage=True`
- 每个阻塞设置下又输出多个 `station_power_*` 候选功率列，对应不同等效入流风速口径。

本文整体研究逻辑是：

1. 前期激光雷达观测提示海上风电场可能存在阻塞效应；
2. 激光雷达及空间风速分析表明，不同空间位置、不同上游距离风速与功率曲线的适配性不同；
3. 因此，本文在传统尾流模型基础上：
   - 引入/开启阻塞效应；
   - 比较不同等效入流风速口径；
   - 分析哪个上游距离或哪类空间平均风速更适合输入功率曲线；
4. 在真实场站数据验证中，通过维护状态修正和限电样本筛选保证模型预测对象与实测功率统计对象一致。

第 3 章需要回答的是：

> 本文的方法流程是什么？模型如何构建？阻塞效应如何设置？不同等效入流风速口径如何定义？场站功率如何计算？实验如何设计？指标如何计算？如何控制变量比较维护、阻塞和风速口径的影响？

---

# 1. 本次任务目标

请 Copilot 基于仓库实际代码和输出文件，撰写论文第 3 章：

```markdown
# 3. Methodology
```

最终输出文件：

```text
paper_drafts/paper_draft_chapter_3.md
```

第 3 章需要接近期刊论文初稿，而不是只给提纲。

请注意：

- 必须结合仓库代码中的真实模型流程；
- 必须使用仓库真实字段名和文件名；
- 不要编造代码中不存在的模型配置；
- 如果无法确认某个模型名称、参数或公式，请写 `TODO:`；
- 不要写模型结果好坏；
- 不要提前下结论哪个候选口径最好；
- 不要把维护状态修正写成主要模型创新。

---

# 2. 本次任务不要做什么

请不要写以下内容：

- 不要写第 2 章 Study Site and Data；
- 不要重新介绍所有数据源细节，除非方法中必须引用；
- 不要写第 4 章 Results；
- 不要写第 5 章 Discussion；
- 不要比较哪个实验结果最好；
- 不要输出 ranking 分析；
- 不要做风速分箱或风向分箱结果解释；
- 不要生成最终结论；
- 不要编造仓库中没有的信息。

第 3 章可以说明“后续将如何比较”，但不能写“比较结果显示……”。

---

# 3. 输出要求

请生成：

```text
paper_drafts/paper_draft_chapter_3.md
```

建议结构如下：

```markdown
# 3. Methodology

## 3.1 Overall Modeling Framework

## 3.2 Baseline Wake Model

## 3.3 Blockage Effect Configuration

## 3.4 Maintenance-State Correction in Wake Simulation

## 3.5 Equivalent Inflow Wind-Speed Definitions

## 3.6 Station Power Calculation

## 3.7 Experimental Design

## 3.8 Evaluation Metrics

## 3.9 Controlled Comparison Strategy

## 3.10 Robustness Assessment of Candidate Wind-Speed Definitions

# Information Still Needed

# Suggested Figures and Tables
```

如果 Copilot 根据仓库实际情况认为小节标题需要微调，可以调整，但必须保持“只写方法章节”的边界。

---

# 4. 写作风格要求

1. 使用中文学术论文风格，接近期刊论文初稿；
2. 正文应有连贯叙述，不要只堆 bullet list；
3. 每节需要结合仓库中的实际代码、函数、字段和输出逻辑；
4. 变量名、文件名、字段名、单位必须以仓库实际内容为准；
5. 如果示例字段与仓库实际字段不一致，以仓库实际字段为准；
6. 如果无法确认某个模型配置或参数，请写 `TODO:`；
7. 不要夸大方法贡献；
8. 不要把维护状态修正写成主要创新；
9. 不要把当前模型称为已经验证的业务功率预测系统；
10. 第 3 章末尾必须列出：
   - `Information Still Needed`
   - `Suggested Figures and Tables`

建议避免：

```text
本文提出一种全新的尾流模型。
本文模型已显著提升实际业务预测能力。
维护状态修正是本文核心创新。
```

建议使用：

```text
本文在现有尾流模型框架中引入阻塞效应并进行对比验证。
本文定义并比较多种等效入流风速口径。
维护状态修正用于保证模型计算对象与实测统计对象一致。
```

---

# 5. 请优先阅读的仓库文件

请 Copilot 在写作前先阅读以下文件。不要只根据本文档泛泛写作。

---

## 5.1 主模型运行脚本

请重点阅读：

```text
run_five_experiments_维护缺失默认跳过版.py
```

需要理解并写入方法章节：

- 脚本整体流程；
- 气象输入如何读取；
- 风机布局如何读取；
- 功率曲线和推力曲线如何读取；
- PyWake 或自定义尾流模型如何初始化；
- `enable_blockage=False/True` 如何设置；
- 每个 `valid_time` 如何运行模型；
- 维护矩阵如何接入；
- 维护缺失时刻如何处理；
- 维护风机如何从模型计算中剔除；
- 风机级输出如何生成；
- 场站级输出如何生成；
- `all_experiments_station_power_timeseries.csv` 如何形成。

如果脚本中有具体函数名，请在方法章节中适度引用。例如：

```text
load_forecast(...)
load_maintenance_matrix(...)
run_single_time_step(...)
build_wind_farm_model(...)
```

如果函数名不同，以实际代码为准。

---

## 5.2 PyWake 集成与模型配置文件

请检查仓库中类似以下文件：

```text
pywake_integration/wind_farm_setup.py
pywake_integration/turbine_model.py
pywake_integration/config.py
pywake_integration/ziyan_deficit.py
```

请确认并写入方法章节：

- 是否使用 PyWake；
- 使用的 wind farm model；
- 是否使用 `All2AllIterative`；
- wake deficit model 名称；
- blockage model 名称；
- superposition model；
- turbulence model；
- deflection model，如果有；
- rotor averaging 或 power curve 处理方式；
- 风切变修正方式，例如是否使用 `PowerShear`；
- 功率曲线和推力曲线如何封装，例如是否使用 `PowerCtTabular`；
- 单位是 kW 还是 MW。

如果某些模型名称无法确认，请写：

```text
TODO: 根据代码确认具体 PyWake 模型配置。
```

---

## 5.3 风机布局与功率/推力曲线文件

请查找并阅读：

```text
风机布局及功率推力曲线/turbine_layout.csv
风机布局及功率推力曲线/turbine_data.csv
```

或仓库中的实际文件名。

需要理解：

- 风机坐标如何用于模型；
- 风机类型如何映射；
- 轮径和轮毂高度如何进入模型；
- 功率曲线和推力曲线如何用于计算；
- 不同机型是否分别定义曲线。

第 3 章只需要写它们如何进入模型，不要重复第 2 章数据细节。

---

## 5.4 两组模型输出

请检查：

```text
five_experiments_output_考虑维护-全月份/all_experiments_station_power_timeseries.csv
five_experiments_output_不考虑维护-全月份/all_experiments_station_power_timeseries.csv
```

需要确认：

- `enable_blockage` 字段；
- `station_power_*` 候选功率列；
- 候选列是 `_kW` 还是 `_MW`；
- 是否包含风速、风向、维护台数等辅助字段；
- 是否包含 PyWake 内部功率口径；
- 是否包含上游固定距离风速功率口径；
- 是否包含转子圆盘上游平均风速功率口径。

这些信息用于写 3.5 等效入流风速定义和 3.7 实验设计。

---

## 5.5 维护矩阵与实测功率脚本

请阅读：

```text
JMZSFD维护记录/jmzsfd_maintenance_matrix.csv
获取风机功率之和用于尾流比较.py
```

第 3 章中只需要说明：

- 维护矩阵如何用于模型计算；
- 可运行风机集合如何定义；
- 实测端如何构建非维护风机功率和；
- 为什么模型端和实测端需要一致口径。

不要在第 3 章展开第 2 章的数据描述，也不要写维护改善结果。

---

## 5.6 评价脚本

请阅读仓库中已有评价脚本，例如：

```text
evaluate_station_power_accuracy_multi_station.py
evaluate_station_power_accuracy_multi_station_monthly_combined.py
```

或仓库中的实际文件。

需要理解：

- 实测与预测如何合并；
- all samples 与 non-curtailed samples 如何区分；
- 限电样本如何识别；
- MAE、RMSE、Bias、nRMSE、R²、Corr 如何计算；
- ranking 如何排序；
- 月度评价如何进行。

第 3 章需要写评价指标和控制变量比较策略，但不要写评价结果。

---

# 6. 第 3 章具体写作要求

---

## 6.1 3.1 Overall Modeling Framework

这一节需要概述整个方法流程。

建议写作逻辑：

1. 以气象输入、风机布局、功率曲线、推力曲线作为模型输入；
2. 构建传统尾流模型；
3. 设置阻塞开启/关闭两种情景；
4. 根据维护矩阵修正可运行风机集合；
5. 对每个时刻计算风机有效风速；
6. 定义多种等效入流风速口径；
7. 将不同风速口径输入功率曲线；
8. 汇总为场站功率；
9. 与实测非维护风机功率和比较。

建议加入流程图草案：

```text
Figure 4. Overall workflow of wake-blockage power simulation and evaluation.
```

请注意：这里是方法总览，不写具体结果。

---

## 6.2 3.2 Baseline Wake Model

这一节需要定义传统尾流基线。

请写：

- baseline 是 `enable_blockage=False`；
- 模型使用仓库中的 PyWake / 自定义尾流模块；
- 输入包括风速、风向、风机坐标、功率曲线和推力曲线；
- 输出为风机有效风速和功率；
- 该基线用于后续与开启阻塞效应的模型进行对照。

如果代码中使用：

```text
All2AllIterative
ZiyanWakeDeficit
SquaredSum
STF2005TurbulenceModel
PowerShear
PowerCtTabular
```

请准确写入；如果实际名称不同，以代码为准。

不要编造模型名称。

---

## 6.3 3.3 Blockage Effect Configuration

这一节需要说明阻塞效应如何设置。

请写：

- 阻塞效应表示风机或风机群对上游来流的影响；
- 本文通过 `enable_blockage` 控制阻塞项；
- `enable_blockage=False` 表示 wake-only；
- `enable_blockage=True` 表示 wake + blockage；
- 同一时刻、同一气象输入、同一风机状态下，仅切换阻塞开关；
- 这样可以构成控制变量实验。

如果代码中使用：

```text
SelfSimilarity
SelfSimilarityDeficit2020
```

或其他 blockage model，请准确写出。

注意：  
不要写成提出新的阻塞理论，只能写“在现有模型框架中开启/接入阻塞项并进行验证”。

---

## 6.4 3.4 Maintenance-State Correction in Wake Simulation

这一节需要写维护状态如何进入模型。

请写：

- 维护矩阵给出每个时刻每台风机是否维护；
- 考虑维护实验中，维护风机从可运行集合中剔除；
- 可运行风机集合可记为：

```text
A(t) = {i | turbine i is not under maintenance at time t}
```

- 维护风机不参与功率汇总；
- 如果代码中确实如此，也写明维护风机不作为尾流/阻塞源；
- 不考虑维护实验中，默认所有风机处于可运行状态；
- 如果维护矩阵缺失，该时刻按脚本策略跳过。

请强调：

> 维护状态修正不是新的尾流物理机制，而是保证模型计算对象与实测功率统计对象一致的运行状态约束。

---

## 6.5 3.5 Equivalent Inflow Wind-Speed Definitions

这是第 3 章重点之一。

请从模型输出候选列 `station_power_*` 自动归纳不同功率口径。

可能包括：

1. PyWake 内部功率口径；
2. 基于 PyWake native effective wind speed 的功率口径；
3. 上游固定距离点风速输入功率曲线；
4. 转子圆盘上游不同距离平均风速输入功率曲线。

请解释每类口径的物理意义：

### A. PyWake 内部功率口径

由 PyWake 或模型内部有效风速直接计算得到的功率。

### B. PyWake native effective wind speed 口径

使用模型输出的有效风速，再通过统一功率曲线重新计算功率。

### C. 上游固定距离点风速口径

在风机上游某一距离处取点风速，作为功率曲线输入。

### D. 转子圆盘上游平均风速口径

在风机转子圆盘上游某一距离处，对多个空间采样点或转子圆盘区域风速进行平均，作为等效入流风速。

请解释：

- 单点风速可能受局部扰动影响；
- 转子圆盘平均风速更接近风机扫掠面积上的能量输入；
- 不同上游距离代表不同空间位置的入流定义；
- 这些口径不是随便试参数，而是为了研究风速代表性与功率曲线适配性。

请根据实际输出列列出候选口径，例如：

```text
station_power_pywake_internal_kW
station_power_from_ws_eff_pywake_native_kW
station_power_from_upstream_1m_kW
station_power_from_upstream_50m_kW
...
station_power_from_rotor_disc_upstream50m_mean_kW
station_power_from_rotor_disc_upstream60m_mean_kW
...
```

如果实际列名是 `_MW`，请以实际列名为准。

建议生成表格草案：

```markdown
Table 5. Candidate power definitions and corresponding equivalent inflow wind-speed concepts.

| Candidate type | Example columns | Wind-speed concept | Physical interpretation |
|---|---|---|---|
| PyWake internal | TODO | Internal effective wind speed | Baseline model output |
| Native effective wind speed | TODO | Effective wind speed + unified power curve | Separates wind-speed definition from power curve |
| Upstream point | TODO | Point wind speed at upstream distance | Local inflow at a selected position |
| Rotor-disc upstream mean | TODO | Rotor-disc averaged wind speed | Spatially averaged inflow over rotor-relevant area |
```

---

## 6.6 3.6 Station Power Calculation

这一节需要说明单机功率和场站功率如何聚合。

建议使用公式：

```text
P_station(t) = Σ P_i(t), i ∈ A(t)
```

其中：

- `A(t)` 为时刻 `t` 的可运行风机集合；
- `P_i(t)` 是第 `i` 台风机根据对应等效入流风速和功率曲线计算得到的功率；
- 对不同等效入流风速口径，都会形成一组对应的单机功率和场站功率；
- 场站级输出为 `station_power_*` 候选列；
- 维护风机不参与功率汇总；
- 如果代码中维护风机功率置零，请准确说明。

请说明单位：

- 如果候选列为 `_kW`，最终评价前可能需要转换为 MW；
- 如果候选列为 `_MW`，请以实际输出为准；
- 需要在方法中明确单位处理。

---

## 6.7 3.7 Experimental Design

这一节需要清楚写出实验矩阵。

当前已有两组主要实验：

1. **With maintenance**：接入维护矩阵；
2. **Without maintenance**：不接入维护矩阵。

每组实验内部包含：

```text
enable_blockage=False
enable_blockage=True
```

每个阻塞状态下包含多个候选功率口径。

请说明两组实验命令或等价配置：

```text
考虑维护：--maintenance-matrix JMZSFD维护记录/jmzsfd_maintenance_matrix.csv
不考虑维护：不传入 --maintenance-matrix
```

请解释每个实验目的：

- 不考虑维护实验：作为全机组运行假设下的对照；
- 考虑维护实验：保证模型运行风机集合与实际运行状态一致；
- blockage off/on：检验阻塞效应；
- 多候选功率口径：检验等效入流风速定义。

建议表格草案：

```markdown
Table 6. Summary of numerical experiments.

| Experiment | Maintenance matrix | Blockage setting | Candidate power definitions | Purpose |
|---|---|---|---|---|
| Without maintenance | No | Off/On | station_power_* | Baseline operational assumption |
| With maintenance | Yes | Off/On | station_power_* | Operational-state-consistent simulation |
```

请强调：

> 这些实验结果不能通过“各自最优 ranking”直接比较，后续分析需要控制变量。

---

## 6.8 3.8 Evaluation Metrics

这一节需要写指标公式。

设实测功率为：

```text
P_obs(t)
```

预测功率为：

```text
P_pred(t)
```

误差：

```text
e(t) = P_pred(t) - P_obs(t)
```

请写出：

- MAE；
- RMSE；
- Bias；
- nMAE；
- nRMSE；
- R²；
- Corr；
- median absolute error；
- p90 absolute error；
- energy error if used。

建议公式：

```text
MAE = mean(|e|)
RMSE = sqrt(mean(e^2))
Bias = mean(e)
nMAE = MAE / P_norm
nRMSE = RMSE / P_norm
```

请根据代码确认：

- `P_norm` 使用场站额定容量；
- 或使用实测高分位数；
- 或使用 `LIMIT_POWER` 高分位数。

如果代码里不统一，请写：

```text
TODO: 需要统一 nMAE/nRMSE 的归一化容量定义。
```

请说明：

- 主评价对象为 `MZS_FAN_ACTIVE_POWER_SUM` 或实际字段；
- 同时可辅助检查场站总功率；
- 评价分为 `all_samples` 和 `non_curtailed`；
- 主结论优先基于 `non_curtailed`；
- 月度评价用于分析模型稳定性。

---

## 6.9 3.9 Controlled Comparison Strategy

这一节非常重要。

请明确写出三类控制变量比较。

### 3.9.1 维护状态比较

比较目的：

> 判断维护状态修正是否影响模型验证结果。

控制变量：

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

不能使用：

```text
with_maintenance 的最佳口径 vs without_maintenance 的最佳口径
```

作为维护有效性的证据。

### 3.9.2 阻塞效应比较

比较目的：

> 判断阻塞效应是否改善传统尾流模型误差。

控制变量：

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

### 3.9.3 等效入流风速口径比较

比较目的：

> 判断哪个风速口径更适合功率曲线。

控制变量：

```text
experiment_name
enable_blockage
scope_name
period_type
```

只改变：

```text
candidate_power_col
```

请强调：

- 不采用逐月自由选择最优口径作为最终模型；
- 更关注跨月份稳定性；
- 需要统计 overall 表现、月度平均误差、月度波动、最差月份、top-k 月份数量等。

---

## 6.10 3.10 Robustness Assessment of Candidate Wind-Speed Definitions

这一节用于说明如何评价候选风速口径是否稳定。

请写：

- 为什么不能只看 overall 第一名；
- 为什么不能每个月换一个最优距离；
- 需要评价跨月份稳定性；
- 可用指标包括：

```text
monthly_nrmse_mean
monthly_nrmse_std
monthly_nrmse_max
monthly_rank_mean
monthly_rank_std
top1_month_count
top3_month_count
top5_month_count
worst_month_nrmse
```

可以定义一个稳健性评分，例如：

```text
stability_score = monthly_nrmse_mean + α * monthly_nrmse_std + β * monthly_nrmse_max
```

如果代码中已有具体公式，请以代码为准。  
如果还没有固定公式，请写：

```text
TODO: 根据后续结果分析确定 stability_score 的权重。
```

请说明：

> 稳健性评价的目标是筛选一个可复用的等效入流风速口径或距离带，而不是为每个月单独选择最优模型。

---

# 7. 最终文件末尾必须包含

## 7.1 Information Still Needed

请列出所有无法确认但方法章节需要补充的信息，例如：

- 具体 PyWake 模型配置；
- wake deficit model 名称；
- blockage model 名称；
- turbulence model；
- superposition model；
- 风切变参数；
- 空气密度设置；
- 功率曲线插值方法；
- 候选上游距离列表；
- rotor-disc mean 的具体采样方式；
- nMAE/nRMSE 的归一化容量定义；
- energy error 的时间间隔处理方式。

## 7.2 Suggested Figures and Tables

请列出建议图表，例如：

```markdown
## Suggested Figures

- Figure 4. Overall workflow of wake-blockage power simulation and evaluation.
- Figure 5. Wake-only and wake-blockage simulation configurations.
- Figure 6. Equivalent inflow wind-speed definitions: upstream point and rotor-disc upstream mean.
- Figure 7. Controlled comparison design for maintenance, blockage and candidate wind-speed definitions.

## Suggested Tables

- Table 5. Candidate station-power definitions and equivalent inflow concepts.
- Table 6. Summary of numerical experiments.
- Table 7. Evaluation metrics.
- Table 8. Controlled comparison strategy.
```

---

# 8. Copilot 输出前自查清单

在提交 `paper_drafts/paper_draft_chapter_3.md` 前，请 Copilot 自查：

- [ ] 是否只写了第 3 章，没有重复第 2 章；
- [ ] 是否没有写结果分析；
- [ ] 是否使用仓库实际文件名、字段名和模型名称；
- [ ] 是否明确 baseline wake model；
- [ ] 是否明确 blockage on/off；
- [ ] 是否明确维护状态如何进入模型；
- [ ] 是否归纳了所有候选 `station_power_*` 口径；
- [ ] 是否说明了场站功率聚合公式；
- [ ] 是否写清楚实验设计；
- [ ] 是否写出评价指标；
- [ ] 是否强调控制变量比较；
- [ ] 是否说明为什么不能只比较各自最优 ranking；
- [ ] 是否说明为什么不能逐月自由选择最优口径；
- [ ] 是否把无法确认的信息标记为 TODO；
- [ ] 是否没有编造模型配置；
- [ ] 是否列出了建议图表和仍需补充信息。

---

# 9. 推荐给 Copilot 的启动指令

将本文件放入仓库后，请对 Copilot 发送：

```text
请阅读 COPILOT_WRITE_CHAPTER_3_REQUEST.md。现在只完成论文第 3 章 Methodology，不要写第 2 章，也不要做结果分析。请结合仓库中的完整代码、模型配置、实验输出和评价脚本，生成 paper_drafts/paper_draft_chapter_3.md。无法从仓库确认的信息请用 TODO 标注，不要编造。
```
