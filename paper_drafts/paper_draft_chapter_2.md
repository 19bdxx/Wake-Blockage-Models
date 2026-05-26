# 2. Study Site and Data

## 2.1 Study Site and Wind Farm Layout

本研究对象为仓库中标记为 `MZS` / `JMZSFD` 的海上风电场。根据 `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/风机布局及功率推力曲线/turbine_layout.csv`，场站共有 58 台风机（编号 `#1`–`#58`），其中机型分布为：`GW155/4500` 共 38 台，`GW171/6450` 共 20 台。布局文件同时给出了经纬度与平面坐标，风机经纬度范围约为经度 121.5210–121.6691、纬度 33.3067–33.3383，平面坐标范围约为 X=41362259.34–41376055.02、Y=3687738.373–3691076.594。

根据 `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/风机布局及功率推力曲线/turbine_data.csv`，两类机型分别对应 `type_id=1/2`，并包含 `speed`、`power`、`thrust`、`D`、`Z` 等字段。可从数据中直接读取到主要参数：`GW155/4500` 对应 `D=155 m, Z=100 m`，`GW171/6450` 对应 `D=171 m, Z=105.5 m`；功率曲线最大值分别约为 4500 kW 与 6450 kW。建模端通过 `pywake_integration/run_integration.py` 与 `pywake_integration/wind_farm_setup.py` 将布局中的风机编号、机型映射到 `turbine_model.py` 与 PyWake 的 `type` 索引，实现机组参数与布局的一致调用。

需要说明的是，场站命名在不同文件中存在 `MZS` 与 `JMZSFD` 并行使用（例如布局与模型输出中多为 `MZS`，维护与实测文件多为 `JMZSFD` 前缀），后续论文正式稿建议统一命名规则。

## 2.2 Lidar Observation and Research Motivation

仓库中可检索到与阻塞证据相关的文件 `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/阻塞效应证据.pdf`，且代码注释中多次提及“激光雷达观测为阻塞问题提供动机”（如 `pywake_integration/wind_farm_setup.py` 的阻塞模型说明）。据此可确认：激光雷达观测在本文中主要承担研究动机角色，即提示风电场上游来流可能存在阻塞减速、并提示不同来流代表风速口径可能影响功率表征。

但就当前仓库可直接机器读取的结构化数据而言，尚未发现完整的激光雷达原始时序、观测网格参数或观测元数据文件。因此本章不展开仪器级细节，仅保留研究动机层面的描述。

TODO: 补充激光雷达观测文件、观测时段、仪器型号、时间分辨率、空间分辨率及典型流场图来源。

## 2.3 Meteorological Input Data

模型统一读取 `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv`。该文件包含字段：`valid_time`、`latitude`、`longitude`、`u100`、`v100`、`wind_speed`、`wind_direction`、`is_interpolated`，覆盖时间为 2024-01-01 08:00 至 2024-07-31 23:45，时间分辨率为 15 min。文件名与运行脚本注释（如 `run_five_experiments_维护缺失默认跳过版.py` 中“valid_time 已转换为 UTC8”）均指向 UTC+8 时间体系。

在运行逻辑上，两组实验（考虑维护 / 不考虑维护）均由同一 `forecast` 输入驱动，仅在维护矩阵接入与维护缺失处理策略上发生差异，因此后续实验横向比较不由气象驱动差异造成。

TODO: 需要人工确认 `wind_lat_33.250_lon_121.500-UTC8.csv` 的数据来源（ERA5、EC 或其他来源）。

## 2.4 SCADA Power and Turbine Operational Data

场站原始 SCADA 宽表文件为 `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/场站实测数据/JMZSFD_202309-202407-处理后.csv`，共 317 列，除场站级字段（如 `ACTIVE_POWER_STATION`、`LIMIT_POWER`）外，包含 58 台机组逐机字段对：`STATUS_#i`、`ACTIVE_POWER_#i`、`WINDSPEED_#i`（并含 `REACTIVE_POWER_#i`、`WINDDIRECTION_#i`）。

用于模型对照的轻量实测文件为 `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/场站实测数据/JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv`，字段为 `timestamp`、`MZS_ACTIVE_POWER_STATION`、`MZS_LIMIT_POWER`、`MZS_FAN_ACTIVE_POWER_SUM`、`MZS_FAN_WINDSPEED_MEAN`。该文件由脚本 `场站实测数据/获取风机功率之和用于尾流比较.py` 生成，核心规则为：

