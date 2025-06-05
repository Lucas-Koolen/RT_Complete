average_height = None
_raw_height_buffer = []
MAX_BUFFER_SIZE = 10

# Nieuwe kalibratiefactoren (gebaseerd op jouw metingen)
HEIGHT_SCALE = -1.305
HEIGHT_OFFSET = 382.4
HEIGHT_MAX_VALID = 100  # mm

def get_latest_height():
    return average_height

def update_height(self, raw_height):
    height = HEIGHT_SCALE * raw_height + HEIGHT_OFFSET
    if 0 <= height <= HEIGHT_MAX_VALID:
        _raw_height_buffer.append(height)
        if len(_raw_height_buffer) > MAX_BUFFER_SIZE:
            _raw_height_buffer.pop(0)
        average_height = round(
            sum(self._raw_height_buffer) / len(_raw_height_buffer), 1
        )
        self.height_label.setText(f"Height: {average_height} mm")