# Entrega — IDs reais da loja e do produto

forge-key: `sratlas:dispatch:5`  
agente: Cursor  
ramo: `claude/sratlas-license-ids`  
hora UTC do registo: 2026-11-15T17:02:03Z

## VERIFIED

Ficheiros alterados, e só estes:

- `backend/license.py` — `LEMON_STORE_ID = 524518` (Forge Factory Lab); `LEMON_PRODUCT_ID = 1529348` (Sr. Atlas Pro). O override por ambiente continua só com `PYTEST_CURRENT_TEST` ou com `ATLAS_ENV` em `dev`, `development` ou `test`.
- `backend/tests/test_license.py` — os testes que dependiam dos dois ids a 0 passam a fixar `0` no monkeypatch. `test_production_lemon_ids` confirma os valores de produção e que, sem pytest e sem `ATLAS_ENV` de desenvolvimento, o ambiente não os substitui.
- `docs/entregas/licenca-ids/ENTREGA.md`

Comportamento observado:

- Com as constantes de produção e as variáveis de ambiente ausentes, `lemon_store_id()` devolve `524518` e `lemon_product_id()` devolve `1529348`.
- Com `LEMON_STORE_ID=10` e `LEMON_PRODUCT_ID=20`, e sem `PYTEST_CURRENT_TEST` nem `ATLAS_ENV`, os ids usados continuam `524518` e `1529348`.
- Os testes de comportamento que antes contavam com omissão a 0 fixam `LEMON_STORE_ID` e `LEMON_PRODUCT_ID` a `0`. A verificação da loja continua a ser saltada só nesse caso. Uma chave de outra loja, com os dois ids fixados a `0` e sem modo de desenvolvimento, continua Pro. Com `ATLAS_ENV=development`, o override `10` / `20` volta a valer.
- Loja só definida (`10`) e produto fixado a `0` não dá Pro. O aviso de configuração parcial sai uma vez.

Comando e código de saída:

```text
cd backend && python3 -m pytest tests/test_license.py -q --tb=short
```

exit code 0 — 52 passed, 10 warnings, 0.79s. Os 10 warnings são `DeprecationWarning` de `on_event` no arranque do FastAPI e do `TestClient` do Starlette. Nenhum teste falhou. Esta alteração não editou esses `on_event`. O `pytest.ini` do backend aplica `-n 2 --dist loadscope`.

`AGENTS.md` e `.cursor/rules/` não foram alterados. A Fase 3 não foi ligada. Não houve merge. Não entrou dependência nova.

## INFERENCE

- Uma instalação de cliente, sem `PYTEST_CURRENT_TEST` e sem `ATLAS_ENV` de desenvolvimento, usa estes dois ids mesmo que o ambiente traga outros. O teste cobre esse ramo ao apagar essas variáveis; não foi corrido um binário instalado no Windows.

## NOT VERIFIED

- Ativação real na Lemon Squeezy contra a loja `524518` e o produto `1529348`. Não há chave de teste neste ambiente.
- Instalador Windows e bridge MT5 ao vivo.
- Suite pytest completa.
- Revisão Codex deste HEAD e o «sim» do Fundador. Não fazer merge sem isso.
