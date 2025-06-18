import pymysql
from config.config import DB_CONFIG, TABLE_NAME, DB_STATUS_FILTER, MATCH_TOLERANCE
from logic.shape import Shape

class DatabaseConnector:
    def __init__(self):
        try:
            self.connection = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                port=DB_CONFIG['port'],
                autocommit=True
            )
            self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            print("[DB] Verbonden met MySQL.")
        except Exception as e:
            print(f"[DB ERROR] Kon niet verbinden: {e}")
            self.connection = None

    def get_unprocessed_boxes(self):
        if self.connection is None:
            return []
        query = f"SELECT * FROM {TABLE_NAME} WHERE status = %s"
        self.cursor.execute(query, (DB_STATUS_FILTER,))
        return self.cursor.fetchall()

    def mark_as_processed(self, common_id):
        if self.connection is None:
            return
        query = f"UPDATE {TABLE_NAME} SET status = 'processed' WHERE commonId = %s"
        self.cursor.execute(query, (common_id,))
        self.connection.commit()
        print(f"[DB] Doos {common_id} gemarkeerd als 'processed'.")

    def find_best_match(self, detected_l, detected_w, detected_h, detected_shape):
        candidates = self.get_unprocessed_boxes()
        best_match = None
        best_score = float('inf')  # lagere score = betere match

        for box in candidates:
            l_db = float(box['length'])
            w_db = float(box['width'])
            h_db = float(box['height'])
            shapeStr = box['shape']

            # get shape enum from string
            if shapeStr == 'box':
                shape = Shape.BOX
            elif shapeStr == 'cylinder':
                shape = Shape.CYLINDER
            else:
                shape = Shape.INVALID

            # controleer toleranties beide richtingen (L-B / B-L matchen)
            for dims in [(l_db, w_db), (w_db, l_db)]:
                l_match = self.is_within_tolerance(detected_l, dims[0])
                b_match = self.is_within_tolerance(detected_w, dims[1])
                shape_match = (shape == detected_shape)
                h_match = self.is_within_tolerance(detected_h, h_db)

                if l_match and b_match and shape_match:
                    deviation = abs(detected_l - dims[0]) + abs(detected_w - dims[1]) + abs(detected_h - h_db)
                    if deviation < best_score:
                        best_score = deviation
                        best_match = box

        return best_match, best_match is not None

    def is_within_tolerance(self, measured, reference):
        tolerance = reference * MATCH_TOLERANCE
        return (reference - tolerance) <= measured <= (reference + tolerance)

    def close(self):
        if self.connection:
            self.connection.close()
            print("[DB] Verbinding gesloten.")
