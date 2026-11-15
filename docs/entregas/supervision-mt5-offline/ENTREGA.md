# Entrega — painel Supervision a distinguir a MT5 fechada

forge-key: `sratlas:dispatch:3`  
agente: Cursor  
ramo: `claude/sratlas-supervision-mt5-offline`  
hora UTC do registo: 2026-11-15T07:29:10Z

## VERIFIED

Ficheiros alterados, e só estes:

- `backend/server.py` — `_live_supervision_snapshot` e `_supervision_snapshot_from_accounts`
- `backend/tests/test_supervision_live_snapshot.py`
- `frontend/src/components/SupervisionPanel.jsx`
- `frontend/src/components/supervisionTerminal.test.js`
- `docs/entregas/supervision-mt5-offline/RECECAO.md`
- `docs/entregas/supervision-mt5-offline/ENTREGA.md`

Comportamento observado nos testes que correram:

- Sem `terminal_offline` (omisso ou `False`), `services` continua `backend_ok`, `store_ok`, `bridge_ok`, `dashboard_ok`, sem `mt5_terminal_ok`, e a nota de bridge em baixo mantém-se.
- Com `terminal_offline=True`, `services.bridge_ok` é `True`, `services.mt5_terminal_ok` é `False`, o estado que seria OK passa a WARNING, e ALERT mantém-se ALERT.
- A nota nessa situação é: «MetaTrader 5 is closed or not logged in; displayed data comes from cache and may be outdated. Atlas reconnects automatically when it is open again.» Quando o estado já é ALERT ou WARNING por conta/alerta, a frase entra a seguir ao prefixo que já existia (`ALERT:` / `Degraded:`).
- `_live_supervision_snapshot` só chama `_probe_bridge_health` quando `_mt5_live_accounts` devolve `bridge_ok=False`. O indicador só entra se `_LAST_BRIDGE_REACHABLE is True` e `_LAST_TERMINAL_OK is False`.
- O painel mostra `<ServiceDot label="MT5 terminal" …>` logo a seguir a «Bridge», e só quando `svc.mt5_terminal_ok !== undefined`. O teste Jest lê o fonte do componente; não monta o Dashboard.

Comandos e códigos de saída:

```text
cd backend && python3 -m pytest tests/test_supervision_live_snapshot.py -q --tb=short
```

exit code 0 — 14 passed.

```text
cd backend && python3 -m pytest tests/test_bridge_down_status.py -q --tb=line
```

exit code 0 — 14 passed. A primeira tentativa, antes de `motor` estar instalado neste ambiente, falhou na recolha com `ModuleNotFoundError: No module named 'motor'` (exit code 1). O ficheiro de teste não foi alterado. Depois de instalar `motor==3.3.1`, o comando acima saiu 0.

```text
cd frontend && CI=true yarn test --watchAll=false --testPathPattern=supervisionTerminal --watchman=false
```

exit code 0 — 1 passed.

```text
cd frontend && CI=true yarn test --watchAll=false --testPathPattern=remainingVisual --watchman=false
```

exit code 0 — 9 passed. Regressão do fonte do `SupervisionPanel`; o ficheiro de teste não foi alterado.

`AGENTS.md` e `.cursor/rules/` não foram alterados. A Fase 3 não foi ligada. Não houve merge.

## INFERENCE

A frase pedida é a nota de cache. No caminho em que a bridge está em baixo, essa nota já era acrescentada à mensagem de ALERT e de WARNING. O mesmo formato foi usado aqui, para o estado ALERT continuar visível na mensagem. Quando não há outra causa de WARNING, a mensagem é só a frase pedida.

O probe real (`_probe_bridge_health`) e a leitura das flags no snapshot foram testados em separado. Não houve uma chamada HTTP real a uma bridge que respondesse `terminal_connected: false`. O teste de isolamento com `127.0.0.1:9` confirma o outro lado: bridge inalcançável, sem o indicador.

O Jest não monta o `SupervisionPanel` porque o componente importa `@/lib/api` e o `craco.config.js` não define `moduleNameMapper` para `@`. O teste do pedido verifica a linha nova no fonte.

## NOT VERIFIED

- Terminal MT5 real fechado, com a bridge de pé, no Windows.
- Instalador, bridge e `atlas_alerts.py` (fora do âmbito; não foram executados como prova deste pedido).
- Suite Jest completa e suite pytest completa.
- O painel no browser.
- Revisão Codex e autorização de merge do Fundador. Não fazer merge sem isso.
