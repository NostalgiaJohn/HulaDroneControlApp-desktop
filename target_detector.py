import cv2
import numpy as np
import os

class TargetDetector:
    """
    目标检测器类，用于检测图像中的目标。
    目前实现了寻找黑色正方形的功能。
    """
    def load_calibration_data(self):
        if not os.path.exists(self.calibration_file_path):
            print(f"错误：标定文件 '{self.calibration_file_path}' 未找到。")
            return None, None
        try:
            with np.load(self.calibration_file_path) as data:
                if 'camera_matrix' in data and 'dist_coeffs' in data:
                    camera_matrix = data['camera_matrix']
                    dist_coeffs = data['dist_coeffs']
                    print(f"从 '{self.calibration_file_path}' 成功加载标定数据。")
                    # print("相机内参矩阵 (Camera Matrix):\n", camera_matrix)
                    # print("畸变系数 (Distortion Coefficients):\n", dist_coeffs)
                    return camera_matrix, dist_coeffs
                elif 'mtx' in data and 'dist' in data:
                    camera_matrix = data['mtx']
                    dist_coeffs = data['dist']
                    print(f"从 '{self.calibration_file_path}' 成功加载标定数据 (使用键 'mtx' 和 'dist')。")
                    # print("相机内参矩阵 (Camera Matrix):\n", camera_matrix)
                    # print("畸变系数 (Distortion Coefficients):\n", dist_coeffs)
                    return camera_matrix, dist_coeffs
                else:
                    print(f"错误：在 '{self.calibration_file_path}' 中未找到预期的键 ('camera_matrix'/'dist_coeffs' 或 'mtx'/'dist')。")
                    print(f"文件中的可用键为: {list(data.keys())}")
                    return None, None
        except Exception as e:
            print(f"错误：加载标定文件 '{self.calibration_file_path}' 失败: {e}")
            return None, None
    
    @staticmethod
    def find_square_corners(image):
        """
        在图像中寻找黑色正方形的四个角点。
        此版本使用 OTSU 法进行二值化。

        Args:
            image: 输入的BGR图像。

        Returns:
            如果找到正方形，则返回其四个角点的numpy数组 (shape=(4, 1, 2), dtype=np.float32)，
            否则返回None。角点顺序：左上, 右上, 右下, 左下。
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 增加高斯模糊有助于OTSU更好地工作，尤其是在有噪声的情况下
        blurred = cv2.GaussianBlur(gray, (5, 5), 0) # 可以尝试不同的核大小，如 (3,3) 或 (7,7)

        # 使用 OTSU 法进行二值化
        # 注意：我们仍然使用 THRESH_BINARY_INV 是因为我们假设正方形是黑色的（暗色），
        # 而背景是亮色的。OTSU 会找到一个最佳阈值 ret_otsu。
        # 小于 ret_otsu 的像素（我们的目标黑色正方形）会被设为255（白色），
        # 大于 ret_otsu 的像素会被设为0（黑色），这符合后续轮廓查找的期望。
        ret_otsu, thresh_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # print(f"OTSU's threshold: {ret_otsu}") # 可以取消注释来查看OTSU计算出的阈值

        # --- 如果OTSU效果仍然不佳，可以尝试自适应阈值 (Adaptive Thresholding) ---
        # 取消注释下面的行来使用自适应阈值，并注释掉上面的OTSU阈值化行。
        # blockSize 通常选择奇数，如 11, 15, 21 等。
        # C 是一个常数，从计算出的平均值或高斯加权平均值中减去。通常是一个较小的值，可以是正数或负数。
        # adaptive_block_size = 15 # 例如
        # adaptive_C = 4          # 例如
        # thresh_adaptive = cv2.adaptiveThreshold(blurred, 255,
        #                                     cv2.ADAPTIVE_THRESH_GAUSSIAN_C, # 或 cv2.ADAPTIVE_THRESH_MEAN_C
        #                                     cv2.THRESH_BINARY_INV,
        #                                     adaptive_block_size,
        #                                     adaptive_C)
        # thresh = thresh_adaptive # 如果使用自适应阈值，将 thresh 指向它
        thresh = thresh_otsu # 当前我们使用OTSU的结果

        # (可选) 显示二值化图像以进行调试
        # cv2.imshow("Binarized Image", thresh)

        # 查找轮廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            # 调整 approxPolyDP 的 epsilon 参数，0.01 到 0.04 * perimeter 都是常见范围
            approx = cv2.approxPolyDP(contour, 0.025 * perimeter, True) # 可以微调 0.025

            if len(approx) == 4:
                area = cv2.contourArea(approx)
                # 调整面积阈值，根据正方形在摄像头中的大致像素大小
                if area < 500 or area > (image.shape[0] * image.shape[1] * 0.8): # 过滤掉太小或太大的轮廓
                    continue

                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = float(w) / h
                # 调整宽高比阈值，使其更严格或更宽松
                if 0.80 < aspect_ratio < 1.20: # 稍微放宽一点，因为透视可能导致变形
                    # 进一步检查凸性，正方形应该是凸的
                    if not cv2.isContourConvex(approx):
                        continue

                    corners = approx.reshape(4, 2)
                    rect = np.zeros((4, 2), dtype="float32")

                    s = corners.sum(axis=1)
                    rect[0] = corners[np.argmin(s)] # 左上
                    rect[2] = corners[np.argmax(s)] # 右下

                    # 对于角点排序，使用 ptp (peak-to-peak) 即 max-min 来确定另外两个点可能更鲁棒
                    # diff = np.diff(corners, axis=1) # x-y
                    # rect[1] = corners[np.argmin(diff)] # 右上
                    # rect[3] = corners[np.argmax(diff)] # 左下

                    # 更可靠的角点排序方法：
                    # 左上: sum 最小
                    # 右下: sum 最大
                    # 为了区分右上和左下，它们有相似的 sum 值。
                    # 右上: diff (y - x) 最小 (或 x - y 最大)
                    # 左下: diff (y - x) 最大 (或 x - y 最小)
                    # 这里我们使用之前的方法，如果需要更鲁棒的排序，可以研究更复杂的策略
                    # 但通常对于近似水平的正方形，(x+y) 和 (x-y) 的组合是有效的

                    # 重新计算 diff 来确保排序正确
                    # 确保 corners 是 (4,2) 数组
                    temp_corners = corners.copy()

                    # 对点按 y 坐标排序，如果 y 相同则按 x 排序 (通常用于统一处理)
                    # temp_corners = temp_corners[np.argsort(temp_corners[:, 1])]
                    # if temp_corners[0][0] > temp_corners[1][0]: #如果前两个y值相近，x小的为左
                    #     temp_corners[[0,1]] = temp_corners[[1,0]]
                    # if temp_corners[2][0] > temp_corners[3][0]: #如果后两个y值相近，x小的为左
                    #     temp_corners[[2,3]] = temp_corners[[3,2]]
                    # rect = temp_corners # 左上，右上，左下，右下 (如果按y排序)
                    # 你需要确保这里的顺序与 OBJECT_POINTS 对应

                    # 恢复到之前的排序方式，因为它与OBJECT_POINTS的定义相匹配
                    diff_val = np.array([c[0] - c[1] for c in corners]) # x - y
                    rect[1] = corners[np.argmax(diff_val)] # 右上 (x-y 最大)
                    rect[3] = corners[np.argmin(diff_val)] # 左下 (x-y 最小)


                    # 确保 rect[0] 是左上, rect[1] 是右上, rect[2] 是右下, rect[3] 是左下
                    # 重新整理一次以确保顺序对于 solvePnP
                    # 1. 按y坐标排序，再按x坐标排序
                    sorted_corners = corners[np.lexsort((corners[:, 0], corners[:, 1]))]

                    # sorted_corners 现在是 [左上, 右上, 左下, 右下] （大致）
                    # 我们需要的是 左上, 右上, 右下, 左下
                    # 左上 (y最小，x最小) -> sorted_corners[0]
                    # 右下 (y最大，x最大) -> sorted_corners[3]
                    # 剩下的两个点是右上和左下
                    # 对于右上: y 较小, x 较大
                    # 对于左下: y 较大, x 较小
                    if sorted_corners[1][0] > sorted_corners[2][0]: # 如果第二个点的x大于第三个点的x
                        # sorted_corners[1] 是 右上
                        # sorted_corners[2] 是 左下
                        rect[0] = sorted_corners[0] # 左上
                        rect[1] = sorted_corners[1] # 右上
                        rect[3] = sorted_corners[2] # 左下
                        rect[2] = sorted_corners[3] # 右下
                    else:
                        rect[0] = sorted_corners[0] # 左上
                        rect[1] = sorted_corners[2] # 右上
                        rect[3] = sorted_corners[1] # 左下
                        rect[2] = sorted_corners[3] # 右下

                    # 另一种更简单的排序方式 (如果物体大致水平)
                    # 假设 OBJECT_POINTS 是 左上, 右上, 右下, 左下
                    center_x = np.mean(corners[:, 0])
                    center_y = np.mean(corners[:, 1])
                    final_corners = np.zeros((4,2), dtype=np.float32)
                    for point in corners:
                        if point[0] < center_x and point[1] < center_y:
                            final_corners[0] = point # 左上
                        elif point[0] > center_x and point[1] < center_y:
                            final_corners[1] = point # 右上
                        elif point[0] > center_x and point[1] > center_y:
                            final_corners[2] = point # 右下
                        elif point[0] < center_x and point[1] > center_y:
                            final_corners[3] = point # 左下

                    # 确保所有角点都被分配了
                    if np.all(final_corners != 0): # 检查是否所有角点都被正确分类
                        return final_corners.astype(np.float32).reshape(-1, 1, 2)
                    # else:
                        # print("角点分类失败") # 如果上面的中心点分类法失败

        return None


    def get_target_frame(self, original_image):
        """
        从原始图像中提取目标框架。
        """
        # 图像预处理：如果摄像头有鱼眼效果或者畸变较大，可以先进行去畸变
        # undistorted_frame = cv2.undistort(frame, CAMERA_MATRIX, DIST_COEFFS, None, CAMERA_MATRIX)
        # image_to_process = undistorted_frame
        image_to_process = original_image # 如果畸变不大，可以直接处理原始帧

        image_points = self.find_square_corners(image_to_process)
        image_height, image_width = original_image.shape[:2]
        image_center_x = image_width / 2
        image_center_y = image_height / 2

        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]


        display_frame = original_image.copy() # 在原始帧的副本上绘制，以防去畸变

        # 1. 绘制图像几何中心 (例如：蓝色圆点)
        cv2.circle(display_frame, (int(image_center_x), int(image_center_y)), 7, (255, 100, 0), -1)
        cv2.putText(display_frame, "Img Center", (int(image_center_x) + 10, int(image_center_y) + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)

        # 2. 绘制相机标定的主点 (cx, cy) (例如：红色叉)
        cv2.drawMarker(display_frame, (int(cx), int(cy)), (0, 0, 255),
                       markerType=cv2.MARKER_CROSS, markerSize=15, thickness=2)
        cv2.putText(display_frame, "Principal Pt (cx,cy)", (int(cx) + 10, int(cy) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)


        if image_points is not None:
            # 确保 image_points 是 (4, 1, 2) 形状的 float32 数组
            # print(f"Image points shape: {image_points.shape}, dtype: {image_points.dtype}")
            for point_idx, point in enumerate(image_points):
                cv2.circle(display_frame, tuple(point[0].astype(int)), 5, (0, 255, 0), -1)
                cv2.putText(display_frame, str(point_idx), tuple(point[0].astype(int) + np.array([5,5])), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,255),1)


            success, rotation_vector, translation_vector = cv2.solvePnP(
                self.object_points, image_points, self.camera_matrix, self.dist_coeffs, flags=cv2.SOLVEPNP_IPPE # PnP解算 使用 IPPE 方法
            )

            if success:
                # rotation_matrix, _ = cv2.Rodrigues(rotation_vector) # 不需要显式转换，除非要用矩阵
                axis_length = self.square_side_length_meters
                axis_points = np.float32([
                    [0, 0, 0],
                    [axis_length, 0, 0], # X
                    [0, axis_length, 0], # Y
                    [0, 0, -axis_length] # Z (OpenCV Z轴指向相机内部为正，所以绘制-Z代表向外)
                ]).reshape(-1, 3)

                projected_axis_points, _ = cv2.projectPoints(
                    axis_points, rotation_vector, translation_vector, self.camera_matrix, self.dist_coeffs
                )
                if projected_axis_points is not None: # 确保投影成功
                    origin = tuple(projected_axis_points[0].ravel().astype(int))
                    cv2.line(display_frame, origin, tuple(projected_axis_points[1].ravel().astype(int)), (0, 0, 255), 3) # X Red
                    cv2.line(display_frame, origin, tuple(projected_axis_points[2].ravel().astype(int)), (0, 255, 0), 3) # Y Green
                    cv2.line(display_frame, origin, tuple(projected_axis_points[3].ravel().astype(int)), (255, 0, 0), 3) # Z Blue

                    distance = np.linalg.norm(translation_vector)
                    cv2.putText(display_frame, f"Dist: {distance:.2f} m", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(display_frame, f"X: {translation_vector[0][0]:.2f}m", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.putText(display_frame, f"Y: {translation_vector[1][0]:.2f}m", (10, 85),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Z: {translation_vector[2][0]:.2f}m", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                
                # 从 translation_vector 获取目标在相机坐标系下的坐标
                # tx = translation_vector[0][0]
                # ty = translation_vector[1][0]
                # tz = translation_vector[2][0]

                # 1. 获取目标相对于相机的向量 (Tc)
                target_vector_from_camera = translation_vector.flatten()

                # 2. 计算目标相对于激光器的向量 (Tl = Tc - L_offset)
                target_vector_from_laser = target_vector_from_camera - self.laser_offset_vector

                # 3. 使用新的向量 Tl 计算对准激光器所需的角度
                tx_laser = target_vector_from_laser[0]
                ty_laser = target_vector_from_laser[1]
                tz_laser = target_vector_from_laser[2]

                # 计算偏航角 (yaw) - 围绕相机Y轴的旋转
                # target is tx to the right, tz in front
                yaw_angle_rad = np.arctan2(tx_laser, tz_laser)
                # 转换为度
                yaw_angle_deg = np.degrees(yaw_angle_rad)

                # 计算俯仰角 (pitch) - 围绕相机X轴的旋转
                # target is ty below, sqrt(tx^2 + tz^2) away in the XZ plane
                # We use -ty because positive ty is downwards in OpenCV camera coordinates,
                # and positive pitch usually means aiming upwards.
                pitch_angle_rad = np.arctan2(-ty_laser, np.sqrt(tx_laser**2 + tz_laser**2))
                # 转换为度
                pitch_angle_deg = np.degrees(pitch_angle_rad)

                # 显示计算出的角度
                cv2.putText(display_frame, f"Yaw: {yaw_angle_deg:.2f} deg", (10, 135),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2) # Orange color
                cv2.putText(display_frame, f"Pitch: {pitch_angle_deg:.2f} deg", (10, 160),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2) # Orange color
                
                self.current_offset_yaw = yaw_angle_deg
                self.current_offset_pitch = pitch_angle_deg

        else:
            cv2.putText(display_frame, "Square Not Detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            self.current_offset_yaw = 0.0
            self.current_offset_pitch = 0.0
        return display_frame

    def __init__(self, square_side_length_meters=0.06):
        self.square_side_length_meters = square_side_length_meters
        self.object_points = np.array([
            [-square_side_length_meters / 2, square_side_length_meters / 2, 0],  # 左上
            [square_side_length_meters / 2, square_side_length_meters / 2, 0],   # 右上
            [square_side_length_meters / 2, -square_side_length_meters / 2, 0],  # 右下
            [-square_side_length_meters / 2, -square_side_length_meters / 2, 0]   # 左下
        ], dtype=np.float32)
        self.calibration_file_path = "camera_calibration.npz"
        self.camera_matrix, self.dist_coeffs = self.load_calibration_data()
        self.current_offset_yaw = 0.0
        self.current_offset_pitch = 0.0
        self.laser_offset_vector = np.array([0.0, 0.0085, 0.0], dtype=np.float32) # 激光偏移量 | 单位m

# --- 标定文件名 ---
# CALIBRATION_FILE = "camera_calibration.npz"

# # --- 正方形的真实世界尺寸 (单位：米) ---
# SQUARE_SIDE_LENGTH_METERS = 0.06  # 6 cm

# # --- 3D模型点 (正方形在自身坐标系中的角点) ---
# OBJECT_POINTS = np.array([
#     [-SQUARE_SIDE_LENGTH_METERS / 2, SQUARE_SIDE_LENGTH_METERS / 2, 0],  # 左上
#     [SQUARE_SIDE_LENGTH_METERS / 2, SQUARE_SIDE_LENGTH_METERS / 2, 0],   # 右上
#     [SQUARE_SIDE_LENGTH_METERS / 2, -SQUARE_SIDE_LENGTH_METERS / 2, 0],  # 右下
#     [-SQUARE_SIDE_LENGTH_METERS / 2, -SQUARE_SIDE_LENGTH_METERS / 2, 0]   # 左下
# ], dtype=np.float32)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return

    # 尝试将分辨率设置为 1280x720
    target_width = 1280
    target_height = 720
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)
    
    # 读取设置后的实际分辨率
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
    print(f"请求的分辨率: {target_width} * {target_height}")
    print(f"摄像头实际设置的分辨率: {int(width)} * {int(height)}")


    # cv2.namedWindow("Binarized Image", cv2.WINDOW_NORMAL) # 如果需要显示二值化图像
    detector = TargetDetector(square_side_length_meters=0.06)  # 6 cm 正方形

    # 从相机矩阵中获取 cx, cy
    cx = detector.camera_matrix[0, 2]
    cy = detector.camera_matrix[1, 2]
    print(f"从相机矩阵加载的主点 (cx, cy): ({cx:.2f}, {cy:.2f})")


    if detector.camera_matrix is None or detector.dist_coeffs is None:
        print("错误：无法加载相机标定数据。请检查标定文件是否存在且格式正确。")
        return
    
    ret, frame_for_size = cap.read()
    if not ret:
        print("错误：无法读取摄像头帧")
        return
    image_height, image_width = frame_for_size.shape[:2]
    image_center_x = image_width / 2
    image_center_y = image_height / 2
    print(f"图像几何中心 (width/2, height/2): ({image_center_x:.2f}, {image_center_y:.2f})")

    print("\n按 'q' 键退出。")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("错误：无法读取帧")
            break

        display_frame = detector.get_target_frame(frame)

        cv2.imshow('Real-time Pose Estimation', display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    print(f"--- 实时位姿估计 ---")
    # print(f"尝试从 '{CALIBRATION_FILE}' 加载摄像头标定数据。")
    # print(f"正方形的边长已设置为 {SQUARE_SIDE_LENGTH_METERS * 100} 厘米。")
    main()