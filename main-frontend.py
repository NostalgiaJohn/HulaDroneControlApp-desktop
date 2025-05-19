# main_customtkinter_enhanced.py (HulaDroneGUI with CustomTkinter - Enhanced)
import customtkinter as ctk
import tkinter as tk # For StringVar, BooleanVar, and dialogs like messagebox
from tkinter import messagebox # Retaining for dialogs
# from tkinter import filedialog # Uncomment if used
# import os # Only keep if needed

from HulaDrone import HulaDrone # Assuming HulaDrone.py is in the same directory or accessible
import threading

class HulaDroneGUI_CTk_Enhanced:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Hula 无人机图形化控制界面")
        self.root.geometry("700x780") # Adjusted initial size
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing_window)

        # --- Appearance and Theme ---
        ctk.set_appearance_mode("Dark")  # Modes: "System" (default), "Dark", "Light"
        ctk.set_default_color_theme("dark-blue")  # Themes: "blue", "green", "dark-blue"

        # --- Styling Defaults ---
        ctk.FontManager().load_font("./fonts/PingFangSC-Light.otf")
        ctk.FontManager().load_font("./fonts/PingFangSC-Medium.otf")
        ctk.FontManager().load_font("./fonts/PingFangSC-Regular.otf")
        ctk.FontManager().load_font("./fonts/PingFangSC-Semibold.otf")
        ctk.FontManager().load_font("./fonts/PingFangSC-Thin.otf")
        ctk.FontManager().load_font("./fonts/PingFangSC-Ultralight.otf")
        self.font_main = ("PingFangSC-Regular", 17) # A more modern font, ensure it's available or use default
        self.font_small = ("PingFangSC-Medium", 14)
        self.font_title = ("PingFangSC-Semibold", 22, "bold")
        self.corner_radius = 8
        self.padding = 10
        self.button_height = 35

        self.drone = HulaDrone()
        self.drone.register_status_callback(self.update_status_display_from_callback)

        self.default_ip = ""
        self.gui_active = True

        # --- Main container frame ---
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=self.padding, pady=self.padding)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=1) # Allow flight control to expand a bit
        main_container.grid_rowconfigure(2, weight=1)
        main_container.grid_rowconfigure(3, weight=1)


        self.setup_connection_info_ui(main_container)
        self.setup_flight_control_ui(main_container)
        self.setup_square_flight_ui(main_container)
        self.setup_laser_video_ui(main_container)

    def _create_section_frame(self, parent, title_text, row):
        """Helper to create a titled section frame."""
        section_title = ctk.CTkLabel(parent, text=title_text, font=self.font_title, anchor="w")
        section_title.grid(row=row*2, column=0, padx=self.padding, pady=(self.padding, 5), sticky="ew")

        frame = ctk.CTkFrame(parent, corner_radius=self.corner_radius)
        frame.grid(row=row*2 + 1, column=0, padx=0, pady=(0, self.padding), sticky="ew")
        return frame

    def setup_connection_info_ui(self, parent_container):
        frame = self._create_section_frame(parent_container, "连接与状态", 0)
        frame.grid_columnconfigure(1, weight=1) # IP entry expands

        ctk.CTkLabel(frame, text="IP 地址:", font=self.font_main).grid(row=0, column=0, padx=self.padding, pady=self.padding, sticky="e")
        self.ip_entry = ctk.CTkEntry(frame, placeholder_text="输入 IP 或留空", font=self.font_main, corner_radius=self.corner_radius)
        self.ip_entry.insert(0, self.default_ip)
        self.ip_entry.grid(row=0, column=1, padx=(0,self.padding), pady=self.padding, sticky="ew")

        self.connect_button = ctk.CTkButton(
            frame, text="连接", command=self.action_connect_drone,
            font=self.font_main, height=self.button_height, corner_radius=self.corner_radius
        )
        self.connect_button.grid(row=0, column=2, padx=(0, self.padding), pady=self.padding)

        # Status Area
        status_sub_frame = ctk.CTkFrame(frame, fg_color="transparent")
        status_sub_frame.grid(row=1, column=0, columnspan=3, padx=self.padding, pady=(0,self.padding), sticky="ew")
        status_sub_frame.grid_columnconfigure((0,1,2), weight=1)


        self.status_label = ctk.CTkLabel(status_sub_frame, text="状态: 等待连接", font=self.font_main, anchor="w")
        self.status_label.grid(row=0, column=0, columnspan=3, pady=(5,10), sticky="ew")

        self.battery_label = ctk.CTkLabel(status_sub_frame, text="电池: 未知", font=self.font_small, anchor="w")
        self.battery_label.grid(row=1, column=0, pady=2, sticky="w")

        self.position_label = ctk.CTkLabel(status_sub_frame, text="位置: 未知", font=self.font_small, anchor="w")
        self.position_label.grid(row=1, column=1, pady=2, sticky="w")

        self.heading_label = ctk.CTkLabel(status_sub_frame, text="航向: 未知", font=self.font_small, anchor="w")
        self.heading_label.grid(row=1, column=2, pady=2, sticky="w")


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
        ctk.CTkLabel(frame, text="旋转 (度):", font=self.font_main).grid(row=2, column=0, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.heading_entry = ctk.CTkEntry(frame, width=move_entry_width, font=self.font_main, corner_radius=self.corner_radius); self.heading_entry.insert(0, "0")
        self.heading_entry.grid(row=2, column=1, padx=5, pady=self.padding)
        ctk.CTkButton(frame, text="开始旋转", command=self.action_set_rotation, height=self.button_height, font=self.font_main, corner_radius=self.corner_radius).grid(row=2, column=2, columnspan=2, padx=(self.padding, 5), pady=self.padding, sticky="ew")

        # Row 3: Set Heading
        ctk.CTkLabel(frame, text="航向 (度):", font=self.font_main).grid(row=2, column=4, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.heading_entry = ctk.CTkEntry(frame, width=move_entry_width, font=self.font_main, corner_radius=self.corner_radius); self.heading_entry.insert(0, "0")
        self.heading_entry.grid(row=2, column=5, padx=5, pady=self.padding)
        ctk.CTkButton(
            frame, text="设置航向", command=self.action_set_heading,
            height=self.button_height, font=self.font_main, corner_radius=self.corner_radius
        ).grid(row=2, column=6, padx=(self.padding, 5), pady=self.padding, sticky="ew")


    def setup_square_flight_ui(self, parent_container):
        frame = self._create_section_frame(parent_container, "自动飞行: 正方形", 2)
        frame.grid_columnconfigure(3, weight=1) # Button expands

        ctk.CTkLabel(frame, text="边长:", font=self.font_main).grid(row=0, column=0, padx=(self.padding,0), pady=self.padding, sticky="e")
        self.side_length_entry = ctk.CTkEntry(frame, width=80, font=self.font_main, corner_radius=self.corner_radius); self.side_length_entry.insert(0, "50")
        self.side_length_entry.grid(row=0, column=1, padx=5, pady=self.padding)

        # Radio buttons in their own sub-frame for better grouping
        radio_frame = ctk.CTkFrame(frame, fg_color="transparent")
        radio_frame.grid(row=0, column=2, padx=self.padding, pady=self.padding/2, sticky="ew")

        self.unit_var = tk.StringVar(value="distance")
        ctk.CTkRadioButton(radio_frame, text="时间 (s)", variable=self.unit_var, value="time", font=self.font_main, corner_radius=self.corner_radius).pack(side="left", padx=(0,10))
        ctk.CTkRadioButton(radio_frame, text="距离 (cm)", variable=self.unit_var, value="distance", font=self.font_main, corner_radius=self.corner_radius).pack(side="left")

        ctk.CTkButton(frame, text="飞行正方形路径", command=self.action_square_flight, height=self.button_height, font=self.font_main, corner_radius=self.corner_radius).grid(row=0, column=3, padx=(0, self.padding), pady=self.padding, sticky="ew")


    def setup_laser_video_ui(self, parent_container):
        frame = self._create_section_frame(parent_container, "Accessories", 3)
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

    # --- Action Methods (Unchanged from previous CustomTkinter version) ---
    def _run_drone_action_in_thread(self, action_func, *args):
        thread = threading.Thread(target=action_func, args=args, daemon=True)
        thread.start()

    def action_connect_drone(self):
        ip = self.ip_entry.get().strip()
        if not ip: ip = None
        self.status_label.configure(text="状态: 正在连接...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.connect, ip)

    def action_start_services(self):
        self.status_label.configure(text="状态: 正在准备服务...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.start_background_services)

    def action_takeoff(self):
        self.status_label.configure(text="状态: 正在起飞...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.takeoff)

    def action_land(self):
        self.status_label.configure(text="状态: 正在降落...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.land)

    def action_move_to_target(self):
        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())
            z = float(self.z_entry.get())
            self.status_label.configure(text=f"状态: 正在移动到 ({x},{y},{z})...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.move_to_target, x, y, z)
        except ValueError:
            messagebox.showerror("输入错误", "坐标必须为有效数字")

    def action_set_rotation(self):
        try:
            heading = int(self.heading_entry.get())
            self.status_label.configure(text=f"状态: 正在旋转 {heading}°...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.set_rotation, heading)
        except ValueError:
            messagebox.showerror("输入错误", "旋转角度必须为有效整数")

    def action_set_heading(self):
        try:
            heading = int(self.heading_entry.get())
            self.status_label.configure(text=f"状态: 正在设置航向到 {heading}°...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.set_heading, heading)
        except ValueError:
            messagebox.showerror("输入错误", "航向角度必须为有效整数")

    def action_square_flight(self):
        try:
            side = float(self.side_length_entry.get())
            unit = self.unit_var.get()
            self.status_label.configure(text=f"状态: 正在开始正方形飞行 (边长: {side} {unit})...", text_color=self._get_status_color("orange"))
            self._run_drone_action_in_thread(self.drone.square_flight, side, unit)
        except ValueError:
            messagebox.showerror("输入错误", "边长必须为有效数字")

    def action_toggle_laser(self):
        enable = self.laser_var.get()
        action_text = "启用" if enable else "禁用"
        self.status_label.configure(text=f"状态: {action_text} 激光...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.toggle_laser, enable)

    def action_capture_image_stream(self):
        # This action might toggle, so the status message should reflect that possibility.
        # For now, a generic message. The backend should provide more specific status.
        self.status_label.configure(text="状态: 正在切换视频流...", text_color=self._get_status_color("orange"))
        self._run_drone_action_in_thread(self.drone.capture_image_stream)

    # --- UI Update and Closing (Adapted for better color use) ---
    def _get_status_color(self, color_name: str):
        """Returns theme-appropriate color"""
        # Standard CustomTkinter colors often adapt automatically.
        # For explicit control:
        is_dark_mode = ctk.get_appearance_mode() == "Dark"
        colors = {
            "green": ("#2ECC71", "#27AE60") if not is_dark_mode else ("#58D68D", "#2ECC71"),
            "orange": ("#F39C12", "#D35400") if not is_dark_mode else ("#F5B041", "#F39C12"),
            "red": ("#E74C3C", "#C0392B") if not is_dark_mode else ("#EC7063", "#E74C3C"),
            "grey": ("#95A5A6", "#7F8C8D") if not is_dark_mode else ("#BDC3C7", "#95A5A6"),
            "blue_text": ("#3498DB", "#5DADE2") # General info text
        }
        return colors.get(color_name.lower(), ("#000000", "#FFFFFF"))[1 if is_dark_mode else 0]

    def update_status_display_from_callback(self, drone_status: dict):
        if not self.gui_active: return
        self.root.after(0, self._do_update_ui, drone_status)

    def _do_update_ui(self, drone_status: dict):
        if not self.gui_active: return

        msg = drone_status.get("message", "Unknown Status")
        connected = drone_status.get("connected", False)
        current_status_text = f"状态: {msg}"

        if connected:
            self.status_label.configure(text=current_status_text, text_color=self._get_status_color("green"))
            self.connect_button.configure(text="已连接", state="disabled", fg_color=self._get_status_color("grey"))
        else:
            if "connecting" in msg.lower() :
                 self.status_label.configure(text=current_status_text, text_color=self._get_status_color("orange"))
                 self.connect_button.configure(text="连接", state="normal") # Re-enable if failed/disconnected
            elif "failed" in msg.lower() or "error" in msg.lower() or "disconnected" in msg.lower():
                 self.status_label.configure(text=current_status_text, text_color=self._get_status_color("red"))
                 self.connect_button.configure(text="连接", state="normal")
            else: # e.g., "Awaiting Connection", "Exited Safely"
                 self.status_label.configure(text=current_status_text, text_color=self._get_status_color("grey"))
                 self.connect_button.configure(text="连接", state="normal")


        battery = drone_status.get("battery_level", "Unknown")
        self.battery_label.configure(text=f"电池: {battery}%" if isinstance(battery, (int, float)) else f"电池: {battery}", text_color=self._get_status_color("blue_text"))

        loc = drone_status.get("location", ["N/A", "N/A"])
        height = drone_status.get("height", "N/A")
        pos_str = f"X:{loc[0]} Y:{loc[1]} Z:{height}"
        self.position_label.configure(text=f"位置: {pos_str}", text_color=self._get_status_color("blue_text"))

        heading = drone_status.get("heading", "N/A")
        self.heading_label.configure(text=f"航向: {heading:.1f}°" if isinstance(heading, float) else f"航向: {heading}", text_color=self._get_status_color("blue_text"))

    def on_closing_window(self):
        if messagebox.askokcancel("退出确认", "您确定要退出 Hula Drone 控制界面吗？\n无人机将尝试安全着陆并保存数据。"):
            self.gui_active = False
            self.status_label.configure(text="状态: 正在退出，请稍候...", text_color=self._get_status_color("orange"))
            self.root.update_idletasks()

            exit_thread = threading.Thread(target=self.drone.graceful_exit, daemon=True)
            exit_thread.start()
            self.root.after(2000, self._destroy_root_safely)

    def _destroy_root_safely(self):
        try:
            if self.root: self.root.destroy()
        except tk.TclError: pass
        finally:
            self.root = None
            print("图形化界面已安全关闭。")

    def run_gui(self):
        self.root.mainloop()

# Main program entry point
if __name__ == "__main__":
    # Ensure HulaDrone class is defined or imported correctly
    # from HulaDrone import HulaDrone # Already imported at the top

    gui_root = ctk.CTk()
    app = HulaDroneGUI_CTk_Enhanced(gui_root)
    try:
        app.run_gui()
    except KeyboardInterrupt:
        print("\n检测到Ctrl+C，正在关闭应用程序...")
        if hasattr(app, 'gui_active') and app.gui_active : # Check if app object and gui_active exist
            app.on_closing_window()
    except Exception as e:
        print(f"在GUI主循环中发生未处理的异常: {e}")
    finally:
        print("应用程序主线程已完成。")