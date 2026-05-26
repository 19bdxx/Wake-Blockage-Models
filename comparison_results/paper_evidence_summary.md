# Paper Evidence Summary

## 1. Overall Judgment

当前结果已经能够支撑一条相对清晰的论文主线，但前提是论文必须把结论限定在**共同时间交集、统一气象输入、统一 MW 单位、以 `not_curtailed` 为主评价域的历史样本比较**之内。从现有证据看，“维护状态修正是否有必要”这一点证据最强，因为在控制 `candidate_power_col` 和 `enable_blockage` 后，`not_curtailed` overall 的 80/80 个组合 `nRMSE` 全部改善；这足以支持“运行状态一致性处理会系统性改变验证结果”的主结论。关于“阻塞效应是否值得纳入尾流模型”，当前也已有可写结论，但应写成**条件性收益**：在 `with_maintenance + not_curtailed` 主线下，35/40 个组合 `nRMSE` 改善，且收益集中在 rotor-disc mean 与 61–160 m 距离带，而不是所有候选都受益。

“不同等效入流风速口径是否确实存在差异”这一点也有较强支撑，因为 strict overall 最优、稳健最优、月度最优、风速分箱最优、风向扇区最优均不相同，说明候选定义与距离带确实影响误差表现。不过，当前最适合推荐的是**稳定距离带/稳定候选群**，而不是单一“唯一最优口径”：现有证据更支持“upstream 60–80 m + blockage on”与“rotor-disc mean 30–70 m + blockage on”属于跨月份稳定前列范围，而不支持“某一个口径在所有条件下都最优”。需要谨慎表述的部分主要有：月度最优的泛化、风速/风向局部现象的机理解释、blockage 的物理归因、以及气象输入来源与代表性边界。

## 2. Results Suitable for Main Paper Conclusions

### 2.1 维护状态修正的必要性
- conclusion：维护状态修正是必要的，因为运行状态不一致会系统性改变验证结果。
- evidence：在共同时间交集、固定 `candidate_power_col`、固定 `enable_blockage` 后，`not_curtailed` overall 的 80/80 个组合 `nRMSE` 全部改善；均值改善 10.12%，中位改善 11.34%。
- metrics：`nRMSE` improved count = 80/80，mean improvement = 10.12%，median = 11.34%，range = 1.10%–11.83%。
- sample scope：common time + `not_curtailed` + overall（每组合 `n=18467`）。
- controlled variables：固定 `candidate_power_col`、固定 `enable_blockage`、统一实测目标、统一 MW 单位。
- source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/maintenance_controlled_overall.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/maintenance_controlled_summary.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/02_maintenance_effect_by_month.png`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/chapter4_analysis_report.md`。
- recommended wording：在共同时间交集和非限电影响样本上，维护状态修正使相同候选定义与相同 blockage 设置下的误差指标一致下降，说明运行状态一致性处理会系统性影响模型验证结果。
- caution：应明确这是**评价口径对齐/运行状态一致性处理**，不是新的尾流物理模型创新；收益大小具有月份依赖性。

### 2.2 阻塞效应对误差的影响
- conclusion：在当前历史样本下，纳入 blockage 倾向于改善误差，但这种收益是候选相关、距离相关和月份相关的条件性结果。
- evidence：`with_maintenance + not_curtailed` overall 中，35/40 个组合 `nRMSE` 改善；平均改善 3.43%，中位改善 6.64%；rotor-disc mean 平均改善 7.30%，upstream point 仅 1.45%，0–20 m 距离带平均恶化 8.60%。
- metrics：`nRMSE` improved count = 35/40；mean improvement = 3.43%；median = 6.64%；best = 9.78%；worst = -27.21%；candidate-type mean improvement：rotor-disc mean 7.30%，upstream point 1.45%。
- sample scope：`with_maintenance + not_curtailed` + overall（每组合 `n=18467`）。
- controlled variables：固定 `experiment_name`、固定 `candidate_power_col`、固定 `scope_name`。
- source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/blockage_controlled_overall.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/blockage_controlled_summary.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/03_blockage_effect_summary.png`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/chapter4_analysis_report.md`。
- recommended wording：在控制实验组与候选定义后，启用 blockage 在大多数组合上降低了误差，但收益主要集中在 rotor-disc mean 及中等距离带，因此其效果应表述为条件性改进而非普适性提升。
- caution：不能写成“blockage 对所有口径都有效”；1–3 月组合平均收益为负，短距离带也可能恶化。

