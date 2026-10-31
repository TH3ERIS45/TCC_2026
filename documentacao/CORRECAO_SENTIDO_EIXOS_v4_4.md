# Correção do sentido dos eixos — v4.4

## Sintoma

Os botões X+/X− e Y+/Y− atualizavam o modelo 3D no sentido esperado, mas a maquete física se deslocava no sentido contrário nos dois eixos.

## Correção aplicada

A convenção lógica do painel e do modelo 3D foi mantida. A correção foi feita nas polaridades dos pinos DIR do Arduino, no firmware `arduino_cnc/arduino_cnc.ino`:

| Eixo | Comando positivo no modelo | Posição física esperada | DIR positivo |
|---|---|---|---|
| X | X aumenta | Direita | HIGH |
| Y | Y aumenta | Fundo / MAX Y | LOW |

Os sentidos negativos são derivados como o nível lógico oposto. Isso corrige também movimentos `MOVE`, `CENTER` e `SCANMOVE`, pois todos usam as mesmas rotinas de passo lógico. O JOG contínuo e o JOG por clique também compartilham essa lógica.

## O que precisa ser atualizado no hardware

- **Arduino Uno:** regravar o sketch `arduino_cnc/arduino_cnc.ino` desta versão.
- **ESP32-CAM:** não precisa ser regravada; seu firmware/protocolo não foi alterado.
- **Painel/servidor:** não foi necessário alterar a lógica de coordenadas nesta correção.

## Teste após a gravação

1. Deixe a máquina em uma região intermediária do curso, longe dos batentes. Não teste inicialmente nos extremos.
2. Faça HOME manual somente depois de confirmar que a posição física corresponde à coordenada indicada. HOME não move os motores.
3. Selecione o menor deslocamento disponível (1 passo) e teste X+ e X− separadamente. Confirme que o carro se move para a direita em X+ e para a esquerda em X−, conforme a orientação do modelo.
4. Faça o mesmo para Y: Y+ deve levar o pórtico em direção ao fundo/MAX Y; Y− deve levá-lo à frente/HOME Y=0.
5. Só então teste deslocamentos maiores e um pequeno roteiro.

Se o sentido continuar invertido em algum eixo após regravar, pare os testes e confira a identificação dos motores, os canais da CNC Shield e a fiação dos pinos DIR. Não altere simultaneamente a fiação e as constantes, pois isso pode inverter o sentido duas vezes.

## Limitação

A verificação feita nesta entrega é estática, por inspeção do firmware e testes automatizados sem hardware. A confirmação final depende do ensaio físico com a maquete. Como não há fins de curso nem encoders, a posição continua sendo estimada pela contagem de passos e exige HOME manual correto.
