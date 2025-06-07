import cv2
import numpy as np
import os

# AprilTag 的真实物理尺寸 (单位：米)
# 确保这个尺寸和你打印的 AprilTag 的黑色边框边长一致
APRILTAG_SIDE_LENGTH_METERS = 0.154 # 假设你的 AprilTag 也是 15.4cm 边长

class TargetDetectorAruco:
    """
    使用 OpenCV Aruco 模块检测 AprilTag 并估计其位姿的检测器。
    """
    def __init__(self, tag_family=cv2.aruco.DICT_APRILTAG_36h11, tag_side_length=0.154):
        """
        初始化 Aruco 检测器。

        Args:
            tag_family: AprilTag/Aruco 标记的字典族。
            tag_side_length: 标记的边长（单位：米）。
        """
        self.tag_side_length = tag_side_length
        self.calibration_file_path = "camera_calibration.npz"
        self.camera_matrix, self.dist_coeffs = self.load_calibration_data()

        # 定义 Aruco 字典和检测器参数
        # 注意: 新版 OpenCV (4.7+) 中 getPredefinedDictionary 是 cv2.aruco 的一个函数
        if False:
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(tag_family)
            self.aruco_params = cv2.aruco.DetectorParameters()
            self.aruco_detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        else: # 兼容旧版 OpenCV
            self.aruco_dict = cv2.aruco.Dictionary_get(tag_family)
            self.aruco_params = cv2.aruco.DetectorParameters_create()
            self.aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
            # 在旧版中，检测函数是 cv2.aruco.detectMarkers，不需要创建 ArucoDetector 对象
            self.aruco_detector = None


        # 定义 AprilTag 的 3D 世界坐标
        # Aruco 返回的角点顺序是：左上, 右上, 右下, 左下
        # 这与你之前的 object_points 定义顺序不同，需要注意！
        # 我们将坐标系原点设在 Tag 的中心。
        half_size = self.tag_side_length / 2
        self.object_points = np.array([
            [-half_size,  half_size, 0], # 左上 (Top-Left)
            [ half_size,  half_size, 0], # 右上 (Top-Right)
            [ half_size, -half_size, 0], # 右下 (Bottom-Right)
            [-half_size, -half_size, 0]  # 左下 (Bottom-Left)
        ], dtype=np.float32)

        self.current_offset_yaw = 0.0
        self.current_offset_pitch = 0.0
        self.laser_offset_vector = np.array([0.0, 0.009, 0.0], dtype=np.float32)

    def load_calibration_data(self):
        # 这个函数和你的原代码完全一样，直接复用
        if not os.path.exists(self.calibration_file_path):
            print(f"错误：标定文件 '{self.calibration_file_path}' 未找到。")
            return None, None
        try:
            with np.load(self.calibration_file_path) as data:
                if 'camera_matrix' in data and 'dist_coeffs' in data:
                    return data['camera_matrix'], data['dist_coeffs']
                elif 'mtx' in data and 'dist' in data:
                    return data['mtx'], data['dist']
                else:
                    print("错误：标定文件中未找到键。")
                    return None, None
        except Exception as e:
            print(f"错误：加载标定文件失败: {e}")
            return None, None

    def get_target_frame(self, original_image):
        """
        检测 AprilTag，计算位姿，并在图像上绘制结果。
        """
        display_frame = original_image.copy()
        gray_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

        # cv2.imshow('Gray Image', gray_image)

        # 检测 Aruco 标记
        if self.aruco_detector: # 新版 OpenCV
             corners, ids, rejected = self.aruco_detector.detectMarkers(gray_image)
        else: # 旧版 OpenCV
             corners, ids, rejected = cv2.aruco.detectMarkers(gray_image, self.aruco_dict, parameters=self.aruco_params)


        # 如果检测到标记
        if ids is not None:
            # 在图像上绘制检测到的标记边界
            cv2.aruco.drawDetectedMarkers(display_frame, corners, ids)
            
            # 遍历所有检测到的标记
            for i, marker_id in enumerate(ids):
                # 图像上的角点
                image_points = corners[i]

                # --- 方法一: 使用 cv2.solvePnP (和你原来的方法类似) ---
                success, rotation_vector, translation_vector = cv2.solvePnP(
                    self.object_points, image_points, self.camera_matrix, self.dist_coeffs
                )
                
                # --- 方法二: 使用 Aruco 模块内置的位姿估计函数 (更推荐!) ---
                # 这个函数内部完成了 solvePnP 的工作，更直接。
                # 注意：它会为每个 marker 返回 rvec 和 tvec，所以结果是列表形式。
                # rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                #     [image_points], self.tag_side_length, self.camera_matrix, self.dist_coeffs
                # )
                # rotation_vector = rvecs[0]
                # translation_vector = tvecs[0]
                # success = True # estimatePoseSingleMarkers 总是返回结果

                if success:
                    # 在标记上绘制坐标轴
                    cv2.drawFrameAxes(display_frame, self.camera_matrix, self.dist_coeffs,
                                      rotation_vector, translation_vector, self.tag_side_length * 0.75)

                    # --- 后续的距离、角度计算和显示逻辑 (与你的代码基本一致) ---
                    distance = np.linalg.norm(translation_vector)
                    cv2.putText(display_frame, f"ID: {marker_id[0]}", (10, 30 + i*150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    cv2.putText(display_frame, f"Dist: {distance:.2f} m", (10, 60 + i*150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(display_frame, f"X: {translation_vector[0][0]:.2f}m", (10, 85 + i*150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.putText(display_frame, f"Y: {translation_vector[1][0]:.2f}m", (10, 110 + i*150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Z: {translation_vector[2][0]:.2f}m", (10, 135 + i*150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

                    # 计算 Yaw 和 Pitch (这部分逻辑不变)
                    target_vector_from_camera = translation_vector.flatten()
                    target_vector_from_laser = target_vector_from_camera - self.laser_offset_vector
                    tx_laser, ty_laser, tz_laser = target_vector_from_laser
                    
                    yaw_angle_rad = np.arctan2(tx_laser, tz_laser)
                    yaw_angle_deg = np.degrees(yaw_angle_rad)
                    pitch_angle_rad = np.arctan2(-ty_laser, np.sqrt(tx_laser**2 + tz_laser**2))
                    pitch_angle_deg = np.degrees(pitch_angle_rad)
                    
                    cv2.putText(display_frame, f"Yaw: {yaw_angle_deg:.2f} deg", (10, 160 + i*150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2) # Orange color
                    cv2.putText(display_frame, f"Pitch: {pitch_angle_deg:.2f} deg", (10, 185 + i*150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2) # Orange color

                    # 假定我们只关心第一个检测到的 Tag
                    if i == 0:
                        self.current_offset_yaw = yaw_angle_deg
                        self.current_offset_pitch = pitch_angle_deg

        else:
            cv2.putText(display_frame, "AprilTag Not Detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            self.current_offset_yaw = 0.0
            self.current_offset_pitch = 0.0
            
        return display_frame

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print(f"摄像头实际设置的分辨率: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))} * {int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

    # 使用新的 Aruco 检测器
    detector = TargetDetectorAruco(tag_side_length=APRILTAG_SIDE_LENGTH_METERS)

    if detector.camera_matrix is None or detector.dist_coeffs is None:
        print("错误：无法加载相机标定数据。")
        return

    print("\n按 'q' 键退出。")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("错误：无法读取帧")
            break

        display_frame = detector.get_target_frame(frame)
        cv2.imshow('AprilTag Pose Estimation', display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    print(f"--- 实时 AprilTag 位姿估计 ---")
    print(f"AprilTag 的边长设置为 {APRILTAG_SIDE_LENGTH_METERS * 100} 厘米。")
    main()