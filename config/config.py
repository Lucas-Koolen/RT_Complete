# =============[ DATABASE CONFIG ]============
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'rotator',
    'password': 's!P30DtH0UVv!#',
    'database': 'pallet_db'
}

TABLE_NAME = 'Objects'
DB_STATUS_FILTER = 'unprocessed'

# =============[ OBJECT DETECTION CONFIG ]============
FRAME_WIDTH = 2592
FRAME_HEIGHT = 1944
PIXEL_FORMAT = 0x02180014  # RGB8 Packed
EXPOSURE_TIME = 15000.0
GAIN = 10.0

# Process scale factor to speed up detection
PROCESS_SCALE = 0.5  # resize factor for processing frames

# =============[ CAMERA CONFIG ]============
MM_PER_PIXEL = 0.059  # mm per pixel (handmatig bepaald)
MATCH_TOLERANCE = 0.15  # 15% afwijking

# =============[ PUSHER CONFIG ]============
MM_PER_SECOND_PUSH_1 = 53  # mm per second calibrated for pusher 1
MM_PER_SECOND_PUSH_2 = 61  # mm per second calibrated for pusher 2
PUSHER_MAX_DISTANCE = 255  # mm

# =============[ SERIAL COMMUNICATION ]============
SERIAL_PORT = 'COM4'
BAUD_RATE = 9600
SERIAL_TIMEOUT = 1  # seconden

# =============[ ROTATION LOGIC ]============
# Default instellingen voor rotatie invoeren

# =============[ DEBUG / LOGGING ]============
DEBUG_MODE = True
