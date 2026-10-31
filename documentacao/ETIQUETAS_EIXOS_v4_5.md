# ATLAS CNC — Etiquetas dos eixos v4.5

Esta versão troca somente os nomes apresentados na interface:

| Canal interno preservado | Etiqueta mostrada no painel |
|---|---|
| X (firmware/API) | Y |
| Y (firmware/API) | X |

## O que foi preservado

- Nenhum comando `JOG`, `MOVE`, `HOME`, `SETPOS` ou `CENTER` foi alterado.
- Os atributos internos `data-jog`, os identificadores HTML e a ordem dos campos enviados à ESP32-CAM/Arduino permanecem como antes.
- Nenhuma direção, quantidade de passos, escala, limite, calibração, velocidade ou posição foi modificada.
- Os firmwares Arduino e ESP32-CAM são idênticos aos da versão v4.4; não precisam ser regravados por esta mudança.
- Rotas e dados já salvos continuam no formato interno original. Na tabela do painel, a primeira coordenada é exibida como Y e a segunda como X.

A mudança é de apresentação: o antigo canal interno X recebe o rótulo visual Y; o antigo canal interno Y recebe o rótulo visual X. Não representa uma alteração elétrica ou mecânica.
