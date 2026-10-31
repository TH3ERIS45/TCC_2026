# Modelo mecânico OpenSCAD — fontes originais

`main_2.scad` é o ponto de entrada da montagem e utiliza os módulos desta pasta. O pacote recebido está incompleto: o arquivo faz referência a dois arquivos que não estão presentes:

- `suporte_nema.scad`
- `Suporte_Nema_Eixo_Y.scad`

Esses arquivos definem módulos e parâmetros necessários para concluir a montagem. Não foram criados substitutos artificiais, porque isso alteraria a geometria mecânica sem uma fonte confiável. Recupere os arquivos originais e coloque-os nesta pasta para renderizar a montagem completa.

O módulo `notebook/modelo3d.js` é uma visualização esquemática independente; ele não substitui nem corrige as fontes CAD.
