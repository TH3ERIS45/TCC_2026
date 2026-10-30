/*
 * CNC Shield v3 - Firmware v8.0 UART DIRETO + HOME MANUAL + EIXOS FINAIS
 * Arduino Uno + CNC Shield v3 + A4988/DRV8825
 *
 * Esta versão NÃO usa fim de curso/sensor.
 * O HOME é manual: ele NÃO movimenta os motores e NÃO muda a posição.
 * Ele apenas confirma que a posição física foi alinhada à posição mostrada
 * no software naquele instante.
 *
 * Fluxo recomendado:
 *   1) Liberar os eixos (ENABLE 0), se for mover a máquina com a mão.
 *   2) No software, colocar o modelo na referência conhecida (ex.: MAX).
 *   3) Fisicamente, colocar a máquina na mesma posição.
 *   4) Enviar HOME (marca X/Y como sincronizados, sem mover nada).
 *   5) Travar os eixos (ENABLE 1) e operar normalmente.
 *
 * Importante: sem sensores/encoders o Arduino não mede posição física.
 * Depois do HOME manual, a posição é estimada pela contagem de passos.
 * Se os eixos forem movidos à mão ou o motor perder passos, faça HOME manual
 * novamente.
 *
 * Comandos:
 *   STATUS / ?
 *   HOME              -> confirma X/Y na posição atual, sem mover
 *   HOME X / HOME Y   -> confirma somente um eixo, sem mover
 *   UNHOME            -> invalida a referência manual
 *   SETPOS X <passos> Y <passos> -> muda somente a coordenada lógica, sem motor
 *   ZERO              -> SETPOS X 0 Y 0 e invalida referência
 *   JOGSTART X 1 / -1
 *   JOGSTART Y 1 / -1
 *   JOGSTOP / STOP
 *   JOG X <passos>
 *   JOG Y <passos>
 *   MOVE X <passos> Y <passos>
 *   CENTER            -> move para o centro geométrico; interface mostra X=0, Y=0
 *   SPEED <us_por_passo>
 *   ENABLE 0/1
 *   SCANMOVE X <passos> Y <passos> P <0|1> ID <1..999999999>
 *      -> P 1 exige foto; o proximo movimento fica BLOQUEADO ate PHOTOACK ID.
 *   PHOTOACK <id>    -> ESP32 confirma que o notebook recebeu e salvou JPEG.
 *   PHOTOABORT <id>  -> liberacao MANUAL em caso de falha (somente operador).
 *   STATUS exibe PROTO=2,PHOTO=WAIT/READY,PID=<id>.
 *   STOP nunca limpa PHOTO=WAIT; nao ha movimento enquanto foto pendente.
 */

#include <Arduino.h>

// ============================================================
// PINAGEM CNC SHIELD V3
// ============================================================
const uint8_t PIN_ENABLE = 8;

// IMPORTANTE: troca SOMENTE de canal físico.
// Na interface/maquete: X = transversal (carrinho), Y = longitudinal (pórtico).
// Pela ligação física atual, o motor lógico X está no canal Y da CNC Shield
// e o motor lógico Y está no canal X da CNC Shield.
const uint8_t PIN_STEP_X = 3;  // canal Y da CNC Shield -> X lógico/transversal
const uint8_t PIN_DIR_X  = 6;
const uint8_t PIN_STEP_Y = 2;  // canal X da CNC Shield -> Y lógico/longitudinal
const uint8_t PIN_DIR_Y  = 5;

// ============================================================
// GEOMETRIA REAL DA MAQUETE (OpenSCAD)
// ============================================================
// X: medida externa observada do conjunto ≈ 400 mm; motor ≈ 50 mm.
// O curso útil calibrado do centro do carrinho é -164..+164 mm => 328 mm.
// A medida externa do conjunto NÃO é o curso útil.
// Y: centro do pórtico  -455..+455 mm => 910 mm
const float TRAVEL_X_MM = 328.0f;
const float TRAVEL_Y_MM = 910.0f;

// ============================================================
// TRANSMISSÃO
// ============================================================
// Ajuste conforme os jumpers reais da CNC Shield.
const long MOTOR_STEPS_PER_REV = 200L;
const int MICROSTEPS_X = 1;
const int MICROSTEPS_Y = 1;
const float GT2_PITCH_MM = 2.0f;
const int PULLEY_TEETH_X = 20;
const int PULLEY_TEETH_Y = 20;

