# IPC timeout -10005 numa instalação nova do MetaTrader 5

Data da consulta: 2026-10-18. Sem custos, só páginas públicas. Este ficheiro separa facto, hipótese e o que já ficou de fora. Não há contas, palavras-passe nem dinheiro real.

O pacote em uso no Atlas é `MetaTrader5` 5.0.6231. O sintoma é `mt5.initialize` a devolver `(-10005, 'IPC timeout')`.

## Factos medidos nesta beta (não são fontes públicas)

Registados em `COORDINATION.md` (ramo `coord/forge-care`, 2026-10-18), sondas em `C:\Users\Lenovo\AtlasIPC`:

- Um perfil novo falha sempre com `-10005`, no Sandbox (instalador MetaQuotes, build 6272, e build 6230 sem rede) e no Windows real (cópias portáteis do 6230).
- Falhou também com sessão demo PepperstoneUK-Demo já iniciada, com o diálogo «Abrir uma Conta» fechado, com `[Experts] Enabled=1` / `Api=0`, com os `.ini` não secretos do perfil que funciona, com timeout de 300 s, e 7 minutos depois de o terminal estar aberto.
- Falhou com o terminal antigo fechado e a porta `127.0.0.1:22346` livre. O diário do perfil novo dizia `MCP started on 127.0.0.1:22346`.
- O terminal Pepperstone antigo (build 6230, perfil antigo) liga em 0,0 s. O bridge do Atlas arranca-o a frio no arranque do Windows.
- Dois terminais ao mesmo tempo: o segundo regista `MCP bind error on 127.0.0.1:22346 (10048)`.
- O perfil novo regista «started for MetaQuotes Ltd.». O antigo regista «Pepperstone MetaTrader 5 … for Pepperstone Limited».
- O perfil que funciona tem `config/jupyter.ini`, `settings.ini`, `metaeditor.ini`, `projects.ini`, `community.ini`, `agents.dat` e a pasta `liveupdate`. Copiar os `.ini` não secretos não chegou.

## O que a documentação oficial diz

- `initialize` (consulta 2026-10-18): <https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py>. Três formas: sem argumentos, com o caminho do `terminal64.exe`, ou com caminho, login, palavra-passe, servidor, `timeout` (omissão 60 000 ms) e `portable` (omissão `False`). Se for preciso, o terminal é lançado. Não há porta `22346` nesta página.
- Servidor MCP (consulta 2026-10-18): <https://www.metatrader5.com/en/terminal/help/mcp_and_ai/configuration>. Tools → Options → MCP. «Enable internal server». O exemplo de endereço é `http://127.0.0.1:22346/mcp`, com uma chave de API para clientes de IA (Claude Code, Codex). É o servidor MCP do terminal para agentes de IA, não o canal descrito em `initialize`.
- `origin.txt` (MetaQuotes, build 880, 7 de Dezembro de 2013): <https://www.metaquotes.net/en/metatrader5/news/4086>. O ficheiro é gerado na pasta de dados e contém o caminho da pasta de instalação. Não identifica a corretora.
- API Python e Experts (consulta 2026-10-18): <https://www.metatrader5.com/en/terminal/help/algotrading/trade_robots_indicators>. A opção «Disable automatic trading through the external Python API» vem desligada para negociação, por segurança. Os scripts Python só negoceiam quando essa opção está desligada. O mesmo texto trata isto como permissão de negociação, não como o estabelecimento da ligação `initialize`.

## Fórum MQL5 (páginas lidas em 2026-10-18)

- <https://www.mql5.com/en/forum/517169> — Adeyemi8819, 2026-09-28. Windows Server 2019, terminal 6231, pacotes 5.0.6180 e 5.0.6231, os dois falham com `-10005`. O terminal abre, inicia sessão, e o diário mostra `MCP started on 127.0.0.1:22346`. Já tinha excluído credenciais, processos órfãos, a porta 22346, 64 bits, a versão do pacote, `portable`, `initialize` com login contra lançar o terminal e só depois `initialize()`, as caixas de Algo Trading e da API Python, firewall, Defender, duas contas demo e um reboot. Sandro Begashvili, 2026-10-01: a causa habitual é «Python Integration» desligada; reiniciar o MT5; com vários terminais, passar o caminho. Alain Verleyen, 2026-10-01, no mesmo fio: com a integração Python desligada o erro que obteve foi `(-10003, "IPC initialize failed, Pipe server didn't answer in 60 sec")`, não `-10005`.
- <https://www.mql5.com/en/forum/517620> — 67193433, 2026-10-05. Build 6231, pacote 5.0.6231, Python 3.13, demo Exness, caminho explícito, caixa da API Python desmarcada, timeout 120 s, portable isolado: sempre `-10005`. Navid Mirzaaghazadeh, 2026-10-05: uma causa frequente é um processo elevado e o outro não; os dois ao mesmo nível, fechar os terminais e deixar o Python lançar o terminal. Alain Verleyen, no mesmo dia: «Nice assumption without any evidence.» AFX Trading, 2026-10-09 a 2026-10-10: mesmo utilizador, sem elevação, build 6249, pacote 5.0.6231, barras ou barras invertidas no caminho, timeout 60 s (~65 s medidos) → `-10005` enquanto nenhuma conta tinha sido aberta na interface. Depois de um login manual numa demo, o mesmo `initialize` passou em cerca de 4 ms. Perguntou como fazer o primeiro arranque sem esse login manual; a página lida não tem resposta a isso.
- <https://www.mql5.com/en/forum/443248> — fio antigo (Tessany, 2023-03-09) ainda activo. lax lutther, 2024-07-29: ligar «Allow algorithmic trading», desligar «Disable algorithmic trading via external Python API», e em File → Open an Account escolher a corretora e entrar uma vez. Eduard Xue, 2026-02-19: entrar uma vez não chega; é preciso procurar a corretora para o terminal descarregar a informação dos servidores, e é por isso que o MT5 da corretora funciona e o instalador oficial não. Paliativo que descreve: copiar `{pasta de dados}\config\servers.dat` de um terminal que já tenha ligado para `Config\servers.dat` e chamar `initialize` com `portable=True`.

