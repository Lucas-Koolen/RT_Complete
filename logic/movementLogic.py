from interfaces.serialCommunicator import SerialCommunicator
from config.config import FRAME_HEIGHT
from config.config import MM_PER_SECOND_PUSH_1

import time
from math import sqrt

class MovementLogic:
    def __init__(self, communicator: SerialCommunicator):
        self.communicator = communicator
        self.state = "IDLE"
        self.waitStartTime = 0
        self.waitTime = 0
        self.heightDimension = 0
        self.needToFlip = False
        self.needToRotate90 = False

    def handle_movement(self, angle, objectCenterX, objectCenterY, objectLength, objectWidth, objectHeight, targetLength, targetWidth, targetHeight):

        print(f"Handling movement with angle: {angle}, center: ({objectCenterX}, {objectCenterY}), dimensions: ({objectLength}, {objectWidth}, {objectHeight}), target: ({targetLength}, {targetWidth}, {targetHeight})")
        
        # switch case based on the current state
        match self.state:
            case "IDLE":
                #move conveyor belt 1 forward
                self.communicator.moveConveyor(1, "FWD")
                if self.communicator.get_beam2_state():
                    self.state = "LOADING"
            case "LOADING":
                if not self.communicator.get_beam2_state():
                    #stop conveyor belt 1
                    self.communicator.moveConveyor(1, "STOP")
                    self.state = "PUSHING1"
            case "PUSHING1":
                self.communicator.movePusher(1, "FWD", 250)
                self.state = "WAIT_FOR_PUSHING1"
            case "WAIT_FOR_PUSHING1":
                if objectCenterY > FRAME_HEIGHT / 2:
                    #stop pusher 1
                    distance = sqrt((objectWidth / 2) ** 2 + (objectLength / 2) ** 2)
                    self.waitTime = distance + 5 / MM_PER_SECOND_PUSH_1 * 1000  # convert to milliseconds
                    self.communicator.movePusher(1, "REV")
                    self.waitStartTime = time.time_ns() // 1_000_000
                    self.state = "WAIT_FOR_CLEARANCE"
            case "WAIT_FOR_CLEARANCE":
                # find dimension that is closest to the target height
                for dimension in [objectLength, objectWidth, objectHeight]:
                    if abs(dimension - targetHeight) < abs(self.heightDimension - targetHeight):
                        self.heightDimension = dimension

                if self.heightDimension == objectWidth:
                    # if the height dimension is the width, we need to rotate the object 90 degrees
                    self.needToRotate90 = True
                else:  
                    self.needToRotate90 = False

                if self.heightDimension == objectLength or self.heightDimension == objectWidth:
                    # if the height dimension is the length or width, we need to flip the object
                    self.needToFlip = True
                else:
                    self.needToFlip = False
                
                if time.time_ns() // 1_000_000 - self.waitStartTime > self.waitTime:
                    self.state = "ROTATING"
            case "ROTATING":
                if self.needToRotate90:
                    angle += 90

                if angle < 0:
                    self.communicator.rotateRotator(1, angle, "REV")
                elif angle > 0:
                    self.communicator.rotateRotator(1, angle, "FWD")
                # get current time from system
                self.waitStartTime = time.time_ns() // 1_000_000
                self.state = "WAIT_FOR_ROTATION"
            case "WAIT_FOR_ROTATION":
                if time.time_ns() // 1_000_000 - self.waitStartTime > 500 and self.communicator.get_limit1_state():
                    self.state = "PREPARING_FLIP"
            case "PREPARING_FLIP":
                if self.needToFlip:
                    self.communicator.moveFlipper(1, "ENTER")
                self.state = "PUSHING2"
            case "PUSHING2":
                self.communicator.movePusher(1, "FWD", 255)
                self.communicator.moveConveyor(2, "FWD")
                self.waitTime = 255 / MM_PER_SECOND_PUSH_1 * 1000
                self.waitStartTime = time.time_ns() // 1_000_000
                self.state = "WAIT_FOR_PUSHING2"
            case "WAIT_FOR_PUSHING2":
                if time.time_ns() // 1_000_000 - self.waitStartTime > self.waitTime:
                    self.communicator.movePusher(1, "REV")
                    self.state = "WAIT_FOR_PUSHING3"
            case "WAIT_FOR_PUSHING3":
                if self.communicator.get_limit1_state():
                    self.state = "FLIPPING"
            case "FLIPPING":
                if self.needToFlip:
                    self.communicator.moveFlipper(1, "EXIT")
                    self.waitStartTime = time.time_ns() // 1_000_000
                    self.state = "WAIT_FOR_FLIP"
                else:
                    self.waitStartTime = time.time_ns() // 1_000_000
                    self.state = "WAIT_FOR_CONVEYOR2"
            case "WAIT_FOR_FLIP":
                if time.time_ns() // 1_000_000 - self.waitStartTime > 1500:
                    self.communicator.moveFlipper(1, "CLEAR")
                    self.waitStartTime = time.time_ns() // 1_000_000
                    self.state = "WAIT_FOR_CONVEYOR2"
            case "WAIT_FOR_CONVEYOR2":
                if time.time_ns() // 1_000_000 - self.waitStartTime > 1000:
                    self.communicator.moveConveyor(2, "STOP")
                    self.state = "IDLE"
            case "DONE":
                print("Movement logic is done")
