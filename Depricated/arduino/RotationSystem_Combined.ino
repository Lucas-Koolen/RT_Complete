#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include "Adafruit_VL53L1X.h"

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();
Adafruit_VL53L1X vl53 = Adafruit_VL53L1X();

#define SERVO_STOP_DEFAULT 365
#define SERVO_STOP_SERVO5 367
#define SERVO_STOP_SERVO6 365
#define SERVO_STOP_SERVO7 368
#define SERVO_PWM_MOVE 200
#define POS_MIN 90
#define POS_MAX 530

#define PUSHER1_ENDSTOP_PIN 8  // NC
#define PUSHER2_ENDSTOP_PIN 9  // NC
#define BEAM_SENSOR1_PIN 4     // NO (LOW = gebroken)
#define BEAM_SENSOR2_PIN 5     // NO (LOW = gebroken)

int custom_pwm[9] = {
  SERVO_STOP_DEFAULT, // 0 - Lopende Band 1
  SERVO_STOP_DEFAULT, // 1 - Draaitafel 1
  SERVO_STOP_DEFAULT, // 2 - Pusher 1
  SERVO_STOP_DEFAULT, // 3 - L1
  SERVO_STOP_DEFAULT, // 4 - L2
  SERVO_STOP_SERVO5,  // 5 - Lopende Band 2
  SERVO_STOP_SERVO6,  // 6 - Pusher 2
  SERVO_STOP_SERVO7,  // 7 - Draaitafel 2
  SERVO_STOP_DEFAULT  // 8 - Reserve
};

String incoming = "";
unsigned long lastHeightTime = 0;
const int HEIGHT_INTERVAL_MS = 200;

void setup() {
  Serial.begin(9600);
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(50);

  pinMode(PUSHER1_ENDSTOP_PIN, INPUT_PULLUP);
  pinMode(PUSHER2_ENDSTOP_PIN, INPUT_PULLUP);
  pinMode(BEAM_SENSOR1_PIN, INPUT_PULLUP);
  pinMode(BEAM_SENSOR2_PIN, INPUT_PULLUP);

  // Set all motors to stop
  for (int i = 0; i < 9; i++) {
    pwm.setPWM(i, 0, custom_pwm[i]);
  }

  // VL53L1X Init
  if (!vl53.begin(0x29, &Wire)) {
    Serial.println("ERROR: Failed to initialize VL53L1X");
    while (1);
  }
  vl53.setDistanceMode(VL53L1X::LONG);
  vl53.setMeasurementTimingBudget(50000);
  vl53.startRanging();

  delay(500);
  Serial.println("READY");
}

void loop() {
  // Commando verwerken
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      handleCommand(incoming);
      incoming = "";
    } else {
      incoming += c;
    }
  }

  // Hoogtemeting periodiek verzenden
  if (millis() - lastHeightTime > HEIGHT_INTERVAL_MS) {
    if (vl53.dataReady()) {
      uint16_t distance = vl53.read();
      Serial.print("HEIGHT:");
      Serial.println(distance);
      vl53.clearInterrupt();
    }
    lastHeightTime = millis();
  }
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.startsWith("SET")) {
    int index = cmd.substring(4, 5).toInt();
    String dir = cmd.substring(6);
    if (dir == "FWD") pwm.setPWM(index, 0, SERVO_PWM_MOVE);
    else if (dir == "REV") pwm.setPWM(index, 0, 600 - SERVO_PWM_MOVE);
    else pwm.setPWM(index, 0, custom_pwm[index]);
    Serial.println("INFO:SET OK");
  } else if (cmd.startsWith("ROTATE")) {
    int index = cmd.substring(7, 8).toInt();
    String dir = cmd.substring(9);
    if (dir == "FWD") pwm.setPWM(index, 0, SERVO_PWM_MOVE);
    else if (dir == "REV") pwm.setPWM(index, 0, 600 - SERVO_PWM_MOVE);
    else pwm.setPWM(index, 0, custom_pwm[index]);
    Serial.println("INFO:ROTATE OK");
  } else if (cmd.startsWith("CAL")) {
    int index = cmd.substring(4).toInt();
    custom_pwm[index] = pwmRead(index); // placeholder voor echte kalibratie
    Serial.print("INFO:CALIBRATED ");
    Serial.println(index);
  } else if (cmd == "STATUS") {
    Serial.print("STOP2:");
    Serial.println(digitalRead(PUSHER2_ENDSTOP_PIN) == LOW ? "Pressed" : "Not pressed");
    Serial.print("b10:");
    Serial.println(digitalRead(BEAM_SENSOR1_PIN) == LOW ? "Broken" : "Clear");
  } else {
    Serial.print("ERROR:Unknown command - ");
    Serial.println(cmd);
  }
}

int pwmRead(int index) {
  return custom_pwm[index]; // stub, kan aangepast worden voor echte uitlezing
}
