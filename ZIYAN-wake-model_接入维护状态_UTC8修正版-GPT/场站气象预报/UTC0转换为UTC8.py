# -*- coding: utf-8 -*-
"""
将 ERA5 气象预报 CSV 的时间从 UTC0 转换为 UTC8。

输入文件要求：
    至少包含 valid_time 列。

输出文件：
    在原 valid_time 基础上 +8 小时；
    其他列不变。
"""

from pathlib import Path
import argparse
import pandas as pd


def convert_forecast_utc0_to_utc8(input_csv: Path, output_csv: Path):
    if not input_csv.exists():
        raise FileNotFoundError(f"找不到输入文件：{input_csv}")

    try:
        df = pd.read_csv(input_csv, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(input_csv, encoding="gbk")

    if "valid_time" not in df.columns:
        raise ValueError(
            f"气象预报文件中找不到 valid_time 列。当前列名为：{list(df.columns)}"
        )

    df["valid_time"] = pd.to_datetime(df["valid_time"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["valid_time"]).copy()
    after = len(df)

    if before != after:
        print(f"提示：有 {before - after} 行 valid_time 无法解析，已删除。")

    # UTC0 -> UTC8
    df["valid_time"] = df["valid_time"] + pd.Timedelta(hours=8)

    df = df.sort_values("valid_time").reset_index(drop=True)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print("转换完成。")
    print(f"输入文件：{input_csv}")
    print(f"输出文件：{output_csv}")
    print(f"转换后时间范围：{df['valid_time'].min()} 至 {df['valid_time'].max()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=r"C:\Users\29949\Desktop\尾流模型建模\ZIYAN-wake-model_接入维护状态_UTC8修正版\场站气象预报\wind_lat_33.250_lon_121.500.csv",
        help="原始 UTC0 气象预报 CSV 路径",
    )
    parser.add_argument(
        "--output",
        default=r"C:\Users\29949\Desktop\尾流模型建模\ZIYAN-wake-model_接入维护状态_UTC8修正版\场站气象预报\wind_lat_33.250_lon_121.500-UTC8.csv",
        help="输出 UTC8 气象预报 CSV 路径",
    )

    args = parser.parse_args()

    convert_forecast_utc0_to_utc8(
        input_csv=Path(args.input),
        output_csv=Path(args.output),
    )


if __name__ == "__main__":
    main()