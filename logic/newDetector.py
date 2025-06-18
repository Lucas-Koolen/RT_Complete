import cv2
import numpy as np
from config.config import MM_PER_PIXEL, PROCESS_SCALE
from logic.shape import Shape
from logic.db_connector import DatabaseConnector
from logic.communicator import Communicator

# Global variables (make sure these are initialized somewhere in your module)
_last_dimensions = None
_last_detected_time = 0.0

def detect_dimensions(frame, dataBase: DatabaseConnector, communicator: Communicator):
    global _last_dimensions, _last_detected_time
    log = ""

    return_frame = frame.copy()  # Keep original frame for drawing contours

    try:
        # Optionally resize frame for faster processing
        scale = PROCESS_SCALE if PROCESS_SCALE > 0 else 1.0
        proc = (
            cv2.resize(frame, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            if scale != 1.0
            else frame
        )

        # median filter on image
        filtered = cv2.medianBlur(proc, 9)

        # make image binary
        filtered = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)

        # uncomment if calibrating threshold value is needed
        #thresholdValue, filtered = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # use static threshold value for consistency
        thresholdValue = 30
        _, filtered = cv2.threshold(filtered, thresholdValue, 255, cv2.THRESH_BINARY)

        #print(f"Threshold value used: {thresholdValue}")

        orig = filtered.copy()  # Keep original for drawing contours

        # --- 2) EDGE DETECTION FOR RECTANGLES (Canny) ---
        edges = cv2.Canny(filtered, threshold1=50, threshold2=150)

        # --- 3) FIND CONTOURS & APPROXIMATE POLYGONS ---
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        rectangles = []

        for cnt in contours:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            if len(approx) == 4:
                rect = cv2.minAreaRect(approx)
                (cx, cy), (w, l), angle = rect
                area = w * l
                if area < 400:
                    continue

                length_mm = max(w, l) / scale * MM_PER_PIXEL
                width_mm = min(w, l) / scale * MM_PER_PIXEL

                rectangles.append({
                    "rect": rect,
                    "center": (cx / scale, cy / scale),
                    "width_px": w / scale,
                    "length_px": l / scale,
                    "length_mm": round(length_mm, 1),
                    "width_mm": round(width_mm, 1),
                })

        # Detect circles using Hough Transform
        filtered = cv2.GaussianBlur(filtered, (9, 9), sigmaX=2, sigmaY=2)
        detected_circles = cv2.HoughCircles(
            filtered,
            method=cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=filtered.shape[0] / 8,
            param1=150,
            param2=30,
            minRadius=5,
            maxRadius=0
        )

        circles = []
        if detected_circles is not None:
            print(f"Detected {len(detected_circles[0])} circles")
            detected_circles = np.uint16(np.around(detected_circles))
            for vc in detected_circles[0, :]:
                cir_cx, cir_cy, cir_r = vc
                # Check overlap with any rectangle (distance center‐to‐center < rectangle diag/2)
                overlaps_rect = False
                for r in rectangles:
                    rx, ry = r["center"]
                    dist = np.hypot(rx - cir_cx, ry - cir_cy)
                    if dist < max(r["width_px"], r["height_px"]) / 2 + cir_r:
                        overlaps_rect = True
                        break
                if overlaps_rect:
                    continue

                # Save circle info (in pixels → mm)
                circles.append({
                    "center": (cir_cx / scale, cir_cy / scale),
                    "radius_px": cir_r / scale,
                    "radius_mm": round((cir_r / scale) * MM_PER_PIXEL, 1)
                })

        # --- 5) COMBINE WITH HEIGHT SENSOR & LOGGING ---
        
        #height = communicator.get_height()
        height = 0  # For testing purposes, we set height to 0

        if height is None:
            log = "⚠️ Geen hoogte gemeten"
            return 0, 0, 0, Shape.INVALID, None, False, log, return_frame

        h_mm = round(height, 1)

        shape = None

        # find object with lowest Y-center coordinate
        rightMostShape = None
        if rectangles:
            rightMostShape = min(rectangles, key=lambda r: r["center"][1])
            shape = Shape.BOX
        if circles:
            rightMostCircle = min(circles, key=lambda c: c["center"][1])
            if rightMostShape is None or rightMostCircle["center"][1] < rightMostShape["center"][1]:
                rightMostShape = rightMostCircle
                shape = Shape.CYLINDER
        
        if rightMostShape is None:
            log = "❌ No shape detected"
            return 0, 0, 0, Shape.INVALID, None, False, log, return_frame
        
        l, w = None, None

        if shape == Shape.BOX:
            l, w = rightMostShape["length_mm"], rightMostShape["width_mm"]
            box_pts = cv2.boxPoints(rightMostShape["rect"]) / scale
            cv2.drawContours(return_frame, [box_pts.astype(np.int32)], 0, (0, 255, 0), 2)
        elif shape == Shape.CYLINDER:
            l, w = rightMostShape["radius_mm"] * 2, rightMostShape["radius_mm"] * 2
            cv2.circle(return_frame, (int(cir_cx / scale), int(cir_cy / scale)), int(cir_r / scale), (0, 0, 255), 2)
            cv2.circle(return_frame, (int(cir_cx / scale), int(cir_cy / scale)), 2, (255, 0, 0), 2)

        matched_id, ok = dataBase.find_best_match(l, w, h_mm, shape)

        log = f"✅ Vorm gedetecteerd: L={l:.1f} mm × W={w:.1f} mm, H={h_mm:.1f} mm, shape={shape.shapeToString()}, match={matched_id or 'geen'}"

        return l, w, h_mm, shape, matched_id, ok, log, return_frame

    except Exception as e:
        log = f"❌ Fout tijdens detectie: {e}"
        return 0, 0, 0, Shape.INVALID, None, False, log, return_frame
