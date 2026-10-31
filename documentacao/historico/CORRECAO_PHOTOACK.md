# Correcao PHOTOACK (v2.6) — ATLAS CNC

## O que foi corrigido

Na versao anterior, a ESP32-CAM exigia exclusivamente a linha de UART `OK:PHOTOACK ID=n`. Em caso de perda dessa linha, mesmo quando o Arduino ja tinha liberado a trava, a ESP32-CAM entrava em `ERRO: Arduino nao confirmou PHOTOACK`.

Agora, **depois de o notebook responder OK ao JPEG**, a ESP32-CAM envia o mesmo `PHOTOACK` e aceita duas provas de conclusao:

1. Mensagem UART `OK:PHOTOACK ID=n` correspondente; ou
2. Telemetria do Arduino em protocolo 2 com `PHOTO=READY`, `PID=0`, maquina parada, HOME valido e coordenadas iguais as do ponto fotografado.

O firmware **nao** avanca se a fotografia nao foi salva no notebook. Nao e necessario alterar o firmware do Arduino Uno.

## Instalacao

1. Confirme que nao ha movimento e que a maquete esta numa posicao segura; desligue a alimentacao dos motores antes de mexer nas conexoes.
2. Anote Wi-Fi, API_KEY, NOTEBOOK_IP e NOTEBOOK_PORT atualmente configurados no firmware da ESP32-CAM.
3. Abra `esp32cam/esp32cam.ino` na Arduino IDE; configure os mesmos parametros de rede e de seguranca.
4. Com a UART da ESP32-CAM desconectada do Arduino, grave a ESP32-CAM e reconecte os fios com a alimentacao desligada.
5. Inicie o painel Debian normalmente. Mantenha `arduino_cnc/arduino_cnc.ino` como estava.
6. Confira as fotografias no `notebook/capturas` (no notebook em uso, nao na pasta nova do ZIP).
7. Faca novamente a referencia HOME manual, confirme o espaco livre, teste movimentos curtos, salve/recarregue o roteiro e execute uma prova com um unico ponto antes dos quatro.

**Sem sensores:** nao considere os numeros X/Y como posicao fisica absoluta apos reinicios ou movimentos manuais.

## Validacao

Foi realizada verificacao automatizada do projeto e dos casos previstos no codigo. A placa ESP32-CAM e a CNC reais ainda precisam de teste de bancada.
