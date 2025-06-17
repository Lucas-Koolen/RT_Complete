import cv2
import numpy as np
import time
from config.config import MM_PER_PIXEL, PROCESS_SCALE
from logic.newHeightSensor import get_latest_height
from logic.shape import Shape
from logic.db_connector import DatabaseConnector

# Global variables (make sure these are initialized somewhere in your module)
_last_dimensions = None
_last_detected_time = 0.0

def detect_dimensions(frame, dataBase: DatabaseConnector):
    global _last_dimensions, _last_detected_time
    log = ""

    return_frame = frame.copy()  # Keep original frame for drawing contours
    return_frame = cv2.cvtColor(return_frame, cv2.COLOR_BGR2GRAY)  # Convert to RGB for display

    try:
        # Optionally resize frame for faster processing
        scale = PROCESS_SCALE if PROCESS_SCALE > 0 else 1.0
        proc = (
            cv2.resize(frame, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            if scale != 1.0
            else frame
        )

        # median filter on image
        proc = cv2.medianBlur(proc, 5)

        # --- 1) Pre‐process color image exactly as in C++ (bilateral filter) ---
        filtered = cv2.bilateralFilter(proc, d=9, sigmaColor=75, sigmaSpace=75)

        # make image binary
        filtered = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
        _, filtered = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        orig = filtered.copy()  # Keep original for drawing contours

        # --- 2) EDGE DETECTION FOR RECTANGLES (Canny) ---
        #gray_filt = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
        gray_filt = filtered  # Already in grayscale after thresholding
        edges = cv2.Canny(gray_filt, threshold1=50, threshold2=150)

        # --- 3) FIND CONTOURS & APPROXIMATE POLYGONS ---
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # Keep track of the largest suitable rectangle
        largest_rect = None
        max_area = 0
        rectangles = []

        for cnt in contours:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            if len(approx) == 4:
                rect = cv2.minAreaRect(approx)
                (cx, cy), (w, h), angle = rect
                area = w * h
                if area < 400:
                    continue
                if area > max_area:
                    max_area = area
                    largest_rect = rect

        if largest_rect is not None:
            (cx, cy), (w, h), angle = largest_rect
            length_mm = max(w, h) / scale * MM_PER_PIXEL
            breadth_mm = min(w, h) / scale * MM_PER_PIXEL
            box_pts = cv2.boxPoints(largest_rect) / scale
            cv2.drawContours(orig, [box_pts.astype(np.int32)], 0, (0, 255, 0), 2)
            rectangles.append({
                "center": (cx / scale, cy / scale),
                "width_px": w / scale,
                "height_px": h / scale,
                "length_mm": round(length_mm, 1),
                "breadth_mm": round(breadth_mm, 1),
            })
            _last_dimensions = (round(length_mm, 1), round(breadth_mm, 1))
            _last_detected_time = time.time()
            detected = True
        else:
            detected = False

        # Reset dimensions if nothing detected for >3 seconds (same logic you already had)
        if not detected:
            if time.time() - _last_detected_time > 3:
                _last_dimensions = None

        # If we still have no dimensions, immediately return with a warning
        if not _last_dimensions:
            log = "⚠️ Geen geschikte rechthoek of cirkel gevonden"
            return 0, 0, 0, Shape.INVALID, None, False, log, return_frame

        # --- 4) If we did detect a rectangle, we could also attempt CIRCLE DETECTION ---
        #    (only if you care about circles; otherwise you can skip this entire block)

        # Convert to gray & blur (similar to C++ before HoughCircles)
        #gray_circle = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
        gray_circle = filtered
        gray_circle = cv2.GaussianBlur(gray_circle, (9, 9), sigmaX=2, sigmaY=2)

        # HoughCircles parameters as in C++: (dp=1, minDist=rows/8, param1=100, param2=30, minRadius=5)
        detected_circles = cv2.HoughCircles(
            gray_circle,
            method=cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=gray_circle.shape[0] / 8,
            param1=100,
            param2=30,
            minRadius=5,
            maxRadius=0
        )

        circles = []
        if detected_circles is not None:
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

                # Draw circle in red, center dot in blue
                cv2.circle(orig, (int(cir_cx / scale), int(cir_cy / scale)), int(cir_r / scale), (0, 0, 255), 2)
                cv2.circle(orig, (int(cir_cx / scale), int(cir_cy / scale)), 2, (255, 0, 0), 2)

                # Save circle info (in pixels → mm)
                circles.append({
                    "center": (cir_cx / scale, cir_cy / scale),
                    "radius_px": cir_r / scale,
                    "radius_mm": round((cir_r / scale) * MM_PER_PIXEL, 1)
                })

                # If you only want to handle one circle (like you do one rectangle), break
                break

        # --- 5) COMBINE WITH HEIGHT SENSOR & LOGGING ---
        l, b = _last_dimensions  # rectangle dims in mm
        height = get_latest_height()  # same as your original
        if height is None:
            log = "⚠️ Geen hoogte gemeten"
            # We still return the original image with rectangles/circles drawn
            # For height=0, the return signature is (l, b, 0, None, False, log, orig)
            return l, b, 0, Shape.INVALID, None, False, log, orig

        h_mm = round(height, 1)

        shape = Shape.BOX  # Default shape is box; change if you detect a circle

        # If you did detect a circle and want to report it, you could override l/b (optional)
        if circles:
            c = circles[0]
            # For example, you could display “Diameter: X mm” instead of length × breadth
            dia = round(2 * c["radius_mm"], 1)
            shape = Shape.CYLINDER
            l, b = dia, dia

        #matched_id, ok = None, False  # Placeholder: you can insert your own matching logic here
        matched_id, ok = dataBase.find_best_match(l, b, h_mm, shape)

        log = f"✅ Vorm gedetecteerd: L={l:.1f} mm × B={b:.1f} mm, H={h_mm:.1f} mm, shape={shape.shapeToString()}, match={matched_id or 'geen'}"

        return l, b, h_mm, shape, matched_id, ok, log, orig

    except Exception as e:
        log = f"❌ Fout tijdens detectie: {e}"
        return 0, 0, 0, Shape.INVALID, None, False, log, return_frame
