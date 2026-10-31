# Câmera ao vivo na maquete — v2.4

## O que muda

- Adicionada transmissão MJPEG da ESP32-CAM em TCP **81**, separada da API de comandos TCP **80**.
- `notebook/controle.py` cria o endpoint de proxy **/api/camera/stream**: a API key é enviada diretamente do Flask para a ESP32, não no navegador.
- A aba **Câmera e fotos** tem **Iniciar câmera ao vivo**, **Parar transmissão** e **Grade de enquadramento**.
- Stream VGA (640×480, máximo aproximado de 4 fps) **apenas para visualizar**; JPEGs do roteiro seguem com a resolução original. Ao iniciar o roteiro, o vídeo cede prioridade às fotos sincronizadas com PHOTOACK.
- **HOME manual, centralização automática depois de HOME, mapa 2D/isométrico/3D e firmware Arduino foram preservados.**

## Atualização obrigatória

1. Desligue a alimentação da maquete antes de modificar conexões. Desconecte temporariamente RX/TX das placas durante a gravação da ESP32-CAM para evitar conflito na UART0.
2. Abra `esp32cam/esp32cam.ino` no Arduino IDE e selecione **AI Thinker ESP32-CAM**.
3. Configure `WIFI_SSID`, `WIFI_PASSWORD`, `NOTEBOOK_IP` (IP do Debian), `NOTEBOOK_PORT = 8765` e `API_KEY` (igual à chave passada ao Python). **Não use a senha padrão do exemplo.**
4. Compile e grave **o firmware novo da ESP32-CAM**. O Arduino Uno **não precisa ser regravado**.
5. No Debian, preserve suas fotos em `notebook/capturas/`; coloque os novos `controle.py`, `painel.html`, `painel.css` e `painel.js` na pasta notebook. Preserve `modelo3d.js`.
6. Ative seu ambiente virtual e inicie:

   ```bash
   cd /CAMINHO/DA/PASTA/Maquete_TCC_STREAM_CALIBRACAO/notebook
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python controle.py --esp IP_DA_ESP32 --chave 'SUA_CHAVE_IDENTICA_A_DO_FIRMWARE'
   ```

7. Abra `http://127.0.0.1:8765`, pressione Ctrl+Shift+R e navegue em **Câmera e fotos → Iniciar câmera ao vivo**. Ative a grade se quiser comparar as plantas com o centro da imagem.

## Como verificar

- `http://IP_DA_ESP32/health` deve retornar `ESP32-CAM gateway online`.
- No notebook, `nc -vz IP_DA_ESP32 81` pode verificar se a porta de vídeo está acessível; é diferente da porta 8765 do Flask.
- O navegador deve abrir vídeo na aba Câmera. Não é necessário informar API key na URL nem abrir diretamente `:81/stream` no navegador — esse endpoint exige um cabeçalho de autenticação.
- Pressione **Parar transmissão** antes de fotografar manualmente se estiver testando separadamente; o painel também encerra automaticamente.
- Para testar fotos, mantenha HOME confirmado e Arduino parado, conforme o procedimento original. Depois confira a galeria e os arquivos salvos.

## Limites e segurança

- Sem fim de curso, a CNC **não identifica HOME físico sozinha**. A transmissão de vídeo não altera esse fato.
- O fluxo usa CPU, PSRAM e Wi-Fi da ESP32-CAM. Na ausência de PSRAM, desempenho pode cair bastante. O vídeo não deve ser usado como prova de segurança para movimentar a máquina sem supervisão.
- Quando o roteiro começa, o vídeo **para** para priorizar os JPEGs e as confirmações de salvamento. Ele não grava o vídeo; somente os JPGs pontuais vão para `capturas/`.
- A interface Flask continua destinada à **rede local confiável**. Não exponha as portas 80, 81 ou 8765 à internet.
- O firmware ESP32-CAM ainda precisa ser compilado e validado na placa física. Teste com motores desligados primeiro.
