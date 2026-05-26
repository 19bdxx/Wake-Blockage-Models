# Copilot 第 4 章补充要求：分析结论与论文可用表述

> 建议将本文件放在 GitHub 仓库根目录，文件名可设为：  
> `COPILOT_CHAPTER_4_CONCLUSION_REQUIREMENTS.md`
>
> 本文件用于补充 `COPILOT_WRITE_CHAPTER_4_REQUEST.md`。  
> 当前第 4 章已经生成了初步结果，但还需要 Copilot 将分析结论、证据链、图表解释和论文可用表述写得更充分。

---

# 1. 本补充任务目标

请 Copilot 在现有第 4 章结果分析基础上，进一步生成两类内容：

1. **更新论文第 4 章正文**
   - 文件：`paper_drafts/paper_draft_chapter_4.md`
   - 要求：保留已有结构，但每个结果小节都要增加更明确的“本节结论”和“论文可用表述”。

2. **生成第 4 章分析报告**
   - 文件：`comparison_results/chapter4_analysis_report.md`
   - 要求：这是支撑第 4 章写作的详细分析报告，不是论文正文。报告可以更详细地记录样本数、控制变量、CSV路径、图表路径、异常现象和结论解释。

---

# 2. 为什么需要分析报告

论文第 4 章不宜写得像实验日志，也不宜塞入过多辅助检查。  
但后续写论文、回复老师或整理 Discussion 时，需要清楚知道：

- 每个结论来自哪个 CSV；
- 每个图说明什么；
- 每个统计结果的样本数是多少；
- 哪些结果可以写成论文主结论；
- 哪些结果只是辅助检查；
- 哪些地方存在不确定性或矛盾；
- 哪些内容应放到第 5 章 Discussion 再解释。

因此，请将“论文正文”和“详细分析报告”分开输出。

---

# 3. 第 4 章正文需要补强的内容

请检查 `paper_drafts/paper_draft_chapter_4.md`，对每个小节补充以下内容。

## 3.1 每节必须包含一个小结句

每个结果小节末尾增加 1 段简短小结，格式可类似：

```text
Overall, this subsection indicates that ...
```

或中文：

```text
综上，本节结果表明……
```

小结需要明确回答该小节的问题，而不是只列数值。

例如：

- 4.1 应回答：后续比较为什么必须使用共同时间交集；
- 4.2 应回答：ranking 为什么只能作为概览；
- 4.3 应回答：维护状态修正是否会系统性影响模型评价；
- 4.4 应回答：阻塞效应是否在控制变量条件下带来改善；
- 4.5 应回答：等效入流风速口径是否具有明显距离依赖；
- 4.6 应回答：是否可以逐月自由选择最优口径；
- 4.7/4.8 应回答：模型表现是否受风速/风向工况影响；
- 4.9 应回答：典型案例是否支持统计结论。

## 3.2 每节必须给出证据链

每个主要结论必须包含：

```text
分析对象
控制变量
样本范围
样本数
核心指标变化
对应 CSV
对应图表
可写入论文的结论
```

例如，维护状态小节不能只写：

```text
维护后 nRMSE 改善 100%。
```

而应写：

```text
在共同时间交集、not_curtailed 样本、固定 candidate_power_col 和 enable_blockage 条件下，共比较 80 个 overall 组合，nRMSE 改善比例为 100%。结果来源为 ...csv，图示为 ...png。该结果说明维护状态修正会系统性影响模型验证结果，因此后续模型比较应采用运行状态一致的实测功率口径。
```

## 3.3 每节需要区分“结果”和“解释”

第 4 章可以进行简单解释，但不要过度讨论机理。请使用以下边界：

- 第 4 章写：
  - 观察到了什么；
  - 指标如何变化；
  - 图表显示了什么；
  - 该结果支持什么直接结论。

- 第 5 章 Discussion 再写：
  - 为什么会这样；
  - 物理机制；
  - 与文献对比；
  - 局限性；
  - 工程应用含义。

如果某段解释太深入，请标记：

```text
This point should be further discussed in Chapter 5.
```

---

# 4. 需要生成的 chapter4_analysis_report.md 结构

请生成：

```text
comparison_results/chapter4_analysis_report.md
```

建议结构如下：

```markdown
# Chapter 4 Analysis Report

## 1. Executive Summary
- 本章最重要的 5–8 个发现
- 哪些发现适合写入论文主结论
- 哪些发现需要在 Discussion 中进一步解释

## 2. Data Coverage and Sample Construction
### 2.1 Common time range
### 2.2 all_samples and not_curtailed samples
### 2.3 Unit consistency
### 2.4 Main measured target

## 3. Single-Experiment Ranking
### 3.1 Key rankings
### 3.2 Why ranking alone is insufficient
### 3.3 Paper-ready statement

## 4. Maintenance-State Correction
### 4.1 Controlled variables
### 4.2 Overall results
### 4.3 Monthly results
### 4.4 Relation with maintenance count
### 4.5 Paper-ready statement
### 4.6 What should be discussed later

## 5. Blockage Effect
### 5.1 Controlled variables
### 5.2 Overall results
### 5.3 Candidate-type dependence
### 5.4 Monthly / wind-speed / wind-direction dependence
### 5.5 Paper-ready statement
### 5.6 Open questions

## 6. Equivalent Inflow Wind-Speed Definitions
### 6.1 Overall ranking
### 6.2 Distance-error relationship
### 6.3 Point speed vs rotor-disc mean
### 6.4 Bias and nRMSE consistency
### 6.5 Paper-ready statement
### 6.6 Open questions

## 7. Monthly Robustness
### 7.1 Monthly best candidates
### 7.2 Stable candidates
### 7.3 Stability score definition
### 7.4 Paper-ready statement

## 8. Wind-Speed and Wind-Direction Dependence
### 8.1 Wind-speed bins
### 8.2 Wind-direction sectors
### 8.3 Paper-ready statement
### 8.4 What needs Discussion

## 9. Case Studies
### 9.1 Maintenance case
### 9.2 Blockage case
### 9.3 Candidate-distance case
### 9.4 What each case supports

## 10. Recommended Statements for the Paper
### 10.1 Results section statements
### 10.2 Discussion section statements
### 10.3 Conclusion section statements

## 11. Limitations and TODO
```

