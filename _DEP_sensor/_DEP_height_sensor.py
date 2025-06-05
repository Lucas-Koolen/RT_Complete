import serial
import threading
import time
from config.config import SERIAL_PORT

latest_height = None
_raw_buffer = []
_lock = threading.Lock()
MAX_BUFFER = 10

# Nieuwe kalibratiefactoren (gebaseerd op jouw metingen)
HEIGHT_SCALE = -1.305
HEIGHT_OFFSET = 382.4
HEIGHT_MAX_VALID = 100  # mm

def read_height_sensor():
    global latest_height
    try:
        ser = serial.Serial(SERIAL_PORT, 9600, timeout=1)
        print(f"📡 Verbonden met VL53L1X op {SERIAL_PORT}")
    except Exception as e:
        print(f"❌ Sensor verbinding mislukt: {e}")
        return

    while True:
        try:
            raw = ser.readline().decode("utf-8").strip()
            if not raw or not raw.isdigit():
                continue
            val = int(raw)
            height = HEIGHT_SCALE * val + HEIGHT_OFFSET

            if 0 <= height <= HEIGHT_MAX_VALID:
                with _lock:
                    _raw_buffer.append(height)
                    if len(_raw_buffer) > MAX_BUFFER:
                        _raw_buffer.pop(0)
                    latest_height = round(sum(_raw_buffer) / len(_raw_buffer), 1)
        except Exception:
            continue

def start_sensor_thread():
    threading.Thread(target=read_height_sensor, daemon=True).start()

def get_latest_height():
    with _lock:
        return latest_height
