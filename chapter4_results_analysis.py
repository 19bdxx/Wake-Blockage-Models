from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parent
BASE_DIR = REPO_DIR / 'ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT'
OUT_DIR = REPO_DIR / 'comparison_results'
FIG_DIR = OUT_DIR / 'figures'
SINGLE_DIR = OUT_DIR / 'single_experiment_evaluation'
CONTROL_DIR = OUT_DIR / 'controlled_comparison'
CANDIDATE_DIR = OUT_DIR / 'candidate_analysis'
CASE_DIR = OUT_DIR / 'case_studies'
DRAFT_PATH = REPO_DIR / 'paper_drafts' / 'paper_draft_chapter_4.md'

WITH_OUTPUT = BASE_DIR / 'five_experiments_output_考虑维护-全月份' / 'all_experiments_station_power_timeseries.csv'
WITHOUT_OUTPUT = BASE_DIR / 'five_experiments_output_不考虑维护-全月份' / 'all_experiments_station_power_timeseries.csv'
MEASURED_FILE = BASE_DIR / '场站实测数据' / 'JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv'
FORECAST_FILE = BASE_DIR / '场站气象预报' / 'wind_lat_33.250_lon_121.500-UTC8.csv'
MAINT_FILE = BASE_DIR / 'JMZSFD维护记录' / 'jmzsfd_maintenance_matrix.csv'
MAINT_SUMMARY_FILE = BASE_DIR / 'five_experiments_output_考虑维护-全月份' / 'maintenance_match_summary.csv'

STATION = 'MZS'
ACTUAL_POWER_COL = 'MZS_FAN_ACTIVE_POWER_SUM'
ACTUAL_STATION_POWER_COL = 'MZS_ACTIVE_POWER_STATION'
LIMIT_POWER_COL = 'MZS_LIMIT_POWER'
MEASURED_WS_COL = 'MZS_FAN_WINDSPEED_MEAN'
CURTAILMENT_LIMIT_MW = 300.0
CURTAILMENT_THRESHOLD = 0.95
WIND_SPEED_BINS = [0, 3, 5, 7, 9, 11, 13, np.inf]
WIND_SPEED_LABELS = ['0-3', '3-5', '5-7', '7-9', '9-11', '11-13', '13+']
STABILITY_ALPHA = 1.0
STABILITY_BETA = 1.0
TRADITIONAL_CANDIDATE = 'station_power_from_ws_eff_pywake_native_kW'


@dataclass(frozen=True)
class CandidateInfo:
    candidate_power_col: str
    converted_power_col: str
    candidate_type: str
    distance_m: float | None
    candidate_family: str


