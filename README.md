# 📦 Rotation Table – Detectie & Aansturing

Een geavanceerd systeem voor het detecteren, herkennen en oriënteren van dozen met behulp van een 2D-camera, hoogte-uitlezing via VL53L1X, en automatische aansturing van servomotoren. Het systeem vergelijkt gemeten dozen met een centrale MySQL-database en stuurt automatisch een rotatiesequentie naar een Arduino-platform.

---

## 🔧 Functionaliteiten

### ✅ Live Detectie & Matching
- Realtime camera feed + bounding box
- L×B meting via beeldverwerking (OpenCV + Hikvision SDK)
- Hoogte uitlezing via VL53L1X sensor op Arduino
- Matcht doos tegen een MySQL-database (`status = 'unprocessed'`)
- Houdt rekening met oriëntatie (ook omgewisselde L/B)

### ✅ Automatische Aansturing
- Berekening van rotatiesequentie naar gewenste eindpositie
- Seriële communicatie met Arduino
- Doos wordt automatisch gemarkeerd als `processed` in database

### ✅ Handmatige Bediening
- Los tabblad voor handmatige motorsturing (pusher, draaitafel, etc.)
- Directe Arduino-commando’s via UI
- Logging van commando's en status

---

## 🗂 Projectstructuur

```bash
RT_COMPLETE/
│
├── main.py                  # Startpunt applicatie
├── dashboard.py             # UI met auto & manual modus
│
├── config/
│   └── config.py            # Instellingen (MySQL, COM, tolerantie)
│
├── logic/
│   ├── detector.py          # Camera + LxB meting
│   ├── height_sensor.py     # Hoogte uitlezing Arduino
│   ├── db_connector.py      # MySQL verbinding & matching
│   ├── rotation_logic.py    # Berekening rotatiesequentie
│   └── serial_comm.py       # Seriële communicatie Arduino
│
├── arduino/
│   └── RotationSystem_Combined.ino  # 1 Arduino sketch voor alles
│
├── hikvision_sdk/           # SDK-bestanden voor cameracontrole
│   └── ...
│
└── .vscode/
    └── launch.json          # Startconfiguratie voor VS Code
