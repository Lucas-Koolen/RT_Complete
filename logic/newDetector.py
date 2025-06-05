import cv2
import numpy as np
import time
from config.config import MM_PER_PIXEL
from logic.newHeightSensor import get_latest_height

# Global variables (make sure these are initialized somewhere in your module)
_last_dimensions = None
_last_detected_time = 0.0

def detect_dimensions(frame):
    global _last_dimensions, _last_detected_time
    log = ""
    
    try:
        orig = frame.copy()

        # --- 1) Pre‐process color image exactly as in C++ (bilateral filter) ---
        # (C++: bilateralFilter(colorMat, filteredColorMat, 9, 75, 75))
        filtered = cv2.bilateralFilter(orig, d=9, sigmaColor=75, sigmaSpace=75)

        # --- 2) EDGE DETECTION FOR RECTANGLES (Canny) ---
        gray_filt = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_filt, threshold1=50, threshold2=150)

        # --- 3) FIND CONTOURS & APPROXIMATE POLYGONS ---
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # We'll keep a list of "detected rectangles" (center, size_in_pixels)
        rectangles = []

        for cnt in contours:
            # Approximate polygon for each contour
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon=0.02 * peri, closed=True)

            # Only consider contours that have 4 (or nearly‐4) corners
            if len(approx) == 4:
                # Compute minimum‐area rectangle
                rect = cv2.minAreaRect(approx)
                (cx, cy), (w, h), angle = rect

                # Filter out too‐small "rectangles" (same as C++: area < 50 px^2)
                if w * h < 50:
                    continue

                # Convert size to millimeters (using your MM_PER_PIXEL constant)
                length_mm = max(w, h) * MM_PER_PIXEL
                breadth_mm = min(w, h) * MM_PER_PIXEL

                # Draw the green bounding box in orig
                box_pts = cv2.boxPoints(rect).astype(np.int32)
                cv2.drawContours(orig, [box_pts], contourIdx=0, color=(0, 255, 0), thickness=2)

                # Save this rectangle's center + size (in pixels) for overlap checks later
                rectangles.append({
                    "center": (cx, cy),
                    "width_px": w,
                    "height_px": h,
                    "length_mm": round(length_mm, 1),
                    "breadth_mm": round(breadth_mm, 1)
                })

                # For this example, we break after the first valid rectangle,
                # similar to your existing code’s “break once detected”
                _last_dimensions = (round(length_mm, 1), round(breadth_mm, 1))
                _last_detected_time = time.time()
                detected = True
                break
        else:
            detected = False

        # Reset dimensions if nothing detected for >3 seconds (same logic you already had)
        if not detected:
            if time.time() - _last_detected_time > 3:
                _last_dimensions = None

        # If we still have no dimensions, immediately return with a warning
        if not _last_dimensions:
            log = "⚠️ Geen geschikte rechthoek of cirkel gevonden"
            return 0, 0, 0, None, False, log, frame

        # --- 4) If we did detect a rectangle, we could also attempt CIRCLE DETECTION ---
        #    (only if you care about circles; otherwise you can skip this entire block)

        # Convert to gray & blur (similar to C++ before HoughCircles)
        gray_circle = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
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
                cv2.circle(orig, (cir_cx, cir_cy), cir_r, (0, 0, 255), 2)
                cv2.circle(orig, (cir_cx, cir_cy), 2, (255, 0, 0), 2)

                # Save circle info (in pixels → mm)
                circles.append({
                    "center": (cir_cx, cir_cy),
                    "radius_px": cir_r,
                    "radius_mm": round(cir_r * MM_PER_PIXEL, 1)
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
            return l, b, 0, None, False, log, orig

        h_mm = round(height, 1)
        matched_id, ok = None, False  # Placeholder: you can insert your own matching logic here

        # If you did detect a circle and want to report it, you could override l/b (optional)
        if circles:
            c = circles[0]
            # For example, you could display “Diameter: X mm” instead of length × breadth
            dia = round(2 * c["radius_mm"], 1)
            log = f"✅ Cirkel gedetecteerd: Diameter={dia:.1f} mm, H={h_mm:.1f} mm, match={matched_id or 'geen'}"
        else:
            log = f"✅ Rechthoek gedetecteerd: L={l:.1f} mm × B={b:.1f} mm, H={h_mm:.1f} mm, match={matched_id or 'geen'}"

        return l, b, h_mm, matched_id, ok, log, orig

    except Exception as e:
        log = f"❌ Fout tijdens detectie: {e}"
        return 0, 0, 0, None, False, log, frame
