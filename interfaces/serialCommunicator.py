import serial
import time
import sys

from helpers.heightBuffer import HeightBuffer
from config.config import SERIAL_PORT, BAUD_RATE
from config.config import PUSHER_MAX_DISTANCE, MM_PER_SECOND_PUSH_1, MM_PER_SECOND_PUSH_2

class SerialCommunicator:

    def __init__(self):
        self.beam1State = None
        self.beam2State = None
        self.limit1State = None
        self.pusher1Pos = None
        self.limit2State = None
        self.pusher2Pos = None
        self.height = None
        self.dobotState = None
        self.flipper2Pos = None
        self.heightSensor = HeightBuffer()

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
    
    def get_pusher1_pos(self):
        return self.pusher1Pos
    
    def get_limit2_state(self):
        return self.limit2State
    
    def get_pusher2_pos(self):  
        return self.pusher2Pos
    
    def get_height(self):
        return self.height
    
    def get_dobot_state(self):
        return self.dobotState
    
    def get_flipper2_pos(self):
        return self.flipper2Pos
    
    def send_command(self, cmd):
        try:
            full_cmd = cmd.strip() + "\r\n"
            self.ser.write(full_cmd.encode("utf-8"))
            print(f"Sent: {full_cmd.strip()}")
        except serial.SerialException as e:
            print(f"Error sending command: {e}")
    
    def update_from_serial(self):
        try:
            while self.ser.in_waiting:
                line = self.ser.readline().decode().strip()
                if line:
                    print(f"Received: {line}")

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
                        newHeight = self.heightSensor.update(raw_height)
                        if newHeight is not None:
                            self.height = newHeight
                    except ValueError as ve:
                        print(f"Error with processing height: {ve}")

        except Exception as e:
            print(f"Error: {e}")

    def rotateRotator(self, rotatorNumber, degrees, direction):
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

        cmd = f"ROTATE {servoNumber} {degrees} {direction}"
        self.send_command(cmd)
        print(f"Rotator {rotatorNumber} {degrees} {direction}° was sent")

    def movePusher(self, pusherNumber, direction, distance = None):
        # pusher numbers: 2 = pusher 1, 6 = pusher 2
        # direction: either "FWD" (forward), "REV" (reverse) or "STOP"
        # REV and STOP do not require use the distance parameter
        # command uses time instead of distance
        servoNumber = None
        mmPerSecond = None

        match pusherNumber:
            case 1:
                servoNumber = 2
                mmPerSecond = MM_PER_SECOND_PUSH_1
            case 2:
                servoNumber = 6
                mmPerSecond = MM_PER_SECOND_PUSH_2
            case _:
                print("Error: Invalid pusher number")
                return
                        
        if pusherNumber == 2 and self.flipper2Pos != 200:
            print("Error: Flipper 2 is not in safe position.")
            return
        
        if direction == "FWD":
            if distance is None or distance < 0 or distance > PUSHER_MAX_DISTANCE:
                print(f"Error: Invalid distance for pusher {pusherNumber}, must be between 0 and {PUSHER_MAX_DISTANCE} mm")
                return
            time_millis = int(distance / mmPerSecond * 1000)
            cmd = f"SET {servoNumber} {direction} {time_millis}"
            if pusherNumber == 1:
                self.pusher1Pos = self.pusher1Pos + distance if self.pusher1Pos is not None else distance
            elif pusherNumber == 2:
                self.pusher2Pos = self.pusher2Pos + distance if self.pusher2Pos is not None else distance
        elif direction == "REV" or direction == "STOP":
            cmd = f"SET {servoNumber} {direction}"
            if pusherNumber == 1:
                self.pusher1Pos = 0
            elif pusherNumber == 2:
                self.pusher2Pos = 0
        else:
            print("Error: Invalid direction, must be 'FWD', 'REV' or 'STOP'")
            return
        
        self.send_command(cmd)
        print(f"Pusher {pusherNumber} {direction} was sent")

    def moveConveyor(self, conveyorNumber, direction):
        # conveyor numbers: 0 = conveyor 1, 5 = conveyor 2
        # direction: either "FWD" (forward), "REV" (reverse) or "STOP"
        servoNumber = None
        match conveyorNumber:
            case 1:
                servoNumber = 0
            case 2:
                servoNumber = 5
            case _:
                print("Error: Invalid conveyor number")
                return
            
        if direction not in ["FWD", "REV", "STOP"]:
            print("Error: Invalid direction, must be 'FWD', 'REV' or 'STOP'")
            return
        
        cmd = f"SET {servoNumber} {direction}"
        self.send_command(cmd)
        print(f"Conveyor {conveyorNumber} {direction} was sent")

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
                servoPosition = 110
            case (1, "EXIT"):
                servoNumber = 3
                servoPosition = 185
            case (2, "CLEAR"):
                servoNumber = 4
                servoPosition = 200
                self.flipper2Pos = 200
            case (2, "ENTER"):
                servoNumber = 4
                servoPosition = 10
                self.flipper2Pos = 10
            case (2, "EXIT"):
                servoNumber = 4
                servoPosition = 100
                self.flipper2Pos = 100
            case _:
                print("Error: Invalid flipper number or position")
                return
            
        cmd = f"POS {servoNumber} {servoPosition}"
        self.send_command(cmd)
        print(f"Flipper {flipperNumber} {position} was sent")