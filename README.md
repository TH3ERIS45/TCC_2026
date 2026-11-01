# TCC

Painel local para operar a maquete CNC, acompanhar a ESP32-CAM e receber as fotografias do percurso. O notebook faz a interface e o armazenamento; o controle de movimento e a sequência de captura continuam distribuídos entre os dois microcontroladores.

**v4.6 — centro e pré-verificação da captura:** o botão de centro mecânico usa um ajuste de **+42 mm no canal interno X (etiqueta Y no painel)**, estimado visualmente pela foto, que mostra o carro cerca de 42 mm à esquerda do ponto médio do trilho de aproximadamente 400 mm. O ajuste só afeta o comando `CENTER`; não altera JOG, MOVE, limites, passos/mm ou pontos de roteiro. Antes de iniciar um percurso, a ESP32-CAM agora confirma que a câmera está inicializada, o Wi-Fi está ativo e o notebook aceita o teste autenticado de gravação na pasta de fotos.

**v4.7 — confirmação de JOG:** o painel não estima mais o tempo limite de um movimento manual pela velocidade editável do navegador, que pode divergir da velocidade realmente aplicada ao Arduino. O prazo usa o limite conservador de 10 passos/s permitido pelo firmware e mantém a confirmação por duas leituras finais iguais. Quando a chegada não é confirmada, a mensagem agora informa o destino esperado e a última posição lida do Arduino. **Esta correção altera somente o painel JavaScript/HTML; não exige regravar Arduino nem ESP32-CAM.**


**Atenção:** o valor +42 mm é uma calibração inicial estimada pela fotografia e precisa ser conferido fisicamente com um deslocamento supervisionado. A referência HOME continua manual, pois a montagem não tem sensores de fim de curso.

## Como o projeto está dividido

| Pasta/arquivo | Responsabilidade |
|---|---|
| `arduino_cnc/arduino_cnc.ino` | Controle dos motores, posição lógica, HOME manual, JOG, watchdog e telemetria. |
| `esp32cam/esp32cam.ino` | Wi-Fi, API HTTP, câmera, stream MJPEG, comunicação serial com o Arduino e confirmação `PHOTOACK`. |
| `notebook/controle.py` | Servidor Flask, painel web, proxy restrito para a ESP32-CAM e receptor autenticado de JPEG. |
| `notebook/conexao.py` | Validação e gravação local do endereço e da chave da ESP32-CAM. |
| `notebook/geometria.py` | Armazenamento do centro ensinado do canteiro; não altera os limites do firmware. |
| `notebook/mosaico.py` | Montagem offline dos mosaicos a partir do manifesto e das coordenadas X/Y. |
| `notebook/painel.html`, `painel.css`, `painel.js` | Interface, estilos e comportamento do painel. |
| `notebook/planejador.js` | Geração de trajetórias de varredura. |
| `notebook/modelo3d.js` | Visualização 3D esquemática; não envia comandos aos motores. |
| `modelo_OpenSCAD_original/` | Fontes CAD mecânicas originais. Algumas dependências externas não vieram no pacote; veja o README dessa pasta. |
| `tests/` | Testes automatizados e verificações de regressão sem hardware. |
| `documentacao/historico/` | Guias de versões anteriores, mantidos como histórico. |

## Iniciar o painel

Requer Python 3.10 ou superior. No terminal, a partir da raiz do projeto:

```bash
cd notebook
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python controle.py --configurar
python controle.py
```

Abra `http://127.0.0.1:8765`. Para usar outra porta, informe `--porta 9000` (ou a porta desejada). O endereço e a chave também podem ser passados temporariamente por `--esp` e `--chave`.

A configuração persistente fica em `notebook/atlas_conexao.json`, criada pelo comando `--configurar`. Ela contém a chave em texto simples, mas o programa restringe as permissões do arquivo no sistema local. **Não compartilhe esse arquivo nem o publique no repositório.** O arquivo de configuração real foi removido desta cópia distribuível; configure novamente no notebook que executará o painel.

## Fluxo de operação

1. **Nesta v4.6, regrave o Arduino e a ESP32-CAM.** O Arduino recebeu o destino de centro calibrado e telemetria `CENTERX/CENTERY`; a ESP32-CAM recebeu a pré-verificação da câmera/receptor antes de iniciar o percurso. Confira a ligação entre as placas.
2. Conecte o notebook e a ESP32-CAM à rede configurada.
3. Abra o painel e verifique se a telemetria mostra os dispositivos conectados.
4. Como a maquete não possui sensores de fim de curso, faça a referência física manual conforme as instruções da aba **Controle**. Não presuma que a posição lógica após ligar corresponda à posição física.
5. Cadastre ou importe o roteiro em **Mapeamento** e confira os pontos antes de iniciar.
6. A ESP32-CAM coordena o movimento e a captura. Antes do primeiro movimento, ela testa câmera, Wi-Fi e a possibilidade de gravar no notebook. Em cada ponto com `P=1`, aguarda chegada do Arduino, estabiliza por 1,4 s, captura JPEG, envia ao notebook e só depois de receber `OK:<ID>` envia `PHOTOACK`; não envie `PHOTOACK` manualmente pelo painel.

O servidor escuta na porta local configurada (padrão `8765`) e o stream da câmera é obtido da porta `81` da ESP32-CAM por proxy. Libere a porta do notebook no firewall apenas para a rede local necessária.

## Testes

Instale as dependências de desenvolvimento a partir da raiz:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Os testes cobrem validação de dados, rotas, protocolo de recebimento, mosaico e regressões estáticas. Eles não substituem compilação dos firmwares, teste de comunicação serial nem ensaio físico com motores e câmera.

## Estado dos dados de captura

A pasta `notebook/capturas/` contém imagens legadas com nomes `Fotos...jpg`, enquanto o `manifesto.csv` atual aponta para arquivos `foto_XXXXXXXXX_X..._Y....jpg` que não estão incluídos nesta cópia. As imagens legadas foram preservadas, mas não foram associadas automaticamente aos registros porque o pacote não contém uma correspondência confiável entre cada imagem, ID e coordenada. Consulte `notebook/capturas/README.md` antes de gerar mosaicos com esse conjunto.

## Limitações conhecidas

- A visualização 3D é esquemática, não é uma malha CAD exata nem uma medição da posição física.
- As medidas do canteiro e a escala nominal de passos/mm não substituem calibração física.
- A pasta OpenSCAD está incompleta: `main_2.scad` referencia `suporte_nema.scad` e `Suporte_Nema_Eixo_Y.scad`, ausentes no pacote recebido.
- A validação automatizada não foi feita com placas conectadas; o ensaio de hardware continua necessário.
- O ajuste de +42 mm para o centro do trilho é aproximado. Confirme o centro visualmente com movimento de teste curto e, se necessário, ajuste `CENTER_OFFSET_X_MM` no firmware Arduino.


### Proteções adicionais da v4.6

- O início do percurso autônomo exige pelo menos um ponto marcado para fotografia.
- Antes de mover, a ESP32-CAM verifica câmera, Wi-Fi e receptor autenticado do notebook.
- O notebook testa gravação tanto na pasta de fotos quanto na pasta de sessão do mosaico.
- O comando CENTER valida os limites do destino calibrado em tempo de execução.
