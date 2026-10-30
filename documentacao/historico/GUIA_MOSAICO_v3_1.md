# ATLAS CNC v3.1 — encaixe fino do mosaico

## O que mudou

O mosaico mantém as coordenadas X/Y como referência e, opcionalmente, procura detalhes iguais nas regiões que duas fotografias deveriam compartilhar. O ajuste usa pontos de interesse ORB e uma correção **somente de translação**, limitada a **até cerca de 9% do tamanho da foto** em cada eixo (no máximo 60 pixels). Para locais sem correspondências suficientes, volta automaticamente à posição por coordenadas, sem deslocar a fotografia arbitrariamente.

O objetivo é reduzir pequenas emendas e desalinhamentos; **não garante encaixe perfeito**. Plantas parecidas, pouca sobreposição, mudança de luz/foco, perspectivas e campo de visão mal calibrado podem impedir ou confundir o ajuste.

## Instalação

- Não atualize Arduino ou ESP32-CAM; esses firmwares são idênticos aos do pacote v3.0 e mantêm o PHOTOACK funcional.
- No Debian, preserve a pasta `notebook/capturas` e `manifesto.csv`; faça backup antes de trocar os arquivos.
- Atualize somente `notebook/mosaico.py`, `painel.js`, `painel.html` e `requirements.txt`. Mantenha os demais arquivos da versão v3.0.
- Ative o venv e execute `python -m pip install -r requirements.txt` para instalar o OpenCV (`opencv-python-headless`) usado no encaixe fino.
- Reinicie `controle.py` e atualize a página com Ctrl+Shift+R.

## Como comparar as duas versões

1. Entre em **Câmera e fotos → Imagem geral da plantação**.
2. Confira **Cobertura X/Y** em passos, rotação e espelhamento. As coberturas iniciais (600 e 1500) são exemplos, **não representam calibração física**.
3. Marque **Encaixe fino por pontos em comum** e clique **Gerar mosaico agora**.
4. Desmarque **Encaixe fino** e gere novamente usando a mesma seleção de fotos.
5. Compare as duas imagens. Ambas são armazenadas com nomes distintos. Escolha visualmente a melhor. A prévia mostra quantas fotografias foram ajustadas e quantas mantiveram as coordenadas originais.

Faça o primeiro ensaio com 2–4 fotos com cerca de 25–35% de área comum, câmera na mesma altura e iluminação parecida. Garanta imagens nítidas, parando o carrinho antes da captura.

## Limites e segurança

- O processamento acontece **somente no notebook** e **nunca envia movimento** à CNC; as fotos originais não são editadas.
- A montagem não deforma a perspectiva, não corrige lente e **não é um mapa métrico**. Para visão computacional use principalmente os JPEGs originais.
- Até 48 posições distintas; tamanho final limitado a aproximadamente 26 MP. Em mosaicos extensos, ajuste fino consome mais memória e CPU.
- Um alinhamento não aceito é um comportamento esperado quando não há correspondências confiáveis; o mosaico usa os X/Y naquele trecho.
- Para testar sem a máquina: `python -m unittest discover -s tests -v` no diretório principal do projeto.

## Resultado dos testes locais

O teste sintético com duas fotografias de textura compartilhada e 12 pixels de erro em X foi alinhado corretamente. Os testes não substituem a validação com fotos reais da plantação.
