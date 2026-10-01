import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import time

# ================= 硬體配置 =================
# 根據您之前的測試結果設定 COM Port
# 請確認順序：[前, 後, 左, 右]
SERIAL_PORTS = ['COM6', 'COM7', 'COM8', 'COM9'] 
BAUD_RATE = 115200

# 定義每個感測器的朝向 (Polar Plot 標準：0=右, 90=前, 180=左, 270=後)
# 根據您的安裝位置設定
SENSOR_ANGLES = [90, 270, 180, 0] 

# VL53L5CX 水平視場角 (FOV) 設定
# 雖然規格寫 45度，但邊緣通常較弱，這裡設定 50度 來嘗試抓取最大範圍
FOV = 50 
# ===========================================

# 共享數據緩衝區 (用來累積所有的點)
# 我們設大一點，讓點不會消失，這樣你轉一圈後可以看出完整的形狀
MAX_POINTS = 5000 
points_buffer = [] 
lock = threading.Lock() # 執行緒鎖，避免數據讀寫衝突
running = True

# --- Serial 讀取函式 ---
def read_serial(index, port_name):
    global points_buffer
    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=1)
        print(f"[{port_name}] 連接成功 - Sensor {index}")
    except Exception as e:
        print(f"[{port_name}] 連接失敗: {e}")
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
                
                # 簡單過濾：必須是 64 個數字
                if len(parts) == 64:
                    values = []
                    valid_line = True
                    for p in parts:
                        if p.replace('-','').isdigit():
                            v = int(p)
                            values.append(v)
                        else:
                            valid_line = False
                            break
                    
                    if valid_line and len(values) == 64:
                        matrix = np.array(values).reshape((8, 8))
                        
                        # 解析數據並轉換為極座標
                        sensor_center_deg = SENSOR_ANGLES[index]
                        new_points = []
                        
                        # 我們只取矩陣的中間幾行 (Row 3, 4)，代表水平切面
                        # 這樣可以畫出最準確的水平覆蓋範圍
                        for col in range(8):
                            # 取中間兩行的平均距離
                            dist = (matrix[3, col] + matrix[4, col]) / 2.0
                            
                            # 過濾無效距離 (太近<20mm 或 太遠>800mm 都不要)
                            if 50 < dist < 800:
                                # 計算角度偏移：Col 0 在最左(-FOV/2), Col 7 在最右(+FOV/2)
                                # 映射公式： (col - 3.5) 把 0~7 變成 -3.5 ~ +3.5
                                angle_offset = (col - 3.5) * (FOV / 7.0)
                                
                                # 絕對角度 (轉成弧度給 matplotlib 用)
                                final_angle_rad = np.radians(sensor_center_deg + angle_offset)
                                
                                new_points.append((final_angle_rad, dist))
                        
                        # 存入共享緩衝區
                        with lock:
                            points_buffer.extend(new_points)
                            # 如果點太多，刪掉舊的 (保持在 MAX_POINTS 內)
                            if len(points_buffer) > MAX_POINTS:
                                del points_buffer[:len(points_buffer) - MAX_POINTS]

        except Exception as e:
            pass
        time.sleep(0.002) # 極短暫休眠

# 啟動 4 個執行緒
for i, port in enumerate(SERIAL_PORTS):
    t = threading.Thread(target=read_serial, args=(i, port))
    t.daemon = True
    t.start()

# --- 繪圖設定 ---
fig = plt.figure(figsize=(10, 10), facecolor='black') # 視窗背景全黑
ax = fig.add_subplot(111, projection='polar')

# 設定雷達圖外觀
ax.set_facecolor('black') # 繪圖區背景全黑
ax.grid(True, color='#333333', linestyle='--', alpha=0.5) # 網格設為暗灰色
ax.set_theta_zero_location('E') # 0度在右邊
ax.set_rlabel_position(45)
ax.set_ylim(0, 800) # 設定顯示半徑為 80cm
ax.tick_params(colors='white') # 刻度文字設為白色

# 設定標題
plt.title("360° Blind Spot Mapper\n(Red=Visible, Black=Blind)", color='red', fontsize=16, pad=20)

# 初始化散點圖 (全紅色)
# s=30 點大一點，alpha=0.5 半透明讓重疊處更亮
scat = ax.scatter([], [], c='red', s=30, alpha=0.5, edgecolors='none')

def update(frame):
    with lock:
        if len(points_buffer) > 0:
            data = np.array(points_buffer)
            # data[:, 0] 是角度, data[:, 1] 是距離
            scat.set_offsets(np.c_[data[:, 0], data[:, 1]])
    return scat,

# 啟動動畫 (30ms 更新一次)
ani = FuncAnimation(fig, update, interval=30, blit=True, cache_frame_data=False)

print("程式啟動中... 請拿一個物體圍繞感測器旋轉以繪製地圖。")
plt.show()
running = False