### 2.3 等效入流风速口径的距离依赖性
- conclusion：等效入流风速口径存在明确的距离依赖，且 blockage 会改变最优距离带。
- evidence：`upstream_point` 在 blockage off 时 `nRMSE` 最优距离为 400 m、on 时转为 80 m；`rotor_disc_upstream_mean` 在 off 时最优为 160 m、on 时最优为 70 m。
- metrics：strict overall 最优 = `station_power_from_rotor_disc_upstream70m_mean_kW + blockage_on`（`nRMSE=0.1553`）；距离最优点随 blockage 改变而迁移。
- sample scope：`with_maintenance + not_curtailed` + overall。
- controlled variables：统一实验组、统一样本范围，分别比较 blockage on/off 下各距离候选。
- source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/distance_error_curve.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/04_distance_vs_nrmse.png`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/chapter4_analysis_report.md`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/paper_drafts/paper_draft_chapter_4.md`。
- recommended wording：结果表明，候选等效入流风速的优劣不仅取决于口径类型，还取决于距离定义与是否启用 blockage，因此“最优距离”并非固定常数。
- caution：这是描述性结果，不等于已经完成物理机理解释；最优距离目前只在该历史样本和当前输入口径下成立。

### 2.4 rotor-disc mean 与 upstream point 的差异
- conclusion：rotor-disc mean 与 upstream point 确有差异，但更准确的结论是“二者在不同距离带竞争”，而不是一类始终优于另一类。
- evidence：blockage on 下，rotor-disc mean 在整体 strict optimum 中领先（70 m mean），但稳健前列同时包含 upstream 60–80 m 与 rotor-disc mean 30–70 m；blockage 对 rotor-disc mean 的平均收益也更高。
- metrics：strict overall best = rotor-disc 70 m；robust rank #1 = upstream 60 m；candidate-type blockage improvement：rotor-disc mean 7.30%，upstream point 1.45%。
- sample scope：主要为 `with_maintenance + not_curtailed` overall + monthly robustness。
- controlled variables：统一实验组、统一样本域、统一误差指标；在同一 blockage 设置下比较两类候选。
- source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/robust_candidate_selection.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/distance_error_curve.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/blockage_controlled_summary.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/03_blockage_effect_summary.png`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/04_distance_vs_nrmse.png`。
- recommended wording：当前结果并不支持简单地将 rotor-disc mean 或 upstream point 宣称为全局最优，而是表明两类口径在不同距离带上各有优势，且其表现会受到 blockage 设置影响。
- caution：不宜写成类型优劣的绝对结论；应避免脱离距离带谈“类型本身”的胜负。

### 2.5 跨月份稳健口径或稳定距离带
- conclusion：可以推荐稳定距离带/稳定候选群，但不宜推荐“所有月份唯一最优”的单一口径。
- evidence：稳健性前 10 名全部为 `blockage_on`；主要集中在 upstream 60–80 m 与 rotor-disc mean 30–70 m；`station_power_from_upstream_60m_kW + blockage_on` 虽无单月 top-1，但 `stability_score` 最低。
- metrics：robust rank #1 = `station_power_from_upstream_60m_kW + blockage_on`；`monthly_nRMSE_mean=0.1525`；`monthly_nRMSE_std=0.0402`；`monthly_nRMSE_max=0.2368`；top 10 全部为 blockage on。
- sample scope：`with_maintenance + not_curtailed` 月度结果（2024-01 至 2024-07）。
- controlled variables：统一 `stability_score` 规则；统一样本域；统一按月比较。
- source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/robust_candidate_selection.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/monthly_performance_summary.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/06_monthly_nrmse_heatmap.png`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/07_candidate_rank_heatmap.png`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/chapter4_analysis_report.md`。
- recommended wording：考虑到月度最优候选随月份变化，本文更倾向于推荐跨月份保持稳定前列的候选距离带，而不是逐月切换局部最优组合。
- caution：`stability_score` 是当前分析脚本定义的复合指标，权重仍需在正式论文中说明其经验性；不宜将其写成唯一正式准则。

