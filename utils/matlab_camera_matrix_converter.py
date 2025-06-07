import scipy.io
import numpy as np

# 1. 定义 .mat 文件名和将要创建的 .npz 文件名
mat_file_path = 'utils/matlab_calibration_data.mat'
npz_file_path = 'camera_calibration.npz'

try:
    # 2. 加载 .mat 文件
    #    loadmat 返回一个字典，其中键是 MATLAB 中保存的变量名
    mat_data = scipy.io.loadmat(mat_file_path)

    # 3. 从加载的数据中提取 camera_matrix 和 dist_coeffs
    #    确保键名与你在 MATLAB 中 save 命令使用的变量名一致
    camera_matrix = mat_data['cameraMatrix']
    dist_coeffs = mat_data['distCoeffs']

    # 确保 dist_coeffs 是一个一维数组 (NumPy 通常期望的形式)
    # loadmat 可能会将其加载为二维数组 (例如 [[k1, k2, p1, p2, k3]])
    if dist_coeffs.ndim > 1:
        dist_coeffs = dist_coeffs.flatten()

    # 打印以验证 (可选)
    print("Camera Matrix (from .mat):")
    print(camera_matrix)
    print("\nDistortion Coefficients (from .mat):")
    print(dist_coeffs)
    print(f"\nShape of camera_matrix: {camera_matrix.shape}")
    print(f"Shape of dist_coeffs: {dist_coeffs.shape}")


    # 4. 保存为 .npz 文件
    #    你可以使用 savez (未压缩) 或 savez_compressed (压缩)
    np.savez(npz_file_path,
             camera_matrix=camera_matrix,
             dist_coeffs=dist_coeffs)
    # 或者使用压缩：
    # np.savez_compressed(npz_file_path,
    #                     camera_matrix=camera_matrix,
    #                     dist_coeffs=dist_coeffs)

    print(f"\nCalibration data successfully saved to {npz_file_path}")
    print("You can load it in Python using:")
    print("data = np.load('camera_calibration.npz')")
    print("camera_matrix_loaded = data['camera_matrix']")
    print("dist_coeffs_loaded = data['dist_coeffs']")


except FileNotFoundError:
    print(f"错误: 文件 '{mat_file_path}' 未找到。请确保 MATLAB 脚本已成功运行并生成该文件。")
except KeyError as e:
    print(f"错误: 无法在 '{mat_file_path}' 中找到预期的变量。缺失的键: {e}")
    print("请检查 MATLAB 保存时的变量名是否与 Python 加载时使用的键名 ('cameraMatrix', 'distCoeffs') 一致。")
except Exception as e:
    print(f"处理文件时发生错误: {e}")