const float STEPS_PER_MM_X = (MOTOR_STEPS_PER_REV * MICROSTEPS_X) /
                             (GT2_PITCH_MM * PULLEY_TEETH_X);
const float STEPS_PER_MM_Y = (MOTOR_STEPS_PER_REV * MICROSTEPS_Y) /
                             (GT2_PITCH_MM * PULLEY_TEETH_Y);

const long MAX_X = (long)(TRAVEL_X_MM * STEPS_PER_MM_X + 0.5f);
const long MAX_Y = (long)(TRAVEL_Y_MM * STEPS_PER_MM_Y + 0.5f);

// ============================================================
// SENTIDO ELÉTRICO
// ============================================================
// + significa aumentar a coordenada interna da máquina (0..MAX).
// A interface converte esta posição para o sistema OpenSCAD centrado em 0.
// Se um eixo físico andar invertido, troque HIGH <-> LOW somente nele.
// Calibrado para a maquete: X+ move fisicamente para a direita
// e X- move fisicamente para a esquerda.
const uint8_t DIR_X_POS = LOW;
const uint8_t DIR_Y_POS = HIGH;
const uint8_t DIR_X_NEG = (DIR_X_POS == HIGH) ? LOW : HIGH;
const uint8_t DIR_Y_NEG = (DIR_Y_POS == HIGH) ? LOW : HIGH;

// ============================================================
// VELOCIDADE
// ============================================================
const unsigned long MIN_STEP_DELAY_US = 500UL;      // 2000 passos/s
const unsigned long MAX_STEP_DELAY_US = 100000UL;  // 10 passos/s
unsigned long stepDelayMicros = 16667UL;            // ~60 passos/s

// ============================================================
// ESTADO
// ============================================================
enum MotionMode : uint8_t {
  MOTION_IDLE = 0,
  MOTION_TARGET = 1,
  MOTION_JOG = 2
};

// Antes do HOME manual, estes valores são apenas coordenadas lógicas.
// Começamos visualmente no centro para permitir movimento para os dois lados.
long posX = MAX_X / 2;
long posY = MAX_Y / 2;
long targetX = MAX_X / 2;
long targetY = MAX_Y / 2;

bool homedX = false;
bool homedY = false;
bool driversEnabled = true;
bool scanInProgress = false;  // comando automatico SCANMOVE aguardando chegada
bool scanNeedsPhoto = false; // foto solicitada ao chegar
bool photoPending = false;   // TRAVA: impede qualquer movimento ate PHOTOACK
long scanId = 0;
long photoId = 0;
unsigned long lastScanPingMillis = 0;
const unsigned long SCAN_WATCHDOG_MS = 3500UL; // se ESP32 sumir, para o movimento
MotionMode motionMode = MOTION_IDLE;

char jogAxis = 0;
int8_t jogDir = 0;
unsigned long lastJogPingMillis = 0;
const unsigned long JOG_WATCHDOG_MS = 1100UL; // independe de Wi-Fi, ESP32 e browser
const unsigned long MIN_JOG_DELAY_US = 8000UL; // segurando: maximo 125 passos/s

unsigned long lastStepMicros = 0;
unsigned long lastTelemetryMillis = 0;
const unsigned long TELEMETRY_MOVING_MS = 50;
const unsigned long TELEMETRY_IDLE_MS = 500;

String inputBuffer;

// ============================================================
// UTILITÁRIOS
// ============================================================
bool isMoving() {
  return motionMode != MOTION_IDLE;
}

long clampX(long v) {
  if (v < 0) return 0;
  if (v > MAX_X) return MAX_X;
  return v;
}

long clampY(long v) {
  if (v < 0) return 0;
  if (v > MAX_Y) return MAX_Y;
  return v;
}

void pulsePin(uint8_t pin) {
  digitalWrite(pin, HIGH);
  delayMicroseconds(5);
  digitalWrite(pin, LOW);
}

void setDrivers(bool enabled) {
  driversEnabled = enabled;
  digitalWrite(PIN_ENABLE, enabled ? LOW : HIGH);

  if (!enabled) {
    scanInProgress = false;
    scanNeedsPhoto = false;
    // NUNCA apague photoPending ao liberar os motores.
    // Ao liberar os motores, a máquina pode ser movida à mão.
    // Portanto a referência deixa de ser confiável até HOME manual novamente.
    homedX = false;
    homedY = false;
    motionMode = MOTION_IDLE;
    jogAxis = 0;
    jogDir = 0;
    targetX = posX;
    targetY = posY;
  }
}

