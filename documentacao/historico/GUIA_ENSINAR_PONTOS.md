# Como ensinar o percurso com os botões X/Y — painel v2.5

Esta atualização modifica **somente o painel do notebook** (`notebook/painel.html`, `painel.css`, `painel.js`).
Os arquivos `.ino` do Arduino Uno e da ESP32-CAM são **idênticos** aos do pacote com stream ao vivo v2.4.
Se o stream e os comandos já funcionam, não é necessário regravar as placas.

## Passo a passo

1. Inicie o painel e confira que **ESP32-CAM e Arduino estão online**.
2. Execute o **HOME manual** no canto físico correto; depois ative os drivers. Como não existem sensores, o sistema não identifica a origem sozinho.
3. Na aba **Câmera e fotos**, clique em **Iniciar câmera ao vivo** para enxergar as plantas.
4. Logo abaixo da imagem, use os botões **X+, X−, Y+, Y−**. Escolha no campo o número de passos por clique (1 a 250); comece com deslocamentos pequenos.
5. Aguarde o deslocamento terminar e confirme no vídeo se a região desejada está bem enquadrada.
6. Deixe marcado **Fotografar neste ponto** e clique em **Marcar este enquadramento**.
7. Mova para o próximo enquadramento, deixando sobreposição suficiente para que as plantas das bordas não fiquem fora das fotos. Repita.
8. Abra **Percurso**. Você verá a lista dos pontos X/Y na ordem em que foram ensinados. Pode reorganizar, excluir ou corrigir posições.
9. Clique em **Salvar na ESP32-CAM**. A marcação é local até esse salvamento; só os pontos salvos serão executados.
10. Inicie o percurso. O Arduino para em cada ponto, a ESP32-CAM tira uma foto JPEG, o notebook confirma que salvou e só então a CNC avança.

## Observações

- O clique **Marcar** apenas cadastra o ponto, não tira a fotografia naquele momento.
- O painel tenta confirmar a chegada do movimento ao destino e faz duas leituras de posição estável antes de marcar. Isso depende da telemetria da placa; não detecta falhas mecânicas nem perda de passos.
- Um mesmo par de coordenadas X/Y não será incluído duas vezes.
- Limite atual: **48 pontos**.
- Você pode ensinar pontos na aba **Percurso** sem usar vídeo, ou na aba **Câmera e fotos** com o vídeo aberto.
- A opção de **digitar coordenadas** permanece, escondida em *Inserir coordenadas manualmente (opcional)*.
- Quando se fala em “mover na mão”, use os botões do painel. Se empurrar o pórtico ou carrinho fisicamente, com ou sem drivers, o Arduino não consegue medir esse movimento: a posição X/Y deixa de ser confiável. Nesse caso, repita a referência manual.
- Sem sensores e sem encoders, medidas em milímetros são estimativas calculadas a partir dos passos e da calibração configurada, não leituras físicas.
- Durante o roteiro o stream é interrompido, preservando a prioridade das fotos e a confirmação de salvamento.

## Atualização no Debian

Preserve a pasta `notebook/capturas/` e substitua na instalação antiga:

- `notebook/painel.html`
- `notebook/painel.css`
- `notebook/painel.js`

Na pasta `notebook`, inicie normalmente:

```bash
source .venv/bin/activate
python controle.py --esp IP_ATUAL_DA_ESP32 --chave 'SUA_API_KEY'
```

Abra `http://127.0.0.1:8765` e use **Ctrl+Shift+R** para recarregar a interface sem cache.

Testes estáticos e simulação de navegador foram executados. **Não houve ensaio físico dos motores/câmera**, portanto comece com 1 a 5 passos, observe a máquina e mantenha um meio de parada acessível.
