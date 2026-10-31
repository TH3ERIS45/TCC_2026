/*
 ESP32-CAM AI Thinker / GC2145 (RGB565) - gateway Wi-Fi e coordenador de captura.
 Arduino Uno (CNC Shield v3) ligado via UART0 GPIO1/TX e GPIO3/RX.
 ATENCAO: GPIO1/3 sao os mesmos usados na gravacao serial da ESP32-CAM.
 A UART NAO deve ser conectada simultaneamente a adaptadores de programacao.

 Notebook -> Wi-Fi HTTP -> ESP32-CAM -> UART -> Arduino -> motores.
 Arduino DONE com P=1 -> ESP32 captura -> POST JPEG ao notebook -> confirma
 HTTP 200 + OK:<ID> -> ESP32 envia PHOTOACK <ID> diretamente ao Arduino.
 Sem resposta confirmada o Arduino PERMANECE bloqueado (PHOTO=WAIT).

 Requer Python receptor rodando no notebook, e ESP32 e notebook na mesma LAN.
 Painel disponivel no notebook (controle.py). Sem SD obrigatorio.
*/
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <ESPmDNS.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include "esp_camera.h"
#include "img_converters.h"
#include "esp_log.h"

// Rede e chave configuradas UMA VEZ pelo Monitor Serial, armazenadas na NVS.
// Nao insira SSID/senha/chave no codigo. UART0 e compartilhada com Arduino:
// para configurar, DESLIGUE A ALIMENTACAO DOS MOTORES e DESCONECTE RX/TX
// do Arduino (com ambas as placas desligadas). Use adaptador USB-serial 3,3 V.
const uint16_t NOTEBOOK_PORT = 8765;
String wifiSsid, wifiPassword, notebookIp, apiKey;
bool redeConfigurada = false;
const uint32_t BOOT_CONFIG_WINDOW_MS = 9000UL;

// Flash branco integrado da ESP32-CAM AI Thinker (GPIO4, ativo em HIGH).
// GPIO4 tambem e linha do microSD: este firmware nao usa microSD.
#define FLASH_LED_GPIO 4
const uint32_t FLASH_MANUAL_TIMEOUT_MS = 60000UL; // evita LED aceso indefinidamente
const uint8_t FLASH_AUTO_LIMIAR = 60; // brilho RGB estimado 0..255; ajuste experimental
bool flashManual = false, flashAuto = false, flashFotoTemporario = false;
uint32_t flashManualDesdeMs = 0;
int flashUltimoBrilho = -1;
bool flashUltimaFotoUsou = false;

void atualizarLedFlash() {
  digitalWrite(FLASH_LED_GPIO, (flashManual || flashFotoTemporario) ? HIGH : LOW);
}
void definirFlashManual(bool ligado) {
  flashManual=ligado;
  flashManualDesdeMs=ligado?millis():0;
  atualizarLedFlash();
}
void definirFlashTemporario(bool ligado) {
  flashFotoTemporario=ligado;
  atualizarLedFlash();
}

// Amostragem de luminancia sobre RGB565 nativo, sem alocar imagem adicional.
// Exposicao e ganho automaticos do sensor podem afetar a estimativa:
// o limiar e apenas uma heuristica, nao um luximetro.
int estimarBrilhoRGB565(const camera_fb_t* fb) {
  if (!fb || fb->format!=PIXFORMAT_RGB565 || !fb->buf || fb->len<2) return -1;
  const size_t pixels = min((size_t)fb->width * fb->height, fb->len/2);
  if (!pixels) return -1;
  const size_t passo = max((size_t)1, pixels/320);
  uint32_t soma=0, count=0;
  for (size_t i=0; i<pixels; i+=passo) {
    const size_t k=i*2;
    const uint16_t rgb=((uint16_t)fb->buf[k]<<8)|fb->buf[k+1];
    const uint16_t r=((rgb>>11)&31)*255/31;
    const uint16_t g=((rgb>>5)&63)*255/63;
    const uint16_t b=(rgb&31)*255/31;
    soma+=(77*r+150*g+29*b)>>8;
    ++count;
  }
  return count ? (int)(soma/count) : -1;
}

#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

WebServer server(80);
// MJPEG em uma tarefa separada, sem bloquear o WebServer de comandos (80).
WiFiServer videoServer(81);
SemaphoreHandle_t cameraMutex = nullptr;
volatile bool cameraReady = false;
volatile bool streamConnected = false;
volatile bool cameraUploadBusy = false;
bool mdnsAtivo = false;
uint32_t ultimoMdnsMs = 0;
// GC2145 nao possui JPEG nativo. Foto e stream sao convertidos por software.
// Com PSRAM, ambos operam em VGA (640x480) desde a inicializacao:
// nao ha troca de resolucao ao abrir o stream ou capturar uma foto.
// Sem PSRAM, QQVGA continua como protecao contra falta de memoria.
framesize_t fotoFrameMode = FRAMESIZE_QVGA;
framesize_t streamFrameMode = FRAMESIZE_QVGA;
framesize_t currentFrameMode = FRAMESIZE_QVGA;
const uint8_t FOTO_QUALIDADE_JPEG = 80;   // frame2jpg: 0..100, maior = melhor
const uint8_t STREAM_QUALIDADE_JPEG = 65;
String cameraSensorPid = "indisponivel";
// Diagnostico somente: parametros atomicos simples entre tarefa do video e HTTP.
// last_failure: 0=nada, 1=mutex, 2=resolucao, 3=fb nulo, 4=tamanho,
//               5=formato nao RGB565, 6=frame2jpg, 7=jpeg curto, 8=envio.
// step: 0=parado, 1=mutex, 2=configuracao, 3=captura, 4=conversao,
//       5=envio, 6=frame enviado.
volatile uint32_t streamAttempts=0, streamFrames=0;
volatile uint32_t streamCaptureFailures=0, streamConvertFailures=0;
volatile uint32_t streamLastWidth=0, streamLastHeight=0, streamLastFormat=0;
volatile uint32_t streamLastJpegBytes=0, streamLastFrameMs=0;
volatile uint32_t streamStep=0, streamLastFailure=0;
Preferences prefs;

struct Ponto { int32_t x, y; bool foto; };
const uint8_t MAX_POINTS = 48;
Ponto pontos[MAX_POINTS];
uint8_t totalPontos = 0, indice = 0;
uint32_t nextId = 1, ultimaFotoId = 0;
volatile uint32_t pendenteId = 0;
int32_t ultimaFotoX = 0, ultimaFotoY = 0;
String linhaSerial, ultimoEvento = "Inicializando", erro = "";
String telemetria = "";
int32_t eixoX = -1, eixoY = -1, maxX = 1640, maxY = 4550;
int32_t centerXSteps = 820, centerYSteps = 2275; // canais internos; painel troca apenas os rotulos
bool homedX = false, homedY = false, enabled = false, movimentando = false;
volatile bool fotoLock = false;
volatile bool executando = false;
uint32_t pidArduino = 0, lastStatusMs = 0;
uint32_t telemetriaSeq = 0;  // muda SOMENTE quando chega POS real do Arduino
// So considerar telemetria como confirmacao se o JPEG ja foi salvo no notebook
// e o PHOTOACK dessa transacao ja foi enviado pela UART.
bool fotoAckEnviado = false;
// Versao e diagnosticos visiveis em /api/status para conferir a gravacao real.
const char* FW_VERSION = "ESP32-4.3-GC2145-PREFLIGHT-CENTER-CAL";
// Base de captura/ACK mantida de "ESP32-4.2-GC2145-UARTACK-FIX1"; protocolo PHOTOACK 2.7 preservado (ESP32-2.7-PHOTOACK-DIAG).
uint8_t fotoAckTentativas = 0;
uint32_t ultimoAckMs = 0;
String ultimaLinhaArduino = "";
String ultimoPhotoEstado = "";
uint32_t linhasArduinoLidas = 0;
const uint32_t PHOTOACK_RETRY_MS = 1800UL;
const uint32_t PHOTOACK_TIMEOUT_MS = 18000UL;

