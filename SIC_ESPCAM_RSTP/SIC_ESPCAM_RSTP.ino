#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "OV2640.h"
#include "OV2640Streamer.h"
#include "CRtspSession.h"

const char *ssid = "Liem"; 
const char *password = "fibonacci"; 

#define ENABLE_RTSPSERVER

WiFiClient espClient;
OV2640 cam;

void enableRTSP(void);
void resetDevice(void);
void initRTSP(void);
void stopRTSP(void);
void rtspTask(void *pvParameters);

TaskHandle_t rtspTaskHandler;

WiFiServer rtspServer(8554);

CStreamer *streamer = NULL;
CRtspSession *session = NULL;
WiFiClient rtspClient;
boolean stopRTSPtask = false;

camera_config_t camera_config = {
  .pin_pwdn = 32,
  .pin_reset = -1,
  .pin_xclk = 0,
  .pin_sccb_sda = 26,
  .pin_sccb_scl = 27,
  .pin_d7 = 35,
  .pin_d6 = 34,
  .pin_d5 = 39,
  .pin_d4 = 36,
  .pin_d3 = 21,
  .pin_d2 = 19,
  .pin_d1 = 18,
  .pin_d0 = 5,
  .pin_vsync = 25,
  .pin_href = 23,
  .pin_pclk = 22,
  .xclk_freq_hz = 20000000,
  .ledc_timer = LEDC_TIMER_0,
  .ledc_channel = LEDC_CHANNEL_0,
  .pixel_format = PIXFORMAT_JPEG, 
  .frame_size = FRAMESIZE_VGA,    
  .jpeg_quality = 10,             
  .fb_count = 2
};

void setup()
{
  pinMode(4, OUTPUT);
  pinMode(12, OUTPUT);
  pinMode(13, OUTPUT);
  digitalWrite(12, LOW);
  digitalWrite(13, LOW);

  Serial.begin(115200);

  Serial.println("\n\n##################################");
  Serial.printf("Internal Total heap %d, internal Free Heap %d\n", ESP.getHeapSize(), ESP.getFreeHeap());
  Serial.printf("SPIRam Total heap %d, SPIRam Free Heap %d\n", ESP.getPsramSize(), ESP.getFreePsram());
  Serial.printf("ChipRevision %d, Cpu Freq %d, SDK Version %s\n", ESP.getChipRevision(), ESP.getCpuFreqMHz(), ESP.getSdkVersion());
  Serial.printf("Flash Size %d, Flash Speed %d\n", ESP.getFlashChipSize(), ESP.getFlashChipSpeed());
  Serial.println("##################################\n\n");

  delay(100);
  cam.init(camera_config);
  delay(100);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  IPAddress ip = WiFi.localIP();
  Serial.print("\nWiFi connected with IP ");
  Serial.println(ip);

  String rtspURL = "rtsp://" + ip.toString() + ":8554/mjpeg/1";
  Serial.print("Browser Stream Link: ");
  Serial.println(rtspURL);

  // Kirim URL RTSP ke API Flask
  sendRTSPURL(rtspURL);

  initRTSP();
}

void sendRTSPURL(String url) {
  HTTPClient http;
  http.begin("http://192.168.1.6:5000/update-rtsp");
  http.addHeader("Content-Type", "application/json");
  String jsonPayload = "{\"url\": \"" + url + "\"}";

  int httpResponseCode = http.POST(jsonPayload);
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("Response from server: " + response);
  } else {
    Serial.println("Error on sending POST: " + String(httpResponseCode));
  }
  http.end();
}

void loop()
{
  delay(100);
}

#ifdef ENABLE_RTSPSERVER

void initRTSP(void)
{
  xTaskCreate(rtspTask, "RTSP", 4096, NULL, 1, &rtspTaskHandler);

  if (rtspTaskHandler == NULL)
  {
    Serial.println("Create RTSP task failed");
  }
  else
  {
    Serial.println("RTSP task up and running");
  }
}

void stopRTSP(void)
{
  stopRTSPtask = true;
}

void rtspTask(void *pvParameters)
{
  uint32_t msecPerFrame = 30;
  static uint32_t lastimage = millis();

  rtspServer.setTimeout(1);
  rtspServer.begin();

  while (1)
  {
    if (session)
    {
      session->handleRequests(0);

      uint32_t now = millis();
      if (now > lastimage + msecPerFrame || now < lastimage)
      {
        session->broadcastCurrentFrame(now);
        lastimage = now;
      }

      if (session->m_stopped)
      {
        Serial.println("RTSP client closed connection");
        delete session;
        delete streamer;
        session = NULL;
        streamer = NULL;
      }
    }
    else
    {
      rtspClient = rtspServer.accept();
      if (rtspClient)
      {
        Serial.println("RTSP client started connection");
        streamer = new OV2640Streamer(&rtspClient, cam);
        session = new CRtspSession(&rtspClient, streamer);
        delay(100);
      }
    }
    if (stopRTSPtask)
    {
      if (rtspClient)
      {
        Serial.println("Shut down RTSP server");
        delete session;
        delete streamer;
        session = NULL;
        streamer = NULL;
      }
      vTaskDelete(NULL);
    }
    delay(10);
  }
}
#endif