### 2.6 风速段/风向段下模型表现差异
- conclusion：候选口径与 blockage 设置的相对优劣具有明显工况依赖性。
- evidence：风速分箱中，低风速最优多为 blockage off，而多数中高风速段转为 blockage on；风向扇区中，不同扇区最优候选与最优 blockage 设置也变化明显。
- metrics：风速 `0-3` 最优为 `WS_eff native + blockage_off`（`nRMSE=0.0563`）；`9-11` 最优可达误差最高（`nRMSE=0.2122`）；风向扇区样本数范围 622–2781，不同扇区最优组合不同。
- sample scope：`with_maintenance + not_curtailed` 的风速分箱 / 风向扇区结果。
- controlled variables：统一实验组、统一样本域，按风速或风向重新分组。
- source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/08_wind_speed_bin_performance.png`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/09_wind_direction_bin_performance.png`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/chapter4_analysis_report.md`。
- recommended wording：分箱结果表明，不同来流工况下的优选候选并不一致，因此整体推荐应强调稳健性，而不应声称某一候选在所有工况下均最优。
- caution：适合支撑“工况依赖”结论，不适合直接支撑物理因果解释；部分风向扇区样本较少。

### 2.7 典型案例对整体统计结论的支持
- conclusion：典型案例能够作为统计结论的可视化支撑，但只能起到“印证”作用，不能替代总体统计。
- evidence：维护案例 96/96 个时刻 `improvement_abs_error` 为正；blockage 与 candidate difference 案例窗口平均收益为正，但均存在局部负改善时刻。
- metrics：maintenance case 平均每步改善 71.54 MW，最小改善 50.79 MW；blockage case 平均 31.09 MW，最小 -21.54 MW；candidate case 平均 41.17 MW，最小 -31.98 MW。
- sample scope：三个 24 h 连续窗口，各 96 个 15 min 时刻。
- controlled variables：案例各自固定比较对（with vs without maintenance；blockage on vs off；recommended vs traditional candidate）。
- source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/case_studies/case_maintenance_improvement.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/case_studies/case_blockage_improvement.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/case_studies/case_candidate_difference.csv`；对应三张 case PNG；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/chapter4_analysis_report.md`。
- recommended wording：典型连续窗口表明，维护修正的收益可以在持续时段内稳定体现，而 blockage 与候选替换更适合写成窗口总体收益为正、但局部时刻并非始终占优。
- caution：案例是代表性窗口，不等于总体规律本身；不能用个案替代总体统计证据。

## 3. Results Suitable for Results Chapter Only

1. **单实验 overall / monthly ranking**  
   - 适合展示原因：能快速交代每组实验内部的优选组合与误差量级，是读者进入结果部分的入口。  
   - 不宜上升为主结论原因：ranking 同时混入了维护修正、候选定义和 blockage 三类变化，不能单独回答某一因素是否有效。  
   - source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/single_experiment_evaluation/*.csv`。