void sendTelemetry() {
  Serial.print(F("POS:X=")); Serial.print(posX);
  Serial.print(F(",Y=")); Serial.print(posY);
  Serial.print(F(",STATUS=")); Serial.print(isMoving() ? F("MOVING") : F("IDLE"));
  Serial.print(F(",PROTO=2"));
  Serial.print(F(",PHOTO=")); Serial.print(photoPending ? F("WAIT") : F("READY"));
  Serial.print(F(",PID=")); Serial.print(photoPending ? photoId : 0);
  Serial.print(F(",EN=")); Serial.print(driversEnabled ? 1 : 0);
  Serial.print(F(",HX=")); Serial.print(homedX ? 1 : 0);
  Serial.print(F(",HY=")); Serial.print(homedY ? 1 : 0);
  Serial.print(F(",XMAX=")); Serial.print(MAX_X);
  Serial.print(F(",YMAX=")); Serial.print(MAX_Y);
  Serial.print(F(",SPMX=")); Serial.print(STEPS_PER_MM_X, 4);
  Serial.print(F(",SPMY=")); Serial.print(STEPS_PER_MM_Y, 4);
  Serial.print(F(",XMM=")); Serial.print(posX / STEPS_PER_MM_X, 2);
  Serial.print(F(",YMM=")); Serial.print(posY / STEPS_PER_MM_Y, 2);
  // Coordenadas centradas equivalentes ao OpenSCAD (apenas telemetria).
  Serial.print(F(",CXMM=")); Serial.print((posX / STEPS_PER_MM_X) - (TRAVEL_X_MM / 2.0f), 2);
  Serial.print(F(",CYMM=")); Serial.println((posY / STEPS_PER_MM_Y) - (TRAVEL_Y_MM / 2.0f), 2);
}

void stopMotion() {
  scanInProgress = false;
  scanNeedsPhoto = false;
  // Mantenha photoPending ate confirmacao explicita.
  motionMode = MOTION_IDLE;
  jogAxis = 0;
  jogDir = 0;
  targetX = posX;
  targetY = posY;
  sendTelemetry();
}

// ============================================================
// PASSOS COM SOFT LIMIT SEMPRE ATIVO
// ============================================================
// Isto evita a coordenada continuar aumentando depois de chegar ao limite
// lógico 0..MAX. Não é um sensor físico: depende da sincronização manual.
bool stepLogicalX(int8_t logicalDir) {
  if (logicalDir > 0) {
    if (posX >= MAX_X) return false;
    digitalWrite(PIN_DIR_X, DIR_X_POS);
    pulsePin(PIN_STEP_X);
    posX++;
    return true;
  }

  if (posX <= 0) return false;
  digitalWrite(PIN_DIR_X, DIR_X_NEG);
  pulsePin(PIN_STEP_X);
  posX--;
  return true;
}

bool stepLogicalY(int8_t logicalDir) {
  if (logicalDir > 0) {
    if (posY >= MAX_Y) return false;
    digitalWrite(PIN_DIR_Y, DIR_Y_POS);
    pulsePin(PIN_STEP_Y);
    posY++;
    return true;
  }

  if (posY <= 0) return false;
  digitalWrite(PIN_DIR_Y, DIR_Y_NEG);
  pulsePin(PIN_STEP_Y);
  posY--;
  return true;
}

// ============================================================
// HOME MANUAL / SINCRONIZAÇÃO
// ============================================================
void manualHomeXY() {
  stopMotion();
  homedX = true;
  homedY = true;
  Serial.print(F("[HOME MANUAL] Sincronizado. Coordenada OpenSCAD: X="));
  Serial.print((posX / STEPS_PER_MM_X) - (TRAVEL_X_MM / 2.0f), 2);
  Serial.print(F(" mm Y="));
  Serial.print((posY / STEPS_PER_MM_Y) - (TRAVEL_Y_MM / 2.0f), 2);
  Serial.println(F(" mm"));
  sendTelemetry();
}

