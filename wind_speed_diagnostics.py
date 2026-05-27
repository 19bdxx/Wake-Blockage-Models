from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from chapter4_results_analysis import (
    MEASURED_WS_COL,
    WITH_OUTPUT,
    WITHOUT_OUTPUT,
    build_common_wide,
    display_candidate,
    load_forecast,
    load_measured,
    load_model_output,
    load_maintenance,
)

REPO_DIR = Path(__file__).resolve().parent
OUT_DIR = REPO_DIR / "comparison_results" / "wind_speed_diagnostics"
FIG_DIR = OUT_DIR / "figures"
REPORT_PATH = OUT_DIR / "wind_speed_diagnostics_report.md"

WIND_SPEED_BINS = [0, 3, 5, 7, 9, 11, 13, np.inf]
WIND_SPEED_LABELS = ["0-3", "3-5", "5-7", "7-9", "9-11", "11-13", "13+"]
WIND_DIRECTION_BINS = np.arange(0, 361, 30)
WIND_DIRECTION_LABELS = [f"{int(WIND_DIRECTION_BINS[i])}-{int(WIND_DIRECTION_BINS[i + 1])}" for i in range(len(WIND_DIRECTION_BINS) - 1)]


@dataclass(frozen=True)
class PairSpec:
    pair_key: str
    pair_label: str
    ws_col: str
    power_col: str
    source_role: str


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def wind_source_metadata(ws_col: str) -> dict[str, object]:
    if ws_col == "wind_speed":
        return {
            "ws_col": ws_col,
            "source_group": "meteorological_input",
            "distance_m": np.nan,
            "paired_power_col": "station_power_pywake_internal_kW",
            "display_name": "Meteorological input",
            "short_name": "Met input",
        }
    if ws_col == "mean_WS_eff_pywake_native_m_s":
        return {
            "ws_col": ws_col,
            "source_group": "ws_eff_native",
            "distance_m": np.nan,
            "paired_power_col": "station_power_from_ws_eff_pywake_native_kW",
            "display_name": "PyWake WS_eff native mean",
            "short_name": "WS_eff native",
        }
    match = re.match(r"^mean_WS_rotor_disc_upstream(\d+)m_mean_m_s$", ws_col)
    if match:
        distance_m = float(match.group(1))
        return {
            "ws_col": ws_col,
            "source_group": "rotor_disc_upstream_mean",
            "distance_m": distance_m,
            "paired_power_col": f"station_power_from_rotor_disc_upstream{int(distance_m)}m_mean_kW",
            "display_name": f"Rotor-disc upstream {int(distance_m)} m mean",
            "short_name": f"Rotor {int(distance_m)} m",
        }
    match = re.match(r"^mean_WS_probe_upstream_(\d+)m_m_s$", ws_col)
    if match:
        distance_m = float(match.group(1))
        return {
            "ws_col": ws_col,
            "source_group": "upstream_probe",
            "distance_m": distance_m,
            "paired_power_col": f"station_power_from_upstream_{int(distance_m)}m_kW",
            "display_name": f"Upstream probe {int(distance_m)} m mean",
            "short_name": f"Probe {int(distance_m)} m",
        }
    return {
        "ws_col": ws_col,
        "source_group": "other",
        "distance_m": np.nan,
        "paired_power_col": None,
        "display_name": ws_col,
        "short_name": ws_col,
    }


def power_col_to_ws_col(power_col: str) -> str | None:
    if power_col == "station_power_pywake_internal_kW":
        return "wind_speed"
    if power_col == "station_power_from_ws_eff_pywake_native_kW":
        return "mean_WS_eff_pywake_native_m_s"
    match = re.match(r"^station_power_from_rotor_disc_upstream(\d+)m_mean_kW$", power_col)
    if match:
        return f"mean_WS_rotor_disc_upstream{match.group(1)}m_mean_m_s"
    match = re.match(r"^station_power_from_upstream_(\d+)m_kW$", power_col)
    if match:
        return f"mean_WS_probe_upstream_{match.group(1)}m_m_s"
    return None


def display_ws_col(ws_col: str) -> str:
    return str(wind_source_metadata(ws_col)["display_name"])


def available_station_ws_cols(df: pd.DataFrame) -> list[str]:
    cols = []
    for col in df.columns:
        if col == "wind_speed" or col.startswith("mean_WS_"):
            meta = wind_source_metadata(col)
            if meta["source_group"] in {"meteorological_input", "ws_eff_native", "rotor_disc_upstream_mean", "upstream_probe"}:
                cols.append(col)
    return cols


def representative_pairs() -> list[PairSpec]:
    ranking = pd.read_csv(REPO_DIR / "comparison_results" / "single_experiment_evaluation" / "ranking_with_maintenance_overall.csv", encoding="utf-8-sig")
    ranking = ranking[(ranking["scope_name"] == "not_curtailed") & (ranking["enable_blockage"] == True)].sort_values("nRMSE")
    strict_power_col = str(ranking.iloc[0]["candidate_power_col"])

    robust = pd.read_csv(REPO_DIR / "comparison_results" / "candidate_analysis" / "robust_candidate_selection.csv", encoding="utf-8-sig")
    robust = robust[robust["enable_blockage"] == True].sort_values("stability_score")
    robust_power_col = str(robust.iloc[0]["candidate_power_col"])

    pair_defs = [
        PairSpec(
            pair_key="meteorological_input",
            pair_label="Meteorological input + PyWake internal power",
            ws_col="wind_speed",
            power_col="station_power_pywake_internal_kW",
            source_role="baseline",
        ),
        PairSpec(
            pair_key="ws_eff_native",
            pair_label="PyWake WS_eff native + native power",
            ws_col="mean_WS_eff_pywake_native_m_s",
            power_col="station_power_from_ws_eff_pywake_native_kW",
            source_role="baseline",
        ),
        PairSpec(
            pair_key="strict_best_power",
            pair_label=f"Strict best Chapter 4 candidate ({display_candidate(strict_power_col)})",
            ws_col=power_col_to_ws_col(strict_power_col) or "wind_speed",
            power_col=strict_power_col,
            source_role="chapter4_best",
        ),
        PairSpec(
            pair_key="robust_recommendation",
            pair_label=f"Robust Chapter 4 recommendation ({display_candidate(robust_power_col)})",
            ws_col=power_col_to_ws_col(robust_power_col) or "wind_speed",
            power_col=robust_power_col,
            source_role="chapter4_robust",
        ),
    ]
    deduped: list[PairSpec] = []
    seen: set[tuple[str, str]] = set()
    for pair in pair_defs:
        key = (pair.ws_col, pair.power_col)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(pair)
    return deduped


