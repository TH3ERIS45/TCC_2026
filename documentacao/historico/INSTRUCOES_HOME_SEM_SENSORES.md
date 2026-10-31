# HOME manual + centralização automática (sem sensores)

## O que realmente é automático

**Não existe HOME físico automático sem um meio de detectar a referência** (fim de curso, encoder absoluto etc.). Não há tentativa de forçar os eixos contra a estrutura para descobrir o zero.

Esta atualização mantém o **HOME manual** e cria um atalho com indicações para **centralização automática após o HOME manual**. O botão usa o comando `CENTER` que já existia nos firmwares. Os botões X/Y continuam disponíveis caso queira centralizar manualmente.

## Procedimento após cada inicialização ou perda de referência

1. Com a máquina parada, área livre e alimentação em condições seguras, libere os drivers se precisar reposicionar a maquete manualmente. O comando `ENABLE 0` invalida a referência.
2. Posicione **fisicamente** o carrinho e o pórtico na origem definida do curso útil, menor X e menor Y. Não force contra batentes.
3. Na aba **Movimentação**, em **HOME manual + centralização automática**, clique **Definir X0/Y0 (sem mover)**. Esse comando (`SETPOS X 0 Y 0`) somente ajusta as coordenadas lógicas e invalida HOME.
4. Ainda com os eixos na referência física, clique **Confirmar HOME manual** (`HOME`), que não movimenta a máquina.
5. Clique **Ativar drivers** (`ENABLE 1`).
6. Se o deslocamento inteiro foi medido e conferido, clique **Centralizar automaticamente** (`CENTER`). A máquina moverá para o centro do curso programado. Acompanhe fisicamente e use **PARAR** se houver qualquer anomalia; pare a alimentação de potência por dispositivo apropriado quando necessário.

Você também pode usar o HOME manual antigo, `HOME X`, `HOME Y`, `SETPOS` e os botões de passos, sem usar a centralização automática.

## Dimensões do firmware e limites reais

- Curso X programado: 328 mm, centro = 164 mm.
- Curso Y programado: 910 mm, centro = 455 mm.
- Na configuração atualmente escrita, há 200 passos por volta, microstepping 1 e polia GT2 20 dentes: 5 passos/mm, X máximo 1640 passos e Y máximo 4550 passos. Centro nominal: X 820, Y 2275 passos. **Confira os jumpers de microstepping reais e a transmissão antes de mover**.
- As dimensões externas do OpenSCAD, 560 × 1060 mm, **não** são o percurso do carrinho da câmera.
- Limites de software só funcionam se a posição física e a lógica foram alinhadas corretamente. Eles **não impedem uma colisão física** quando a posição foi informada incorretamente ou passos foram perdidos.
- Não execute centralização sem supervisão. Mantenha caminho desimpedido e parada de emergência de potência acessível.

## Instalação

Atualize apenas `notebook/painel.html`, `notebook/painel.js` e `notebook/painel.css` no projeto que você já usa. Preserve sua pasta `capturas/` e suas configurações. Reinicie o servidor `controle.py`, abra `http://127.0.0.1:8765` e use `Ctrl+Shift+R` para limpar o cache.

**Os firmwares do Arduino e da ESP32-CAM não foram modificados nesta versão. Não precisa regravar as placas se você já usa o pacote v2.2.**

## Verificações

`python3 -m unittest discover -s tests -v`

Os testes são de código/servidor e **não equivalem a teste com motores e placas reais**. Teste os eixos em baixa velocidade antes de usar `CENTER`.