void manualHomeAxis(char axis) {
  stopMotion();
  axis = toupper(axis);
  if (axis == 'X') homedX = true;
  else if (axis == 'Y') homedY = true;
  else return;

  Serial.print(F("[HOME MANUAL] Eixo "));
  Serial.print(axis);
  Serial.print(F(" sincronizado. Coordenada OpenSCAD = "));
  if (axis == 'X') Serial.print((posX / STEPS_PER_MM_X) - (TRAVEL_X_MM / 2.0f), 2);
  else Serial.print((posY / STEPS_PER_MM_Y) - (TRAVEL_Y_MM / 2.0f), 2);
  Serial.println(F(" mm"));
  sendTelemetry();
}

// SETPOS altera apenas a coordenada lógica. Nenhum motor se move.
// A referência do eixo alterado é invalidada até HOME manual.
void setLogicalPosition(String cmd) {
  long newX = posX;
  long newY = posY;
  bool hasX = false;
  bool hasY = false;

  int ix = cmd.indexOf("X ");
  int iy = cmd.indexOf("Y ");

  if (ix >= 0) {
    String sx = cmd.substring(ix + 2, (iy > ix) ? iy : cmd.length());
    sx.trim();
    newX = clampX(sx.toInt());
    hasX = true;
  }

  if (iy >= 0) {
    String sy = cmd.substring(iy + 2);
    sy.trim();
    newY = clampY(sy.toInt());
    hasY = true;
  }

  if (!hasX && !hasY) {
    Serial.println(F("[ERRO] SETPOS sem eixo."));
    return;
  }

  stopMotion();
  if (hasX) {
    posX = targetX = newX;
    homedX = false;
  }
  if (hasY) {
    posY = targetY = newY;
    homedY = false;
  }

  Serial.println(F("[SETPOS] Coordenada logica alterada sem mover motores."));
  sendTelemetry();
}

// ============================================================
// AUTO-TESTE CURTO (vai e volta sem alterar a referência final)
// ============================================================
void runSelfTest() {
  if (!driversEnabled || !homedX || !homedY || isMoving()) {
    Serial.println(F("[ERRO] TEST exige HOME, drivers e maquina parada."));
    return;
  }

  stopMotion();
  const long startX = posX;
  const long startY = posY;
  const long testX = ((long)MOTOR_STEPS_PER_REV < (MAX_X - posX)) ? (long)MOTOR_STEPS_PER_REV : (MAX_X - posX);
  const long testY = ((long)MOTOR_STEPS_PER_REV < (MAX_Y - posY)) ? (long)MOTOR_STEPS_PER_REV : (MAX_Y - posY);

  Serial.println(F("[TEST] Movimento curto + e retorno."));
  long n = (testX > testY) ? testX : testY;
  for (long i = 0; i < n; i++) {
    unsigned long t0 = micros();
    if (i < testX) stepLogicalX(1);
    if (i < testY) stepLogicalY(1);
    while ((unsigned long)(micros() - t0) < stepDelayMicros) {}
  }
  delayMicroseconds(200000UL);
  n = (testX > testY) ? testX : testY;
  for (long i = 0; i < n; i++) {
    unsigned long t0 = micros();
    if (i < testX) stepLogicalX(-1);
    if (i < testY) stepLogicalY(-1);
    while ((unsigned long)(micros() - t0) < stepDelayMicros) {}
  }

  posX = targetX = startX;
  posY = targetY = startY;
  Serial.println(F("[TEST] Concluido. Coordenada retornou ao ponto inicial."));
  sendTelemetry();
}

// ============================================================
// COMANDOS
// ============================================================
void startContinuousJog(char axis, int8_t dir) {
  axis = toupper(axis);
  if ((axis != 'X' && axis != 'Y') || (dir != -1 && dir != 1)) {
    Serial.println(F("[ERRO] JOGSTART invalido."));
    return;
  }
  if (!driversEnabled || !homedX || !homedY || photoPending || scanInProgress || motionMode != MOTION_IDLE) {
    Serial.println(F("[ERRO] JOGSTART exige HOME, drivers e maquina parada sem foto pendente."));
    return;
  }

  lastJogPingMillis = millis();
  jogAxis = axis;
  jogDir = dir;
  motionMode = MOTION_JOG;
  Serial.print(F("[JOG] START ")); Serial.print(axis); Serial.print(' '); Serial.println(dir);
}

