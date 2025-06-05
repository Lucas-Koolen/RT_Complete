from enum import Enum

class Shape(Enum):
    """
    Enum representing different shapes.
    """
    BOX = 1
    CYLINDER = 2
    INVALID = 0

    def shapeToString(self):
        """
        Convert the shape enum to a string representation.
        """
        if self == Shape.BOX:
            return "box"
        elif self == Shape.CYLINDER:
            return "cylinder"
        else:
            return "invalid"