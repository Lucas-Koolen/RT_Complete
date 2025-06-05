import cv2
import numpy as np

def calculate_scale_from_reference(frame):
    print("🧪 Start schaalberekening op basis van referentie")

    h, w = frame.shape[:2]
    crop_w, crop_h = 640, 480
    x1 = w // 2 - crop_w // 2
    y1 = h // 2 - crop_h // 2
    crop = frame[y1:y1+crop_h, x1:x1+crop_w]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 3)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_contour = None
    best_area = float("inf")

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 100 or area > 4000:
            continue

        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        if len(approx) != 4:
            continue

        x, y, cw, ch = cv2.boundingRect(approx)
        aspect_ratio = cw / ch
        if 0.8 < aspect_ratio < 1.2 and area < best_area:
            best_contour = (x, y, cw, ch)
            best_area = area

    if best_contour:
        x, y, cw, ch = best_contour
        mm_per_pixel = 10 / cw  # 10mm referentie

        abs_x, abs_y = x1 + x, y1 + y
        cv2.rectangle(frame, (abs_x, abs_y), (abs_x + cw, abs_y + ch), (255, 255, 255), 2)
        cv2.putText(frame, "10mm ref", (abs_x, abs_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        print(f"✅ Pixelschaal berekend: {mm_per_pixel:.4f} mm/pixel")
        return mm_per_pixel, frame

    print("⚠️ Geen referentie gevonden in beeld")
    return None, frame