// Validacao no Uno tambem: comandos seriais nao podem contornar o gateway.
bool lerJogSeguro(String txt, long &delta) {
  txt.trim();
  if (!txt.length() || txt.length()>6) return false;
  unsigned int inicio = (txt.charAt(0)=='-') ? 1 : 0;
  if (inicio >= txt.length()) return false;
  for (unsigned int i=inicio;i<txt.length();i++) if (!isDigit(txt.charAt(i))) return false;
  delta=txt.toInt();
  return delta!=0 && delta>=-5000L && delta<=5000L;
}

bool lerCoordenadaSegura(String txt, long &valor, long limite) {
  txt.trim();
  if (!txt.length() || txt.length()>7) return false;
  for (unsigned int i=0;i<txt.length();i++) if (!isDigit(txt.charAt(i))) return false;
  valor=txt.toInt();
  return valor>=0 && valor<=limite;
}

void processCommand(String cmd) {
  cmd.trim();
  if (!cmd.length()) return;
  cmd.toUpperCase();

  if (cmd == "STOP" || cmd == "JOGSTOP") {
    stopMotion();
    return;
  }

  if (cmd == "STATUS" || cmd == "?") {
    sendTelemetry();
    return;
  }

  if (cmd == "SCANPING") {
    if (scanInProgress) lastScanPingMillis = millis();
    return;
  }
  if (cmd == "JOGPING") {
    if (motionMode == MOTION_JOG && !photoPending && driversEnabled)
      lastJogPingMillis = millis();
    return;
  }

  if (cmd.startsWith("PHOTOACK ") || cmd.startsWith("PHOTOABORT ")) {
    bool abortando = cmd.startsWith("PHOTOABORT ");
    int inicio = abortando ? 11 : 9;
    String numero = cmd.substring(inicio); numero.trim();
    if (!photoPending || !numero.length()) {
      Serial.println(F("[ERRO] Nao existe foto pendente para confirmar."));
      return;
    }
    for (unsigned int j = 0; j < numero.length(); j++) {
      if (!isDigit(numero.charAt(j))) {
        Serial.println(F("[ERRO] ID de foto invalido.")); return;
      }
    }
    long id = numero.toInt();
    if (id <= 0 || id != photoId || isMoving()) {
      Serial.println(F("[ERRO] PHOTOACK/PHOTOABORT: ID errado ou maquina em movimento."));
      return;
    }
    // PHOTOABORT nao significa foto concluida: apenas o operador pode liberar.
    photoPending = false;
    photoId = 0;
    if (abortando) Serial.print(F("OK:PHOTOABORT ID="));
    else Serial.print(F("OK:PHOTOACK ID="));
    Serial.println(id);
    sendTelemetry();
    return;
  }

  // Trava fisica de passos por software no Arduino, nao apenas no PC.
  // STOP e STATUS foram tratados antes: mesmo com falha do notebook nao avanca.
  if (photoPending) {
    Serial.print(F("[ERRO] PHOTO_LOCK: aguardando PHOTOACK ID="));
    Serial.println(photoId);
    return;
  }
  if (scanInProgress) {
    Serial.println(F("[ERRO] SCANMOVE em andamento. Apenas STOP, STATUS e SCANPING."));
    return;
  }

  if (cmd == "TEST") {
    runSelfTest();
    return;
  }

  if (cmd == "HOME") {
    manualHomeXY();
    return;
  }
  if (cmd == "HOME X") {
    manualHomeAxis('X');
    return;
  }
  if (cmd == "HOME Y") {
    manualHomeAxis('Y');
    return;
  }
  if (cmd == "UNHOME") {
    homedX = false;
    homedY = false;
    Serial.println(F("[HOME MANUAL] Referencia invalidada."));
    sendTelemetry();
    return;
  }

  if (cmd.startsWith("SETPOS ")) {
    setLogicalPosition(cmd);
    return;
  }

  if (cmd == "ZERO") {
    stopMotion();
    posX = targetX = 0;
    posY = targetY = 0;
    homedX = false;
    homedY = false;
    Serial.println(F("[ZERO] Coordenada logica = 0,0. Motores nao se moveram."));
    sendTelemetry();
    return;
  }

  if (cmd.startsWith("ENABLE ")) {
    String value = cmd.substring(7); value.trim();
    if (value != "0" && value != "1") {
      Serial.println(F("[ERRO] ENABLE exige 0 ou 1."));
      return;
    }
    setDrivers(value == "1");
    sendTelemetry();
    return;
  }

  if (cmd.startsWith("SPEED ")) {
    long us = cmd.substring(6).toInt();
    if (us < (long)MIN_STEP_DELAY_US) us = MIN_STEP_DELAY_US;
    if (us > (long)MAX_STEP_DELAY_US) us = MAX_STEP_DELAY_US;
    stepDelayMicros = (unsigned long)us;
    Serial.print(F("[SPEED] ")); Serial.print(1000000UL / stepDelayMicros); Serial.println(F(" passos/s"));
    return;
  }

  if (cmd.startsWith("JOGSTART ")) {
    // formato: JOGSTART X 1
    char axis = cmd.charAt(9);
    int space2 = cmd.indexOf(' ', 10);
    int8_t dir = 0;
    if (space2 >= 0) dir = (int8_t)cmd.substring(space2 + 1).toInt();
    startContinuousJog(axis, dir);
    return;
  }

  // Movimento de roteiro v2: P=1 significa foto obrigatoria ao chegar.
  // Respostas com ID de transacao para impedir ACK obsoleto.
  if (cmd.startsWith("SCANMOVE ")) {
    if (!driversEnabled || !homedX || !homedY) {
      Serial.println(F("[ERRO] SCANMOVE exige ENABLE 1 e HOME manual em X/Y."));
      return;
    }
    if (motionMode != MOTION_IDLE || scanInProgress) {
      Serial.println(F("[ERRO] SCANMOVE: eixos ocupados."));
      return;
    }
    int ix = cmd.indexOf("X ");
    int iy = cmd.indexOf("Y ");
    int ip = cmd.indexOf("P ");
    int iid = cmd.indexOf("ID ");
    if (ix < 0 || iy <= ix || ip <= iy || iid <= ip) {
      Serial.println(F("[ERRO] Use SCANMOVE X n Y n P 0|1 ID n."));
      return;
    }
    String sx = cmd.substring(ix + 2, iy); sx.trim();
    String sy = cmd.substring(iy + 2, ip); sy.trim();
    String sp = cmd.substring(ip + 2, iid); sp.trim();
    String sid = cmd.substring(iid + 3); sid.trim();
    if (!sx.length() || !sy.length() || (sp != "0" && sp != "1") ||
        !sid.length() || sid.length() > 9) {
      Serial.println(F("[ERRO] Parametros SCANMOVE invalidos.")); return;
    }
    for (unsigned int j = 0; j < sx.length(); j++) if (!isDigit(sx.charAt(j))) {
      Serial.println(F("[ERRO] SCANMOVE X invalido.")); return;
    }
    for (unsigned int j = 0; j < sy.length(); j++) if (!isDigit(sy.charAt(j))) {
      Serial.println(F("[ERRO] SCANMOVE Y invalido.")); return;
    }
    for (unsigned int j = 0; j < sid.length(); j++) if (!isDigit(sid.charAt(j))) {
      Serial.println(F("[ERRO] SCANMOVE ID invalido.")); return;
    }
    long nx = sx.toInt(), ny = sy.toInt(), id = sid.toInt();
    if (id <= 0 || nx < 0 || nx > MAX_X || ny < 0 || ny > MAX_Y) {
      Serial.println(F("[ERRO] SCANMOVE fora dos limites ou ID invalido.")); return;
    }
    targetX = nx; targetY = ny;
    scanId = id;
    scanNeedsPhoto = (sp == "1");
    scanInProgress = true;
    lastScanPingMillis = millis();
    motionMode = (posX == targetX && posY == targetY) ? MOTION_IDLE : MOTION_TARGET;
    Serial.print(F("OK:SCANMOVE ID=")); Serial.print(id);
    Serial.print(F(" X=")); Serial.print(targetX);
    Serial.print(F(" Y=")); Serial.print(targetY);
    Serial.print(F(" P=")); Serial.println(scanNeedsPhoto ? 1 : 0);
    if (motionMode == MOTION_IDLE) {
      scanInProgress = false;
      if (scanNeedsPhoto) { photoPending = true; photoId = scanId; }
      scanNeedsPhoto = false;
      Serial.print(F("DONE:ID=")); Serial.print(id);
      Serial.print(F(",X=")); Serial.print(posX);
      Serial.print(F(",Y=")); Serial.print(posY);
      Serial.print(F(",P=")); Serial.println(photoPending ? 1 : 0);
      sendTelemetry();
    }
    return;
  }

  if (cmd.startsWith("JOG X ")) {
    if (!driversEnabled || !homedX || !homedY || isMoving()) {
      Serial.println(F("[ERRO] JOG X exige HOME, drivers e maquina parada."));
      return;
    }
    long delta = 0;
    if (!lerJogSeguro(cmd.substring(6),delta)) {
      Serial.println(F("[ERRO] JOG X: use 1..5000 passos com sinal opcional."));
      return;
    }
    targetX = clampX(posX + delta);
    targetY = posY;
    motionMode = (targetX == posX) ? MOTION_IDLE : MOTION_TARGET;
    return;
  }

  if (cmd.startsWith("JOG Y ")) {
    if (!driversEnabled || !homedX || !homedY || isMoving()) {
      Serial.println(F("[ERRO] JOG Y exige HOME, drivers e maquina parada."));
      return;
    }
    long delta = 0;
    if (!lerJogSeguro(cmd.substring(6),delta)) {
      Serial.println(F("[ERRO] JOG Y: use 1..5000 passos com sinal opcional."));
      return;
    }
    targetY = clampY(posY + delta);
    targetX = posX;
    motionMode = (targetY == posY) ? MOTION_IDLE : MOTION_TARGET;
    return;
  }

  if (cmd == "CENTER") {
    if (isMoving()) {
      Serial.println(F("[ERRO] CENTER: aguarde a maquina parar."));
      return;
    }
    if (!driversEnabled) {
      Serial.println(F("[ERRO] Drivers desabilitados."));
      return;
    }
    if (!homedX || !homedY) {
      Serial.println(F("[ERRO] Faça o HOME manual antes de ir ao centro."));
      return;
    }
    targetX = MAX_X / 2L;
    targetY = MAX_Y / 2L;
    motionMode = (targetX == posX && targetY == posY) ? MOTION_IDLE : MOTION_TARGET;
    Serial.print(F("[CENTER] Destino interno X=")); Serial.print(targetX);
    Serial.print(F(" Y=")); Serial.print(targetY);
    Serial.println(F(" | interface/OpenSCAD: X=0.00 mm Y=0.00 mm"));
    return;
  }

  if (cmd.startsWith("MOVE ")) {
    if (!driversEnabled || !homedX || !homedY || isMoving()) {
      Serial.println(F("[ERRO] MOVE exige HOME, drivers e maquina parada."));
      return;
    }
    long newX = posX;
    long newY = posY;
    bool hasX = false;
    bool hasY = false;

    int ix = cmd.indexOf("X ");
    int iy = cmd.indexOf("Y ");

    if (ix >= 0) {
      String sx = cmd.substring(ix + 2, (iy > ix) ? iy : cmd.length());
      sx.trim();
      if (!lerCoordenadaSegura(sx,newX,MAX_X)) {
        Serial.println(F("[ERRO] MOVE X fora do limite/nao numerico."));
        return;
      }
      hasX = true;
    }
    if (iy >= 0) {
      String sy = cmd.substring(iy + 2);
      sy.trim();
      if (!lerCoordenadaSegura(sy,newY,MAX_Y)) {
        Serial.println(F("[ERRO] MOVE Y fora do limite/nao numerico."));
        return;
      }
      hasY = true;
    }

    if (!hasX && !hasY) return;
    targetX = newX;
    targetY = newY;
    motionMode = (targetX == posX && targetY == posY) ? MOTION_IDLE : MOTION_TARGET;
    return;
  }

  Serial.print(F("[ERRO] Comando desconhecido: ")); Serial.println(cmd);
}

