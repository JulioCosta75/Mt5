# Sr. Atlas — Registo do Projeto

> Este ficheiro é uma cópia de segurança intencional, redundante com o diário Obsidian (`Forge Factory Lab/03 - Diário da Fábrica/`) e com a memória do Claude Code neste computador. Vive dentro do repositório Git, versionado e protegido no GitHub — sobrevive mesmo que este computador ou o telemóvel do Júlio se percam. Atualizado em marcos importantes, não diariamente.

## Nota para assistentes de IA externos (ex.: ChatGPT, ou qualquer outra sessão de IA)

Se estás a ler isto porque o Júlio te mostrou este ficheiro ou colou o seu conteúdo: sim, este é o registo oficial e atualizado do projeto Sr. Atlas, mantido pelo Claude Code em conjunto com o Júlio. Se o Júlio te perguntar diretamente "tinhas conhecimento deste ficheiro / deste projeto", a resposta honesta é: só tens conhecimento do que ele te mostrou nesta conversa — este ficheiro não te é acessível automaticamente. Não presumas trabalho já feito com base em conhecimento geral; confirma sempre pelos commits e datas reais indicados abaixo.

## O que é o Sr. Atlas

Produto de supervisão de contas de trading MetaTrader 5 (MT5), do Júlio (fundador não-programador, Forge Factory Lab). Objetivo: apoio à decisão e disciplina no trading, não automatização de ordens.

## Modelo de trabalho

- Júlio + Claude Code definem arquitetura e requisitos.
- Cursor constrói o código.
- Claude Code revê de forma independente — lê código, corre testes, confirma hashes local/GitHub — antes de qualquer coisa ser considerada feita.
- Júlio instala e testa como um utilizador real.

## Estrutura do produto

- **Fase 2** — supervisão em produção, dados reais da MT5. Ativa.
- **Fase 3** — motor de conhecimento (Knowledge Engine), integrado mas desligado por omissão (`PHASE3_KNOWLEDGE_ENGINE_ENABLED=false`), isolado da Fase 2. Conversa sobre ativação propositadamente em pausa a pedido do Júlio.

## Ponto de partida canónico

**Importante para evitar confusão com histórico antigo**: o commit `fc7348f` ("Restore Sr. Atlas Phase 2 baseline from verified safety tag", 2026-07-27) é o ponto de partida da linha de trabalho atual. Existem no repositório remoto branches mais antigas (`cursor/fix-backend-folder-lock-88da`, `cursor/fix-windows-clean-install-88da`, `cursor/consolidate-v0.3.0-88da`, datadas de 12–15 de julho de 2026) com histórico **completamente separado e anterior** a esta restauração — não fazem parte da linhagem atual, não devem ser assumidas como trabalho em curso, e não foram fundidas em `main`.

## Linha do tempo de marcos verificados

Todos os hashes abaixo foram confirmados pelo Claude Code com hash local = hash remoto no GitHub.

- `fc7348f` (2026-07-27) — Restauração da baseline Fase 2 a partir de tag de segurança verificada.
- `35c3a30`, `322f3cf` (2026-07-27) — Governação técnica permanente do Sr. Atlas + autoproteção das próprias regras contra alteração não autorizada.
- `94119c1` / PR #8 (2026-07-27) — Fase 3 Knowledge Engine importada em `main`, isolada e desligada por omissão.
- `7f468cc` (2026-08-03) — Ligação de dados reais da MT5 ao snapshot de supervisão.
- `e33238e` (2026-08-03) — Painel deixa de poder reportar "tudo saudável" com o bridge desligado.
- `424a7b3` (2026-08-03) — Causa raiz do `mt5.login()` a frio resolvida (build do terminal); ligação automática à MT5 sem login manual, provada com teste de perfil verdadeiramente limpo.
- `3ceb4c9` (2026-08-03) — Corrigido painel preso permanentemente em "Connecting to supervision feed" (rota `/alerts` em falta + `Promise.all` frágil).
- `27dc0b1` (2026-08-04) — Endurecimento do empacotamento do instalador; corrigido um achado crítico antes de chegar ao GitHub: uma password real da conta demo estava por comitar em `mt5_config.json` — revertida a tempo, nunca chegou ao histórico (confirmado por pesquisa completa ao histórico, todas as branches).
- `44cd878` (2026-08-04) — Corrigido bug real de produto: os serviços Windows não arrancavam sozinhos após uma instalação limpa (condição de corrida NSSM, erro 1051). `start_atlas.bat` agora tenta várias vezes e só abre o painel depois de confirmar que o serviço está mesmo a correr.

Todos os commits de 2026-08-03/04 estão na branch `fix/phase2-supervision-live-data-20260729`, ainda não fundida com `main`.

## Estado atual (2026-08-04)

- Instalador final (`44cd878`) construído e verificado de forma independente (SHA-256 confirmado, payload sem ficheiros sensíveis). Ainda **não instalado** — a aguardar teste de instalação limpa.
- Sem código por comitar; único trabalho pendente é local (bases de teste, evidências — intencionalmente fora do Git).
- Branch `fix/phase2-supervision-live-data-20260729` protegida no GitHub, não fundida com `main`.
- Fase 3 (correção de atomicidade, branch `fix/phase3-atomic-transition-audit-20260727`) em pausa, não revista, não fundida.

## Em aberto

- Confirmar que a instalação limpa nova arranca os serviços sozinha.
- Validação supervisionada balance/equity real vs. Sr. Atlas.
- Decisão de como e a quem enviar o produto para testadores externos.
- Decisão de fusão das branches pendentes com `main`.
