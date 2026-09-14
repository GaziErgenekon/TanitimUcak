// GAZİ Kampüs Uçuş Simülatörü — ESP32 kumanda firmware'i
// Kart: Lolin32 Lite | Sensör: MPU-6050 (I2C) | 1x buton
//
// BAĞLANTI:
//   MPU-6050 VCC -> 3V3 | GND -> GND | SDA -> GPIO25 | SCL -> GPIO26
//   Buton bir ucu -> GPIO4, diğer ucu -> GND (harici direnç YOK, dahili pull-up)
//   (Opsiyonel) Batarya ölçümü: BAT+ --100k--+--100k-- GND, orta nokta -> GPIO35
//               + 100nF filtre. Takınca PIL_AKTIF 1 yapın (4.2V -> 2.1V, güvenli).
//
// SENSÖR YÖNÜ (önemli!):
//   MPU-6050'nin X ekseni İLERİ (uçuş yönü), Z ekseni YUKARI bakmalı.
//   Ters duruyorsa aşağıdaki TERS_PITCH / TERS_ROLL değerini -1 yap.
//
// KÜTÜPHANE (Arduino IDE > Kütüphane Yöneticisi):
//   "Adafruit MPU6050" (Adafruit Unified Sensor ile birlikte gelir)
//   BLE için ek kütüphane GEREKMEZ (ESP32 çekirdeğiyle gelir).
// KART AYARI: Tools > Board > "WEMOS LOLIN32 Lite", baud 115200.
//
// ÇIKTI (USB Seri + Bluetooth LE, 50 Hz):
//   pitch,roll,butonState,pil_mV\n   örn: 12.50,-4.20,1,3980
//   butonState: 1 = basılı değil, 0 = basılı (INPUT_PULLUP)
//   pil_mV: -1 = batarya ölçümü kapalı (PIL_AKTIF 0)
//
// BLUETOOTH (BLE, Nordic UART Servis):
//   Servis : 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
//   TX     : 6E400003-B5A3-F393-E0A9-E50E24DCCA9E  (notify; tarayıcı dinler)
//   RX     : 6E400002-B5A3-F393-E0A9-E50E24DCCA9E  (yazma; şimdilik boş)
//   Cihaz adı: "GAZI-UCAK". USB ve BLE aynı anda veri basar; tarayıcı hangisine
//   bağlanırsa onu kullanır. Butona >1.5 sn basılı tutmak BLE'yi aç/kapat
//   (güç tasarrufu); USB seri çıkışı her zaman açıktır.

#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#ifndef ESP_ARDUINO_VERSION_MAJOR
#define ESP_ARDUINO_VERSION_MAJOR 1   // eski çekirdek uyumluluğu
#endif

// --- Pin ve ayarlar ---
#define SDA_PIN     25
#define SCL_PIN     26
#define BUTON_PIN   4
#define PIL_AKTIF   0        // 1 yapınca batarya ADC'si okunur (harici bölücü şart)
#define PIL_PIN     35       // input-only, harici 100k/100k bölücü orta noktası
#define PIL_BOLEN   2.0      // 100k/100k için 2.0; farklı dirençte güncelleyin
#define TERS_PITCH  1        // pitch tersse -1 yap
#define TERS_ROLL   1        // roll tersse -1 yap
#define TAMAMLAYICI 0.96     // complementary filtre katsayısı (gyro ağırlığı)
#define ORNEK_MS    20       // gönderim aralığı (50 Hz)
#define PIL_MS      500      // batarya okuma aralığı
#define DEBOUNCE_MS 50       // buton sönümleme
#define UZUN_BAS_MS 1500     // BLE aç/kapat için basılı tutma süresi

#define NUS_SERVIS_UUID "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define NUS_TX_UUID     "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
#define NUS_RX_UUID     "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