// Os estados seguem a maquina, nao o notebook.
enum Stage : uint8_t { IDLE, WAIT_ARRIVAL, SETTLE, TAKE_PHOTO, WAIT_PHOTOACK, FAULT };
volatile Stage stage = IDLE;
uint32_t stageSince = 0, heartbeatAt = 0, lastStatusRequest = 0;
const uint32_t ARRIVAL_TIMEOUT_MS = 180000UL;
const uint32_t PHOTO_SETTLE_MS = 1400UL;

void enviarArduino(const String &s) { Serial.print(s); Serial.print('\n'); }

String stageName() {
  switch (stage) {
    case IDLE: return "PARADO";
    case WAIT_ARRIVAL: return "MOVENDO";
    case SETTLE: return "ESTABILIZANDO";
    case TAKE_PHOTO: return "FOTOGRAFANDO/ENVIANDO";
    case WAIT_PHOTOACK: return "AGUARDANDO PHOTOACK";
    case FAULT: return "ERRO";
  }
  return "DESCONHECIDO";
}

String campo(const String &s, const char *key) {
  String token = String(key) + "=";
  int p = s.indexOf(token);
  if (p < 0) return "";
  p += token.length();
  int e = s.indexOf(',', p);
  return s.substring(p, e < 0 ? s.length() : e);
}

void falhar(const String &msg) {
  erro = msg;
  ultimoEvento = "FALHA: " + msg;
  stage = FAULT;
  executando = false;
  // Nao confirma nem libera foto pendente. STOP interrompe movimento.
  enviarArduino("STOP");
}

// O Arduino envia OK:PHOTOACK ID=n e depois POS:...PHOTO=READY,PID=0.
// Se a linha OK se perder na UART, a telemetria confirmada do proprio
// Arduino e uma segunda prova de que a trava foi liberada.
void fotoConfirmada(uint32_t id, const String &via) {
  if (stage != WAIT_PHOTOACK || !fotoAckEnviado || id != pendenteId) return;
  ultimoEvento = "Foto " + String(id) + " salva e confirmada (" + via + "). Proximo ponto liberado.";
  ultimaFotoId = id;
  pendenteId = 0;
  fotoAckEnviado = false;
  fotoAckTentativas = 0;
  indice++;
  stage = IDLE;
}

void tratarLinha(const String &line) {
  linhasArduinoLidas++;
  ultimaLinhaArduino = line.substring(0, 210);
  if (line.startsWith("POS:")) {
    telemetria = line;
    lastStatusMs = millis();
    telemetriaSeq++;
    eixoX = campo(line, "X").toInt();
    eixoY = campo(line, "Y").toInt();
    if (campo(line, "XMAX").length()) maxX = campo(line, "XMAX").toInt();
    if (campo(line, "YMAX").length()) maxY = campo(line, "YMAX").toInt();
    centerXSteps = campo(line, "CENTERX").length() ? campo(line, "CENTERX").toInt() : maxX / 2;
    centerYSteps = campo(line, "CENTERY").length() ? campo(line, "CENTERY").toInt() : maxY / 2;
    homedX = campo(line, "HX") == "1";
    homedY = campo(line, "HY") == "1";
    enabled = campo(line, "EN") == "1";
    movimentando = campo(line, "STATUS") == "MOVING";
    fotoLock = campo(line, "PHOTO") == "WAIT";
    pidArduino = static_cast<uint32_t>(campo(line, "PID").toInt());
    ultimoPhotoEstado = "PROTO=" + campo(line,"PROTO") + ",PHOTO=" +
                        campo(line,"PHOTO") + ",PID=" + String(pidArduino);
    // Fallback seguro: este ponto JA tinha PHOTO=WAIT com ID correspondente
    // na etapa de captura, o notebook confirmou o JPEG e so entao o ACK
    // foi enviado. Exigir PROTO=2, HOME e coordenadas atuais identicas.
    if (stage == WAIT_PHOTOACK && fotoAckEnviado && pendenteId != 0 &&
        campo(line, "PROTO") == "2" && campo(line, "PHOTO") == "READY" &&
        pidArduino == 0 && !movimentando && homedX && homedY && enabled &&
        eixoX == ultimaFotoX && eixoY == ultimaFotoY) {
      fotoConfirmada(pendenteId, "telemetria");
    }
  } else if (line.startsWith("DONE:ID=")) {
    uint32_t id = static_cast<uint32_t>(campo(line.substring(5), "ID").toInt());
    int32_t x = campo(line, "X").toInt();
    int32_t y = campo(line, "Y").toInt();
    bool precisaFoto = campo(line, "P") == "1";
    if (stage != WAIT_ARRIVAL || id != pendenteId) return; // resposta obsoleta
    if (x != pontos[indice].x || y != pontos[indice].y || precisaFoto != pontos[indice].foto) {
      falhar("Posicao/foto de chegada nao confere com o roteiro");
      return;
    }
    ultimaFotoX = x;
    ultimaFotoY = y;
    ultimoEvento = "Chegou ao ponto " + String(indice + 1) + "/" + String(totalPontos);
    if (precisaFoto) { stage = SETTLE; stageSince = millis(); }
    else { pendenteId = 0; indice++; stage = IDLE; }
  } else if (line.startsWith("OK:PHOTOACK ID=")) {
    uint32_t id = static_cast<uint32_t>(line.substring(strlen("OK:PHOTOACK ID=")).toInt());
    fotoConfirmada(id, "resposta UART");
  } else if (line.startsWith("[ERRO]")) {
    ultimoEvento = line;
    // Uma repeticao do ACK pode chegar DEPOIS de o Arduino ja ter liberado a
    // foto. Nao a tratar como sucesso nem encerrar sem verificar telemetria.
    bool ackJaLiberado = (stage == WAIT_PHOTOACK && fotoAckEnviado &&
                           line.indexOf("Nao existe foto pendente") >= 0);
    if (!ackJaLiberado && (stage == WAIT_ARRIVAL || stage == WAIT_PHOTOACK)) falhar(line);
  }
}

void lerUART() {
  size_t n = 0;
  while (Serial.available() && n++ < 512) {
    char c = static_cast<char>(Serial.read());
    if (c == '\r' || c == '\n') {
      if (linhaSerial.length()) { tratarLinha(linhaSerial); linhaSerial = ""; }
    } else if (linhaSerial.length() < 250 && c >= 32 && c < 127) linhaSerial += c;
  }
}

bool salvarRoteiro(const String &dados, String &mensagem) {
  if (stage != IDLE || executando || pendenteId || fotoLock) {
    mensagem = "Pare o roteiro e resolva qualquer foto pendente";
    return false;
  }
  if (dados.length() > 1500) { mensagem = "Roteiro excede o limite"; return false; }
  Ponto tmp[MAX_POINTS];
  uint8_t count = 0;
  int inicio = 0;
  while (inicio < dados.length()) {
    int fim = dados.indexOf('\n', inicio);
    if (fim < 0) fim = dados.length();
    String ln = dados.substring(inicio, fim); ln.trim();
    inicio = fim + 1;
    if (!ln.length()) continue;
    int a = ln.indexOf(','), b = ln.indexOf(',', a + 1);
    if (a < 1 || b <= a + 1 || count >= MAX_POINTS) { mensagem = "Formato/quantidade de pontos invalido"; return false; }
    String sx = ln.substring(0, a), sy = ln.substring(a + 1, b), sp = ln.substring(b + 1);
    sx.trim(); sy.trim(); sp.trim();
    if (sp != "0" && sp != "1") { mensagem = "Foto deve ser 0 ou 1"; return false; }
    for (int which=0; which<2; which++) {
      String s = (which==0) ? sx : sy;
      if (!s.length() || s.length() > 7) { mensagem = "Coordenada invalida"; return false; }
      for (size_t i = 0; i < s.length(); i++) if (!isDigit(s[i])) { mensagem = "Apenas coordenadas positivas inteiras"; return false; }
    }
    int32_t x = sx.toInt(), y = sy.toInt();
    if (x < 0 || y < 0 || x > maxX || y > maxY) { mensagem = "Ponto fora dos limites do Arduino"; return false; }
    tmp[count++] = {x, y, sp == "1"};
  }
  if (!count) { mensagem = "Adicione pelo menos um ponto"; return false; }
  for (uint8_t i = 0; i < count; i++) pontos[i] = tmp[i];
  totalPontos = count;
  String compact = "";
  for (uint8_t i = 0; i < count; i++) compact += String(pontos[i].x) + "," + String(pontos[i].y) + "," + (pontos[i].foto ? "1\n" : "0\n");
  prefs.putString("route", compact);
  mensagem = "Roteiro salvo com " + String(count) + " pontos";
  return true;
}

