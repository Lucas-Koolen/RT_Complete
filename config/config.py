# =============[ DATABASE CONFIG ]============
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'password',
    'database': 'pallet_db'
}

TABLE_NAME = 'Objects'
DB_STATUS_FILTER = 'unplaced'

# =============[ CAMERA CONFIG ]============
PIXEL_TO_MM = 0.052  # mm per pixel (handmatig bepaald)
TOLERANCE_PERCENTAGE = 0.10  # 10% afwijking

# =============[ SERIAL COMMUNICATION ]============
SERIAL_PORT = 'COM3'
BAUD_RATE = 9600
SERIAL_TIMEOUT = 1  # seconden

# =============[ ROTATION LOGIC ]============
# Default instellingen voor rotatie invoeren

# =============[ DEBUG / LOGGING ]============
DEBUG_MODE = True
