#include <Arduino.h>
#include <DHT.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define DHTPIN 13
#define DHTTYPE DHT22
#define LDRPIN 34
#define HIGRO_PIN 35
#define RELAYPIN 4
#define LEDPIN 2

const char* ssid = "Wokwi-GUEST";
const char* password = "";
const char* mqtt_server = "broker.hivemq.com";
const char* mqtt_topic = "iot/aluno/gsFiasco";

WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado.");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Tentando conexao MQTT...");
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("conectado");
    } else {
      Serial.print("falha, rc=");
      Serial.print(client.state());
      Serial.println(" tentando novamente em 5 segundos");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  
  dht.begin();
  delay(2000);

  pinMode(LDRPIN, INPUT);
  pinMode(HIGRO_PIN, INPUT);
  pinMode(RELAYPIN, OUTPUT);
  pinMode(LEDPIN, OUTPUT);

  digitalWrite(RELAYPIN, LOW);
  digitalWrite(LEDPIN, HIGH);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  delay(2000);

  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int ldrValue = analogRead(LDRPIN);
  int higroValue = analogRead(HIGRO_PIN);

  if (isnan(h) || isnan(t)) {
    Serial.println("Falha de leitura no DHT22");
    return;
  }

  String payload = "{\"temperatura\":";
  payload += t;
  payload += ",\"umidade_ar\":";
  payload += h;
  payload += ",\"umidade_solo\":";
  payload += higroValue;
  payload += ",\"luminosidade\":";
  payload += ldrValue;
  payload += "}";

  client.publish(mqtt_topic, payload.c_str());
  Serial.print("Payload publicado: ");
  Serial.println(payload);

  if (t > 30.0 || higroValue < 1000) {
    digitalWrite(RELAYPIN, HIGH);
  } else {
    digitalWrite(RELAYPIN, LOW);
  }
}