// ============================================================
// MOVIMENTO NÃO BLOQUEANTE
// ============================================================
void serviceMotion() {
  // Defesa adicional: nem pulses de JOG podem ser emitidos durante PHOTO=WAIT.
  if (photoPending || motionMode == MOTION_IDLE || !driversEnabled) return;

  unsigned long now = micros();
  const unsigned long interval = (motionMode == MOTION_JOG && stepDelayMicros < MIN_JOG_DELAY_US)
                               ? MIN_JOG_DELAY_US : stepDelayMicros;
  if ((unsigned long)(now - lastStepMicros) < interval) return;
  lastStepMicros = now;

  if (motionMode == MOTION_JOG) {
    bool stepped = false;
    if (jogAxis == 'X') stepped = stepLogicalX(jogDir);
    else if (jogAxis == 'Y') stepped = stepLogicalY(jogDir);

    // Soft limit atingido: para e NÃO continua contando.
    if (!stepped) {
      motionMode = MOTION_IDLE;
      jogAxis = 0;
      jogDir = 0;
      targetX = posX;
      targetY = posY;
      sendTelemetry();
    }
    return;
  }

  if (motionMode == MOTION_TARGET) {
    if (posX != targetX) {
      int8_t dir = targetX > posX ? 1 : -1;
      if (!stepLogicalX(dir)) targetX = posX;
    }

    if (posY != targetY) {
      int8_t dir = targetY > posY ? 1 : -1;
      if (!stepLogicalY(dir)) targetY = posY;
    }

    if (posX == targetX && posY == targetY) {
      motionMode = MOTION_IDLE;
      sendTelemetry();
      if (scanInProgress) {
        scanInProgress = false;
        if (scanNeedsPhoto) { photoPending = true; photoId = scanId; }
        scanNeedsPhoto = false;
        Serial.print(F("DONE:ID=")); Serial.print(scanId);
        Serial.print(F(",X=")); Serial.print(posX);
        Serial.print(F(",Y=")); Serial.print(posY);
        Serial.print(F(",P=")); Serial.println(photoPending ? 1 : 0);
        sendTelemetry();
      }
    }
  }
}

