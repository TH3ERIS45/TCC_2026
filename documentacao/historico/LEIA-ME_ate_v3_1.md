# ATLAS CNC v3.1 — mosaico automático e manual de fotografias

**Novo nesta atualização:** consulte `GUIA_MOSAICO_v3_0.md`. A versão v3.1 acrescenta ao notebook uma montagem aproximada dos JPEGs com as coordenadas dos pontos, uma imagem geral na aba **Câmera e fotos** e um gerador automático ao fim dos percursos concluídos. **Os firmwares existentes não foram alterados.**

---

# ATLAS CNC v2.9 — Gerador de roteiros para fotografar plantas

A atualização v2.9 adiciona **seis métodos de varredura**, além do **mapeamento manual por X/Y**, com pré-visualização, sobreposição configurável e limite de 48 pontos. A geração **não movimenta a máquina**; depois de conferir os pontos, é preciso clicar em **Salvar na ESP32-CAM** antes de iniciar. Veja **`GUIA_METODOS_VARREDURA_v2_9.md`**.

**Arquivos alterados**: `notebook/painel.html`, `painel.css`, `painel.js`, `controle.py`; novo `notebook/planejador.js`. **Firmwares do Arduino e da ESP32-CAM mantidos byte a byte iguais à versão v2.8, incluindo a correção PHOTOACK v2.7.**

---

# ATLAS CNC v2.8 — MAX no modelo 3D e alinhamento físico sem sensores

A maquete preserva as funções de stream, ensino de pontos, mapeamento, fotografia sincronizada e correção PHOTOACK v2.7. Agora o painel permite **visualizar XMAX/YMAX no 3D sem movimentar motores** e **registrar manualmente a referência MAX** antes de centralizar.

Leia primeiro **`GUIA_MAX_SEM_SENSORES.md`**. **Nenhum firmware foi alterado nesta versão**; atualize apenas `painel.html`, `painel.css`, `painel.js` e `modelo3d.js` no notebook. Os botões de prévia são apenas visuais, enquanto **Centralizar automaticamente** movimenta fisicamente os motores.

---

# ATUALIZAÇÃO v2.7 — DIAGNÓSTICO PHOTOACK

Leia primeiro `DIAGNOSTICO_PHOTOACK_v2_7.md`. Apenas o firmware ESP32-CAM foi alterado em relação à v2.6.

# ATUALIZACAO v2.6 — CONFIRMACAO ROBUSTA PHOTOACK

Esta versao corrige a espera da confirmacao de foto no firmware da ESP32-CAM, sem mexer no Arduino nem no painel. Leia `CORRECAO_PHOTOACK.md` antes da instalacao.

---

# Maquete CNC — painel v2.5 · ensinar pontos pelo movimento X/Y

**Novo:** para mapear o canteiro, abra `GUIA_ENSINAR_PONTOS.md`. Você pode usar o vídeo ao vivo, mover X/Y pelos botões e marcar a posição atual (sem digitar coordenadas). Os firmwares permanecem iguais aos da versão de stream v2.4.

## Projeto e funcionamento anterior

# Maquete CNC — ESP32-CAM e Arduino por UART, notebook por Wi-Fi

Esta versão **substitui a ponte USB Python**. Não há visão computacional: o software de visão poderá consumir os JPG da pasta `notebook/capturas/` separadamente.

## 1. Arquitetura

```text
            Notebook Debian
        painel + receptor de JPG
      http://127.0.0.1:8765
                 | Wi-Fi (LAN)
                 | comandos HTTP / estado HTTP
                 | recebimento HTTP POST dos JPG
                 v
          ESP32-CAM AI Thinker
      coordenador de percurso/captura
                 | UART 115200
       RX ↔ TX, GND comum
                 v
       Arduino Uno + CNC Shield V3
           STEP/DIR motores X/Y
```