void carregarRoteiro() {
  String dados = prefs.getString("route", "");
  // Inicializacao isolada para nao tentar persistir durante o boot.
  int inicio = 0;
  while (inicio < dados.length() && totalPontos < MAX_POINTS) {
    int fim = dados.indexOf('\n', inicio);
    if (fim < 0) fim = dados.length();
    String ln = dados.substring(inicio, fim); inicio = fim + 1;
    int a = ln.indexOf(','), b = ln.indexOf(',', a + 1);
    if (a < 0 || b < 0) continue;
    int32_t x = ln.substring(0, a).toInt(), y = ln.substring(a + 1, b).toInt();
    if (x < 0 || y < 0 || x > 1640 || y > 4550) continue;
    pontos[totalPontos++] = {x, y, ln.substring(b + 1).toInt() == 1};
  }
}

void proximoPonto() {
  if (stage != IDLE || indice >= totalPontos || !homedX || !homedY ||
      !enabled || fotoLock || movimentando || (millis() - lastStatusMs > 1800)) return;
  if (pontos[indice].x > maxX || pontos[indice].y > maxY) { falhar("Roteiro fora dos limites atuais"); return; }
  nextId = (nextId % 899999998UL) + 1;
  prefs.putUInt("nextid", nextId); // persistir ANTES de enviar para descartar ACK antigo
  pendenteId = nextId;
  fotoAckEnviado = false;
  fotoAckTentativas = 0;
  ultimoAckMs = 0;
  String cmd = "SCANMOVE X " + String(pontos[indice].x) + " Y " + String(pontos[indice].y) +
               " P " + (pontos[indice].foto ? "1" : "0") + " ID " + String(pendenteId);
  enviarArduino(cmd);
  stage = WAIT_ARRIVAL;
  stageSince = millis();
  heartbeatAt = millis();
  ultimoEvento = "Movendo para ponto " + String(indice + 1) + "/" + String(totalPontos);
}

// GC2145: os framebuffers saem em RGB565, e o notebook continua recebendo
// JPEG normal. Conversao/captura sob mutex para nao disputar sensor/PSRAM
// com o stream da porta 81. Nenhum PHOTOACK e enviado se falhar a conversao.
bool capturarJpegFotografico(uint8_t* &jpeg, size_t &jpegLen) {
  jpeg = nullptr;
  jpegLen = 0;
  flashUltimaFotoUsou=false;
  flashUltimoBrilho=-1;
  if (!cameraReady || !cameraMutex) { erro = "Camera indisponivel"; return false; }
  if (xSemaphoreTake(cameraMutex, pdMS_TO_TICKS(5000)) != pdTRUE) {
    erro = "Camera ocupada pelo stream";
    return false;
  }
  sensor_t* sensor = esp_camera_sensor_get();
  bool configured = sensor && (currentFrameMode == fotoFrameMode ||
                    sensor->set_framesize(sensor, fotoFrameMode) == 0);
  if (configured) currentFrameMode = fotoFrameMode;
  camera_fb_t* fb = nullptr;
  if (configured) {
    const uint16_t expectedWidth = fotoFrameMode == FRAMESIZE_VGA ? 640 :
                                   fotoFrameMode == FRAMESIZE_QVGA ? 320 : 160;
    for (int attempt = 0; attempt < 4; ++attempt) {
      fb = esp_camera_fb_get();
      if (!fb || fb->width == expectedWidth) break;
      esp_camera_fb_return(fb);
      fb = nullptr;
    }
  }
  // Modo manual: LED ja esta ligado. No automatico, medir SEM flash e,
  // se necessario, refazer a captura com o LED aceso.
  if (fb && fb->format==PIXFORMAT_RGB565) {
    if (flashAuto && !flashManual) {
      flashUltimoBrilho=estimarBrilhoRGB565(fb);
      if (flashUltimoBrilho>=0 && flashUltimoBrilho<FLASH_AUTO_LIMIAR) {
        esp_camera_fb_return(fb);
        fb=nullptr;
        definirFlashTemporario(true);
        delay(220); // tempo para iluminacao e ajuste de exposicao do sensor
        camera_fb_t* descarte=esp_camera_fb_get();
        if (descarte) esp_camera_fb_return(descarte);
        fb=esp_camera_fb_get();
        flashUltimaFotoUsou=true;
      }
    } else if (flashManual) {
      flashUltimaFotoUsou=true;
    }
  }
  const bool converted = fb && fb->format == PIXFORMAT_RGB565 &&
                         frame2jpg(fb, FOTO_QUALIDADE_JPEG, &jpeg, &jpegLen);
  if (fb) esp_camera_fb_return(fb);
  // Flash automatico SEMPRE apaga, mesmo se a captura/conversao falhar.
  definirFlashTemporario(false);
  xSemaphoreGive(cameraMutex);
  if (!converted || !jpeg || jpegLen < 1024 || jpeg[0] != 0xFF ||
      jpeg[1] != 0xD8 || jpeg[jpegLen-2] != 0xFF || jpeg[jpegLen-1] != 0xD9) {
    if (jpeg) free(jpeg);
    jpeg = nullptr;
    jpegLen = 0;
    erro = "Falha RGB565 -> JPEG fotografico";
    return false;
  }
  return true;
}

bool fotografarEEnviar(uint32_t id) {
  // A foto/PHOTOACK tem prioridade sobre o stream de calibracao.
  cameraUploadBusy = true;
  if (WiFi.status() != WL_CONNECTED) {
    erro = "Wi-Fi desconectado"; cameraUploadBusy = false; return false;
  }
  uint8_t* jpeg = nullptr;
  size_t jpegLen = 0;
  if (!capturarJpegFotografico(jpeg, jpegLen)) {
    cameraUploadBusy = false; return false;
  }
  HTTPClient http;
  String url = "http://" + notebookIp + ":" + String(NOTEBOOK_PORT) + "/api/photos/receive";
  if (!http.begin(url)) {
    free(jpeg); cameraUploadBusy = false;
    erro = "URL de recebimento invalida";
    return false;
  }
  http.setTimeout(12000); // compressao por software pode gerar JPEGs maiores
  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("X-Photo-Token", apiKey);
  http.addHeader("X-Photo-Id", String(id));
  http.addHeader("X-Photo-X", String(ultimaFotoX));
  http.addHeader("X-Photo-Y", String(ultimaFotoY));
  int code = http.sendRequest("POST", jpeg, jpegLen);
  String answer = code == 200 ? http.getString() : "";
  http.end();
  free(jpeg);
  cameraUploadBusy = false;
  if (code != 200 || answer != "OK:" + String(id)) {
    erro = "Notebook nao confirmou JPEG (HTTP " + String(code) + ")";
    return false;
  }
  return true;
}