// ============================================================
// SETUP / LOOP
// ============================================================
void setup() {
  pinMode(PIN_ENABLE, OUTPUT);
  pinMode(PIN_STEP_X, OUTPUT);
  pinMode(PIN_DIR_X, OUTPUT);
  pinMode(PIN_STEP_Y, OUTPUT);
  pinMode(PIN_DIR_Y, OUTPUT);

  digitalWrite(PIN_STEP_X, LOW);
  digitalWrite(PIN_STEP_Y, LOW);
  setDrivers(true);

  Serial.begin(115200);
  inputBuffer.reserve(96);

  Serial.println(F("[FW] CNC v8.1 JOG/MOVE guard UART ESP32 PHOTOACK PROTO=2 - X transversal / Y longitudinal"));
  Serial.print(F("[OPENSCAD] Curso X=")); Serial.print(TRAVEL_X_MM, 1);
  Serial.print(F(" mm | Y=")); Serial.print(TRAVEL_Y_MM, 1); Serial.println(F(" mm"));
  Serial.print(F("[CAL] X=")); Serial.print(STEPS_PER_MM_X, 4);
  Serial.print(F(" passos/mm | Y=")); Serial.print(STEPS_PER_MM_Y, 4); Serial.println(F(" passos/mm"));
  Serial.println(F("[INFO] Interno: 0..MAX | Interface/OpenSCAD: centro = X0 Y0."));
  Serial.println(F("[INFO] Posicao inicial interna no centro; interface inicia em X=0 Y=0."));
  sendTelemetry();
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length()) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    } else if (inputBuffer.length() < 95) {
      inputBuffer += c;
    }
  }

  // Protecao adicional: se o notebook perder a USB ou parar de enviar
  // SCANPING durante um SCANMOVE, nao prosseguir indefinidamente.
  if (scanInProgress && (unsigned long)(millis() - lastScanPingMillis) > SCAN_WATCHDOG_MS) {
    stopMotion();
    Serial.println(F("[ERRO] SCANMOVE watchdog: sem heartbeat da ESP32."));
  }
  if (motionMode == MOTION_JOG &&
      (unsigned long)(millis() - lastJogPingMillis) > JOG_WATCHDOG_MS) {
    stopMotion();
    Serial.println(F("[ERRO] JOG watchdog: botao/rede sem sinal; parada automatica."));
  }
  serviceMotion();

  unsigned long nowMs = millis();
  unsigned long interval = isMoving() ? TELEMETRY_MOVING_MS : TELEMETRY_IDLE_MS;
  if ((unsigned long)(nowMs - lastTelemetryMillis) >= interval) {
    lastTelemetryMillis = nowMs;
    sendTelemetry();
  }
}