O *notebook NÃO comanda as fotos ponto a ponto*. Ele cadastra o roteiro e recebe os arquivos. A ESP32-CAM coordena o percurso e conversa diretamente com o Arduino pela UART.

### Sincronização de uma parada com foto

1. ESP32 manda `SCANMOVE X 400 Y 600 P 1 ID 125` pela UART.
2. Arduino move o pórtico e informa `DONE:ID=125,X=400,Y=600,P=1`. O firmware entra em `PHOTO=WAIT` e recusa comandos de movimento.
3. ESP32 verifica `PHOTO=WAIT,PID=125`, espera estabilização, fotografa e envia **JPEG por HTTP POST** ao notebook com `X-Photo-Id: 125`.
4. Python valida JPEG e grava `notebook/capturas/foto_000000125_X400_Y600.jpg`, com `manifesto.csv`. **Só então** responde `HTTP 200`, corpo `OK:125`.
5. ESP32 envia `PHOTOACK 125` diretamente ao Arduino. Arduino confere ID e libera a trava, enviando `OK:PHOTOACK ID=125`.
6. ESP32 somente após esse retorno envia o movimento ao ponto seguinte. Ao terminar a lista, o pórtico **permanece no último ponto**.

Se a foto, a rede, o disco ou a confirmação falhar, **não há PHOTOACK**, e o Arduino permanece parado e travado. O operador pode tentar a captura outra vez pelo painel. A liberação manual `PHOTOABORT` está separada e deixa claro que a foto foi descartada.

Para pontos de passagem sem foto (`P 0`), a ESP32 aguarda `DONE` e avança. Durante o deslocamento ela envia `SCANPING` periodicamente; a ausência faz o Arduino parar, usando watchdog de 3,5 s.

## 2. Conexões lógicas — conferir revisão da placa antes de ligar

| CNC Shield V3 / Arduino Uno | ESP32-CAM AI Thinker | Observação |
| --- | --- | --- |
| TX / D1 (5 V) | U0R / GPIO3 (3,3 V) | **Conversor de nível 5 V -> 3,3 V obrigatório** |
| RX / D0 | U0T / GPIO1 (3,3 V) | Saída da ESP32 para entrada do Uno; usar conversor bidirecional adequado se necessário |
| GND | GND | Terra comum |
| Alimentação regulada de 5 V | Pino 5V | Fonte dimensionada; não confundir com 12 V dos motores |

**A CNC Shield V3 apenas replica RX/TX/5V/GND do Arduino Uno**. O conector 5V não é um regulador independente. A fonte dos motores de 12 V e alta corrente deve ficar em circuito de potência protegido; um técnico responsável deve dimensionar proteções, 5 V regulados, distribuição e corte de emergência. Nunca aplicar 12 V no pino 5V da ESP32-CAM. **Não usar o pino 3,3 V do Uno para alimentar a câmera.**

**D0/D1 do Uno compartilham a UART USB**: desligue/desconecte a interligação serial com a ESP32 quando for gravar o Arduino ou usar o Monitor Serial. O U0R/U0T da ESP32 também é usado por adaptadores USB-seriais na gravação: desconecte a UART entre placas ao gravar a ESP32. Evite usar duas fontes USB/5V no mesmo barramento sem gestão adequada.

**Atenção:** esta é uma trava de **software**, não um intertravamento elétrico certificado. Reinicialização/queda de energia em uma das placas pode apagar estados em RAM. Use parada de emergência física e não opere sem supervisão ou próximo a pessoas/obstáculos. O HOME é **manual**, e os limites são coordenadas calculadas, sem sensores físicos.

## 3. Preparar os dois firmwares

- Arduino IDE: abrir `arduino_cnc/arduino_cnc.ino`, escolher **Arduino Uno**, compilar e gravar.
- Arduino IDE com suporte ESP32: abrir `esp32cam/esp32cam.ino`, escolher **AI Thinker ESP32-CAM**; editar:
  - `WIFI_SSID` e `WIFI_PASSWORD` (Wi-Fi de **2,4 GHz**).
  - `NOTEBOOK_IP` (endereço **da rede local do notebook**, não `127.0.0.1`).
  - `NOTEBOOK_PORT` (padrão `8765`).
  - `API_KEY` (um segredo próprio; use o mesmo valor ao iniciar o Python).
