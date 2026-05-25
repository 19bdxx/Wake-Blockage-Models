import pandas as pd


def convert_kw_to_mw(input_file, output_file):
    # 1. 读取文件
    df = pd.read_csv(input_file, sep=None, engine="python", encoding="utf-8-sig")

    # 2. 清理列名
    df.columns = [str(col).replace("\ufeff", "").strip() for col in df.columns]

    # 3. 找到所有包含 _kW 的列
    kw_cols = [col for col in df.columns if "_kW" in col]

    print("找到以下需要转换的列：")
    print(kw_cols)

    # 4. 转换单位并重命名
    for col in kw_cols:
        new_col = col.replace("_kW", "_MW")
        df[new_col] = (pd.to_numeric(df[col], errors="coerce") / 1000).round(1)

    # 5. 删除原来的 _kW 列
    df = df.drop(columns=kw_cols)

    # 6. 输出
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"处理完成，结果已保存到: {output_file}")


if __name__ == "__main__":
    input_file = r"five_experiments_output_不考虑维护-全月份\all_experiments_station_power_timeseries.csv"
    output_file = r"尾流预测与全站实测对比\all_experiments_station_power_timeseries-不考虑维护-全月份.csv"
    convert_kw_to_mw(input_file, output_file)