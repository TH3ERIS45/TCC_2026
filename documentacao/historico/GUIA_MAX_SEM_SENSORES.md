# ATLAS CNC v2.8 — Prévia MAX 3D e alinhamento manual por MAX

Esta atualização modifica **somente os arquivos do painel do notebook** (`painel.html`, `painel.css`, `painel.js` e `modelo3d.js`). Os firmwares do Arduino e da ESP32-CAM são **idênticos aos da v2.7**, com a correção `PHOTOACK` que já funciona na sua maquete.

## Objetivo

A estrutura não possui sensores de fim de curso. O painel não consegue determinar onde os eixos estão após ligar a máquina. A função **Visualizar MAX X/Y no 3D** coloca **somente o carrinho e o pórtico virtuais** nos extremos do curso, para você comparar a maquete física com o desenho. Não envia comandos aos motores nem muda a contagem de passos do Arduino.

| Coordenada | Referência lógica do firmware | Curso programado |
|---|---:|---:|
| X máximo | 1640 passos | 328 mm |
| Y máximo | 4550 passos | 910 mm |
| Centro X | 820 passos | 164 mm a partir do mínimo |
| Centro Y | 2275 passos | 455 mm a partir do mínimo |

**Esses números são os limites PROGRAMADOS**, não limites detectados. Confirme que escala, direção, microstepping, correias, polias e curso mecânico correspondem ao seu conjunto antes de mandar centralizar.

## Procedimento — referência por MAX

1. Abra **Movimentação → Mostrar MAX no modelo 3D** (ou **Visão geral → Visualizar MAX X/Y no 3D**). O painel passa para a vista 3D, mostra o carrinho em XMAX e o pórtico em YMAX e exibe **PRÉVIA VIRTUAL**. **Nada se move fisicamente.**
2. **Desligue a máquina e a alimentação dos motores** antes de ajustar a estrutura manualmente. Posicione cuidadosamente o carrinho em X máximo e o pórtico em Y máximo, **sem pressionar batentes nem forçar polias/correias**. Caso não seja possível alinhar manualmente com segurança, use ajustes graduais sob supervisão, não tente um deslocamento automático até o batente.
3. Religue a lógica e aguarde a conexão do Arduino e da ESP32-CAM. Na aba **Movimentação**, mantenha os **drivers desativados** (`Liberar drivers`). Verifique que a máquina está parada, sem foto pendente nem roteiro ativo.
4. Clique **Confirmar MAX físico + HOME manual (sem mover)**, leia a confirmação e confirme apenas se a posição física estiver correta. O painel envia `SETPOS X <XMAX> Y <YMAX>` e aguarda a telemetria. Em seguida, envia `HOME`, espera X/Y HOME confirmado e confere as coordenadas. **Esses comandos NÃO movimentam os motores.**
5. Clique **Ativar drivers** e, com o curso livre e calibrado, **Centralizar automaticamente**. O Arduino recebe `CENTER` e percorre o deslocamento **de MAX para o meio do curso**, chegando teoricamente a X=820, Y=2275. Fique pronto para parar imediatamente se houver problema.
6. Depois, use os botões X/Y e o modo **Marcar posição atual** normalmente para ensinar o roteiro.

## Alternativa — referência pelo mínimo (continua disponível)

Desligue antes do alinhamento físico. Posicione a estrutura em X0/Y0, religue e clique **Definir X0/Y0 (sem mover)** → **Confirmar HOME manual** → **Ativar drivers** → **Centralizar automaticamente**.

## Diferença entre os botões

- **Visualizar MAX X/Y no 3D**: afeta **apenas o desenho**; não escreve posição na placa.
- **Voltar à posição real**: volta a desenhar os valores de telemetria do Arduino.
- **Confirmar MAX físico + HOME**: escreve a **posição lógica máxima** no Arduino **sem acionar os motores**, após confirmação humana.
- **Centralizar automaticamente**: **aciona fisicamente os motores** de acordo com a referência lógica confirmada. Não há sensores para impedir colisões se o alinhamento estiver errado.

## Instalar no Debian

Preserve sua pasta `notebook/capturas` com todas as fotos. Copie os quatro arquivos alterados para a pasta `notebook` já usada no Debian, reinicie `controle.py` e pressione **Ctrl+Shift+R** no navegador.

```bash
source .venv/bin/activate
python controle.py --esp IP_DA_ESP32 --chave 'SUA_API_KEY'
```

Abra `http://127.0.0.1:8765`. Nada precisa ser regravado nas placas **se elas já executam a v2.7**.

## Validação

Os testes automatizados e um ensaio simulado do navegador verificaram a sequência `SETPOS X 1640 Y 4550` → `HOME` → `ENABLE 1` → `CENTER`; a visualização MAX não enviou nenhum comando de motor. **Ainda não houve teste físico nesta maquete.**
