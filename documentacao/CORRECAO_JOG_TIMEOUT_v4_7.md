# Correção da confirmação de JOG — v4.7

## Diagnóstico com o status enviado

O estado informado pela ESP32-CAM mostrava `arduino=true`, `home_x=true`, `home_y=true`, `enabled=true`, `moving=false`, `stage=PARADO`, posição interna `X=1030, Y=2275` e centro `CENTERX=1030, CENTERY=2275`. Portanto, o comando `CENTER` já havia alcançado o destino calibrado. O aviso genérico seguinte era gerado por `waitJogTarget()`, usado pelo JOG discreto do painel para aproximar a câmera e ensinar pontos, não pelo comando `CENTER`.

## Causa provável corrigida

A versão anterior calculava o prazo de confirmação pelo valor editável `speedPps` do navegador. Esse campo não garante refletir a velocidade realmente aplicada ao Arduino: `SPEED` pode ter sido alterado anteriormente e o painel pode ter sido recarregado sem sincronizar o valor. Um movimento lento podia, assim, exceder o prazo calculado no navegador apesar de continuar válido.

## Alteração v4.7

- O prazo do JOG agora usa o limite inferior seguro permitido pelo firmware: 10 passos/s.
- Mantém a confirmação por duas leituras consecutivas de telemetria com a posição final exata e a máquina parada.
- Se a chegada não for confirmada, a mensagem mostra o destino esperado e a última posição informada pela ESP32/Arduino.
- Não repete comandos automaticamente, não relaxa HOME/limites e não altera direção, escala, coordenadas ou protocolo.

## Impacto e validação

A correção está somente em `notebook/painel.js` (e no título da versão em `notebook/painel.html`). Não é necessário regravar Arduino nem ESP32-CAM para esta correção. Foram executados `node --check`, `python -m compileall`, verificação de IDs HTML e a suíte de testes: 101 aprovados, 1 ignorado.

A validação física ainda deve ser feita com deslocamento pequeno, operador junto ao PARAR e área livre. O firmware não tem encoder/sensor de posição: a telemetria confirma a contagem lógica de passos, não mede independentemente a posição física real.
