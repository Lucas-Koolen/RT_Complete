from interfaces.serialCommunicator import SerialCommunicator
from config.config import FRAME_HEIGHT
from config.config import MM_PER_SECOND_PUSH_1, MM_PER_SECOND_PUSH_2

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

        #print(f"Handling movement with angle: {angle}, center: ({objectCenterX}, {objectCenterY}), dimensions: ({objectLength}, {objectWidth}, {objectHeight}), target: ({targetLength}, {targetWidth}, {targetHeight})")
        
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
                    if targetLength == 0 or targetWidth == 0 or targetHeight == 0:
                        return

                    # Mapping van targetdimensies met labels
                    remainingTargets = {
                        "length": targetLength,
                        "width": targetWidth,
                        "height": targetHeight
                    }

                    # --- 1. Match objectLength ---
                    bestMatch = min(remainingTargets.items(), key=lambda kv: abs(objectLength - kv[1]))
                    setattr(self, f"{bestMatch[0]}Dimension", objectLength)
                    del remainingTargets[bestMatch[0]]

                    # --- 2. Match objectWidth ---
                    bestMatch = min(remainingTargets.items(), key=lambda kv: abs(objectWidth - kv[1]))
                    setattr(self, f"{bestMatch[0]}Dimension", objectWidth)
                    del remainingTargets[bestMatch[0]]

                    # --- 3. Overgebleven target wordt gekoppeld aan objectHeight ---
                    remainingLabel = list(remainingTargets.keys())[0]
                    setattr(self, f"{remainingLabel}Dimension", objectHeight)

                    # Doelwaarden opslaan
                    self.targetLength = targetLength
                    self.targetWidth = targetWidth
                    self.targetHeight = targetHeight

                    # ROTATIE- EN FLIP-LOGICA
                    if objectHeight == self.widthDimension:
                        self.needToRotateFirstTable = True
                    else:
                        self.needToRotateFirstTable = False

                    if self.heightDimension == objectLength or self.heightDimension == objectWidth:
                        self.needToFlip = True
                        self.needToRotateSecondTable = (objectHeight == self.widthDimension)
                    else:
                        self.needToFlip = False
                        self.needToRotateSecondTable = (self.lengthDimension != objectLength)

                    # Debugoutput
                    print(f"Logic determined: needToFlip={self.needToFlip}, needToRotateFirstTable={self.needToRotateFirstTable}, needToRotateSecondTable={self.needToRotateSecondTable}")
                    print(f"Based on measurements: object: [{objectLength}, {objectWidth}, {objectHeight}], target: [{targetLength}, {targetWidth}, {targetHeight}], matching: [L:{self.lengthDimension}, W:{self.widthDimension}, H:{self.heightDimension}]")

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
                    if self.needToFlip:
                        self.state = "FLIPPING"
                    else:
                        self.waitStartTime = time.time_ns() // 1_000_000
                        self.waitTime = 10000
                        self.state = "WAIT_FOR_CONVEYOR2"
            case "FLIPPING":
                self.communicator.moveFlipper(1, "EXIT")
                self.waitStartTime = time.time_ns() // 1_000_000
                self.state = "WAIT_FOR_FLIP"
            case "WAIT_FOR_FLIP":
                if time.time_ns() // 1_000_000 - self.waitStartTime > 5000:
                    self.communicator.moveFlipper(1, "CLEAR")
                    self.waitStartTime = time.time_ns() // 1_000_000
                    self.waitTime = 6000
                    self.state = "WAIT_FOR_CONVEYOR2"
            case "WAIT_FOR_CONVEYOR2":
                if time.time_ns() // 1_000_000 - self.waitStartTime > self.waitTime:
                    self.communicator.moveConveyor(2, "STOP")
                    self.state = "PUSHING3"
            case "PUSHING3":
                distance = self.distance

                self.waitStartTime = time.time_ns() // 1_000_000
                if self.needToRotateSecondTable:
                    self.communicator.movePusher(2, "FWD", distance)
                    self.waitTime = distance / MM_PER_SECOND_PUSH_2 * 1000  # convert to milliseconds
                    self.state = "WAIT_FOR_PUSHING4"
                else:
                    self.communicator.movePusher(2, "FWD", 255)
                    self.waitTime = 255 / MM_PER_SECOND_PUSH_2 * 1000  # convert to milliseconds
                    self.state = "WAIT_FOR_PUSHING5"
            case "WAIT_FOR_PUSHING4":
                if time.time_ns() // 1_000_000 - self.waitStartTime > self.waitTime:
                    self.communicator.movePusher(2, "REV")
                    self.state = "WAIT_FOR_CLEARANCE2"
            case "WAIT_FOR_CLEARANCE2":
                if self.communicator.get_limit2_state():
                    self.state = "ROTATING_SECOND_TABLE"
            case "ROTATING_SECOND_TABLE":
                if self.needToRotateSecondTable:
                    self.communicator.rotateRotator(2, 90, "FWD")
                self.waitStartTime = time.time_ns() // 1_000_000
                self.state = "WAIT_FOR_ROTATION2"
            case "WAIT_FOR_ROTATION2":
                if time.time_ns() // 1_000_000 - self.waitStartTime > 500:
                    self.communicator.movePusher(2, "FWD", 255)
                    self.waitStartTime = time.time_ns() // 1_000_000
                    self.waitTime = 255 / MM_PER_SECOND_PUSH_2 * 1000
                    self.state = "WAIT_FOR_PUSHING5"
            case "WAIT_FOR_PUSHING5":
                if time.time_ns() // 1_000_000 - self.waitStartTime > self.waitTime:
                    self.communicator.movePusher(2, "REV")
                    self.state = "IDLE"
            case "DONE":
                print("Movement logic is done")