bool autorizado() {
  if (server.header("X-Api-Key") != apiKey) {
    server.send(403, "text/plain", "Chave incorreta"); return false;
  }
  return true;
}
String jsonEscape(const String &txt) {
  String out; out.reserve(txt.length()+12);
  for (size_t i=0; i<txt.length(); i++) {
    char c=txt[i];
    if (c=='\\' || c=='"') { out+='\\'; out+=c; }
    else if (c=='\n' || c=='\r' || c=='\t') out+=' ';
    else if (static_cast<uint8_t>(c)>=32) out+=c;
  }
  return out;
}
void jsonStatus() {
  if (!autorizado()) return;
  String s = "{";
  s += "\"fw_version\":\"" + String(FW_VERSION) + "\"";
  s += ",\"jog_hold_supported\":true";
  s += ",\"command_ack_supported\":true";
  s += ",\"flash_supported\":true";
  s += ",\"flash_manual\":" + String(flashManual?"true":"false");
  s += ",\"flash_auto\":" + String(flashAuto?"true":"false");
  s += ",\"flash_on\":" + String((flashManual||flashFotoTemporario)?"true":"false");
  s += ",\"flash_manual_timeout_s\":60";
  s += ",\"flash_auto_limiar\":" + String(FLASH_AUTO_LIMIAR);
  s += ",\"flash_last_brightness\":" + String(flashUltimoBrilho);
  s += ",\"flash_last_photo_used\":" + String(flashUltimaFotoUsou?"true":"false");
  s += ",\"jog_max_steps\":5000";
  s += ",\"wifi\":" + String(WiFi.status()==WL_CONNECTED?"true":"false");
  s += ",\"wifi_ssid\":\"" + jsonEscape(wifiSsid) + "\"";
  s += ",\"configured\":" + String(redeConfigurada?"true":"false");
  s += ",\"ip\":\"" + WiFi.localIP().toString() + "\"";
  s += ",\"camera_ok\":" + String(cameraReady?"true":"false");
  s += ",\"camera_pid\":\"" + jsonEscape(cameraSensorPid) + "\"";
  s += ",\"stream_active\":" + String(streamConnected?"true":"false");
  s += ",\"stream_diag_version\":1";
  s += ",\"stream_diag_step\":" + String(streamStep);
  s += ",\"stream_diag_last_failure\":" + String(streamLastFailure);
  s += ",\"stream_diag_attempts\":" + String(streamAttempts);
  s += ",\"stream_diag_frames\":" + String(streamFrames);
  s += ",\"stream_diag_capture_failures\":" + String(streamCaptureFailures);
  s += ",\"stream_diag_convert_failures\":" + String(streamConvertFailures);
  s += ",\"stream_diag_width\":" + String(streamLastWidth);
  s += ",\"stream_diag_height\":" + String(streamLastHeight);
  s += ",\"stream_diag_format\":" + String(streamLastFormat);
  s += ",\"stream_diag_jpeg_bytes\":" + String(streamLastJpegBytes);
  s += ",\"stream_diag_last_frame_ms\":" + String(streamLastFrameMs);
  const bool uartRecente = lastStatusMs && millis()-lastStatusMs<2500;
  s += ",\"arduino\":" + String(uartRecente?"true":"false");
  s += ",\"telemetry_seq\":" + String(telemetriaSeq);
  s += ",\"telemetry_age_ms\":" + String(lastStatusMs ? millis()-lastStatusMs : 0);
  s += ",\"ready_to_move\":" + String(uartRecente && homedX && homedY && enabled &&
        !movimentando && !fotoLock && !executando && stage==IDLE && !pendenteId ? "true" : "false");
  s += ",\"x\":" + String(eixoX) + ",\"y\":" + String(eixoY);
  s += ",\"xmax\":" + String(maxX) + ",\"ymax\":" + String(maxY);
  s += ",\"center_x\":" + String(centerXSteps) + ",\"center_y\":" + String(centerYSteps);
  s += ",\"home_x\":" + String(homedX?"true":"false") + ",\"home_y\":" + String(homedY?"true":"false");
  s += ",\"enabled\":" + String(enabled?"true":"false");
  s += ",\"moving\":" + String(movimentando?"true":"false");
  s += ",\"photo_lock\":" + String(fotoLock?"true":"false");
  s += ",\"photo_id\":" + String(pidArduino);
  s += ",\"stage\":\"" + stageName() + "\"";
  s += ",\"active\":" + String(executando?"true":"false");
  s += ",\"point\":" + String(indice) + ",\"total\":" + String(totalPontos);
  s += ",\"last_photo_id\":" + String(ultimaFotoId);
  // evitar inserir strings UART arbitrarias em JSON
  s += ",\"photo_ack_tries\":" + String(fotoAckTentativas);
  s += ",\"photo_ack_sent\":" + String(fotoAckEnviado?"true":"false");
  s += ",\"pending_id\":" + String(pendenteId);
  s += ",\"uart_lines\":" + String(linhasArduinoLidas);
  s += ",\"uart_last\":\"" + jsonEscape(ultimaLinhaArduino) + "\"";
  s += ",\"arduino_photo_state\":\"" + jsonEscape(ultimoPhotoEstado) + "\"";
  s += ",\"error\":\"" + jsonEscape(erro) + "\"";
  s += ",\"event\":\"" + jsonEscape(ultimoEvento) + "\"";
  s += "}";
  server.send(200, "application/json; charset=utf-8", s);
}

bool jogHoldActive = false;
// Diagnostico: prioridade para dizer qual trava esta impedindo o movimento.
String motivoBloqueio(const String &cmd) {
  if (cmd=="STATUS" || cmd=="STOP" || cmd=="JOGSTOP") return "";
  if (!lastStatusMs || millis()-lastStatusMs>2500)
    return "Arduino sem telemetria recente (UART). Verifique RX/TX e alimentacao.";
  if (jogHoldActive) return "JOG continuo ativo: solte o botao e confirme a parada.";
  if (stage!=IDLE || executando || fotoLock || pendenteId || movimentando)
    return "Maquina ocupada, movendo ou aguardando PHOTOACK; confira /api/status.";
  if (cmd=="HOME" || cmd=="HOME X" || cmd=="HOME Y" || cmd=="UNHOME" ||
      cmd=="ENABLE 0" || cmd=="ENABLE 1") return "Comando invalido.";
  if (!homedX || !homedY)
    return "HOME X/Y nao confirmado no Arduino: confira referencia fisica e use HOME.";
  if (!enabled)
    return "Drivers desativados no Arduino: use Ativar drivers apos HOME.";
  return "Comando invalido ou coordenadas fora dos limites da maquina.";
}

unsigned long lastJogHttpMs = 0;
const unsigned long JOG_HTTP_WATCHDOG_MS = 1700UL;

bool podeComando(const String &cmd) {
  if (cmd=="STATUS" || cmd=="STOP" || cmd=="JOGSTOP") return true;
  if (jogHoldActive) return false;
  if (stage != IDLE || executando || fotoLock || pendenteId || movimentando ||
      !lastStatusMs || millis()-lastStatusMs>2500) return false;
  if (cmd=="HOME" || cmd=="HOME X" || cmd=="HOME Y" || cmd=="UNHOME" || cmd=="ENABLE 0" || cmd=="ENABLE 1") return true;
  if (cmd=="CENTER") return homedX && homedY && enabled;
  if (cmd.startsWith("MOVE X ")) {
    long x=0,y=0; char end=0;
    int n=sscanf(cmd.c_str(),"MOVE X %ld Y %ld%c",&x,&y,&end);
    return n==2 && homedX && homedY && enabled && x>=0 && x<=maxX && y>=0 && y<=maxY;
  }
  if (cmd.startsWith("SPEED ")) {
    String arg = cmd.substring(6);
    if (!arg.length()) return false;
    for (int i=0;i<arg.length();i++) if (!isDigit(arg[i])) return false;
    return arg.toInt() >= 500 && arg.toInt() <= 100000;
  }
  if (cmd.startsWith("JOGSTART ")) {
    char axis=0, tail=0; long dir=0;
    int n=sscanf(cmd.c_str(),"JOGSTART %c %ld%c",&axis,&dir,&tail);
    return n==2 && (axis=='X'||axis=='Y') && (dir==1||dir==-1) &&
           homedX && homedY && enabled;
  }
  if (cmd.startsWith("JOG X ") || cmd.startsWith("JOG Y ")) {
    String arg = cmd.substring(6);
    if (!arg.length() || arg.length() > 6) return false;
    int start = arg[0]=='-' ? 1 : 0;
    if (start == (int)arg.length()) return false;
    for (int i=start;i<(int)arg.length();i++) if(!isDigit(arg[i])) return false;
    long delta=arg.toInt();
    return delta != 0 && delta >= -5000 && delta <= 5000 && homedX && homedY && enabled;
  }
  if (cmd.startsWith("SETPOS X ")) {
    long x=0, y=0; char end=0;
    int n=sscanf(cmd.c_str(), "SETPOS X %ld Y %ld%c", &x, &y, &end);
    return n==2 && x>=0 && x<=maxX && y>=0 && y<=maxY;
  }
  return false;
}

