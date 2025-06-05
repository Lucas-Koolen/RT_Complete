import cv2
import numpy as np
import time
from config.config import MM_PER_PIXEL
from sensor.height_sensor import get_latest_height
from logic.json_parser import match_dimensions

_last_dimensions = None
_last_detected_time = 0

def detect_dimensions(frame):
    global _last_dimensions, _last_detected_time
    log = ""

    try:
        orig = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 7
        )

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = False

        for c in contours:
            area = cv2.contourArea(c)
            if area < 800:
                continue

            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            if len(approx) in [4, 8]:
                rect = cv2.minAreaRect(c)
                (x, y), (w, h), angle = rect
                box = cv2.boxPoints(rect)
                box = np.intp(box)
                cv2.drawContours(orig, [box], 0, (0, 255, 0), 2)

                l = max(w, h) * MM_PER_PIXEL
                b = min(w, h) * MM_PER_PIXEL
                _last_dimensions = (round(l, 1), round(b, 1))
                _last_detected_time = time.time()
                detected = True

                cv2.putText(
                    orig,
                    f"LxB: {round(l,1)} x {round(b,1)} mm",
                    (int(x), int(y)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )
                break

        # reset na 3 seconden geen contour
        if not detected and time.time() - _last_detected_time > 3:
            _last_dimensions = None

        if not _last_dimensions:
            log = "⚠️ Geen geschikte contour gemeten"
            return 0, 0, 0, None, False, log, frame

        l, b = _last_dimensions
        height = get_latest_height()
        if height is None:
            log = "⚠️ Geen hoogte gemeten"
            return l, b, 0, None, False, log, orig

        h = round(height, 1)
        matched_id, ok = match_dimensions(l, b, h)

        log = f"✅ Gedetecteerd: L={l:.1f}, B={b:.1f}, H={h:.1f}, match={matched_id or 'geen'}"
        return l, b, h, matched_id, ok, log, orig

    except Exception as e:
        log = f"❌ Fout tijdens detectie: {e}"
        return 0, 0, 0, None, False, log, frame