- Compilar e gravar a ESP32-CAM. Se o firmware não compilar devido a versão da biblioteca/core, verifique sua versão do pacote ESP32 e a compatibilidade com `esp_camera`.
- **Desconecte os cabos UART entre placas antes de gravar qualquer uma**. Após gravar e desligar a alimentação, faça as conexões de baixa tensão validadas.

A câmera usa **UXGA 1600×1200 com PSRAM**; sem PSRAM, **VGA 640×480**. Neste desenho não é necessário cartão microSD: as fotos são salvas no notebook. Se o notebook não receber, a máquina para no ponto da foto.

## 4. Configurar o Debian

No notebook:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
cd Maquete_TCC_STREAM_CALIBRACAO/notebook
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
hostname -I
```

Use o IP da rede local mostrado por `hostname -I` no `NOTEBOOK_IP` do código da ESP32. A ESP32 e o notebook precisam se enxergar na mesma rede Wi-Fi/LAN e a porta TCP **8765** precisa estar acessível no notebook. Se houver firewall, permita somente a rede local confiável.

Inicie o painel e receptor **antes** da varredura:

```bash
python controle.py --esp 192.168.1.80 --chave 'SUA_CHAVE_CONFIGURADA'
```

Troque `192.168.1.80` pelo IP da ESP32; veja o IP no roteador DHCP ou teste `http://IP_DA_ESP32/health` após ligar.

Abra **http://127.0.0.1:8765** no navegador do notebook. Não use cabo USB do Arduino para comandar a maquete durante a operação UART; neste projeto o painel comunica **somente por Wi-Fi**. O notebook pode permanecer com a ESP32 na rede mesmo quando o Arduino não está ligado à USB.

## 5. Ensinar e executar o percurso

1. Confirme a alimentação, segurança, pórtico livre e a comunicação `Arduino: Conectado` no painel.
2. Ajuste a posição física conhecida e a referência lógica. `HOME manual` **não move** motores; somente marca os eixos como referenciados. Use cautela antes de usar `SETPOS` (ele invalida o HOME).
3. Use comandos de passos pequenos para posicionar manualmente cada ponto.
4. Clique em **Guardar posição atual** em cada ponto; marque ou desmarque **Foto**.
5. Use os controles **↑/↓** para definir a sequência e salve o roteiro (persistente na memória não volátil da ESP32).
6. Clique em **Iniciar percurso**. A ESP32 dirige os pontos, o Arduino movimenta e trava nas fotografias, e o notebook recebe os JPG.
7. Fotos e `manifesto.csv` ficam em `notebook/capturas/`; a galeria aparece no painel. O software futuro de visão computacional poderá ler essa pasta separadamente.

**Em caso de falha:** verifique o estado da trava. `Tentar novamente` recaptura e reenvia a foto pendente. `PHOTOABORT` é recuperação manual, não confirmação de foto, e só deve ser usada quando você aceitar a perda daquela captura.

## 6. Testes

```bash
cd Maquete_TCC_STREAM_CALIBRACAO
python3 -m unittest discover -s tests -v
python3 -m py_compile notebook/controle.py
```

Os testes validam o receptor e rejeição de JPEG incorreto/ID errado sem placas físicas. Eles **não** provam o comportamento no hardware. Antes de um percurso real: compilar os dois firmwares, testar UART sem motores energizados, conferir nível lógico e GND, usar velocidades baixas, e testar a condição de falha interrompendo o notebook durante uma captura. Nunca presumir segurança física apenas com teste de software.

---

## 7. NOVO painel ATLAS CNC v2.0 — recursos restaurados e ampliados

