# Revisão geral do projeto

## O que foi ajustado

- A interface foi simplificada e reorganizada para reduzir informações e comandos repetidos entre as telas.
- O receptor Flask agora concentra em constantes os limites de upload, porta e tamanho dos blocos do stream, além dos limites de histórico e galeria.
- Foi removido o contador de falhas de consulta do monitor de mosaico, que era incrementado mas nunca apresentado nem utilizado.
- A visualização 3D deixou de manter variáveis de movimento e tamanho que não eram lidas.
- Os limites usados pela validação do centro ensinado foram nomeados em `geometria.py`, com a observação de que o firmware continua sendo a referência final.
- A documentação de instalação, operação, arquitetura e limitações foi consolidada na raiz e nas pastas de dados/CAD.
- Foram removidos bytecodes Python, cache de testes e o arquivo `.gitkeep` de uma pasta que já contém dados.
- A credencial local `notebook/atlas_conexao.json` foi retirada da cópia distribuível. O arquivo `atlas_conexao.example.json` é apenas um modelo; configure a conexão novamente no notebook de operação.

## O que foi deliberadamente preservado

Os códigos `arduino_cnc.ino` e `esp32cam.ino` foram revisados, mas não tiveram sua lógica alterada nesta limpeza. Temporizações, watchdogs, passos dos motores e o fluxo `MOVE → DONE → captura → upload → PHOTOACK` são partes sensíveis da operação física. A remoção de trechos sem comprovação de que eram dispensáveis poderia comprometer o movimento ou deixar a máquina bloqueada/liberada indevidamente.

Também foram preservados o gerador de mosaico, o planejador de percurso, os fontes OpenSCAD disponíveis, os testes históricos e as imagens legadas. Não foi encontrada uma base confiável para apagar ou associar automaticamente esses dados.

## Pendências encontradas no pacote original

1. **Imagens:** o `manifesto.csv` possui 55 entradas que apontam para JPEGs `foto_...` ausentes. Há 48 JPEGs legados com nomes `Fotos...`, sem correspondência comprovada com os IDs e coordenadas. Estão preservados e descritos em `notebook/capturas/README.md`.
2. **OpenSCAD:** `main_2.scad` depende de `suporte_nema.scad` e `Suporte_Nema_Eixo_Y.scad`, não incluídos. A montagem CAD completa não pode ser considerada validada até que esses arquivos sejam recuperados.
3. **Hardware:** não houve compilação/flash em placas nem ensaio mecânico nesta revisão. A validação de software não substitui o teste real da CNC.

## Validação executada

- `python -m compileall -q notebook tests`: passou.
- `node --check` nos três módulos JavaScript: passou.
- Análise sintática do HTML: 136 IDs verificados, sem duplicatas.
- Análise sintática do CSS: passou.
- `python -m pytest -q`: 88 passaram; 1 foi ignorado porque Flask não está instalado no ambiente de revisão. Flask está declarado em `notebook/requirements.txt`; o teste de API do mosaico deve ser executado após instalar as dependências do projeto.


## Atualização v4.4 — sentido físico dos eixos

Após relato de que X+/X− e Y+/Y− moviam a maquete no sentido oposto ao modelo 3D, foram invertidas as polaridades `DIR_X_POS` e `DIR_Y_POS` no firmware Arduino. O painel e o firmware ESP32-CAM não foram alterados nesta correção. É necessário regravar o Arduino e confirmar os quatro sentidos com deslocamentos mínimos em região intermediária do curso; não houve teste físico nesta entrega. Consulte `documentacao/CORRECAO_SENTIDO_EIXOS_v4_4.md`.
