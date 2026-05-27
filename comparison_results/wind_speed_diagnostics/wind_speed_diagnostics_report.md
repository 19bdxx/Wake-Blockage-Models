# Wind Speed Diagnostics Report

## 1. Purpose and Data Sources

- **Purpose:** diagnose whether wind-speed mismatch helps explain station-power prediction error in the same common-time framework used by Chapter 4.
- **Common-sample basis:** `with_maintenance valid_time ∩ without_maintenance valid_time ∩ measured timestamp ∩ forecast valid_time`.
- **Main sample for interpretation:** `with_maintenance + enable_blockage=True + not_curtailed`, `n=18467`.
- **Data files used:**
  - `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/five_experiments_output_考虑维护-全月份/all_experiments_station_power_timeseries.csv`
  - `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/five_experiments_output_不考虑维护-全月份/all_experiments_station_power_timeseries.csv`
  - `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/场站实测数据/JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv`
  - `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv`
- **Generated outputs:** all CSVs, figures, and this report are under `comparison_results/wind_speed_diagnostics/`.

## 2. Available Wind-Speed Variables

- **Meteorological input wind speed:** `wind_speed` from the forecast input file.
- **Measured turbine mean wind speed:** `MZS_FAN_WINDSPEED_MEAN` from the lightweight SCADA-derived station file.
- **Model-derived station-level mean wind speed fields found in the lightweight experiment output:**
  - `mean_WS_eff_pywake_native_m_s` (`1` field family)
  - `mean_WS_rotor_disc_upstream*m_mean_m_s` (`14` distances)
  - `mean_WS_probe_upstream_*m_m_s` (`24` distances)
- **Excluded from the main comparison:** downstream probe speeds were not used as turbine-inflow proxies.
- **Variable inventory CSV:** `comparison_results/wind_speed_diagnostics/available_wind_speed_variables.csv`

## 3. Meteorological Wind Speed vs Measured Turbine Wind Speed

- **Comparison object:** meteorological input `wind_speed` vs measured turbine mean wind speed.
- **Sample range:** `with_maintenance`, common-time samples, both blockage states share the same meteorological input values.
- **Main sample:** `not_curtailed + enable_blockage=True`, `n=18467`.
- **Key metrics:** Bias=0.839 m/s, MAE=1.285 m/s, RMSE=1.680 m/s, r=0.912.
- **Monthly / conditional dependence:**
  - The meteorological input keeps a positive bias in every month of the main sample; monthly wind-speed bias vs monthly power bias correlation is 0.652.
  - The strongest positive meteorological wind-speed bias by measured wind-speed bin appears in `5-7` with Bias=1.033 m/s.
  - The strongest positive meteorological wind-speed bias by direction sector appears in `180-210` with Bias=1.282 m/s.
- **Figure paths:**
  - `comparison_results/wind_speed_diagnostics/figures/01_wind_speed_vs_measured_scatter.png`
  - `comparison_results/wind_speed_diagnostics/figures/03_monthly_bias_comparison.png`
  - `comparison_results/wind_speed_diagnostics/figures/04_wind_speed_bin_bias.png`
  - `comparison_results/wind_speed_diagnostics/figures/05_wind_direction_bin_bias.png`
- **Paper-ready statement:** The meteorological input wind speed is systematically higher than the measured turbine-mean wind speed over the common non-curtailed sample, indicating that part of the station-power overprediction can originate from inflow-input bias rather than wake-model structure alone.
- **Caution:** this measured reference is a turbine-mean SCADA quantity, not a free-stream mast or lidar inflow measurement.

## 4. Model-Derived Wind Speed vs Measured Turbine Wind Speed

- **Best model-speed field in the Chapter 4 main sample (`not_curtailed + blockage_on`):** `Rotor-disc upstream 70 m mean`.
- **Its metrics:** Bias=-0.038 m/s, MAE=1.008 m/s, RMSE=1.404 m/s, r=0.916.
- **Meteorological baseline for the same sample:** Bias=0.839 m/s, RMSE=1.680 m/s.
- **Relative interpretation:** the best `blockage_on` model-speed field reduces wind-speed RMSE by about 16.4% relative to the meteorological input.
- **Best model-speed field in `not_curtailed + blockage_off`:** `Rotor-disc upstream 160 m mean` with RMSE=1.484 m/s.
- **Chapter 4 links:**
  - Strict best power candidate: `Strict best Chapter 4 candidate (Rotor-disc upstream 70 m mean)`.
  - Robust recommended candidate: `Robust Chapter 4 recommendation (Upstream 60 m)`.