A interface agora está nos arquivos **`notebook/painel.html`**, **`notebook/painel.css`** e **`notebook/painel.js`**. O servidor `controle.py` publica os três. Abra sempre `http://127.0.0.1:8765`, não o HTML diretamente pelo gerenciador de arquivos.

Abas:

- **Visão geral:** indicadores grandes de X/Y em **passos e mm centrados**, estado Wi-Fi, UART, drivers, HOME, trava fotográfica, progresso, evento e mapa com vistas **2D e isométrica**.
- **Movimentação:** jog de 1 a 250 passos por clique, presets, velocidades por passos/s, HOME geral e por eixo, invalidar HOME, ativar/liberar drivers, definir posição lógica, mover fisicamente ao centro ou a X=0/Y=0.
- **Percurso:** ensinar posição atual, adicionar/editar X/Y de pontos, escolher fotografia, reordenar, excluir, salvar na ESP32-CAM, recarregar, iniciar/parar e importar/exportar CSV `X,Y,0|1` (até 48 pontos).
- **Câmera e fotos:** botão **Tirar foto agora**; fotografia manual sem avançar o roteiro, imagem mais recente e galeria ampliável; recuperação de falha fotográfica e `PHOTOABORT` claramente separados.
- **Diagnóstico:** IP reportado pela ESP32, status Wi-Fi/UART, referências, drivers, trava, máximos dos eixos e monitor de eventos com copiar/limpar.

### Como fazer uma foto manual

1. Inicie o servidor Python no Debian **antes** de tirar a foto.
2. Confirme `ESP32 online` e `Arduino conectado`.
3. Referencie a máquina com **HOME manual** em posição física conhecida. Os motores precisam estar parados, sem foto pendente e sem roteiro em execução.
4. Acesse **Câmera e fotos → Tirar foto agora**.
5. A ESP32 chama a câmera, envia o JPEG à porta 8765 do notebook, aguarda `OK:<ID>` depois do salvamento no disco e só então responde sucesso à interface. A fotografia aparece na galeria e em `capturas/`.

**Observações:** a foto manual **não movimenta os motores**, **não envia PHOTOACK** e não altera o roteiro. Ela exige telemetria recente do Arduino e HOME; câmera ligada sozinha não satisfaz essa regra por segurança. A resposta pode demorar alguns segundos conforme Wi-Fi/tamanho do JPEG. A captura e o envio são síncronos, por isso `PARAR` via Wi-Fi pode aguardar o fim dessa operação; mantenha sempre uma parada elétrica apropriada. **Atualização v2.4:** agora há MJPEG ao vivo para calibração, iniciado manualmente pela aba Câmera e fotos. Confira a seção final e `GUIA_STREAM_AO_VIVO.md`.

### Compatibilidade com o painel antigo

- **Restaurado:** posições X/Y em passos e mm, vista da mesa, HOME por eixo, velocidade por presets, controles de jog, centralização, posicionamento lógico e mensagens.
- **Adaptado:** visualização isométrica 2D projetada (não é o antigo ambiente WebGL com órbita), captura por imagem salva e, na versão 2.4, transmissão MJPEG separada para calibração.
- **Não incluído nesta arquitetura:** operação direta por USB/WebSerial/Bluetooth e JOG contínuo ao manter o botão pressionado. A UART D0/D1 pertence exclusivamente à conversa Arduino ↔ ESP32-CAM durante a operação e o modo contínuo seria arriscado com perda de Wi-Fi, sem um watchdog próprio para JOG.

### Atualização dos firmwares

**Para o botão de foto manual e os botões “Ir ao centro / X0,Y0” funcionarem, é obrigatório atualizar `esp32cam/esp32cam.ino`.** O firmware Arduino existente nesta pasta continua o mesmo. Ao gravar uma das placas, desconecte temporariamente a UART entre elas. Refaça as conexões com as alimentações desligadas.

### Primeiro teste recomendado

