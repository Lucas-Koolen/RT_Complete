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
        self.lengthDimension = 0
        self.widthDimension = 0
        self.heightDimension = 0
        self.targetLength = 0
        self.targetWidth = 0
        self.targetHeight = 0
        self.distance = 0
        self.needToFlip = False
        self.needToRotateFirstTable = False
        self.needToRotateSecondTable = False

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
                self.waitStartTime = time.time_ns() // 1_000_000
                self.communicator.movePusher(1, "FWD", 250)
                self.state = "WAIT_FOR_PUSHING1"
            case "WAIT_FOR_PUSHING1":
                if objectCenterY > FRAME_HEIGHT / 2:
                    timeTaken = time.time_ns() // 1_000_000 - self.waitStartTime
                    self.distance = timeTaken / 1000 * MM_PER_SECOND_PUSH_1  # convert to seconds

                    #stop pusher 1
                    distance = sqrt((objectWidth / 2) ** 2 + (objectLength / 2) ** 2)
                    self.waitTime = distance + 5 / MM_PER_SECOND_PUSH_1 * 1000  # convert to milliseconds
                    self.communicator.movePusher(1, "REV")
                    self.waitStartTime = time.time_ns() // 1_000_000
                    self.state = "WAIT_FOR_CLEARANCE"
            case "WAIT_FOR_CLEARANCE":
                if time.time_ns() // 1_000_000 - self.waitStartTime > self.waitTime:
                    # find dimension that is closest to the target height

                    if targetLength == 0 or targetWidth == 0 or targetHeight == 0:
                        return

                    for dimension in [objectLength, objectWidth, objectHeight]:
                        if abs(dimension - targetLength) < abs(self.lengthDimension - targetLength):
                            self.lengthDimension = dimension
                    
                    for dimension in [objectLength, objectWidth, objectHeight]:
                        if abs(dimension - targetWidth) < abs(self.widthDimension - targetWidth) and dimension != self.lengthDimension:
                            self.widthDimension = dimension

                    for dimension in [objectLength, objectWidth, objectHeight]:
                        if dimension != self.lengthDimension and dimension != self.widthDimension:
                            self.heightDimension = dimension
                            break

                    self.targetLength = targetLength
                    self.targetWidth = targetWidth
                    self.targetHeight = targetHeight

                    if self.heightDimension == objectWidth:
                        # if the height dimension is the width, we need to rotate the object 90 degrees
                        self.needToRotateFirstTable = True
                    else:  
                        self.needToRotateFirstTable = False

                    if self.heightDimension == objectLength or self.heightDimension == objectWidth:
                        # if the height dimension is the length or width, we need to flip the object
                        self.needToFlip = True
                        # if width on top, rotate second table
                        if self.heightDimension == objectWidth:
                            self.needToRotateSecondTable = True
                        else:
                            self.needToRotateSecondTable = False
                    else:
                        self.needToFlip = False
                        if self.lengthDimension != objectLength:
                            # if the length or width dimension is not the same as the object, we need to rotate the second table
                            self.needToRotateSecondTable = True
                        else:
                            self.needToRotateSecondTable = False
                    self.state = "ROTATING"
            case "ROTATING":
                if self.needToRotateFirstTable:
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
                if time.time_ns() // 1_000_000 - self.waitStartTime > 5000:
                    self.communicator.moveFlipper(1, "CLEAR")
                    self.waitStartTime = time.time_ns() // 1_000_000
                    self.state = "WAIT_FOR_CONVEYOR2"
            case "WAIT_FOR_CONVEYOR2":
                if time.time_ns() // 1_000_000 - self.waitStartTime > 15000:
                    self.communicator.moveConveyor(2, "STOP")
                    self.state = "IDLE"
            case "PUSHING3":
                distance = self.distance + objectLength / 2
                if self.needToRotateFirstTable:
                    distance -= objectWidth / 2
                else:
                    distance -= objectLength / 2
                self.communicator.movePusher(2, "FWD", distance)

            case "DONE":
                print("Movement logic is done")
