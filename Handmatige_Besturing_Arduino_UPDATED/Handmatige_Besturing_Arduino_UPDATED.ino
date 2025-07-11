#include <Wire.h>
#include <VL53L1X.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();
VL53L1X sensor;

struct ServoAction {
  unsigned long startTime;
  unsigned long duration;
  int active;
};

ServoAction servoActions[16];  // Max 16 servo's

struct FlipperMove {
  int servoNum;
  int startPulse;
  int targetPulse;
  unsigned long startTime;
  unsigned long duration;
  bool active;
};

FlipperMove flipperMoves[16];  // Max 16 flippers tegelijk

// Stopwaarden
#define SERVO_STOP_DEFAULT  365
#define SERVO_STOP_SERVO5   367
#define SERVO_STOP_SERVO6   366
#define SERVO_STOP_SERVO7   368

#define SERVO_PWM_MOVE      200
#define POS_MIN             90
#define POS_MAX             530

// --- Sensor pinmapping ---
#define PUSHER1_ENDSTOP_PIN 8    // NC
#define PUSHER2_ENDSTOP_PIN 9    // NC
#define BEAM_SENSOR1_PIN    4    // NO (LOW = gebroken)
#define BEAM_SENSOR2_PIN    5    // NO

int custom_pwm[9] = {
  SERVO_STOP_DEFAULT,  // 0 - Lopende Band 1
  SERVO_STOP_DEFAULT,  // 1 - Draaitafel 1
  SERVO_STOP_SERVO5,   // 2 - Pusher 1
  SERVO_STOP_DEFAULT,  // 3 - L1 (positioneel)
  SERVO_STOP_DEFAULT,  // 4 - L2 (positioneel)
  SERVO_STOP_SERVO5,   // 5 - Lopende Band 2 (gekalibreerd)
  SERVO_STOP_SERVO6,   // 6 - Pusher 2 (gekalibreerd)
  SERVO_STOP_SERVO7,   // 7 - Draaitafel 2 (aparte waarde)
  SERVO_STOP_DEFAULT   // 8 - Reserve / toekomstig gebruik
};

String inputString = "";
bool lastEndstop1 = false;
bool lastEndstop2 = false;
bool lastBeam1 = false;
bool lastBeam2 = false;

unsigned long lastHeightSendTime = 0;

void setup() {
  Serial.begin(9600);
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(60);

  pinMode(PUSHER1_ENDSTOP_PIN, INPUT_PULLUP);
  pinMode(PUSHER2_ENDSTOP_PIN, INPUT_PULLUP);
  pinMode(BEAM_SENSOR1_PIN, INPUT_PULLUP);
  pinMode(BEAM_SENSOR2_PIN, INPUT_PULLUP);

  lastEndstop1 = digitalRead(PUSHER1_ENDSTOP_PIN) == HIGH;
  lastEndstop2 = digitalRead(PUSHER2_ENDSTOP_PIN) == HIGH;
  lastBeam1 = digitalRead(BEAM_SENSOR1_PIN) == LOW;
  lastBeam2 = digitalRead(BEAM_SENSOR2_PIN) == LOW;

  sensor.setTimeout(500);
  if (!sensor.init()) {
    Serial.println("Sensor init mislukt!");
    while (true);
  }

  sensor.setDistanceMode(VL53L1X::Long);
  sensor.setMeasurementTimingBudget(50000);
  sensor.startContinuous(50);

  Serial.println("READY");
}

void loop() {
  updateHeight();
  checkBeamSensors();
  checkEndstops();
  handleSerial();
  handleServoActions();
  handleFlipperMoves();
}

void updateHeight() {
  if (millis() - lastHeightSendTime >= 500) {
    uint16_t d = sensor.read();
    if (!sensor.timeoutOccurred()) {
      Serial.print("HT ");
      Serial.println(d);
    }
    lastHeightSendTime = millis();
  }
}

void checkBeamSensors() {
  bool currentBeam1 = digitalRead(BEAM_SENSOR1_PIN) == LOW;
  bool currentBeam2 = digitalRead(BEAM_SENSOR2_PIN) == LOW;

  if (currentBeam1 != lastBeam1) {
    lastBeam1 = currentBeam1;
    Serial.println(currentBeam1 ? "b11" : "b10");
  }
  if (currentBeam2 != lastBeam2) {
    lastBeam2 = currentBeam2;
    Serial.println(currentBeam2 ? "b21" : "b20");
  }
}

void checkEndstops() {
  bool current1 = digitalRead(PUSHER1_ENDSTOP_PIN) == HIGH;
  bool current2 = digitalRead(PUSHER2_ENDSTOP_PIN) == HIGH;

  if (!lastEndstop1 && current1) {
    if (servoActions[2].active != 1) {
      pwm.setPWM(2, 0, custom_pwm[2]);
      servoActions[2].active = 0;  // Reset action state
    }
    Serial.println("STOP2");
  }
  if (lastEndstop1 && !current1) {
    Serial.println("GO2");
  }

  if (!lastEndstop2 && current2) {
    if (servoActions[6].active != 1) {
      pwm.setPWM(6, 0, custom_pwm[6]);
      servoActions[6].active = 0;  // Reset action state
    }
    Serial.println("STOP6");
  }
  if (lastEndstop2 && !current2) {
    Serial.println("GO6");
  }

  lastEndstop1 = current1;
  lastEndstop2 = current2;
}