- `99999` 视为无效值，替换为缺失后不参与计算；
- 仅 `STATUS_#i` 有效且 `STATUS_#i != 6` 的风机参与统计（`STATUS_#i == 6` 视作维护）；
- 单机有功按 `max(0, ACTIVE_POWER_#i)` 截断负值；
- 场站实测对照功率定义为非维护机组功率和，并在脚本内执行 `/1000`，由 kW 转为 MW；
- 场站实测对照风速定义为非维护机组 `WINDSPEED_#i` 的均值。

可将该过程写为：

\[
P_{\text{meas}}(t)=\sum_{i\in A_{obs}(t)}\max(0,P_i(t)),\quad
A_{obs}(t)=\{i\mid STATUS_i(t)\ \text{有效且}\ STATUS_i(t)\neq 6\}
\]

其中 `P_meas` 与模型端“参与计算的运行机组集合”保持一致，有利于减少“模型预测对象”与“实测统计对象”不一致造成的系统偏差。

## 2.5 Maintenance Matrix

维护信息文件为 `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/JMZSFD维护记录/jmzsfd_maintenance_matrix.csv`，时间列为 `timestamp`，风机列为 `是否维护_#1` 至 `是否维护_#58`，取值为 0/1（1 表示维护）。该矩阵覆盖 2023-09-21 00:00 至 2024-07-29 10:29，原始分辨率以 1 min 为主。

维护矩阵生成逻辑见 `maintenance_tools/生成JMZSFD维护矩阵_宽表_含15min直接对齐.py`：基于状态码识别规则 `STATUS_#i == 6 -> 是否维护_#i=1`，并对异常状态码时刻做质量控制。模型运行脚本 `run_five_experiments_维护缺失默认跳过版.py` 在每个 `valid_time` 查询维护状态（默认 `maintenance_time_offset_hours=0`，即按 UTC+8 直接对齐）。

在“考虑维护”实验中，维护风机不参与当时刻 PyWake 计算且不作为尾流/阻塞源，结果表中对应维护机组功率列置 0；在“不考虑维护”实验中，默认全部风机处于运行状态，不引入维护剔除。

## 2.6 Curtailment Identification and Sample Filtering

限电识别逻辑在评价脚本 `尾流预测与全站实测对比/evaluate_station_power_accuracy_multi_station_monthly_combined.py` 中定义。该脚本读取实测列 `MZS_LIMIT_POWER`（由 `JMZS_LIMIT_POWER` 命名体系映射至 `MZS`），采用规则：

- 站点额定限电基准 `RATED_LIMIT_POWER["MZS"] = 300.0`；
- 默认阈值 `--limit-drop-threshold = 0.95`；
- 判定条件：`LIMIT_POWER < rated * 0.95` 则标记 `is_curtailed=True`。

在样本组织上，脚本同时输出 `all_samples` 与 `not_curtailed` 两套口径。第 2 章仅说明其数据处理意义：限电期间机组输出受调度约束，不宜直接用于检验尾流模型在“自然可发工况”下的功率偏差，因此后续模型评价应重点参考 `not_curtailed` 样本。

TODO: 需要在论文定稿前确认 `RATED_LIMIT_POWER=300.0` 的单位定义与容量基准是否与场站正式容量口径完全一致。

## 2.7 Time Alignment and Common Evaluation Period

主要数据源时间覆盖如下：

- 气象输入：2024-01-01 08:00 至 2024-07-31 23:45（15 min）；
- 维护矩阵：2023-09-21 00:00 至 2024-07-29 10:29（以 1 min 为主）；
- SCADA 轻量实测：2023-09-21 00:00 至 2024-07-29 10:29（以 1 min 为主）；
- 不考虑维护实验输出：2024-01-01 08:00 至 2024-07-31 23:45（15 min）；
- 考虑维护实验输出：2024-01-01 08:00 至 2024-07-29 10:15（15 min）。

“考虑维护”输出较短，原因是该实验使用 `missing_maintenance_policy=skip`，当维护矩阵在某些模型时刻缺失时直接跳过。`five_experiments_output_考虑维护-全月份/maintenance_match_summary.csv` 显示 `exact=19586`、`skipped=830`，对应 `all_experiments_station_power_timeseries.csv` 共 39172 行（每个有效时刻含 blockage on/off 两行）。

因此，涉及“考虑维护 vs 不考虑维护”横向比较时，应使用共同时间交集（可由两实验输出与实测数据按 `valid_time` 内连接得到）。就当前文件覆盖而言，共同比较窗口可设为 2024-01-01 08:00 至 2024-07-29 10:15（15 min 对齐）。

## 2.8 Summary of Data Sources