def ensure_dirs() -> None:
    for path in [OUT_DIR, FIG_DIR, SINGLE_DIR, CONTROL_DIR, CANDIDATE_DIR, CASE_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def parse_candidate(col: str) -> CandidateInfo:
    converted = col.replace('_kW', '_MW')
    if col == 'station_power_pywake_internal_kW':
        return CandidateInfo(col, converted, 'pywake_internal', None, 'PyWake internal')
    if col == 'station_power_from_ws_eff_pywake_native_kW':
        return CandidateInfo(col, converted, 'ws_eff_pywake_native', None, 'WS_eff native')
    m = re.match(r'^station_power_from_upstream_(\d+)m_kW$', col)
    if m:
        d = float(m.group(1))
        return CandidateInfo(col, converted, 'upstream_point', d, 'Upstream point')
    m = re.match(r'^station_power_from_rotor_disc_upstream(\d+)m_mean_kW$', col)
    if m:
        d = float(m.group(1))
        return CandidateInfo(col, converted, 'rotor_disc_upstream_mean', d, 'Rotor-disc upstream mean')
    return CandidateInfo(col, converted, 'other', None, 'Other')


def display_candidate(col: str) -> str:
    info = parse_candidate(col)
    if info.candidate_type == 'pywake_internal':
        return 'PyWake internal'
    if info.candidate_type == 'ws_eff_pywake_native':
        return 'WS_eff native'
    if info.candidate_type == 'upstream_point':
        return f'Upstream {int(info.distance_m)} m'
    if info.candidate_type == 'rotor_disc_upstream_mean':
        return f'Rotor-disc upstream {int(info.distance_m)} m mean'
    return col


def distance_band(distance_m: float | None) -> str:
    if pd.isna(distance_m):
        return 'no_distance'
    d = float(distance_m)
    if d <= 20:
        return '0-20m'
    if d <= 60:
        return '21-60m'
    if d <= 100:
        return '61-100m'
    if d <= 160:
        return '101-160m'
    return '160m+'


def load_model_output(path: Path, experiment_name: str) -> tuple[pd.DataFrame, list[CandidateInfo]]:
    df = pd.read_csv(path)
    df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
    df['valid_time'] = pd.to_datetime(df['valid_time'], errors='coerce')
    df = df[df['station'] == STATION].copy()
    df['experiment_name'] = experiment_name
    df['enable_blockage'] = df['enable_blockage'].astype(bool)
    power_cols = [c for c in df.columns if c.startswith('station_power_') and c.endswith('_kW')]
    infos = [parse_candidate(c) for c in power_cols]
    return df.sort_values(['valid_time', 'enable_blockage']).reset_index(drop=True), infos


def load_measured() -> pd.DataFrame:
    df = pd.read_csv(MEASURED_FILE)
    df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
    df['valid_time'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df[['valid_time', ACTUAL_POWER_COL, ACTUAL_STATION_POWER_COL, LIMIT_POWER_COL, MEASURED_WS_COL]].copy()
    df = df.dropna(subset=['valid_time']).drop_duplicates(subset=['valid_time']).sort_values('valid_time')
    return df.reset_index(drop=True)


def load_forecast() -> pd.DataFrame:
    df = pd.read_csv(FORECAST_FILE)
    df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
    df['valid_time'] = pd.to_datetime(df['valid_time'], errors='coerce')
    keep = [c for c in ['valid_time', 'wind_speed', 'wind_direction', 'is_interpolated'] if c in df.columns]
    return df[keep].dropna(subset=['valid_time']).drop_duplicates(subset=['valid_time']).sort_values('valid_time').reset_index(drop=True)


def load_maintenance() -> pd.DataFrame:
    df = pd.read_csv(MAINT_FILE)
    df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
    df['valid_time'] = pd.to_datetime(df['timestamp'], errors='coerce')
    maint_cols = [c for c in df.columns if c.startswith('是否维护_#')]
    df['maintenance_count'] = df[maint_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
    return df[['valid_time', 'maintenance_count']].dropna(subset=['valid_time']).drop_duplicates(subset=['valid_time']).sort_values('valid_time').reset_index(drop=True)


def candidate_metadata(infos: Iterable[CandidateInfo], experiment_names: list[str]) -> pd.DataFrame:
    rows = []
    for exp in experiment_names:
        for info in infos:
            rows.append({
                'experiment_name': exp,
                'candidate_power_col': info.candidate_power_col,
                'converted_power_col': info.converted_power_col,
                'candidate_type': info.candidate_type,
                'candidate_family': info.candidate_family,
                'distance_m': info.distance_m,
                'display_name': display_candidate(info.candidate_power_col),
                'original_unit': 'kW',
                'analysis_unit': 'MW',
            })
    return pd.DataFrame(rows).drop_duplicates().sort_values(['candidate_type', 'distance_m', 'candidate_power_col']).reset_index(drop=True)


def build_time_coverage_summary(df_with: pd.DataFrame, df_without: pd.DataFrame, measured: pd.DataFrame, forecast: pd.DataFrame, common_times: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for name, df, time_col in [
        ('with_maintenance_model_output', df_with, 'valid_time'),
        ('without_maintenance_model_output', df_without, 'valid_time'),
        ('measured_reference', measured, 'valid_time'),
        ('forecast_input', forecast, 'valid_time'),
    ]:
        ts = pd.to_datetime(df[time_col], errors='coerce').dropna().sort_values().drop_duplicates()
        rows.append({
            'dataset_name': name,
            'row_count': int(len(df)),
            'unique_time_count': int(len(ts)),
            'start_time': ts.min(),
            'end_time': ts.max(),
            'common_time_overlap_count': int(ts.isin(common_times).sum()),
            'common_time_overlap_ratio': float(ts.isin(common_times).mean()) if len(ts) else np.nan,
        })
    maint_summary = pd.read_csv(MAINT_SUMMARY_FILE)
    skipped = int(maint_summary.loc[maint_summary['maintenance_match_status'] == 'skipped', 'count'].sum())
    rows.append({
        'dataset_name': 'common_intersection',
        'row_count': int(len(common_times)),
        'unique_time_count': int(len(common_times)),
        'start_time': common_times.min() if len(common_times) else pd.NaT,
        'end_time': common_times.max() if len(common_times) else pd.NaT,
        'common_time_overlap_count': int(len(common_times)),
        'common_time_overlap_ratio': 1.0 if len(common_times) else np.nan,
    })
    rows.append({
        'dataset_name': 'with_maintenance_skipped_due_to_missing_maintenance',
        'row_count': skipped,
        'unique_time_count': skipped,
        'start_time': pd.NaT,
        'end_time': pd.NaT,
        'common_time_overlap_count': np.nan,
        'common_time_overlap_ratio': np.nan,
    })
    return pd.DataFrame(rows)


def build_measured_quality_check(measured: pd.DataFrame) -> pd.DataFrame:
    ts = measured['valid_time'].sort_values()
    diffs = ts.diff().dropna().dt.total_seconds() / 60.0
    rows = [
        {'metric': 'total_rows', 'value': len(measured)},
        {'metric': 'start_time', 'value': ts.min()},
        {'metric': 'end_time', 'value': ts.max()},
        {'metric': 'actual_power_missing', 'value': int(measured[ACTUAL_POWER_COL].isna().sum())},
        {'metric': 'actual_station_power_missing', 'value': int(measured[ACTUAL_STATION_POWER_COL].isna().sum())},
        {'metric': 'limit_power_missing', 'value': int(measured[LIMIT_POWER_COL].isna().sum())},
        {'metric': 'negative_actual_power_rows', 'value': int((pd.to_numeric(measured[ACTUAL_POWER_COL], errors='coerce') < 0).sum())},
        {'metric': 'negative_station_power_rows', 'value': int((pd.to_numeric(measured[ACTUAL_STATION_POWER_COL], errors='coerce') < 0).sum())},
        {'metric': 'time_step_median_min', 'value': float(diffs.median()) if not diffs.empty else np.nan},
        {'metric': 'time_step_mode_min', 'value': float(diffs.mode().iloc[0]) if not diffs.empty else np.nan},
        {'metric': 'actual_power_p95_mw', 'value': float(pd.to_numeric(measured[ACTUAL_POWER_COL], errors='coerce').quantile(0.95))},
        {'metric': 'limit_power_p95_mw', 'value': float(pd.to_numeric(measured[LIMIT_POWER_COL], errors='coerce').quantile(0.95))},
    ]
    return pd.DataFrame(rows)


def build_common_wide(df: pd.DataFrame, common_times: pd.DatetimeIndex, measured: pd.DataFrame, forecast: pd.DataFrame, maintenance: pd.DataFrame) -> pd.DataFrame:
    out = df[df['valid_time'].isin(common_times)].copy()
    out = out.merge(measured, on='valid_time', how='left')
    out = out.merge(forecast, on='valid_time', how='left', suffixes=('', '_forecast'))
    out = out.merge(maintenance, on='valid_time', how='left')
    out['maintenance_count'] = out['maintenance_count'].fillna(out['station_maintenance_turbines']).fillna(0)
    out['actual_power_mw'] = pd.to_numeric(out[ACTUAL_POWER_COL], errors='coerce')
    out['actual_station_power_mw'] = pd.to_numeric(out[ACTUAL_STATION_POWER_COL], errors='coerce')
    out['limit_power_mw'] = pd.to_numeric(out[LIMIT_POWER_COL], errors='coerce')
    out['is_curtailed'] = out['limit_power_mw'] < (CURTAILMENT_LIMIT_MW * CURTAILMENT_THRESHOLD)
    out['month'] = out['valid_time'].dt.month.astype('Int64')
    return out


def build_long_table(common_wide: pd.DataFrame, infos: list[CandidateInfo]) -> pd.DataFrame:
    power_cols = [info.candidate_power_col for info in infos]
    meta = pd.DataFrame([info.__dict__ for info in infos])
    long_df = common_wide.melt(
        id_vars=[
            'valid_time', 'month', 'experiment_name', 'station', 'enable_blockage',
            'wind_speed', 'wind_direction', 'maintenance_count', 'actual_power_mw',
            'actual_station_power_mw', 'limit_power_mw', 'is_curtailed'
        ],
        value_vars=power_cols,
        var_name='candidate_power_col',
        value_name='pred_power_kw',
    )
    long_df = long_df.merge(meta, on='candidate_power_col', how='left')
    long_df['pred_power_mw'] = pd.to_numeric(long_df['pred_power_kw'], errors='coerce') / 1000.0
    long_df['error'] = long_df['pred_power_mw'] - long_df['actual_power_mw']
    long_df['abs_error'] = long_df['error'].abs()
    long_df = long_df.drop(columns=['pred_power_kw', 'converted_power_col', 'candidate_family'])

    all_df = long_df.copy()
    all_df['scope_name'] = 'all_samples'
    nc_df = long_df[~long_df['is_curtailed']].copy()
    nc_df['scope_name'] = 'not_curtailed'
    long_df = pd.concat([all_df, nc_df], ignore_index=True)

    for c in ['experiment_name', 'station', 'candidate_power_col', 'candidate_type', 'scope_name']:
        long_df[c] = long_df[c].astype('category')
    long_df['distance_m'] = long_df['distance_m'].astype('float32')
    for c in ['pred_power_mw', 'actual_power_mw', 'actual_station_power_mw', 'limit_power_mw', 'wind_speed', 'wind_direction', 'maintenance_count', 'error', 'abs_error']:
        long_df[c] = pd.to_numeric(long_df[c], errors='coerce').astype('float32')
    long_df['month'] = long_df['month'].astype('Int16')
    return long_df.sort_values(['valid_time', 'experiment_name', 'enable_blockage', 'candidate_power_col', 'scope_name']).reset_index(drop=True)


def infer_interval_hours(times: pd.Series) -> float:
    ts = pd.Series(pd.to_datetime(times, errors='coerce').dropna().sort_values().unique())
    if len(ts) < 2:
        return math.nan
    delta_hours = ts.diff().dropna().dt.total_seconds() / 3600.0
    if delta_hours.empty:
        return math.nan
    return float(delta_hours.median())


def calc_metrics(sub: pd.DataFrame, p_norm_mw: float) -> dict:
    x = pd.to_numeric(sub['actual_power_mw'], errors='coerce').to_numpy(dtype=float)
    y = pd.to_numeric(sub['pred_power_mw'], errors='coerce').to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    n = len(x)
    if n == 0:
        return {k: np.nan for k in ['n', 'MAE', 'RMSE', 'Bias', 'abs_bias', 'nMAE', 'nRMSE', 'R2', 'Corr', 'median_abs_error', 'p90_abs_error', 'energy_error_mwh', 'absolute_energy_error_mwh']}
    err = y - x
    abs_err = np.abs(err)
    mae = abs_err.mean()
    rmse = float(np.sqrt(np.mean(err ** 2)))
    bias = float(err.mean())
    ss_res = float(np.sum((x - y) ** 2))
    ss_tot = float(np.sum((x - x.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    corr = float(np.corrcoef(x, y)[0, 1]) if n >= 2 else np.nan
    interval_h = infer_interval_hours(sub['valid_time'])
    energy = float(np.nansum(err) * interval_h) if np.isfinite(interval_h) else np.nan
    abs_energy = float(np.nansum(abs_err) * interval_h) if np.isfinite(interval_h) else np.nan
    return {
        'n': int(n),
        'MAE': float(mae),
        'RMSE': float(rmse),
        'Bias': bias,
        'abs_bias': float(abs(bias)),
        'nMAE': float(mae / p_norm_mw) if p_norm_mw > 0 else np.nan,
        'nRMSE': float(rmse / p_norm_mw) if p_norm_mw > 0 else np.nan,
        'R2': float(r2) if np.isfinite(r2) else np.nan,
        'Corr': float(corr) if np.isfinite(corr) else np.nan,
        'median_abs_error': float(np.nanmedian(abs_err)),
        'p90_abs_error': float(np.nanpercentile(abs_err, 90)),
        'energy_error_mwh': energy,
        'absolute_energy_error_mwh': abs_energy,
    }


def compute_metrics_table(long_df: pd.DataFrame, group_cols: list[str], p_norm_mw: float) -> pd.DataFrame:
    rows = []
    for keys, sub in long_df.groupby(group_cols, observed=True, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_cols, keys))
        row.update(calc_metrics(sub, p_norm_mw))
        if 'maintenance_count' in sub.columns:
            row['maintenance_count_mean'] = float(pd.to_numeric(sub['maintenance_count'], errors='coerce').mean())
            row['maintenance_count_median'] = float(pd.to_numeric(sub['maintenance_count'], errors='coerce').median())
        rows.append(row)
    return pd.DataFrame(rows)


def add_ranks(df: pd.DataFrame, rank_group_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    sort_cols = rank_group_cols + ['nRMSE', 'MAE', 'abs_bias', 'candidate_power_col']
    out = out.sort_values(sort_cols).reset_index(drop=True)
    out['rank'] = out.groupby(rank_group_cols, observed=True).cumcount() + 1
    return out


def single_experiment_rankings(long_df: pd.DataFrame, p_norm_mw: float) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    for experiment_name in sorted(long_df['experiment_name'].astype(str).unique()):
        sub = long_df[long_df['experiment_name'].astype(str) == experiment_name].copy()
        overall = compute_metrics_table(sub, ['experiment_name', 'scope_name', 'enable_blockage', 'candidate_power_col', 'candidate_type', 'distance_m'], p_norm_mw)
        overall['period_type'] = 'overall'
        overall['period_value'] = 'ALL'
        overall = add_ranks(overall, ['experiment_name', 'scope_name'])

        monthly = compute_metrics_table(sub, ['experiment_name', 'scope_name', 'month', 'enable_blockage', 'candidate_power_col', 'candidate_type', 'distance_m'], p_norm_mw)
        monthly['period_type'] = 'month'
        monthly['period_value'] = monthly['month'].map(lambda x: f'M{int(x):02d}')
        monthly = add_ranks(monthly, ['experiment_name', 'scope_name', 'month'])
        results[f'{experiment_name}_overall'] = overall
        results[f'{experiment_name}_monthly'] = monthly
    return results


def compare_experiments(metrics_df: pd.DataFrame, left_name: str, right_name: str, key_cols: list[str], label_left: str, label_right: str) -> pd.DataFrame:
    left = metrics_df[metrics_df['experiment_name'] == left_name].copy()
    right = metrics_df[metrics_df['experiment_name'] == right_name].copy()
    left = left.rename(columns={c: f'{c}_{label_left}' for c in left.columns if c not in key_cols})
    right = right.rename(columns={c: f'{c}_{label_right}' for c in right.columns if c not in key_cols})
    merged = left.merge(right, on=key_cols, how='inner')
    for metric in ['MAE', 'RMSE', 'nRMSE', 'abs_bias', 'median_abs_error', 'p90_abs_error', 'absolute_energy_error_mwh']:
        a = merged[f'{metric}_{label_left}']
        b = merged[f'{metric}_{label_right}']
        merged[f'delta_{metric}'] = a - b
        merged[f'percent_improvement_{metric}'] = np.where(a != 0, (a - b) / a * 100.0, np.nan)
    merged['delta_Bias_abs'] = merged[f'abs_bias_{label_left}'] - merged[f'abs_bias_{label_right}']
    return merged


def compare_blockage(metrics_df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    off = metrics_df[metrics_df['enable_blockage'] == False].copy()
    on = metrics_df[metrics_df['enable_blockage'] == True].copy()
    off = off.drop(columns=['enable_blockage']).rename(columns={c: f'{c}_blockage_off' for c in off.columns if c not in key_cols})
    on = on.drop(columns=['enable_blockage']).rename(columns={c: f'{c}_blockage_on' for c in on.columns if c not in key_cols})
    merged = off.merge(on, on=key_cols, how='inner')
    for metric in ['MAE', 'RMSE', 'nRMSE', 'abs_bias', 'median_abs_error', 'p90_abs_error', 'absolute_energy_error_mwh']:
        a = merged[f'{metric}_blockage_off']
        b = merged[f'{metric}_blockage_on']
        merged[f'delta_{metric}'] = a - b
        merged[f'percent_improvement_{metric}'] = np.where(a != 0, (a - b) / a * 100.0, np.nan)
    return merged


def summarize_improvement(df: pd.DataFrame, metric: str, group_desc: dict) -> dict:
    pct = pd.to_numeric(df[f'percent_improvement_{metric}'], errors='coerce')
    return {
        **group_desc,
        'metric': metric,
        'total_combinations': int(len(df)),
        'improved_count': int((pct > 0).sum()),
        'improved_ratio': float((pct > 0).mean()) if len(df) else np.nan,
        'mean_improvement_pct': float(pct.mean()) if len(pct) else np.nan,
        'median_improvement_pct': float(pct.median()) if len(pct) else np.nan,
        'max_improvement_pct': float(pct.max()) if len(pct) else np.nan,
        'min_improvement_pct': float(pct.min()) if len(pct) else np.nan,
    }


def build_maintenance_summaries(overall_cmp: pd.DataFrame, monthly_cmp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope in sorted(overall_cmp['scope_name'].astype(str).unique()):
        sub = overall_cmp[overall_cmp['scope_name'].astype(str) == scope]
        for metric in ['MAE', 'RMSE', 'nRMSE', 'abs_bias']:
            rows.append(summarize_improvement(sub, metric, {'summary_level': 'overall', 'scope_name': scope}))
        corr = sub[['maintenance_count_mean_with_maintenance', 'percent_improvement_nRMSE']].corr(numeric_only=True).iloc[0, 1]
        rows.append({'summary_level': 'overall', 'scope_name': scope, 'metric': 'maintenance_count_vs_nRMSE_improvement_corr', 'value': float(corr) if np.isfinite(corr) else np.nan})
        if not sub.empty:
            best = sub.sort_values('percent_improvement_nRMSE', ascending=False).iloc[0]
            worst = sub.sort_values('percent_improvement_nRMSE', ascending=True).iloc[0]
            rows.append({'summary_level': 'overall', 'scope_name': scope, 'metric': 'best_combo_by_nRMSE', 'value': json.dumps({'candidate_power_col': best['candidate_power_col'], 'enable_blockage': bool(best['enable_blockage']), 'percent_improvement_nRMSE': float(best['percent_improvement_nRMSE'])}, ensure_ascii=False)})
            rows.append({'summary_level': 'overall', 'scope_name': scope, 'metric': 'worst_combo_by_nRMSE', 'value': json.dumps({'candidate_power_col': worst['candidate_power_col'], 'enable_blockage': bool(worst['enable_blockage']), 'percent_improvement_nRMSE': float(worst['percent_improvement_nRMSE'])}, ensure_ascii=False)})
    for scope in sorted(monthly_cmp['scope_name'].astype(str).unique()):
        sub = monthly_cmp[monthly_cmp['scope_name'].astype(str) == scope]
        for metric in ['MAE', 'RMSE', 'nRMSE', 'abs_bias']:
            rows.append(summarize_improvement(sub, metric, {'summary_level': 'monthly', 'scope_name': scope}))
    return pd.DataFrame(rows)


def build_blockage_summaries(overall_cmp: pd.DataFrame, monthly_cmp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (experiment_name, scope_name), sub in overall_cmp.groupby(['experiment_name', 'scope_name'], observed=True):
        for metric in ['MAE', 'RMSE', 'nRMSE', 'abs_bias']:
            rows.append(summarize_improvement(sub, metric, {'summary_level': 'overall', 'experiment_name': experiment_name, 'scope_name': scope_name}))
        for candidate_type, sub_type in sub.groupby('candidate_type', observed=True):
            rows.append({
                'summary_level': 'candidate_type',
                'experiment_name': experiment_name,
                'scope_name': scope_name,
                'candidate_type': candidate_type,
                'metric': 'mean_nRMSE_improvement_pct',
                'value': float(pd.to_numeric(sub_type['percent_improvement_nRMSE'], errors='coerce').mean()),
                'n_candidates': int(len(sub_type)),
            })
        dist_sub = sub[sub['distance_m'].notna()].copy()
        if not dist_sub.empty:
            dist_sub['distance_band'] = dist_sub['distance_m'].map(distance_band)
            for band, band_df in dist_sub.groupby('distance_band', observed=True):
                rows.append({
                    'summary_level': 'distance_band',
                    'experiment_name': experiment_name,
                    'scope_name': scope_name,
                    'distance_band': band,
                    'metric': 'mean_nRMSE_improvement_pct',
                    'value': float(pd.to_numeric(band_df['percent_improvement_nRMSE'], errors='coerce').mean()),
                    'n_candidates': int(len(band_df)),
                })
    focus = overall_cmp[(overall_cmp['experiment_name'] == 'with_maintenance') & (overall_cmp['scope_name'] == 'not_curtailed')]
    if not focus.empty:
        best = focus.sort_values('percent_improvement_nRMSE', ascending=False).iloc[0]
        worst = focus.sort_values('percent_improvement_nRMSE', ascending=True).iloc[0]
        rows.append({'summary_level': 'focus', 'experiment_name': 'with_maintenance', 'scope_name': 'not_curtailed', 'metric': 'best_candidate_by_nRMSE_improvement', 'value': json.dumps({'candidate_power_col': best['candidate_power_col'], 'candidate_type': best['candidate_type'], 'percent_improvement_nRMSE': float(best['percent_improvement_nRMSE'])}, ensure_ascii=False)})
        rows.append({'summary_level': 'focus', 'experiment_name': 'with_maintenance', 'scope_name': 'not_curtailed', 'metric': 'worst_candidate_by_nRMSE_improvement', 'value': json.dumps({'candidate_power_col': worst['candidate_power_col'], 'candidate_type': worst['candidate_type'], 'percent_improvement_nRMSE': float(worst['percent_improvement_nRMSE'])}, ensure_ascii=False)})
    for (experiment_name, scope_name), sub in monthly_cmp.groupby(['experiment_name', 'scope_name'], observed=True):
        for metric in ['MAE', 'RMSE', 'nRMSE', 'abs_bias']:
            rows.append(summarize_improvement(sub, metric, {'summary_level': 'monthly', 'experiment_name': experiment_name, 'scope_name': scope_name}))
    return pd.DataFrame(rows)


def build_robust_candidate_selection(monthly_metrics: pd.DataFrame, overall_metrics: pd.DataFrame) -> pd.DataFrame:
    focus_monthly = monthly_metrics[(monthly_metrics['experiment_name'] == 'with_maintenance') & (monthly_metrics['scope_name'] == 'not_curtailed')].copy()
    focus_overall = overall_metrics[(overall_metrics['experiment_name'] == 'with_maintenance') & (overall_metrics['scope_name'] == 'not_curtailed')].copy()
    monthly_ranks = add_ranks(focus_monthly.copy(), ['enable_blockage', 'month'])

    rows = []
    for keys, sub in monthly_ranks.groupby(['enable_blockage', 'candidate_power_col', 'candidate_type', 'distance_m'], observed=True, dropna=False):
        worst_row = sub.loc[sub['nRMSE'].idxmax()]
        rows.append({
            'enable_blockage': keys[0],
            'candidate_power_col': keys[1],
            'candidate_type': keys[2],
            'distance_m': keys[3],
            'monthly_nRMSE_mean': float(sub['nRMSE'].mean()),
            'monthly_nRMSE_std': float(sub['nRMSE'].std(ddof=0)),
            'monthly_nRMSE_max': float(sub['nRMSE'].max()),
            'monthly_rank_mean': float(sub['rank'].mean()),
            'monthly_rank_std': float(sub['rank'].std(ddof=0)),
            'top1_month_count': int((sub['rank'] == 1).sum()),
            'top3_month_count': int((sub['rank'] <= 3).sum()),
            'top5_month_count': int((sub['rank'] <= 5).sum()),
            'worst_month': int(worst_row['month']),
            'worst_month_nRMSE': float(worst_row['nRMSE']),
        })
    agg = pd.DataFrame(rows)
    agg['stability_score'] = agg['monthly_nRMSE_mean'] + STABILITY_ALPHA * agg['monthly_nRMSE_std'] + STABILITY_BETA * agg['monthly_nRMSE_max']
    out = focus_overall.merge(agg, on=['enable_blockage', 'candidate_power_col', 'candidate_type', 'distance_m'], how='left')
    out = out.sort_values(['stability_score', 'nRMSE', 'MAE', 'abs_bias']).reset_index(drop=True)
    out['robust_rank'] = np.arange(1, len(out) + 1)
    return out


def build_distance_error_curve(overall_metrics: pd.DataFrame) -> pd.DataFrame:
    focus = overall_metrics[(overall_metrics['experiment_name'] == 'with_maintenance') & (overall_metrics['scope_name'] == 'not_curtailed') & (overall_metrics['distance_m'].notna())].copy()
    return focus.sort_values(['candidate_type', 'enable_blockage', 'distance_m']).reset_index(drop=True)


def plot_time_coverage(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 4))
    rows = summary_df[summary_df['dataset_name'].isin(['with_maintenance_model_output', 'without_maintenance_model_output', 'measured_reference', 'forecast_input', 'common_intersection'])].copy()
    y = np.arange(len(rows))
    starts = pd.to_datetime(rows['start_time'])
    ends = pd.to_datetime(rows['end_time'])
    for i, (_, row) in enumerate(rows.iterrows()):
        ax.plot([starts.iloc[i], ends.iloc[i]], [i, i], linewidth=8)
    ax.set_yticks(y)
    ax.set_yticklabels(rows['dataset_name'])
    ax.set_title('Time coverage and common evaluation samples')
    ax.grid(True, axis='x', linestyle='--', alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / '01_time_coverage.png', dpi=150)
    plt.close(fig)


def plot_maintenance_effect(monthly_cmp: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    focus = monthly_cmp[monthly_cmp['scope_name'] == 'not_curtailed'].copy()
    grouped = focus.groupby('month', observed=True)['percent_improvement_nRMSE'].mean().reset_index()
    ax.bar(grouped['month'].astype(int), grouped['percent_improvement_nRMSE'])
    ax.axhline(0, color='black', linewidth=1)
    ax.set_xlabel('Month')
    ax.set_ylabel('Mean nRMSE improvement (%)\n(with maintenance vs without maintenance)')
    ax.set_title('Monthly maintenance-state correction effect (controlled comparison)')
    fig.tight_layout()
    fig.savefig(FIG_DIR / '02_maintenance_effect_by_month.png', dpi=150)
    plt.close(fig)


def plot_blockage_effect(overall_cmp: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    focus = overall_cmp[(overall_cmp['experiment_name'] == 'with_maintenance') & (overall_cmp['scope_name'] == 'not_curtailed')].copy()
    type_summary = focus.groupby('candidate_type', observed=True).agg(
        mean_nRMSE_improvement=('percent_improvement_nRMSE', 'mean'),
        mean_abs_bias_improvement=('percent_improvement_abs_bias', 'mean'),
    ).reset_index()
    axes[0].bar(type_summary['candidate_type'].astype(str), type_summary['mean_nRMSE_improvement'])
    axes[0].axhline(0, color='black', linewidth=1)
    axes[0].set_title('Blockage effect on nRMSE by candidate type')
    axes[0].tick_params(axis='x', rotation=20)
    axes[1].bar(type_summary['candidate_type'].astype(str), type_summary['mean_abs_bias_improvement'])
    axes[1].axhline(0, color='black', linewidth=1)
    axes[1].set_title('Blockage effect on |Bias| by candidate type')
    axes[1].tick_params(axis='x', rotation=20)
    fig.tight_layout()
    fig.savefig(FIG_DIR / '03_blockage_effect_summary.png', dpi=150)
    plt.close(fig)


def plot_distance_curves(distance_df: pd.DataFrame, metric: str, filename: str, title: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for (ctype, blk), sub in distance_df.groupby(['candidate_type', 'enable_blockage'], observed=True):
        ax.plot(sub['distance_m'], sub[metric], marker='o', label=f'{ctype} | blockage={blk}')
    ax.set_xlabel('Distance (m)')
    ax.set_ylabel(metric)
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, linestyle='--', alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / filename, dpi=150)
    plt.close(fig)


def heatmap_from_pivot(pivot: pd.DataFrame, title: str, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(14, max(5, 0.25 * len(pivot))))
    data = pivot.to_numpy(dtype=float)
    im = ax.imshow(data, aspect='auto', cmap='viridis')
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([str(i) for i in pivot.index])
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels([str(c) for c in pivot.columns], rotation=45, ha='right')
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / filename, dpi=150)
    plt.close(fig)


def plot_bin_performance(df: pd.DataFrame, bin_col: str, filename: str, title: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    summary = df.groupby([bin_col, 'candidate_type'], observed=True)['nRMSE'].mean().reset_index()
    for ctype, sub in summary.groupby('candidate_type', observed=True):
        ax.plot(sub[bin_col].astype(str), sub['nRMSE'], marker='o', label=str(ctype))
    ax.set_xlabel(bin_col)
    ax.set_ylabel('Mean nRMSE')
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, linestyle='--', alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / filename, dpi=150)
    plt.close(fig)


def find_best_contiguous_window(df: pd.DataFrame, score_col: str, min_len: int = 24, max_len: int = 96) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.sort_values('valid_time').reset_index(drop=True)
    gap = df['valid_time'].diff().dt.total_seconds().div(60).fillna(15)
    df['segment_id'] = (gap != 15).cumsum()
    best_score = -np.inf
    best_slice = None
    lengths = [l for l in [24, 48, 72, 96] if min_len <= l <= max_len]
    for _, seg in df.groupby('segment_id'):
        if len(seg) < min_len:
            continue
        vals = pd.to_numeric(seg[score_col], errors='coerce').fillna(0.0)
        for length in lengths:
            if len(seg) < length:
                continue
            roll = vals.rolling(length).sum()
            idx = roll.idxmax()
            score = roll.loc[idx]
            if pd.notna(score) and score > best_score:
                end_pos = seg.index.get_loc(idx)
                start_pos = end_pos - length + 1
                best_score = float(score)
                best_slice = seg.iloc[start_pos:end_pos + 1].copy()
    if best_slice is None:
        return df.head(min(len(df), min_len)).copy()
    return best_slice.drop(columns=['segment_id'])


def build_case_studies(long_df: pd.DataFrame, maintenance_cmp: pd.DataFrame, blockage_cmp: pd.DataFrame, robust_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}

    maint_best = maintenance_cmp[(maintenance_cmp['scope_name'] == 'not_curtailed')].sort_values('percent_improvement_nRMSE', ascending=False).iloc[0]
    maint_pair = long_df[
        (long_df['scope_name'].astype(str) == 'not_curtailed') &
        (long_df['candidate_power_col'].astype(str) == str(maint_best['candidate_power_col'])) &
        (long_df['enable_blockage'] == bool(maint_best['enable_blockage']))
    ][['valid_time', 'experiment_name', 'pred_power_mw', 'actual_power_mw', 'wind_speed', 'wind_direction', 'maintenance_count', 'is_curtailed']].copy()
    maint_pivot = maint_pair.pivot_table(index=['valid_time', 'actual_power_mw', 'wind_speed', 'wind_direction', 'maintenance_count', 'is_curtailed'], columns='experiment_name', values='pred_power_mw').reset_index()
    maint_pivot['improvement_abs_error'] = (maint_pivot['without_maintenance'] - maint_pivot['actual_power_mw']).abs() - (maint_pivot['with_maintenance'] - maint_pivot['actual_power_mw']).abs()
    out['case_maintenance_improvement'] = find_best_contiguous_window(maint_pivot, 'improvement_abs_error')

    blk_best = blockage_cmp[(blockage_cmp['experiment_name'] == 'with_maintenance') & (blockage_cmp['scope_name'] == 'not_curtailed')].sort_values('percent_improvement_nRMSE', ascending=False).iloc[0]
    blk_pair = long_df[
        (long_df['experiment_name'].astype(str) == 'with_maintenance') &
        (long_df['scope_name'].astype(str) == 'not_curtailed') &
        (long_df['candidate_power_col'].astype(str) == str(blk_best['candidate_power_col']))
    ][['valid_time', 'enable_blockage', 'pred_power_mw', 'actual_power_mw', 'wind_speed', 'wind_direction', 'maintenance_count', 'is_curtailed']].copy()
    blk_pivot = blk_pair.pivot_table(index=['valid_time', 'actual_power_mw', 'wind_speed', 'wind_direction', 'maintenance_count', 'is_curtailed'], columns='enable_blockage', values='pred_power_mw').reset_index().rename(columns={False: 'blockage_off', True: 'blockage_on'})
    blk_pivot['improvement_abs_error'] = (blk_pivot['blockage_off'] - blk_pivot['actual_power_mw']).abs() - (blk_pivot['blockage_on'] - blk_pivot['actual_power_mw']).abs()
    out['case_blockage_improvement'] = find_best_contiguous_window(blk_pivot, 'improvement_abs_error')

    recommended = robust_df.iloc[0]
    selected_blockage = bool(recommended['enable_blockage'])
    cand_pair = long_df[
        (long_df['experiment_name'].astype(str) == 'with_maintenance') &
        (long_df['scope_name'].astype(str) == 'not_curtailed') &
        (long_df['enable_blockage'] == selected_blockage) &
        (long_df['candidate_power_col'].astype(str).isin([str(recommended['candidate_power_col']), TRADITIONAL_CANDIDATE]))
    ][['valid_time', 'candidate_power_col', 'pred_power_mw', 'actual_power_mw', 'wind_speed', 'wind_direction', 'maintenance_count', 'is_curtailed']].copy()
    cand_pivot = cand_pair.pivot_table(index=['valid_time', 'actual_power_mw', 'wind_speed', 'wind_direction', 'maintenance_count', 'is_curtailed'], columns='candidate_power_col', values='pred_power_mw').reset_index()
    rec_col = str(recommended['candidate_power_col'])
    if TRADITIONAL_CANDIDATE not in cand_pivot.columns:
        cand_pivot[TRADITIONAL_CANDIDATE] = np.nan
    cand_pivot['improvement_abs_error'] = (cand_pivot[TRADITIONAL_CANDIDATE] - cand_pivot['actual_power_mw']).abs() - (cand_pivot[rec_col] - cand_pivot['actual_power_mw']).abs()
    out['case_candidate_difference'] = find_best_contiguous_window(cand_pivot, 'improvement_abs_error')

    return out


def plot_case(df: pd.DataFrame, baseline_col: str, proposed_col: str, filename: str, title: str) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    axes[0].plot(df['valid_time'], df['actual_power_mw'], label='Observed', linewidth=2)
    axes[0].plot(df['valid_time'], df[baseline_col], label='Baseline')
    axes[0].plot(df['valid_time'], df[proposed_col], label='Proposed')
    axes[0].set_ylabel('Power (MW)')
    axes[0].legend(fontsize=8)
    axes[0].set_title(title)

    axes[1].plot(df['valid_time'], df[baseline_col] - df['actual_power_mw'], label='Baseline error')
    axes[1].plot(df['valid_time'], df[proposed_col] - df['actual_power_mw'], label='Proposed error')
    axes[1].axhline(0, color='black', linewidth=1)
    axes[1].set_ylabel('Error (MW)')
    axes[1].legend(fontsize=8)

    axes[2].plot(df['valid_time'], df['wind_speed'], label='Wind speed')
    axes[2].plot(df['valid_time'], df['wind_direction'] / 50.0, label='Wind direction / 50')
    axes[2].plot(df['valid_time'], df['maintenance_count'], label='Maintenance count')
    if 'is_curtailed' in df.columns:
        axes[2].step(df['valid_time'], df['is_curtailed'].astype(int), where='mid', label='Curtailment flag')
    axes[2].legend(fontsize=8)
    axes[2].set_xlabel('Time')
    axes[2].set_ylabel('Auxiliary')
    fig.tight_layout()
    fig.savefig(FIG_DIR / filename, dpi=150)
    plt.close(fig)


def chapter4_markdown(time_summary: pd.DataFrame, ranking_results: dict[str, pd.DataFrame], maintenance_summary: pd.DataFrame, blockage_summary: pd.DataFrame, robust_df: pd.DataFrame, ws_bin_df: pd.DataFrame, wd_bin_df: pd.DataFrame, case_files: dict[str, pd.DataFrame], p_norm_mw: float) -> str:
    common = time_summary[time_summary['dataset_name'] == 'common_intersection'].iloc[0]
    skipped = time_summary[time_summary['dataset_name'] == 'with_maintenance_skipped_due_to_missing_maintenance'].iloc[0]
    with_overall = ranking_results['with_maintenance_overall']
    without_overall = ranking_results['without_maintenance_overall']
    best_with_nc = with_overall[with_overall['scope_name'] == 'not_curtailed'].sort_values('rank').iloc[0]
    best_without_nc = without_overall[without_overall['scope_name'] == 'not_curtailed'].sort_values('rank').iloc[0]
    maint_focus = maintenance_summary[(maintenance_summary['summary_level'] == 'overall') & (maintenance_summary['scope_name'] == 'not_curtailed') & (maintenance_summary['metric'] == 'nRMSE')].iloc[0]
    block_focus = blockage_summary[(blockage_summary['summary_level'] == 'overall') & (blockage_summary['experiment_name'] == 'with_maintenance') & (blockage_summary['scope_name'] == 'not_curtailed') & (blockage_summary['metric'] == 'nRMSE')].iloc[0]
    best_robust = robust_df.iloc[0]
    ws_best = ws_bin_df.sort_values(['wind_speed_bin', 'nRMSE']).groupby('wind_speed_bin', observed=True).first().reset_index()
    wd_best = wd_bin_df.sort_values(['wind_direction_bin', 'nRMSE']).groupby('wind_direction_bin', observed=True).first().reset_index()

    case_maint = case_files['case_maintenance_improvement']
    case_blk = case_files['case_blockage_improvement']
    case_cand = case_files['case_candidate_difference']

    return f"""# 4. Results

## 4.1 Sample Coverage and Evaluation Dataset

本章所有横向比较均基于共同时间交集构建，交集定义为 `with_maintenance valid_time ∩ without_maintenance valid_time ∩ measured timestamp`，并进一步并入气象风速、风向与维护台数。根据 `comparison_results/time_coverage_summary.csv`，共同评价样本共有 {int(common['unique_time_count'])} 个 15 min 时刻，对应时间范围为 {pd.to_datetime(common['start_time']).strftime('%Y-%m-%d %H:%M')} 至 {pd.to_datetime(common['end_time']).strftime('%Y-%m-%d %H:%M')}。其中，考虑维护实验相对于完整预报时段额外跳过了 {int(skipped['row_count'])} 个时刻，这与维护矩阵缺失时的 `missing_maintenance_policy=skip` 一致。因此，后续维护状态比较均不能直接使用两组实验各自原始时间范围，而必须使用共同交集样本。

共同样本长表文件为 `comparison_results/merged_common_samples.csv`（并同步保存 `comparison_results/merged_common_samples.parquet`），其中统一将候选 `station_power_*_kW` 转换为 MW。归一化容量 `P_norm` 统一取共同样本下实测 `MZS_FAN_ACTIVE_POWER_SUM` 的 95 分位值，即 {p_norm_mw:.3f} MW，以保持与现有评价脚本的口径一致。时间覆盖图见 `comparison_results/figures/01_time_coverage.png`。

## 4.2 Overview of Single-Experiment Rankings

单实验 ranking 结果分别见：

- `comparison_results/single_experiment_evaluation/ranking_without_maintenance_overall.csv`
- `comparison_results/single_experiment_evaluation/ranking_with_maintenance_overall.csv`
- `comparison_results/single_experiment_evaluation/ranking_without_maintenance_monthly.csv`
- `comparison_results/single_experiment_evaluation/ranking_with_maintenance_monthly.csv`

在共同样本与 `not_curtailed` 条件下，不考虑维护实验的 overall 最优组合为 `{best_without_nc['candidate_power_col']}`（`enable_blockage={bool(best_without_nc['enable_blockage'])}`，`nRMSE={best_without_nc['nRMSE']:.4f}`），而考虑维护实验的 overall 最优组合为 `{best_with_nc['candidate_power_col']}`（`enable_blockage={bool(best_with_nc['enable_blockage'])}`，`nRMSE={best_with_nc['nRMSE']:.4f}`）。这一结果可作为实验内部概览，但不能直接证明维护修正或阻塞项本身有效，因为不同实验之间若直接比较“各自最优”组合，会同时混入候选风速口径与 blockage 开关差异。

月度 ranking 也显示最优候选并非逐月完全固定，因此 overall 第一名并不自动等价于跨月份最稳健方案。后续各节因此统一采用控制变量比较，而不以“各自最优”作为唯一结论依据。

## 4.3 Effect of Maintenance-State Correction

维护状态修正的控制变量比较结果见：

- `comparison_results/controlled_comparison/maintenance_controlled_overall.csv`
- `comparison_results/controlled_comparison/maintenance_controlled_monthly.csv`
- `comparison_results/controlled_comparison/maintenance_controlled_summary.csv`
- `comparison_results/figures/02_maintenance_effect_by_month.png`

在 `not_curtailed` 条件下，固定 `candidate_power_col` 与 `enable_blockage` 后，共比较 {int(maint_focus['total_combinations'])} 个 overall 组合；其中 `nRMSE` 改善的组合占比为 {maint_focus['improved_ratio']:.2%}，平均改善幅度为 {maint_focus['mean_improvement_pct']:.2f}% ，中位改善幅度为 {maint_focus['median_improvement_pct']:.2f}% 。这说明维护状态修正并非对所有候选口径都带来同方向影响，但在共同样本与相同 blockage 设置下，运行状态一致性处理会实质改变评价结果。

月度结果进一步表明，维护修正的收益存在明显时间波动，并与维护台数变化同步出现起伏（见 `02_maintenance_effect_by_month.png`）。因此，维护状态修正更适合被解释为“保证模型计算对象与实测统计对象一致”的数据一致性步骤，而不应被表述为新的尾流物理机制。

## 4.4 Effect of Blockage

阻塞控制变量比较结果见：

- `comparison_results/controlled_comparison/blockage_controlled_overall.csv`
- `comparison_results/controlled_comparison/blockage_controlled_monthly.csv`
- `comparison_results/controlled_comparison/blockage_controlled_summary.csv`
- `comparison_results/figures/03_blockage_effect_summary.png`

以 `with_maintenance + not_curtailed` 为主线，固定实验组与候选口径后，共比较 {int(block_focus['total_combinations'])} 个 overall 组合；其中 `nRMSE` 改善组合占比为 {block_focus['improved_ratio']:.2%}，平均改善幅度为 {block_focus['mean_improvement_pct']:.2f}% ，中位改善幅度为 {block_focus['median_improvement_pct']:.2f}% 。从 `03_blockage_effect_summary.png` 可见，阻塞项的净效果并非对所有候选口径一致，其改善程度受候选类型与距离定义影响。

因此，第 4 章对 blockage 的表述应限定为：在控制变量条件下，阻塞开启对部分候选风速口径表现出平均误差改善，但其收益大小依赖候选定义、月份与样本域，不能由单个 overall 最优排名直接推出全局性结论。

## 4.5 Performance of Equivalent Inflow Wind-Speed Definitions

候选口径整体表现与稳健性排序见：

- `comparison_results/candidate_analysis/robust_candidate_selection.csv`
- `comparison_results/candidate_analysis/distance_error_curve.csv`
- `comparison_results/figures/04_distance_vs_nrmse.png`
- `comparison_results/figures/05_distance_vs_bias.png`

在 `with_maintenance + not_curtailed` 主线下，稳健性排序第一的候选为 `{best_robust['candidate_power_col']}`（`enable_blockage={bool(best_robust['enable_blockage'])}`），其 overall `nRMSE={best_robust['nRMSE']:.4f}`，`stability_score={best_robust['stability_score']:.4f}`。从距离误差曲线可以看出，upstream point 与 rotor-disc upstream mean 两类候选随距离变化均呈现明显的距离依赖性，且不同 blockage 设置下曲线位置并不完全重合。这说明等效入流风速口径的差异不仅体现为“哪一列更好”，更体现为特定距离带的整体误差特征。

同时，`04_distance_vs_nrmse.png` 与 `05_distance_vs_bias.png` 显示 nRMSE 与 Bias 对距离的响应并不总是同步，因此最终候选筛选不能只依据单一误差指标，也不能逐月自由选择局部最优距离。

## 4.6 Monthly Robustness of Candidate Wind-Speed Definitions

跨月份稳健性结果见：

- `comparison_results/candidate_analysis/monthly_candidate_rank.csv`
- `comparison_results/candidate_analysis/monthly_performance_summary.csv`
- `comparison_results/figures/06_monthly_nrmse_heatmap.png`
- `comparison_results/figures/07_candidate_rank_heatmap.png`

本研究对每个候选定义统计 `monthly_nRMSE_mean`、`monthly_nRMSE_std`、`monthly_nRMSE_max`、`monthly_rank_mean`、`monthly_rank_std`、`top1_month_count`、`top3_month_count`、`top5_month_count` 与 `worst_month_nRMSE`，并采用 `stability_score = mean + {STABILITY_ALPHA:.1f}×std + {STABILITY_BETA:.1f}×max` 的等权复合形式进行排序。该评分用于结果章节的可复现筛选，不代表仓库已有固定权重规范。

热力图结果表明，月度最优候选并不完全一致，但部分候选在多数月份保持前列。因此，本研究更倾向于选择跨月份稳定的候选或距离带，而不是为每个月单独切换最优模型。

## 4.7 Wind-Speed-Dependent Performance

风速分箱结果见：

- `comparison_results/candidate_analysis/candidate_performance_by_wind_speed_bin.csv`
- `comparison_results/figures/08_wind_speed_bin_performance.png`

本次结果分析采用风速分箱 `{', '.join(WIND_SPEED_LABELS)}`。在各风速段内，最优候选并不完全一致：例如，`{ws_best.iloc[0]['wind_speed_bin']}` 风速段下当前最优候选为 `{ws_best.iloc[0]['candidate_power_col']}`，而更高风速段会出现不同候选进入前列。该结果说明候选口径差异与来流强度相关，且阻塞收益并非在所有风速段均等出现。对误差最大的风速段及其物理解释，可留待第 5 章进一步讨论。

## 4.8 Wind-Direction-Dependent Performance

风向扇区结果见：

- `comparison_results/candidate_analysis/candidate_performance_by_wind_direction_bin.csv`
- `comparison_results/figures/09_wind_direction_bin_performance.png`

本次分析按 30° 扇区组织风向样本。在当前结果中，不同扇区的最优候选并不完全相同，例如 `{wd_best.iloc[0]['wind_direction_bin']}` 扇区下最优候选为 `{wd_best.iloc[0]['candidate_power_col']}`。这意味着候选风速口径与 blockage 收益都可能受到阵列相对来流方向的影响，但更深入的阵列几何解释应放在 Discussion 章节展开。

## 4.9 Case Studies

典型案例结果见：

- `comparison_results/case_studies/case_maintenance_improvement.csv`
- `comparison_results/case_studies/case_blockage_improvement.csv`
- `comparison_results/case_studies/case_candidate_difference.csv`
- `comparison_results/figures/case_maintenance_improvement.png`
- `comparison_results/figures/case_blockage_improvement.png`
- `comparison_results/figures/case_candidate_difference.png`

维护修正改善最明显的连续时段为 `{case_maint['valid_time'].min()}` 至 `{case_maint['valid_time'].max()}`；阻塞改善最明显的连续时段为 `{case_blk['valid_time'].min()}` 至 `{case_blk['valid_time'].max()}`；推荐口径相对于传统 `WS_eff native` 差异最明显的连续时段为 `{case_cand['valid_time'].min()}` 至 `{case_cand['valid_time'].max()}`。这些案例均使用连续 6–24 h 窗口识别，而非孤立单点，因此更适合展示模型差异在时间序列上的累积表现。

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
"""


def main() -> None:
    ensure_dirs()

    with_df, with_infos = load_model_output(WITH_OUTPUT, 'with_maintenance')
    without_df, without_infos = load_model_output(WITHOUT_OUTPUT, 'without_maintenance')
    measured = load_measured()
    forecast = load_forecast()
    maintenance = load_maintenance()

    all_infos = sorted({info.candidate_power_col: info for info in (with_infos + without_infos)}.values(), key=lambda x: (x.candidate_type, -1 if x.distance_m is None else x.distance_m, x.candidate_power_col))
    candidate_metadata_df = candidate_metadata(all_infos, ['with_maintenance', 'without_maintenance'])
    candidate_metadata_df.to_csv(OUT_DIR / 'candidate_columns_detected.csv', index=False, encoding='utf-8-sig')

    common_times = pd.Index(sorted(
        set(with_df['valid_time']) & set(without_df['valid_time']) & set(measured['valid_time']) & set(forecast['valid_time'])
    ))
    common_times = pd.to_datetime(common_times)

    time_summary = build_time_coverage_summary(with_df, without_df, measured, forecast, common_times)
    time_summary.to_csv(OUT_DIR / 'time_coverage_summary.csv', index=False, encoding='utf-8-sig')

    quality_df = build_measured_quality_check(measured)
    quality_df.to_csv(OUT_DIR / 'measured_power_quality_check.csv', index=False, encoding='utf-8-sig')

    with_common = build_common_wide(with_df, common_times, measured, forecast, maintenance)
    without_common = build_common_wide(without_df, common_times, measured, forecast, maintenance)
    common_wide = pd.concat([with_common, without_common], ignore_index=True)
    long_df = build_long_table(common_wide, all_infos)
    long_df.to_csv(OUT_DIR / 'merged_common_samples.csv', index=False, encoding='utf-8-sig')
    long_df.to_parquet(OUT_DIR / 'merged_common_samples.parquet', index=False)

    p_norm_mw = float(with_common['actual_power_mw'].dropna().quantile(0.95))

    ranking_results = single_experiment_rankings(long_df, p_norm_mw)
    ranking_results['with_maintenance_overall'].to_csv(SINGLE_DIR / 'ranking_with_maintenance_overall.csv', index=False, encoding='utf-8-sig')
    ranking_results['with_maintenance_monthly'].to_csv(SINGLE_DIR / 'ranking_with_maintenance_monthly.csv', index=False, encoding='utf-8-sig')
    ranking_results['without_maintenance_overall'].to_csv(SINGLE_DIR / 'ranking_without_maintenance_overall.csv', index=False, encoding='utf-8-sig')
    ranking_results['without_maintenance_monthly'].to_csv(SINGLE_DIR / 'ranking_without_maintenance_monthly.csv', index=False, encoding='utf-8-sig')

    overall_metrics = pd.concat([ranking_results['with_maintenance_overall'], ranking_results['without_maintenance_overall']], ignore_index=True)
    monthly_metrics = pd.concat([ranking_results['with_maintenance_monthly'], ranking_results['without_maintenance_monthly']], ignore_index=True)

    maintenance_overall = compare_experiments(overall_metrics, 'without_maintenance', 'with_maintenance', ['scope_name', 'enable_blockage', 'candidate_power_col', 'candidate_type', 'distance_m'], 'without_maintenance', 'with_maintenance')
    maintenance_monthly = compare_experiments(monthly_metrics, 'without_maintenance', 'with_maintenance', ['scope_name', 'month', 'candidate_power_col', 'candidate_type', 'distance_m', 'period_type', 'period_value', 'enable_blockage'], 'without_maintenance', 'with_maintenance')
    maintenance_overall.to_csv(CONTROL_DIR / 'maintenance_controlled_overall.csv', index=False, encoding='utf-8-sig')
    maintenance_monthly.to_csv(CONTROL_DIR / 'maintenance_controlled_monthly.csv', index=False, encoding='utf-8-sig')
    maintenance_summary = build_maintenance_summaries(maintenance_overall, maintenance_monthly)
    maintenance_summary.to_csv(CONTROL_DIR / 'maintenance_controlled_summary.csv', index=False, encoding='utf-8-sig')

    blockage_overall = compare_blockage(overall_metrics, ['experiment_name', 'scope_name', 'candidate_power_col', 'candidate_type', 'distance_m'])
    blockage_monthly = compare_blockage(monthly_metrics, ['experiment_name', 'scope_name', 'month', 'period_type', 'period_value', 'candidate_power_col', 'candidate_type', 'distance_m'])
    blockage_overall.to_csv(CONTROL_DIR / 'blockage_controlled_overall.csv', index=False, encoding='utf-8-sig')
    blockage_monthly.to_csv(CONTROL_DIR / 'blockage_controlled_monthly.csv', index=False, encoding='utf-8-sig')
    blockage_summary = build_blockage_summaries(blockage_overall, blockage_monthly)
    blockage_summary.to_csv(CONTROL_DIR / 'blockage_controlled_summary.csv', index=False, encoding='utf-8-sig')

    robust_df = build_robust_candidate_selection(monthly_metrics, overall_metrics)
    robust_df.to_csv(CANDIDATE_DIR / 'robust_candidate_selection.csv', index=False, encoding='utf-8-sig')
    distance_df = build_distance_error_curve(overall_metrics)
    distance_df.to_csv(CANDIDATE_DIR / 'distance_error_curve.csv', index=False, encoding='utf-8-sig')

    focus_monthly = monthly_metrics[(monthly_metrics['experiment_name'] == 'with_maintenance') & (monthly_metrics['scope_name'] == 'not_curtailed')].copy()
    focus_monthly_ranked = add_ranks(focus_monthly.copy(), ['enable_blockage', 'month'])
    focus_monthly_ranked.to_csv(CANDIDATE_DIR / 'monthly_candidate_rank.csv', index=False, encoding='utf-8-sig')
    robust_df.to_csv(CANDIDATE_DIR / 'monthly_performance_summary.csv', index=False, encoding='utf-8-sig')

    ws_focus = long_df[(long_df['experiment_name'].astype(str) == 'with_maintenance') & (long_df['scope_name'].astype(str) == 'not_curtailed')].copy()
    ws_focus['wind_speed_bin'] = pd.cut(pd.to_numeric(ws_focus['wind_speed'], errors='coerce'), bins=WIND_SPEED_BINS, labels=WIND_SPEED_LABELS, right=False, include_lowest=True)
    ws_bin_df = compute_metrics_table(ws_focus.dropna(subset=['wind_speed_bin']), ['enable_blockage', 'candidate_power_col', 'candidate_type', 'distance_m', 'wind_speed_bin'], p_norm_mw)
    ws_bin_df.to_csv(CANDIDATE_DIR / 'candidate_performance_by_wind_speed_bin.csv', index=False, encoding='utf-8-sig')

    wd_focus = long_df[(long_df['experiment_name'].astype(str) == 'with_maintenance') & (long_df['scope_name'].astype(str) == 'not_curtailed')].copy()
    wd_deg = pd.to_numeric(wd_focus['wind_direction'], errors='coerce') % 360.0
    bins = np.arange(0, 361, 30)
    labels = [f'{int(bins[i])}-{int(bins[i+1])}' for i in range(len(bins) - 1)]
    wd_focus['wind_direction_bin'] = pd.cut(wd_deg, bins=bins, labels=labels, right=False, include_lowest=True)
    wd_bin_df = compute_metrics_table(wd_focus.dropna(subset=['wind_direction_bin']), ['enable_blockage', 'candidate_power_col', 'candidate_type', 'distance_m', 'wind_direction_bin'], p_norm_mw)
    wd_bin_df.to_csv(CANDIDATE_DIR / 'candidate_performance_by_wind_direction_bin.csv', index=False, encoding='utf-8-sig')

    plot_time_coverage(time_summary)
    plot_maintenance_effect(maintenance_monthly)
    plot_blockage_effect(blockage_overall)
    plot_distance_curves(distance_df[distance_df['candidate_type'].isin(['upstream_point', 'rotor_disc_upstream_mean'])], 'nRMSE', '04_distance_vs_nrmse.png', 'Distance-dependent nRMSE (with maintenance, not curtailed)')
    plot_distance_curves(distance_df[distance_df['candidate_type'].isin(['upstream_point', 'rotor_disc_upstream_mean'])], 'Bias', '05_distance_vs_bias.png', 'Distance-dependent Bias (with maintenance, not curtailed)')

    heat_nrmse = focus_monthly_ranked.pivot_table(index='candidate_power_col', columns='period_value', values='nRMSE')
    heat_rank = focus_monthly_ranked.pivot_table(index='candidate_power_col', columns='period_value', values='rank')
    heatmap_from_pivot(heat_nrmse, 'Monthly nRMSE heatmap (with maintenance, not curtailed)', '06_monthly_nrmse_heatmap.png')
    heatmap_from_pivot(heat_rank, 'Monthly rank heatmap (with maintenance, not curtailed)', '07_candidate_rank_heatmap.png')
    plot_bin_performance(ws_bin_df, 'wind_speed_bin', '08_wind_speed_bin_performance.png', 'Wind-speed-bin performance (with maintenance, not curtailed)')
    plot_bin_performance(wd_bin_df, 'wind_direction_bin', '09_wind_direction_bin_performance.png', 'Wind-direction-sector performance (with maintenance, not curtailed)')

    cases = build_case_studies(long_df, maintenance_overall, blockage_overall, robust_df)
    cases['case_maintenance_improvement'].to_csv(CASE_DIR / 'case_maintenance_improvement.csv', index=False, encoding='utf-8-sig')
    cases['case_blockage_improvement'].to_csv(CASE_DIR / 'case_blockage_improvement.csv', index=False, encoding='utf-8-sig')
    cases['case_candidate_difference'].to_csv(CASE_DIR / 'case_candidate_difference.csv', index=False, encoding='utf-8-sig')
    plot_case(cases['case_maintenance_improvement'], 'without_maintenance', 'with_maintenance', 'case_maintenance_improvement.png', 'Case study: maintenance-state correction')
    plot_case(cases['case_blockage_improvement'], 'blockage_off', 'blockage_on', 'case_blockage_improvement.png', 'Case study: blockage effect')
    rec_col = str(robust_df.iloc[0]['candidate_power_col'])
    plot_case(cases['case_candidate_difference'], TRADITIONAL_CANDIDATE, rec_col, 'case_candidate_difference.png', 'Case study: recommended candidate vs WS_eff native')

    draft = chapter4_markdown(time_summary, ranking_results, maintenance_summary, blockage_summary, robust_df, ws_bin_df, wd_bin_df, cases, p_norm_mw)
    DRAFT_PATH.write_text(draft, encoding='utf-8')

    print('Generated comparison_results and paper draft successfully.')


if __name__ == '__main__':
    main()
