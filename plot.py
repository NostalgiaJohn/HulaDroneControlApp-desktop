import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from datetime import datetime
import pathlib
import os
import re
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d.art3d import Line3DCollection

def get_latest_json_file(journal_path : pathlib.Path):
    """Scan current directory for flight_data_YYYYMMDD_HHMM.json files and return the latest."""
    json_pattern = r'flight_data_(\d{8}_\d{4})\.json'
    json_files = []
    
    if not journal_path.exists():
        raise FileNotFoundError(f"Directory '{journal_path}' does not exist. Please ensure the flight journals are stored there.")
    if not journal_path.is_dir():
        raise NotADirectoryError(f"Path '{journal_path}' is not a directory. Please ensure the flight journals are stored there.")
    
    for file in journal_path.iterdir():
        match = re.match(json_pattern, file.name)
        if match:
            timestamp_str = match.group(1)
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M')
                json_files.append((file, timestamp))
            except ValueError:
                continue
    
    if not json_files:
        raise FileNotFoundError("No valid 'flight_data_YYYYMMDD_HHMM.json' files found in the current directory.")
    
    return max(json_files, key=lambda x: x[1])[0]

def plot_flight_data(json_file=None):
    """Generate multiple interactive plots to visualize drone flight data from the specified or latest JSON file."""
    # Enable interactive mode
    plt.ion()
    
    # Define paths
    journal_path = pathlib.Path(__file__).parent / 'flight_journals'
    plot_path = pathlib.Path(__file__).parent / 'flight_plots'
    plot_path.mkdir(parents=True, exist_ok=True)  # Ensure plots directory exists
    journal_path = journal_path.resolve()  # Ensure we have an absolute path
    # Use provided file or find the latest
    if json_file is None:
        json_file = get_latest_json_file(journal_path=journal_path)
        json_path = os.path.join(journal_path, json_file)
    else:
        # If full path provided, use it; otherwise combine with journals directory
        if os.path.dirname(json_file):
            json_path = json_file
        else:
            json_path = os.path.join(journal_path, json_file)
    
    # Read JSON data
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file '{json_path}' not found. Ensure the control loop has run and the file exists.")

    # Extract data
    current_x = [epoch['current_location'][0] for epoch in data]
    current_y = [epoch['current_location'][1] for epoch in data]
    current_z = [epoch['current_location'][2] for epoch in data]
    target_x = [epoch['target_location'][0] for epoch in data]
    target_y = [epoch['target_location'][1] for epoch in data]
    target_z = [epoch['target_location'][2] for epoch in data]
    elapsed_time = [epoch['elapsed_time'] for epoch in data]
    dx_local = [epoch['dx_local'] for epoch in data]
    dy_local = [epoch['dy_local'] for epoch in data]
    dz = [epoch['dz'] for epoch in data]
    dx = [epoch['dx'] for epoch in data]
    dy = [epoch['dy'] for epoch in data]
    current_heading = [epoch['current_heading'] for epoch in data]
    epoch_duration = [epoch['epoch_duration'] for epoch in data]
    
    # Plot 1: 3D Trajectory
    fig1 = plt.figure(figsize=(10, 8))
    ax1 = fig1.add_subplot(111, projection='3d')
    points = np.array([current_x, current_y, current_z]).T
    segments = np.concatenate([points[:-1, np.newaxis], points[1:, np.newaxis]], axis=1)
    norm = plt.Normalize(min(elapsed_time), max(elapsed_time))
    lc = Line3DCollection(segments, cmap='viridis', norm=norm)
    lc.set_array(np.array(elapsed_time[:-1]))
    ax1.add_collection3d(lc)
    fig1.colorbar(lc, ax=ax1, label='Elapsed Time (s)')
    unique_targets = np.unique(np.vstack((target_x, target_y, target_z)).T, axis=0)
    ax1.scatter(unique_targets[:, 0], unique_targets[:, 1], unique_targets[:, 2], 
                c='r', marker='o', s=100, label='Target Locations')
    ax1.set_xlabel('X (cm)')
    ax1.set_ylabel('Y (cm)')
    ax1.set_zlabel('Z (cm)')
    ax1.set_title(f'Drone Flight Path: Current vs Target Locations\nData from {json_file}')
    ax1.legend()

    # Annotate each current location point with its elapsed time label.
    # Offset is applied in the z-direction so that the text appears "under" the point.
    offset = 5  # adjust this value based on your data scale
    for x, y, z, t in zip(current_x, current_y, current_z, elapsed_time):
        ax1.text(x, y, z - offset, f'{t:.1f}s', fontsize=8, color='black', ha='center')

    plt.savefig(os.path.join(plot_path, 'flight_path_3d.png'))

    # Plot 2: Error Over Time
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.plot(elapsed_time, np.abs(dx_local), label='|dx_local| (X Error)', color='b')
    ax2.plot(elapsed_time, np.abs(dy_local), label='|dy_local| (Y Error)', color='g')
    ax2.plot(elapsed_time, np.abs(dz), label='|dz| (Z Error)', color='r')
    ax2.set_xlabel('Elapsed Time (s)')
    ax2.set_ylabel('Absolute Error (cm)')
    ax2.set_title('Positional Errors Over Time')
    ax2.legend()
    ax2.grid(True)
    plt.savefig(os.path.join(plot_path, 'error_over_time.png'))

    # Plot 3: Control Outputs Over Time
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    ax3.plot(elapsed_time, dx, label='dx (X Control)', color='b')
    ax3.plot(elapsed_time, dy, label='dy (Y Control)', color='g')
    ax3.plot(elapsed_time, dz, label='dz (Z Control)', color='r')
    ax3.set_xlabel('Elapsed Time (s)')
    ax3.set_ylabel('Control Output (cm/s)')
    ax3.set_title('Control Outputs Over Time')
    ax3.legend()
    ax3.grid(True)
    plt.savefig(os.path.join(plot_path, 'control_outputs_over_time.png'))

    # Plot 4: Heading Over Time
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    ax4.plot(elapsed_time, current_heading, label='Current Heading', color='m')
    ax4.set_xlabel('Elapsed Time (s)')
    ax4.set_ylabel('Heading (degrees)')
    ax4.set_title('Heading Over Time')
    ax4.legend()
    ax4.grid(True)
    plt.savefig(os.path.join(plot_path, 'heading_over_time.png'))

    # Plot 5: Epoch Duration Histogram
    fig5, ax5 = plt.subplots(figsize=(10, 6))
    ax5.hist(epoch_duration, bins=20, color='c', edgecolor='k')
    ax5.set_xlabel('Epoch Duration (s)')
    ax5.set_ylabel('Frequency')
    ax5.set_title('Histogram of Epoch Durations')
    ax5.grid(True)
    plt.savefig(os.path.join(plot_path, 'epoch_duration_histogram.png'))

    # Display all plots and wait until closed
    plt.show(block=True)

if __name__ == "__main__":
    plot_flight_data()