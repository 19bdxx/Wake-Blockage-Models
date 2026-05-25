# -*- coding: utf-8 -*-
"""
从 JMZSFD 原始 1min 场站数据生成风机维护矩阵，并抽取 15min 直接对齐版本。

输入文件默认：脚本同目录或当前工作目录下的 JMZSFD_202309-202407-处理后.csv
也可通过 --input 指定。

维护识别规则：
    只使用状态码判断：STATUS_#i == 6 -> 是否维护_#i = 1，否则为 0。

质量控制规则：
    任意时刻只要存在任意风机 STATUS_#i 不属于 0,1,2,3,4,5,6，
    则删除该时刻全场数据，并输出异常统计。

核心输出：
    jmzsfd_maintenance_matrix_1min.csv
    jmzsfd_maintenance_matrix_15min_direct.csv
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

TIME_COL = "timestamp"
VALID_STATUS_CODES = {0, 1, 2, 3, 4, 5, 6}
MAINTENANCE_STATUS_CODE = 6
DEFAULT_INPUT_NAME = "JMZSFD_202309-202407-处理后.csv"


def read_csv_smart(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"找不到输入文件：{path}")
    last_err = None
    for enc in ("utf-8-sig", "gbk", "gb18030"):
        try:
            print(f"尝试读取编码：{enc}")
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except UnicodeDecodeError as e:
            last_err = e
    raise RuntimeError(f"CSV 编码读取失败：{last_err}")


def detect_turbine_ids(columns) -> list[str]:
    pattern = re.compile(r"^STATUS_(#\d+)$")
    ids = []
    for c in columns:
        m = pattern.match(str(c).strip())
        if m:
            ids.append(m.group(1))
    ids = sorted(ids, key=lambda x: int(x.replace("#", "")))
    if not ids:
        raise ValueError("没有识别到 STATUS_#i 格式的状态列，例如 STATUS_#1。")
    return ids


def load_and_clean_raw(input_csv: Path, turbine_ids: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = read_csv_smart(input_csv)
    if TIME_COL not in df.columns:
        raise ValueError(f"找不到时间列 {TIME_COL}。当前前 30 个列名：{list(df.columns)[:30]}")

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    before = len(df)
    df = df.dropna(subset=[TIME_COL]).copy()
    if before != len(df):
        print(f"删除时间无法解析的行数：{before - len(df)}")

    df = df.sort_values(TIME_COL).reset_index(drop=True)

    status_cols = [f"STATUS_{tid}" for tid in turbine_ids]
    missing = [c for c in status_cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少状态码列：{missing[:20]}" + (" ..." if len(missing) > 20 else ""))

    status_num = df[status_cols].apply(pd.to_numeric, errors="coerce").round()
    valid_mask = status_num.isin(VALID_STATUS_CODES).all(axis=1)
    invalid_df = df.loc[~valid_mask, [TIME_COL]].copy()

    if not invalid_df.empty:
        invalid_detail = []
        bad = status_num.loc[~valid_mask]
        for idx, row in bad.iterrows():
            bad_cols = [c for c in status_cols if row[c] not in VALID_STATUS_CODES]
            invalid_detail.append({
                "时间": df.loc[idx, TIME_COL],
                "异常风机数量": len(bad_cols),
                "异常状态码列": ";".join(bad_cols),
                "异常状态码值": ";".join([f"{c}={row[c]}" for c in bad_cols[:50]]),
            })
        invalid_detail_df = pd.DataFrame(invalid_detail)
    else:
        invalid_detail_df = pd.DataFrame(columns=["时间", "异常风机数量", "异常状态码列", "异常状态码值"])

    invalid_summary_df = pd.DataFrame([{
        "原始时刻数": int(len(df)),
        "异常状态码时刻数": int((~valid_mask).sum()),
        "保留时刻数": int(valid_mask.sum()),
        "异常时刻占比": float((~valid_mask).sum() / len(df)) if len(df) else 0.0,
    }])

    df_valid = df.loc[valid_mask].copy().reset_index(drop=True)
    return df_valid, invalid_summary_df, invalid_detail_df


def build_maintenance_matrix(df_valid: pd.DataFrame, turbine_ids: list[str]) -> pd.DataFrame:
    out = pd.DataFrame({"timestamp": df_valid[TIME_COL]})
    for tid in turbine_ids:
        status = pd.to_numeric(df_valid[f"STATUS_{tid}"], errors="coerce").round()
        out[f"是否维护_{tid}"] = np.where(status == MAINTENANCE_STATUS_CODE, 1, 0).astype(int)
    return out


def build_15min_direct(matrix_1min: pd.DataFrame) -> pd.DataFrame:
    out = matrix_1min.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out = out.dropna(subset=["timestamp"]).copy()
    out = out[(out["timestamp"].dt.minute % 15 == 0) & (out["timestamp"].dt.second == 0)].copy()
    out = out.sort_values("timestamp").reset_index(drop=True)
    return out


def build_farm_timeseries(matrix: pd.DataFrame) -> pd.DataFrame:
    maint_cols = [c for c in matrix.columns if c.startswith("是否维护_#")]
    out = pd.DataFrame({"timestamp": matrix["timestamp"]})
    vals = matrix[maint_cols].to_numpy(dtype=int)
    out["全场风机总数"] = len(maint_cols)
    out["维护风机数量"] = vals.sum(axis=1)
    out["运行风机数量"] = len(maint_cols) - out["维护风机数量"]
    out["全场维护风机占比"] = out["维护风机数量"] / len(maint_cols)

    turbine_names = [c.replace("是否维护_", "") for c in maint_cols]
    lists = []
    for row in vals:
        lists.append(";".join([tid for tid, flag in zip(turbine_names, row) if flag == 1]))
    out["维护风机列表"] = lists
    return out


def build_concurrent_distribution(farm_ts: pd.DataFrame, sample_interval_min: float) -> pd.DataFrame:
    dist = (
        farm_ts.groupby("维护风机数量")
        .size()
        .reset_index(name="时刻数")
        .rename(columns={"维护风机数量": "同时维护风机数量"})
    )
    dist["持续时间_小时"] = dist["时刻数"] * sample_interval_min / 60.0
    dist["时间占比"] = dist["时刻数"] / dist["时刻数"].sum()
    return dist.sort_values("同时维护风机数量").reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description="生成 JMZSFD 维护矩阵宽表，并抽取 15min direct 版本")
    parser.add_argument("--input", type=str, default="", help="JMZSFD 原始CSV路径")
    parser.add_argument("--output-dir", type=str, default="", help="输出目录，默认 input 同目录下的 维护状态分析结果")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    input_csv = Path(args.input) if args.input else (Path.cwd() / DEFAULT_INPUT_NAME)
    if not input_csv.exists() and not args.input:
        input_csv = script_dir / DEFAULT_INPUT_NAME

    output_dir = Path(args.output_dir) if args.output_dir else input_csv.parent / "维护状态分析结果"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 先读取表头识别风机编号
    header_df = read_csv_smart(input_csv).head(0)
    turbine_ids = detect_turbine_ids(header_df.columns)
    print(f"识别到风机数量：{len(turbine_ids)}，范围：{turbine_ids[:3]} ... {turbine_ids[-3:]}")

    df_valid, invalid_summary, invalid_detail = load_and_clean_raw(input_csv, turbine_ids)
    print(f"保留有效时刻数：{len(df_valid)}")
    print(f"异常状态码时刻数：{int(invalid_summary.loc[0, '异常状态码时刻数'])}")

    matrix_1min = build_maintenance_matrix(df_valid, turbine_ids)
    matrix_15min = build_15min_direct(matrix_1min)
    farm_ts_1min = build_farm_timeseries(matrix_1min)
    farm_ts_15min = build_farm_timeseries(matrix_15min)
    dist_1min = build_concurrent_distribution(farm_ts_1min, sample_interval_min=1.0)
    dist_15min = build_concurrent_distribution(farm_ts_15min, sample_interval_min=15.0)

    paths = {
        "1min维护矩阵": output_dir / "jmzsfd_maintenance_matrix_1min.csv",
        "15min直接对齐维护矩阵": output_dir / "jmzsfd_maintenance_matrix_15min_direct.csv",
        "1min全场维护时序": output_dir / "jmzsfd_farm_maintenance_timeseries_1min.csv",
        "15min全场维护时序": output_dir / "jmzsfd_farm_maintenance_timeseries_15min_direct.csv",
        "1min同时维护数量分布": output_dir / "jmzsfd_farm_concurrent_maintenance_distribution_1min.csv",
        "15min同时维护数量分布": output_dir / "jmzsfd_farm_concurrent_maintenance_distribution_15min_direct.csv",
        "异常状态码汇总": output_dir / "jmzsfd_invalid_timestamp_summary.csv",
        "异常状态码明细": output_dir / "jmzsfd_invalid_timestamp_detail.csv",
    }

    matrix_1min.to_csv(paths["1min维护矩阵"], index=False, encoding="utf-8-sig")
    matrix_15min.to_csv(paths["15min直接对齐维护矩阵"], index=False, encoding="utf-8-sig")
    farm_ts_1min.to_csv(paths["1min全场维护时序"], index=False, encoding="utf-8-sig")
    farm_ts_15min.to_csv(paths["15min全场维护时序"], index=False, encoding="utf-8-sig")
    dist_1min.to_csv(paths["1min同时维护数量分布"], index=False, encoding="utf-8-sig")
    dist_15min.to_csv(paths["15min同时维护数量分布"], index=False, encoding="utf-8-sig")
    invalid_summary.to_csv(paths["异常状态码汇总"], index=False, encoding="utf-8-sig")
    invalid_detail.to_csv(paths["异常状态码明细"], index=False, encoding="utf-8-sig")

    print("\n输出完成：")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    print("\n尾流模型建议使用：jmzsfd_maintenance_matrix_15min_direct.csv")


if __name__ == "__main__":
    main()
