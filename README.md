# Hula 无人机激光打靶

## 标定相机
使用无人机相机拍摄10-20张棋盘格标定板图片，打开Matlab，使用App中的Camera Calibrator工具进行标定，得到相机内参和畸变系数。

然后，使用utils中的`matlab_camera_matrix_converter.py`脚本，将Matlab导出的相机内参和畸变系数转换为NumPy格式，保存为`camera_calibration.npz`文件。

## 测量激光发射器和相机的相对位置
由于计算的偏差yaw和pitch是相对于相机坐标系的，因此需要测量激光发射器和相机的相对位置。可以使用尺子或其他测量工具，记录下激光发射器和相机之间的距离，以此在PnP解算后，通过向量相减加上一个translation_vector的偏差。

## 启动
启动打靶需要在`main_frontend.py`GUI启动视频流、目标检测和“打靶”按钮。这样无人机就会在检测到靶子后自动开始旋转yaw和pitch角度打靶。

## 运行环境
- Python 3.6.7

## 目录结构
main_frontend.py # GUI主程序
HulaDrone.py # 无人机控制程序
target_detector.py # 目标检测程序
utils/ # 工具函数目录 主要是相机标定相关
  - matlab_camera_matrix_converter.py # Matlab相机矩阵转换脚本
  - camera_calibration.npz # 相机标定文件