Teste sem os motores energizados: IP e página, telemetria do Arduino, botões de HOME lógico e uma fotografia manual. Depois execute movimentação de poucos passos com o curso livre. Não execute um roteiro longo antes de verificar as travas, os limites e os resultados fotográficos em uma sequência curta.

**Diagnóstico de erro 503:** `--esp` precisa ser o IP da **ESP32-CAM**, não o IP do notebook. O IP do notebook pertence à constante `NOTEBOOK_IP` na ESP32, para onde os JPEGs serão enviados.


## 8. Visualização 3D interativa (v2.1)

A seção **Visão geral → Posição e trajetória** agora tem **três vistas**:

- **2D**: mapa superior X/Y, ideal para conferir coordenadas.
- **Isométrica**: projeção fixa da mesa.
- **3D interativo**: representação 3D dimensionada da estrutura da maquete, baseada nos arquivos OpenSCAD fornecidos, com perspectiva, profundidade, pórtico, carro da câmera, trilhos, caminho e pontos fotográficos. Arraste para girar, use a roda do mouse ou os botões +/− para aproximar/afastar e ↺ para restaurar a vista. Em dispositivos touch, arraste para girar.

O 3D é calculado **localmente no navegador**, em Canvas com projeção perspectiva e ordenação por profundidade; **não depende de CDN, internet ou WebGL**. O estado X/Y e os pontos vêm das mesmas respostas já utilizadas pelo mapa 2D; **nenhuma alteração ou atualização de firmware é necessária em relação à versão Painel Pro anterior**. A atualização do firmware ESP32-CAM descrita na seção 7 continua necessária *caso você ainda use a versão anterior à foto manual*.

**Importante:** é uma representação tridimensional **esquemática**, e não um arquivo CAD dimensionalmente exato da estrutura real. As posições refletem passos lógicos reportados pela máquina; não há sensores que garantam a posição física absoluta. Se o Arduino estiver offline, o modelo indica ausência de telemetria. A visualização não altera o comando de movimentos e não substitui limites físicos ou parada elétrica.

Para instalar por cima da v2.0, mantenha a pasta `notebook/capturas/` e substitua **somente** `notebook/painel.html`, `notebook/painel.css`, `notebook/painel.js`, `notebook/controle.py`, e adicione `notebook/modelo3d.js`. Reinicie `controle.py` e atualize o navegador com Ctrl+Shift+R.


## 9. Modelo do TCC integrado (v2.2)

O arquivo original `Maquete(2).zip` continha seis arquivos OpenSCAD; as fontes recebidas estão preservadas em `modelo_OpenSCAD_original/`. A visualização 3D do painel foi refeita com proporções e componentes extraídos de:

- `config.scad`: base 560 × 1060 × 30 mm; área útil 500 × 1000 mm; quatro pilares de 30 × 30 × 300 mm; tubos PVC de 20 mm de diâmetro.
- `estrutura.scad`: tubos longitudinais sobre os pilares.
- `main_2.scad`: plataforma de cultivo, travessa móvel, tubo transversal, transmissão GT2 e ESP32-CAM.
- `pecas_moveis.scad` e `Carrinho_eixoY_2.scad`: blocos de deslizamento e suporte da câmera.

**Limitação do material recebido:** `main_2.scad` referencia `suporte_nema.scad` e `Suporte_Nema_Eixo_Y.scad`, que **não vieram no ZIP**. Portanto, a montagem OpenSCAD completa não pôde ser convertida fielmente como malha original. O painel mostra uma **representação 3D paramétrica baseada nas medidas reais**, não um arquivo CAD importado pixel a pixel. Os suportes e motores faltantes são aproximados; fileiras verdes adicionais são ilustração visual.

**Telemetria:** o percurso lógico 0..X_MAX e 0..Y_MAX é mapeado para deslocamentos internos aproximados de 420 mm em X e 870 mm em Y. Esses valores visuais precisam ser calibrados conforme os limites físicos; **não são medições de sensores nem modificam o firmware**. O botão 3D nunca comanda motores.

