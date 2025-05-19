"""Drone position control using PID and threading for non-blocking operation.

This script controls a drone to reach a specified 3D target location using PID controllers
for each axis (x, y, z). The control loop runs in a separate thread to ensure non-blocking
execution, allowing dynamic updates to the target location via console input.
Thread-safe mechanisms prevent race conditions during target updates.
"""

import threading
import json
import time
import pyhula
import math
from dataclasses import dataclass
from datetime import datetime


class PidCalculator:
    """PID controller for computing control signals based on error.

    Attributes:
        kp (float): Proportional gain.
        ki (float): Integral gain.
        kd (float): Derivative gain.
        prev_error (float): Previous error for derivative calculation.
        integral (float): Accumulated integral term.
        integral_min (float): Minimum limit for integral term.
        integral_max (float): Maximum limit for integral term.
    """
    def __init__(self, kp=0.5, ki=0.0, kd=0.0, integral_min=-0, integral_max=0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_error = 0
        self.integral = 0
        self.integral_min = integral_min
        self.integral_max = integral_max

    def compute(self, error):
        """Compute PID control output for a given error.

        Args:
            error (float): Current error (difference between desired and actual value).

        Returns:
            float: Control signal computed as P + I + D terms.
        """
        # Accumulate error for integral term
        self.integral += error
        # Clamp integral to prevent windup
        self.integral = max(self.integral_min, min(self.integral, self.integral_max))
        # Calculate derivative term
        derivative = error - self.prev_error
        self.prev_error = error
        # Compute and return PID output
        return self.kp * error + self.ki * self.integral + self.kd * derivative
    
@dataclass
class Controller:
    """Manages drone position and heading control using PID controllers in a separate thread.

    Attributes:
        instance (pyhula.UserApi): API instance for drone communication.
        target_location (list): Desired [heading, x, y, z] (heading in degrees, x, y, z in cm).
        pid_x (PidCalculator): PID controller for x-axis.
        pid_y (PidCalculator): PID controller for y-axis.
        pid_z (PidCalculator): PID controller for z-axis.
        running (bool): Flag to control the PID loop.
        control_interval (float): Time between control iterations in seconds.
        _lock (threading.Lock): Lock for thread-safe access to target_location.
        _pause_event (threading.Event): Event to control pause/resume of the control loop.
    """
    instance: pyhula.UserApi
    heading_ini : int = 0
    target_location: list = None
    pid_x: PidCalculator = None
    pid_y: PidCalculator = None
    pid_z: PidCalculator = None
    running: bool = False
    control_interval: float = 0.1  # Seconds
    control_tolerance: int = 5
    _lock: threading.Lock = None
    _pause_event: threading.Event = None
    # Initialize JSON data storage
    json_data = []
    # Generate filename with current date and time
    current_time = datetime.now().strftime("%Y%m%d_%H%M")
    json_file = f'flight_data_{current_time}.json'    
    # 添加回调相关属性
    _target_reached_callbacks: list = None
    _target_monitor_lock: threading.Lock = None

    def __post_init__(self):
        """Initialize the thread lock and pause event after dataclass creation."""
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Initially set to allow the thread to run
        # 初始化回调列表和监视锁
        self._target_reached_callbacks = []
        self._target_monitor_lock = threading.Lock()
        

    def __calculate_location_delta(self, current: list, desired: list) -> list:
        """Calculate the difference between current and desired coordinates.

        Args:
            current (list): Current [x, y, z].
            desired (list): Desired [x, y, z].

        Returns:
            list: Delta [dx, dy, dz].
        """
        return [desired[i] - current[i] for i in range(0, 3)]
    
    def __calculate_heading_delta(self, current : int, desired : int) -> int:
        '''Calculate the difference between current and the desired heading

        Args:
            current (int)
            desired (int)

        Return:
            dheading (int): assuming right turn as positive
        '''

        dheading = (desired - current) % 360
        if dheading > 180:
            dheading = dheading - 360  # Ensure shortest rotation
        return dheading

    def __global_to_local(self, dx_global: float, dy_global: float, heading: float) -> tuple:
        """Transform 2D position error from global to local frame using heading.

        Args:
            dx_global (float): X error in global frame.
            dy_global (float): Y error in global frame.
            heading (float): Current heading angle in degrees.

        Returns:
            tuple: (dx_local, dy_local) in the drone's local frame.
        """
        heading_rad = math.radians(heading)
        dx_local = dx_global * math.cos(heading_rad) + dy_global *-math.sin(heading_rad)
        dy_local = dx_global * math.sin(heading_rad) + dy_global * math.cos(heading_rad)
        return dx_local, dy_local

    def register_target_reached_callback(self, callback):
        """
        注册目标到达时的回调函数
        
        Args:
            callback: 一个接受当前位置的函数，形式为 callback(current_position)
        """
        with self._target_monitor_lock:
            if callback not in self._target_reached_callbacks:
                self._target_reached_callbacks.append(callback)
                return True
        return False
    
    def unregister_target_reached_callback(self, callback):
        """
        注销目标到达回调函数
        
        Args:
            callback: 先前注册的回调函数
        """
        with self._target_monitor_lock:
            if callback in self._target_reached_callbacks:
                self._target_reached_callbacks.remove(callback)
                return True
        return False
    
    def _notify_target_reached(self, current_position):
        """
        通知所有注册的回调函数目标已达到
        
        Args:
            current_position: 当前位置坐标
        """
        callbacks_to_call = []
        with self._target_monitor_lock:
            callbacks_to_call = self._target_reached_callbacks.copy()
        
        for callback in callbacks_to_call:
            try:
                callback(current_position)
            except Exception as e:
                print(f"目标到达回调执行出错: {e}")

    def set_target_location(self, new_target: list) -> bool:
        """Update target_location thread-safely with validation.

        Args:
            new_target (list): [x, y, z].

        Returns:
            bool: True if update successful, False if input is invalid.
        """
        # Validate input: must be a list of 3 numbers
        if not isinstance(new_target, list) or len(new_target) != 3 or not all(isinstance(x, (int, float)) for x in new_target):
            print("Invalid target location: must be [x, y, z]")
            return False
        with self._lock:
            self.target_location = new_target.copy()
            print(f"Target location updated to: {self.target_location}")
            return True
        
    def get_target_location(self) -> list:
        """Get the current target location.

        Returns:
            list: Current target location [x, y, z].
        """
        with self._lock:
            return self.target_location.copy() if self.target_location else None

    def set_current_location(self) -> bool:
        """Update target_location with current location and heading."""
        current = self.instance.get_coordinate()
        if not current or len(current) != 3:
            print("Failed to get current coordinates")
            return False
        return self.set_target_location(current)

    def pause(self):
        """Pause the control loop thread and command the drone to hover."""
        self._pause_event.clear()
        print("Control loop paused, drone hovering")

    def resume(self):
        """Resume the control loop thread."""
        self._pause_event.set()
        print("Control loop resumed")
    
    def flight_data_dump(self):
        with open(self.json_file, "w") as f:
            json.dump(self.json_data, f, indent=4)
            
    def control_loop(self):
        """Run PID control loop in a separate thread to adjust drone position and heading."""
        print("Starting PID control loop")
        self.i = 1          # Epoch indicator
        start_time = time.time()
        while self.running: # Check running state, stop before landing
            self._pause_event.wait() # Wait till _pause_event set, that is when resume() called
            ## Telemetry section 1
            epoch_start = time.time()
            self.i = self.i + 1

            ## Control section
            current_location = self.instance.get_coordinate()               # Get current location
            current_heading = self.instance.get_yaw()[0] - self.heading_ini # Get current heading (substracted by initial heading offset)

            with self._lock:                            # Acquire target location safely
                target_location = self.target_location

            # Acquire x, y,z error and transform x, y error to local frame using current heading
            delta_coordinate = self.__calculate_location_delta(current_location, target_location)
            dx_local, dy_local = self.__global_to_local(delta_coordinate[0], delta_coordinate[1], current_heading)

            dz = delta_coordinate[2]  # Z-axis unaffected by heading

            # Compute dx, dy, dz via PID calculator
            dx = self.pid_x.compute(dx_local)
            dy = self.pid_y.compute(dy_local)
            dz = self.pid_z.compute(dz)

            # Tolerance in cm
            if all(abs(d) < self.control_tolerance for d in [dx_local, dy_local, dz]):
                print("Target reached, hovering")
                # 当达到目标位置时触发回调，但只触发一次直到位置变化
                if not target_notified:
                    self._notify_target_reached(current_location)
                    target_notified = True
            else:
                # 位置发生变化，重置通知标志
                target_notified = False
                self.instance.single_fly_straight_flight(int(dx), int(dy), int(dz))

            ## Telemetry section 2
            # Calculate time metrics
            epoch_end = time.time()
            epoch_duration = epoch_end - epoch_start
            elapsed_time = epoch_end - start_time

            # Store data in JSON structure
            epoch_data = {
                'epoch': self.i,
                'timestamp': epoch_end,
                'epoch_duration': epoch_duration,
                'elapsed_time': elapsed_time,
                'current_location': current_location,
                'current_heading': current_heading,
                'target_location': target_location,
                'delta_coordinate': delta_coordinate,
                'dx_local': dx_local,
                'dy_local': dy_local,
                'dx': dx,
                'dy': dy,
                'dz': dz
            }
            self.json_data.append(epoch_data)


            time.sleep(self.control_interval)

        print("Control loop terminated")