---

# 5. 必须写入报告的关键结论类型

请至少形成以下类型的结论。

## 5.1 数据覆盖结论

需要明确：

- 共同样本时刻数；
- 时间范围；
- 为什么使用共同时间交集；
- 维护缺失跳过样本的影响；
- `not_curtailed` 为什么是主评价样本。

## 5.2 维护状态修正结论

需要明确：

- 是否控制了 candidate 和 blockage；
- 总组合数；
- MAE / RMSE / nRMSE / |Bias| 改善比例；
- 改善是否一致；
- 是否与维护台数或月份有关；
- 论文中应如何定位维护状态修正：
  - 不是模型创新；
  - 是运行状态一致性处理；
  - 是实测验证公平性的必要条件。

## 5.3 阻塞效应结论

需要明确：

- 是否控制了 candidate 和 maintenance；
- 阻塞开启后改善比例；
- 改善主要体现在哪些指标；
- 是否对所有候选一致；
- 是否与候选类型、距离、月份、风速、风向有关；
- 如果出现“平均改善但某些稳健指标不推荐”的矛盾，要解释。

## 5.4 等效入流风速口径结论

需要明确：

- 哪些候选整体表现好；
- 点风速和 rotor-disc mean 的差异；
- 最优距离是否固定；
- 是否存在距离带；
- nRMSE 和 Bias 是否同步；
- 推荐候选是 strict metric-optimal 还是 physically interpretable；
- 不能逐月自由选择最优。

## 5.5 工况依赖结论

需要明确：

- 风速段差异；
- 风向扇区差异；
- 哪些分析足够写进第 4 章；
- 哪些分析更适合放入 Discussion。

---

# 6. 论文可用表述要求

请在 `chapter4_analysis_report.md` 中为每个关键发现提供 1–2 句“可直接改写进论文”的表述。

格式示例：

```markdown
**Paper-ready statement:**  
在共同时间交集与非限电样本条件下，维护状态修正使相同候选口径和相同阻塞设置下的 nRMSE 均得到改善，说明运行状态一致性处理对真实场站功率验证具有重要影响。
```

注意：

- 表述要克制；
- 不要夸大；
- 不要写成最终结论；
- 不要说“显著”除非做了统计显著性检验；
- 不要把 ERA5/再分析输入下的历史模拟写成业务预测结论。

---

# 7. 图表解释要求

对每张图，报告中需要写：

```text
Figure path
Data source CSV
What it shows
Main observation
How it supports the Results chapter
Potential caveat
```

至少覆盖：

```text
01_time_coverage.png
02_maintenance_effect_by_month.png
03_blockage_effect_summary.png
04_distance_vs_nrmse.png
05_distance_vs_bias.png
06_monthly_nrmse_heatmap.png
07_candidate_rank_heatmap.png
08_wind_speed_bin_performance.png
09_wind_direction_bin_performance.png
case_maintenance_improvement.png
case_blockage_improvement.png
case_candidate_difference.png
```

如果某图不存在，请说明原因并列入 TODO。

---

# 8. 输出前自查清单

Copilot 完成后，请自查：

- [ ] 是否更新了 `paper_drafts/paper_draft_chapter_4.md`；
- [ ] 是否生成了 `comparison_results/chapter4_analysis_report.md`；
- [ ] 第 4 章每个小节是否都有清楚小结；
- [ ] 报告中每个主要结论是否有证据链；
- [ ] 是否区分了 Results 与 Discussion；
- [ ] 是否说明了哪些结论适合写进论文；
- [ ] 是否没有编造不存在的数值；
- [ ] 是否所有 CSV 和图表路径真实存在；
- [ ] 是否没有把维护状态写成核心模型创新；
- [ ] 是否没有将当前结果夸大为业务预测验证。

---

# 9. 推荐给 Copilot 的启动指令

请对 Copilot 发送：

```text
请阅读 COPILOT_CHAPTER_4_CONCLUSION_REQUIREMENTS.md，并基于当前 paper_drafts/paper_draft_chapter_4.md、comparison_results 下的 CSV 和 figures，补强第 4 章结果表述。请同时生成 comparison_results/chapter4_analysis_report.md，用于记录每个结论的证据链、图表解释和论文可用表述。不要编造不存在的数值或图表路径。
```
