import serial
import time
import sys

from logic.newHeightSensor import update_height
from config.config import SERIAL_PORT, BAUD_RATE
from config.config import PUSHER_MAX_DISTANCE, MM_PER_SECOND

class Communicator:

    def __init__(self, communicator):
        self._communicator = communicator
        self.beam1State = None
        self.beam2State = None
        self.limit1State = None
        self.limit2State = None
        self.height = None
        self.dobotState = None
        self.flipper2Pos = None

        # ─── Serial Connection ────────────────────────────────────────────────────
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
        except serial.SerialException:
            print("Error: No connection to serial port")
            sys.exit(1)

    def get_beam1_state(self):
        return self.beam1State
    
    def get_beam2_state(self):
        return self.beam2State
    
    def get_limit1_state(self):
        return self.limit1State
    
    def get_limit2_state(self):
        return self.limit2State
    
    def get_height(self):
        return self.height
    
    def get_dobot_state(self):
        return self.dobotState
    
    def get_flipper2_pos(self):
        return self.flipper2Pos
    
    def send_command(self, cmd):
        try:
            if cmd.startswith("POS 4"):
                try:
                    self.flipper2Pos = int(cmd.split()[2])
                    self.log(f"Flipper 2 position updated to {self.flipper2Pos}")
                except ValueError:
                    self.log("ERROR: Invalid POS 4 value")

            full_cmd = cmd.strip() + "\r\n"
            self.ser.write(full_cmd.encode("utf-8"))
            self.log(f"Sent: {cmd}")
        except serial.SerialException as e:
            self.log(f"ERROR sending: {e}")
    
    def update_from_serial(self):
        try:
            while self.ser.in_waiting:
                line = self.ser.readline().decode().strip()
                if line:
                    self.log(f"Received: {line}")

                # Beam sensors
                if line == "b10":
                    self.beam1State = False
                elif line == "b11":
                    self.beam1State = True
                elif line == "b20":
                    self.beam2State = False
                elif line == "b21":
                    self.beam2State = True

                # Limit switches
                elif line == "STOP2":
                    self.limit1State = True
                elif line == "STOP6":
                    self.limit2State = True
                elif line == "GO2":
                    self.limit1State = False
                elif line == "GO6":
                    self.limit2State = False

                # Height sensor
                elif line.startswith("HT "):
                    try:
                        raw_height = int(line.split()[1])
                        newHeight = update_height(raw_height)
                        if newHeight is not None:
                            self.height = newHeight
                    except ValueError as ve:
                        print(f"Error with processing height: {ve}")

            # Always refresh Pusher 2 enable/disable
            #self.update_pusher2_state()

        except Exception as e:
            print(f"Error: {e}")

    def rotateRotator(self, rotatorNumber, direction, degrees):
        # servo numbers: 1 = rotator 1, 7 = rotator 2
        # rotation: either "FWD" (clockwise) or "REV" (counter-clockwise)
        servoNumber = None
        match rotatorNumber:
            case 1:
                servoNumber = 1
            case 2:
                servoNumber = 7
            case _:
                print("Error: Invalid rotator number")
                return

        if direction not in ["FWD", "REV"]:
            print("Error: Invalid direction, must be 'FWD' or 'REV'")
            return
        
        if not (0 <= degrees <= 360):
            print("Error: Invalid degrees, must be between 0 and 360")
            return

        cmd = f"ROTATE {servoNumber} {direction} {degrees}"
        self.send_command(cmd)
        print(f"Rotator {rotatorNumber} {direction} {degrees}° was sent")

    def movePusher(self, pusherNumber, direction, distance = None):
        # pusher numbers: 2 = pusher 1, 6 = pusher 2
        # direction: either "FWD" (forward), "REV" (reverse) or "STOP"
        # REV and STOP do not require use the distance parameter
        # command uses time instead of distance
        servoNumber = None
        match pusherNumber:
            case 1:
                servoNumber = 2
            case 2:
                servoNumber = 6
            case _:
                print("Error: Invalid pusher number")
                return
            
        if pusherNumber == 2 and self.flipper2Pos != 210:
            print("Error: Flipper 2 is not in safe position.")
            return
        
        if direction == "FWD":
            if distance is None or distance < 0 or distance > PUSHER_MAX_DISTANCE:
                print(f"Error: Invalid distance for pusher {pusherNumber}, must be between 0 and {PUSHER_MAX_DISTANCE} mm")
                return
            time_millis = int(distance / MM_PER_SECOND * 1000)
            cmd = f"SET {servoNumber} {direction} {time_millis}"
        elif direction == "REV" or direction == "STOP":
            cmd = f"SET {servoNumber} {direction}"
        else:
            print("Error: Invalid direction, must be 'FWD', 'REV' or 'STOP'")
            return
        
        self.send_command(cmd)
        print(f"Pusher {pusherNumber} {direction} was sent")

    def moveFlipper(self, flipperNumber, position):
        # flipper numbers: 3 = flipper 1, 4 = flipper 2
        # position: either "CLEAR", "ENTER" or "EXIT"
        servoNumber = None
        servoPosition = None
        match flipperNumber, position:
            case (1, "CLEAR"):
                servoNumber = 3
                servoPosition = 0
            case (1, "ENTER"):
                servoNumber = 3
                servoPosition = 105
            case (1, "EXIT"):
                servoNumber = 3
                servoPosition = 210
            case (2, "CLEAR"):
                servoNumber = 4
                servoPosition = 210
            case (2, "ENTER"):
                servoNumber = 4
                servoPosition = 0
            case (2, "EXIT"):
                servoNumber = 4
                servoPosition = 110
            case _:
                print("Error: Invalid flipper number or position")
                return
            
        cmd = f"POS {servoNumber} {servoPosition}"
        self.send_command(cmd)
        print(f"Flipper {flipperNumber} {position} was sent")