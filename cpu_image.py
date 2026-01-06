import re
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def generate_cpu_chart_from_files(cpu_file_path, event_file_path, platform, image_path):
    """
    Args:
        cpu_file_path (str):  CPU data TXT file path
        event_file_path (str): event time stamp TXT file path
        image_path (str): the output filename
    """
    timestamps = []
    cpu_percents = []
    event_data = []

    # --- 1. read and analyze cpu data file ---
    cpu_pattern = re.compile(r'\[(\d{2}:\d{2}:\d{2})\], cpu percent: ([\d.]+)\%')
    try:
        with open(cpu_file_path, 'r') as f:
            for line in f:
                match = cpu_pattern.search(line)
                if match:
                    time_str = match.group(1)
                    percent_str = match.group(2)
                    
                    try:
                        # 转换时间字符串为 datetime 对象 (只处理 HH:MM:SS)
                        dt = datetime.strptime(time_str, '%H:%M:%S')
                        timestamps.append(dt)
                        cpu_percents.append(float(percent_str))
                    except ValueError:
                        # 跳过无效数据行
                        pass
    except FileNotFoundError:
        print(f"错误: 找不到 CPU 数据文件 {cpu_file_path}")
        return

    if not timestamps:
        print("错误: CPU 数据文件中没有找到有效数据来绘图。")
        return

    # --- 2. read and analyze event time stamp ---
    event_pattern = re.compile(r'\[(\d{2}:\d{2}:\d{2})\], (.+)')
    try:
        with open(event_file_path, 'r') as f:
            for line in f:
                match = event_pattern.search(line)
                if match:
                    # 提取 HH:MM:SS 和事件标签
                    time_str = match.group(1).strip()
                    label = match.group(2).strip()
                    event_data.append((time_str, label))
    except FileNotFoundError:
        print(f"警告: 找不到事件文件 {event_file_path}，将只绘制 CPU 曲线，不添加事件线。")
    
    # --- Matplotlib draw ---
    
    # 3. creat draw
    fig, ax = plt.subplots(figsize=(12, 7))

    # 4. draw CPU 
    max_cpu = max(cpu_percents) if cpu_percents else 100
    ax.plot(timestamps, cpu_percents, marker='o', linestyle='-', color='blue', label='CPU Usage', zorder=1)

    # 5. add even vertical line and tag
    if event_data:
        y_text_pos = max_cpu * 1.05
        
        for time_str, label in event_data:
            # 将事件时间转换为 datetime 对象，用于与 X 轴时间匹配
            event_dt = datetime.strptime(time_str, '%H:%M:%S')
            
            # 绘制垂直线
            ax.axvline(
                x=event_dt, 
                color='red', 
                linestyle='--', 
                linewidth=1.5, 
                zorder=0
            )
            
            # 添加文本标签
            ax.text(
                x=event_dt, 
                y=y_text_pos, 
                s=label, 
                rotation=90, 
                verticalalignment='bottom', 
                horizontalalignment='left', 
                color='darkred', 
                fontsize=10, 
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2') 
            )

    # 6. format X 
    date_format = mdates.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_format)
    fig.autofmt_xdate(rotation=45) 
    
    # 7. set title
    title="CPU usage of "+ platform
    ax.set_title(title, fontsize=16)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('CPU Usage (%)', fontsize=12)
    
    # 8. add grid
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(loc='upper right') 
    
    # 9. set Y scale
    ax.set_ylim(bottom=0, top=max_cpu * 1.2 if max_cpu > 0 else 100) 

    # 10. save image
    plt.tight_layout()
    plt.savefig(image_path)
    print(f"\nsucuss genrate image: {image_path}")
    plt.close(fig)

def cpu_image(txt_file_folder,platform, image_path):
    cpu_data_path = os.path.join(txt_file_folder, "cpu-consume.txt")
    event_path = os.path.join(txt_file_folder, "time-stamp.txt")
    generate_cpu_chart_from_files(cpu_data_path, event_path,platform, image_path)

if __name__ == "__main__":
    cpu_data_path = "test-results/cpu-consume.txt"
    event_path = "test-results/time-stamp.txt"
    generate_cpu_chart_from_files(cpu_data_path,event_path, 'cpu_usage_chart.png')