def build_with_maintenance_common() -> pd.DataFrame:
    with_df, _ = load_model_output(WITH_OUTPUT, "with_maintenance")
    without_df, _ = load_model_output(WITHOUT_OUTPUT, "without_maintenance")
    measured = load_measured()
    forecast = load_forecast()
    maintenance = load_maintenance()
    common_times = pd.Index(sorted(set(with_df["valid_time"]) & set(without_df["valid_time"]) & set(measured["valid_time"]) & set(forecast["valid_time"])))
    common_times = pd.to_datetime(common_times)
    df = build_common_wide(with_df, common_times, measured, forecast, maintenance)
    df["measured_ws"] = pd.to_numeric(df[MEASURED_WS_COL], errors="coerce")
    df["actual_power_mw"] = pd.to_numeric(df["actual_power_mw"], errors="coerce")
    df["wind_speed"] = pd.to_numeric(df["wind_speed"], errors="coerce")
    df["wind_direction"] = pd.to_numeric(df["wind_direction"], errors="coerce")
    for col in available_station_ws_cols(df):
        if col != "wind_speed":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    power_cols = [col for col in df.columns if col.startswith("station_power_") and col.endswith("_kW")]
    for col in power_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def scope_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    valid_power = df["actual_power_mw"].notna()
    return {
        "all_samples": valid_power,
        "not_curtailed": valid_power & (~df["is_curtailed"].fillna(False)),
    }


def build_available_variables_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in available_station_ws_cols(df):
        meta = wind_source_metadata(col)
        rows.append(
            {
                "ws_col": col,
                "display_name": meta["display_name"],
                "source_group": meta["source_group"],
                "distance_m": meta["distance_m"],
                "paired_power_col": meta["paired_power_col"],
                "paired_power_label": display_candidate(meta["paired_power_col"]) if meta["paired_power_col"] else None,
                "unit": "m/s",
            }
        )
    out = pd.DataFrame(rows).sort_values(["source_group", "distance_m", "ws_col"], na_position="first").reset_index(drop=True)
    out.to_csv(OUT_DIR / "available_wind_speed_variables.csv", index=False, encoding="utf-8-sig")
    return out


def compute_wind_speed_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ws_cols = available_station_ws_cols(df)
    for scope_name, mask in scope_masks(df).items():
        scope_df = df[mask].copy()
        for enable_blockage, group in scope_df.groupby("enable_blockage"):
            for ws_col in ws_cols:
                meta = wind_source_metadata(ws_col)
                sub = group[[ws_col, "measured_ws"]].dropna()
                if sub.empty:
                    continue
                err = sub[ws_col] - sub["measured_ws"]
                rows.append(
                    {
                        "scope_name": scope_name,
                        "enable_blockage": bool(enable_blockage),
                        "ws_col": ws_col,
                        "display_name": meta["display_name"],
                        "source_group": meta["source_group"],
                        "distance_m": meta["distance_m"],
                        "paired_power_col": meta["paired_power_col"],
                        "paired_power_label": display_candidate(meta["paired_power_col"]) if meta["paired_power_col"] else None,
                        "n": int(len(sub)),
                        "bias_mps": float(err.mean()),
                        "mae_mps": float(err.abs().mean()),
                        "rmse_mps": float(np.sqrt(np.mean(err**2))),
                        "corr": float(sub[ws_col].corr(sub["measured_ws"])),
                    }
                )
    out = pd.DataFrame(rows)
    out["rmse_rank_within_scope"] = out.groupby(["scope_name", "enable_blockage"])["rmse_mps"].rank(method="dense")
    out = out.sort_values(["scope_name", "enable_blockage", "rmse_rank_within_scope", "mae_mps", "ws_col"]).reset_index(drop=True)
    out.to_csv(OUT_DIR / "wind_speed_comparison_summary.csv", index=False, encoding="utf-8-sig")
    return out


def pair_frame(df: pd.DataFrame, pair: PairSpec, extra_cols: list[str] | None = None) -> pd.DataFrame:
    cols = ["valid_time", "month", "wind_direction", "measured_ws", "actual_power_mw", pair.ws_col, pair.power_col]
    if extra_cols:
        cols.extend(extra_cols)
    cols = list(dict.fromkeys(cols))
    sub = df[cols].dropna().copy()
    sub["ws_error"] = sub[pair.ws_col] - sub["measured_ws"]
    sub["abs_ws_error"] = sub["ws_error"].abs()
    sub["pred_power_mw"] = sub[pair.power_col] / 1000.0
    sub["power_error_mw"] = sub["pred_power_mw"] - sub["actual_power_mw"]
    sub["abs_power_error_mw"] = sub["power_error_mw"].abs()
    return sub


