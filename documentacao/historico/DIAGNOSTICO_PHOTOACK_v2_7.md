# PHOTOACK v2.7: diagnóstico e retransmissão controlada

**Causa identificada no v2.6:** o laço calculava `now=millis()` antes do upload JPEG, mas definia `stageSince=millis()` depois do upload. No mesmo laço, comparava `now-stageSince` como inteiro sem sinal: com `now` antigo, a subtração estourava e acionava o timeout de 5 segundos imediatamente, muitas vezes antes da resposta do Arduino. **A v2.7 recalcula `now` depois da fotografia e do envio**, além de mostrar os detalhes para diagnóstico.

## O que mudou
- `fw_version` em `/api/esp/api/status`: `ESP32-2.7-PHOTOACK-DIAG` confirma que o firmware novo está rodando.
- `pending_id`, `arduino_photo_state`, `uart_last`, `uart_lines`, `photo_ack_tries` e `photo_ack_sent` mostram o ponto exato da falha.
- Depois de o notebook confirmar a imagem JPEG, a ESP32 envia `PHOTOACK ID` e `STATUS`.
- Se a telemetria mostrar `PHOTO=WAIT` com o **mesmo ID**, repete `PHOTOACK` em intervalos controlados; se já estiver `READY`, usa confirmação por telemetria com posição e PROTO=2.
- O timeout foi aumentado para 18s para permitir respostas UART após uploads de fotos.
- O sistema **nunca avança** sem foto salva e sem confirmação inequívoca do Arduino. Erros de ID e perda de HOME continuam interrompendo o roteiro.

## Instalação
1. Com os motores desligados, solte temporariamente a UART da ESP32-CAM e regrave **apenas a ESP32-CAM** com `esp32cam/esp32cam.ino`. Configure Wi-Fi, NOTEBOOK_IP, API_KEY iguais aos do painel; não altere firmware do Arduino.
2. Reconecte a UART com tudo desligado. Ligue o sistema, confira HOME manual, drivers e espaço livre.
3. Abra `http://127.0.0.1:8765/api/esp/api/status` e **confirme `fw_version`**. Se não aparecer v2.7, está rodando firmware anterior (ou IP de outra ESP32).
4. Teste uma rota curta com **dois pontos diferentes**, sem ir próximo aos limites físicos. Evite repetir muitas vezes para não gerar imagens duplicadas.
5. Se falhar, copie o JSON inteiro. `arduino_photo_state` revela `PHOTO=WAIT` ou `READY`, `photo_ack_tries` indica repetições e `uart_last` mostra a última linha recebida.

Importante: testes automatizados verificam o código, não comprovam o funcionamento físico na ESP32-CAM/Arduino. NÃO force movimento ou libere a trava com PHOTOABORT sem compreender se a foto foi salva.