Para esta alteração exclusivamente visual, basta substituir `notebook/modelo3d.js` e atualizar `notebook/painel.html`, mantendo o restante da versão Pro 3D. Reinicie o Python e force atualização do navegador (Ctrl+Shift+R).


## v2.3 — HOME sem sensores

Veja `INSTRUCOES_HOME_SEM_SENSORES.md` para usar a referência manual e a centralização automática com a geometria real. Os firmwares permanecem idênticos aos do pacote v2.2.


## 10. Novo stream MJPEG para calibração (v2.4)

**A ESP32-CAM precisa receber o `esp32cam/esp32cam.ino` desta versão.** A alteração é real no firmware da ESP32; só trocar o HTML não basta. O arquivo `arduino_cnc/arduino_cnc.ino` permanece **idêntico ao da versão 2.3**.

- `ESP32-CAM:80`: comandos e telemetria originais. Continuam independentes do vídeo.
- `ESP32-CAM:81/stream`: MJPEG autenticado por header `X-Api-Key`, em uma tarefa própria. O navegador **não** precisa saber a chave.
- `Notebook:8765/api/camera/stream`: proxy Flask que repassa o fluxo, usando a chave definida em `--chave`.
- **Painel → Câmera e fotos → Iniciar câmera ao vivo**: prévia para centralizar a lente e conferir quais plantas cabem no quadro. **Mostrar grade de enquadramento** insere uma grade 3×3 visual que não altera os arquivos JPEG salvos.
- **Parar transmissão**: fecha a imagem; ao sair da aba Câmera, iniciar percurso ou tirar foto manual, o painel interrompe o stream automaticamente. O próprio firmware também não transmite enquanto coordena o roteiro ou há uma foto pendente.

O vídeo usa **VGA 640×480, até ~4 quadros/s**, sujeito à qualidade do Wi-Fi e às limitações da ESP32. Cada foto manual ou do roteiro mantém a **resolução anterior** (UXGA 1600×1200 com PSRAM; VGA sem PSRAM). O código usa um mutex para impedir acesso concorrente ao hardware da câmera. O stream não substitui a confirmação de gravação `PHOTOACK`.

Para atualizar a partir da v2.3, preserve `notebook/capturas/`, e substitua `notebook/controle.py`, `notebook/painel.html`, `notebook/painel.css` e `notebook/painel.js`; mantenha `modelo3d.js`. Regrave **somente a ESP32-CAM** (com a UART entre placas desligada durante a gravação). Certifique-se de configurar Wi-Fi, `NOTEBOOK_IP` e `API_KEY` no novo firmware; eles **não** são migrados automaticamente. Desconecte a ligação UART para gravação conforme seção 2. Reinicie o Python e faça Ctrl+Shift+R no navegador.

**Diagnóstico:** se a prévia não aparecer, verifique `http://IP_DA_ESP32/health` (porta 80) e se o notebook alcança a **porta TCP 81** da câmera. Em Debian: `nc -vz IP_DA_ESP32 81` (se `nc` estiver instalado). A porta 81 não precisa ficar aberta à internet; use apenas a rede local confiável. Se a câmera estiver ocupada, o stream deve ser interrompido ou retornar indisponibilidade. O uso contínuo de vídeo exige uma alimentação 5 V regulada e estável.

**Validação:** os testes automatizados e checagens de sintaxe não substituem compilar no Arduino IDE com seu pacote de placas ESP32 nem testar fisicamente com a ESP32-CAM. Primeiro teste o stream com os motores desabilitados e sem executar o percurso.


## NOVO v3.1 — Encaixe fino do mosaico
Consulte `GUIA_MOSAICO_v3_1.md`. O encaixe fino por OpenCV é opcional e não altera Arduino/ESP32-CAM nem as fotos originais.
