# ATLAS CNC v3.0 — Mosaico da plantação por coordenadas X/Y

## O que foi acrescentado

O notebook Debian passa a montar um **mosaico JPEG** a partir das fotografias individuais do roteiro, sem regravar o Arduino ou a ESP32-CAM. O programa mantém os arquivos `foto_...jpg` e o `manifesto.csv` originais. Também registra uma sessão quando o painel envia o comando **Iniciar percurso**; ao receber da ESP32-CAM o status de que todos os pontos foram concluídos, o notebook gera automaticamente um mosaico **se a opção automática estiver ativada**.

Um botão **Gerar mosaico agora** permite montar manualmente as fotos da última sessão ou das **últimas 48 posições distintas** que existem no manifesto. O segundo modo serve para reaproveitar fotos antigas, mas **pode misturar capturas de execuções diferentes**.

## Instalação — somente notebook

1. Extraia o ZIP v3.0.
2. Faça cópia de segurança da pasta `notebook/capturas/` existente.
3. Substitua os arquivos `controle.py`, `painel.html`, `painel.css`, `painel.js` e adicione **`mosaico.py`**. Mantenha `planejador.js` e `modelo3d.js` existentes ou copie os do ZIP.
4. Preserve `capturas/` e `manifesto.csv`; **não apague as fotos**. Se trocar de pasta de projeto, copie `capturas/` para a nova.
5. No Debian, dentro de `notebook`, execute:

   ```bash
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python controle.py --esp IP_ATUAL_DA_ESP32 --chave 'SUA_CHAVE'
   ```

6. Abra `http://127.0.0.1:8765` → **Câmera e fotos** → **Imagem geral da plantação**. Faça `Ctrl+Shift+R` se o navegador tiver arquivos antigos em cache.

**Firmwares:** não regrave Arduino nem ESP32-CAM. O pacote os inclui intactos (Arduino anterior e ESP32-CAM com PHOTOACK corrigido v2.7).

## Calibração que faz diferença

- Informe a largura em **passos de X** e a altura em **passos de Y** que UMA foto enxerga sobre o canteiro.
- Valores iniciais de `600` X e `1500` Y **são EXEMPLOS, não medidas confirmadas**. Não assuma que o mosaico será exato com eles.
- Use a câmera ao vivo para identificar um marco e estime a diferença de X/Y entre posições que colocam esse marco nas bordas opostas da imagem. Registre a cobertura em passos; ajuste com fotos de teste.
- Mantenha **altura e inclinação da câmera fixas**, foco e iluminação uniformes, e procure **20–30% de sobreposição** entre fotos.
- Se os fragmentos aparecerem espelhados ou girados, ajuste **rotação** e **espelhamento** no painel e gere de novo. Os JPEGs originais não são modificados.
- Fotos duplicadas em exatamente X/Y: o sistema seleciona a **mais recente** para evitar sobreposição repetida. Fotografias com posições levemente diferentes são preservadas.

## Processo automático

1. Com cobertura e orientação conferidas, clique **Salvar calibração**. Deixe **Gerar automaticamente ao concluir roteiro** marcado.
2. Confirme HOME físico, drivers e área livre; ensine ou gere até 48 pontos com foto e salve o percurso na ESP32-CAM.
3. Clique **Iniciar percurso** **pelo painel do notebook**. Ele abre uma nova sessão e memoriza o ponto de início do manifesto.
4. O firmware já existente faz **mover → parar → capturar → salvar JPEG no notebook → confirmar PHOTOACK** em cada ponto. O mosaico **não participa** dessa confirmação.
5. Quando todos os pontos terminarem, o notebook detecta a conclusão e gera um JPEG em `notebook/capturas/mosaicos/`. A tela mostra a imagem e um link para baixar.
6. Se o roteiro for interrompido ou terminar com erro, **o mosaico não é marcado como concluído**. Corrija a causa e, se precisar, gere manualmente com a seleção adequada.

**Atenção:** deixe o servidor `controle.py` ligado durante a execução. Se o painel não iniciou a sessão (versão antiga ou botão externo), utilize **Últimas 48 posições**; isso pode misturar fotos de dias diferentes.

## Arquivos gerados

```text
notebook/capturas/
  manifesto.csv
  foto_000000011_X800_Y2275.jpg
  ...
  mosaicos/
    config.json                  # calibração do mosaico
    sessao_atual.json            # início e resultado do último roteiro
    mosaico_AAAAMMDD_HHMMSS_ffffff.jpg
    mosaico_AAAAMMDD_HHMMSS_ffffff.jpg.json
```

O software limita a **48 posições distintas** por mosaico e uma imagem de aproximadamente **26 megapixels** para evitar consumo excessivo de memória. Em casos extremos, uma calibração incompatível ou um percurso muito esparso pode ser rejeitado; ajuste os parâmetros ou use uma sessão menor.

## Limitações técnicas

Este recurso faz **alinhamento aproximado baseado nas coordenadas da câmera**. As bordas são suavizadas onde fotos se sobrepõem, mas a geometria **não é calibrada automaticamente** e não existe correção avançada de distorção de lente ou perspectiva. Isso pode causar emendas visíveis e repetição aparente das plantas nas faixas sobrepostas. Para visão computacional, **prefira as fotos originais** até validar o mosaico.

O arquivo final NÃO é um mapa métrico preciso, nem garante cobrir todo o canteiro sem uma calibração real e imagens sobrepostas suficientes. O mosaico é apenas processamento no notebook; nenhuma chamada do recurso movimenta os motores ou altera o protocolo de fotos da ESP32-CAM.

## Testes

No diretório principal do projeto:

```bash
python -m unittest discover -s tests -v
```

Depois da atualização, faça o primeiro ensaio com 2–4 pontos e confira as coordenadas e a imagem montada antes de um percurso longo.
