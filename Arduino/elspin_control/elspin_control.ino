int inPin = 9;    // pushbutton connected to digital pin 7

void setup() {
  Serial.begin(9600);
  pinMode(inPin, INPUT);    // sets the digital pin 7 as input
}

void loop() {
  Serial.println(digitalRead(inPin));
  delay(1000);
}