# Sr. Atlas — Guia do Utilizador

Fonte canónica do texto mostrado no separador **Help** (`/docs`) da aplicação.
Se alterares este ficheiro, actualiza também `frontend/src/pages/Help.jsx`.

## Porque existe o Sr. Atlas

O trading é muitas vezes vendido como uma promessa de enriquecer depressa. Na realidade, a maioria de quem tenta acaba a agir por impulso — o que, sem perceber, se parece muito com jogar à sorte. Estudar a sério é difícil, quase como perceber como um avião voa.

O Sr. Atlas nasceu de uma necessidade real, não de uma oportunidade de negócio vista de fora: a de ter algo que ajudasse **a cada decisão**, e que ajudasse a **aprender com cada decisão** — não uma ferramenta que decide ou negoceia por ti.

**O que o Sr. Atlas NÃO faz:**

- Não decide por ti.
- Não compra nem vende nada sozinho.
- Não toca no teu dinheiro nem nas tuas ordens.

**O que o Sr. Atlas faz:** mostra-te a verdade sobre o estado real da tua conta, sem filtros e sem enfeites — mesmo quando essa verdade é desconfortável (por exemplo, avisar que os dados estão desatualizados, em vez de fingir que está tudo bem). A decisão continua sempre a ser tua; o Atlas só te ajuda a decidir a ver com clareza.

## O painel, elemento a elemento

### Barra superior

- **Separadores** (Overview, Strategies, Risk, Reports, Audit, About, Help, Settings) — as diferentes vistas do Atlas.
- **REFRESH FEED** — força uma atualização imediata dos dados, em vez de esperar pelo próximo ciclo automático.
- **v0.3.0 · [versão do código] · session-XXXX** — a versão exata instalada e o identificador da sessão atual, úteis para reportar problemas.

### Barra de estatísticas globais

- **TOTAL EQUITY** — o valor real da tua conta neste momento (saldo mais/menos o resultado das posições abertas).
- **DAILY P&L** — quanto ganhaste ou perdeste hoje, em valor e em percentagem.
- **AVG DD** — a média do "drawdown" (quanto a conta caiu desde o pico mais recente) nas contas monitorizadas.
- **OPEN POS** — número de posições abertas neste momento.
- **ACCOUNTS** — quantas contas estão "ao vivo" (ligadas e a receber dados reais) sobre o total configurado.
- **ALERTS** — número de alertas ativos a precisar da tua atenção.
- **UTC, data/hora** — o relógio de referência do sistema (hora universal, não a hora local).

### Tabela "MT5 Accounts"

Uma linha por conta MT5 ligada. Colunas: **Status**, **Account** (número da conta), **Broker** (corretora), **Strategy** (nome da estratégia associada), **Balance** (saldo), **Equity** (valor real, incluindo posições abertas), **Daily P&L**, **DD** (drawdown atual), **POS** (posições abertas), **LEV** (alavancagem, ex: 1:30), **Margin %** (nível de margem — quanto mais alto, mais folga tens antes de um "stop out" do broker).

### Secção "Risk"

Repete os números da conta selecionada (Equity, Balance, Margin Used, Margin Lvl, Daily P&L, Cur DD, Max DD, Leverage), e acrescenta:

- **Risk Limits** — três campos que defines tu: **Max Daily Loss (%)**, **Max Position Size (lots)**, **Max Open Positions** — com botão **Save Limits** para gravar.

### Painel "Sr. Atlas Supervision" (lado direito)

- Selo de estado geral: **OK** ou **WARNING**, com uma frase a explicar porquê (ex: "MT5 bridge is unavailable; displayed data comes from cache and may be outdated").
- Resumo: Total Equity, Daily P&L, Accounts Live, Active Alerts.
- **Core Services** — o estado de cada peça interna do Atlas, uma a uma:
  - **Backend** — o "cérebro" que serve o painel.
  - **Store** — onde os dados ficam guardados.
  - **Bridge** — a ligação direta ao teu terminal MT5.
  - **Dashboard** — o próprio painel que estás a ver.

  Cada uma mostra **OK** (verde) ou **DOWN** (vermelho). Se o Bridge estiver "DOWN", os números que vês vêm de uma cópia guardada (cache), não ao vivo — o Atlas avisa sempre quando isto acontece.
- **Generate Sr. Atlas Report** — botão para criar um relatório da conta.
- **Recent Reports** — lista dos relatórios já gerados.

### Gráficos, em baixo

- **Equity Curve · 90D** — a evolução do valor da tua conta nos últimos 90 dias.
- **Drawdown · 90D** — a evolução das quedas desde o pico, no mesmo período.

### Histórico de operações (fundo do Overview)

- **Trade History** — lista das tuas operações já fechadas: símbolo, lado (compra/venda), lotes, hora de abertura e fecho, duração em minutos, resultado (P&L) e estratégia associada. Podes filtrar por símbolo e por lado. No topo da tabela: resultado líquido total (**NET**), percentagem de operações ganhas (**WIN%**), e número de operações (**N**).

