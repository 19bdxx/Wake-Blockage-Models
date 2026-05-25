#!/usr/bin/env python3
from __future__ import annotations

import os
import math
import argparse
from typing import List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 因为跑模型的时候，将JMZS写成了MZS，所以这里评估也统一用 MZS 来命名，避免不必要的麻烦
STATIONS = ["MZS"]

# 额定限电值（单位与实测 LIMIT_POWER 保持一致）
RATED_LIMIT_POWER = {
    "MZS": 300.0
}


def parse_args():
    parser = argparse.ArgumentParser(description="评估 station 级尾流模型功率预测精度（多场站 + 月份汇总 + 单CSV版）")
    parser.add_argument(
        "--measured-csv",
        type=str,
        default=r"场站实测数据\JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv",
        help="实测 CSV 路径",
    )
    parser.add_argument(
        "--pred-csv",
        type=str,
        default=r"尾流预测与全站实测对比\all_experiments_station_power_timeseries-不考虑维护-全月份.csv",
        help="预测 CSV 路径",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation_output_multi_station_MONTH-不考虑维护-全月份",
        help="输出目录",
    )
    parser.add_argument(
        "--limit-drop-threshold",
        type=float,
        default=0.95,
        help="判定限电阈值：LIMIT_POWER < 额定值 * 该阈值，则认为被限电",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="作图显示前 N 个候选",
    )
    parser.add_argument(
        "--save-station-subdirs",
        action="store_true",
        help="是否额外保留每个场站的子目录明细文件；默认仅输出合并后的总 CSV",
    )
    return parser.parse_args()


