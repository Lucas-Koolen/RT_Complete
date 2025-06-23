import pymysql
from config.config import DB_CONFIG, TABLE_NAME, DB_STATUS_FILTER, MATCH_TOLERANCE
from helpers.shape import Shape

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

        # also sort detected dimensions
        sorted_detected_dims = sorted([detected_l, detected_w, detected_h], reverse=True)
        # find resulting spot of height dimension in sorted list
        h_index = sorted_detected_dims.index(detected_h)
        # handle value error if height is not in the list
        if h_index == -1:
            print(f"[DB ERROR] Height {h_db} not found in sorted dimensions {sorted_db_dims}.")
            return None, False
        
        # create list for potential matches
        potential_matches = []

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

            # sort length, width and height from largest to smallest
            sorted_db_dims = sorted([l_db, w_db, h_db], reverse=True)

            match = True

            for i in range(3):
                if i == h_index:
                    continue
                if not self.is_within_tolerance(sorted_detected_dims[i], sorted_db_dims[i]):
                    match = False
                    break
            # if we reach here, we have a potential match
            if match and shape == detected_shape:
                potential_matches.append((sorted_db_dims, sorted_detected_dims, box))

        # go over potential matches and find the best one
        for sorted_db_dims, sorted_detected_dims, box in potential_matches:
            # calculate deviation for each dimension
            deviation = 0.0

            for i in range(3):
                deviation += abs(sorted_detected_dims[i] - sorted_db_dims[i])
                
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
