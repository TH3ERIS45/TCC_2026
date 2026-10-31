# Guia rápido — ATLAS CNC (interface da série 4.x)

Este guia fica na raiz por compatibilidade com os testes e referências existentes. Para a visão completa da arquitetura, instalação e limitações, consulte `README.md`.

## 1. Preparação do notebook

```bash
cd notebook
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python controle.py --configurar
python controle.py
```

A configuração solicita o endereço da ESP32-CAM e a chave API. O painel abre, por padrão, em `http://127.0.0.1:8765`.

## 2. Antes de movimentar

- Confirme a alimentação e a comunicação entre as placas.
- A maquete não tem fins de curso; faça a referência física manual antes de usar coordenadas.
- Confira a posição e o estado dos drivers na tela inicial.
- Use o botão **PARAR** quando precisar interromper uma operação.
- Não use a prévia MAX/3D como se fosse um comando de movimento: ela altera somente a visualização.

## 3. Criar e executar um percurso

1. Abra **Mapeamento**.
2. Adicione pontos manualmente, importe um CSV ou gere uma varredura.
3. Confira coordenadas e indicação de fotografia de cada ponto.
4. Salve o roteiro na ESP32-CAM.
5. Inicie a execução e acompanhe posição, progresso e bloqueio de fotografia no painel.

O protocolo de captura depende da confirmação `PHOTOACK` depois do recebimento e gravação do JPEG. Não remova essa etapa nem tente substituí-la por uma confirmação manual.

## 4. Câmera e mosaico

- A câmera ao vivo fica junto aos controles de enquadramento.
- As fotografias recebidas são salvas em `notebook/capturas/` e registradas no `manifesto.csv`.
- Os mosaicos são processados localmente a partir das coordenadas X/Y; não são ortofotos nem mapas métricos.
- O encaixe fino usa OpenCV. Para desativá-lo, altere a opção na área de resultados.

**Atenção:** o manifesto presente no pacote aponta para JPEGs `foto_...` que não vieram no ZIP. As imagens `Fotos...jpg` preservadas na pasta não foram vinculadas aos registros. Verifique `notebook/capturas/README.md` antes de gerar mosaicos.

## 5. Encerramento e diagnóstico

Pare a execução, aguarde a máquina ficar parada e confira o estado da câmera antes de desligar a alimentação. A aba **Diagnóstico** concentra telemetria e mensagens técnicas; use-a quando a tela inicial não for suficiente.

## 6. Testes sem hardware

Na raiz do projeto:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Testes aprovados não comprovam o funcionamento elétrico ou mecânico da maquete.