void handleSerial() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n' || inChar == '\r') {
      processCommand(inputString);
      inputString = "";
    } else {
      inputString += inChar;
    }
  }
}

void processCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  Serial.print("CMD: ");
  Serial.println(cmd);

  if (cmd.startsWith("SET")) {
    int s1 = cmd.indexOf(' ');
    int s2 = cmd.indexOf(' ', s1 + 1);
    int s3 = cmd.indexOf(' ', s2 + 1);
    int servoNum = cmd.substring(s1 + 1, s2).toInt();

    String action;
    int duration = 0;

    if (s3 > 0) {
      action = cmd.substring(s2 + 1, s3);
      duration = cmd.substring(s3 + 1).toInt();
    } else {
      action = cmd.substring(s2 + 1);
    }

    if (action == "FWD") {
      if (servoNum == 2 || servoNum == 6) {
        pwm.setPWM(servoNum, 0, SERVO_PWM_MOVE);
        servoActions[servoNum] = { millis(), (unsigned long)(duration > 0 ? duration : 500), 1 };
      } else if (servoNum == 0 || servoNum == 5) {
        pwm.setPWM(servoNum, 0, 730 - SERVO_PWM_MOVE);
      }
    } else if (action == "REV") {
      if (servoNum == 2 || servoNum == 6) {
        pwm.setPWM(servoNum, 0, 730 - SERVO_PWM_MOVE);
        servoActions[servoNum].active = -1;
      } else if (servoNum == 0 || servoNum == 5) {
        pwm.setPWM(servoNum, 0, SERVO_PWM_MOVE);
      }
    } else if (action == "STOP") {
      pwm.setPWM(servoNum, 0, custom_pwm[servoNum]);
      servoActions[servoNum].active = 0;
    }
  }

  else if (cmd.startsWith("POS")) {
    int s1 = cmd.indexOf(' ');
    int s2 = cmd.indexOf(' ', s1 + 1);
    int servoNum = cmd.substring(s1 + 1, s2).toInt();
    int degrees = cmd.substring(s2 + 1).toInt();
    degrees = constrain(degrees, 0, 210);
    int targetPulse = map(degrees, 0, 180, POS_MIN, POS_MAX);

    int currentPulse = custom_pwm[servoNum];
    flipperMoves[servoNum] = {
      servoNum,
      currentPulse,
      targetPulse,
      millis(),
      1500,
      true
    };
  }

  else if (cmd.startsWith("CAL")) {
    int s1 = cmd.indexOf(' ');
    int s2 = cmd.indexOf(' ', s1 + 1);
    int servoNum = cmd.substring(s1 + 1, s2).toInt();
    int pwmVal = cmd.substring(s2 + 1).toInt();
    if (pwmVal >= 100 && pwmVal <= 530) {
      custom_pwm[servoNum] = pwmVal;
    }
  }

  else if (cmd.startsWith("ROTATE")) {
    int s1 = cmd.indexOf(' ');
    int s2 = cmd.indexOf(' ', s1 + 1);
    int s3 = cmd.indexOf(' ', s2 + 1);
    int servoNum = cmd.substring(s1 + 1, s2).toInt();
    int degrees = cmd.substring(s2 + 1, s3).toInt();
    String dir = cmd.substring(s3 + 1);
    int timeMs = map(abs(degrees), 0, 360, 0, 1560);
    int pwmVal = SERVO_PWM_MOVE;

    if (dir == "FWD") pwm.setPWM(servoNum, 0, 730 - pwmVal);
    else if (dir == "REV") pwm.setPWM(servoNum, 0, pwmVal);
    else return;

    servoActions[servoNum] = { millis(), (unsigned long)timeMs, true };
  }
}

void handleServoActions() {
  for (int i = 0; i < 16; i++) {
    if (servoActions[i].active == -1) {
      if (i == 2 && digitalRead(PUSHER1_ENDSTOP_PIN) == HIGH) {
        pwm.setPWM(i, 0, custom_pwm[i]);
        servoActions[i].active = 0;
      } else if (i == 6 && digitalRead(PUSHER2_ENDSTOP_PIN) == HIGH) {
        pwm.setPWM(i, 0, custom_pwm[i]);
        servoActions[i].active = 0;
      }
    } else if (servoActions[i].active == 1) {
      if (millis() - servoActions[i].startTime >= servoActions[i].duration) {
        pwm.setPWM(i, 0, custom_pwm[i]);
        servoActions[i].active = 0;
      }
    }
  }
}

void handleFlipperMoves() {
  for (int i = 0; i < 16; i++) {
    if (!flipperMoves[i].active) continue;

    unsigned long elapsed = millis() - flipperMoves[i].startTime;
    if (elapsed >= flipperMoves[i].duration) {
      pwm.setPWM(i, 0, flipperMoves[i].targetPulse);
      custom_pwm[i] = flipperMoves[i].targetPulse;
      flipperMoves[i].active = false;
    } else {
      float t = (float)elapsed / flipperMoves[i].duration;
      int interp = flipperMoves[i].startPulse + (flipperMoves[i].targetPulse - flipperMoves[i].startPulse) * t;
      pwm.setPWM(i, 0, interp);
    }
  }
}