def compute_relationship_summary(df: pd.DataFrame, pairs: list[PairSpec]) -> pd.DataFrame:
    rows = []
    for pair in pairs:
        sub = pair_frame(df, pair)
        same_sign_ratio = (((sub["ws_error"] >= 0) & (sub["power_error_mw"] >= 0)) | ((sub["ws_error"] < 0) & (sub["power_error_mw"] < 0))).mean()
        rows.append(
            {
                "summary_level": "overall",
                "pair_key": pair.pair_key,
                "pair_label": pair.pair_label,
                "source_role": pair.source_role,
                "ws_col": pair.ws_col,
                "power_col": pair.power_col,
                "n": int(len(sub)),
                "ws_bias_mps": float(sub["ws_error"].mean()),
                "ws_mae_mps": float(sub["abs_ws_error"].mean()),
                "ws_rmse_mps": float(np.sqrt(np.mean(sub["ws_error"] ** 2))),
                "power_bias_mw": float(sub["power_error_mw"].mean()),
                "power_mae_mw": float(sub["abs_power_error_mw"].mean()),
                "power_rmse_mw": float(np.sqrt(np.mean(sub["power_error_mw"] ** 2))),
                "corr_signed": float(sub["ws_error"].corr(sub["power_error_mw"])),
                "corr_abs": float(sub["abs_ws_error"].corr(sub["abs_power_error_mw"])),
                "same_sign_ratio": float(same_sign_ratio),
                "bin_or_group": None,
                "mean_abs_ws_error_mps": np.nan,
                "mean_abs_power_error_mw": np.nan,
            }
        )
        sub["abs_ws_error_quintile"] = pd.qcut(sub["abs_ws_error"], q=5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"], duplicates="drop")
        for quintile, q_group in sub.groupby("abs_ws_error_quintile", observed=False):
            if pd.isna(quintile):
                continue
            rows.append(
                {
                    "summary_level": "abs_ws_error_quintile",
                    "pair_key": pair.pair_key,
                    "pair_label": pair.pair_label,
                    "source_role": pair.source_role,
                    "ws_col": pair.ws_col,
                    "power_col": pair.power_col,
                    "n": int(len(q_group)),
                    "ws_bias_mps": float(q_group["ws_error"].mean()),
                    "ws_mae_mps": float(q_group["abs_ws_error"].mean()),
                    "ws_rmse_mps": float(np.sqrt(np.mean(q_group["ws_error"] ** 2))),
                    "power_bias_mw": float(q_group["power_error_mw"].mean()),
                    "power_mae_mw": float(q_group["abs_power_error_mw"].mean()),
                    "power_rmse_mw": float(np.sqrt(np.mean(q_group["power_error_mw"] ** 2))),
                    "corr_signed": float(q_group["ws_error"].corr(q_group["power_error_mw"])) if len(q_group) > 1 else np.nan,
                    "corr_abs": float(q_group["abs_ws_error"].corr(q_group["abs_power_error_mw"])) if len(q_group) > 1 else np.nan,
                    "same_sign_ratio": float((((q_group["ws_error"] >= 0) & (q_group["power_error_mw"] >= 0)) | ((q_group["ws_error"] < 0) & (q_group["power_error_mw"] < 0))).mean()),
                    "bin_or_group": str(quintile),
                    "mean_abs_ws_error_mps": float(q_group["abs_ws_error"].mean()),
                    "mean_abs_power_error_mw": float(q_group["abs_power_error_mw"].mean()),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "wind_speed_error_power_error_relationship.csv", index=False, encoding="utf-8-sig")
    return out


def compute_monthly_bias(df: pd.DataFrame, pairs: list[PairSpec]) -> pd.DataFrame:
    rows = []
    for pair in pairs:
        sub = pair_frame(df, pair)
        for month, group in sub.groupby("month"):
            rows.append(
                {
                    "pair_key": pair.pair_key,
                    "pair_label": pair.pair_label,
                    "source_role": pair.source_role,
                    "month": int(month),
                    "n": int(len(group)),
                    "ws_bias_mps": float(group["ws_error"].mean()),
                    "ws_mae_mps": float(group["abs_ws_error"].mean()),
                    "ws_rmse_mps": float(np.sqrt(np.mean(group["ws_error"] ** 2))),
                    "power_bias_mw": float(group["power_error_mw"].mean()),
                    "power_mae_mw": float(group["abs_power_error_mw"].mean()),
                    "power_rmse_mw": float(np.sqrt(np.mean(group["power_error_mw"] ** 2))),
                    "corr_ws_vs_power_error": float(group["ws_error"].corr(group["power_error_mw"])) if len(group) > 1 else np.nan,
                }
            )
    out = pd.DataFrame(rows).sort_values(["pair_label", "month"]).reset_index(drop=True)
    out.to_csv(OUT_DIR / "monthly_wind_power_bias.csv", index=False, encoding="utf-8-sig")
    return out


def compute_conditional_diagnostics(df: pd.DataFrame, pairs: list[PairSpec], group_col: str, group_label: str) -> pd.DataFrame:
    rows = []
    for pair in pairs:
        sub = pair_frame(df, pair, extra_cols=[group_col])
        for value, group in sub.groupby(group_col, observed=False):
            if pd.isna(value):
                continue
            rows.append(
                {
                    "group_type": group_label,
                    "pair_key": pair.pair_key,
                    "pair_label": pair.pair_label,
                    "source_role": pair.source_role,
                    "bin_or_group": str(value),
                    "n": int(len(group)),
                    "ws_bias_mps": float(group["ws_error"].mean()),
                    "ws_mae_mps": float(group["abs_ws_error"].mean()),
                    "ws_rmse_mps": float(np.sqrt(np.mean(group["ws_error"] ** 2))),
                    "power_bias_mw": float(group["power_error_mw"].mean()),
                    "power_mae_mw": float(group["abs_power_error_mw"].mean()),
                    "power_rmse_mw": float(np.sqrt(np.mean(group["power_error_mw"] ** 2))),
                    "corr_ws_vs_power_error": float(group["ws_error"].corr(group["power_error_mw"])) if len(group) > 1 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def select_case_studies(df: pd.DataFrame, pairs: list[PairSpec]) -> pd.DataFrame:
    pair_map = {pair.pair_key: pair for pair in pairs}
    strict_pair = next(pair for pair in pairs if pair.source_role == "chapter4_best")
    robust_pair = next(pair for pair in pairs if pair.source_role == "chapter4_robust")
    met_pair = next(pair for pair in pairs if pair.pair_key == "meteorological_input")

    work = df[["valid_time", "measured_ws", "actual_power_mw", met_pair.ws_col, met_pair.power_col, strict_pair.ws_col, strict_pair.power_col, robust_pair.ws_col, robust_pair.power_col]].dropna().copy()
    work["met_ws_err"] = work[met_pair.ws_col] - work["measured_ws"]
    work["strict_ws_err"] = work[strict_pair.ws_col] - work["measured_ws"]
    work["robust_ws_err"] = work[robust_pair.ws_col] - work["measured_ws"]
    work["met_power_err"] = work[met_pair.power_col] / 1000.0 - work["actual_power_mw"]
    work["strict_power_err"] = work[strict_pair.power_col] / 1000.0 - work["actual_power_mw"]
    work["robust_power_err"] = work[robust_pair.power_col] / 1000.0 - work["actual_power_mw"]

    input_case = work.assign(score=work["met_power_err"].abs() - work["strict_power_err"].abs() + work["met_ws_err"].abs()).sort_values("score", ascending=False).iloc[0]
    small_ws_threshold = work["strict_ws_err"].abs().quantile(0.25)
    residual_case = work[work["strict_ws_err"].abs() <= small_ws_threshold].assign(score=lambda d: d["strict_power_err"].abs()).sort_values("score", ascending=False).iloc[0]
    good_case = work.assign(score=work["strict_ws_err"].abs() + work["strict_power_err"].abs() / 20.0).sort_values("score", ascending=True).iloc[0]

    rows = [
        {
            "case_key": "input_bias_dominant",
            "case_label": "Input-bias-dominant case",
            "center_time": input_case["valid_time"],
            "selection_reason": "Large meteorological wind-speed error and large power-error reduction after switching to Chapter 4 best candidate.",
            "met_ws_error_mps": float(input_case["met_ws_err"]),
            "strict_ws_error_mps": float(input_case["strict_ws_err"]),
            "robust_ws_error_mps": float(input_case["robust_ws_err"]),
            "met_power_error_mw": float(input_case["met_power_err"]),
            "strict_power_error_mw": float(input_case["strict_power_err"]),
            "robust_power_error_mw": float(input_case["robust_power_err"]),
        },
        {
            "case_key": "residual_model_mismatch",
            "case_label": "Residual mismatch case",
            "center_time": residual_case["valid_time"],
            "selection_reason": "Chapter 4 best candidate has small wind-speed error but still large power error.",
            "met_ws_error_mps": float(residual_case["met_ws_err"]),
            "strict_ws_error_mps": float(residual_case["strict_ws_err"]),
            "robust_ws_error_mps": float(residual_case["robust_ws_err"]),
            "met_power_error_mw": float(residual_case["met_power_err"]),
            "strict_power_error_mw": float(residual_case["strict_power_err"]),
            "robust_power_error_mw": float(residual_case["robust_power_err"]),
        },
        {
            "case_key": "good_match",
            "case_label": "Good-match case",
            "center_time": good_case["valid_time"],
            "selection_reason": "Chapter 4 best candidate simultaneously matches wind speed and power closely.",
            "met_ws_error_mps": float(good_case["met_ws_err"]),
            "strict_ws_error_mps": float(good_case["strict_ws_err"]),
            "robust_ws_error_mps": float(good_case["robust_ws_err"]),
            "met_power_error_mw": float(good_case["met_power_err"]),
            "strict_power_error_mw": float(good_case["strict_power_err"]),
            "robust_power_error_mw": float(good_case["robust_power_err"]),
        },
    ]
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "case_studies.csv", index=False, encoding="utf-8-sig")
    return out


def scatter_panel(ax: plt.Axes, x: pd.Series, y: pd.Series, title: str) -> None:
    ax.scatter(x, y, s=6, alpha=0.25, edgecolors="none")
    finite = pd.concat([x, y], axis=1).dropna()
    if finite.empty:
        return
    min_v = float(np.nanmin(finite.to_numpy()))
    max_v = float(np.nanmax(finite.to_numpy()))
    ax.plot([min_v, max_v], [min_v, max_v], color="black", linestyle="--", linewidth=1)
    err = finite.iloc[:, 0] - finite.iloc[:, 1]
    corr = finite.iloc[:, 0].corr(finite.iloc[:, 1])
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Compared source (m/s)")
    ax.set_ylabel("Measured turbine mean wind speed (m/s)")
    ax.text(
        0.02,
        0.98,
        f"n={len(finite)}\nBias={err.mean():.2f} m/s\nRMSE={math.sqrt(np.mean(err**2)):.2f} m/s\nr={corr:.3f}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
        fontsize=8,
    )


def plot_wind_speed_scatter(df: pd.DataFrame, pairs: list[PairSpec]) -> None:
    fig, axes = plt.subplots(1, len(pairs), figsize=(5 * len(pairs), 4), constrained_layout=True)
    if len(pairs) == 1:
        axes = [axes]
    for ax, pair in zip(axes, pairs):
        sub = pair_frame(df, pair)
        scatter_panel(ax, sub[pair.ws_col], sub["measured_ws"], pair.pair_label)
    fig.savefig(FIG_DIR / "01_wind_speed_vs_measured_scatter.png", dpi=200)
    plt.close(fig)


def plot_relationship_scatter(df: pd.DataFrame, pairs: list[PairSpec]) -> None:
    fig, axes = plt.subplots(1, len(pairs), figsize=(5 * len(pairs), 4), constrained_layout=True)
    if len(pairs) == 1:
        axes = [axes]
    for ax, pair in zip(axes, pairs):
        sub = pair_frame(df, pair)
        ax.scatter(sub["ws_error"], sub["power_error_mw"], s=6, alpha=0.25, edgecolors="none")
        ax.axvline(0, color="black", linestyle="--", linewidth=1)
        ax.axhline(0, color="black", linestyle="--", linewidth=1)
        ax.set_title(pair.pair_label, fontsize=10)
        ax.set_xlabel("Wind-speed error (m/s)")
        ax.set_ylabel("Power error (MW)")
        ax.text(
            0.02,
            0.98,
            f"r={sub['ws_error'].corr(sub['power_error_mw']):.3f}\n|r|={sub['abs_ws_error'].corr(sub['abs_power_error_mw']):.3f}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
            fontsize=8,
        )
    fig.savefig(FIG_DIR / "02_wind_speed_error_vs_power_error.png", dpi=200)
    plt.close(fig)


def plot_monthly_bias(monthly_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    for pair_label, group in monthly_df.groupby("pair_label"):
        axes[0].plot(group["month"], group["ws_bias_mps"], marker="o", label=pair_label)
        axes[1].plot(group["month"], group["power_bias_mw"], marker="o", label=pair_label)
    axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0].set_ylabel("Wind-speed bias (m/s)")
    axes[1].set_ylabel("Power bias (MW)")
    axes[1].set_xlabel("Month")
    axes[0].set_title("Monthly wind-speed bias")
    axes[1].set_title("Monthly power bias")
    axes[0].legend(fontsize=8, ncol=2)
    fig.savefig(FIG_DIR / "03_monthly_bias_comparison.png", dpi=200)
    plt.close(fig)


def plot_group_bias(df: pd.DataFrame, title: str, filename: str) -> None:
    focus = df[df["pair_key"].isin(["meteorological_input", "strict_best_power", "robust_recommendation"])].copy()
    order = list(dict.fromkeys(focus["bin_or_group"].tolist()))
    x = np.arange(len(order))
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True, constrained_layout=True)
    for pair_label, group in focus.groupby("pair_label"):
        aligned = group.set_index("bin_or_group").reindex(order)
        axes[0].plot(x, aligned["ws_bias_mps"], marker="o", label=pair_label)
        axes[1].plot(x, aligned["power_bias_mw"], marker="o", label=pair_label)
    axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0].set_ylabel("Wind-speed bias (m/s)")
    axes[1].set_ylabel("Power bias (MW)")
    axes[1].set_xlabel("Condition bin")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(order, rotation=45, ha="right")
    axes[0].set_title(f"{title}: wind-speed bias")
    axes[1].set_title(f"{title}: power bias")
    axes[0].legend(fontsize=8, ncol=2)
    fig.savefig(FIG_DIR / filename, dpi=200)
    plt.close(fig)


def plot_case_studies(df: pd.DataFrame, cases: pd.DataFrame, pairs: list[PairSpec]) -> None:
    met_pair = next(pair for pair in pairs if pair.pair_key == "meteorological_input")
    strict_pair = next(pair for pair in pairs if pair.source_role == "chapter4_best")
    robust_pair = next(pair for pair in pairs if pair.source_role == "chapter4_robust")

    fig, axes = plt.subplots(len(cases), 2, figsize=(14, 4 * len(cases)), sharex=False, constrained_layout=True)
    if len(cases) == 1:
        axes = np.array([axes])
    for idx, (_, case) in enumerate(cases.iterrows()):
        center = pd.to_datetime(case["center_time"])
        window = df[(df["valid_time"] >= center - pd.Timedelta(hours=12)) & (df["valid_time"] <= center + pd.Timedelta(hours=12))].copy()
        ax_ws = axes[idx, 0]
        ax_power = axes[idx, 1]

        ax_ws.plot(window["valid_time"], window["measured_ws"], label="Measured turbine mean", linewidth=1.6)
        ax_ws.plot(window["valid_time"], window[met_pair.ws_col], label="Meteorological input", linewidth=1.2)
        ax_ws.plot(window["valid_time"], window[strict_pair.ws_col], label=display_ws_col(strict_pair.ws_col), linewidth=1.2)
        if robust_pair.ws_col != strict_pair.ws_col:
            ax_ws.plot(window["valid_time"], window[robust_pair.ws_col], label=display_ws_col(robust_pair.ws_col), linewidth=1.2)
        ax_ws.axvline(center, color="black", linestyle="--", linewidth=1)
        ax_ws.set_title(case["case_label"])
        ax_ws.set_ylabel("Wind speed (m/s)")
        ax_ws.legend(fontsize=7)

        ax_power.plot(window["valid_time"], window["actual_power_mw"], label="Measured power", linewidth=1.6)
        ax_power.plot(window["valid_time"], window[met_pair.power_col] / 1000.0, label="PyWake internal", linewidth=1.2)
        ax_power.plot(window["valid_time"], window[strict_pair.power_col] / 1000.0, label=display_candidate(strict_pair.power_col), linewidth=1.2)
        if robust_pair.power_col != strict_pair.power_col:
            ax_power.plot(window["valid_time"], window[robust_pair.power_col] / 1000.0, label=display_candidate(robust_pair.power_col), linewidth=1.2)
        ax_power.axvline(center, color="black", linestyle="--", linewidth=1)
        ax_power.set_ylabel("Power (MW)")
        ax_power.legend(fontsize=7)
    axes[-1, 0].set_xlabel("Time")
    axes[-1, 1].set_xlabel("Time")
    fig.savefig(FIG_DIR / "06_case_studies.png", dpi=200)
    plt.close(fig)


def fmt(x: float, digits: int = 3) -> str:
    if pd.isna(x):
        return "NA"
    return f"{x:.{digits}f}"


def build_report(
    available_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    relationship_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    speed_bin_df: pd.DataFrame,
    direction_bin_df: pd.DataFrame,
    cases_df: pd.DataFrame,
    pairs: list[PairSpec],
) -> str:
    summary_focus = summary_df[(summary_df["scope_name"] == "not_curtailed") & (summary_df["enable_blockage"] == True)].copy()
    met_row = summary_focus[summary_focus["ws_col"] == "wind_speed"].iloc[0]
    model_best_row = summary_focus[summary_focus["source_group"] != "meteorological_input"].sort_values("rmse_mps").iloc[0]
    blockage_off_best = summary_df[(summary_df["scope_name"] == "not_curtailed") & (summary_df["enable_blockage"] == False) & (summary_df["source_group"] != "meteorological_input")].sort_values("rmse_mps").iloc[0]

    overall_rel = relationship_df[relationship_df["summary_level"] == "overall"].copy()
    strict_row = overall_rel[overall_rel["source_role"] == "chapter4_best"].iloc[0]
    robust_row = overall_rel[overall_rel["source_role"] == "chapter4_robust"].iloc[0]
    met_pair_row = overall_rel[overall_rel["pair_key"] == "meteorological_input"].iloc[0]

    strict_quintiles = relationship_df[(relationship_df["summary_level"] == "abs_ws_error_quintile") & (relationship_df["source_role"] == "chapter4_best")].sort_values("bin_or_group")
    q1_row = strict_quintiles.iloc[0]
    q5_row = strict_quintiles.iloc[-1]

    monthly_focus = monthly_df[monthly_df["source_role"].isin(["baseline", "chapter4_best", "chapter4_robust"])].copy()
    july_strict = monthly_focus[(monthly_focus["source_role"] == "chapter4_best") & (monthly_focus["month"] == 7)].iloc[0]
    met_month_corr = monthly_focus[monthly_focus["pair_key"] == "meteorological_input"][["ws_bias_mps", "power_bias_mw"]].corr().iloc[0, 1]
    strict_month_corr = monthly_focus[monthly_focus["source_role"] == "chapter4_best"][["ws_bias_mps", "power_bias_mw"]].corr().iloc[0, 1]

    top_direction_met = direction_bin_df[direction_bin_df["pair_key"] == "meteorological_input"].sort_values("ws_bias_mps", ascending=False).iloc[0]
    top_speed_met = speed_bin_df[speed_bin_df["pair_key"] == "meteorological_input"].sort_values("ws_bias_mps", ascending=False).iloc[0]

    rotor_count = int((available_df["source_group"] == "rotor_disc_upstream_mean").sum())
    probe_count = int((available_df["source_group"] == "upstream_probe").sum())
    native_count = int((available_df["source_group"] == "ws_eff_native").sum())

    strict_pair = next(pair for pair in pairs if pair.source_role == "chapter4_best")
    robust_pair = next(pair for pair in pairs if pair.source_role == "chapter4_robust")

    return f"""# Wind Speed Diagnostics Report

## 1. Purpose and Data Sources

- **Purpose:** diagnose whether wind-speed mismatch helps explain station-power prediction error in the same common-time framework used by Chapter 4.
- **Common-sample basis:** `with_maintenance valid_time ∩ without_maintenance valid_time ∩ measured timestamp ∩ forecast valid_time`.
- **Main sample for interpretation:** `with_maintenance + enable_blockage=True + not_curtailed`, `n={int(strict_row["n"])}`.
- **Data files used:**
  - `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/five_experiments_output_考虑维护-全月份/all_experiments_station_power_timeseries.csv`
  - `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/five_experiments_output_不考虑维护-全月份/all_experiments_station_power_timeseries.csv`
  - `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/场站实测数据/JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv`
  - `ZIYAN-wake-model_接入维护状态_UTC8修正版-GPT/场站气象预报/wind_lat_33.250_lon_121.500-UTC8.csv`
- **Generated outputs:** all CSVs, figures, and this report are under `comparison_results/wind_speed_diagnostics/`.

## 2. Available Wind-Speed Variables

- **Meteorological input wind speed:** `wind_speed` from the forecast input file.
- **Measured turbine mean wind speed:** `{MEASURED_WS_COL}` from the lightweight SCADA-derived station file.
- **Model-derived station-level mean wind speed fields found in the lightweight experiment output:**
  - `mean_WS_eff_pywake_native_m_s` (`{native_count}` field family)
  - `mean_WS_rotor_disc_upstream*m_mean_m_s` (`{rotor_count}` distances)
  - `mean_WS_probe_upstream_*m_m_s` (`{probe_count}` distances)
- **Excluded from the main comparison:** downstream probe speeds were not used as turbine-inflow proxies.
- **Variable inventory CSV:** `comparison_results/wind_speed_diagnostics/available_wind_speed_variables.csv`

## 3. Meteorological Wind Speed vs Measured Turbine Wind Speed

- **Comparison object:** meteorological input `wind_speed` vs measured turbine mean wind speed.
- **Sample range:** `with_maintenance`, common-time samples, both blockage states share the same meteorological input values.
- **Main sample:** `not_curtailed + enable_blockage=True`, `n={int(met_row["n"])}`.
- **Key metrics:** Bias={fmt(float(met_row["bias_mps"]), 3)} m/s, MAE={fmt(float(met_row["mae_mps"]), 3)} m/s, RMSE={fmt(float(met_row["rmse_mps"]), 3)} m/s, r={fmt(float(met_row["corr"]), 3)}.
- **Monthly / conditional dependence:**
  - The meteorological input keeps a positive bias in every month of the main sample; monthly wind-speed bias vs monthly power bias correlation is {fmt(float(met_month_corr), 3)}.
  - The strongest positive meteorological wind-speed bias by measured wind-speed bin appears in `{top_speed_met["bin_or_group"]}` with Bias={fmt(float(top_speed_met["ws_bias_mps"]), 3)} m/s.
  - The strongest positive meteorological wind-speed bias by direction sector appears in `{top_direction_met["bin_or_group"]}` with Bias={fmt(float(top_direction_met["ws_bias_mps"]), 3)} m/s.
- **Figure paths:**
  - `comparison_results/wind_speed_diagnostics/figures/01_wind_speed_vs_measured_scatter.png`
  - `comparison_results/wind_speed_diagnostics/figures/03_monthly_bias_comparison.png`
  - `comparison_results/wind_speed_diagnostics/figures/04_wind_speed_bin_bias.png`
  - `comparison_results/wind_speed_diagnostics/figures/05_wind_direction_bin_bias.png`
- **Paper-ready statement:** The meteorological input wind speed is systematically higher than the measured turbine-mean wind speed over the common non-curtailed sample, indicating that part of the station-power overprediction can originate from inflow-input bias rather than wake-model structure alone.
- **Caution:** this measured reference is a turbine-mean SCADA quantity, not a free-stream mast or lidar inflow measurement.

## 4. Model-Derived Wind Speed vs Measured Turbine Wind Speed

- **Best model-speed field in the Chapter 4 main sample (`not_curtailed + blockage_on`):** `{model_best_row["display_name"]}`.
- **Its metrics:** Bias={fmt(float(model_best_row["bias_mps"]), 3)} m/s, MAE={fmt(float(model_best_row["mae_mps"]), 3)} m/s, RMSE={fmt(float(model_best_row["rmse_mps"]), 3)} m/s, r={fmt(float(model_best_row["corr"]), 3)}.
- **Meteorological baseline for the same sample:** Bias={fmt(float(met_row["bias_mps"]), 3)} m/s, RMSE={fmt(float(met_row["rmse_mps"]), 3)} m/s.
- **Relative interpretation:** the best `blockage_on` model-speed field reduces wind-speed RMSE by about {fmt(100.0 * (1.0 - float(model_best_row["rmse_mps"]) / float(met_row["rmse_mps"])), 1)}% relative to the meteorological input.
- **Best model-speed field in `not_curtailed + blockage_off`:** `{blockage_off_best["display_name"]}` with RMSE={fmt(float(blockage_off_best["rmse_mps"]), 3)} m/s.
- **Chapter 4 links:**
  - Strict best power candidate: `{strict_pair.pair_label}`.
  - Robust recommended candidate: `{robust_pair.pair_label}`.
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
  - Meteorological baseline: wind-speed Bias={fmt(float(met_pair_row["ws_bias_mps"]), 3)} m/s and power Bias={fmt(float(met_pair_row["power_bias_mw"]), 3)} MW, with signed error correlation r={fmt(float(met_pair_row["corr_signed"]), 3)}.
  - Chapter 4 strict-best pair: wind-speed Bias={fmt(float(strict_row["ws_bias_mps"]), 3)} m/s and power Bias={fmt(float(strict_row["power_bias_mw"]), 3)} MW, with signed error correlation r={fmt(float(strict_row["corr_signed"]), 3)} and absolute-error correlation r={fmt(float(strict_row["corr_abs"]), 3)}.
  - Chapter 4 robust pair: wind-speed Bias={fmt(float(robust_row["ws_bias_mps"]), 3)} m/s and power Bias={fmt(float(robust_row["power_bias_mw"]), 3)} MW, with signed error correlation r={fmt(float(robust_row["corr_signed"]), 3)}.
- **Magnitude effect:** for the Chapter 4 strict-best pair, mean |power error| rises from {fmt(float(q1_row["mean_abs_power_error_mw"]), 3)} MW in `Q1` to {fmt(float(q5_row["mean_abs_power_error_mw"]), 3)} MW in `Q5` as |wind-speed error| rises from {fmt(float(q1_row["mean_abs_ws_error_mps"]), 3)} to {fmt(float(q5_row["mean_abs_ws_error_mps"]), 3)} m/s.
- **Direct conclusion:** wind-speed error and power error are strongly coupled, but the case studies show they are not perfectly equivalent.
- **Figure path:** `comparison_results/wind_speed_diagnostics/figures/02_wind_speed_error_vs_power_error.png`
- **Paper-ready statement:** Across the non-curtailed Chapter 4 main sample, larger wind-speed mismatch is associated with larger power mismatch, implying that wind-speed error explains a meaningful share of power-prediction error.
- **Caution:** the coupling is partly amplified by the nonlinear turbine power curve, so correlation alone should not be over-interpreted as full causal proof.

## 6. Monthly and Conditional Dependence

- **Monthly CSV:** `comparison_results/wind_speed_diagnostics/monthly_wind_power_bias.csv`
- **Wind-speed-bin CSV:** `comparison_results/wind_speed_diagnostics/wind_speed_bin_diagnostics.csv`
- **Wind-direction-bin CSV:** `comparison_results/wind_speed_diagnostics/wind_direction_bin_diagnostics.csv`
- **Main monthly finding:** for the Chapter 4 strict-best pair, monthly wind-speed bias vs monthly power bias correlation is {fmt(float(strict_month_corr), 3)}.
- **Important residual month:** in July, the Chapter 4 strict-best pair still has wind-speed Bias={fmt(float(july_strict["ws_bias_mps"]), 3)} m/s but power Bias={fmt(float(july_strict["power_bias_mw"]), 3)} MW, showing that small average wind-speed bias does not guarantee small power bias.
- **Conditional interpretation:**
  - The meteorological input overestimates measured turbine speed most strongly in lower-to-mid measured wind-speed bins and in southerly sectors around `{top_direction_met["bin_or_group"]}`.
  - The best Chapter 4 model-speed pairs reduce those biases substantially, but some bins still retain non-negligible power bias.
- **Figure paths:**
  - `comparison_results/wind_speed_diagnostics/figures/03_monthly_bias_comparison.png`
  - `comparison_results/wind_speed_diagnostics/figures/04_wind_speed_bin_bias.png`
  - `comparison_results/wind_speed_diagnostics/figures/05_wind_direction_bin_bias.png`
- **Paper-ready statement:** The wind-speed diagnostic is condition-dependent: meteorological bias is stronger in specific wind-speed bins and direction sectors, whereas residual power bias persists in some months even after wind-speed bias is largely reduced.

## 7. Case Studies

- **Case summary CSV:** `comparison_results/wind_speed_diagnostics/case_studies.csv`
- **Case figure:** `comparison_results/wind_speed_diagnostics/figures/06_case_studies.png`
- **Case 1 – input-bias-dominant:** `{pd.to_datetime(cases_df.iloc[0]["center_time"]).strftime("%Y-%m-%d %H:%M")}`. Meteorological wind-speed error is {fmt(float(cases_df.iloc[0]["met_ws_error_mps"]), 3)} m/s and meteorological power error is {fmt(float(cases_df.iloc[0]["met_power_error_mw"]), 3)} MW; the Chapter 4 strict-best pair reduces the power error to {fmt(float(cases_df.iloc[0]["strict_power_error_mw"]), 3)} MW.
- **Case 2 – residual mismatch:** `{pd.to_datetime(cases_df.iloc[1]["center_time"]).strftime("%Y-%m-%d %H:%M")}`. The Chapter 4 strict-best pair has only {fmt(float(cases_df.iloc[1]["strict_ws_error_mps"]), 3)} m/s wind-speed error but still {fmt(float(cases_df.iloc[1]["strict_power_error_mw"]), 3)} MW power error.
- **Case 3 – good match:** `{pd.to_datetime(cases_df.iloc[2]["center_time"]).strftime("%Y-%m-%d %H:%M")}`. The Chapter 4 strict-best pair simultaneously keeps wind-speed and power errors close to zero.
- **Direct conclusion:** the case studies support a mixed diagnosis: some bad power predictions are input-wind problems, while others remain after wind-speed alignment improves.

## 8. Implications for Chapter 4 Results

- The persistent positive bias of the raw meteorological input helps explain why the more processed turbine-speed proxies outperform raw-input-based power estimates.
- The Chapter 4 strict-best candidate (`{display_candidate(strict_pair.power_col)}`) is also the closest `blockage_on` wind-speed proxy to the measured turbine mean in the main sample, which strengthens the interpretation that its power advantage is not accidental.
- The Chapter 4 robust recommendation (`{display_candidate(robust_pair.power_col)}`) is not the single closest wind-speed field overall, but it still shows much smaller wind-speed bias and power bias than the meteorological baseline; this is consistent with its robustness-oriented role.
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

1. **Does the meteorological input show obvious bias versus measured turbine wind speed?** Yes. It is positively biased in the main non-curtailed sample by about {fmt(float(met_row["bias_mps"]), 3)} m/s, with RMSE {fmt(float(met_row["rmse_mps"]), 3)} m/s.
2. **Is model-derived wind speed closer to measured wind speed than the meteorological input?** Yes. The best `blockage_on` model-speed field (`{model_best_row["display_name"]}`) reduces RMSE to {fmt(float(model_best_row["rmse_mps"]), 3)} m/s, clearly below the meteorological RMSE of {fmt(float(met_row["rmse_mps"]), 3)} m/s.
3. **Is power error related to wind-speed error?** Yes. The signed correlation is about {fmt(float(strict_row["corr_signed"]), 3)} for the Chapter 4 strict-best pair, and |power error| rises sharply across |wind-speed error| quintiles.
4. **Can part of the current power-prediction error be explained by wind-speed bias?** Yes. The meteorological baseline has both positive wind-speed bias and positive power bias, and much of that bias shrinks after switching to better turbine-speed proxies.
5. **Should this analysis sit in Chapter 4 Results or Chapter 5 Discussion?** The diagnostic results and summary figures fit in Chapter 4 Results; the broader implication that meteorological-input error constrains model evaluation should be emphasized in Chapter 5 Discussion.
6. **What else is still needed?** Independent inflow measurements, turbine-level matched diagnostics, and more explicit separation of residual maintenance/curtailment/data-quality cases would make the argument more convincing.
"""


def main() -> None:
    ensure_dirs()

    common_df = build_with_maintenance_common()
    available_df = build_available_variables_table(common_df)
    summary_df = compute_wind_speed_summary(common_df)

    main_focus = common_df[(common_df["enable_blockage"] == True) & common_df["actual_power_mw"].notna() & (~common_df["is_curtailed"].fillna(False))].copy()
    main_focus["measured_ws_bin"] = pd.cut(main_focus["measured_ws"], bins=WIND_SPEED_BINS, labels=WIND_SPEED_LABELS, right=False, include_lowest=True)
    main_focus["wind_direction_bin"] = pd.cut(main_focus["wind_direction"] % 360.0, bins=WIND_DIRECTION_BINS, labels=WIND_DIRECTION_LABELS, right=False, include_lowest=True)

    pairs = representative_pairs()
    relationship_df = compute_relationship_summary(main_focus, pairs)
    monthly_df = compute_monthly_bias(main_focus, pairs)
    speed_bin_df = compute_conditional_diagnostics(main_focus, pairs, "measured_ws_bin", "measured_ws_bin")
    direction_bin_df = compute_conditional_diagnostics(main_focus, pairs, "wind_direction_bin", "wind_direction_bin")
    speed_bin_df.to_csv(OUT_DIR / "wind_speed_bin_diagnostics.csv", index=False, encoding="utf-8-sig")
    direction_bin_df.to_csv(OUT_DIR / "wind_direction_bin_diagnostics.csv", index=False, encoding="utf-8-sig")
    cases_df = select_case_studies(main_focus, pairs)

    scatter_pairs = [
        next(pair for pair in pairs if pair.pair_key == "meteorological_input"),
        next(pair for pair in pairs if pair.source_role == "chapter4_best"),
        next(pair for pair in pairs if pair.source_role == "chapter4_robust"),
    ]
    plot_wind_speed_scatter(main_focus, scatter_pairs)
    plot_relationship_scatter(main_focus, scatter_pairs)
    plot_monthly_bias(monthly_df)
    plot_group_bias(speed_bin_df, "Measured-wind-speed-bin diagnostic", "04_wind_speed_bin_bias.png")
    plot_group_bias(direction_bin_df, "Forecast-direction-bin diagnostic", "05_wind_direction_bin_bias.png")
    plot_case_studies(main_focus, cases_df, pairs)

    report = build_report(available_df, summary_df, relationship_df, monthly_df, speed_bin_df, direction_bin_df, cases_df, pairs)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print("Generated wind-speed diagnostics outputs.")


if __name__ == "__main__":
    main()
