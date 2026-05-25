# -*- coding: utf-8 -*-
"""
从 JMZSFD 宽表数据中提取场站级轻量 CSV。

输出字段：
1. timestamp
2. JMZS_ACTIVE_POWER_STATION
3. JMZS_LIMIT_POWER
4. JMZS_FAN_ACTIVE_POWER_SUM
5. JMZS_FAN_WINDSPEED_MEAN

计算规则：
- JMZS_ACTIVE_POWER_STATION = 原文件 ACTIVE_POWER_STATION
- JMZS_LIMIT_POWER = 原文件 LIMIT_POWER
- JMZS_FAN_ACTIVE_POWER_SUM =
    所有非维护风机，即 STATUS_#i != 6 的风机，
    max(0, ACTIVE_POWER_#i) 之和
- JMZS_FAN_WINDSPEED_MEAN =
    所有非维护风机的 WINDSPEED_#i 均值

注意：
- 99999 视为人工修正/未知值，不参与计算。
- STATUS_#i == 6 的风机不参与功率求和和风速均值。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


TIME_COL = "timestamp"
STATION_POWER_COL = "ACTIVE_POWER_STATION"
LIMIT_POWER_COL = "LIMIT_POWER"

N_FANS = 58
UNKNOWN_VALUE = 99999


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="gbk")

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)

    if suffix == ".parquet":
        return pd.read_parquet(path)

    raise ValueError(f"暂不支持的输入文件类型: {suffix}")


def write_table(df: pd.DataFrame, path: Path) -> None:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return

    if suffix in [".xlsx", ".xls"]:
        df.to_excel(path, index=False)
        return

    if suffix == ".parquet":
        df.to_parquet(path, index=False)
        return

    raise ValueError(f"暂不支持的输出文件类型: {suffix}")


def require_columns(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"原始数据缺少必要字段: {missing}")


def build_light_station_csv(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, [TIME_COL, STATION_POWER_COL, LIMIT_POWER_COL])

    df = df.copy()

    # 时间列
    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    bad_time_rows = int(df[TIME_COL].isna().sum())
    if bad_time_rows > 0:
        print(f"警告：有 {bad_time_rows} 行 timestamp 无法解析，将删除。")
        df = df.dropna(subset=[TIME_COL]).copy()

    # 基础输出
    out = pd.DataFrame()
    out["timestamp"] = df[TIME_COL]
    out["JMZS_ACTIVE_POWER_STATION"] = pd.to_numeric(
        df[STATION_POWER_COL].replace(UNKNOWN_VALUE, np.nan),
        errors="coerce",
    )
    out["JMZS_LIMIT_POWER"] = pd.to_numeric(
        df[LIMIT_POWER_COL].replace(UNKNOWN_VALUE, np.nan),
        errors="coerce",
    )

    fan_power_values = []
    fan_windspeed_values = []

    missing_fans = []

    for fan_id in range(1, N_FANS + 1):
        status_col = f"STATUS_#{fan_id}"
        power_col = f"ACTIVE_POWER_#{fan_id}"
        windspeed_col = f"WINDSPEED_#{fan_id}"

        required = [status_col, power_col, windspeed_col]
        missing = [c for c in required if c not in df.columns]
        if missing:
            missing_fans.append((fan_id, missing))
            continue

        status = pd.to_numeric(
            df[status_col].replace(UNKNOWN_VALUE, np.nan),
            errors="coerce",
        )

        active_power = pd.to_numeric(
            df[power_col].replace(UNKNOWN_VALUE, np.nan),
            errors="coerce",
        )

        windspeed = pd.to_numeric(
            df[windspeed_col].replace(UNKNOWN_VALUE, np.nan),
            errors="coerce",
        )

        # 非维护风机：状态码不等于 6
        # 同时要求状态码非空，避免 UNKNOWN 或异常状态误参与
        non_maintenance_mask = status.notna() & (status != 6)

        # 功率：非维护风机参与；max(0, ACTIVE_POWER)
        # 维护风机或无效值置为 NaN，最后求和时按 skipna 处理
        valid_power = active_power.where(non_maintenance_mask)
        valid_power = valid_power.clip(lower=0)

        # 风速：非维护风机参与均值
        valid_windspeed = windspeed.where(non_maintenance_mask)

        fan_power_values.append(valid_power)
        fan_windspeed_values.append(valid_windspeed)

    if missing_fans:
        print("警告：以下风机缺少必要字段，将跳过：")
        for fan_id, missing in missing_fans:
            print(f"  #{fan_id}: {missing}")

    if not fan_power_values:
        raise ValueError("没有任何风机可用于计算，请检查列名是否为 STATUS_#1 / ACTIVE_POWER_#1 / WINDSPEED_#1 格式。")

    fan_power_df = pd.concat(fan_power_values, axis=1)
    fan_windspeed_df = pd.concat(fan_windspeed_values, axis=1)

    # 所有非维护风机 max(0, ACTIVE_POWER) 之和
    # min_count=1 表示如果某一行所有风机都是 NaN，则结果为 NaN，而不是 0
    out["JMZS_FAN_ACTIVE_POWER_SUM"] = fan_power_df.sum(axis=1, skipna=True, min_count=1)
    out["JMZS_FAN_ACTIVE_POWER_SUM"] =  out["JMZS_FAN_ACTIVE_POWER_SUM"]/1000
    # 所有非维护风机风速均值
    out["JMZS_FAN_WINDSPEED_MEAN"] = fan_windspeed_df.mean(axis=1, skipna=True)

    out = out.sort_values("timestamp").reset_index(drop=True)

    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 JMZSFD 宽表中提取场站级轻量 CSV"
    )
    parser.add_argument(
        "--input",
        default="JMZSFD_202309-202407-处理后.csv",
        help="输入 JMZSFD 宽表文件，建议使用最终处理后的 JMZSFD_final_processed.csv",
    )
    parser.add_argument(
        "--output",
        default="JMZSFD_202309-202407-处理后-获取功率和用于尾流比较.csv",
        help="输出轻量 CSV 文件路径",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = read_table(input_path)
    out = build_light_station_csv(df)
    write_table(out, output_path)

    print("提取完成。")
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")
    print(f"输出行数: {len(out)}")
    print("输出字段:")
    for c in out.columns:
        print(f"  - {c}")

    print("\n结果预览:")
    print(out.head(10).to_string(index=False))


if __name__ == "__main__":
    main()