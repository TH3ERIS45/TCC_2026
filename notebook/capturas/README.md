# Dados de captura

Esta pasta contém os JPEGs recebidos, o índice `manifesto.csv` e as configurações/resultados do mosaico.

## Atenção ao conjunto incluído neste pacote

O manifesto possui 55 registros que apontam para nomes no padrão `foto_000000001_X..._Y....jpg`, mas esses arquivos não estão presentes nesta cópia. Há 48 imagens legadas (`Fotos (n).jpg` e `Fotos 2 (n).jpg`), porém seus nomes não codificam o ID e as coordenadas do manifesto.

As imagens legadas foram mantidas intactas. Não foram renomeadas nem associadas por ordem, pois isso poderia atribuir uma coordenada incorreta a uma fotografia. O gerador de mosaico usa o manifesto e ignora arquivos que não estejam referenciados por ele.

Para reconstruir esse conjunto, é necessário recuperar os JPEGs originais `foto_...` ou fornecer uma tabela confiável relacionando cada imagem legada ao `photo_id`, `x_steps` e `y_steps` corretos.

`mosaicos/config.json` contém os parâmetros do gerador; `mosaicos/sessao_atual.json` registra o estado da última sessão local. Os arquivos `mosaico_*.jpg` são resultados gerados e não fazem parte do conjunto-fonte.