### Painel de alertas (lado direito)

- **Alerts** — contagem de alertas por gravidade (vermelho = crítico, laranja = aviso, azul = informativo). Mostra "No alerts" quando não há nada a assinalar.
- **System** — o "pulso" técnico do sistema: **API Latency**, **MT5 Bridge**, **Risk Engine**, **Telegram Notif**, **Last Heartbeat**, **Strategies Loaded**.

## Os outros separadores

### Strategies

Agrupa as tuas contas por estratégia em vez de por conta individual — útil se um dia tiveres várias contas a seguir a mesma abordagem. Mostra, por estratégia: contas associadas, quantas estão ao vivo, equity total, P&L diário, posições abertas, drawdown médio.

### Risk

A mesma secção "Risk" já descrita acima (Risk Limits), mas como página própria.

### Reports

Lista dos relatórios já gerados pelo botão "Generate Sr. Atlas Report", com estado, mensagem e origem de cada um. Vazio até gerares o primeiro.

### Audit

Um registo histórico de eventos do sistema (o "diário de bordo" do Atlas) — separado do histórico de operações. Vazio até haver eventos registados.

### About

Página de apresentação da marca — o logótipo e princípios da Forge Factory Lab ("Conhecimento, validação e verdade vêm antes da automação") e do Sr. Atlas. Não tem funcionalidade, é só identidade.

### Settings

Onde ligas (ou alteras, a qualquer momento, sem reinstalar) a tua conta MT5:

- **MT5 Login** — o número da tua conta.
- **MT5 Password** — fica guardada; podes deixar em branco para manter a atual.
- **Server / Broker** — o nome do servidor da tua corretora (ex: `PepperstoneUK-Demo`).
- **Terminal path** (opcional) — onde o MT5 está instalado; normalmente não precisas de mexer, o Atlas encontra sozinho.
- **Bridge port** — a porta técnica usada para a ligação (não precisas de alterar isto, a não ser que saibas exatamente porquê).
- **Save & Connect** — grava e liga.
- **Clear** — limpa os campos.

Um indicador no topo mostra sempre se estás **Connected** (ligado) ou não, em tempo real.

## Antes de começares

Precisas de:

1. Uma conta MetaTrader 5 (demo ou real) já criada, com login, password e nome do servidor (ex: `PepperstoneUK-Demo`).
2. O terminal MetaTrader 5 instalado neste computador.
3. No terminal MT5: ir a **Ferramentas → Opções → Expert Advisors** e ativar **"Allow algorithmic trading"**. Sem isto, o Sr. Atlas liga-se à tua conta mas não consegue confirmar que está tudo pronto.

## Como ligar a tua conta

1. Abre o Sr. Atlas.
2. Vai a **Definições**.
3. Introduz o login, password e servidor da tua conta MT5.
4. Guarda. O painel deve mostrar os teus dados reais em poucos segundos.

Não precisas de abrir o terminal MT5 manualmente primeiro — o Sr. Atlas trata disso sozinho.

## O que significam os estados do painel

| Estado | O que significa |
|---|---|
| **OK / Saudável** | Tudo ligado e a funcionar normalmente. |
| **WARNING (Aviso)** | Ligado, mas há algo a precisar da tua atenção — por exemplo, "Allow algorithmic trading" desligado no terminal. |
| **PAUSED (Em pausa)** | A supervisão está temporariamente parada — normalmente porque a ligação ao terminal MT5 foi interrompida. |

O Sr. Atlas nunca mostra "tudo saudável" se a ligação à tua conta estiver mesmo em baixo — preferimos avisar-te a mentir-te sobre o estado da tua conta.

## Problemas comuns

**"O painel não mostra os meus dados"**

- Confirma que o terminal MT5 está instalado neste computador.
- Confirma que "Allow algorithmic trading" está ativado (ver acima).
- Confirma o login/password/servidor em Definições.

**"Aparece um aviso sobre trading automático desligado"**

- Vai ao terminal MT5 → Ferramentas → Opções → Expert Advisors → ativa "Allow algorithmic trading".

**"Instalei mas não abre nada no browser"**

- Espera um minuto — os serviços podem demorar uns segundos a arrancar após a instalação.
- Se continuar sem abrir, tenta o atalho "Start Atlas" no menu Iniciar.

## Onde pedir ajuda

Se as secções acima não resolverem, usa o botão **"Reportar problema"** no painel. Ele junta automaticamente o estado de saúde do sistema e os registos relevantes — nunca as tuas credenciais — e envia diretamente para a Forge Factory Lab, com um clique.

---

*Este documento explica o que o Sr. Atlas faz e não faz. Se algo aqui não corresponder ao que vês no ecrã, é mais importante confiares no que vês do que neste texto — e por favor avisa-nos.*
