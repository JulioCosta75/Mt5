# Pedido: painel «Sr. Atlas Supervision» a distinguir a MT5 fechada da bridge em baixo

forge-key: sratlas:dispatch:3. Alteração à Fase 2 autorizada pelo Fundador a 2026-11-15. Construção: Cursor (neste ramo). Revisão: Claude + Codex. Merge só com o «sim» do Fundador.

**Problema:** com a MT5 fechada e a bridge a funcionar, o painel lateral «Sr. Atlas Supervision» mostra «MT5 bridge is unavailable…» e «Bridge: DOWN». O cartão «MT5 CONNECTION» já distingue os dois casos desde o #64 (`backend/server.py`: `_probe_bridge_health`, `_LAST_BRIDGE_REACHABLE`, `_LAST_TERMINAL_OK`).

**Âmbito, e só este:**
1. `backend/server.py`, `_live_supervision_snapshot()`:
   - quando `_mt5_live_accounts()` devolve `bridge_ok=False`, fazer `await _probe_bridge_health()`;
   - se `_LAST_BRIDGE_REACHABLE is True` e `_LAST_TERMINAL_OK is False`, passar `terminal_offline=True` a `_supervision_snapshot_from_accounts`.
2. `_supervision_snapshot_from_accounts(..., terminal_offline=False)`. Quando é True:
   - `services["bridge_ok"] = True`, e entra o campo novo `services["mt5_terminal_ok"] = False`;
   - a nota de cache passa a: «MetaTrader 5 is closed or not logged in; displayed data comes from cache and may be outdated. Atlas reconnects automatically when it is open again.»;
   - mantém-se: nesta situação o estado nunca é OK (no mínimo WARNING), e ALERT continua a ter prioridade.

   Sem o indicador, a resposta fica igual à de hoje.
3. `frontend/src/components/SupervisionPanel.jsx`: se `svc.mt5_terminal_ok` existir (não `undefined`), mostrar `<ServiceDot label="MT5 terminal" ok={svc.mt5_terminal_ok} />` logo a seguir a «Bridge».
4. Testes:
   - backend: com e sem o indicador;
   - frontend: Jest da linha nova, se der sem montar o Dashboard completo.

**Fora do âmbito:** `atlas_alerts.py`, a bridge, o instalador, as dependências e a Fase 3.

**Entrega:**
- `docs/entregas/supervision-mt5-offline/RECECAO.md` (hora UTC, agente, forge-key);
- `ENTREGA.md` com VERIFIED, INFERENCE e NOT VERIFIED separados, e os comandos de teste com o código de saída de cada um.
