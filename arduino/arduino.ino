#include <ArduinoJson.h> //Load Json Library
#include <Servo.h>

Servo servo_lf;
Servo servo_rt;
Servo servo_up1;
Servo servo_up2;

int val; //variable for temperature reading
int tempPin = A1;//define analog pin to read
byte servoPin_rt= 22;
byte servoPin_lf= 28;
byte servoPin_up1 = 24;
byte servoPin_up2 = 26;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);// initialize digital pin LED_BUILTIN as an output.
  digitalWrite(13,LOW);
  Serial.begin(9600);
  servo_up1.attach(servoPin_up1);
  servo_up2.attach(servoPin_up2);
  servo_lf.attach(servoPin_lf);
  servo_rt.attach(servoPin_rt);
  delay(7000); //delay to allow ESC to recognize the stopped signal
}

void loop() {
  String thruster;
  while (!Serial.available()){ 
   //Serial.print("No data");
   digitalWrite(13,HIGH);
   delay(100);
   digitalWrite(13,LOW);
   delay(100);
  }
  if(Serial.available()) {
      thruster=Serial.readStringUntil( '\x7D' );//Read data from Arduino until};
  
    StaticJsonDocument<1000> json_doc; //the StaticJsonDocument we write to
    deserializeJson(json_doc,thruster);
     
    //Left Thruster
    float th_left=json_doc["tleft"];
    int th_left_sig=(th_left+1)*400+1100; //map controller to servo
    servo_lf.writeMicroseconds(th_left_sig); //Send signal to ESC
    
    //Right Thruster
    float th_right=json_doc["tright"];
    int th_right_sig=(th_right+1)*400+1100; //map controller to servo
    servo_rt.writeMicroseconds(th_right_sig); //Send signal to ESC
   
    //Vertical Thruster 1 
    float th_up_1 = json_doc["tup"];
    int th_up_sig_1=(th_up_1+1)*400+1100; //map controller to servo
    servo_up1.writeMicroseconds(th_up_sig_1); //Send signal to ESC

    //Vertical Thruster 2
    float th_up_2 = json_doc["tup"];
    int th_up_sig_2=(th_up_1+1)*400+1100; //map controller to servo
    servo_up2.writeMicroseconds(th_up_sig_2); //Send signal to ESC

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
    
