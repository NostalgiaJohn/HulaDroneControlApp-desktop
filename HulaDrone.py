# HulaDrone.py
import pyhula
import time
import cv2 # 仅当实际使用cv2功能时保留
import threading
from datetime import datetime # 用于 Controller 中的文件名
import json # 用于 Controller 中的数据转储

# 假设 Controller.py 和 PidCalculator 在同一目录下或可被导入
from Controller import Controller, PidCalculator

class HulaDrone:
    def __init__(self):
        self.instance: pyhula.UserApi = pyhula.UserApi()
        self.status: dict = {
            "connected": False,
            "battery_level": "未知",
            "heading": "未知",
            "location": ["未知", "未知"], # x, y
            "height": "未知",      # z
            "message": "等待连接..." # 可以用于显示一般信息
        }
        self.controller: Controller = None
        self._initial_heading_offset: int = 0

        self._query_thread = threading.Thread(target=self._query_loop, daemon=True)
        self._control_thread = None # 将在Controller实例化后创建

        self._query_running: bool = False
        # self.controller.running 由 Controller 内部管理，或通过 HulaDrone 的方法间接控制

        self._status_callbacks = [] # 列表，用于存储注册的回调函数

    def register_status_callback(self, callback):
        """注册一个回调函数，当无人机状态更新时调用。
           回调函数应接受一个参数：状态字典。
        """
        if callable(callback) and callback not in self._status_callbacks:
            self._status_callbacks.append(callback)

    def unregister_status_callback(self, callback):
        """注销一个已注册的回调函数。"""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def _notify_status_callbacks(self):
        """调用所有注册的回调函数，传递当前状态的副本。"""
        current_status = self.get_status() # 获取状态副本
        for callback in self._status_callbacks:
            try:
                callback(current_status)
            except Exception as e:
                print(f"执行状态回调时出错: {e}")

    def connect(self, ip: str = None) -> bool:
        """连接无人机，输入IP地址（可选）。成功返回True，失败返回False。"""
        try:
            if not ip: # 自动获取IP
                connection_success = self.instance.connect()
            else:
                connection_success = self.instance.connect(ip)

            if connection_success:
                self.status["connected"] = True
                self.status["message"] = "连接成功"
                self._initial_heading_offset = self.instance.get_yaw()[0]

                # 初始化Controller
                self.controller = Controller(
                    instance=self.instance,
                    heading_ini=self._initial_heading_offset,
                    target_location=[0, 0, 100], # 初始目标设为当前位置或默认值
                    control_interval=0.1,
                    pid_x=PidCalculator(kp=0.8, ki=0.1, kd=0.05, integral_min=-20, integral_max=20),
                    pid_y=PidCalculator(kp=0.8, ki=0.1, kd=0.05, integral_min=-20, integral_max=20),
                    pid_z=PidCalculator(kp=0.6, ki=0.1, kd=0.05, integral_min=-20, integral_max=20),
                )
                self._control_thread = threading.Thread(target=self.controller.control_loop, daemon=True)
                self.controller.pause() # 未起飞，先暂停 controller
                self._notify_status_callbacks()
                print("无人机连接成功，控制器已初始化。")
                return True
            else:
                self.status["connected"] = False
                self.status["message"] = "连接失败，请检查无人机或网络。"
                self._notify_status_callbacks()
                return False
        except Exception as e:
            self.status["connected"] = False
            self.status["message"] = f"连接过程中发生错误: {e}"
            self._notify_status_callbacks()
            print(f"连接错误: {e}")
            return False

    def get_status(self) -> dict:
        """获取无人机当前状态的副本。"""
        # 可以考虑加锁如果self.status的更新不是完全原子的，但回调机制下通常还好
        return self.status.copy()

    def _query_loop(self):
        """内部线程循环，用于定期查询无人机状态并触发回调。"""
        while self._query_running:
            if self.status["connected"]:
                try:
                    battery = self.instance.get_battery()
                    coords = self.instance.get_coordinate() # [x,y,z]
                    yaw_data = self.instance.get_yaw()

                    self.status["battery_level"] = battery
                    if coords and len(coords) == 3:
                        self.status["location"] = [coords[0], coords[1]]
                        self.status["height"] = coords[2]
                    if yaw_data:
                        self.status["heading"] = yaw_data[0] - self._initial_heading_offset
                    # message 可以由具体操作方法更新
                    self._notify_status_callbacks()
                except Exception as e:
                    print(f"状态查询错误: {e}")
                    # 可以在这里处理因查询失败导致的连接断开逻辑
                    # self.status["connected"] = False
                    # self.status["message"] = "失去连接"
                    # self._notify_status_callbacks()
                    # self._query_running = False # 或者停止查询
                    time.sleep(1) # 出错时降低查询频率
            else:
                # 如果未连接，可以减少查询尝试或完全停止，等待重新连接
                time.sleep(1)
            time.sleep(0.5) # 状态查询间隔

    def start_background_services(self):
        """启动状态查询和PID控制的背景线程。应在连接成功后调用。"""
        if not self.status["connected"]:
            self.status["message"] = "无法启动服务：无人机未连接"
            self._notify_status_callbacks()
            print(self.status["message"])
            return False

        if self.controller is None:
            self.status["message"] = "无法启动控制：控制器未初始化"
            self._notify_status_callbacks()
            print(self.status["message"])
            return False

        try:
            if not self._query_running:
                self._query_running = True
                self._query_thread.start()
                print("状态查询服务已启动。")

            # Controller 的 running 标志由其内部的 control_loop 控制开始和结束
            # HulaDrone 负责启动控制线程
            if self.controller and not self.controller.running: # 检查Controller内部状态
                if self._control_thread and not self._control_thread.is_alive():
                    self.controller.running = True # 设置Controller的运行标志
                    self._control_thread.start()
                    print("PID控制服务已启动。")
                else:
                     print("控制线程已在运行或未正确初始化。")
            elif not self.controller:
                print("控制器未初始化，无法启动控制服务。")

            self.status["message"] = "后台服务已启动"
            self._notify_status_callbacks()
            return True
        except RuntimeError as e: # 例如线程已启动
            print(f"启动后台服务时发生运行时错误 (可能线程已启动): {e}")
            self.status["message"] = f"服务启动错误: {e}"
            self._notify_status_callbacks()
            return False
        except Exception as e:
            print(f"启动后台服务失败: {e}")
            self.status["message"] = f"服务启动失败: {e}"
            self._notify_status_callbacks()
            return False


    def takeoff(self):
        if not self.status["connected"] or not self.controller:
            self.status["message"] = "未连接或控制器未就绪，无法起飞"
            self._notify_status_callbacks()
            print(self.status["message"])
            return

        if not self.controller.running or not self._control_thread.is_alive():
            self.status["message"] = "控制服务未运行，请先启动服务"
            self._notify_status_callbacks()
            print(self.status["message"])
            # 尝试自动启动服务
            if not self.start_background_services():
                return


        self.instance.single_fly_takeoff()
        self.status["message"] = "起飞命令已发送"
        # 起飞后，让无人机在当前XY，指定高度（例如50cm）悬停
        # Controller的target_location会在其循环中被使用
        initial_pos = [0, 0, 100]
        if initial_pos:
            self.controller.set_target_location([initial_pos[0], initial_pos[1], initial_pos[2]]) # 目标高度50cm
            self.status["message"] = f"已起飞，目标位置：[{initial_pos[0]}, {initial_pos[1]}, {initial_pos[2]}]"
        else:
            # 如果无法获取当前坐标，Controller会使用其初始化时的默认目标
            self.status["message"] = "已起飞，前往默认目标位置"

        if self.controller and self.controller._pause_event.is_set() == False: # 如果之前是暂停的
            self.controller.resume() # 确保PID控制器是活动的
        self._notify_status_callbacks()


    def land(self):
        if not self.status["connected"]:
            self.status["message"] = "未连接，无法降落"
            self._notify_status_callbacks()
            print(self.status["message"])
            return

        if self.controller:
            self.controller.pause() # 在发送降落指令前，先让PID控制器指令无人机悬停
            self.status["message"] = "准备降落，PID已暂停"
            self._notify_status_callbacks()
            time.sleep(0.5) # 给悬停一点时间

        self.instance.single_fly_touchdown()
        self.status["message"] = "降落命令已发送"
        # 降落后，可以考虑停止PID控制器的运行标志，但保留查询线程
        if self.controller:
             self.controller.running = False # 标记PID回路可以结束
        self._notify_status_callbacks()

    def move_to_target(self, x: float, y: float, z: float):
        """通过PID控制器移动到全局目标坐标 [x, y, z] (单位cm)。"""
        if not self.status["connected"] or not self.controller or not self.controller.running:
            self.status["message"] = "未连接或控制服务未运行，无法移动"
            self._notify_status_callbacks()
            print(self.status["message"])
            return

        if self.controller.set_target_location([x, y, z]):
            self.status["message"] = f"移动目标设定: [{x}, {y}, {z}]"
        else:
            self.status["message"] = "无效的目标位置"
        self._notify_status_callbacks()

    def right_rotation(self, rotate_degrees: int):
        """直接控制无人机旋转指定的偏航角度（非PID控制）。
           正数为右转，负数为左转。
        """
        if not self.status["connected"]:
            self.status["message"] = "未连接，无法旋转"
            self._notify_status_callbacks()
            print(self.status["message"])
            return

        if self.controller and self.controller.running:
            self.controller.pause() # 旋转时暂停PID位置控制，避免冲突
            self.status["message"] = "PID暂停以执行旋转"
            self._notify_status_callbacks()
            time.sleep(0.5)

        if rotate_degrees > 0:
            self.instance.single_fly_turnright(rotate_degrees)
            self.status["message"] = f"向右旋转 {rotate_degrees}°"
        elif rotate_degrees < 0:
            self.instance.single_fly_turnleft(abs(rotate_degrees))
            self.status["message"] = f"向左旋转 {abs(rotate_degrees)}°"
        else:
            self.status["message"] = "旋转角度为0，无操作"
        
        rotate_degrees = 0 # 重置旋转角度
        
        if self.controller and self.controller._pause_event.is_set() == False : # 检查是否是因为本次调用而暂停的
            self.controller.resume()
            self.status["message"] += "，PID已恢复"
        self._notify_status_callbacks()

    def set_heading(self, to_head: int):
        """直接控制无人机朝向指定的偏航角度（非PID控制）。
           0°为初始方向，顺时针方向增加。
        """
        if not self.status["connected"]:
            self.status["message"] = "未连接，无法设置航向"
            self._notify_status_callbacks()
            return

        if self.controller and self.controller.running:
            self.controller.pause()
            self.status["message"] = "PID已暂停以设置航向"
            self._notify_status_callbacks()
            time.sleep(0.5)

        # 计算当前航向与目标航向之间的差值
        current_heading = self.status["heading"]
        heading_diff = (to_head - current_heading) % 360
        if heading_diff > 180:
            heading_diff -= 360
        # 直接控制无人机旋转到目标航向
        if heading_diff > 0:
            self.instance.single_fly_turnright(abs(heading_diff))
            self.status["message"] = f"设置航向为 {to_head}°，向右旋转 {abs(heading_diff)}°"
        elif heading_diff < 0:
            self.instance.single_fly_turnleft(abs(heading_diff))
            self.status["message"] = f"设置航向为 {to_head}°，向左旋转 {abs(heading_diff)}°"
        else:
            self.status["message"] = f"航向已设置为 {to_head}°，无需旋转"

        if self.controller and self.controller._pause_event.is_set() == False : # 检查是否是因为本次调用而暂停的
            self.controller.resume()
            self.status["message"] += "，PID已恢复"
        self._notify_status_callbacks()



    def square_flight(self, side_length: float, unit: str = "time",completion_callback=None, step_callback=None):
        """
        执行四方形飞行路径
        
        Args:
            side_length (float): 正方形边长
            unit (str): 'time' 表示时间单位(秒)，'distance' 表示距离单位(cm)
            completion_callback (callable, optional): 飞行完成后执行的回调函数
        """
        if not self.status["connected"]:
            self.status["message"] = "未连接，无法执行四方飞行"
            self._notify_status_callbacks()
            return

        # 原始的四方飞行逻辑
        if unit == "time":
            speed = 10  # cm/s, 假设值
            actual_distance = speed * side_length # 如果side_length是秒
            print(f"四方飞行：时间模式，边长 {side_length}秒，预估距离 {actual_distance}cm/边")
        else: # unit == "distance"
            actual_distance = side_length # side_length是cm
            print(f"四方飞行：距离模式，边长 {actual_distance}cm/边")

        # 为简化，假设 actual_distance 是要飞行的距离（cm）
        # 注意：原代码中 unit=="time" 时，distance = speed * side_length / 4
        # 这里需要明确 side_length 的含义。假设这里的 side_length 已经是SDK期望的参数。
        # 如果 SDK 的 single_fly_xxx 的参数是距离 (cm):
        fly_dist = int(actual_distance) # 确保是整数
        target_pos_original = self.controller.get_target_location()
        fly_plan = list() # 初始化飞行计划列表，飞行计划包括6个点，分别由 (x, y, z, complete_right_turn_degree) 组成
        # target_pos_original 是一个列表或元组，包含 [x, y, z] 坐标
        if target_pos_original and len(target_pos_original) == 3:
            x_original, y_original, z_original = target_pos_original
            # 计算四个目标位置
            fly_plan.append((x_original - fly_dist/2, y_original - fly_dist/2, z_original, 0))
            fly_plan.append((x_original - fly_dist/2, y_original + fly_dist/2, z_original, 90))
            fly_plan.append((x_original + fly_dist/2, y_original + fly_dist/2, z_original, 90))
            fly_plan.append((x_original + fly_dist/2, y_original - fly_dist/2, z_original, 90))
            fly_plan.append((x_original - fly_dist/2, y_original - fly_dist/2, z_original, 90))
            fly_plan.append((x_original, y_original, z_original, 0))# 回到起点
        else:
            self.status["message"] = "无法获取当前目标位置，无法计算飞行路径。"
            self._notify_status_callbacks()
            return

        try:
            self.set_heading(0) # 设置航向为 0
            # 执行飞行计划
            def wrapped_completion_callback():
                """包装完成回调以添加四方飞行特定的消息"""
                self.status["message"] = "四方飞行已完成"
                self._notify_status_callbacks()
                if completion_callback:
                    completion_callback()
            
            success = self.execute_fly_plan(
                fly_plan, 
                completion_callback=wrapped_completion_callback,
                step_callback=step_callback
            )
            
            if not success:
                self.status["message"] = "四方飞行初始化失败"
                self._notify_status_callbacks()
        except Exception as e:
            self.status["message"] = f"四方飞行出错: {e}"
            print(f"四方飞行出错: {e}")
            # 如果出错，确保清理飞行计划
            self._cleanup_fly_plan()
        finally:
            self.controller.resume()
            self.status["message"] += "，PID已恢复"
            self._notify_status_callbacks()

    def toggle_laser(self, enable: bool):
        if not self.status["connected"]:
            self.status["message"] = "未连接，无法操作激光"
            self._notify_status_callbacks()
            return
        if enable:
            self.instance.plane_fly_generating(4, 10, 100)
            self.status["message"] = "激光已开启"
        else:
            self.instance.plane_fly_generating(5, 0, 0)
            self.status["message"] = "激光已关闭"
        self._notify_status_callbacks()

    def execute_fly_plan(self, fly_plan, completion_callback=None, step_callback=None):
        """
        执行飞行计划，在每个目标点到达后继续下一个点，全部完成后执行回调
        
        Args:
            fly_plan (list): 包含(x, y, z, complete_right_turn_degree)的飞行计划点列表
            completion_callback (callable, optional): 整个飞行计划完成后执行的回调函数
            step_callback (callable, optional): 每个飞行点到达后执行的回调函数，参数为当前点索引
        """
        if not fly_plan:
            self.status["message"] = "无法执行飞行计划：计划为空"
            self._notify_status_callbacks()
            return False
        
        if not self.status["connected"]:
            self.status["message"] = "无法执行飞行计划：无人机未连接"
            self._notify_status_callbacks()
            return False
        
        if self.controller is None:
            self.status["message"] = "无法执行飞行计划：控制器未初始化"
            self._notify_status_callbacks()
            return False

        # 清理可能存在的旧飞行计划
        self._cleanup_fly_plan()
        
        # 储存飞行计划和回调以供访问
        self._current_fly_plan = fly_plan
        self._current_fly_plan_index = 0
        self._fly_plan_completion_callback = completion_callback
        self._fly_plan_step_callback = step_callback
        
        # 定义目标到达的回调函数
        def on_target_reached(current_position):
            """当目标位置到达时的回调处理"""
            # 确保飞行计划正在执行
            if not hasattr(self, '_current_fly_plan') or not hasattr(self, '_current_fly_plan_index'):
                return
            
            # 更新状态消息
            current_index = self._current_fly_plan_index
            current_point = self._current_fly_plan[current_index]
            total_points = len(self._current_fly_plan)
            self.status["message"] = f"执行飞行计划：到达第{current_index + 1}/{total_points}个点：[{current_point[0]}, {current_point[1]}, {current_point[2]}]"
            self._notify_status_callbacks()
            
            # 如果存在步骤回调，执行它
            if self._fly_plan_step_callback:
                try:
                    self._fly_plan_step_callback(current_point[3])
                except Exception as e:
                    print(f"步骤回调执行错误: {e}")
            
            # 移动到下一个点
            self._current_fly_plan_index += 1
            
            # 检查是否完成了整个计划
            if self._current_fly_plan_index >= len(self._current_fly_plan):
                # 飞行计划完成
                self.status["message"] = "飞行计划已完成"
                self._notify_status_callbacks()
                
                # 执行完成回调
                if self._fly_plan_completion_callback:
                    try:
                        self._fly_plan_completion_callback()
                    except Exception as e:
                        print(f"完成回调执行错误: {e}")
                
                # 清理计划相关属性
                self._cleanup_fly_plan()
                return
            
            # 设置下一个目标点
            next_point = self._current_fly_plan[self._current_fly_plan_index][0:3] # 取前3个元素 (x, y, z)
            self.controller.set_target_location(list(next_point))
            
            # 更新状态消息
            self.status["message"] = f"执行飞行计划：前往第{self._current_fly_plan_index + 1}/{total_points}个点：[{next_point[0]}, {next_point[1]}, {next_point[2]}]"
            self._notify_status_callbacks()
        
        # 保存回调函数以便后续清理
        self._target_reached_callback = on_target_reached
        
        try:
            # 注册目标到达回调
            self.controller.register_target_reached_callback(self._target_reached_callback)
            
            # 确保控制器在运行
            if not self.controller._pause_event.is_set():
                self.controller.resume()
            
            # 设置第一个目标位置
            first_point = fly_plan[0][0:3] # 取前3个元素 (x, y, z)
            self.controller.set_target_location(list(first_point))
            self.status["message"] = f"执行飞行计划：前往第1/{len(fly_plan)}个点：[{first_point[0]}, {first_point[1]}, {first_point[2]}]"
            self._notify_status_callbacks()
            return True
            
        except Exception as e:
            self.status["message"] = f"执行飞行计划出错: {e}"
            print(f"执行飞行计划出错: {e}")
            self._cleanup_fly_plan()
            return False

    def _cleanup_fly_plan(self):
        """清理飞行计划相关的属性和回调"""
        if hasattr(self, '_target_reached_callback') and self.controller:
            self.controller.unregister_target_reached_callback(self._target_reached_callback)
            del self._target_reached_callback
        
        for attr in ['_current_fly_plan', '_current_fly_plan_index', 
                    '_fly_plan_completion_callback', '_fly_plan_step_callback']:
            if hasattr(self, attr):
                delattr(self, attr)

    def capture_image_stream(self): # 改名以示区分，此方法仅打开流
        if not self.status["connected"]:
            self.status["message"] = "未连接，无法打开视频流"
            self._notify_status_callbacks()
            return
        try:
            self.instance.Plane_cmd_swith_rtp(0)      # 开启视频流命令
            time.sleep(1)                         # 等待流初始化
            self.instance.single_fly_flip_rtp()       # 打开视频流窗口的命令
            self.status["message"] = "打开视频流命令已发送"
            # 注意：实际图像数据的获取和显示需要更复杂的处理，
            # pyhula.get_image_array() 如果可用，需要在查询循环或独立线程中处理。
            # 对于简单的“前后端分离”而不改逻辑，我们只负责发送命令。
        except Exception as e:
            self.status["message"] = f"打开视频流失败: {e}"
            print(f"打开视频流失败: {e}")
        self._notify_status_callbacks()


    def graceful_exit(self):
        """安全地停止所有无人机活动并关闭线程。"""
        print("开始执行安全退出程序...")
        self.status["message"] = "正在退出..."
        self._notify_status_callbacks()

        # 确保清理飞行计划
        self._cleanup_fly_plan()

        if self.controller:
            self.controller.running = False # 请求PID控制回路停止
            if self._control_thread and self._control_thread.is_alive():
                print("等待控制线程结束...")
                self._control_thread.join(timeout=0.5)
                if self._control_thread.is_alive():
                    print("警告：控制线程未能及时结束。")
            if hasattr(self.controller, 'json_data') and self.controller.json_data:
                try:
                    self.controller.flight_data_dump()
                    print("飞行数据已保存。")
                except Exception as e:
                    print(f"保存飞行数据时出错: {e}")


        if self.status.get("connected", False):
            print("正在尝试降落无人机...")
            self.land() # land 方法内部会暂停PID并发送降落指令
            time.sleep(4) # 给无人机足够的时间降落

        self._query_running = False # 请求查询线程停止
        if self._query_thread and self._query_thread.is_alive():
            print("等待查询线程结束...")
            self._query_thread.join(timeout=2.0)
            if self._query_thread.is_alive():
                print("警告：查询线程未能及时结束。")

        # SDK 是否有显式的断开连接方法？
        # if hasattr(self.instance, 'disconnect'):
        # self.instance.disconnect()

        self.status["connected"] = False
        self.status["message"] = "已安全退出并断开连接。"
        self._notify_status_callbacks() # 最后一次状态更新
        print("无人机接口已安全关闭。")