// Aguarda POS posterior ao comando. HTTP 200 para HOME/ENABLE/SETPOS so
// depois que o proprio Arduino confirmar pela UART (nao pelo envio serial).
bool esperarConfirmacaoUART(const String &cmd, uint32_t seqAnterior) {
  const unsigned long inicio = millis();
  while (millis()-inicio < 2000UL) {
    lerUART();
    if (telemetriaSeq != seqAnterior) {
      bool esperado = false;
      if (cmd=="HOME") esperado = homedX && homedY;
      else if (cmd=="HOME X") esperado = homedX;
      else if (cmd=="HOME Y") esperado = homedY;
      else if (cmd=="UNHOME") esperado = !homedX && !homedY;
      else if (cmd=="ENABLE 1") esperado = enabled;
      else if (cmd=="ENABLE 0") esperado = !enabled && !homedX && !homedY;
      else if (cmd.startsWith("SETPOS X ")) {
        long x=0,y=0; char tail=0;
        esperado = sscanf(cmd.c_str(),"SETPOS X %ld Y %ld%c",&x,&y,&tail)==2 &&
                   eixoX==x && eixoY==y && !homedX && !homedY;
      }
      if (esperado) return true;
    }
    delay(8);
  }
  return false;
}

bool ipNotebookValido(const String &s);

bool verificarReceptorNotebook() {
  if (WiFi.status() != WL_CONNECTED || !ipNotebookValido(notebookIp) || apiKey.length() < 12)
    return false;
  HTTPClient http;
  const String url = "http://" + notebookIp + ":" + String(NOTEBOOK_PORT) + "/api/photos/ready";
  if (!http.begin(url)) return false;
  http.setConnectTimeout(1800);
  http.setTimeout(2500);
  http.addHeader("X-Photo-Token", apiKey);
  const int code = http.GET();
  const String body = code == 200 ? http.getString() : "";
  http.end();
  return code == 200 && body == "READY";
}

void initHttp() {
  const char* head[] = {"X-Api-Key"};
  server.collectHeaders(head, 1);
  server.on("/health", HTTP_GET, [](){ server.send(200,"text/plain","ESP32-CAM gateway online"); });
  server.on("/api/status", HTTP_GET, jsonStatus);
  server.on("/api/flash", HTTP_POST, [](){
    if (!autorizado()) return;
    if (!cameraReady) { server.send(503,"text/plain","Camera nao inicializada");return; }
    String cmd=server.arg("plain");cmd.trim();cmd.toUpperCase();
    if (cmd=="ON") {
      definirFlashManual(true);
    } else if (cmd=="OFF") {
      definirFlashManual(false);
    } else if (cmd=="AUTO ON") {
      flashAuto=true;
      prefs.putBool("flashauto",true);
    } else if (cmd=="AUTO OFF") {
      flashAuto=false;
      prefs.putBool("flashauto",false);
    } else {
      server.send(400,"text/plain","Use ON, OFF, AUTO ON ou AUTO OFF");return;
    }
    server.send(200,"application/json",String("{\"ok\":true,\"flash_manual\":")+
                (flashManual?"true":"false")+",\"flash_auto\":"+
                (flashAuto?"true":"false")+"}");
  });
  server.on("/api/route", HTTP_GET, [](){
    if (!autorizado()) return;
    String s;
    for (uint8_t i=0;i<totalPontos;i++) s += String(pontos[i].x)+","+String(pontos[i].y)+","+(pontos[i].foto?"1\n":"0\n");
    server.send(200,"text/plain; charset=utf-8",s);
  });
  server.on("/api/route", HTTP_POST, [](){
    if(!autorizado()) return;
    String msg;
    if(salvarRoteiro(server.arg("plain"),msg)) server.send(200,"text/plain",msg);
    else server.send(409,"text/plain",msg);
  });
  server.on("/api/start",HTTP_POST,[](){
    if(!autorizado()) return;
    if(stage!=IDLE || executando || pendenteId || fotoLock || movimentando || !enabled || !homedX || !homedY ||
       !lastStatusMs || millis()-lastStatusMs>1800 || !totalPontos) {
      server.send(409,"text/plain","Arduino deve estar conectado, parado, referenciado e sem foto pendente");return;
    }
    bool roteiroTemFoto = false;
    for (uint8_t i=0; i<totalPontos; ++i) {
      if (pontos[i].foto) { roteiroTemFoto = true; break; }
    }
    if (!roteiroTemFoto) {
      server.send(409,"text/plain","Roteiro sem fotografias: marque Foto em pelo menos um ponto antes de iniciar");return;
    }
    // Preflight antes de qualquer movimento: se a camera ou o receptor falhar,
    // a maquete permanece parada e nenhuma foto fica presa em PHOTO=WAIT.
    if (!cameraReady) {
      server.send(503,"text/plain","Camera nao inicializada; percurso autonomo bloqueado antes do movimento");return;
    }
    if (WiFi.status() != WL_CONNECTED) {
      server.send(503,"text/plain","Wi-Fi desconectado; percurso autonomo bloqueado antes do movimento");return;
    }
    if (!verificarReceptorNotebook()) {
      server.send(503,"text/plain","Notebook nao confirmou o receptor/gravação de fotos. Verifique IP, porta 8765, firewall e chave; nenhum movimento foi iniciado.");return;
    }
    indice=0; erro=""; executando=true;
    // Roteiro roda na ESP32 sem depender de comandos adicionais do notebook.
    proximoPonto();
    server.send(stage==WAIT_ARRIVAL?200:409,"text/plain",stage==WAIT_ARRIVAL?"Roteiro iniciado":"Nao foi possivel iniciar");
  });
  server.on("/api/stop",HTTP_POST,[](){
    if(!autorizado()) return;
    enviarArduino("STOP");
    jogHoldActive=false;
    stage=IDLE; pendenteId=0; fotoAckEnviado=false; indice=0; executando=false; ultimoEvento="Parada solicitada no painel";
    // PHOTO_LOCK permanece no Arduino se a foto ainda estava pendente.
    server.send(200,"text/plain","Parada solicitada; confira travas");
  });
  server.on("/api/command",HTTP_POST,[](){
    if(!autorizado()) return;
    String cmd=server.arg("plain");cmd.trim();cmd.toUpperCase();
    if(!podeComando(cmd)) {server.send(409,"text/plain",motivoBloqueio(cmd));return;}
    if (cmd=="JOGSTART X 1" || cmd=="JOGSTART X -1" ||
        cmd=="JOGSTART Y 1" || cmd=="JOGSTART Y -1") {
      // Renovacao inicial ate o primeiro ping do browser; Arduino tambem tem watchdog.
      jogHoldActive=true;
      lastJogHttpMs=millis();
    }
    if (cmd=="JOGSTOP" || cmd=="STOP") jogHoldActive=false;
    const uint32_t seqAntes = telemetriaSeq;
    enviarArduino(cmd);
    bool exigeConfirmacao = cmd=="HOME" || cmd=="HOME X" || cmd=="HOME Y" ||
        cmd=="UNHOME" || cmd=="ENABLE 0" || cmd=="ENABLE 1" || cmd.startsWith("SETPOS X ");
    if (exigeConfirmacao) {
      if (esperarConfirmacaoUART(cmd,seqAntes)) {
        server.send(200,"text/plain","Confirmado pelo Arduino: "+cmd);
      } else {
        server.send(504,"text/plain","Arduino nao confirmou "+cmd+
              ". Verifique /api/status e a conexao UART; nao repita movimento automaticamente.");
      }
    } else {
      server.send(200,"text/plain","Enviado ao Arduino (execucao ainda nao confirmada): "+cmd);
    }
  });
  server.on("/api/jog-ping", HTTP_POST, [](){
    if (!autorizado()) return;
    if (!jogHoldActive || stage!=IDLE || executando || fotoLock || pendenteId ||
        !homedX || !homedY || !enabled ||
        !lastStatusMs || millis()-lastStatusMs>2500) {
      server.send(409,"text/plain","JOG continuo nao autorizado");return;
    }
    lastJogHttpMs=millis();
    enviarArduino("JOGPING");
    server.send(200,"text/plain","OK:JOGPING");
  });
  // Foto manual: exige estado recente de Arduino parado; nao entra no fluxo
  // PHOTOACK da varredura e nunca altera o indice do roteiro.
  server.on("/api/manual-photo",HTTP_POST,[](){
    if(!autorizado()) return;
    if(stage!=IDLE || executando || pendenteId || fotoLock || movimentando ||
       !lastStatusMs || millis()-lastStatusMs>2500 || !homedX || !homedY ||
       eixoX<0 || eixoY<0) {
      server.send(409,"text/plain","Foto manual exige Arduino conectado, referenciado e parado, sem roteiro/trava ativa");
      return;
    }
    // Reserva o ID antes do upload para impedir reutilizacao em reinicios.
    nextId = (nextId % 899999998UL) + 1;
    prefs.putUInt("nextid", nextId);
    uint32_t id = nextId;
    ultimaFotoX=eixoX; ultimaFotoY=eixoY;
    erro="";
    if(fotografarEEnviar(id)) {
      ultimaFotoId=id;
      ultimoEvento="Foto manual " + String(id) + " recebida e salva no notebook";
      server.send(200,"application/json", "{\"ok\":true,\"id\":"+String(id)+"}");
    } else {
      ultimoEvento="Falha ao tirar foto manual";
      server.send(502,"text/plain", "Falha foto manual: "+erro);
    }
  });
  server.on("/api/retry",HTTP_POST,[](){
    if(!autorizado()) return;
    // Recuperacao manual SOMENTE para foto pendente, sem liberar trava.
    if(stage!=FAULT || !pendenteId || !fotoLock || pidArduino!=pendenteId || movimentando) {
      server.send(409,"text/plain","Sem fotografia pendente compativel");return;
    }
    erro="";stage=SETTLE;stageSince=millis();
    server.send(200,"text/plain","Nova tentativa de captura e envio iniciada");
  });
  server.on("/api/recover",HTTP_POST,[](){
    if(!autorizado()) return;
    if(stage!=IDLE && stage!=FAULT) {server.send(409,"text/plain","Interrompa o roteiro primeiro");return;}
    if(!fotoLock || pidArduino<=0 || movimentando) {server.send(409,"text/plain","Nao ha foto bloqueada");return;}
    // ABORTAR NAO E FOTO CONCLUIDA: operador assume perda da foto.
    enviarArduino("PHOTOABORT " + String(pidArduino));
    stage=IDLE;pendenteId=0;fotoAckEnviado=false;erro="";indice=0;executando=false;
    server.send(200,"text/plain","PHOTOABORT manual solicitado; confira o estado antes de prosseguir");
  });
  server.begin();
}