def load_measured(path: str, station: str) -> Tuple[pd.DataFrame, str, str]:
    df = pd.read_csv(path)
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]

    actual_col = f"{station}_FAN_ACTIVE_POWER_SUM"
    limit_col = f"{station}_LIMIT_POWER"

    required = {"timestamp", actual_col, limit_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"[{station}] 实测文件缺少列: {sorted(missing)}")

    df = df.copy()
    df["valid_time"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.tz_localize(None)

    if df["valid_time"].isna().any():
        raise ValueError(f"[{station}] 实测文件 timestamp 存在无法解析的值")

    keep_cols = ["valid_time", actual_col, limit_col]
    df = df[keep_cols].sort_values("valid_time").reset_index(drop=True)
    return df, actual_col, limit_col


def load_pred(path: str, station: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]

    required = {"valid_time", "enable_blockage", "station"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"预测文件缺少列: {sorted(missing)}")

    df = df.copy()

    # # 预测时间：原始是 UTC，转北京时间后再去掉时区
    # df["valid_time"] = (
    #     pd.to_datetime(df["valid_time"], utc=True, errors="coerce")
    #     .dt.tz_convert("Asia/Shanghai")
    #     .dt.tz_localize(None)
    # )
    df["valid_time"] = (pd.to_datetime(df["valid_time"]))
    
    if df["valid_time"].isna().any():
        raise ValueError(f"[{station}] 预测文件 valid_time 存在无法解析的值")

    df = df[df["station"] == station].copy()
    if df.empty:
        raise ValueError(f"预测文件中没有 station={station} 的记录")

    power_cols = [c for c in df.columns if c.startswith("station_power_") and c.endswith("_MW")]
    if not power_cols:
        raise ValueError(f"[{station}] 预测文件中未找到 station_power_*_MW 列")

    keep_cols = ["valid_time", "enable_blockage", "station"] + power_cols
    return df[keep_cols].sort_values(["valid_time", "enable_blockage"]).reset_index(drop=True)


def merge_measured_pred(
    measured: pd.DataFrame,
    pred: pd.DataFrame,
    actual_col: str,
    limit_col: str,
) -> pd.DataFrame:
    keep_cols = ["valid_time", actual_col, limit_col]
    merged = pred.merge(
        measured[keep_cols],
        on="valid_time",
        how="inner",
    )
    return merged


def mark_curtailment_by_limit_power(
    df: pd.DataFrame,
    station: str,
    limit_col: str,
    threshold: float,
) -> pd.DataFrame:
    out = df.copy()

    if station == "YY":
        out["is_curtailed"] = False
        return out

    rated = RATED_LIMIT_POWER.get(station)
    if rated is None:
        out["is_curtailed"] = False
        return out

    limit_series = pd.to_numeric(out[limit_col], errors="coerce")
    out["is_curtailed"] = limit_series < rated * threshold
    return out


def melt_candidates(df: pd.DataFrame) -> pd.DataFrame:
    power_cols = [c for c in df.columns if c.startswith("station_power_") and c.endswith("_MW")]
    id_vars = [c for c in df.columns if c not in power_cols]
    out = df.melt(
        id_vars=id_vars,
        value_vars=power_cols,
        var_name="candidate_power_col",
        value_name="pred_mw",
    )
    out["month"] = pd.to_datetime(out["valid_time"]).dt.month
    out["month_label"] = out["month"].map(lambda m: f"M{int(m):02d}" if pd.notna(m) else "M00")
    return out


def calc_metrics(sub: pd.DataFrame, actual_col: str, capacity_mw: float) -> dict:
    x = pd.to_numeric(sub[actual_col], errors="coerce").to_numpy()
    y = pd.to_numeric(sub["pred_mw"], errors="coerce").to_numpy()

    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]

    n = len(x)
    if n == 0:
        return {
            "n": 0, "mae": np.nan, "rmse": np.nan, "bias": np.nan,
            "nmae": np.nan, "nrmse": np.nan, "r2": np.nan, "corr": np.nan
        }

    err = y - x
    mae = np.mean(np.abs(err))
    rmse = math.sqrt(np.mean(err ** 2))
    bias = np.mean(err)

    nmae = mae / capacity_mw if capacity_mw > 0 else np.nan
    nrmse = rmse / capacity_mw if capacity_mw > 0 else np.nan

    ss_res = np.sum((x - y) ** 2)
    ss_tot = np.sum((x - np.mean(x)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    corr = np.corrcoef(x, y)[0, 1] if n >= 2 else np.nan

    return {
        "n": int(n),
        "mae": float(mae),
        "rmse": float(rmse),
        "bias": float(bias),
        "nmae": float(nmae) if np.isfinite(nmae) else np.nan,
        "nrmse": float(nrmse) if np.isfinite(nrmse) else np.nan,
        "r2": float(r2) if np.isfinite(r2) else np.nan,
        "corr": float(corr) if np.isfinite(corr) else np.nan,
    }


def rank_candidates(long_df: pd.DataFrame, actual_col: str, capacity_mw: float) -> pd.DataFrame:
    rows: List[dict] = []

    for (blk, cand), sub in long_df.groupby(["enable_blockage", "candidate_power_col"], dropna=False):
        metrics = calc_metrics(sub, actual_col=actual_col, capacity_mw=capacity_mw)
        rows.append({
            "enable_blockage": bool(blk),
            "candidate_power_col": cand,
            **metrics,
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out["abs_bias_for_sort"] = out["bias"].abs()
    out = out.sort_values(
        ["nrmse", "mae", "abs_bias_for_sort"],
        ascending=[True, True, True]
    ).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    return out.drop(columns=["abs_bias_for_sort"])


def build_period_rankings(
    long_df: pd.DataFrame,
    actual_col: str,
    capacity_mw: float,
    station: str,
    scope_name: str,
) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []

    overall = rank_candidates(
        long_df=long_df,
        actual_col=actual_col,
        capacity_mw=capacity_mw,
    )
    if not overall.empty:
        overall.insert(0, "period_type", "overall")
        overall.insert(1, "period_value", "ALL")
        overall.insert(2, "month", np.nan)
        overall.insert(3, "month_label", "ALL")
        overall.insert(0, "scope_name", scope_name)
        overall.insert(0, "station", station)
        frames.append(overall)

    for month in sorted(pd.Series(long_df["month"]).dropna().astype(int).unique().tolist()):
        sub = long_df[long_df["month"] == month].copy()
        monthly = rank_candidates(
            long_df=sub,
            actual_col=actual_col,
            capacity_mw=capacity_mw,
        )
        if monthly.empty:
            continue
        monthly.insert(0, "period_type", "month")
        monthly.insert(1, "period_value", f"M{month:02d}")
        monthly.insert(2, "month", month)
        monthly.insert(3, "month_label", f"M{month:02d}")
        monthly.insert(0, "scope_name", scope_name)
        monthly.insert(0, "station", station)
        frames.append(monthly)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def plot_best_timeseries(long_df: pd.DataFrame, ranking: pd.DataFrame, actual_col: str, outpath: str):
    if ranking.empty:
        return

    best = ranking.iloc[0]
    sub = long_df[
        (long_df["enable_blockage"] == best["enable_blockage"]) &
        (long_df["candidate_power_col"] == best["candidate_power_col"])
    ].copy().sort_values("valid_time")

    fig = plt.figure(figsize=(12, 5))
    ax = fig.add_subplot(111)
    ax.plot(sub["valid_time"], sub[actual_col], label=f"Actual: {actual_col}")
    ax.plot(
        sub["valid_time"],
        sub["pred_mw"],
        label=f"Best: {best['candidate_power_col']} | blockage={best['enable_blockage']}"
    )
    ax.set_xlabel("Time")
    ax.set_ylabel("Power [MW]")
    ax.set_title("Best candidate time series")
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def plot_top_scatter(long_df: pd.DataFrame, ranking: pd.DataFrame, actual_col: str, outpath: str, top_n: int):
    if ranking.empty:
        return

    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111)

    top = ranking.head(top_n)
    for _, r in top.iterrows():
        sub = long_df[
            (long_df["enable_blockage"] == r["enable_blockage"]) &
            (long_df["candidate_power_col"] == r["candidate_power_col"])
        ]
        ax.scatter(
            sub[actual_col],
            sub["pred_mw"],
            s=12,
            alpha=0.5,
            label=f"{r['candidate_power_col']} | blk={r['enable_blockage']}"
        )

    vals = pd.concat([long_df[actual_col], long_df["pred_mw"]], axis=0)
    vals = pd.to_numeric(vals, errors="coerce")
    vals = vals[np.isfinite(vals)]

    if len(vals) > 0:
        vmin, vmax = np.nanmin(vals.values), np.nanmax(vals.values)
        ax.plot([vmin, vmax], [vmin, vmax], linestyle="--")

    ax.set_xlabel(f"Actual ({actual_col}) [MW]")
    ax.set_ylabel("Predicted [MW]")
    ax.set_title("Top candidate scatter")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def evaluate_one_station(
    station: str,
    measured_csv: str,
    pred_csv: str,
    output_dir: str,
    limit_drop_threshold: float,
    top_n: int,
    save_station_subdirs: bool,
):
    station_outdir = os.path.join(output_dir, station)
    if save_station_subdirs:
        os.makedirs(station_outdir, exist_ok=True)

    measured, actual_col, limit_col = load_measured(measured_csv, station)
    pred = load_pred(pred_csv, station=station)

    merged = merge_measured_pred(
        measured=measured,
        pred=pred,
        actual_col=actual_col,
        limit_col=limit_col,
    )

    if merged.empty:
        raise ValueError(f"[{station}] 按 valid_time 直接合并后没有匹配数据，请检查时间格式或时区转换")

    merged = mark_curtailment_by_limit_power(
        merged,
        station=station,
        limit_col=limit_col,
        threshold=limit_drop_threshold,
    )

    long_df = melt_candidates(merged)
    capacity_mw = float(np.nanpercentile(pd.to_numeric(long_df[actual_col], errors="coerce"), 95))

    long_not_curtailed = long_df.copy() if station == "YY" else long_df[~long_df["is_curtailed"]].copy()

    ranking_all = build_period_rankings(
        long_df=long_df,
        actual_col=actual_col,
        capacity_mw=capacity_mw,
        station=station,
        scope_name="all_samples",
    )
    ranking_not_curtailed = build_period_rankings(
        long_df=long_not_curtailed,
        actual_col=actual_col,
        capacity_mw=capacity_mw,
        station=station,
        scope_name="not_curtailed",
    )

    if save_station_subdirs:
        merged.to_csv(os.path.join(station_outdir, "merged_detail.csv"), index=False, float_format="%.4f")
        long_df.to_csv(os.path.join(station_outdir, "merged_detail_long.csv"), index=False, float_format="%.4f")
        ranking_all.to_csv(os.path.join(station_outdir, "ranking_all.csv"), index=False, float_format="%.6f")
        ranking_not_curtailed.to_csv(os.path.join(station_outdir, "ranking_not_curtailed.csv"), index=False, float_format="%.6f")

        overall_best_all = ranking_all[ranking_all["period_type"] == "overall"].copy()
        overall_best_nc = ranking_not_curtailed[ranking_not_curtailed["period_type"] == "overall"].copy()
        plot_best_timeseries(
            long_df=long_df,
            ranking=overall_best_all,
            actual_col=actual_col,
            outpath=os.path.join(station_outdir, "best_overall_timeseries.png"),
        )
        plot_top_scatter(
            long_df=long_not_curtailed,
            ranking=overall_best_nc,
            actual_col=actual_col,
            outpath=os.path.join(station_outdir, "best_not_curtailed_scatter.png"),
            top_n=min(top_n, max(len(overall_best_nc), 1)),
        )

    summary = {
        "station": station,
        "matched_rows": len(merged),
        "actual_col": actual_col,
        "limit_col": limit_col,
        "capacity_mw": capacity_mw,
        "curtailed_rows": int(merged["is_curtailed"].sum()),
        "not_curtailed_rows": int((~merged["is_curtailed"]).sum()),
    }

    overall_all = ranking_all[ranking_all["period_type"] == "overall"].copy()
    overall_nc = ranking_not_curtailed[ranking_not_curtailed["period_type"] == "overall"].copy()

    if not overall_all.empty:
        best_all = overall_all.iloc[0].to_dict()
        summary["best_all_candidate"] = best_all.get("candidate_power_col")
        summary["best_all_blockage"] = best_all.get("enable_blockage")
        summary["best_all_nrmse"] = best_all.get("nrmse")
        summary["best_all_mae"] = best_all.get("mae")

    if not overall_nc.empty:
        best_nc = overall_nc.iloc[0].to_dict()
        summary["best_nc_candidate"] = best_nc.get("candidate_power_col")
        summary["best_nc_blockage"] = best_nc.get("enable_blockage")
        summary["best_nc_nrmse"] = best_nc.get("nrmse")
        summary["best_nc_mae"] = best_nc.get("mae")

    return summary, ranking_all, ranking_not_curtailed, merged, long_df


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    all_summaries = []
    all_ranking_frames = []
    all_merged_frames = []
    all_long_frames = []

    for station in STATIONS:
        print("=" * 80)
        print(f"开始评估场站: {station}")

        summary, ranking_all, ranking_not_curtailed, merged, long_df = evaluate_one_station(
            station=station,
            measured_csv=args.measured_csv,
            pred_csv=args.pred_csv,
            output_dir=args.output_dir,
            limit_drop_threshold=args.limit_drop_threshold,
            top_n=args.top_n,
            save_station_subdirs=args.save_station_subdirs,
        )
        all_summaries.append(summary)

        ranking_station = pd.concat([ranking_all, ranking_not_curtailed], ignore_index=True)
        all_ranking_frames.append(ranking_station)

        merged = merged.copy()
        if "station" not in merged.columns:
            merged.insert(0, "station", station)
        all_merged_frames.append(merged)

        long_df = long_df.copy()
        if "station" not in long_df.columns:
            long_df.insert(0, "station", station)
        all_long_frames.append(long_df)

        print(f"station                 : {station}")
        print(f"matched rows            : {summary['matched_rows']}")
        print(f"actual_col              : {summary['actual_col']}")
        print(f"capacity_mw (norm)      : {summary['capacity_mw']:.3f}")
        print(f"curtailed rows          : {summary['curtailed_rows']}")
        print(f"not curtailed rows      : {summary['not_curtailed_rows']}")

        preview = ranking_station[(ranking_station["period_type"] == "overall")].head(5)
        if not preview.empty:
            print("\n[overall Top 5]")
            print(preview[[
                "scope_name", "rank", "enable_blockage", "candidate_power_col",
                "n", "mae", "rmse", "nrmse", "bias", "r2", "corr"
            ]].to_string(index=False))

    summary_df = pd.DataFrame(all_summaries)
    ranking_combined = pd.concat(all_ranking_frames, ignore_index=True) if all_ranking_frames else pd.DataFrame()
    merged_combined = pd.concat(all_merged_frames, ignore_index=True) if all_merged_frames else pd.DataFrame()
    long_combined = pd.concat(all_long_frames, ignore_index=True) if all_long_frames else pd.DataFrame()

    summary_path = os.path.join(args.output_dir, "summary_all_stations.csv")
    ranking_path = os.path.join(args.output_dir, "ranking_all_stations_combined.csv")
    merged_path = os.path.join(args.output_dir, "merged_detail_all_stations.csv")
    long_path = os.path.join(args.output_dir, "merged_detail_long_all_stations.csv")

    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig", float_format="%.6f")
    ranking_combined.to_csv(ranking_path, index=False, encoding="utf-8-sig", float_format="%.6f")
    merged_combined.to_csv(merged_path, index=False, encoding="utf-8-sig", float_format="%.4f")
    long_combined.to_csv(long_path, index=False, encoding="utf-8-sig", float_format="%.4f")

    print("\n" + "=" * 80)
    print("全部场站评估完成")
    print("输出目录：", os.path.abspath(args.output_dir))
    print("汇总文件：", os.path.abspath(summary_path))
    print("综合排名：", os.path.abspath(ranking_path))
    print("全站明细：", os.path.abspath(merged_path))
    print("长表明细：", os.path.abspath(long_path))


if __name__ == "__main__":
    main()
