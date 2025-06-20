class HeightBuffer:
    def __init__(self, max_size=1, scale=-0.9722, offset=342.22, max_valid=100):
        self.buffer = []
        self.max_size = max_size
        self.scale = scale
        self.offset = offset
        self.max_valid = max_valid
        self.average = None

    def update(self, raw_height):
        height = self.scale * raw_height + self.offset
        if height <= self.max_valid:
            if height < 0:
                height = 0
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