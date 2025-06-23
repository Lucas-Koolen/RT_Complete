import cv2
import numpy as np
from config.config import MM_PER_PIXEL, PROCESS_SCALE
from helpers.shape import Shape
from interfaces.dbConnector import DatabaseConnector
from interfaces.serialCommunicator import SerialCommunicator

# Global variables (make sure these are initialized somewhere in your module)
_last_dimensions = None
_last_detected_time = 0.0

def detect_dimensions(frame, dataBase: DatabaseConnector, communicator: SerialCommunicator):
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

                length_mm = l / scale * MM_PER_PIXEL
                width_mm = w / scale * MM_PER_PIXEL

                rectangles.append({
                    "rect": rect,
                    "angle": angle,
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
                    if dist < max(r["width_px"], r["length_px"]) / 2 + cir_r:
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
        
        height = communicator.get_height()
        #height = 0  # For testing purposes, we set height to 0

        if height is None:
            log = "⚠️ Geen hoogte gemeten"
            return 0, 0, 0, 0, 0, 0, Shape.INVALID, None, False, log, return_frame

        h_mm = round(height, 1)

        shape = None

        # find object with lowest Y-center coordinate
        rightMostShape = None
        if rectangles:
            rightMostShape = max(rectangles, key=lambda r: r["center"][1])
            shape = Shape.BOX
        if circles:
            rightMostCircle = max(circles, key=lambda c: c["center"][1])
            if rightMostShape is None or rightMostCircle["center"][1] > rightMostShape["center"][1]:
                rightMostShape = rightMostCircle
                shape = Shape.CYLINDER
        
        if rightMostShape is None:
            log = "❌ No shape detected"
            return 0, 0, 0, 0, 0, 0, Shape.INVALID, None, False, log, return_frame
        
        l, w, angle = None, None, None

        if shape == Shape.BOX:
            box_pts_one = cv2.boxPoints(rightMostShape["rect"])
            boundingBox = cv2.boundingRect(box_pts_one.astype(np.int32))
            boundingBox
            if (boundingBox[2] > boundingBox[3] and rightMostShape["width_px"] < rightMostShape["length_px"]) or (boundingBox[2] < boundingBox[3] and rightMostShape["width_px"] > rightMostShape["length_px"]):
                l = rightMostShape["width_mm"]
                w = rightMostShape["length_mm"]
                angle = rightMostShape["angle"] + 90
            else:
                l = rightMostShape["length_mm"]
                w = rightMostShape["width_mm"]
                angle = rightMostShape["angle"]

            if angle > 90:
                angle = angle - 180
            elif angle < -90:
                angle = angle + 180

            box_pts = cv2.boxPoints(rightMostShape["rect"]) / scale
            cv2.drawContours(return_frame, [box_pts.astype(np.int32)], 0, (0, 255, 0), 2)
            #also draw bounding box
            cv2.rectangle(return_frame, (int(boundingBox[0] / scale), int(boundingBox[1] / scale)), 
                          (int((boundingBox[0] + boundingBox[2]) / scale), int((boundingBox[1] + boundingBox[3]) / scale)), 
                          (255, 0, 0), 2)
        elif shape == Shape.CYLINDER:
            angle = 0  # Not used for circles
            l, w = rightMostShape["radius_mm"] * 2, rightMostShape["radius_mm"] * 2
            cv2.circle(return_frame, (int(cir_cx / scale), int(cir_cy / scale)), int(cir_r / scale), (0, 0, 255), 2)
            cv2.circle(return_frame, (int(cir_cx / scale), int(cir_cy / scale)), 2, (255, 0, 0), 2)

        matched_id, target_l, target_w, target_h, ok = dataBase.find_best_match(l, w, h_mm, shape)

        log = f"✅ Vorm gedetecteerd: L={l:.1f} mm × W={w:.1f} mm, H={h_mm:.1f} mm, shape={shape.shapeToString()}, match={matched_id or 'geen'}"

        centerX = int(rightMostShape["center"][0] / scale)
        centerY = int(rightMostShape["center"][1] / scale)

        return l, w, h_mm, centerX, centerY, angle, shape, matched_id, ok, target_l, target_w, target_h, log, return_frame

    except Exception as e:
        log = f"❌ Fout tijdens detectie: {e}"
        return 0, 0, 0, 0, 0, 0, Shape.INVALID, None, False, log, return_frame
