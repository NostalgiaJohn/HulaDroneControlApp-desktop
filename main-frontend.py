# main_customtkinter_enhanced.py (HulaDroneGUI with CustomTkinter - Enhanced)
import matplotlib.font_manager
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
matplotlib.use("TkAgg")
import numpy as np
import PIL.Image, PIL.ImageTk
import cv2
import threading
import time
import queue
import os

from HulaDrone import HulaDrone # 无人机控制模块

class HulaDroneGUI_CTk_Enhanced:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Hula 无人机控制")
        self.root.geometry("800x400")  # 初始窗口大小较小，之后会调整
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing_window)

        # --- 主题设置 ---
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        # --- 加载字体 ---
        fonts_path = "./fonts/"
        if os.path.exists(fonts_path):
            font_files = [
                "PingFangSC-Light.otf", "PingFangSC-Medium.otf", 
                "PingFangSC-Regular.otf", "PingFangSC-Semibold.otf",
                "PingFangSC-Thin.otf", "PingFangSC-Ultralight.otf"
            ]
            for font in font_files:
                if os.path.exists(os.path.join(fonts_path, font)):
                    ctk.FontManager().load_font(os.path.join(fonts_path, font))

        # --- 样式设置 ---
        self.font_main = ("PingFangSC-Regular", 17)
        self.font_small = ("PingFangSC-Medium", 14)
        self.font_title = ("PingFangSC-Semibold", 22, "bold")
        self.corner_radius = 8
        self.padding = 10
        self.button_height = 35
        self.image_width = 1280//3
        self.image_height = 720//3

        # --- 初始化无人机实例和状态 ---
        self.drone = HulaDrone()
        self.drone.register_status_callback(self.update_status_display_from_callback)

        self.default_ip = ""
        self.gui_active = False  # 跟踪GUI是否处于活动状态
        self.connected = False  # 跟踪连接状态
        
        # 飞行路径数据和视频流相关
        self.flight_path_data = {
            'x': [],
            'y': [],
            'z': [],
            'timestamps': []
        }
        self.video_stream_active = False
        self.frame_raw_queue = queue.Queue(maxsize=1)  # 只保存最新帧
        self.frame_update_queue = queue.Queue(maxsize=1)  # 只保存最新帧
        
        # --- 创建主容器 ---
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=self.padding, pady=self.padding)
        
        # --- 初始化只显示连接UI ---
        self.setup_connection_frame()
        
        # --- 创建但隐藏主界面框架 ---
        self.main_interface_frame = ctk.CTkFrame(self.root)
        # 不pack它，直到连接成功

        # # Track all scheduled callbacks and animations
        self.scheduled_callbacks = []
        self.cleanup_in_progress = False
        
    def setup_connection_frame(self):
        """创建连接界面"""
        self.connection_frame = ctk.CTkFrame(self.main_container)
        self.connection_frame.pack(fill="both", expand=True)
        
        # 标题
        ctk.CTkLabel(
            self.connection_frame, 
            text="Hula 无人机控制系统", 
            font=self.font_title
        ).pack(pady=(20, 30))
        
        # IP输入框架
        ip_frame = ctk.CTkFrame(self.connection_frame, fg_color="transparent")
        ip_frame.pack(pady=10, fill="x", padx=50)
        
        ctk.CTkLabel(
            ip_frame, 
            text="无人机IP地址:", 
            font=self.font_main
        ).pack(side="left", padx=(0, 10))
        
        self.ip_entry = ctk.CTkEntry(
            ip_frame, 
            placeholder_text="输入IP地址或留空", 
            font=self.font_main,
            width=250,
            corner_radius=self.corner_radius
        )
        self.ip_entry.insert(0, self.default_ip)
        self.ip_entry.pack(side="left", fill="x", expand=True)
        
        # 连接按钮
        self.connect_button = ctk.CTkButton(
            self.connection_frame, 
            text="连接无人机", 
            command=self.action_connect_drone,
            font=self.font_main, 
            height=40, 
            width=200,
            corner_radius=self.corner_radius
        )
        self.connect_button.pack(pady=20)
        
        # 状态显示区域
        status_frame = ctk.CTkFrame(self.connection_frame, fg_color="transparent")
        status_frame.pack(pady=10, fill="x", padx=20)
        
        self.status_label = ctk.CTkLabel(
            status_frame, 
            text="状态: 等待连接", 
            font=self.font_main, 
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=5)
        
        self.battery_label = ctk.CTkLabel(
            status_frame, 
            text="电池: --", 
            font=self.font_small, 
            anchor="w"
        )
        self.battery_label.pack(fill="x", pady=2)
        
        self.position_label = ctk.CTkLabel(
            status_frame, 
            text="位置: --", 
            font=self.font_small, 
            anchor="w"
        )
        self.position_label.pack(fill="x", pady=2)
        
        self.heading_label = ctk.CTkLabel(
            status_frame, 
            text="航向: --", 
            font=self.font_small, 
            anchor="w"
        )
        self.heading_label.pack(fill="x", pady=2)
        
    def setup_main_interface(self):
        """创建连接成功后的主界面"""
        # 如果已经创建过，就不重复创建
        if hasattr(self, 'main_interface_created') and self.main_interface_created:
            return
        
        # 设置标记，避免重复创建
        self.main_interface_created = True
        
        # 调整窗口大小以适应完整界面
        self.root.geometry("1200x850")
        
        # 主界面采用网格布局
        self.main_interface_frame.columnconfigure(0, weight=3)  # 控制区域
        self.main_interface_frame.columnconfigure(1, weight=2)  # 显示区域
        self.main_interface_frame.rowconfigure(0, weight=1)     # 单行布局
        
        # 创建左侧控制区域
        self.control_frame = ctk.CTkFrame(self.main_interface_frame)
        self.control_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        
        # 配置控制区域网格
        self.control_frame.columnconfigure(0, weight=1)
        self.control_frame.rowconfigure(0, weight=0)  # 连接状态UI (已有信息复制过来)
        self.control_frame.rowconfigure(1, weight=1)  # 飞行控制UI
        self.control_frame.rowconfigure(2, weight=1)  # 正方形飞行UI
        self.control_frame.rowconfigure(3, weight=1)  # 附件控制UI
        
        # 创建右侧显示区域
        self.display_frame = ctk.CTkFrame(self.main_interface_frame)
        self.display_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
        
        # 配置显示区域网格
        self.display_frame.columnconfigure(0, weight=1)
        self.display_frame.rowconfigure(0, weight=1)  # 视频流
        self.display_frame.rowconfigure(1, weight=1)  # 飞行路径
        
        # --- 设置各子区域 ---
        
        # 1. 控制区域
        # 连接状态信息复制到新位置
        self.setup_connection_info_ui(self.control_frame)
        self.setup_flight_control_ui(self.control_frame)
        self.setup_square_flight_ui(self.control_frame)
        self.setup_laser_video_ui(self.control_frame)
        
        # 2. 显示区域
        self.setup_display_ui()
        
    def show_main_interface(self):
        """显示主界面，隐藏连接界面"""
        # 确保已创建主界面
        self.setup_main_interface()
        
        # 隐藏连接界面
        self.connection_frame.pack_forget()
        self.main_container.pack_forget()
        
        # 显示主界面
        self.main_interface_frame.pack(fill="both", expand=True, padx=self.padding, pady=self.padding)
        
    def setup_display_ui(self):
        """设置显示区域：视频流和飞行路径"""
        # 视频流显示区域
        video_frame = self._create_section_frame(self.display_frame, "视频流显示", 0)
        video_frame.grid_rowconfigure(0, weight=1)
        video_frame.grid_columnconfigure(0, weight=1)
        
        # 创建Matplotlib图形用于显示视频
        self.video_fig = plt.figure(figsize=(10.7, 3))
        self.video_ax = plt.Axes(self.video_fig, [0, 0, 1, 1], facecolor='black')
        self.video_ax.set_axis_off()
        self.video_ax.set_facecolor("black")
        self.video_fig.add_axes(self.video_ax)
        
        # 创建初始黑色图像
        self.video_img = self.video_ax.imshow(np.zeros((self.image_height, self.image_width, 3), dtype=np.uint8))
        
        # 嵌入Matplotlib到Tkinter
        self.video_canvas = FigureCanvasTkAgg(self.video_fig, master=video_frame)
        self.video_canvas_widget = self.video_canvas.get_tk_widget()
        self.video_canvas_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.video_canvas_widget.config(background="black")
        
        # 添加状态文本显示
        self.video_status_label = ctk.CTkLabel(
            video_frame, 
            text="未开启视频流", 
            font=self.font_small,
            corner_radius=self.corner_radius
        )
        self.video_status_label.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # 飞行路径显示区域
        path_frame = self._create_section_frame(self.display_frame, "飞行路径", 1)
        path_frame.grid_rowconfigure(0, weight=1)
        path_frame.grid_columnconfigure(0, weight=1)
        
        # 设置 Matplotlib 字体
        font = matplotlib.font_manager.FontProperties(fname="./fonts/PingFangSC-Regular.otf")
        # plt.rcParams['font.family'] = 'PingFang SC'
        # 创建Matplotlib图形用于显示路径
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.ax.set_title("无人机飞行轨迹", fontproperties=font)
        self.ax.set_xlabel("X 坐标 (cm)", fontproperties=font)
        self.ax.set_ylabel("Y 坐标 (cm)", fontproperties=font)
        self.ax.grid(True)
        
        # 初始化空的路径线和当前位置点
        self.path_line, = self.ax.plot([], [], 'b-', linewidth=1.5, label='飞行路径')
        self.current_pos, = self.ax.plot([], [], 'ro', markersize=8, label='当前位置')
        self.ax.legend(loc='upper right', prop={'family': 'Microsoft YaHei'})
        
        # 设置轴范围初始值
        self.ax.set_xlim([-300, 300])
        self.ax.set_ylim([-300, 300])
        
        # 将Matplotlib图形嵌入Tkinter窗口
        self.canvas = FigureCanvasTkAgg(self.fig, master=path_frame)
        self.canvas.draw()
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # 添加工具按钮
        tools_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        tools_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            tools_frame, 
            text="重置视图", 
            command=self.reset_path_view,
            height=30, 
            width=100,
            font=self.font_small, 
            corner_radius=self.corner_radius
        ).pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(
            tools_frame, 
            text="清除轨迹", 
            command=self.clear_flight_path,
            height=30, 
            width=100,
            font=self.font_small, 
            corner_radius=self.corner_radius
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            tools_frame, 
            text="保存图像", 
            command=self.save_flight_path_image,
            height=30, 
            width=100,
            font=self.font_small, 
            corner_radius=self.corner_radius
        ).pack(side="left", padx=5)

    def _create_section_frame(self, parent, title_text, row, column=0, columnspan=1):
        """创建带标题的区域框架"""
        section_container = ctk.CTkFrame(parent, fg_color="transparent")
        section_container.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=self.padding, pady=self.padding)
        
        section_container.columnconfigure(0, weight=1)
        section_container.rowconfigure(0, weight=0)  # 标题
        section_container.rowconfigure(1, weight=1)  # 内容
        
        # 标题
        section_title = ctk.CTkLabel(section_container, text=title_text, font=self.font_title, anchor="w")
        section_title.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # 内容框架
        frame = ctk.CTkFrame(section_container, corner_radius=self.corner_radius)
        frame.grid(row=1, column=0, sticky="nsew")
        
        return frame

    ## --- 连接与状态 UI ---
    def setup_connection_info_ui(self, parent_container):
        frame = self._create_section_frame(parent_container, "连接与状态", 0)
        frame.grid_columnconfigure(1, weight=1) # IP entry expands
        
        # 状态区域
        status_sub_frame = ctk.CTkFrame(frame, fg_color="transparent")
        status_sub_frame.grid(row=1, column=0, columnspan=3, padx=self.padding, pady=self.padding, sticky="ew")
        status_sub_frame.grid_columnconfigure((0,1,2), weight=1)

        # 复制状态标签
        self.main_status_label = ctk.CTkLabel(status_sub_frame, text="状态: 已连接", font=self.font_main, anchor="w")
        self.main_status_label.grid(row=0, column=0, columnspan=3, pady=(5,10), sticky="ew")

        self.main_battery_label = ctk.CTkLabel(status_sub_frame, text=self.battery_label.cget("text"), font=self.font_small, anchor="w")
        self.main_battery_label.grid(row=1, column=0, pady=2, sticky="w")

        self.main_position_label = ctk.CTkLabel(status_sub_frame, text=self.position_label.cget("text"), font=self.font_small, anchor="w")
        self.main_position_label.grid(row=1, column=1, pady=2, sticky="w")

        self.main_heading_label = ctk.CTkLabel(status_sub_frame, text=self.heading_label.cget("text"), font=self.font_small, anchor="w")
        self.main_heading_label.grid(row=1, column=2, pady=2, sticky="w")

    ## --- 飞行控制 UI ---
    def setup_flight_control_ui(self, parent_container):
        frame = self._create_section_frame(parent_container, "飞行控制", 1)
        frame.grid_columnconfigure((1,3,5), weight=0) # Entries fixed width
        frame.grid_columnconfigure(6, weight=1) # Move button can expand

        # Row 0: Core Actions
        core_actions_frame = ctk.CTkFrame(frame, fg_color="transparent")
        core_actions_frame.grid(row=0, column=0, columnspan=7, pady=self.padding, padx=self.padding, sticky="ew")
        core_actions_frame.grid_columnconfigure((0,1,2), weight=1) # Distribute buttons evenly

        ctk.CTkButton(core_actions_frame, text="准备", command=self.action_start_services, height=self.button_height, font=self.font_main, corner_radius=self.corner_radius).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(core_actions_frame, text="起飞", command=self.action_takeoff, height=self.button_height, font=self.font_main, corner_radius=self.corner_radius).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(core_actions_frame, text="降落", command=self.action_land, height=self.button_height, font=self.font_main, corner_radius=self.corner_radius).grid(row=0, column=2, padx=5, sticky="ew")

        # Row 1: Movement
        move_entry_width = 80
        ctk.CTkLabel(frame, text="X (cm):", font=self.font_main).grid(row=1, column=0, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.x_entry = ctk.CTkEntry(frame, width=move_entry_width, font=self.font_main, corner_radius=self.corner_radius); self.x_entry.insert(0, "0")
        self.x_entry.grid(row=1, column=1, padx=5, pady=self.padding)

        ctk.CTkLabel(frame, text="Y (cm):", font=self.font_main).grid(row=1, column=2, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.y_entry = ctk.CTkEntry(frame, width=move_entry_width, font=self.font_main, corner_radius=self.corner_radius); self.y_entry.insert(0, "0")
        self.y_entry.grid(row=1, column=3, padx=5, pady=self.padding)

        ctk.CTkLabel(frame, text="Z (cm):", font=self.font_main).grid(row=1, column=4, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.z_entry = ctk.CTkEntry(frame, width=move_entry_width, font=self.font_main, corner_radius=self.corner_radius); self.z_entry.insert(0, "50")
        self.z_entry.grid(row=1, column=5, padx=5, pady=self.padding)

        ctk.CTkButton(frame, text="移动", command=self.action_move_to_target, height=self.button_height, font=self.font_main, corner_radius=self.corner_radius).grid(row=1, column=6, padx=(self.padding, self.padding), pady=self.padding, sticky="ew")

        # Row 2: Rotation
        ctk.CTkLabel(frame, text="右转 (度):", font=self.font_main).grid(row=2, column=0, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.rotation_entry = ctk.CTkEntry(frame, width=move_entry_width, font=self.font_main, corner_radius=self.corner_radius); self.rotation_entry.insert(0, "0")
        self.rotation_entry.grid(row=2, column=1, padx=5, pady=self.padding)
        ctk.CTkButton(frame, text="开始旋转", command=self.action_rotation, height=self.button_height, font=self.font_main, corner_radius=self.corner_radius).grid(row=2, column=2, columnspan=2, padx=(self.padding, 5), pady=self.padding, sticky="ew")

        # Row 2: Set Heading
        ctk.CTkLabel(frame, text="航向 (度):", font=self.font_main).grid(row=2, column=4, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.heading_entry = ctk.CTkEntry(frame, width=move_entry_width, font=self.font_main, corner_radius=self.corner_radius); self.heading_entry.insert(0, "0")
        self.heading_entry.grid(row=2, column=5, padx=5, pady=self.padding)
        ctk.CTkButton(
            frame, text="设置航向", command=self.action_set_heading,
            height=self.button_height, font=self.font_main, corner_radius=self.corner_radius
        ).grid(row=2, column=6, padx=(self.padding, 5), pady=self.padding, sticky="ew")

        # Row 3: Manual Control
        # 添加方向控制界面
        self.setup_direction_control_ui(frame, 3)  # 从第3行开始

        # Row 4: Detect and aim routine
        ctk.CTkButton(
            frame, text="目标检测", command=self.action_detect,
            height=self.button_height, font=self.font_main, corner_radius=self.corner_radius
        ).grid(row=4, column=0, columnspan=2, padx=(self.padding, 5), pady=self.padding, sticky="ew")
        ctk.CTkButton(
            frame, text="瞄准", command=self.action_aim_target,
            height=self.button_height, font=self.font_main, corner_radius=self.corner_radius
        ).grid(row=4, column=2, columnspan=2, padx=(self.padding, 5), pady=self.padding, sticky="ew")

    def setup_direction_control_ui(self, parent_container, start_row):
        """添加更紧凑的方向控制按钮界面"""
        # # 创建标题标签
        # ctk.CTkLabel(
        #     parent_container, 
        #     text="方向控制", 
        #     font=self.font_title, 
        #     anchor="w"
        # ).grid(row=start_row, column=0, columnspan=7, sticky="w", pady=(15, 5), padx=self.padding)
        
        # 创建主控制框架
        control_frame = ctk.CTkFrame(parent_container, fg_color="transparent")
        control_frame.grid(row=start_row, column=0, columnspan=7, sticky="ew", padx=self.padding, pady=(0, 5))
        
        # 将控制框架分为左右两部分
        control_frame.grid_columnconfigure(0, weight=1)  # 左侧 - 相机+航向控制
        control_frame.grid_columnconfigure(1, weight=1)  # 右侧 - 移动控制
        
        # ===== 左侧：相机+航向控制 =====
        cam_heading_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        cam_heading_frame.grid(row=0, column=0, sticky="nsew", padx=0)
        cam_heading_frame.grid_columnconfigure((0, 1), weight=1)
        
        # --- 左上：相机控制 ---
        cam_control_frame = ctk.CTkFrame(cam_heading_frame, fg_color=("gray90", "gray20"))
        cam_control_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 相机控制标题和步长
        ctk.CTkLabel(
            cam_control_frame, 
            text="相机俯仰控制", 
            font=self.font_small, 
            anchor="center"
        ).pack(pady=(5, 2))
        
        step_frame = ctk.CTkFrame(cam_control_frame, fg_color="transparent")
        step_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            step_frame, 
            text="步长:", 
            font=("PingFangSC-Regular", 12)
        ).pack(side="left", padx=(45, 5))
        
        self.camera_step_entry = ctk.CTkEntry(
            step_frame, 
            width=40, 
            height=25,
            font=("PingFangSC-Regular", 12), 
            corner_radius=self.corner_radius
        )
        self.camera_step_entry.pack(side="left")
        self.camera_step_entry.insert(0, "5")
        
        ctk.CTkLabel(step_frame, text="°", font=("PingFangSC-Regular", 12)).pack(side="left")
        
        # 相机控制按钮
        buttons_frame = ctk.CTkFrame(cam_control_frame, fg_color="transparent")
        buttons_frame.pack(fill="both", expand=True, pady=3)
        
        # 上按钮
        ctk.CTkButton(
            buttons_frame, 
            text="↑", 
            command=self.action_camera_pitch_up,
            width=45, 
            height=30, 
            font=(self.font_main[0], 18), 
            corner_radius=self.corner_radius
        ).grid(row=0, column=0, pady=(0, 5), padx=(60, 0))
        
        # 下按钮
        ctk.CTkButton(
            buttons_frame, 
            text="↓", 
            command=self.action_camera_pitch_down,
            width=45, 
            height=30, 
            font=(self.font_main[0], 18), 
            corner_radius=self.corner_radius
        ).grid(row=1, column=0, pady=(0, 25), padx=(60, 0))
        
        # --- 右上：航向控制 ---
        heading_control_frame = ctk.CTkFrame(cam_heading_frame, fg_color=("gray90", "gray20"))
        heading_control_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # 航向控制标题和步长
        ctk.CTkLabel(
            heading_control_frame, 
            text="航向控制", 
            font=self.font_small, 
            anchor="center"
        ).pack(pady=(5, 2))
        
        step_frame = ctk.CTkFrame(heading_control_frame, fg_color="transparent")
        step_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            step_frame, 
            text="步长:", 
            font=("PingFangSC-Regular", 12)
        ).pack(side="left", padx=(50, 5))
        
        self.heading_step_entry = ctk.CTkEntry(
            step_frame, 
            width=40,
            height=25,
            font=("PingFangSC-Regular", 12), 
            corner_radius=self.corner_radius
        )
        self.heading_step_entry.pack(side="left")
        self.heading_step_entry.insert(0, "5")
        
        ctk.CTkLabel(step_frame, text="°", font=("PingFangSC-Regular", 12)).pack(side="left")
        
        # 航向控制按钮
        buttons_frame = ctk.CTkFrame(heading_control_frame, fg_color="transparent")
        buttons_frame.pack(fill="both", expand=True, pady=3)
        
        # 左按钮
        ctk.CTkButton(
            buttons_frame, 
            text="←", 
            command=self.action_heading_left,
            width=45, 
            height=30, 
            font=(self.font_main[0], 18), 
            corner_radius=self.corner_radius
        ).grid(row=0, column=0, padx=(35, 5))
        
        # 右按钮
        ctk.CTkButton(
            buttons_frame, 
            text="→", 
            command=self.action_heading_right,
            width=45, 
            height=30, 
            font=(self.font_main[0], 18), 
            corner_radius=self.corner_radius
        ).grid(row=0, column=1)
        
        # ===== 右侧：移动控制 =====
        movement_frame = ctk.CTkFrame(control_frame, fg_color=("gray90", "gray20"))
        movement_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # 移动控制标题和步长
        ctk.CTkLabel(
            movement_frame, 
            text="无人机移动控制", 
            font=self.font_small, 
            anchor="center"
        ).pack(pady=(5, 2))
        
        step_frame = ctk.CTkFrame(movement_frame, fg_color="transparent")
        step_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            step_frame, 
            text="步长:", 
            font=("PingFangSC-Regular", 12)
        ).pack(side="left", padx=(5, 2))
        
        self.movement_step_entry = ctk.CTkEntry(
            step_frame, 
            width=40,
            height=25,
            font=("PingFangSC-Regular", 12), 
            corner_radius=self.corner_radius
        )
        self.movement_step_entry.pack(side="left")
        self.movement_step_entry.insert(0, "10")
        
        ctk.CTkLabel(step_frame, text="cm", font=("PingFangSC-Regular", 12)).pack(side="left")
        
        # 移动控制按钮
        movement_buttons_frame = ctk.CTkFrame(movement_frame, fg_color="transparent")
        movement_buttons_frame.pack(fill="both", expand=True, pady=(3, 5))
        movement_buttons_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        button_size = 35
        button_font = (self.font_small[0], 14)
        
        # 布局六个移动按钮
        # 前后上下按钮
        ctk.CTkButton(
            movement_buttons_frame, 
            text="前", 
            command=self.action_move_forward,
            width=button_size, 
            height=button_size, 
            font=button_font, 
            corner_radius=self.corner_radius
        ).grid(row=0, column=1, padx=2, pady=2)
        
        ctk.CTkButton(
            movement_buttons_frame, 
            text="后", 
            command=self.action_move_backward,
            width=button_size, 
            height=button_size, 
            font=button_font, 
            corner_radius=self.corner_radius
        ).grid(row=1, column=1, padx=2, pady=2)
        
        ctk.CTkButton(
            movement_buttons_frame, 
            text="上", 
            command=self.action_move_up,
            width=button_size, 
            height=button_size, 
            font=button_font, 
            corner_radius=self.corner_radius
        ).grid(row=0, column=3, padx=2, pady=2)
        
        ctk.CTkButton(
            movement_buttons_frame, 
            text="下", 
            command=self.action_move_down,
            width=button_size, 
            height=button_size, 
            font=button_font, 
            corner_radius=self.corner_radius
        ).grid(row=1, column=3, padx=2, pady=2)
        
        # 左右按钮
        ctk.CTkButton(
            movement_buttons_frame, 
            text="左", 
            command=self.action_move_left,
            width=button_size, 
            height=button_size, 
            font=button_font, 
            corner_radius=self.corner_radius
        ).grid(row=1, column=0, padx=2, pady=2)
        
        ctk.CTkButton(
            movement_buttons_frame, 
            text="右", 
            command=self.action_move_right,
            width=button_size, 
            height=button_size, 
            font=button_font, 
            corner_radius=self.corner_radius
        ).grid(row=1, column=2, padx=2, pady=2)

    ## --- 正方形飞行 UI ---
    def setup_square_flight_ui(self, parent_container):
        frame = self._create_section_frame(parent_container, "自动飞行: 正方形", 2)
        frame.grid_columnconfigure(3, weight=1) # Button expands

        ctk.CTkLabel(frame, text="边长:", font=self.font_main).grid(row=0, column=0, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.side_length_entry = ctk.CTkEntry(frame, width=80, font=self.font_main, corner_radius=self.corner_radius); self.side_length_entry.insert(0, "200")
        self.side_length_entry.grid(row=0, column=1, padx=5, pady=self.padding)

        # Radio buttons in their own sub-frame for better grouping
        radio_frame = ctk.CTkFrame(frame, fg_color="transparent")
        radio_frame.grid(row=0, column=2, padx=self.padding, pady=self.padding/2, sticky="ew")

        self.unit_var = tk.StringVar(value="distance")
        ctk.CTkRadioButton(radio_frame, text="时间 (s)", variable=self.unit_var, value="time", font=self.font_main, corner_radius=self.corner_radius).pack(side="left", padx=(0,10))
        ctk.CTkRadioButton(radio_frame, text="距离 (cm)", variable=self.unit_var, value="distance", font=self.font_main, corner_radius=self.corner_radius).pack(side="left")

        ctk.CTkButton(frame, text="飞行正方形路径", command=self.action_square_flight, height=self.button_height, font=self.font_main, corner_radius=self.corner_radius).grid(row=0, column=3, padx=(0, self.padding), pady=self.padding, sticky="ew")

    ## --- 激光与视频流 UI ---
    def setup_laser_video_ui(self, parent_container):
        frame = self._create_section_frame(parent_container, "功能控制", 3)
        frame.grid_columnconfigure(1, weight=1) # Stream button expands

        self.laser_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame, text="发射激光", variable=self.laser_var, command=self.action_toggle_laser,
            onvalue=True, offvalue=False, font=self.font_main, corner_radius=self.corner_radius,
            border_width=2
        ).grid(row=0, column=0, padx=self.padding, pady=self.padding)

        ctk.CTkButton(
            frame, text="开启视频流", command=self.action_capture_image_stream,
            height=self.button_height, font=self.font_main, corner_radius=self.corner_radius
        ).grid(row=0, column=1, padx=(0, self.padding), pady=self.padding, sticky="ew")
    
    # --- 飞行路径绘制相关方法 ---
    def update_flight_path(self, x, y, z):
        """更新飞行路径数据并绘制"""
        if (not hasattr(self, 'main_interface_created') or not self.main_interface_created or 
            self.cleanup_in_progress or not self.gui_active):
            return
            
        try:
            # Check if canvas still exists
            if not hasattr(self, 'canvas') or self.canvas is None:
                return
                
            # Add new path point
            self.flight_path_data['x'].append(x)
            self.flight_path_data['y'].append(y)
            self.flight_path_data['z'].append(z)
            self.flight_path_data['timestamps'].append(time.time())
            
            # Update plot
            self.path_line.set_data(self.flight_path_data['x'], self.flight_path_data['y'])
            self.current_pos.set_data([x], [y])
            
            # Dynamic view adjustment
            if len(self.flight_path_data['x']) > 1:
                x_min = min(self.flight_path_data['x']) - 50
                x_max = max(self.flight_path_data['x']) + 50
                y_min = min(self.flight_path_data['y']) - 50
                y_max = max(self.flight_path_data['y']) + 50
                
                # Ensure minimum range
                x_range = x_max - x_min
                y_range = y_max - y_min
                if x_range < 200:
                    center_x = (x_min + x_max) / 2
                    x_min, x_max = center_x - 100, center_x + 100
                if y_range < 200:
                    center_y = (y_min + y_max) / 2
                    y_min, y_max = center_y - 100, center_y + 100
                    
                self.ax.set_xlim([x_min, x_max])
                self.ax.set_ylim([y_min, y_max])
            
            # Refresh canvas
            self.canvas.draw_idle()
            
        except Exception as e:
            if not self.cleanup_in_progress:
                print(f"更新飞行路径时出错: {e}")
    
    def reset_path_view(self):
        """重置飞行路径视图"""
        if not hasattr(self, 'main_interface_created') or not self.main_interface_created:
            return
            
        if len(self.flight_path_data['x']) > 0:
            x_min = min(self.flight_path_data['x']) - 50
            x_max = max(self.flight_path_data['x']) + 50
            y_min = min(self.flight_path_data['y']) - 50
            y_max = max(self.flight_path_data['y']) + 50
            
            # 确保视图有最小范围和适当的纵横比
            x_range = max(200, x_max - x_min)
            y_range = max(200, y_max - y_min)
            
            # 保持大致相同的缩放级别
            center_x = (x_min + x_max) / 2
            center_y = (y_min + y_max) / 2
            max_range = max(x_range, y_range)
            
            self.ax.set_xlim([center_x - max_range/2, center_x + max_range/2])
            self.ax.set_ylim([center_y - max_range/2, center_y + max_range/2])
        else:
            # 默认视图范围
            self.ax.set_xlim([-300, 300])
            self.ax.set_ylim([-300, 300])
        
        self.canvas.draw()
    
    def clear_flight_path(self):
        """清除飞行路径数据"""
        if not hasattr(self, 'main_interface_created') or not self.main_interface_created:
            return
            
        self.flight_path_data = {
            'x': [],
            'y': [],
            'z': [],
            'timestamps': []
        }
        self.path_line.set_data([], [])
        self.current_pos.set_data([], [])
        
        # 恢复默认视图
        self.ax.set_xlim([-300, 300])
        self.ax.set_ylim([-300, 300])
        
        self.canvas.draw()
    
    def save_flight_path_image(self):
        """保存当前飞行路径图像"""
        if not hasattr(self, 'main_interface_created') or not self.main_interface_created:
            return
            
        import datetime
        filename = f"flight_path_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.fig.savefig(filename, dpi=150, bbox_inches='tight')
        messagebox.showinfo("保存成功", f"飞行路径图像已保存为：\n{filename}")
    
    # --- 视频流处理相关方法 ---
    def start_video_stream(self):
        """启动视频流处理"""
        if not hasattr(self, 'main_interface_created') or not self.main_interface_created or self.cleanup_in_progress:
            return
                
        if not self.video_stream_active:
            self.video_stream_active = True
            if hasattr(self, 'video_status_label') and self.video_status_label.winfo_exists():
                self.video_status_label.configure(text="视频流已开启")
            
            # 创建动画
            def update_frame(frame_num):
                if not self.gui_active or not self.video_stream_active or self.cleanup_in_progress:
                    return [self.video_img]
                    
                try:
                    if not self.frame_raw_queue.empty():
                        frame = self.frame_raw_queue.get_nowait()
                        if frame is not None:
                            # 调整大小并转换颜色空间
                            frame = cv2.resize(frame, (self.image_width, self.image_height))
                            # cv2.imwrite("temp_frame.jpg", frame)  # 保存临时帧用于调试
                            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            self.video_img.set_data(frame)
                    return [self.video_img]
                except Exception as e:
                    if not self.cleanup_in_progress:
                        print(f"视频帧更新错误: {e}")
                    return [self.video_img]
            
            try:
                self.video_animation = FuncAnimation(
                    self.video_fig, 
                    update_frame, 
                    interval=100,
                    blit=True,
                    cache_frame_data=False
                )
                self.video_canvas.draw()
            except Exception as e:
                print(f"创建视频动画时出错: {e}")
                self.video_stream_active = False
    
    def stop_video_stream(self):
        """停止视频流处理"""
        self.video_stream_active = False
        
        if hasattr(self, 'video_animation') and self.video_animation is not None:
            try:
                self.video_animation.event_source.stop()
                self.video_animation = None
            except:
                pass
        
        try:
            if hasattr(self, 'video_status_label') and self.video_status_label.winfo_exists():
                self.video_status_label.configure(text="视频流已关闭")
            
            if hasattr(self, 'video_img') and hasattr(self, 'video_canvas'):
                black_frame = np.zeros((self.image_height, self.image_width, 3), dtype=np.uint8)
                self.video_img.set_data(black_frame)
                self.video_canvas.draw()
        except:
            pass

    # --- 动作方法 ---
    def _run_drone_action_in_thread(self, action_func, *args, **kwargs):
        thread = threading.Thread(target=action_func, args=args, kwargs=kwargs, daemon=True)
        thread.start()

    def action_connect_drone(self):
        ip = self.ip_entry.get().strip()
        if not ip: ip = None
        self.status_label.configure(text="状态: 正在连接...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.connect, ip)

    def action_start_services(self):
        self.main_status_label.configure(text="状态: 正在准备服务...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.start_background_services)

    def action_takeoff(self):
        self.main_status_label.configure(text="状态: 正在起飞...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.takeoff)

    def action_land(self):
        self.main_status_label.configure(text="状态: 正在降落...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.land)

    def action_move_to_target(self):
        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())
            z = float(self.z_entry.get())
            self.main_status_label.configure(text=f"状态: 正在移动到 ({x},{y},{z})...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.move_to_global_target, x, y, z)
        except ValueError:
            messagebox.showerror("输入错误", "坐标必须为有效数字")

    def action_rotation(self):
        try:
            rotate_degrees = int(self.rotation_entry.get())
            self.main_status_label.configure(text=f"状态: 正在旋转 {rotate_degrees}°...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.set_rotation, rotate_degrees)
        except ValueError:
            messagebox.showerror("输入错误", "旋转角度必须为有效整数")

    def action_set_heading(self):
        try:
            heading = int(self.heading_entry.get())
            self.main_status_label.configure(text=f"状态: 正在设置航向到 {heading}°...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.set_heading, heading)
        except ValueError:
            messagebox.showerror("输入错误", "航向角度必须为有效整数")

    ## --- 手动控制Action ---    
    # 相机俯仰控制动作
    def action_camera_pitch_up(self):
        try:
            step = int(self.camera_step_entry.get())
            self.main_status_label.configure(text=f"状态: 相机向上调整 {step}°...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.set_camera_relative_pitch, step)  # 正值表示向上
        except ValueError:
            messagebox.showerror("输入错误", "相机步长必须为有效整数")
    
    def action_camera_pitch_down(self):
        try:
            step = int(self.camera_step_entry.get())
            self.main_status_label.configure(text=f"状态: 相机向下调整 {step}°...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.set_camera_relative_pitch, -step)  # 负值表示向下
        except ValueError:
            messagebox.showerror("输入错误", "相机步长必须为有效整数")
    
    # 航向控制动作
    def action_heading_left(self):
        try:
            step = int(self.heading_step_entry.get())
            self.main_status_label.configure(text=f"状态: 航向左转 {step}°...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.set_rotation, -step)  # 负值表示左转
        except ValueError:
            messagebox.showerror("输入错误", "航向步长必须为有效整数")
    
    def action_heading_right(self):
        try:
            step = int(self.heading_step_entry.get())
            self.main_status_label.configure(text=f"状态: 航向右转 {step}°...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.set_rotation, step)  # 正值表示右转
        except ValueError:
            messagebox.showerror("输入错误", "航向步长必须为有效整数")
    
    # 无人机移动控制动作 - 使用本地坐标系
    def action_move_forward(self):
        try:
            step = int(self.movement_step_entry.get())
            self.main_status_label.configure(text=f"状态: 向前移动 {step}cm...", text_color=self._get_status_color("orange"))
            # 在本地坐标系中，前进是y轴正方向
            self._run_drone_action_in_thread(self.drone.move_to_local_target, 0, step, 0)
        except ValueError:
            messagebox.showerror("输入错误", "移动步长必须为有效整数")
    
    def action_move_backward(self):
        try:
            step = int(self.movement_step_entry.get())
            self.main_status_label.configure(text=f"状态: 向后移动 {step}cm...", text_color=self._get_status_color("orange"))
            # 在本地坐标系中，后退是y轴负方向
            self._run_drone_action_in_thread(self.drone.move_to_local_target, 0, -step, 0)
        except ValueError:
            messagebox.showerror("输入错误", "移动步长必须为有效整数")
    
    def action_move_left(self):
        try:
            step = int(self.movement_step_entry.get())
            self.main_status_label.configure(text=f"状态: 向左移动 {step}cm...", text_color=self._get_status_color("orange"))
            # 在本地坐标系中，左移是x轴负方向
            self._run_drone_action_in_thread(self.drone.move_to_local_target, -step, 0, 0)
        except ValueError:
            messagebox.showerror("输入错误", "移动步长必须为有效整数")
    
    def action_move_right(self):
        try:
            step = int(self.movement_step_entry.get())
            self.main_status_label.configure(text=f"状态: 向右移动 {step}cm...", text_color=self._get_status_color("orange"))
            # 在本地坐标系中，右移是x轴正方向
            self._run_drone_action_in_thread(self.drone.move_to_local_target, step, 0, 0)
        except ValueError:
            messagebox.showerror("输入错误", "移动步长必须为有效整数")
    
    def action_move_up(self):
        try:
            step = int(self.movement_step_entry.get())
            self.main_status_label.configure(text=f"状态: 向上移动 {step}cm...", text_color=self._get_status_color("orange"))
            # 上升是z轴正方向
            self._run_drone_action_in_thread(self.drone.move_to_local_target, 0, 0, step)
        except ValueError:
            messagebox.showerror("输入错误", "移动步长必须为有效整数")
    
    def action_move_down(self):
        try:
            step = int(self.movement_step_entry.get())
            self.main_status_label.configure(text=f"状态: 向下移动 {step}cm...", text_color=self._get_status_color("orange"))
            # 下降是z轴负方向
            self._run_drone_action_in_thread(self.drone.move_to_local_target, 0, 0, -step)
        except ValueError:
            messagebox.showerror("输入错误", "移动步长必须为有效整数")

    ## --- 目标检测与瞄准 ---
    def action_detect(self):
        pass

    def action_aim_target(self):
        pass

    ## --- 自动飞行相关方法 ---
    def action_square_flight(self):
        try:
            side = float(self.side_length_entry.get())
            unit = self.unit_var.get()
            self.main_status_label.configure(text=f"状态: 正在开始正方形飞行 (边长: {side} {unit})...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.square_flight, side, unit, step_callback=self.drone.set_rotation)
        except ValueError:
            messagebox.showerror("输入错误", "边长必须为有效数字")

    def action_toggle_laser(self):
        enable = self.laser_var.get()
        action_text = "启用" if enable else "禁用"
        self.main_status_label.configure(text=f"状态: {action_text} 激光...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.toggle_laser, enable)

    def action_capture_image_stream(self):
        if not self.video_stream_active:
            self.main_status_label.configure(text="状态: 正在开启视频流...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.capture_image_stream, self.frame_raw_queue)
            self.start_video_stream()
        # else:
        #     self.main_status_label.configure(text="状态: 正在关闭视频流...", text_color=self._get_status_color("orange"))
        #     self._run_drone_action_in_thread(self.drone.stop_image_stream)
        #     self.stop_video_stream()

    # --- UI 更新和关闭 ---
    def _get_status_color(self, color_name: str):
        """返回主题适配的颜色"""
        is_dark_mode = ctk.get_appearance_mode() == "Dark"
        colors = {
            "green": ("#2ECC71", "#27AE60") if not is_dark_mode else ("#58D68D", "#2ECC71"),
            "orange": ("#F39C12", "#D35400") if not is_dark_mode else ("#F5B041", "#F39C12"),
            "red": ("#E74C3C", "#C0392B") if not is_dark_mode else ("#EC7063", "#E74C3C"),
            "grey": ("#95A5A6", "#7F8C8D") if not is_dark_mode else ("#BDC3C7", "#95A5A6"),
            "blue_text": ("#3498DB", "#5DADE2")
        }
        return colors.get(color_name.lower(), ("#000000", "#FFFFFF"))[1 if is_dark_mode else 0]

    def update_status_display_from_callback(self, drone_status: dict):
        if not self.gui_active or self.cleanup_in_progress: 
            return
        # Use tracked callback
        self._schedule_callback(0, self._do_update_ui, drone_status)


    def _do_update_ui(self, drone_status: dict):
        if not self.gui_active or self.cleanup_in_progress: 
            return

        try:
            msg = drone_status.get("message", "Unknown Status")
            self.connected = drone_status.get("connected", False)
            current_status_text = f"状态: {msg}"

            # Update connection interface status (if still visible)
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                if self.connected:
                    self.status_label.configure(text=current_status_text, text_color=self._get_status_color("green"))
                    self.connect_button.configure(text="已连接", state="disabled", fg_color=self._get_status_color("grey"))
                    
                    # Switch to main interface if first connection and not already created
                    if not hasattr(self, 'main_interface_shown') or not self.main_interface_shown:
                        self.main_interface_shown = True
                        self._schedule_callback(500, self.show_main_interface)
                else:
                    if "connecting" in msg.lower():
                        self.status_label.configure(text=current_status_text, text_color=self._get_status_color("orange"))
                    elif "failed" in msg.lower() or "error" in msg.lower() or "disconnected" in msg.lower():
                        self.status_label.configure(text=current_status_text, text_color=self._get_status_color("red"))
                    else:
                        self.status_label.configure(text=current_status_text, text_color=self._get_status_color("grey"))

            # Update other status info safely
            battery = drone_status.get("battery_level", "Unknown")
            battery_text = f"电池: {battery}%" if isinstance(battery, (int, float)) else f"电池: {battery}"
            
            loc = drone_status.get("location", ["N/A", "N/A"])
            height = drone_status.get("height", "N/A")
            pos_str = f"位置: X:{loc[0]} Y:{loc[1]} Z:{height}"
            
            heading = drone_status.get("heading", "N/A")
            heading_text = f"航向: {heading:.1f}°" if isinstance(heading, float) else f"航向: {heading}"

            # Update connection interface labels if they exist
            if hasattr(self, 'battery_label') and self.battery_label.winfo_exists():
                self.battery_label.configure(text=battery_text, text_color=self._get_status_color("blue_text"))
            if hasattr(self, 'position_label') and self.position_label.winfo_exists():
                self.position_label.configure(text=pos_str, text_color=self._get_status_color("blue_text"))
            if hasattr(self, 'heading_label') and self.heading_label.winfo_exists():
                self.heading_label.configure(text=heading_text, text_color=self._get_status_color("blue_text"))
            
            # Update main interface labels if they exist
            if hasattr(self, 'main_interface_created') and self.main_interface_created:
                if hasattr(self, 'main_status_label') and self.main_status_label.winfo_exists():
                    self.main_status_label.configure(text=current_status_text, text_color=self._get_status_color("green" if self.connected else "grey"))
                if hasattr(self, 'main_battery_label') and self.main_battery_label.winfo_exists():
                    self.main_battery_label.configure(text=battery_text, text_color=self._get_status_color("blue_text"))
                if hasattr(self, 'main_position_label') and self.main_position_label.winfo_exists():
                    self.main_position_label.configure(text=pos_str, text_color=self._get_status_color("blue_text"))
                if hasattr(self, 'main_heading_label') and self.main_heading_label.winfo_exists():
                    self.main_heading_label.configure(text=heading_text, text_color=self._get_status_color("blue_text"))
                
                # Update flight path if we have valid position data
                if loc[0] != "N/A" and loc[1] != "N/A" and height != "N/A":
                    try:
                        x, y, z = float(loc[0]), float(loc[1]), float(height)
                        self.update_flight_path(x, y, z)
                    except (ValueError, TypeError):
                        pass

        except Exception as e:
            print(f"状态更新时发生错误: {e}")

    def _schedule_callback(self, delay, callback, *args):
        """Helper method to track scheduled callbacks for proper cleanup"""
        if self.cleanup_in_progress or not self.gui_active:
            return None
        try:
            callback_id = self.root.after(delay, callback, *args)
            self.scheduled_callbacks.append(callback_id)
            return callback_id
        except:
            return None

    def _cancel_all_callbacks(self):
        """Cancel all tracked callbacks safely"""
        for callback_id in self.scheduled_callbacks:
            try:
                if callback_id:
                    self.root.after_cancel(callback_id)
            except:
                pass
        self.scheduled_callbacks.clear()


    def on_closing_window(self):
        if messagebox.askokcancel("退出确认", "您确定要退出 Hula Drone 控制界面吗？\n无人机将尝试安全着陆并保存数据。"):
            print("开始关闭应用程序...")
            
            # Set cleanup flag immediately
            self.cleanup_in_progress = True
            self.gui_active = False
            self.video_stream_active = False
            
            # Stop video stream first
            self.stop_video_stream()
            
            # Cancel all scheduled callbacks
            self._cancel_all_callbacks()
            
            # Update status safely
            try:
                if hasattr(self, 'main_interface_created') and self.main_interface_created:
                    if hasattr(self, 'main_status_label') and self.main_status_label.winfo_exists():
                        self.main_status_label.configure(text="状态: 正在退出，请稍候...", text_color=self._get_status_color("orange"))
                else:
                    if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                        self.status_label.configure(text="状态: 正在退出，请稍候...", text_color=self._get_status_color("orange"))
            except:
                pass

            # Force update the display
            try:
                self.root.update_idletasks()
            except:
                pass
            
            # Unregister drone callback safely
            try:
                if hasattr(self.drone, 'unregister_status_callback'):
                    self.drone.unregister_status_callback(self.update_status_display_from_callback)
            except:
                pass

            # Start drone shutdown in background
            exit_thread = threading.Thread(target=self.drone.graceful_exit, daemon=True)
            exit_thread.start()
            
            # Schedule window destruction with a delay
            self.root.after(1000, self._destroy_root_safely)

    def _destroy_root_safely(self):
        """Safely destroy the root window and clean up resources"""
        if not self.cleanup_in_progress:
            self.cleanup_in_progress = True
        
        print("正在安全关闭图形界面...")
        
        try:
            # Cancel any remaining callbacks
            self._cancel_all_callbacks()
            
            # Stop matplotlib animations
            if hasattr(self, 'video_animation') and self.video_animation is not None:
                self.video_animation.event_source.stop()
                self.video_animation = None
                
            # Close matplotlib figures
            if hasattr(self, 'video_fig'):
                plt.close(self.video_fig)
            if hasattr(self, 'fig'):
                plt.close(self.fig)
                
            # Clear references to prevent callback issues
            if hasattr(self, 'video_canvas'):
                self.video_canvas = None
            if hasattr(self, 'canvas'):
                self.canvas = None
                
            # Destroy the root window
            if self.root and self.root.winfo_exists():
                self.root.quit()       # Exit the mainloop
                self.root.destroy()    # Destroy the window
                
        except Exception as e: 
            print(f"关闭图形界面时发生错误: {e}")
            # Force exit if normal cleanup fails
            import sys
            sys.exit(0)
        finally:
            print("图形界面已安全关闭。")
    
    def run_gui(self):
        self.gui_active = True
        self.root.mainloop()

# Main program entry point
if __name__ == "__main__":
    gui_root = ctk.CTk()
    app = HulaDroneGUI_CTk_Enhanced(gui_root)
    try:
        app.run_gui()
    except KeyboardInterrupt:
        print("\n检测到Ctrl+C，正在关闭应用程序...")
        if hasattr(app, 'gui_active') and app.gui_active: 
            app.on_closing_window()
    except Exception as e:
        print(f"在GUI主循环中发生未处理的异常: {e}")
    finally:
        print("应用程序主线程已完成。")