// Servidor MJPEG exclusivamente para calibracao. Tarefa independente da
// UART/controle e autenticada pelo cabecalho X-Api-Key, recebido do Flask.
// Uma conexao por vez: economiza PSRAM e rede da ESP32-CAM AI Thinker.
bool streamPermitido() {
  return cameraReady && WiFi.status()==WL_CONNECTED && !cameraUploadBusy &&
         !executando && stage==IDLE && !fotoLock && pendenteId==0;
}

void rejeitarVideo(WiFiClient &client, int codigo, const char* mensagem) {
  client.print("HTTP/1.1 ");client.print(codigo);client.print(" ");client.print(mensagem);
  client.print("\r\nContent-Type: text/plain\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
  client.stop();
}

void tarefaVideo(void* param) {
  (void)param;
  for (;;) {
    WiFiClient client = videoServer.available();
    if (!client) { vTaskDelay(pdMS_TO_TICKS(35)); continue; }
    client.setTimeout(1600);
    String requestLine = client.readStringUntil('\n'); requestLine.trim();
    bool validPath = requestLine=="GET /stream HTTP/1.1" || requestLine=="GET /stream HTTP/1.0";
    bool auth = false, complete = false;
    // Limita tamanho/quantidade de cabecalhos para evitar alocacao ilimitada.
    for (int n=0; n<22 && client.connected(); ++n) {
      String h = client.readStringUntil('\n');
      if (h.length()>220) break;
      h.trim();
      if (h.length()==0) { complete=true; break; }
      if (h.startsWith("X-Api-Key:")) {
        h.remove(0,10); h.trim(); auth=(h==apiKey);
      }
    }
    if (!validPath || !complete) { rejeitarVideo(client,400,"Bad Request"); continue; }
    if (!auth) { rejeitarVideo(client,403,"Forbidden"); continue; }
    if (!streamPermitido()) { rejeitarVideo(client,409,"Busy"); continue; }
    streamConnected=true;
    streamStep=1;
    client.setNoDelay(true);
    client.print("HTTP/1.1 200 OK\r\n"
                 "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
                 "Cache-Control: no-store, no-cache, must-revalidate\r\n"
                 "Pragma: no-cache\r\nConnection: close\r\n\r\n");
    while (client.connected() && streamPermitido()) {
      streamAttempts++;
      streamStep=1;
      if (xSemaphoreTake(cameraMutex, pdMS_TO_TICKS(500)) != pdTRUE) {
        streamLastFailure=1;
        vTaskDelay(pdMS_TO_TICKS(70)); continue;
      }
      streamStep=2;
      sensor_t* sensor = esp_camera_sensor_get();
      bool configured = sensor && (currentFrameMode == streamFrameMode ||
                         sensor->set_framesize(sensor, streamFrameMode) == 0);
      if (configured) currentFrameMode = streamFrameMode;
      if (!configured) streamLastFailure=2;
      streamStep=3;
      camera_fb_t* fb = configured ? esp_camera_fb_get() : nullptr;
      const uint16_t expectedWidth = streamFrameMode == FRAMESIZE_VGA ? 640 :
                                     streamFrameMode == FRAMESIZE_QVGA ? 320 : 160;
      if (!fb && configured) {streamCaptureFailures++;streamLastFailure=3;}
      if (fb) {
        streamLastWidth=fb->width;
        streamLastHeight=fb->height;
        streamLastFormat=(uint32_t)fb->format;
      }
      if (fb && fb->width != expectedWidth) {
        streamCaptureFailures++;streamLastFailure=4;
        esp_camera_fb_return(fb);
        fb = nullptr; // primeiro quadro com resolucao anterior
      }
      uint8_t* jpeg = nullptr;
      size_t jpegLen = 0;
      streamStep=4;
      if (fb && fb->format != PIXFORMAT_RGB565) {
        streamConvertFailures++;streamLastFailure=5;
      }
      bool converted = fb && fb->format == PIXFORMAT_RGB565 &&
                       frame2jpg(fb, STREAM_QUALIDADE_JPEG, &jpeg, &jpegLen);
      if (fb && fb->format == PIXFORMAT_RGB565 && !converted) {
        streamConvertFailures++;streamLastFailure=6;
      }
      if (fb) esp_camera_fb_return(fb);
      xSemaphoreGive(cameraMutex);
      if (!configured) { if (jpeg) free(jpeg); break; }
      if (!converted || !jpeg || jpegLen < 128) {
        if (converted && jpeg && jpegLen < 128) {
          streamConvertFailures++;streamLastFailure=7;
        }
        if (jpeg) free(jpeg);
        vTaskDelay(pdMS_TO_TICKS(100));
        continue;
      }
      streamLastJpegBytes=(uint32_t)jpegLen;
      streamStep=5;
      // Nunca publicar RGB565 bruto com o Content-Type image/jpeg.
      bool ok = client.printf("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                              (unsigned)jpegLen) > 0;
      if (ok) ok = client.write(jpeg, jpegLen) == jpegLen;
      if (ok) ok = client.print("\r\n") > 0;
      free(jpeg);
      if (!ok) {streamLastFailure=8;break;}
      streamFrames++;
      streamLastFrameMs=millis();
      streamStep=6;
      vTaskDelay(pdMS_TO_TICKS(400)); // ate ~2 fps, conforme CPU e Wi-Fi
    }
    client.stop();
    streamConnected=false;
    streamStep=0;
  }
}

void initCamera() {
  camera_config_t c = {};
  c.ledc_channel=LEDC_CHANNEL_0;c.ledc_timer=LEDC_TIMER_0;
  c.pin_d0=Y2_GPIO_NUM;c.pin_d1=Y3_GPIO_NUM;c.pin_d2=Y4_GPIO_NUM;c.pin_d3=Y5_GPIO_NUM;
  c.pin_d4=Y6_GPIO_NUM;c.pin_d5=Y7_GPIO_NUM;c.pin_d6=Y8_GPIO_NUM;c.pin_d7=Y9_GPIO_NUM;
  c.pin_xclk=XCLK_GPIO_NUM;c.pin_pclk=PCLK_GPIO_NUM;c.pin_vsync=VSYNC_GPIO_NUM;c.pin_href=HREF_GPIO_NUM;
  c.pin_sccb_sda=SIOD_GPIO_NUM;c.pin_sccb_scl=SIOC_GPIO_NUM;
  c.pin_pwdn=PWDN_GPIO_NUM;c.pin_reset=RESET_GPIO_NUM;
  c.xclk_freq_hz=20000000;
  c.pixel_format=PIXFORMAT_RGB565; // GC2145 nao tem JPEG nativo
  c.grab_mode=CAMERA_GRAB_WHEN_EMPTY;
  // RGB565 ocupa 2 bytes/pixel; usar um unico framebuffer.
  c.fb_count=1;
  c.jpeg_quality=12; // sem efeito em PIXFORMAT_RGB565 (qualidade em frame2jpg)
  if (psramFound()) {
    fotoFrameMode=FRAMESIZE_VGA;    // 640x480 nas fotografias
    streamFrameMode=FRAMESIZE_VGA;  // 640x480 tambem no stream, sem troca
    c.fb_location=CAMERA_FB_IN_PSRAM;
  } else {
    fotoFrameMode=FRAMESIZE_QQVGA;  // 160x120, memoria interna limitada
    streamFrameMode=FRAMESIZE_QQVGA;
    c.fb_location=CAMERA_FB_IN_DRAM;
  }
  c.frame_size=fotoFrameMode;
  currentFrameMode=c.frame_size;
  esp_err_t result=esp_camera_init(&c);
  if (result != ESP_OK) {
    erro="Falha camera (" + String(esp_err_to_name(result)) + ", 0x" +
         String((uint32_t)result, HEX) + ")";
    stage=FAULT;
    cameraReady=false;
    return;
  }
  sensor_t* detected=esp_camera_sensor_get();
  if (detected) cameraSensorPid="0x" + String(detected->id.PID, HEX);
  cameraReady=true;
}


// Le uma linha do Monitor Serial (115200, final de linha NL ou CR+NL).
// A senha nao e impressa pelo firmware, mas pode aparecer no campo de entrada
// da Arduino IDE. O operador deve evitar compartilhar essa tela.
String lerEntradaSerial(const char* rotulo, uint8_t limite) {
  Serial.print(rotulo);
  String entrada;
  bool longa = false;
  static bool aguardaLF = false;
  for (;;) {
    while (Serial.available()) {
      char c = static_cast<char>(Serial.read());
      if (aguardaLF) { aguardaLF = false; if (c=='\n') continue; }
      if (c == '\n' || c == '\r') {
        if (c == '\r') aguardaLF = true;
        if (longa) { Serial.println("Entrada grande demais; tente novamente."); return String(""); }
        entrada.trim();
        return entrada;
      }
      if (c >= 32 && c <= 126) {
        if (entrada.length() < limite) entrada += c;
        else longa = true;
      }
    }
    delay(5);
  }
}

bool wifiSenhaValida(const String &s) {
  return s.length() >= 8 && s.length() <= 63;
}
bool chaveValida(const String &s) {
  if (s.length() < 12 || s.length() > 64) return false;
  for (size_t i=0; i<s.length(); i++) {
    char c=s[i];
    if (!(isAlphaNumeric(c) || c=='_' || c=='-' || c=='.')) return false;
  }
  return true;
}
bool ipNotebookValido(const String &s) {
  IPAddress ip;
  return ip.fromString(s) && ip != IPAddress(0,0,0,0) && ip != IPAddress(255,255,255,255);
}

void lerConfiguracaoPersistida() {
  wifiSsid = prefs.getString("wssid", "");
  wifiPassword = prefs.getString("wpass", "");
  notebookIp = prefs.getString("nbook", "");
  apiKey = prefs.getString("apikey", "");
  redeConfigurada = prefs.getBool("netok", false) &&
                   wifiSsid.length()>=1 && wifiSsid.length()<=32 &&
                   wifiSenhaValida(wifiPassword) && ipNotebookValido(notebookIp) &&
                   chaveValida(apiKey);
}

// A configuracao e iniciada SO na primeira gravacao ou ao digitar CONFIG
// nos primeiros segundos apos RESET. Nao ha menu durante o roteiro.
void configurarPeloSerial() {
  Serial.println("\n=== ATLAS CNC: CONFIGURACAO SERIAL ===");
  Serial.println("ATENCAO: Arduino UART desconectada e motores desligados.");
  Serial.println("Monitor Serial: 115200 baud; final de linha = Nova linha.");
  Serial.println("Senha Wi-Fi e chave nao serao mostradas de volta.");
  if (redeConfigurada) {
    Serial.print("SSID atual: "); Serial.println(wifiSsid);
    Serial.print("IP notebook atual: "); Serial.println(notebookIp);
    Serial.println("ENTER conserva o valor anterior de cada campo.");
  }
  String ssid=wifiSsid, senha=wifiPassword, ip=notebookIp, chave=apiKey;
  for (;;) {
    String v=lerEntradaSerial("SSID da rede Wi-Fi 2,4 GHz: ", 32);
    if (v.length()) ssid=v;
    if (ssid.length()>=1 && ssid.length()<=32) break;
    Serial.println("SSID invalido (1 a 32 caracteres).");
  }
  for (;;) {
    String v=lerEntradaSerial("Senha Wi-Fi (8 a 63 caracteres): ", 63);
    if (v.length()) senha=v;
    if (wifiSenhaValida(senha)) break;
    Serial.println("Senha invalida. Use WPA2, 8 a 63 caracteres.");
  }
  for (;;) {
    String v=lerEntradaSerial("IP IPv4 do notebook (hostname -I): ", 15);
    if (v.length()) ip=v;
    if (ipNotebookValido(ip)) break;
    Serial.println("IP invalido. Exemplo: 192.168.1.100");
  }
  for (;;) {
    String v=lerEntradaSerial("Chave API (12 a 64, letras/numeros/_/./-): ", 64);
    if (v.length()) chave=v;
    if (chaveValida(chave)) break;
    Serial.println("Chave invalida. Nao use espacos.");
  }
  Serial.print("Gravar configuracao? Digite SIM: ");
  String aceitar=lerEntradaSerial("",3);
  aceitar.toUpperCase();
  if (aceitar!="SIM") {
    Serial.println("Cancelado. Reinicie para tentar novamente.");
    return;
  }
  // A marca netok e gravada POR ULTIMO para nao iniciar com dados parciais.
  prefs.putBool("netok",false);
  bool ok=(prefs.putString("wssid",ssid)==ssid.length());
  ok=(prefs.putString("wpass",senha)==senha.length()) && ok;
  ok=(prefs.putString("nbook",ip)==ip.length()) && ok;
  ok=(prefs.putString("apikey",chave)==chave.length()) && ok;
  if (ok) ok=prefs.putBool("netok",true)==1;
  if (!ok) {
    Serial.println("ERRO ao salvar na NVS. Verifique a memoria flash.");
    return;
  }
  lerConfiguracaoPersistida();
  Serial.println("[OK] Configuracao salva na memoria da ESP32-CAM.");
  Serial.println("Remova o adaptador serial, reconecte a UART do Arduino com tudo desligado.");
  Serial.println("Reinicie a placa para entrar em operacao normal.");
}

// Nao emitir banners quando o Arduino esta conectado: a UART0 e compartilhada.
// Para editar: conectar adaptador USB serial sem Arduino, abrir monitor 115200,
// pressionar RESET e enviar CONFIG + Nova linha em ate 9 segundos.
void inicializarConfiguracaoSerial() {
  lerConfiguracaoPersistida();
  if (redeConfigurada) {
    String comando;
    uint32_t inicio=millis();
    while (millis()-inicio < BOOT_CONFIG_WINDOW_MS) {
      while (Serial.available()) {
        char c=static_cast<char>(Serial.read());
        if (c=='\n' || c=='\r') {
          comando.trim();comando.toUpperCase();
          if (comando=="CONFIG") {
            // Descartar LF residual quando o monitor envia CR+LF.
            if (c=='\r') {
              delay(20);
              if (Serial.peek()=='\n') Serial.read();
            }
            // O menu so pode ser usado com Arduino desconectado.
            configurarPeloSerial();
            // Se cancelou, NVS anterior ainda esta marcada invalida?
            // Reiniciar apos configuracao, sem mandar comandos ao Arduino.
            Serial.println("Reinicie a ESP32-CAM (RESET).");
            for (;;) delay(200);
          }
          comando="";
        } else if (c>=32 && c<=126) {
          if (comando.length()<20) comando+=c;
        }
      }
      delay(5);
    }
    return;
  }
  Serial.println("\nATLAS CNC: SEM CONFIGURACAO Wi-Fi.");
  Serial.println("Desconecte RX/TX do Arduino e configure pelo Monitor Serial.");
  // Descarta caracteres residuais do boot antes do menu.
  while (Serial.available()) Serial.read();
  while (!redeConfigurada) {
    configurarPeloSerial();
    if (!redeConfigurada) Serial.println("Configure novamente ou reinicie.");
  }
  Serial.println("Reinicie a placa (RESET) antes de ligar a maquina.");
  for (;;) delay(200);
}

void setup() {
  // GPIO4 OFF desde o inicio. Nao ligar manualmente durante a gravacao.
  digitalWrite(FLASH_LED_GPIO,LOW);
  pinMode(FLASH_LED_GPIO,OUTPUT);
  Serial.begin(115200);           // UART0: RX GPIO3, TX GPIO1 -> Arduino Uno
  Serial.setDebugOutput(false);   // NAO imprimir logs na UART dos comandos
  // UART0 tambem chega ao Arduino: mensagens do driver "E (...) CAMERA" nao
  // podem ser interpretadas como comandos CNC. Erros ficam em /api/status.
  esp_log_level_set("*", ESP_LOG_NONE);
  linhaSerial.reserve(260);
  prefs.begin("maquete",false);
  flashAuto=prefs.getBool("flashauto",false); // opt-in persistente, LED inicia apagado
  inicializarConfiguracaoSerial();
  nextId=prefs.getUInt("nextid",1);
  carregarRoteiro();
  cameraMutex = xSemaphoreCreateMutex();
  if (!cameraMutex) { erro="Sem memoria para mutex da camera";stage=FAULT; }
  else initCamera();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(wifiSsid.c_str(),wifiPassword.c_str());
  // Opcional: resolucao por atlas-cnc.local em redes com mDNS liberado.
  // Sem depender de WiFi para aceitar estado UART, tenta conexao em segundo plano
  initHttp();
  if (cameraReady) {
    videoServer.begin();
    BaseType_t taskOk=xTaskCreatePinnedToCore(tarefaVideo,"video-mjpeg",8192,nullptr,1,nullptr,0);
    if (taskOk!=pdPASS) erro="Stream indisponivel: sem memoria para tarefa";
  }
  enviarArduino("STATUS");
}

void loop() {
  // mDNS so e iniciado depois de receber um IP valido do Wi-Fi.
  if (!mdnsAtivo && WiFi.status()==WL_CONNECTED &&
      millis()-ultimoMdnsMs>5000) {
    ultimoMdnsMs=millis();
    if (MDNS.begin("atlas-cnc")) {
      MDNS.addService("http", "tcp", 80);
      mdnsAtivo = true;
    }
  }
  if (mdnsAtivo && WiFi.status()!=WL_CONNECTED) {
    MDNS.end();
    mdnsAtivo = false;
  }
  lerUART();
  server.handleClient();
  if (jogHoldActive && (unsigned long)(millis()-lastJogHttpMs)>JOG_HTTP_WATCHDOG_MS) {
    enviarArduino("JOGSTOP");
    jogHoldActive=false;
    ultimoEvento="JOG parado: heartbeat do painel expirou";
  }
  uint32_t now=millis();
  if (flashManual && (uint32_t)(now-flashManualDesdeMs)>=FLASH_MANUAL_TIMEOUT_MS) {
    definirFlashManual(false);
    ultimoEvento="Flash manual desligado por tempo de seguranca (60 s)";
  }
  if(now-lastStatusRequest>500) {lastStatusRequest=now;enviarArduino("STATUS");}
  if(stage==WAIT_ARRIVAL && now-heartbeatAt>550) {heartbeatAt=now;enviarArduino("SCANPING");}
  if(stage==WAIT_ARRIVAL && now-stageSince>ARRIVAL_TIMEOUT_MS) falhar("Tempo limite do movimento");
  if(stage==SETTLE && now-stageSince>=PHOTO_SETTLE_MS) stage=TAKE_PHOTO;
  if(stage==TAKE_PHOTO) {
    if(!fotoLock || pidArduino!=pendenteId || movimentando) {
      // Arduino deve confirmar PHOTO=WAIT para evitar qualquer foto fora do ponto.
      if(now-stageSince>8000) falhar("Arduino nao confirmou bloqueio de foto");
    } else {
      if(fotografarEEnviar(pendenteId)) {
        // Arma primeiro o estado; a resposta UART pode chegar rapidamente.
        stage=WAIT_PHOTOACK;
        stageSince=millis();
        fotoAckEnviado=true;
        fotoAckTentativas=1;
        ultimoAckMs=millis();
        enviarArduino("PHOTOACK " + String(pendenteId));
        enviarArduino("STATUS");
      } else falhar(erro); // SEM PHOTOACK quando captura/upload falham
    }
  }
  // IMPORTANTE: fotografarEEnviar() e sincrono e pode demorar segundos.
  // Recalcular now APOS o upload: caso contrario, now < stageSince e a
  // subtracao uint32_t produz um valor gigante (timeout imediato!).
  now = millis();
  if(stage==WAIT_PHOTOACK && fotoAckEnviado) {
    // Nunca repetir PHOTOACK de outro ponto. So repetir quando a telemetria
    // confirma que a MESMA foto ainda esta travada no Arduino.
    if (now-ultimoAckMs >= PHOTOACK_RETRY_MS) {
      if (fotoLock && pidArduino == pendenteId && !movimentando &&
          now-lastStatusMs<1800 && fotoAckTentativas<6) {
        enviarArduino("PHOTOACK " + String(pendenteId));
        fotoAckTentativas++;
        ultimoAckMs=now;
      }
      enviarArduino("STATUS");
    }
    if (now-stageSince>PHOTOACK_TIMEOUT_MS) {
      falhar("PHOTOACK sem confirmacao: "+ultimoPhotoEstado+
             " tentativas="+String(fotoAckTentativas)+
             " ultimoUART="+ultimaLinhaArduino.substring(0,65));
    }
  }
  // nao avancar quando terminar tudo. Ultimo ponto permanece como posicao final.
  if(stage==IDLE && executando && indice>=totalPontos) {executando=false;ultimoEvento="Percurso concluido";}
  if(stage==IDLE && pendenteId==0 && indice<totalPontos && executando) proximoPonto();
  delay(2);
}
