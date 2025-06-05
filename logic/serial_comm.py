import serial
import time
from config.config import SERIAL_PORT, BAUD_RATE, SERIAL_TIMEOUT

class SerialCommunicator:
    def __init__(self):
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
            time.sleep(2)  # Wacht tot Arduino reset
            print(f"[SERIAL] Verbonden met Arduino op {SERIAL_PORT}")
        except serial.SerialException as e:
            print(f"[SERIAL ERROR] Kan niet verbinden met {SERIAL_PORT}: {e}")
            self.ser = None

    def send_command(self, command: str):
        if self.ser is None:
            print("[SERIAL] Geen actieve verbinding.")
            return

        try:
            self.ser.write((command.strip() + '\n').encode())
            if self.ser.in_waiting:
                return self.ser.readline().decode().strip()
        except Exception as e:
            print(f"[SERIAL ERROR] Fout bij verzenden: {e}")

    def read_line(self):
        if self.ser and self.ser.in_waiting:
            try:
                return self.ser.readline().decode().strip()
            except Exception as e:
                print(f"[SERIAL ERROR] Fout bij lezen: {e}")
        return None

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[SERIAL] Verbinding gesloten.")
