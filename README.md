# ATLAS CNC — projeto do TCC

Painel local para operar a maquete CNC, acompanhar a ESP32-CAM e receber as fotografias do percurso. O notebook faz a interface e o armazenamento; o controle de movimento e a sequência de captura continuam distribuídos entre os dois microcontroladores.

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

1. **Após a correção de sentido dos eixos (v4.4), regrave somente `arduino_cnc/arduino_cnc.ino` no Arduino Uno.** O firmware da ESP32-CAM não mudou e não precisa ser regravado por esta correção. Confira a ligação entre as placas.
2. Conecte o notebook e a ESP32-CAM à rede configurada.
3. Abra o painel e verifique se a telemetria mostra os dispositivos conectados.
4. Como a maquete não possui sensores de fim de curso, faça a referência física manual conforme as instruções da aba **Controle**. Não presuma que a posição lógica após ligar corresponda à posição física.
5. Cadastre ou importe o roteiro em **Mapeamento** e confira os pontos antes de iniciar.
6. A ESP32-CAM coordena o movimento e a captura. O notebook recebe o JPEG e só confirma o recebimento depois de validar e gravar o arquivo; não envie `PHOTOACK` manualmente pelo painel.

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
