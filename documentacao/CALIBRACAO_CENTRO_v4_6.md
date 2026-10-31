# Calibração do centro mecânico — v4.6

A convenção de etiquetas introduzida no painel v4.5 e mantida na v4.6 apresenta o canal interno `X` com a etiqueta visual **Y**. Por isso, o ajuste do eixo transversal/curto aparece como Y na interface, mas é aplicado a `CENTER_TARGET_X` no Arduino.

## Ajuste aplicado

- Medida aproximada informada/fotografada do trilho: 400 mm.
- Curso interno configurado: 328 mm.
- A foto mostra o centro do carro aproximadamente 42 mm à esquerda do ponto médio do trilho.
- Correção inicial aplicada: `+42 mm` para a direita (sentido X interno positivo).
- Escala: 5 passos/mm.
- Correção: `+210 passos`.
- Novo destino: canal interno X = `820 + 210 = 1030` passos (etiqueta Y no painel).
- Canal interno Y / etiqueta X permanece no meio: `2275` passos.

O ajuste só se aplica ao comando `CENTER`. JOG, MOVE, SCANMOVE, limites, escala e trajetórias não recebem offset.

## Como refinar

No `arduino_cnc/arduino_cnc.ino`, ajuste `CENTER_OFFSET_X_MM`. Valor positivo desloca o centro para a direita da foto (sentido X interno positivo); valor negativo desloca para a esquerda. Mantenha o destino dentro do limite do firmware. Como não há sensores de fim de curso, faça o primeiro ensaio com área livre e operador junto ao botão PARAR.

## Limitação

A foto fornece uma estimativa em perspectiva, não uma medição metrológica. O valor de +42 mm é ponto de partida, não substitui conferência física da posição do carro depois do comando CENTER.

## Percurso autônomo e fotos

Antes de iniciar, a ESP32-CAM exige Arduino referenciado/parado, câmera inicializada, Wi-Fi conectado, receptor do notebook autenticado e gravável, e ao menos um ponto com Foto marcado. Cada ponto com foto continua protegido pelo fluxo chegada (`DONE`) → estabilização (1,4 s) → JPEG válido → gravação/manifesto no notebook → `PHOTOACK`; falhas não liberam o próximo ponto.

O preflight confirma a disponibilidade no momento do início; ele não substitui observação do primeiro trajeto, teste da iluminação, foco/enquadramento e conferência física dos eixos.