- **Direct conclusion:** model-derived turbine-speed proxies are clearly closer to the measured turbine mean than the raw meteorological input, and the best `blockage_on` field is also slightly better than the best `blockage_off` field.
- **Figure path:** `comparison_results/wind_speed_diagnostics/figures/01_wind_speed_vs_measured_scatter.png`
- **Paper-ready statement:** Several model-derived turbine-speed proxies are substantially closer to the measured turbine mean than the raw meteorological wind speed, supporting the interpretation that part of the Chapter 4 gain comes from improved inflow representation.
- **Limitation:** “closest wind speed” and “lowest power error” are related but not identical ranking criteria.

## 5. Relationship Between Wind-Speed Error and Power Error

- **Main comparison pairs:**
  - Meteorological input + PyWake internal power
  - WS_eff native + native power
  - Chapter 4 strict-best pair
  - Chapter 4 robust recommendation pair
- **Overall relationship findings (`comparison_results/wind_speed_diagnostics/wind_speed_error_power_error_relationship.csv`):**
  - Meteorological baseline: wind-speed Bias=0.839 m/s and power Bias=19.101 MW, with signed error correlation r=0.807.
  - Chapter 4 strict-best pair: wind-speed Bias=-0.038 m/s and power Bias=1.056 MW, with signed error correlation r=0.808 and absolute-error correlation r=0.758.
  - Chapter 4 robust pair: wind-speed Bias=-0.263 m/s and power Bias=-6.252 MW, with signed error correlation r=0.804.
- **Magnitude effect:** for the Chapter 4 strict-best pair, mean |power error| rises from 5.693 MW in `Q1` to 69.483 MW in `Q5` as |wind-speed error| rises from 0.137 to 2.518 m/s.
- **Direct conclusion:** wind-speed error and power error are strongly coupled, but the case studies show they are not perfectly equivalent.
- **Figure path:** `comparison_results/wind_speed_diagnostics/figures/02_wind_speed_error_vs_power_error.png`
- **Paper-ready statement:** Across the non-curtailed Chapter 4 main sample, larger wind-speed mismatch is associated with larger power mismatch, implying that wind-speed error explains a meaningful share of power-prediction error.
- **Caution:** the coupling is partly amplified by the nonlinear turbine power curve, so correlation alone should not be over-interpreted as full causal proof.

## 6. Monthly and Conditional Dependence

- **Monthly CSV:** `comparison_results/wind_speed_diagnostics/monthly_wind_power_bias.csv`
- **Wind-speed-bin CSV:** `comparison_results/wind_speed_diagnostics/wind_speed_bin_diagnostics.csv`
- **Wind-direction-bin CSV:** `comparison_results/wind_speed_diagnostics/wind_direction_bin_diagnostics.csv`
- **Main monthly finding:** for the Chapter 4 strict-best pair, monthly wind-speed bias vs monthly power bias correlation is 0.569.
- **Important residual month:** in July, the Chapter 4 strict-best pair still has wind-speed Bias=0.106 m/s but power Bias=12.098 MW, showing that small average wind-speed bias does not guarantee small power bias.
- **Conditional interpretation:**
  - The meteorological input overestimates measured turbine speed most strongly in lower-to-mid measured wind-speed bins and in southerly sectors around `180-210`.
  - The best Chapter 4 model-speed pairs reduce those biases substantially, but some bins still retain non-negligible power bias.
- **Figure paths:**
  - `comparison_results/wind_speed_diagnostics/figures/03_monthly_bias_comparison.png`
  - `comparison_results/wind_speed_diagnostics/figures/04_wind_speed_bin_bias.png`
  - `comparison_results/wind_speed_diagnostics/figures/05_wind_direction_bin_bias.png`
- **Paper-ready statement:** The wind-speed diagnostic is condition-dependent: meteorological bias is stronger in specific wind-speed bins and direction sectors, whereas residual power bias persists in some months even after wind-speed bias is largely reduced.

## 7. Case Studies

