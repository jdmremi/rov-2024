#include <ArduinoJson.h> //Load Json Library
#include <Servo.h>

Servo left;
Servo right;
Servo leftUp;
Servo rightUp;

int val; // variable for temperature reading
int tempPin = A1; // define analog pin to read
byte leftServoPin= 22;
byte rightServoPin = 28;
byte leftUpServoPin = 24;
byte rightUpServoPin = 26;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);// initialize digital pin LED_BUILTIN as an output.
  digitalWrite(13,LOW);
  Serial.begin(9600);
  left.attach(leftServoPin);
  right.attach(rightServoPin);
  leftUp.attach(leftUpServoPin);
  rightUp.attach(rightUpServoPin);
  delay(7000); // delay to allow ESC to recognize the stopped signal
}

void loop() {
  String thruster;
  // Causes LED to flash if serial is unavailable.
  while (!Serial.available()){ 
   // Serial.print("No data");
   digitalWrite(13,HIGH);
   delay(100);
   digitalWrite(13,LOW);
   delay(100);
  }
  if(Serial.available()) {
    thruster = Serial.readStringUntil( '\x7D' ); // Read data from Arduino until }
    StaticJsonDocument<1024> joystickData; //the StaticJsonDocument we write to

    deserializeJson(joystickData, thruster);
    
    float forwardBackwardPulseWidth = joystickData["forward_backward_pulsewidth"];
    float leftPulseWidth = joystickData["left_pulsewidth"];
    float rightPulseWidth = joystick_info["right_pulsewidth"];
    float ascendDescendPulseWidth = joystick_info["ascent_descend_pulsewidth"];
    float pitchLeftPulseWidth = joystick_info["pitch_left_pulsewidth"];
    float pitchRightPulseWidth = joystick_info["pitch_right_pulsewidth"];

    // Move forward/backward. Note, if other values are being written to left/right, then there might be issues.
    left.writeMicroseconds(forwardBackwardPulseWidth);
    right.writeMicroseconds(forwardBackwardPulseWidth);

    // If not moving forward/backward, we can move left/right 
    // Similarly, we can modify the code above so that if not moving left/right, we can move forward/backward
    left.writeMicroseconds(leftPulseWidth);
    right.writeMicroseconds(rightPulseWidth);

    // ... similar issues may arise
    // Vertical movement
    leftUp.writeMicroseconds(ascendDescendPulseWidth);
    rightUp.writeMicroseconds(ascendDescendPulseWidth);

    // ... similar issues may arise
    // Pitch
    leftUp.writeMicroseconds(pitchLeftPulseWidth);
    rightUp.writeMicroseconds(pitchRightPulseWidth);  

//Read Temperature, return to surface
    val=analogRead(tempPin);//read arduino pin
    StaticJsonDocument<500> doc;//define StaticJsonDocument
    float mv = ((val/1024.0)*500);
    float cel = (mv/10);//temperature in Celsius
    doc["temp"]=cel;//add temp to StaticJsonDocument
    doc["volt"]=mv;
    doc["sig_up_1"]=th_up_sig_1;
    doc["sig_up_2"]=th_up_sig_2;
    doc["sig_rt"]=th_right_sig;
    doc["sig_lf"]=th_left_sig;
 
    serializeJson(doc,Serial);//convert to Json string,sends to surface
    Serial.println();//newline
    delay(10);
  }
}
    
