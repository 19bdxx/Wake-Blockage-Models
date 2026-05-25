# power_batch.py

"""
批量处理气象数据，计算大规模风机功率模块
功能：
- 按块读取气象数据
- 多进程并行每个时刻的风场计算
- 保存每个数据块的结果到Excel文件
"""

import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from power_single import calculate_power_single

def process_single_time(i, a100, u_j100, x_coords, y_coords, n_turbines):
    """
    单个时间步的计算函数
    输入：
        i         —— 当前处理的时刻索引
        a100      —— 当前块所有时刻的风向数组
        u_j100    —— 当前块所有时刻的风速数组
        x_coords  —— 风机原始x坐标数组
        y_coords  —— 风机原始y坐标数组
        n_turbines —— 风机总数
    输出：
        uj        —— 当前时刻各风机最终风速
        P         —— 当前时刻各风机输出功率
        P_total   —— 当前时刻全场总功率
        sorted_C_out —— 当前时刻风机编号排序结果
    """

    # 取出当前时刻的风向角、风速
    a = a100[i]
    u100 = u_j100[i]

    # 根据风向旋转风机坐标（顺时针旋转）
    X1 = x_coords * np.cos(np.deg2rad(270 - a)) - y_coords * np.sin(np.deg2rad(270 - a))
    Y1 = y_coords * np.cos(np.deg2rad(270 - a)) + x_coords * np.sin(np.deg2rad(270 - a))

    # 将风机按旋转后的x坐标升序排列
    A = np.vstack((X1, Y1, np.arange(1, n_turbines + 1)))  # 组合成矩阵
    idx_sort = np.argsort(A[0, :])
    X1_sorted = A[0, idx_sort]
    Y1_sorted = A[1, idx_sort]
    sorted_C = A[2, idx_sort]  # 排序后的风机编号

    # 调用单时刻计算模块
    uj, P, P_total, sorted_C_out = calculate_power_single(u100, X1_sorted, Y1_sorted, sorted_C)

    return uj, P, P_total, sorted_C_out

def calculate_power_batch(datafile, x_coords, y_coords, output_folder, endtime=10000, block_size=1000):
    """
    批量计算函数
    输入：
        datafile —— 气象数据CSV文件路径
        x_coords —— 风机x坐标数组
        y_coords —— 风机y坐标数组
        output_folder —— 输出结果保存的文件夹
        endtime —— 最多处理的数据行数（默认10000）
        block_size —— 每块数据大小（默认1000行）
    """

    # 读取气象数据
    data = pd.read_csv(datafile)
    endtime = min(endtime, len(data))
    num_blocks = int(np.ceil(endtime / block_size))  # 计算总块数

    for block in range(num_blocks):
        # 当前块的起止索引
        start_idx = block * block_size
        end_idx = min((block + 1) * block_size, endtime)
        block_data = data.iloc[start_idx:end_idx]

        # 提取风向角、风速、时间
        a100 = block_data.iloc[:, 13].values  # 第14列是风向角
        u_j100 = block_data.iloc[:, 12].values  # 第13列是100米风速
        time = block_data.iloc[:, 0].values  # 第1列是时间戳

        n_turbines = len(x_coords)  # 风机总数

        # 初始化存储数组
        uj_all = np.zeros((n_turbines, len(a100)))       # 各风机风速
        P_all = np.zeros((n_turbines, len(a100)))         # 各风机功率
        P_total_all = np.zeros(len(a100))                 # 每时刻总功率
        sorted_all = np.zeros((n_turbines, len(a100)))    # 各时刻风机排序编号

        # 用partial封装固定参数，只变化i
        partial_process = partial(
            process_single_time,
            a100=a100,
            u_j100=u_j100,
            x_coords=x_coords,
            y_coords=y_coords,
            n_turbines=n_turbines
        )

        # 多进程并行计算
        with ProcessPoolExecutor() as executor:
            results = list(executor.map(partial_process, range(len(a100))))

        # 逐个时间步整理计算结果
        for i, (uj, P, P_total, sorted_C) in enumerate(results):
            uj_all[:, i] = uj
            P_all[:, i] = P
            P_total_all[i] = P_total
            sorted_all[:, i] = sorted_C

        # 打包成DataFrame
        time_series = pd.DataFrame({'time': time, 'u_j100': u_j100, 'a100': a100, 'P_total': P_total_all})
        uj_df = pd.DataFrame(uj_all.T, columns=[f'uj_{k+1}' for k in range(n_turbines)])
        P_df = pd.DataFrame(P_all.T, columns=[f'P_{k+1}' for k in range(n_turbines)])
        sorted_df = pd.DataFrame(sorted_all.T, columns=[f'sorted_{k+1}' for k in range(n_turbines)])

        # 合并最终结果
        result = pd.concat([time_series, uj_df, P_df, sorted_df], axis=1)

        # 生成文件名并保存
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename = f'result_block_{block+1}_{timestamp}.xlsx'
        result.to_excel(f'{output_folder}/{filename}', index=False)

        print(f"✅ 完成数据块 {block+1}/{num_blocks}")