- **Case summary CSV:** `comparison_results/wind_speed_diagnostics/case_studies.csv`
- **Case figure:** `comparison_results/wind_speed_diagnostics/figures/06_case_studies.png`
- **Case 1 – input-bias-dominant:** `2024-03-29 20:45:00`. Meteorological wind-speed error is 4.948 m/s and meteorological power error is 89.962 MW; the Chapter 4 strict-best pair reduces the power error to 34.568 MW.
- **Case 2 – residual mismatch:** `2024-07-19 10:15:00`. The Chapter 4 strict-best pair has only 0.211 m/s wind-speed error but still 100.085 MW power error.
- **Case 3 – good match:** `2024-04-18 12:30:00`. The Chapter 4 strict-best pair simultaneously keeps wind-speed and power errors close to zero.
- **Direct conclusion:** the case studies support a mixed diagnosis: some bad power predictions are input-wind problems, while others remain after wind-speed alignment improves.

## 8. Implications for Chapter 4 Results

- The persistent positive bias of the raw meteorological input helps explain why the more processed turbine-speed proxies outperform raw-input-based power estimates.
- The Chapter 4 strict-best candidate (`Rotor-disc upstream 70 m mean`) is also the closest `blockage_on` wind-speed proxy to the measured turbine mean in the main sample, which strengthens the interpretation that its power advantage is not accidental.
- The Chapter 4 robust recommendation (`Upstream 60 m`) is not the single closest wind-speed field overall, but it still shows much smaller wind-speed bias and power bias than the meteorological baseline; this is consistent with its robustness-oriented role.
- Because July still shows a sizable power bias despite small mean wind-speed bias, not all Chapter 4 error can be attributed to wind-speed input mismatch; residual wake/blockage structure, power-curve adaptation, maintenance-state residuals, or data-quality issues likely remain.
- **Recommended placement in the paper:** the numeric diagnostic itself fits naturally as a short subsection in Chapter 4 Results, while its interpretation as an evaluation-boundary condition belongs in Chapter 5 Discussion.

## 9. Paper-Ready Statements

1. The raw meteorological wind speed is systematically higher than the measured turbine-mean wind speed on the common non-curtailed sample, so part of the station-power overprediction is attributable to inflow-input bias.
2. Model-derived turbine-speed proxies, especially the Chapter 4 best `blockage_on` candidate, are substantially closer to the measured turbine mean than the raw meteorological input.
3. Wind-speed error and power error are strongly correlated across timestamps, indicating that wind-speed mismatch explains a meaningful share of power-prediction error.
4. However, months and cases remain in which power bias stays large even when mean wind-speed bias is small, implying residual model-structure or operating-state error beyond wind-speed input mismatch.

## 10. Limitations and TODOs

- The measured wind-speed reference is a turbine-mean SCADA quantity, not an independent free-stream inflow observation.
- The lightweight station output only provides station-level mean model wind-speed fields; it does not preserve every turbine-level detail in the report outputs.
- Wind-direction conditioning uses forecast wind direction because a lightweight measured direction reference was not found in the aligned comparison files.
- A stronger causal claim would benefit from turbine-level matched cases, explicit curtailed/maintenance-residual diagnostics, and independent inflow observations such as mast or lidar.

## Final Judgments

1. **Does the meteorological input show obvious bias versus measured turbine wind speed?** Yes. It is positively biased in the main non-curtailed sample by about 0.839 m/s, with RMSE 1.680 m/s.
2. **Is model-derived wind speed closer to measured wind speed than the meteorological input?** Yes. The best `blockage_on` model-speed field (`Rotor-disc upstream 70 m mean`) reduces RMSE to 1.404 m/s, clearly below the meteorological RMSE of 1.680 m/s.
3. **Is power error related to wind-speed error?** Yes. The signed correlation is about 0.808 for the Chapter 4 strict-best pair, and |power error| rises sharply across |wind-speed error| quintiles.
4. **Can part of the current power-prediction error be explained by wind-speed bias?** Yes. The meteorological baseline has both positive wind-speed bias and positive power bias, and much of that bias shrinks after switching to better turbine-speed proxies.
5. **Should this analysis sit in Chapter 4 Results or Chapter 5 Discussion?** The diagnostic results and summary figures fit in Chapter 4 Results; the broader implication that meteorological-input error constrains model evaluation should be emphasized in Chapter 5 Discussion.
6. **What else is still needed?** Independent inflow measurements, turbine-level matched diagnostics, and more explicit separation of residual maintenance/curtailment/data-quality cases would make the argument more convincing.
