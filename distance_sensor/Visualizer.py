
import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import time

# --- 參數設定 ---
PORT_NAME = '/dev/ttyUSB0'
BAUD_RATE = 115200

GRIP_THRESHOLD_MM = 80   # 夾取觸發距離門檻 (mm)
COOLDOWN_SEC = 2.0       # 冷卻時間 (秒)

sensor_data = np.zeros((8, 8), dtype=int)
running = True
is_gripping = False
last_trigger_time = 0.0

def execute_grip():
    print("\n" + "="*40)
    print(">>> [ACTION] 偵測到物體進入手心範圍，執行夾取！ <<<")
    print("="*40 + "\n")

def check_trigger(data):
    global is_gripping, last_trigger_time
    center_roi = data[2:6, 2:6]
    valid_points = center_roi[(center_roi > 20) & (center_roi < 1500)]
    
    current_time = time.time()
    if len(valid_points) >= 4:
        min_dist = np.min(valid_points)
        if min_dist <= GRIP_THRESHOLD_MM and (current_time - last_trigger_time > COOLDOWN_SEC):
            is_gripping = True
            last_trigger_time = current_time
            execute_grip()
        elif min_dist > GRIP_THRESHOLD_MM + 20:
            is_gripping = False

def read_serial():
    global sensor_data, running
    try:
        ser = serial.Serial(PORT_NAME, BAUD_RATE, timeout=1)
        ser.reset_input_buffer()
        print(f"[{PORT_NAME}] Serial Open Success")
    except Exception as e:
        print(f"[{PORT_NAME}] Open Failed: {e}")
        return

    while running:
        try:
            if ser.in_waiting:
                line_raw = ser.readline()
                try:
                    line = line_raw.decode('utf-8').strip()
                except:
                    continue

                parts = line.split(',')
                if len(parts) == 64:
                    values = []
                    valid = True
                    for p in parts:
                        clean = p.strip().replace('-', '')
                        if clean.isdigit():
                            v = int(clean)
                            if v > 2000: v = 2000
                            values.append(v)
                        else:
                            valid = False
                            break
                    
                    if valid and len(values) == 64:
                        arr = np.array(values).reshape((8, 8))
                        sensor_data = arr
                        check_trigger(arr)
        except Exception:
            pass
        time.sleep(0.005)


t = threading.Thread(target=read_serial)
t.daemon = True
t.start()


plt.rcParams['toolbar'] = 'None'
fig, ax = plt.subplots(figsize=(8, 8), facecolor='#202020')
fig.canvas.manager.set_window_title('Amazing Hand - Matrix View')


im = ax.imshow(np.zeros((8, 8)), cmap='gray', vmin=0, vmax=1500)
ax.axis('off')

text_grid = []
for r in range(8):
    row_texts = []
    for c in range(8):
        txt = ax.text(c, r, "0", ha="center", va="center", color="#00FF00", fontsize=11, fontweight='bold')
        row_texts.append(txt)
    text_grid.append(row_texts)

title_text = ax.text(3.5, -0.6, 'Distance Sensor', ha='center', va='center', 
                     color='white', fontsize=14, fontweight='bold')

plt.tight_layout()

def update(frame):
    data = sensor_data
    im.set_data(data)
    
    for r in range(8):
        for c in range(8):
            val = data[r, c]
            text_grid[r][c].set_text(str(val))
            
            # 原版文字配色邏輯
            if val == 0:
                text_grid[r][c].set_color('#444444')
            elif val < 200:
                text_grid[r][c].set_color('#FF0000')   # 近距離紅字
            elif val < 500:
                text_grid[r][c].set_color('yellow')    # 中距離黃字
            else:
                text_grid[r][c].set_color('#00FF00')   # 遠距離綠字

    # 頂端觸發狀態提示
    if is_gripping:
        title_text.set_text(f'[ GRIPPING ACTIVATED ] Distance < {GRIP_THRESHOLD_MM}mm')
        title_text.set_color('#FF3366')
    else:
        title_text.set_text('Distance Sensor (Monitoring)')
        title_text.set_color('white')

    return [im, title_text]

ani = FuncAnimation(fig, update, interval=100, blit=False, cache_frame_data=False)
plt.show()
running = False