Adafruit_MPU6050 mpu;
float pitch = 0, roll = 0;          // filtrelenmiş açılar (derece)
float gyroBiasX = 0, gyroBiasY = 0; // gyro kayması (açılışta ölçülür)
unsigned long sonOrnek = 0, sonMicros = 0, sonPil = 0;
int butonHam = HIGH, butonKararli = HIGH;
unsigned long butonDegisimZamani = 0, butonBaslangic = 0;
bool butonUzunIslendi = false;
int pilMv = -1;

// --- BLE durumu ---
BLEServer* bleSunucu = nullptr;
BLECharacteristic* bleTx = nullptr;
bool bleBagli = false, bleAcik = false;

class SunucuCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer*) override { bleBagli = true; }
  void onDisconnect(BLEServer* sunucu) override {
    bleBagli = false;
    sunucu->getAdvertising()->start();   // yeniden bağlanılabilsin
  }
};

void bleBaslat() {
  if (bleAcik) return;
  BLEDevice::init("GAZI-UCAK");
  bleSunucu = BLEDevice::createServer();
  bleSunucu->setCallbacks(new SunucuCallbacks());
  BLEService* servis = bleSunucu->createService(NUS_SERVIS_UUID);
  bleTx = servis->createCharacteristic(NUS_TX_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  bleTx->addDescriptor(new BLE2902());
  servis->start();
  BLEAdvertising* reklam = bleSunucu->getAdvertising();
  reklam->addServiceUUID(BLEUUID(NUS_SERVIS_UUID));
  reklam->setScanResponse(true);
  reklam->setMinPreferred(0x06);        // ~7.5 ms bağlantı aralığı isteği
  reklam->start();
  bleAcik = true;
  Serial.println("BLE aktif: GAZI-UCAK");
}

void bleDurdur() {
  if (!bleAcik) return;
  BLEDevice::deinit(true);
  bleSunucu = nullptr;
  bleTx = nullptr;
  bleBagli = false;
  bleAcik = false;
  Serial.println("BLE kapali (uzun basiş tekrar acar)");
}

float pilOku() {
#if PIL_AKTIF
  const int N = 8;
  uint32_t toplam = 0;
  for (int i = 0; i < N; i++) {
#if ESP_ARDUINO_VERSION_MAJOR >= 2
    toplam += analogReadMilliVolts(PIL_PIN);
#else
    toplam += (uint32_t)(analogRead(PIL_PIN) * 3300.0 / 4095.0);
#endif
    delay(1);
  }
  return (toplam / (float)N) * PIL_BOLEN;
#else
  return -1.0f;
#endif
}

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

  bleBaslat();

  sonMicros = micros();
  sonOrnek = millis();
  sonPil = millis();
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

  // Uzun basış: BLE aç/kapat (uçuş komutunu etkilemez; web butonu ayrı çalışır)
  if (butonKararli == LOW) {
    if (butonBaslangic == 0) butonBaslangic = millis();
    if (!butonUzunIslendi && millis() - butonBaslangic > UZUN_BAS_MS) {
      butonUzunIslendi = true;
      if (bleAcik) bleDurdur(); else bleBaslat();
    }
  } else {
    butonBaslangic = 0;
    butonUzunIslendi = false;
  }

  // Batarya (yavaş örnekleme)
  if (millis() - sonPil >= PIL_MS) {
    sonPil = millis();
    pilMv = (int)lroundf(pilOku());
  }

  // 50 Hz CSV: USB seri + (bağlıysa) BLE notify
  if (millis() - sonOrnek >= ORNEK_MS) {
    sonOrnek = millis();
    char satir[48];
    int n = snprintf(satir, sizeof(satir), "%.2f,%.2f,%d,%d",
                     pitch * TERS_PITCH, roll * TERS_ROLL,
                     butonKararli == LOW ? 0 : 1, pilMv);
    Serial.println(satir);
    if (bleAcik && bleBagli && bleTx != nullptr) {
      bleTx->setValue((uint8_t*)satir, (size_t)n);
      bleTx->notify();   // kuyruk doluysa false döner; örnek atlanır
    }
  }
}