2. **月度最优候选列表**  
   - 适合展示原因：可直观说明“月度最优并不固定”。  
   - 不宜上升为主结论原因：月度 top-1 高度依赖月样本构成，而且当前 `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/monthly_candidate_rank.csv` 是按 `enable_blockage + month` 分组重排名次，和单实验 monthly ranking 的“全候选统一排名”不是同一个问题。  
   - source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/monthly_candidate_rank.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/single_experiment_evaluation/ranking_with_maintenance_monthly.csv`。

3. **风速/风向分箱中的局部最优现象**  
   - 适合展示原因：能体现模型表现的工况依赖性。  
   - 不宜上升为主结论原因：局部最优受分箱样本数、分箱宽度和局部天气构成影响，且缺乏进一步物理验证。  
   - source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`。

4. **典型案例**  
   - 适合展示原因：非常适合做图，帮助读者理解“连续窗口收益”和“局部反向时刻共存”的现象。  
   - 不宜上升为主结论原因：它们来自最佳窗口筛选，本质上是展示性证据而非总体统计。  
   - source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/case_studies/*.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/case_*.png`。

5. **`abs_bias` 百分比改善结果**  
   - 适合展示原因：能补充说明误差结构变化。  
   - 不宜上升为主结论原因：当基准 Bias 很小或接近 0 时，改善百分比会被放大，解释稳定性不如 `nRMSE`。  
   - source files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/maintenance_controlled_summary.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/blockage_controlled_summary.csv`。

## 4. Results Suitable for Discussion

1. **discussion angle：为什么最优距离不是固定的**  
   - supporting evidence：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/distance_error_curve.csv` 显示最优距离随 blockage on/off 改变；风速分箱与风向扇区中的最优距离也不同。  
   - relevant files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/distance_error_curve.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`。

2. **discussion angle：为什么某些远距离口径统计表现较好**  
   - supporting evidence：blockage off 时 upstream point 的 overall 最优距离达到 400 m，风向扇区中 `0-30` 的最优甚至是 250 m upstream。  
   - relevant files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/distance_error_curve.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`。

3. **discussion angle：为什么 nRMSE 和 Bias 的最优距离可能不同**  
   - supporting evidence：rotor-disc mean + blockage on 的最优 `nRMSE` 在 70 m，但最小 `abs_bias` 在 60 m。  
   - relevant files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/distance_error_curve.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/05_distance_vs_bias.png`。

4. **discussion angle：阻塞效应为什么对某些候选更有效**  
   - supporting evidence：blockage 对 rotor-disc mean 的平均改善明显高于 upstream point；0–20 m 平均恶化而 61–160 m 整体为正。  
   - relevant files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/blockage_controlled_summary.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/03_blockage_effect_summary.png`。

5. **discussion angle：风向依赖是否可能与阵列方向有关**  
   - supporting evidence：不同 30° 扇区的最优候选和最优 blockage 设置变化明显，且扇区最优距离跨度较大。  
   - relevant files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/09_wind_direction_bin_performance.png`。

6. **discussion angle：维护修正收益为什么具有月份依赖性**  
   - supporting evidence：维护修正月均 `nRMSE` 改善在 2 月达到 41.08%，4–6 月仅约 0.91%–2.39%。  
   - relevant files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/maintenance_controlled_monthly.csv`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/02_maintenance_effect_by_month.png`。

7. **discussion angle：ERA5/气象输入作为历史模拟输入的边界**  
   - supporting evidence：当前结果统一依赖 `场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv` 这一单一气象输入文件，但在现有 chapter 4 结果文件中尚未给出其数据源、偏差特征与代表性说明。  
   - relevant files：`/tmp/workspace/19bdxx/Wake-Blockage-Models/chapter4_results_analysis.py`；`/tmp/workspace/19bdxx/Wake-Blockage-Models/ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv`。

## 5. Auxiliary Checks Only

1. **单个风速段的偶然最优**  
   - 原因：例如 `13+` 最优为 `upstream_1m + blockage_on`，这更像极端工况下的局部适配，不适合上升为总体推荐。

2. **样本较少扇区的最优结果**  
   - 原因：风向 `240-270`、`270-300` 等扇区样本较少，局部最优可能对样本构成敏感。  
   - source：`/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/chapter4_analysis_report.md` 指出扇区样本范围仅 622–2781。

3. **单个月份的 ranking 第一名**  
   - 原因：月度第一名不稳定，且“第一”与“稳定前列”不是同一概念。

4. **all_samples 下的总体结论**  
   - 原因：`all_samples` 会混入限电影响；它可作辅助检查，但不应替代 `not_curtailed` 主结论。

5. **单个 case 中的局部反向/局部最优时刻**  
   - 原因：案例窗口可用于图示，但个别时刻的局部最好/最差不具有论文主结论层面的统计稳健性。

## 6. Results Not Yet Strong Enough

1. **“blockage 应无条件纳入所有尾流模型”**  
   - 还缺什么：缺少跨候选一致性；短距离带与部分月份存在恶化；缺少更强物理解释或独立观测佐证。

2. **“rotor-disc mean 明显优于 upstream point”**  
   - 还缺什么：当前更像距离带竞争，而非类型绝对胜负；需要更清晰的分层比较和物理解释。

3. **“60 m 是最终最佳距离”**  
   - 还缺什么：缺少对稳健性权重的正式说明；strict optimum 与 robust optimum 不一致；不同工况最优距离会变化。

4. **“风向依赖已经说明了阵列几何机制”**  
   - 还缺什么：缺少布局方向、机组相对位置、阻塞证据与流向关系的联动分析图。

5. **“维护台数与误差改善存在稳定定量关系”**  
   - 还缺什么：当前 overall `maintenance_count_vs_nRMSE_improvement_corr` 没有有限值，尚无稳健量化证据。

6. **“风速/风向局部最优可以直接作为工程推荐”**  
   - 还缺什么：缺少交叉验证、独立时间段验证与样本均衡性分析。

7. **“当前气象输入足以代表一般历史模拟条件”**  
   - 还缺什么：需要确认气象输入来源、时空分辨率、偏差特征，以及与实测风况的一致性边界。

8. **“blockage 的物理收益已经被独立证实”**  
   - 还缺什么：若要把 blockage 写得更强，最好补充激光雷达、流场证据或更直接的 blockage 物理诊断图。

9. **“月度最优候选清单可以直接写进主结论”**  
   - 还缺什么：需要先澄清 `monthly_candidate_rank.csv` 与 `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/single_experiment_evaluation/ranking_with_maintenance_monthly.csv` 的排名口径差异，避免混淆“分 blockage 排名”和“全组合排名”。

## 7. Recommended Core Storyline for the Paper

1. **先讲什么**  
   先讲样本域构造：共同时间交集、缺测剔除、`not_curtailed` 主评价域、统一 MW 单位。这是后续所有比较成立的前提。

2. **再讲什么**  
   第二步讲维护状态修正，强调这是运行状态一致性处理，并展示其对误差评价的系统性影响。

3. **第三步讲什么**  
   第三步讲 blockage，明确其为条件性收益：总体倾向改善，但不是所有候选、所有距离、所有月份都改善。

4. **第四步讲什么**  
   第四步讲等效入流风速定义与距离依赖，区分 strict optimum 与 robust recommendation。

5. **第五步讲什么**  
   第五步讲跨月份稳健性，给出推荐的稳定候选群/距离带，而不是逐月切换最优。

6. **第六步讲什么**  
   最后补充风速/风向工况依赖和典型案例，用于说明边界与可视化支撑，而不作为主因果结论。

7. **哪些图表作为主图**  
   主图优先：`01_time_coverage.png`、`02_maintenance_effect_by_month.png`、`03_blockage_effect_summary.png`、`04_distance_vs_nrmse.png`、`06_monthly_nrmse_heatmap.png`（或 `07_candidate_rank_heatmap.png` 二选一）。

8. **哪些表作为主表**  
   主表优先：maintenance controlled overall summary、blockage controlled overall summary、robust candidate top ranks。

9. **哪些内容放补充材料或附录**  
   单实验 ranking 全表、全部月度排名、风速/风向分箱全表、三个 case 明细表、`distance_vs_bias` 图、全部 CSV 明细。

10. **哪些结果放 Discussion**  
   月份差异原因、距离迁移机制、风向依赖的阵列几何解释、气象输入边界、robustness 权重选择。

## 8. Recommended Figures and Tables for Manuscript

### Main figures
1. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/01_time_coverage.png`  
   - supports：共同样本域是公平比较前提  
   - 正文适合度：高  
   - 是否需要重画：建议重画为更论文化版本，并叠加“19586 common timestamps / 830 skipped / 18467 effective not_curtailed”注释

2. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/02_maintenance_effect_by_month.png`  
   - supports：维护状态修正具有系统性影响且收益具月份依赖  
   - 正文适合度：高  
   - 是否需要重画：建议重画，增加误差条或至少标注月份样本量

3. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/03_blockage_effect_summary.png`  
   - supports：blockage 收益具有候选类型依赖  
   - 正文适合度：高  
   - 是否需要重画：建议增加候选数和离散度信息，避免只看均值

4. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/04_distance_vs_nrmse.png`  
   - supports：距离依赖与最优距离迁移  
   - 正文适合度：高  
   - 是否需要重画：建议突出 recommended distance band，弱化过多曲线噪声

5. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/06_monthly_nrmse_heatmap.png`  
   - supports：月度最优并不固定、需要稳健性推荐  
   - 正文适合度：中高  
   - 是否需要重画：建议只保留核心候选，提升可读性

### Main tables
1. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/maintenance_controlled_summary.csv`  
   - supports：维护修正主结论  
   - 正文适合度：高  
   - 是否需要重画：需要整理为论文表，仅保留 `not_curtailed overall` 核心指标

2. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/controlled_comparison/blockage_controlled_summary.csv`  
   - supports：blockage 条件性收益  
   - 正文适合度：高  
   - 是否需要重画：需要整理为“overall + candidate type + distance band”简表

3. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/robust_candidate_selection.csv`  
   - supports：稳健候选/稳定距离带推荐  
   - 正文适合度：高  
   - 是否需要重画：需要提炼 top 5 或 top 10，避免整表过长

### Supplementary figures
1. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/05_distance_vs_bias.png`  
   - supports：`nRMSE` 与 Bias 最优距离不一致  
   - 正文适合度：中  
   - 是否需要重画：可放补充，正文只引用现象

2. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/07_candidate_rank_heatmap.png`  
   - supports：月度名次不稳定  
   - 正文适合度：中  
   - 是否需要重画：若正文已有 `06`，此图可放补充

3. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/08_wind_speed_bin_performance.png`  
   - supports：风速工况依赖  
   - 正文适合度：中  
   - 是否需要重画：建议只在需要强调工况依赖时保留正文，否则放补充

4. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/09_wind_direction_bin_performance.png`  
   - supports：风向工况依赖  
   - 正文适合度：中  
   - 是否需要重画：建议增加样本量标注，否则更适合作补充

5. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/case_maintenance_improvement.png`  
   - supports：维护修正案例支撑  
   - 正文适合度：中  
   - 是否需要重画：可选，用于结果可视化增强

6. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/case_blockage_improvement.png`  
   - supports：blockage 条件性收益案例  
   - 正文适合度：中低  
   - 是否需要重画：若保留，建议精简为单页图

7. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/figures/case_candidate_difference.png`  
   - supports：推荐候选总体优于传统候选但局部不恒优  
   - 正文适合度：中低  
   - 是否需要重画：更适合作补充

### Supplementary tables
1. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/single_experiment_evaluation/ranking_with_maintenance_overall.csv`
2. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/single_experiment_evaluation/ranking_without_maintenance_overall.csv`
3. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/single_experiment_evaluation/ranking_with_maintenance_monthly.csv`
4. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/single_experiment_evaluation/ranking_without_maintenance_monthly.csv`
5. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/monthly_candidate_rank.csv`
6. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`
7. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`
8. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/case_studies/case_maintenance_improvement.csv`
9. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/case_studies/case_blockage_improvement.csv`
10. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/case_studies/case_candidate_difference.csv`
- supports：提供完整可复核明细  
- 正文适合度：低到中  
- 是否需要重画：通常不需要，整理标题和字段说明即可

### Not recommended
1. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/measured_power_quality_check.csv`  
   - 原因：重要但更适合作为方法/数据附注，不适合作结果主表。

2. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/merged_common_samples.csv` / `.parquet`  
   - 原因：原始长表过大，不适合直接进入稿件。

3. `/tmp/workspace/19bdxx/Wake-Blockage-Models/comparison_results/candidate_columns_detected.csv`  
   - 原因：属于数据字典或附录材料，而非结果展示。

## 9. Suggested Paper Conclusions

1. 在统一气象输入、共同时间交集和非限电影响样本条件下，维护状态修正会系统性改变功率误差评价结果，因此应被视为历史验证中的运行状态一致性处理。

2. 在相同实验组和相同候选定义下，纳入 blockage 在当前样本上更常带来误差下降，但其收益具有明显的候选类型、距离带和月份依赖性。

3. 等效入流风速口径的表现存在明确距离依赖，且最优距离会随 blockage 设置与评价指标而变化，因此不宜将单一距离视为普适最优。

4. 对当前历史样本而言，跨月份稳定前列的候选主要集中在 blockage on 条件下的 upstream 60–80 m 与 rotor-disc mean 30–70 m 距离范围，而非某一个在所有月份均排名第一的单一口径。

5. 风速分箱和风向扇区结果说明候选口径的相对优劣具有工况依赖性，因此总体推荐应强调稳健性而不是局部工况下的最优表现。

6. 典型案例能够为整体统计结论提供可视化支撑，但论文主结论仍应以受控比较和整体统计结果为依据。

## 10. Final Recommendation

- 当前结果是否足够支撑投稿：**基本足够支撑投稿初稿**，前提是论文把定位放在“基于统一历史样本的尾流/阻塞/候选口径比较”，并保持表述克制，不把描述性统计写成普适性物理定律。

- 最需要补强的 3 件事：  
  1. 增加至少一种统计稳健性说明（例如 bootstrap、月度重采样或更明确的不确定性展示）；  
  2. 补充 blockage 与距离依赖的物理解释或独立证据（最好有流场/激光雷达/阵列几何支撑）；  
  3. 明确气象输入来源与适用边界，并在正文中说明 robust ranking 权重只是当前分析设定。

- 哪些结论可以放心写：  
  1. 共同样本域和统一评价口径是公平比较前提；  
  2. 维护状态修正会系统性影响验证结果；  
  3. blockage 的收益是条件性的，不是无条件普适收益；  
  4. 等效入流风速口径存在距离依赖；  
  5. 推荐应基于跨月份稳健性，而不是单月最优。

- 哪些结论需要谨慎写：  
  1. rotor-disc mean 与 upstream point 的优劣比较；  
  2. 风速/风向局部现象的解释；  
  3. 具体推荐距离（如 60 m）是否可外推；  
  4. blockage 为什么在某些月份或短距离带失效。

- 哪些结论暂时不要写：  
  1. “blockage 显著提升模型效果”；  
  2. “某一固定距离在所有条件下最优”；  
  3. “风向依赖已经证明阵列几何机制”；  
  4. “维护台数与误差改善存在稳定定量关系”；  
  5. “当前结果已经可直接外推到一般业务预测场景”。
