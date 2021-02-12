#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

const char* ssid = "WORKSTATION51 6545";
const char* password = "123456789";

WiFiUDP Udp;
unsigned int localUdpPort = 4210;  // local port to listen on
byte incomingPacket[255];  // buffer for incoming packets
char  replyPacket[] = "Hi there! Got the message :-)";  // a reply string to send back

#define RELAY_1 5
#define RELAY_2 4

void setup()
{
  pinMode(LED_BUILTIN, OUTPUT); 
  pinMode(RELAY_1, OUTPUT); 
  pinMode(RELAY_2, OUTPUT); 
  
  Serial.begin(115200);
  Serial.println();

  Serial.printf("Connecting to %s ", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" connected");

  Udp.begin(localUdpPort);
  Serial.printf("Now listening at IP %s, UDP port %d\n", WiFi.localIP().toString().c_str(), localUdpPort);
}


void loop()
{
  int packetSize = Udp.parsePacket();
  if (packetSize)
  {
    // receive incoming UDP packets
    Serial.printf("Received %d bytes from %s, port %d\n", packetSize, Udp.remoteIP().toString().c_str(), Udp.remotePort());
    int len = Udp.read(incomingPacket, 255);
    if (len > 0)
    {
      incomingPacket[len] = 0;
    }
    
    Serial.print("UDP packet contents: ");
    Serial.print(incomingPacket[0]);
    Serial.println(incomingPacket[1]);

    if (incomingPacket[0] == 1) {
      digitalWrite(RELAY_1, LOW);
      digitalWrite(LED_BUILTIN, LOW);
      Serial.println("ON");
    } else {
      digitalWrite(RELAY_1, HIGH);
      digitalWrite(LED_BUILTIN, HIGH);
      Serial.println("OFF");
    }

    if (incomingPacket[1] == 1) {
      digitalWrite(RELAY_2, LOW);
    } else {
      digitalWrite(RELAY_2, HIGH);
    }
    
    // send back a reply, to the IP address and port we got the packet from
    Udp.beginPacket(Udp.remoteIP(), Udp.remotePort());
    Udp.write(replyPacket);
    Udp.endPacket();
  }
}
