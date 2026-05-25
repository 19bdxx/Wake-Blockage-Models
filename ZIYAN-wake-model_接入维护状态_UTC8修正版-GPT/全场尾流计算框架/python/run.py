# run.py

"""
主程序入口模块
功能：
- 配置参数
- 调用批量计算模块
- 启动整体流程
"""

from power_batch import calculate_power_batch
import numpy as np
import os
import pandas as pd

if __name__ == "__main__":
    # ========== 基本参数配置 ==========

    # 气象数据文件路径（注意保证路径正确）
    datafile = "data/latitude_21.3_longitude_111.6.csv"

    # 结果保存目录
    output_folder = "output"

    # 如果输出目录不存在，自动创建
    os.makedirs(output_folder, exist_ok=True)

    # ========== 风机布置（用户需要填写实际坐标） ==========
    # x_coords 和 y_coords 都是数组，单位米
    # 读取风机布局文件
    _here = os.path.dirname(os.path.abspath(__file__))
    layout_path = os.path.normpath(os.path.join(_here, '..', '..', '..', '风机布局及功率推力曲线', 'turbine_layout.csv'))
    for _enc in ('utf-8-sig', 'gbk', 'gb18030'):
        try:
            layout_df = pd.read_csv(layout_path, encoding=_enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    x_coords = layout_df['X'].values
    y_coords = layout_df['Y'].values

    # ========== 启动批量计算 ==========
    calculate_power_batch(
        datafile=datafile,
        x_coords=x_coords,
        y_coords=y_coords,
        output_folder=output_folder,
        endtime=2,    # 最多处理前10000行数据
        block_size=2   # 每1000行保存一个Excel结果块
    )

    # ========== 完成提示 ==========
    print("✅ 全部计算完成！结果已保存到 output/ 文件夹")