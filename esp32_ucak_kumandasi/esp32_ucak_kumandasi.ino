// GAZİ Kampüs Uçuş Simülatörü — ESP32 kumanda firmware'i
// Kart: Lolin32 Lite | Sensör: MPU-6050 (I2C) | 1x buton
//
// BAĞLANTI:
//   MPU-6050 VCC -> 3V3 | GND -> GND | SDA -> GPIO25 | SCL -> GPIO26
//   Buton bir ucu -> GPIO4, diğer ucu -> GND (harici direnç YOK, dahili pull-up)
// SENSÖR YÖNÜ (önemli!):
//   MPU-6050'nin X ekseni İLERİ (uçuş yönü), Z ekseni YUKARI bakmalı.
//   Ters duruyorsa aşağıdaki TERS_PITCH / TERS_ROLL değerini -1 yap.
//
// KÜTÜPHANE (Arduino IDE > Kütüphane Yöneticisi):
//   "Adafruit MPU6050" (Adafruit Unified Sensor ile birlikte gelir)
// KART AYARI: Tools > Board > "WEMOS LOLIN32 Lite", baud 115200.
//
// ÇIKTI (USB Seri, 115200 baud, 50 Hz):
//   pitch,roll,butonState\n   örn: 12.50,-4.20,1
//   butonState: 1 = basılı değil, 0 = basılı (INPUT_PULLUP)

#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// --- Pin ve ayarlar ---
#define SDA_PIN     25
#define SCL_PIN     26
#define BUTON_PIN   4
#define TERS_PITCH  1    // pitch tersse -1 yap
#define TERS_ROLL   1    // roll tersse -1 yap
#define TAMAMLAYICI 0.96 // complementary filtre katsayısı (gyro ağırlığı)
#define ORNEK_MS    20   // gönderim aralığı (50 Hz)
#define DEBOUNCE_MS 50   // buton sönümleme

Adafruit_MPU6050 mpu;
float pitch = 0, roll = 0;          // filtrelenmiş açılar (derece)
float gyroBiasX = 0, gyroBiasY = 0; // gyro kayması (açılışta ölçülür)
unsigned long sonOrnek = 0, sonMicros = 0;
int butonHam = HIGH, butonKararli = HIGH;
unsigned long butonDegisimZamani = 0;

void setup() {
  Serial.begin(115200);
  pinMode(BUTON_PIN, INPUT_PULLUP);
  Wire.begin(SDA_PIN, SCL_PIN);

  if (!mpu.begin(0x68, &Wire)) {          // AD0 GND ise adres 0x68
    Serial.println("HATA: MPU-6050 bulunamadı! Bağlantıyı kontrol et.");
    while (1) delay(100);
  }
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // Gyro bias kalibrasyonu: kartı 2 sn HAREKETSİZ tut
  sensors_event_t a, g, t;
  const int N = 500;
  for (int i = 0; i < N; i++) {
    mpu.getEvent(&a, &g, &t);
    gyroBiasX += g.gyro.x;
    gyroBiasY += g.gyro.y;
    delay(4);
  }
  gyroBiasX /= N;
  gyroBiasY /= N;

  // Başlangıç açısını ivmeölçerden al (kart düz duruyorsa ~0 olur)
  // Eksen: X ileri, Z yukarı (sağ-elli sistemde Y otomatikman sola bakar).
  // pitch: burun-yukarı +, roll: sağa-yatış +.
  mpu.getEvent(&a, &g, &t);
  pitch = atan2f(-a.acceleration.x,
                 sqrtf(a.acceleration.y * a.acceleration.y +
                       a.acceleration.z * a.acceleration.z)) * 57.2958f;
  roll = atan2f(-a.acceleration.y, a.acceleration.z) * 57.2958f;

  sonMicros = micros();
  sonOrnek = millis();
}

void loop() {
  sensors_event_t a, g, t;
  mpu.getEvent(&a, &g, &t);

  // dt (sn)
  unsigned long simdi = micros();
  float dt = (simdi - sonMicros) / 1000000.0f;
  sonMicros = simdi;
  if (dt <= 0 || dt > 0.1f) dt = 0.02f;

  // İvmeölçerden ham açılar (derece): burun-yukarı +, sağa-yatış +
  float pitchAcc = atan2f(-a.acceleration.x,
                          sqrtf(a.acceleration.y * a.acceleration.y +
                                a.acceleration.z * a.acceleration.z)) * 57.2958f;
  float rollAcc = atan2f(-a.acceleration.y, a.acceleration.z) * 57.2958f;

  // Gyro (rad/sn -> derece/sn, bias çıkarılmış).
  // Fizik: pitch ekseni Y'dir ve burun-yukarı harekette gyroY NEGATİF olur;
  // roll ekseni X'tir ve sağa-yatışta gyroX POZİTİF olur. Bu yüzden:
  float gyroPitch = -(g.gyro.y - gyroBiasY) * 57.2958f;
  float gyroRoll  = (g.gyro.x - gyroBiasX) * 57.2958f;

  // Tamamlayıcı filtre
  pitch = TAMAMLAYICI * (pitch + gyroPitch * dt) + (1.0f - TAMAMLAYICI) * pitchAcc;
  roll  = TAMAMLAYICI * (roll + gyroRoll * dt) + (1.0f - TAMAMLAYICI) * rollAcc;

  // Buton (debounce'lu, pull-up: basılı = LOW = 0)
  int okunan = digitalRead(BUTON_PIN);
  if (okunan != butonHam) {
    butonHam = okunan;
    butonDegisimZamani = millis();
  }
  if (millis() - butonDegisimZamani > DEBOUNCE_MS) {
    butonKararli = butonHam;
  }

  // 50 Hz CSV gönder
  if (millis() - sonOrnek >= ORNEK_MS) {
    sonOrnek = millis();
    Serial.print(pitch * TERS_PITCH, 2);
    Serial.print(',');
    Serial.print(roll * TERS_ROLL, 2);
    Serial.print(',');
    Serial.println(butonKararli == LOW ? 0 : 1);
  }
}
