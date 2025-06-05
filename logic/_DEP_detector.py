# logic/detector.py

import cv2
import numpy as np
from config.config import PIXEL_TO_MM
from hikvision_sdk.MvCameraControl_class import MvCamera

class CameraDetector:
    def __init__(self):
        self.cam = None
        self.cap = None

        # Try initializing Hikvision SDK first
        try:
            self.cam = MvCamera()
            device_list = self.cam.EnumDevices()
            if device_list:
                self.cam.Open(device_list[0])
                self.cam.StartGrabbing()
            else:
                self.cam = None
                print("[CAMERA] Geen Hikvision-camera gevonden.")
        except Exception as exc:
            print(f"[CAMERA] Hikvision SDK-fout: {exc}")
            self.cam = None

        # Fallback to OpenCV when Hikvision is not available
        if not self.cam:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                print("[CAMERA] OpenCV fallback geactiveerd.")
            else:
                print("[CAMERA] Geen camera gevonden.")
                self.cap = None

    def get_frame(self):
        # Try Hikvision first
        if self.cam:
            try:
                data, frame = self.cam.GetFrameWithRGB()
                if frame is not None:
                    processed = self.process_frame(frame.copy())
                    return processed["visual"], processed["dimensions"]
            except Exception as exc:
                print(f"[CAMERA] Hikvision framefout: {exc}")
                self.cam = None
                # initialize fallback if not yet active
                if not self.cap:
                    self.cap = cv2.VideoCapture(0)
                    if self.cap.isOpened():
                        print("[CAMERA] OpenCV fallback geactiveerd.")
                    else:
                        print("[CAMERA] Geen camera gevonden.")
                        self.cap = None

        if not self.cap:
            return None, None

        ret, frame = self.cap.read()
        if not ret:
            return None, None

        processed = self.process_frame(frame.copy())
        return processed['visual'], processed['dimensions']

    def process_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        edged = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_box = None
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 10000:  # filter ruis
                rect = cv2.minAreaRect(cnt)
                box = cv2.boxPoints(rect)
                box = np.int8(box)
                w, h = rect[1]
                if w > 0 and h > 0:
                    l_mm = max(w, h) * PIXEL_TO_MM
                    b_mm = min(w, h) * PIXEL_TO_MM
                    best_box = (box, (round(l_mm, 1), round(b_mm, 1)))
                    break

        if best_box:
            cv2.drawContours(frame, [best_box[0]], 0, (0, 255, 0), 2)
            l, b = best_box[1]
            cv2.putText(frame, f"{l}x{b} mm", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
            return {"visual": cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), "dimensions": best_box[1]}
        else:
            return {"visual": cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), "dimensions": None}
