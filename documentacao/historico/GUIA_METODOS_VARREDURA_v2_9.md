# ATLAS CNC v2.9 — métodos de mapeamento e fotografia

## O que há de novo

Na aba **Percurso**, o modo já existente **Ensinar pontos com X/Y** continua funcionando. Abaixo dele, o painel oferece um **Gerador de pontos** com seis métodos automáticos:

1. **Zigue-zague por linhas (recomendado)**: percorre cada fileira e inverte o sentido na próxima, reduzindo deslocamentos sem foto.
2. **Zigue-zague por colunas**: mesma ideia, com o eixo X como passagem entre faixas.
3. **Linhas em sentido único**: todas as linhas são fotografadas no mesmo sentido; entre linhas, a máquina precisa voltar para o começo.
4. **Colunas em sentido único**: equivalente, orientado pelo eixo Y.
5. **Espiral retangular**: visita a grade pelas bordas e vai avançando para o interior. Inclui a área interior conforme a grade gerada.
6. **Perímetro (somente bordas)**: fotografa as bordas; **NÃO é adequado sozinho para cobrir todas as plantas**.

Continuam disponíveis: **roteiro ensinado manualmente**, edição/reordenação dos pontos e **importação/exportação CSV**.

## Como preparar o gerador

1. Faça o HOME manual de forma correta e confirme que a máquina está parada e em condições seguras.
2. Na aba **Câmera e fotos**, use o stream para determinar **quantos passos X/Y representam a largura/altura útil de uma foto**. Os valores iniciais de 600 X / 1500 Y são exemplos, NÃO medidas calibradas.
3. Na aba **Percurso**, selecione o método e defina a região entre **X inicial/final** e **Y inicial/final**. As coordenadas referem-se à **posição da câmera** (passos do Arduino) e devem ficar dentro dos limites indicados no painel.
4. Informe a cobertura medida em **passos** nos eixos X e Y e a **sobreposição desejada** de 0 a 70% (por exemplo 25%).
5. Clique em **Pré-visualizar pontos**. Isso apenas calcula um roteiro local, **não movimenta a máquina**.
6. Confira a linha do trajeto no painel; se estiver correta, clique em **Usar roteiro gerado**. Isso substitui somente a **lista local** após sua confirmação.
7. Confira as coordenadas e a ordem. Clique em **Salvar na ESP32-CAM**. **Somente depois**, quando o equipamento estiver pronto e você autorizar, **Iniciar percurso** movimentará a máquina e tirará as fotos.

## Importante sobre cobertura

- A sobreposição de imagens facilita não deixar plantas cortadas entre posições, mas pode gerar **a mesma planta em mais de uma foto**. O software de visão computacional deverá lidar com duplicatas.
- A quantidade de fotos depende da altura real da câmera, lente, orientação, iluminação e dimensões físicas da região. A fotografia anterior sozinha não fornece cobertura confiável em passos.
- O gerador inclui os dois extremos definidos para o **centro da câmera**, respeitando os limites do Arduino. Você deve certificar-se de que o enquadramento realmente cobre as bordas do canteiro.
- Os percursos completos fotografam a grade de paradas; o **Perímetro** fotografa só suas bordas.
- A ESP32-CAM aceita no máximo **48 pontos**. Se o cálculo exceder, o painel informa o total previsto e **não gera uma lista incompleta**.
- O gerador **não altera firmware, HOME, limites, velocidade, motores, calibração, stream, captura JPEG ou PHOTOACK**.
- **Sem sensores de fim de curso**, uma rota nos limites incorretos pode bater na estrutura; teste primeiro uma área pequena, com movimentos supervisionados e parada acessível.

## Atualização no Debian

Os arquivos novos/alterados ficam em `notebook/`:

- `painel.html`
- `painel.css`
- `painel.js`
- `planejador.js` **(arquivo novo obrigatório)**
- `controle.py` **(alterado somente para servir `/planejador.js`)**

**Não** precisa regravar Arduino ou ESP32-CAM se os firmwares v2.7/v2.8 atuais já funcionam.

Antes de atualizar, faça backup da pasta `capturas/`, do seu `controle.py` configurado e dos roteiros exportados. Atualize os cinco arquivos indicados, reinicie o servidor `controle.py` e recarregue o navegador com **Ctrl+Shift+R**. Se o browser mostrar erro 404 em `/planejador.js`, faltou atualizar `controle.py` ou reiniciar o servidor.

Os testes de software verificam o cálculo e a interface estática. Não substituem um ensaio com a máquina física.
