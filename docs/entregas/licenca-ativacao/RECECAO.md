# Receção

- forge-key: `sratlas:dispatch:4`
- agente: Cursor
- hora UTC: 2026-11-15T16:08:38Z
- ramo: `claude/sratlas-license-activation`
- HEAD ao receber: `46b65b23cce2acca4c8ea4696d2152efec469006`
- pedido: `docs/entregas/licenca-ativacao/PEDIDO.md`

Pedido recebido neste ramo. Construção limitada ao âmbito do `PEDIDO.md`. Sem ramo novo, sem PR novo e sem merge.

## VERIFIED

No HEAD acima, antes de qualquer alteração desta entrega:

- `backend/license.py` só chama `POST https://api.lemonsqueezy.com/v1/licenses/validate`, com o formulário `license_key`. Não envia `instance_id` e não chama `/licenses/activate` nem `/licenses/deactivate`.
- A tabela `atlas_license` é criada com `CREATE TABLE IF NOT EXISTS`. Não tem coluna `instance_id`. O comentário do módulo diz que tabelas existentes não são alteradas.
- `activate()` grava a chave quando a Lemon responde, e uma falha de rede não grava. A revalidação corre no máximo uma vez por dia (`REVALIDATE_AFTER`). Uma falha de rede ou HTTP ≥ 500 mantém o Pro durante 7 dias (`GRACE_AFTER_VALID`). `expired`, `disabled` e `invalid` já não usam essa margem.
- A resposta pública e o `scrub` não devolvem a chave. Os testes em `backend/tests/test_license.py` mockam o `httpx` e usam SQLite temporário.
- `POST /api/license/activate` e `GET /api/license` estão em `backend/server.py`. Não existe `POST /api/license/deactivate`. As duas rotas passam por `_license_response_is_safe`.
- Settings → License (`frontend/src/pages/Settings.jsx`) tem o botão Activate (`data-testid="license-activate"`). Não tem botão de desativação. `frontend/src/lib/api.js` só expõe `getLicense` e `activateLicense`.
- `httpx` já é dependência de `backend/license.py`. Não há `LEMON_STORE_ID` nem `LEMON_PRODUCT_ID` no código.
- O ramo está limpo. `AGENTS.md` e `.cursor/rules/` não foram alterados neste HEAD de receção. A autorização do Fundador está no `PEDIDO.md` (2026-11-15).

## INFERENCE

- Enquanto `LEMON_STORE_ID` ou `LEMON_PRODUCT_ID` for 0, a verificação da loja e do produto não corre, com um aviso único no log. Os dois têm de estar definidos para a verificação contar. Assim uma instalação de teste sem produto continua a aceitar uma chave que a Lemon marque como válida.
- Se a mesma chave já tiver `instance_id` guardado neste PC, `activate(key)` não volta a chamar `/licenses/activate`. Confirma com `/licenses/validate` e esse `instance_id`.
- Uma chave guardada como Pro sem `instance_id` (instalação anterior a esta alteração) regista este PC na próxima revalidação, chamando `/licenses/activate` uma vez. Sem isso o limite de ativações não passava a valer para quem já tinha a chave gravada.
- Uma recusa explícita (limite, chave desativada ou expirada, loja ou produto errados, instância desconhecida) põe `valid=0` e não usa a margem de 7 dias. A margem fica só para erro de rede, timeout ou HTTP ≥ 500.
- Loja ou produto errados depois de um `/licenses/activate` que a Lemon tenha aceite: o Atlas não fica Pro e tenta `/licenses/deactivate` dessa instância, para não consumir o lugar. Se essa libertação falhar por rede, o Pro continua negado na mesma.
- `deactivate()` com sucesso, ou com instância já desconhecida, apaga a chave e o `instance_id` locais e volta ao Free. Não apaga dados de conta. Falha de rede não altera o registo.
- O identificador do PC é `atlas-` mais 32 hex de SHA-256 do `MachineGuid` do Windows, ou de `uuid.getnode()` quando não há `MachineGuid`. O valor cru não sai da máquina.

## NOT VERIFIED

- Ativação, validação e desativação reais na Lemon Squeezy. Não há produto nem chave de teste neste ambiente.
- `MachineGuid` num Windows real.
- Instalador, bridge e o browser.

## Plano (só este âmbito)

- `backend/license.py` — ativar, validar com `instance_id`, verificar loja/produto, desativar, coluna `instance_id` com `ALTER TABLE` só se faltar.
- `backend/server.py` — `POST /api/license/deactivate`, com a mesma proteção das outras rotas de licença.
- `frontend/src/lib/api.js` e `frontend/src/pages/Settings.jsx` — botão «Deactivate on this PC».
- `backend/tests/test_license.py` e os testes de frontend que já fixam o contrato da licença.
