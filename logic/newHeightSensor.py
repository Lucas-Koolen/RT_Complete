class HeightBuffer:
    def __init__(self, max_size=10, scale=-1.305, offset=382.4, max_valid=100):
        self.buffer = []
        self.max_size = max_size
        self.scale = scale
        self.offset = offset
        self.max_valid = max_valid
        self.average = None

    def update(self, raw_height):
        height = self.scale * raw_height + self.offset
        if 0 <= height <= self.max_valid:
            self.buffer.append(height)
            if len(self.buffer) > self.max_size:
                self.buffer.pop(0)
            self.average = round(sum(self.buffer) / len(self.buffer), 1)
        return self.average

    def get_latest(self):
        return self.average

# Example usage:
# height_buffer = HeightBuffer()
# height_buffer.update(raw_height)
# latest = height_buffer.get_latest()