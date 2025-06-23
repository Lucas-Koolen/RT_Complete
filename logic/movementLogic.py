from interfaces.serialCommunicator import SerialCommunicator
from config.config import FRAME_HEIGHT
from config.config import MM_PER_SECOND_PUSH_1

import time
from math import sqrt

class MovementLogic:
    def __init__(self, communicator: SerialCommunicator):
        self.communicator = communicator
        self.state = "IDLE"
        self.rotatorWaitStartTime = 0
        self.pusher1WaitStartTime = 0
        self.pusher1WaitTime = 0

    def handle_movement(self, angle, objectCenterX, objectCenterY, objectLength, objectWidth, objectHeight, targetLength, targetWidth, targetHeight):
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
                    self.pusher1WaitTime = distance + 5 / MM_PER_SECOND_PUSH_1 * 1000  # convert to milliseconds
                    self.communicator.movePusher(1, "REV")
                    self.pusher1WaitStartTime = time.time_ns() // 1_000_000
                    self.state = "WAIT_FOR_CLEARANCE"
            case "WAIT_FOR_CLEARANCE":
                if time.time_ns() // 1_000_000 - self.pusher1WaitStartTime > self.pusher1WaitTime:
                    self.state = "ROTATING"
            case "ROTATING":
                if angle < 0:
                    self.communicator.rotateRotator(1, angle, "REV")
                elif angle > 0:
                    self.communicator.rotateRotator(1, angle, "FWD")
                # get current time from system
                self.rotatorWaitStartTime = time.time_ns() // 1_000_000
                self.state = "WAIT_FOR_ROTATION"
            case "WAIT_FOR_ROTATION":
                if time.time_ns() // 1_000_000 - self.rotatorWaitStartTime > 1000 and self.communicator.get_limit1_state():
                    self.state = "PUSHING2"
            case "PUSHING2":
                self.communicator.movePusher(1, "FWD", 250)
                self.pusher1WaitTime = 250 / MM_PER_SECOND_PUSH_1 * 1000
                self.pusher1WaitStartTime = time.time_ns() // 1_000_000
                self.state = "WAIT_FOR_PUSHING2"
            case "WAIT_FOR_PUSHING2":
                if time.time_ns() // 1_000_000 - self.pusher1WaitStartTime > self.pusher1WaitTime:
                    self.pusher1WaitStartTime = time.time_ns() // 1_000_000
                    self.communicator.movePusher(1, "REV")
                    self.state = "WAIT_FOR_PUSHING3"
            case "WAIT_FOR_PUSHING3":
                if time.time_ns() // 1_000_000 - self.pusher1WaitStartTime > self.pusher1WaitTime:
                    self.state = "DONE"
            case "DONE":
                print("Movement logic is done")
