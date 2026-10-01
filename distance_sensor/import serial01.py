import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import time

# ================= 硬體配置 =================
PORT = 'COM7'  # 僅測試 COM7
BAUD_RATE = 115200

# 垂直視場角 (Vertical FOV) 設定
# VL53L5CX 為正方形矩陣，垂直與水平 FOV 理論上相同，約 45~50 度
FOV = 50 
# ===========================================

points_buffer = [] 
MAX_POINTS = 3000 # 單顆感測器不需要太多點
lock = threading.Lock()
running = True

# --- Serial 讀取函式 ---
def read_serial():
    global points_buffer
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        print(f"[{PORT}] 連接成功，開始垂直掃描...")
    except Exception as e:
        print(f"[{PORT}] 連接失敗: {e}")
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
                    valid_line = True
                    for p in parts:
                        if p.replace('-','').isdigit():
                            values.append(int(p))
                        else:
                            valid_line = False
                            break
                    
                    if valid_line and len(values) == 64:
                        matrix = np.array(values).reshape((8, 8))
                        new_points = []
                        
                        # 【關鍵修改】改為掃描「垂直方向 (Rows)」
                        # 我們取中間兩列 (Col 3, 4) 的平均值來代表正前方的垂直切面
                        for row in range(8):
                            dist = (matrix[row, 3] + matrix[row, 4]) / 2.0
                            
                            if 50 < dist < 800:
                                # 計算仰角：假設 Row 0 在最上面 (+FOV/2)，Row 7 在最下面 (-FOV/2)
                                # (3.5 - row) 會把 row 0~7 轉換成 +3.5 ~ -3.5
                                angle_deg = (3.5 - row) * (FOV / 7.0)
                                angle_rad = np.radians(angle_deg)
                                
                                new_points.append((angle_rad, dist))
                        
                        with lock:
                            points_buffer.extend(new_points)
                            if len(points_buffer) > MAX_POINTS:
                                del points_buffer[:len(points_buffer) - MAX_POINTS]

        except Exception as e:
            pass
        time.sleep(0.002)

# 啟動執行緒
t = threading.Thread(target=read_serial)
t.daemon = True
t.start()

# --- 繪圖設定 ---
fig = plt.figure(figsize=(8, 8), facecolor='black')
ax = fig.add_subplot(111, projection='polar')

# 設定雷達圖外觀
ax.set_facecolor('black')
ax.grid(True, color='#333333', linestyle='--', alpha=0.5)

# 【關鍵修改】將雷達圖設定為「右半圓」，模擬側面視角
ax.set_theta_zero_location('E') # 0度(正前方)在右邊
ax.set_thetamin(-90)            # 顯示下半部到 -90度
ax.set_thetamax(90)             # 顯示上半部到 +90度
ax.set_ylim(0, 800)             # 最遠 80cm
ax.tick_params(colors='white')

plt.title(f"Vertical Blind Spot Mapper ({PORT})\n(0°=Forward, +Up, -Down)", color='red', fontsize=14, pad=20)

scat = ax.scatter([], [], c='red', s=40, alpha=0.5, edgecolors='none')

def update(frame):
    with lock:
        if len(points_buffer) > 0:
            data = np.array(points_buffer)
            scat.set_offsets(np.c_[data[:, 0], data[:, 1]])
    return scat,

ani = FuncAnimation(fig, update, interval=30, blit=True, cache_frame_data=False)

print("請將手掌或板子在感測器正前方『上下』移動...")
plt.show()
running = False