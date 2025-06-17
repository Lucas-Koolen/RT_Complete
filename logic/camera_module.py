import ctypes
import numpy as np
import time

from hikvision_sdk.MvCameraControl_class import *
from config.config import *

def enum_cameras(cam):
    device_list = MV_CC_DEVICE_INFO_LIST()
    tlayer_type = MV_USB_DEVICE
    nRet = cam.MV_CC_EnumDevices(tlayer_type, device_list)
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
    #cam.MV_CC_SetFloatValue("Gain", GAIN)

def start_stream(cam):
    print("🔄 Start streamfunctie")

    device_info = enum_cameras(cam)
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

def get_frame(cam):
    buffer_size = FRAME_WIDTH * FRAME_HEIGHT * 3
    data_buf = (ctypes.c_ubyte * buffer_size)()
    frame_info = MV_FRAME_OUT_INFO_EX()

    nRet = cam.MV_CC_GetImageForBGR(data_buf, buffer_size, frame_info, 1000)
    if nRet == 0:
        np_buf = np.frombuffer(data_buf, dtype=np.uint8)
        if np_buf.size != FRAME_WIDTH * FRAME_HEIGHT * 3:
            print("⚠️ Ongeldige buffer size ontvangen")
            return None

        frame = np_buf.reshape((FRAME_HEIGHT, FRAME_WIDTH, 3))
        if np.count_nonzero(frame) < 100:
            print("⚠️ Leeg beeld, frame wordt overgeslagen")
            return None

        return frame
    else:
        print(f"❌ Fout bij beeld ophalen: code {nRet}")
        return None
        


def stop_stream(cam):
    cam.MV_CC_StopGrabbing()
    cam.MV_CC_CloseDevice()
    cam.MV_CC_DestroyHandle()
    print("✅ Camera afgesloten")