## Pista a pista

| Pista | Veredicto | Porquê |
| --- | --- | --- |
| Porta `127.0.0.1:22346` é o canal do `initialize` | Refutada | A ajuda oficial descreve 22346 como MCP para clientes de IA. Nas sondas locais o MCP arrancou, a porta estava livre, e o `-10005` manteve-se. Dois terminais a disputar a porta são outra falha (`10048`), não a do perfil novo. |
| `origin.txt` escolhe a corretora | Refutada | Desde o build 880 (2013-12-07) o ficheiro só guarda o caminho da instalação. |
| Versão do pacote 5.0.6xxx | Refutada como causa única | 5.0.6180 e 5.0.6231 falharam igual no fórum 517169 (2026-09-28). Aqui o 5.0.6231 liga ao perfil antigo em 0 s. |
| O utilizador tem de abrir o terminal, em vez da API | Refutada como suficiente | `initialize` lança o terminal se for preciso (documentação). O perfil novo falhou aberto e a ser lançado. O perfil antigo é lançado pelo bridge. |
| Caixa «Python» / «API» em Expert Advisors | Refutada para este `-10005` | Alain Verleyen, 2026-10-01: integração Python desligada produz `-10003`, não `-10005`. Adeyemi8819, 2026-09-28: caixas já certas e mesmo assim `-10005`. Sonda local: `Enabled=1` / `Api=0` e mesmo assim `-10005`. A caixa continua a ser a permissão de negociação da ajuda oficial, não a correcção deste timeout. |
| Elevação (administrador contra utilizador normal) | Hipótese fraca, não é a diferença dos dois perfis | Sugerida no fórum 517620 (2026-10-05) e contestada no próprio dia por falta de prova. AFX Trading mediu o mesmo utilizador, sem elevação, e o `-10005` manteve-se até um login manual. Nas sondas locais os dois perfis foram exercitados da mesma forma e só o novo falhou. Vale a pena o diagnóstico dizer se o processo está elevado, porque o mecanismo é plausível noutros arranjos. Não é um candidato de correcção. |
| Chega iniciar sessão uma vez | Refutada neste perfil | AFX Trading (2026-10-10) viu 4 ms depois de um login manual noutro terminal. Aqui a sessão PepperstoneUK-Demo no perfil portátil novo continuou em `-10005` (título confirmado). |
| O terminal tem de ser o da corretora, ou de ter o `servers.dat` dessa corretora | Hipótese ainda aberta | Eduard Xue, 2026-02-19, fórum 443248. Bate certo com o diário local: «MetaQuotes Ltd.» falha, «Pepperstone Limited» liga. O login manual no perfil MetaQuotes não chegou. Os `.ini` foram copiados; `servers.dat` não. `portable=True` sozinho também não chegou. A combinação `servers.dat` + `portable=True` não foi medida. |

## Três candidatos

Nenhum está ligado por omissão. O perfil Pepperstone que já funciona não muda se as variáveis abaixo não estiverem definidas.

1. **Terminal da corretora** (passo do utilizador, sem alteração ao `initialize`). Instalar o MetaTrader 5 da corretora da conta demo (Pepperstone), não só o `mt5setup.exe` genérico da MetaQuotes. Uma instalação nova da corretora ainda não foi medida: o que funciona é o perfil antigo, e o que falha diz «MetaQuotes Ltd.». O diagnóstico imprime a linha «for …» do diário.
2. **`servers.dat` com `portable=True`** (opção `ATLAS_IPC_CANDIDATE=servers-dat`). Antes do `initialize`, o bridge copia só um `servers.dat` indicado por `ATLAS_MT5_SERVERS_DAT` para `ATLAS_MT5_DATA_DIR\config\servers.dat` e passa `portable=True`. É o paliativo de Eduard Xue (2026-02-19). Não copia `accounts.dat` nem qualquer outro ficheiro. Sem as três variáveis, o bridge faz o que faz hoje.
3. **Procurar a corretora no terminal genérico** (passo do utilizador). File → Open an Account, procurar a corretora e deixar o terminal acabar de descarregar os servidores, em vez de fechar o diálogo. Nas sondas o diálogo foi fechado e houve login demo, mas não ficou registado que a lista de servidores tivesse ficado completa. É a outra metade da mesma hipótese de Eduard Xue, sem copiar ficheiros. O diagnóstico só diz se `config/servers.dat` existe e o tamanho; não mostra o conteúdo.

O script `installer/scripts/diagnose_mt5.py` é só de leitura: versão do pacote, build e caminho, porta 22346, `initialize` com e sem caminho e com `portable`, e as últimas 30 linhas do diário. Não aceita login nem palavra-passe. `--no-initialize` salta as ligações.

## O que não se propõe

- Esperar pela porta 22346 ou tratar o MCP de IA como se fosse a API Python.
- Descer a versão do pacote.
- Voltar a copiar os `.ini` do perfil antigo.
- Escrever `origin.txt` à mão para «mudar a corretora».
- Ligar qualquer candidato por omissão.
