import ctypes
import numpy as np
import cv2
import os, sys
import time

from hikvision_sdk.MvCameraControl_class import *
from config.config import *

def enum_cameras():
    device_list = MV_CC_DEVICE_INFO_LIST()
    tlayer_type = MV_USB_DEVICE
    temp_cam = MvCamera()
    nRet = temp_cam.MV_CC_EnumDevices(tlayer_type, device_list)
    if nRet != 0 or device_list.nDeviceNum == 0:
        print("❌ Geen camera's gevonden")
        return None

    print(f"✅ {device_list.nDeviceNum} camera('s) gevonden:")
    for i in range(device_list.nDeviceNum):
        dev = device_list.pDeviceInfo[i].contents
        if dev.nTLayerType == MV_USB_DEVICE:
            model = bytes(dev.SpecialInfo.stUsb3VInfo.chModelName).decode('utf-8').strip('\x00')
            serial = bytes(dev.SpecialInfo.stUsb3VInfo.chSerialNumber).decode('utf-8').strip('\x00')
            print(f"  [{i}] USB | Model: {model} | Serienummer: {serial}")
    return device_list.pDeviceInfo[0].contents

def setup_camera(cam):
    cam.MV_CC_SetEnumValue("PixelFormat", PIXEL_FORMAT)
    cam.MV_CC_SetEnumValue("ExposureAuto", 0)
    cam.MV_CC_SetFloatValue("ExposureTime", EXPOSURE_TIME)
    cam.MV_CC_SetFloatValue("Gain", GAIN)

def start_stream(callback):
    print("🔄 Start streamfunctie")
    cam = MvCamera()

    device_info = enum_cameras()
    if not device_info:
        print("❌ Geen camera gevonden bij herstart")
        return

    if cam.MV_CC_CreateHandle(device_info) != 0:
        print("❌ CreateHandle mislukt")
        return
    if cam.MV_CC_OpenDevice() != 0:
        print("❌ OpenDevice mislukt")
        return

    setup_camera(cam)
    time.sleep(0.5)

    if cam.MV_CC_StartGrabbing() != 0:
        print("❌ Start grabbing mislukt")
        return

    print("✅ Camera grabbing gestart")

    buffer_size = FRAME_WIDTH * FRAME_HEIGHT * 3
    data_buf = (ctypes.c_ubyte * buffer_size)()
    frame_info = MV_FRAME_OUT_INFO_EX()

    while True:
        nRet = cam.MV_CC_GetImageForBGR(data_buf, buffer_size, frame_info, 1000)
        if nRet == 0:
            np_buf = np.frombuffer(data_buf, dtype=np.uint8)
            if np_buf.size != FRAME_WIDTH * FRAME_HEIGHT * 3:
                print("⚠️ Ongeldige buffer size ontvangen")
                continue

            frame = np_buf.reshape((FRAME_HEIGHT, FRAME_WIDTH, 3))
            if np.count_nonzero(frame) < 100:
                print("⚠️ Leeg beeld, frame wordt overgeslagen")
                continue

            try:
                output = callback(frame)
            except Exception as e:
                print(f"⚠️ Callbackfout: {e}")
        else:
            print(f"❌ Fout bij beeld ophalen: code {nRet}")

        if cv2.waitKey(1) == 27:
            break

    cam.MV_CC_StopGrabbing()
    cam.MV_CC_CloseDevice()
    cam.MV_CC_DestroyHandle()
    print("✅ Camera afgesloten")