| Data type | File | Time range | Resolution | Key variables | Purpose |
|---|---|---|---|---|---|
| Wind farm layout | `风机布局及功率推力曲线/turbine_layout.csv` | - | - | turbine id, station, model, lon/lat, X/Y | 布局建模与风机索引 |
| Turbine curves/parameters | `风机布局及功率推力曲线/turbine_data.csv` | - | - | `speed`, `power`, `thrust`, `D`, `Z`, `type_id` | 功率曲线、推力曲线与机型参数 |
| Meteorological input | `场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv` | 2024-01-01 08:00 to 2024-07-31 23:45 | 15 min | `wind_speed`, `wind_direction`, `u100`, `v100`, `is_interpolated` | 模型外部气象驱动 |
| SCADA raw | `场站实测数据/JMZSFD_202309-202407-处理后.csv` | 2023-09-21 00:00 to 2024-07-29 10:29 | mainly 1 min | `ACTIVE_POWER_STATION`, `LIMIT_POWER`, `ACTIVE_POWER_#i`, `WINDSPEED_#i`, `STATUS_#i` | 构建实测对照量 |
| SCADA light reference | `场站实测数据/JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv` | 2023-09-21 00:00 to 2024-07-29 10:29 | mainly 1 min | `MZS_FAN_ACTIVE_POWER_SUM`, `MZS_LIMIT_POWER` | 模型评价实测基准 |
| Maintenance matrix | `JMZSFD维护记录/jmzsfd_maintenance_matrix.csv` | 2023-09-21 00:00 to 2024-07-29 10:29 | mainly 1 min | `是否维护_#1 ... 是否维护_#58` | 运行机组集合修正 |
| Model outputs (with maintenance) | `five_experiments_output_考虑维护-全月份/all_experiments_station_power_timeseries.csv` | 2024-01-01 08:00 to 2024-07-29 10:15 | 15 min | `station_power_*_kW`, `enable_blockage` | 候选功率口径输出（维护修正） |
| Model outputs (without maintenance) | `five_experiments_output_不考虑维护-全月份/all_experiments_station_power_timeseries.csv` | 2024-01-01 08:00 to 2024-07-31 23:45 | 15 min | `station_power_*_kW`, `enable_blockage` | 候选功率口径输出（全机组运行） |
| Evaluation-ready converted outputs | `尾流预测与全站实测对比/all_experiments_station_power_timeseries-*.csv` | 同对应实验输出 | 15 min | `station_power_*_MW` | 与实测 MW 口径对齐 |

## Unit consistency note

仓库中模型输出存在 `_kW` 与 `_MW` 并行文件：`five_experiments_output_*` 下为 `station_power_*_kW`，`尾流预测与全站实测对比` 下为经脚本 `#2kw转换为mw.py` 转换后的 `station_power_*_MW`。论文正文与图表需要统一单位口径，避免同名变量跨文件单位不一致。

# Information Still Needed

- TODO: 场站正式论文名称与缩写（`MZS` / `JMZSFD`）的统一规范。
- TODO: `wind_lat_33.250_lon_121.500-UTC8.csv` 的气象数据来源说明（ERA5、EC 或其他）。
- TODO: 激光雷达观测文件、观测时间、仪器型号、时间/空间分辨率与观测位置。
- TODO: 功率曲线与推力曲线的来源说明（厂家文档版本、现场修正版本或其他）。
- TODO: 限电阈值与容量基准的正式定义（`RATED_LIMIT_POWER=300.0` 的单位与依据）。
- TODO: 是否需要在第 2 章明确 1 min SCADA 向 15 min 评价时标对齐的具体重采样细节（当前评价脚本主要使用时间内连接）。

# Suggested Figures and Tables

## Suggested Figures

- Figure 1. JMZSFD/MZS 风电场风机布局图（含 #1–#58 编号与机型分区）。
- Figure 2. 激光雷达与阻塞证据材料在研究流程中的作用示意图（动机层面，而非模型输入流程）。
- Figure 3. 从原始 SCADA 到 `MZS_FAN_ACTIVE_POWER_SUM` 的构造流程图（状态筛选、异常值处理、负值截断、求和与单位转换）。
- Figure 4. 气象输入、维护矩阵、实测数据与两组实验输出的时间覆盖对比图。

## Suggested Tables

- Table 1. 风电场与机型基础信息（数量、机型、轮径、轮毂高度、额定功率）。
- Table 2. 气象输入变量定义与单位（`wind_speed`、`wind_direction`、`u100`、`v100`、`is_interpolated`）。
- Table 3. SCADA 原始字段与轻量实测字段对照表。
- Table 4. 维护与限电样本处理规则（状态码、阈值、剔除逻辑）。
- Table 5. 数据源时间覆盖与分辨率汇总表。
